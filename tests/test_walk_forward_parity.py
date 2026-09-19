"""
Train/serve parity for the point-in-time feature engine.

The engine builds every training row; the serving JSON (lotto_trigger_periods.json)
builds the prediction row for the main models. If the two disagree, a model is fitted
on one distribution and applied to another. These tests pin the agreement.
"""

import json

import numpy as np
import pandas as pd
import pytest

from ml_lotto.config import MAX_NUMBER, ODDS_JSON_INPUT, TRAINING_START_DRAW
from ml_lotto.data.loader import load_draw_history_with_bias_ratios, load_hmc_json, load_odds_json
from ml_lotto.features.base import get_dynamic_recent_keys
from ml_lotto.features.extractor import extract_features_from_hmc_json
from ml_lotto.features.timing import calculate_days_since_bonus
from ml_lotto.features.walk_forward import PointInTimeFeatureEngine, next_draw_date

DRAW_HISTORY = 'data/lotto_draw_history.json'
TRIGGER_PERIODS = 'data/lotto_trigger_periods.json'
NUMBERS = range(1, MAX_NUMBER + 1)


@pytest.fixture(scope='module')
def draws():
    all_draws, _ = load_draw_history_with_bias_ratios(DRAW_HISTORY)
    return all_draws


@pytest.fixture(scope='module')
def engine(draws):
    return PointInTimeFeatureEngine(draws, {})


@pytest.fixture(scope='module')
def served():
    with open(TRIGGER_PERIODS, encoding='utf-8') as f:
        return json.load(f)


@pytest.mark.parametrize('feature,json_key', [
    ('recent_4', 'last_4'),
    ('recent_5', 'last_5'),
    ('recent_9', 'last_9'),
    ('recent_24', 'last_24'),
])
def test_recent_windows_match_serving_json(engine, served, feature, json_key):
    """Engine and serving JSON must agree on every recent_* count, for every number."""
    features = engine.extract_features_for_next_draw()
    mismatches = {
        num: (features[num][feature], served[str(num)]['recent'][json_key])
        for num in NUMBERS
        if features[num][feature] != served[str(num)]['recent'][json_key]
    }
    assert not mismatches, f"{feature} differs for {len(mismatches)} numbers: {mismatches}"


def test_total_count_matches_serving_json(engine, served):
    """
    total_count must be counted over the same window in training and serving.

    Regression: the JSON counted over the full CSV while the engine counts over the
    draw-history window, putting served values outside the trained range.
    """
    features = engine.extract_features_for_next_draw()
    mismatches = {
        num: (features[num]['total_count'], served[str(num)].get('total_count'))
        for num in NUMBERS
        if features[num]['total_count'] != served[str(num)].get('total_count')
    }
    assert not mismatches, f"total_count differs for {len(mismatches)} numbers: {mismatches}"


def test_next_draw_row_includes_the_most_recent_draw(engine, draws):
    """
    Regression for the off-by-one that made the serving row one draw stale.

    extract_features_at_draw(N-1) conditions on draws 0..N-2. The serving row must
    condition on all N draws, so the last draw's bonus has to be in the window.
    """
    last_bonus = draws[-1]['bonus_number']
    window = engine.draw_states[engine.N]['bonus_window']

    assert last_bonus in window, (
        f"bonus {last_bonus} from the most recent draw is missing from the serving "
        f"bonus window {window} - the serving row is stale by one draw"
    )
    assert engine.extract_features_for_next_draw() != engine.extract_features_at_draw(engine.N - 1)


def test_draws_since_bonus_counts_back_from_the_latest_draw(engine, draws):
    """
    draws_since_bonus must be 0 for the most recent bonus and grow going back.

    Regression: the engine returned the deque index, which is exactly inverted
    (newest bonus scored 9, oldest scored 0).
    """
    features = engine.extract_features_for_next_draw()
    window = engine.draw_states[engine.N]['bonus_window']

    assert features[draws[-1]['bonus_number']]['draws_since_bonus'] == 0

    for num in set(window):
        expected = len(window) - 1 - window.index(num)
        assert features[num]['draws_since_bonus'] == expected, (
            f"number {num}: got {features[num]['draws_since_bonus']}, expected {expected}"
        )

    outside = next(n for n in NUMBERS if n not in window)
    assert features[outside]['draws_since_bonus'] == 10


