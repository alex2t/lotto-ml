"""Bonus predictions come from the non-excluded pool, or fail clearly on input they cannot serve (F-5, F-42)."""

import numpy as np
import pytest

from ml_lotto.prediction.bonus_predictor import assign_bonus_to_models, generate_bonus_predictions
from ml_lotto.prediction.bonus_to_main_predictor import generate_bonus_to_main_predictions


class RisingProbability:
    """Stub model: probability rises with the single feature, so higher numbers rank first."""

    def predict_proba(self, X):
        p = np.asarray(X, dtype=float)[:, 0] / 100
        return np.column_stack([1 - p, p])


def features(excluded):
    return {n: {'x': n, 'was_bonus_last_10': int(n in excluded)} for n in range(1, 48)}


def predict(excluded, num_predictions=3, categories=None):
    if categories is None:
        categories = {n: ('hot', 'medium', 'cold')[n % 3] for n in range(1, 48)}
    picks, _ = generate_bonus_predictions(
        RisingProbability(), ['x'], features(excluded), categories, num_predictions
    )
    return picks


@pytest.mark.parametrize('pool_size', [0, 1, 2])
def test_pool_smaller_than_request_raises_value_error(pool_size):
    excluded = set(range(pool_size + 1, 48))
    with pytest.raises(ValueError, match='Bonus pool has'):
        predict(excluded)


def test_pool_exactly_the_request_size_uses_all_of_it():
    assert sorted(predict(set(range(4, 48)))) == [1, 2, 3]


def test_widest_real_exclusion_still_yields_three_distinct_allowed_numbers():
    # The bonus window holds 10 draws, so at most 10 numbers are ever excluded.
    excluded = set(range(38, 48))
    picks = predict(excluded)
    assert len(picks) == 3
    assert len(set(picks)) == 3
    assert not set(picks) & excluded


def test_three_picks_span_three_categories_when_the_top_two_share_one():
    # 47 and 46 rank first and second and are both cold (F-20).
    categories = {n: 'hot' for n in range(1, 48)}
    categories.update({47: 'cold', 46: 'cold', 45: 'medium'})
    picks = predict(set(), categories=categories)
    assert picks == [47, 45, 44]
    assert {categories[n] for n in picks} == {'hot', 'medium', 'cold'}


def test_every_model_gets_one_of_the_predictions():
    picks = predict(set())
    assignments = assign_bonus_to_models(picks, 4)
    assert sorted(assignments) == [1, 2, 3, 4]
    assert set(assignments.values()) == set(picks)


def test_empty_bonus_window_raises():
    """
    An empty bonus window is broken input, so it fails rather than returning nothing (F-42).

    Regression: the function returned a bare `[]` where it otherwise returns a 2-tuple, so the
    caller in quickpick.py died on `ValueError: not enough values to unpack (expected 2, got 0)`
    instead of on the real problem - no bonus ball in the last 10 draws.
    """
    with pytest.raises(ValueError, match='bonus window'):
        generate_bonus_to_main_predictions(RisingProbability(), ['x'], features(()), {}, {})
