#!/usr/bin/env python3
"""
Verify the lotto pipeline after a change.

Runs the real tests, re-derives train/serve feature parity from the data, validates the
generated tickets, and reports validation metrics against the noise floor.

    python .claude/skills/lotto-verify/verify.py [--baseline path/to/model_comparison.csv]

Exits non-zero if any check fails.
"""

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

TEST_FILES = [
    'tests/test_walk_forward_parity.py',
    'tests/test_selection_invariants.py',
    'tests/test_metrics.py',
    'tests/test_no_constant_features.py',
    'tests/test_freshness_target.py',
    'tests/test_threshold_holdout.py',
    'tests/test_model_capacity.py',
    'tests/test_prediction_alignment.py',
    'tests/test_scraper_sources.py',
    'tests/test_wheel.py',
    'tests/test_permutation_check.py',
    'tests/test_high_number_distribution.py',
    'tests/test_bonus_predictor.py',
    'tests/test_draw_history_numbers.py',
    'tests/test_site_wording.py',
    'tests/test_bonus_transition_baseline.py',
    'tests/test_trend_significance.py',
    'tests/test_anomaly_detector.py',
    'tests/test_bonus_window.py',
    'tests/test_odd_even_affinity.py',
    'tests/test_pipeline_completeness.py',
    'tests/test_docker_stack.py',
    'tests/test_artifact_rounding.py',
]

# Validation window: 60 draws, 47 numbers, 7 winners per draw
N_DRAWS, N_NUMBERS, N_WINNERS = 60, 47, 7

failures = []


def section(title):
    print(f"\n{'=' * 72}\n  {title}\n{'=' * 72}")


def check(ok, label, detail=''):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  {detail}" if detail else ''))
    if not ok:
        failures.append(label)
    return ok


def run_tests():
    section('Tests')
    missing = [f for f in TEST_FILES if not (REPO_ROOT / f).exists()]
    if missing:
        return check(False, 'test files present', f'missing: {missing}')

    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', *TEST_FILES, '-q'],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    tail = [l for l in proc.stdout.strip().split('\n') if l.strip()][-1:]
    check(proc.returncode == 0, 'pytest', tail[0] if tail else '')
    if proc.returncode != 0:
        print('\n'.join(proc.stdout.split('\n')[-25:]))


def check_parity():
    """Re-derive train/serve parity independently of the test suite."""
    section('Train/serve feature parity')
    try:
        from ml_lotto.data.loader import load_draw_history_with_bias_ratios
        from ml_lotto.features.walk_forward import PointInTimeFeatureEngine
    except ImportError as exc:
        return check(False, 'import feature engine', str(exc))

    draws, _ = load_draw_history_with_bias_ratios(str(REPO_ROOT / 'data/lotto_draw_history.json'))
    engine = PointInTimeFeatureEngine(draws, {})
    served = json.loads((REPO_ROOT / 'data/lotto_trigger_periods.json').read_text(encoding='utf-8'))
    feats = engine.extract_features_for_next_draw()
    numbers = range(1, N_NUMBERS + 1)

    for feature, key in [('recent_4', 'last_4'), ('recent_5', 'last_5'),
                         ('recent_9', 'last_9'), ('recent_24', 'last_24')]:
        bad = [n for n in numbers if feats[n][feature] != served[str(n)]['recent'][key]]
        check(not bad, f'{feature} matches lotto_trigger_periods.json',
              f'{len(bad)}/47 mismatched' if bad else '47/47')

    bad = [n for n in numbers if feats[n]['total_count'] != served[str(n)].get('total_count')]
    check(not bad, 'total_count matches serving JSON',
          f'{len(bad)}/47 mismatched' if bad else '47/47')

    # the serving row must condition on every draw, including the most recent
    window = engine.draw_states[engine.N]['bonus_window']
    last_bonus = draws[-1].get('bonus_number')
    check(last_bonus in window, 'serving row includes the most recent draw',
          f'last bonus {last_bonus} in window' if last_bonus in window else 'serving row is stale')

    check(feats[last_bonus]['draws_since_bonus'] == 0,
          'draws_since_bonus counts back from the latest draw',
          f"got {feats[last_bonus]['draws_since_bonus']}, expected 0")


