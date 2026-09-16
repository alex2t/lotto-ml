"""
Correctness of the lottery-specific evaluation metrics.

Top-K is only meaningful within a single draw. Computing it over the flattened
validation set instead reports the K highest probabilities across every draw at once,
which is not a quantity anyone can act on.
"""

import numpy as np
import pytest

from ml_lotto.models.model_metrics import calculate_topk_accuracy

NUMBERS_PER_DRAW = 47
WINNERS_PER_DRAW = 7
N_DRAWS = 300


@pytest.fixture(scope='module')
def labels():
    rng = np.random.default_rng(0)
    y = np.zeros((N_DRAWS, NUMBERS_PER_DRAW), dtype=int)
    for d in range(N_DRAWS):
        y[d, rng.choice(NUMBERS_PER_DRAW, WINNERS_PER_DRAW, replace=False)] = 1
    return y


def test_expected_value_is_the_hypergeometric_mean(labels):
    m = calculate_topk_accuracy(labels.ravel(), np.zeros(labels.size), k_values=[7])
    assert m['top7_expected'] == pytest.approx(7 * WINNERS_PER_DRAW / NUMBERS_PER_DRAW)
    assert m['topk_n_draws'] == N_DRAWS


def test_random_scorer_has_lift_near_one(labels):
    rng = np.random.default_rng(1)
    scores = rng.random(labels.shape)
    m = calculate_topk_accuracy(labels.ravel(), scores.ravel(), k_values=[7, 20])

    assert m['top7_lift'] == pytest.approx(1.0, abs=0.25)
    assert m['top20_lift'] == pytest.approx(1.0, abs=0.25)


def test_perfect_scorer_catches_every_winner(labels):
    m = calculate_topk_accuracy(labels.ravel(), labels.ravel().astype(float), k_values=[7, 20])

    assert m['top7_winners'] == pytest.approx(float(WINNERS_PER_DRAW))
    assert m['top7_hit'] == pytest.approx(1.0)
    assert m['top20_winners'] == pytest.approx(float(WINNERS_PER_DRAW))


def test_adversarial_scorer_catches_nothing(labels):
    """Ranking winners last must score below chance, not above it."""
    m = calculate_topk_accuracy(labels.ravel(), (1 - labels).ravel().astype(float), k_values=[7])
    assert m['top7_winners'] == pytest.approx(0.0)
    assert m['top7_lift'] == pytest.approx(0.0)


def test_scores_are_ranked_per_draw_not_globally(labels):
    """
    One draw given uniformly huge scores must not absorb the whole top-K budget.

    With global ranking, top-7 would be drawn entirely from draw 0 and the metric
    would reflect a single draw instead of the average over all of them.
    """
    scores = np.full(labels.shape, 0.01)
    scores[0, :] = 10.0  # draw 0 dominates on any global ranking

    m = calculate_topk_accuracy(labels.ravel(), scores.ravel(), k_values=[7])
    # Within every draw the scores are flat, so the per-draw result is the
    # chance level, not whatever draw 0 happens to contain.
    assert m['top7_winners'] == pytest.approx(m['top7_expected'], abs=0.4)
    assert m['topk_n_draws'] == N_DRAWS


def test_falls_back_to_a_single_block_when_shape_does_not_divide():
    y = np.array([0, 1, 0, 1, 0])
    m = calculate_topk_accuracy(y, np.array([0.1, 0.9, 0.2, 0.8, 0.3]), k_values=[2])
    assert m['topk_n_draws'] == 1
    assert m['top2_winners'] == pytest.approx(2.0)
