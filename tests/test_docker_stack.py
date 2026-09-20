"""
The Docker stack must order its two services and must not write into the repo (F-45).

`echo >> Step 1/2: ...` in the `.bat` scripts is a file redirect, not an arrow: cmd wrote four junk
files into the repo root and printed nothing. `docker-compose.yml` expressed the engine-before-web
ordering only inside the start scripts, so a bare `docker compose up` let Streamlit read a
half-written artifact.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_batch_scripts_echo_instead_of_redirecting():
    """`echo >> text` makes the first word a filename and the rest its contents."""
    for name in ("docker_start.bat", "docker_stop.bat"):
        for line in (REPO_ROOT / "scripts" / name).read_text().splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("echo"):
                assert ">" not in stripped, f"{name}: {stripped}"


def test_web_service_waits_for_a_successful_engine_run():
    """A bare `docker compose up` must not serve an artifact the engine has not finished writing."""
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    depends = compose["services"]["streamlit-web"]["depends_on"]
    assert depends["data-engine"]["condition"] == "service_completed_successfully"


def test_container_uid_is_a_build_arg():
    """The bind mount replaces the image's data/ with the host's, so the uid must be settable."""
    for name in ("Dockerfile.data_engine", "Dockerfile.streamlit"):
        dockerfile = (REPO_ROOT / name).read_text()
        assert "ARG UID=1000" in dockerfile
        assert "useradd -u ${UID}" in dockerfile
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    for service in ("data-engine", "streamlit-web"):
        assert compose["services"][service]["build"]["args"]["UID"] == "${UID:-1000}"


def test_data_is_not_sent_to_the_build_context():
    """Neither image copies data/; it is bind-mounted at runtime."""
    ignored = (REPO_ROOT / ".dockerignore").read_text().splitlines()
    assert "data/" in [line.strip() for line in ignored]
    for name in ("Dockerfile.data_engine", "Dockerfile.streamlit"):
        dockerfile = (REPO_ROOT / name).read_text()
        assert "COPY data" not in dockerfile
