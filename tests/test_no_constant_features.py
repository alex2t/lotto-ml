"""
No model may train on a full-history constant (issue C-5).

Two failure modes are pinned here:

1. A feature the engine does not compute at all, silently substituted from
   `base_features_dict` by `walk_forward.py`'s `rec.get(fn, static_feat.get(fn, 0))`.
2. A feature the engine does produce, but by copying a static value, so it is identical
   for a given number in every training row.

Either way the model can only learn a per-number fixed effect from it, and the value was
estimated over the whole timeline - including the validation window - so it leaks
outcome information into the features.
"""

import pytest

from ml_lotto.config import (
    MAX_NUMBER,
    MODEL_1_CONFIG,
    MODEL_2_CONFIG,
    MODEL_3_CONFIG,
    MODEL_4_CONFIG,
)
from ml_lotto.data.loader import load_draw_history_with_bias_ratios
from ml_lotto.features.extractor import expand_feature_selection
from ml_lotto.features.walk_forward import PointInTimeFeatureEngine

DRAW_HISTORY = 'data/lotto_draw_history.json'
NUMBERS = range(1, MAX_NUMBER + 1)
EARLY_DRAW, LATE_DRAW = 200, 450

MODELS = [
    ('Model 1 Momentum', MODEL_1_CONFIG),
    ('Model 2 Jackpot', MODEL_2_CONFIG),
    ('Model 3 Complexity', MODEL_3_CONFIG),
    ('Model 4 Pool', MODEL_4_CONFIG),
]


@pytest.fixture(scope='module')
def engine():
    all_draws, _ = load_draw_history_with_bias_ratios(DRAW_HISTORY)
    return PointInTimeFeatureEngine(all_draws, {})


@pytest.fixture(scope='module')
def snapshots(engine):
    return engine.extract_features_at_draw(EARLY_DRAW), engine.extract_features_at_draw(LATE_DRAW)


@pytest.fixture(scope='module')
def produced(snapshots):
    early, _ = snapshots
    return sorted(k for k in early[1] if k != 'category')


def selected_for(config, produced):
    return expand_feature_selection(config['features'], produced)


@pytest.mark.parametrize('label,config', MODELS)
def test_every_selected_feature_is_computed_point_in_time(produced, label, config):
    """No selected feature may fall through to the static substitution path."""
    missing = sorted(set(selected_for(config, produced)) - set(produced))
    assert not missing, (
        f"{label} selects {len(missing)} feature(s) the engine does not compute, so they "
        f"are substituted from full-history values: {missing}"
    )


def _frozen_over_time(early, late, features):
    return [n for n in sorted(features)
            if all(early[num].get(n) == late[num].get(n) for num in NUMBERS)]


def _varies_across_numbers(snapshot, name):
    return len({snapshot[num].get(name) for num in NUMBERS}) > 1


@pytest.mark.parametrize('label,config', MODELS)
def test_no_selected_feature_is_a_per_number_constant(snapshots, produced, label, config):
    """
    This is the C-5 contract.

    A feature that differs between numbers but never changes over time is a per-number
    fixed effect estimated from the whole timeline. That is the leak: the estimate used
    for a 2023 training row was computed from outcomes including the validation window.
    """
    early, late = snapshots
    features = selected_for(config, produced)
    assert features, f"{label} selected no features - check the config"

    leaking = [n for n in _frozen_over_time(early, late, features)
               if _varies_across_numbers(early, n)]
    assert not leaking, (
        f"{label} trains on {len(leaking)} full-history per-number constant(s) - identical "
        f"at draw {EARLY_DRAW} and draw {LATE_DRAW} but varying between numbers: {leaking}"
    )


@pytest.mark.parametrize('label,config', MODELS)
def test_no_selected_feature_is_globally_degenerate(snapshots, produced, label, config):
    """
    Separate defect from C-5, found while writing that test.

    A feature with one value across every number AND every draw carries no information
    at all. Cause: `lotto_feature_interactions.json` stores median 0 for `total_count`,
    `recent_14` and `bonus_hit_contribution`, and `interactions.py:123` tests
    `val >= median`, which is vacuously true for non-negative inputs. `recent_14` is not
    even produced by SCENARIOS (recent_4/5/9/24), so its median defaulted to 0.

    These are candidates only - `select_features` drops them before training - so this is
    wasted computation rather than a leak. Kept as a test because the analyzer should not
    be emitting vacuous thresholds.
    """
    early, late = snapshots
    features = selected_for(config, produced)

    degenerate = [n for n in _frozen_over_time(early, late, features)
                  if not _varies_across_numbers(early, n)]
    assert not degenerate, (
        f"{label} selects {len(degenerate)} feature(s) with a single value for every number "
        f"at every draw: {degenerate}"
    )


def test_the_removed_c5_features_stay_out_of_every_model(produced):
    """
    Guards the C-5 decision. These were removed after measurement showed their removal
    changed validation ranking by less than 2 SE while cutting the Jackpot Optimizer's
    train/val AUC gap from 0.380 to 0.148. The odd/even, sum and range constraints they
    were meant to express are enforced in prediction/filters.py instead.
    """
    removed = {
        'odd_even_json',
        'range_spread_json',
        'sum_contribution_json',
        'window_saturation_penalty',
        'series_recent',
        'series_total',
        'lt_category_alignment',
        'lt_recency_weight',
    }
    for label, config in MODELS:
        back = sorted(removed & set(selected_for(config, produced)))
        assert not back, f"{label} has re-introduced full-history feature(s): {back}"
