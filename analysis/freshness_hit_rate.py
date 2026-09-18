"""
freshness_hit_rate.py
=====================
F-18: does a number's freshness bin change its chance of being drawn?

Enforcing a freshness pattern in selection can only help if it does. For every draw t
with a full 5-draw window behind it, each number's bin is taken as it stood before t -
the walk-forward engine's min(recent_4, 2), the same definition selection enforces - and
compared with whether it was one of the 6 main balls of t.

Rule fixed before running: chi-square test of bin vs hit, p < 0.05 keeps the mechanism;
otherwise its enforcement in selection is deleted.

Run from the project root: python analysis/freshness_hit_rate.py
"""

import sys
from pathlib import Path

import numpy as np
from scipy.stats import chi2_contingency

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml_lotto.config import MAX_NUMBER  # noqa: E402
from ml_lotto.data.loader import load_draw_history_with_bias_ratios  # noqa: E402
from ml_lotto.features.walk_forward import PointInTimeFeatureEngine  # noqa: E402

FIRST_FULL_WINDOW = 5
BINS = (0, 1, 2)
KEEP_P = 0.05


def bin_hit_table(engine: PointInTimeFeatureEngine) -> np.ndarray:
    """Rows are bins 0/1/2, columns are (not drawn, drawn) as a main ball."""
    table = np.zeros((len(BINS), 2), dtype=int)
    for t in range(FIRST_FULL_WINDOW, engine.N):
        features = engine.extract_features_at_draw(t)
        for num in range(1, MAX_NUMBER + 1):
            table[features[num]['freshness_bin'], int(engine.matrix_main[t][num])] += 1
    return table


def main():
    draws, _ = load_draw_history_with_bias_ratios('data/lotto_draw_history.json')
    engine = PointInTimeFeatureEngine(draws)
    table = bin_hit_table(engine)
    chi2, p, dof, _ = chi2_contingency(table)

    n_draws = engine.N - FIRST_FULL_WINDOW
    base_rate = table[:, 1].sum() / table.sum()
    print(f"Draws {FIRST_FULL_WINDOW}..{engine.N - 1} ({n_draws} draws), base hit rate {base_rate:.4f} (6/47 = {6 / 47:.4f})")
    print(f"{'bin':>4} {'exposures':>10} {'hits':>6} {'hit rate':>9} {'expected hits':>14}")
    for b in BINS:
        exposures = table[b].sum()
        print(f"{b:>4} {exposures:>10} {table[b, 1]:>6} {table[b, 1] / exposures:>9.4f} {exposures * base_rate:>14.1f}")
    verdict = "KEEP - bins differ in hit rate" if p < KEEP_P else "DELETE - no bin is drawn more often"
    print(f"chi2 = {chi2:.3f}, dof = {dof}, p = {p:.4f} -> {verdict}")


if __name__ == '__main__':
    main()