def test_serving_row_changes_when_a_draw_is_added(draws):
    """
    The property the whole pipeline depends on: adding a draw must move the features
    the models see. If it does not, every model re-picks the same numbers forever.
    """
    before = PointInTimeFeatureEngine(draws[:-1], {}).extract_features_for_next_draw()
    after = PointInTimeFeatureEngine(draws, {}).extract_features_for_next_draw()

    changed = {
        num for num in NUMBERS
        if any(before[num][k] != after[num][k]
               for k in ('days_since_last', 'recent_4', 'recent_9', 'total_count'))
    }
    # The 7 drawn numbers must move; recency shifts touch far more than that.
    assert len(changed) >= 7, f"only {len(changed)} numbers changed after a new draw"

    for num in draws[-1]['numbers']:
        assert before[num]['recent_4'] != after[num]['recent_4'] or \
               before[num]['days_since_last'] != after[num]['days_since_last'], \
               f"drawn number {num} did not move"


def test_engine_rejects_indices_past_the_next_draw(engine):
    """t == N is the serving row; anything beyond it is not defined."""
    engine.extract_features_at_draw(engine.N)  # must not raise
    with pytest.raises(ValueError):
        engine.extract_features_at_draw(engine.N + 1)
    with pytest.raises(ValueError):
        engine.extract_features_at_draw(-1)


def test_gap_statistics_match_the_draw_history(engine, draws):
    """
    Gap features come from running moments, not stored gap lists (C-15a). They must still
    equal the statistics of the actual gaps between a number's appearances.
    """
    features = engine.extract_features_for_next_draw()
    checked = 0
    for num in NUMBERS:
        seen = [t for t, d in enumerate(draws) if num in d['numbers']]
        gaps = np.diff(seen)
        if len(gaps) < 2:
            continue
        checked += 1
        assert features[num]['gap_variance'] == pytest.approx(np.var(gaps), rel=1e-12)
        assert features[num]['gap_cv'] == pytest.approx(np.std(gaps) / np.mean(gaps), rel=1e-12)
        assert features[num]['max_gap_ratio'] == pytest.approx(gaps.max() / np.mean(gaps), rel=1e-12)
    assert checked == MAX_NUMBER


def test_engine_view_matches_a_freshly_built_engine(engine, draws):
    """One engine per run serves every model through views; a view must equal a rebuild."""
    base = {num: {'win_bias_ratio': 1.0 + num / 100} for num in NUMBERS}
    view = engine.with_base_features(base)

    assert view.draw_states is engine.draw_states, "view must share state, not rebuild it"
    assert engine.base_features_dict == {}, "making a view must not alter the base engine"
    fresh = PointInTimeFeatureEngine(draws, base)
    for t in (TRAINING_START_DRAW, engine.N):
        assert view.extract_features_at_draw(t) == fresh.extract_features_at_draw(t)


def dates(*days):
    return [pd.Timestamp(d) for d in days]


@pytest.mark.parametrize('history,expected', [
    # Wed/Sat schedule: Sat -> Wed is 4 days, Wed -> Sat is 3
    (dates('2026-08-15', '2026-08-19', '2026-08-22', '2026-08-26', '2026-08-29'), '2026-09-02'),
    (dates('2026-08-12', '2026-08-15', '2026-08-19', '2026-08-22', '2026-08-26'), '2026-08-29'),
    # Mon/Wed/Sat since September 2026: Mon -> Wed is 2 days, which a median gap of 3 misses
    (dates('2026-09-02', '2026-09-05', '2026-09-07', '2026-09-09', '2026-09-12', '2026-09-14'), '2026-09-16'),
])
def test_next_draw_date_follows_the_current_schedule(history, expected):
    assert next_draw_date(history) == pd.Timestamp(expected)


@pytest.fixture(scope='module')
def extractor_row(draws, engine):
    """The main models' serving row, built as quickpick.py builds it."""
    hmc_data = load_hmc_json(TRIGGER_PERIODS)
    return extract_features_from_hmc_json(
        hmc_data,
        get_dynamic_recent_keys(hmc_data),
        calculate_days_since_bonus(draws, engine.next_draw_date),
        {},
        consecutive_patterns=load_odds_json(ODDS_JSON_INPUT)['patterns'],
        reference_date=engine.next_draw_date,
    )


@pytest.mark.parametrize('feature', ['days_since_last', 'category', 'days_since_bonus'])
def test_extractor_serving_row_matches_the_engine(engine, extractor_row, feature):
    """
    The main models train on engine rows and serve from the extractor (C-6b).

    Regression: the extractor counted days to the last draw and the engine to the next,
    so every served days_since_last was 3 days short and 4 numbers were served as hot
    that training would call medium. days_since_bonus was counted to the wall clock.
    """
    served = engine.extract_features_for_next_draw()
    mismatches = {
        num: (extractor_row[num][feature], served[num][feature])
        for num in NUMBERS
        if extractor_row[num][feature] != served[num][feature]
    }
    assert not mismatches, f"{feature} differs for {len(mismatches)} numbers: {mismatches}"
