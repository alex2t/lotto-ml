"""
No model may have the capacity to memorise its training set.

A depth-10 forest with unconstrained leaves reached train AUC 0.911 against val AUC
0.528 on ~15,800 rows — it was fitting per-number noise, which makes the model's
training behaviour useless as a diagnostic (C-15b). Capacity is constrained in two
places and both have to hold: the configured parameters, and the tuning grid that
overrides them at run time.
"""

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml_lotto.config import (
    BONUS_MODEL_CONFIG,
    BONUS_TO_MAIN_MODEL_CONFIG,
    MODEL_2_CONFIG,
    MODEL_3_CONFIG,
)
from ml_lotto.models.hyperparameter_tuning import get_random_forest_grid, get_xgboost_grid
from ml_lotto.models.pipelines import create_model_pipeline

PARAM_PREFIX = 'classifier__estimator__'


def _pure_noise(n_rows=8000, n_features=12, positive_rate=0.15, seed=0):
    """Features carrying no information about the label, at the lottery's class balance."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n_rows, n_features))
    y = (rng.random(n_rows) < positive_rate).astype(int)
    return X, y


def test_configured_forest_cannot_memorise_pure_noise():
    """
    Fitted on labels no feature predicts, an honest model scores near 0.5 on its own
    training rows. The old depth-10 forest reaches 0.878 here.
    """
    X, y = _pure_noise()
    pipeline = create_model_pipeline(MODEL_2_CONFIG)
    pipeline.fit(X, y)

    train_auc = roc_auc_score(y, pipeline.predict_proba(X)[:, 1])
    assert train_auc < 0.70


def test_configured_forest_constrains_depth_and_leaf_size():
    params = MODEL_2_CONFIG['algorithm_params']

    assert params['max_depth'] <= 6
    assert params['min_samples_leaf'] >= 100
    assert params['max_features'] not in (None, 1.0)


@pytest.mark.parametrize('quick', [True, False])
def test_no_tuning_candidate_escapes_the_constraint(quick):
    """
    The grid overrides the configured parameters, and its CV scores sit at chance,
    so its pick among near-equal candidates is arbitrary. One unconstrained candidate
    is therefore enough to bring the memorising model back.
    """
    grid = get_random_forest_grid(quick=quick)

    assert grid[PARAM_PREFIX + 'max_depth'], 'depth must be searched, not left unbounded'
    for depth in grid[PARAM_PREFIX + 'max_depth']:
        assert depth is not None and depth <= 6

    for leaf in grid[PARAM_PREFIX + 'min_samples_leaf']:
        assert leaf >= 100

    for max_features in grid[PARAM_PREFIX + 'max_features']:
        assert max_features not in (None, 1.0)


def test_configured_xgboost_cannot_memorise_pure_noise():
    """Depth 3 with min_child_weight=3 reaches 0.758 on noise the label does not follow."""
    X, y = _pure_noise()
    pipeline = create_model_pipeline(MODEL_3_CONFIG)
    pipeline.fit(X, y)

    train_auc = roc_auc_score(y, pipeline.predict_proba(X)[:, 1])
    assert train_auc < 0.60


@pytest.mark.parametrize('quick', [True, False])
def test_no_xgboost_tuning_candidate_escapes_the_constraint(quick):
    grid = get_xgboost_grid(quick=quick)

    for depth in grid[PARAM_PREFIX + 'max_depth']:
        assert depth is not None and depth <= 4

    for min_child_weight in grid[PARAM_PREFIX + 'min_child_weight']:
        assert min_child_weight >= 100

    for reg_lambda in grid[PARAM_PREFIX + 'reg_lambda']:
        assert reg_lambda >= 10


@pytest.mark.parametrize('config', [BONUS_MODEL_CONFIG, BONUS_TO_MAIN_MODEL_CONFIG],
                         ids=['bonus', 'bonus_to_main'])
def test_auxiliary_logistic_models_select_features_with_l1(config):
    """
    L2 shrinks coefficients but keeps their ranking, and AUC only sees the ranking —
    which is why lowering C never moved these models' train/val gap. L1 has to be the
    penalty for the constraint to bite.
    """
    assert config['algorithm_params']['penalty'] == 'l1'
    assert config['algorithm_params']['C'] <= 0.1


def test_bonus_logistic_discards_most_features_on_noise():
    """L2 at C=1.0 keeps all 32 coefficients; the configured L1 model keeps a handful."""
    rng = np.random.default_rng(1)
    X = rng.normal(size=(8000, 32))
    y = (rng.random(8000) < 0.02).astype(int)  # the bonus ball's ~1-in-47 base rate

    model = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(**BONUS_MODEL_CONFIG['algorithm_params']))
    ])
    model.fit(X, y)

    non_zero = int((model.named_steps['clf'].coef_ != 0).sum())
    assert non_zero <= 10