def check_tickets():
    section('Generated tickets')
    picks = REPO_ROOT / 'lottery_picks.txt'
    if not picks.exists():
        return check(False, 'lottery_picks.txt exists', 'run quickpick.py')

    try:
        from ml_lotto.prediction.filters import validate_line
    except ImportError as exc:
        return check(False, 'import filters', str(exc))

    text = picks.read_text(encoding='utf-8')
    lines = re.findall(
        r'Line (\d+): (.+?)\nMain Numbers \(6\): \[(.*?)\]\nBonus Ball: (\S+)', text)
    if not check(bool(lines), 'tickets parsed from lottery_picks.txt', f'{len(lines)} found'):
        return

    bonuses = []
    for idx, name, nums, bonus in lines:
        numbers = [int(x) for x in nums.split(',')]
        valid, why = validate_line(numbers)
        odd = sum(1 for x in numbers if x % 2)
        detail = (f'sum={sum(numbers)} span={max(numbers) - min(numbers)} '
                  f'odd/even={odd}/{6 - odd}')
        check(valid, f'Line {idx} {name[:28]} passes filters',
              detail if valid else f'{detail} :: {why}')
        check(len(set(numbers)) == 6, f'Line {idx} has 6 distinct numbers')
        if bonus != 'None':
            b = int(bonus)
            check(b not in numbers, f'Line {idx} bonus {b} is not a main number')
            bonuses.append(b)

    check(len(bonuses) == len(set(bonuses)), 'bonus balls are distinct across models',
          str(bonuses))


def noise_floor():
    """2 SE floor for the validation window."""
    mean = N_WINNERS * N_WINNERS / N_NUMBERS
    var = (N_WINNERS * (N_WINNERS / N_NUMBERS) * (1 - N_WINNERS / N_NUMBERS)
           * ((N_NUMBERS - N_WINNERS) / (N_NUMBERS - 1)))
    se_topk = math.sqrt(var / N_DRAWS)
    npos, nneg = N_WINNERS * N_DRAWS, (N_NUMBERS - N_WINNERS) * N_DRAWS
    a, q1, q2 = 0.5, 0.5 / 1.5, 0.5 / 1.5
    se_auc = math.sqrt((a * (1 - a) + (npos - 1) * (q1 - a * a)
                        + (nneg - 1) * (q2 - a * a)) / (npos * nneg))
    return mean, 2 * se_topk, 2 * se_auc


def check_metrics(baseline_path):
    section('Validation metrics')
    csv_path = REPO_ROOT / 'model_metrics/model_comparison.csv'
    if not csv_path.exists():
        return check(False, 'model_comparison.csv exists', 'run quickpick.py')

    try:
        import pandas as pd
    except ImportError as exc:
        return check(False, 'import pandas', str(exc))

    df = pd.read_csv(csv_path).set_index('Model')
    expected, floor_topk, floor_auc = noise_floor()
    print(f"  noise floor over {N_DRAWS} draws: 2 SE = {floor_auc:.3f} AUC, "
          f"{floor_topk:.3f} Top-7 AvgCaught (expected {expected:.3f})\n")

    cols = ['Val AUC-ROC', 'Top-7 Lift', 'Overfit Gap (AUC)']
    have = [c for c in cols if c in df.columns]
    print(f"  {'Model':<34}" + ''.join(f'{c:>20}' for c in have))
    for model in df.index:
        row = ''.join(f'{df.loc[model, c]:>20.4f}' for c in have)
        print(f"  {model[:33]:<34}{row}")

    if 'Val AUC-ROC' in df.columns:
        at_chance = ((df['Val AUC-ROC'] - 0.5).abs() < floor_auc).all()
        print(f"\n  all models within 2 SE of chance: {at_chance}"
              "  (expected for a fair draw)")

    if not baseline_path:
        return
    base_file = Path(baseline_path)
    if not base_file.exists():
        return check(False, 'baseline file exists', str(base_file))

    base = pd.read_csv(base_file).set_index('Model')
    print(f"\n  vs baseline {base_file}:")
    for model in df.index:
        if model not in base.index:
            continue
        for col, floor in (('Val AUC-ROC', floor_auc), ('Top-7 AvgCaught', floor_topk)):
            if col not in df.columns or col not in base.columns:
                continue
            delta = df.loc[model, col] - base.loc[model, col]
            verdict = 'noise' if abs(delta) < floor else 'EXCEEDS NOISE FLOOR'
            print(f"    {model[:30]:<32}{col:<18}{delta:+.4f}  {verdict}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', help='model_comparison.csv saved before the change')
    parser.add_argument('--skip-tests', action='store_true')
    args = parser.parse_args()

    if not args.skip_tests:
        run_tests()
    check_parity()
    check_tickets()
    check_metrics(args.baseline)

    section('Result')
    if failures:
        print(f"  {len(failures)} check(s) FAILED:")
        for f in failures:
            print(f"    - {f}")
        print("\n  Parity failures usually mean one side of a feature definition was changed.")
        return 1
    print("  All checks passed.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
