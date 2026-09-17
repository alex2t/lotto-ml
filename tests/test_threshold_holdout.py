"""
The decision threshold must not be scored on the rows it was chosen from.

`calculate_comprehensive_metrics` picks the F1-maximising threshold on the earlier
half of the validation window and reports every threshold-dependent number on the
later half. Tuning and reporting on the same rows makes Precision / Recall / F1 /
Accuracy optimistic by construction (F-3).
"""

import numpy as np
import pytest

from ml_lotto.models.model_metrics import (
    calculate_comprehensive_metrics,
    split_threshold_tuning_rows,
)

NUMBERS_PER_DRAW = 47


class ProbabilityPassthrough:
    """Stub estimator whose predicted probability is column 0 of X."""

    def predict_proba(self, X):
        p = np.asarray(X)[:, 0]
        return np.column_stack([1 - p, p])

    def predict(self, X):
        return (np.asarray(X)[:, 0] >= 0.5).astype(int)


def _draws(n_draws, numbers_per_draw=NUMBERS_PER_DRAW):
    return split_threshold_tuning_rows(n_draws * numbers_per_draw, numbers_per_draw=numbers_per_draw)


def test_split_is_chronological_and_covers_every_row():
    tune, report = _draws(6)

    assert len(tune) + len(report) == 6 * NUMBERS_PER_DRAW
    assert set(tune).isdisjoint(set(report))
    assert tune.max() < report.min()


def test_split_falls_on_draw_boundaries():
    """A draw split across the two halves would leak its own rows into its score."""
    tune, report = _draws(7)

    assert len(tune) % NUMBERS_PER_DRAW == 0
    assert len(report) % NUMBERS_PER_DRAW == 0
    assert len(tune) == 3 * NUMBERS_PER_DRAW


def test_split_respects_variable_sized_draws():
    """The bonus-to-main model scores a different number of candidates each draw."""
    groups = np.array([0, 0, 0, 1, 1, 2, 2, 2, 2, 3])
    tune, report = split_threshold_tuning_rows(len(groups), groups=groups)

    assert list(tune) == [0, 1, 2, 3, 4]
    assert list(report) == [5, 6, 7, 8, 9]


def test_single_block_falls_back_to_halving_rows():
    tune, report = split_threshold_tuning_rows(9, numbers_per_draw=None)

    assert list(tune) == [0, 1, 2, 3]
    assert list(report) == [4, 5, 6, 7, 8]


def _validation_case():
    """
    Six draws, one winner each. The threshold that maximises F1 on the first three
    draws is high, and in the last three draws nothing clears it: the model ranks
    the winners last there.
    """
    n_draws = 6
    y = np.zeros((n_draws, NUMBERS_PER_DRAW))
    proba = np.full((n_draws, NUMBERS_PER_DRAW), 0.01)

    for d in range(n_draws):
        y[d, 0] = 1
        if d < n_draws // 2:
            proba[d, 0] = 0.9       # separable: threshold lands just under 0.9
        else:
            proba[d, 0] = 0.001     # the winner now scores below every other number
            proba[d, 1:] = 0.02

    return y.ravel().astype(int), proba.ravel().reshape(-1, 1)


def test_reported_operating_point_comes_from_untuned_rows():
    y_val, X_val = _validation_case()
    y_train = np.array([0, 1] * 20)
    X_train = np.linspace(0.01, 0.9, 40).reshape(-1, 1)

    metrics = calculate_comprehensive_metrics(
        pipeline=ProbabilityPassthrough(),
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        model_name='threshold_holdout_test',
        save_plots=False
    )

    half = 3 * NUMBERS_PER_DRAW
    assert metrics['threshold_tune_rows'] == half
    assert metrics['threshold_report_rows'] == half

    # The threshold was fitted where the winners were separable...
    assert metrics['optimal_threshold'] > 0.5
    # ...and scored where they are not, so it catches nothing. Tuning and scoring on
    # the same rows would have reported a non-zero recall here.
    assert metrics['recall_optimal'] == pytest.approx(0.0)
    assert metrics['f1_score_optimal'] == pytest.approx(0.0)
    assert metrics['confusion_matrix_optimal']['true_positives'] == 0


def test_threshold_free_metrics_still_use_the_whole_window():
    y_val, X_val = _validation_case()
    y_train = np.array([0, 1] * 20)
    X_train = np.linspace(0.01, 0.9, 40).reshape(-1, 1)

    metrics = calculate_comprehensive_metrics(
        pipeline=ProbabilityPassthrough(),
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        model_name='threshold_holdout_test',
        save_plots=False
    )

    assert metrics['topk_n_draws'] == 6
    assert metrics['pr_auc_baseline'] == pytest.approx(1 / NUMBERS_PER_DRAW)
