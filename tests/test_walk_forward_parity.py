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

from ml_lotto.config import ACTIVE_MODELS, BONUS_TO_MAIN_MODEL_CONFIG, MAX_NUMBER, ODDS_JSON_INPUT, TRAINING_START_DRAW
from ml_lotto.data.loader import load_draw_history_with_bias_ratios, load_hmc_json, load_odds_json
from ml_lotto.features.base import get_dynamic_recent_keys
from ml_lotto.features.extractor import expand_feature_selection, extract_features_from_hmc_json, get_all_feature_names
from ml_lotto.features.timing import calculate_days_since_bonus
from ml_lotto.features.walk_forward import PointInTimeFeatureEngine, next_draw_date
from ml_lotto.models.bonus_to_main_trainer import _build_bonus_to_main_dataset
from ml_lotto.prediction.bonus_to_main_predictor import generate_bonus_to_main_predictions
from ml_lotto.utils.bonus_window import bonus_window_positions

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

    total_count is counted over all 7 balls from the first draw, so the new draw raises
    it by exactly one for each ball it drew, bonus included, and for no other number.
    recent_4 and days_since_last need not move (F-67): recent_4 is over the main six in
    a sliding window, and a ball drawn again two days after the last draw keeps its gap.
    """
    before = PointInTimeFeatureEngine(draws[:-1], {}).extract_features_for_next_draw()
    after = PointInTimeFeatureEngine(draws, {}).extract_features_for_next_draw()

    drawn = set(draws[-1]['numbers'])
    assert len(drawn) == 7
    for num in NUMBERS:
        rise = after[num]['total_count'] - before[num]['total_count']
        assert rise == (1 if num in drawn else 0), f"number {num}: total_count rose by {rise}"


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


@pytest.fixture(scope='module')
def model_columns(engine, extractor_row):
    """Every column some main model trains on: produced by the engine or the base features."""
    all_features = get_all_feature_names({1: {**extractor_row[1], **engine.extract_features_for_next_draw()[1]}})
    return sorted({col for config in ACTIVE_MODELS
                   for col in expand_feature_selection(config['features'], all_features)})


def test_serving_row_matches_the_training_row_for_every_model_column(engine, extractor_row, model_columns):
    """
    A main model is served the row it was trained on, column for column (F-34).

    A training row takes the engine's point-in-time value for every feature the engine
    computes, and the base features only for the rest. Regression: the models were served
    the extractor's row, whose gap statistics came from lotto_advanced_patterns.json with
    different formulas (47/47 numbers wrong), whose freshness_bin was missing so every
    freshness_bin interaction served 0, and whose has_consecutive_partner used another
    definition of a hot neighbour.
    """
    served = engine.with_base_features(extractor_row).extract_serving_rows()
    point_in_time = engine.extract_features_for_next_draw()
    mismatches = {}
    for col in model_columns:
        trained_on = {num: point_in_time[num][col] if col in point_in_time[num] else extractor_row[num][col]
                      for num in NUMBERS}
        wrong = [num for num in NUMBERS if served[num][col] != trained_on[num]]
        if wrong:
            mismatches[col] = len(wrong)
    assert not mismatches, f"served values differ from training values: {mismatches}"


def test_serving_rows_take_the_gap_statistics_from_the_engine(engine, extractor_row):
    """The F-34 columns are the engine's, not the extractor's JSON-derived values."""
    served = engine.with_base_features(extractor_row).extract_serving_rows()
    point_in_time = engine.extract_features_for_next_draw()
    for col in ('appearance_volatility', 'gap_consistency_score', 'max_gap_ratio',
                'freshness_bin', 'has_consecutive_partner'):
        assert all(served[num][col] == point_in_time[num][col] for num in NUMBERS), col


class RecordingModel:
    """Stands in for the fitted pipeline and keeps every row it is asked to score."""

    def __init__(self):
        self.rows = []

    def predict_proba(self, X):
        self.rows.append(list(X[0]))
        return np.array([[0.5, 0.5]])


def test_bonus_to_main_serves_the_row_it_was_trained_on(engine, draws):
    """
    The Bonus-to-Main model is served, for the next draw, the rows the trainer builds (F-40).

    Cut the history at draw t: what the predictor serves for the next draw must equal the
    trainer's rows for draw t, number for number. Regression: serving read a dict built
    from the extractor's row and the JSON profiles, so gap statistics, rolling rates, the
    transition weights and every freshness_bin interaction differed from training.
    """
    t = len(draws) - 1
    names = expand_feature_selection(BONUS_TO_MAIN_MODEL_CONFIG['features'],
                                     list(engine.extract_features_for_next_draw()[1]))
    trained, _, _ = _build_bonus_to_main_dataset(engine, draws, names, t, t + 1)

    history = draws[:t]
    model = RecordingModel()
    generate_bonus_to_main_predictions(
        model, names,
        PointInTimeFeatureEngine(history, {}).extract_features_for_next_draw(),
        bonus_window_positions(history),
        {}, num_predictions=3,
    )
    assert len(model.rows) == len(trained) > 0
    assert sorted(model.rows) == sorted(map(list, trained))
