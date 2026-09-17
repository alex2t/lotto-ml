"""
The probability array is positional: row i must be number i+1.

Every consumer reads it as `probabilities[num - 1]` — `penalties.py`, `pool_generator.py`,
`selection.py`. A features_dict missing one number used to produce a 46-long array, and
every number above the gap would then have silently received another number's
probability. It must raise instead (F-4).
"""

import numpy as np
import pytest

from ml_lotto.config import MAX_NUMBER
from ml_lotto.prediction.predictor import generate_predictions


class ProbabilityPassthrough:
    """Stub pipeline whose predicted probability is column 0 of X."""

    def predict_proba(self, X):
        p = np.asarray(X)[:, 0]
        return np.column_stack([1 - p, p])


def _models():
    return (
        {'model_1': {'pipeline': ProbabilityPassthrough(), 'config': {'name': 'stub'}}},
        {'model_1': ['identity']},
    )


def _features(numbers):
    """Feature whose value encodes the number, so misalignment is visible."""
    return {num: {'identity': num / 100} for num in numbers}


def test_every_number_keeps_its_own_probability():
    models, model_features = _models()
    probabilities = generate_predictions(
        models, model_features, _features(range(1, MAX_NUMBER + 1))
    )['model_1']

    assert len(probabilities) == MAX_NUMBER
    for num in range(1, MAX_NUMBER + 1):
        assert probabilities[num - 1] == pytest.approx(num / 100)


def test_a_missing_number_raises_instead_of_shifting_the_array():
    models, model_features = _models()
    numbers = [n for n in range(1, MAX_NUMBER + 1) if n != 23]

    with pytest.raises(KeyError):
        generate_predictions(models, model_features, _features(numbers))


def test_number_order_does_not_follow_dict_insertion_order():
    """A features_dict built out of order must still produce a number-ordered array."""
    models, model_features = _models()
    shuffled = list(range(MAX_NUMBER, 0, -1))
    probabilities = generate_predictions(
        models, model_features, _features(shuffled)
    )['model_1']

    assert probabilities[0] == pytest.approx(0.01)
    assert probabilities[MAX_NUMBER - 1] == pytest.approx(MAX_NUMBER / 100)
