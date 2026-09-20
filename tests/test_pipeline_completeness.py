"""
A phase that fails in the data engine must stop the run, not be swallowed (F-43).

The Docker engine image lacked scikit-learn, so Phase 16's weight learning returned an error stub,
the recommendation analyzer raised KeyError, the phase handler printed a warning and the run exited
0. The completeness check passed because both Phase 16 artifacts still existed on the mounted
volume from an earlier host run.

A run must also be reproducible wherever it happens (F-44): the artifacts are stored with LF
endings, and the engine dependencies are pinned exactly.
"""

import builtins
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from drawpick import verify_artifacts
from lotto_analysis.analyzers.hmc_success_analyzer import HMCSuccessAnalyzer

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_engine_requirements_list_scikit_learn():
    """The engine image must carry every dependency a phase can reach, lazy imports included."""
    requirements = (REPO_ROOT / "requirements-engine.txt").read_text()
    assert "scikit-learn" in requirements


def test_missing_sklearn_raises_instead_of_returning_a_stub(monkeypatch):
    """A missing dependency is a bug, not a value: no {'error': 'scikit-learn not available'}."""
    real_import = builtins.__import__

    def no_sklearn(name, *args, **kwargs):
        if name.startswith("sklearn"):
            raise ImportError("No module named 'sklearn'")
        return real_import(name, *args, **kwargs)

    analyzer = HMCSuccessAnalyzer(draws_data={}, hmc_data={})
    monkeypatch.setattr(builtins, "__import__", no_sklearn)
    with pytest.raises(ImportError):
        analyzer._learn_feature_weights([{}])


def test_phase_16_failure_is_fatal():
    """The Phase 16 handler re-raises; it must not tell the run to carry on."""
    source = (REPO_ROOT / "drawpick.py").read_text(encoding="utf-8")
    phase_16 = source[source.index("Phase 16: HMC Configuration Recommendation"):]
    handler = phase_16[phase_16.index("except Exception as e:"):]
    assert "raise" in handler[:handler.index("\n\n")]
    assert "System will continue without HMC recommendations" not in source


def test_verify_artifacts_accepts_files_written_by_this_run(tmp_path):
    run_started = time.time()
    artifact = tmp_path / "written.json"
    artifact.write_text("{}")
    verify_artifacts([str(artifact)], run_started)


def test_verify_artifacts_rejects_a_missing_file(tmp_path):
    with pytest.raises(SystemExit) as exit_info:
        verify_artifacts([str(tmp_path / "absent.json")], time.time())
    assert exit_info.value.code == 1


def test_verify_artifacts_rejects_a_file_left_from_an_earlier_run(tmp_path):
    """An existence check passes on any volume that has ever held a complete run."""
    stale = tmp_path / "stale.json"
    stale.write_text("{}")
    run_started = stale.stat().st_mtime + 1
    with pytest.raises(SystemExit) as exit_info:
        verify_artifacts([str(stale)], run_started)
    assert exit_info.value.code == 1


# --- F-44: the artifacts must not churn between the owner's PC and the VPS ---------------------

def test_data_artifacts_are_stored_with_lf_endings():
    """`json.dump` writes CRLF on Windows and LF in the container; git must normalise both."""
    checked = [
        "data/lotto_draw_history.json",
        "data/irish500.csv",
        "data/analysis/lotto_interaction_summary.csv",
        "data/lotto_hmc_recommendations.txt",
    ]
    attrs = subprocess.run(
        ["git", "check-attr", "eol", "--"] + checked,
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    for path in checked:
        assert f"{path}: eol: lf" in attrs


def test_engine_dependencies_are_pinned_exactly():
    """The VPS and the owner's PC must resolve the same versions; the ML layer trains on the
    artifacts they produce, so a drifting engine is a drifting training set."""
    lines = [
        line.strip()
        for line in (REPO_ROOT / "requirements-engine.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert lines
    for line in lines:
        assert "==" in line, line


# --- F-47: a failed data load must exit non-zero, not return 0 ---------------------------------

def test_a_missing_csv_exits_non_zero(tmp_path):
    """`docker compose` starts the dashboard on whatever the engine leaves behind unless the
    engine's exit code says the run failed."""
    (tmp_path / "data").mkdir()
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT), PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "drawpick.py")],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert "not found" in proc.stdout
