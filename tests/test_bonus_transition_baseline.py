"""
The bonus-to-main "boost over random" is measured against the right chance baseline (F-30).

The analyzer compared "a bonus ball comes up as a main number within 10 draws" with 10/47 (21%),
counting one ball per draw instead of six, and reported a 3.44x boost. In a fair draw any number
does that with probability 1 - (41/47)^10 = 74.5%, so on fair draws the boost must be about 1.0.
"""

import datetime
import json
import random

import pytest

from lotto_analysis.analyzers.bonus_to_main_analyzer import generate_bonus_to_main_analysis
from view.pages.prediction_validator import validate_bonus_transition

CHANCE_10_DRAWS = 1 - (41 / 47) ** 10


def fair_draw_history(n_draws, seed):
    """A draw history of uniformly random draws, in the shape the analyzer reads."""
    rng = random.Random(seed)
    start = datetime.date(2010, 1, 1)
    history = {}
    for i in range(n_draws):
        balls = rng.sample(range(1, 48), 7)
        history[(start + datetime.timedelta(days=3 * i)).isoformat()] = {
            'draw_index': i,
            'winning_numbers_details': [
                {'number': b, 'is_bonus': j == 6, 'category': 'medium', 'current_freshness_bin': 0}
                for j, b in enumerate(balls)
            ],
        }
    return history


@pytest.fixture(scope='module')
def fair_analysis():
    return generate_bonus_to_main_analysis(fair_draw_history(3000, seed=7), 47)


def always_transitioning_history(n_draws, seed):
    """Every bonus ball is a main number in the next draw, so every eligible bonus transitions."""
    rng = random.Random(seed)
    start = datetime.date(2010, 1, 1)
    history, previous_bonus = {}, None
    for i in range(n_draws):
        pool = [n for n in range(1, 48) if n != previous_bonus]
        main = ([previous_bonus] if previous_bonus else []) + rng.sample(pool, 6 if previous_bonus is None else 5)
        bonus = rng.choice([n for n in range(1, 48) if n not in main])
        history[(start + datetime.timedelta(days=3 * i)).isoformat()] = {
            'draw_index': i,
            'winning_numbers_details': [
                {'number': b, 'is_bonus': j == 6, 'category': 'medium', 'current_freshness_bin': 0}
                for j, b in enumerate(main + [bonus])
            ],
        }
        previous_bonus = bonus
    return history


def test_transition_rate_counts_only_bonus_balls_with_ten_draws_after_them():
    """F-32: 40 draws, all 30 eligible bonus balls transition - 100%, not 30/40 = 75%."""
    analysis = generate_bonus_to_main_analysis(always_transitioning_history(40, seed=3), 47)
    assert analysis['metadata']['overall_transition_rate'] == 1.0
    assert analysis['metadata']['total_bonus_appearances'] == 40
    for profile in analysis['per_number_transition_profile'].values():
        if profile['eligible_bonus_appearances']:
            assert profile['transition_rate'] == 1.0


def test_random_baseline_is_the_chance_of_any_number_within_10_draws(fair_analysis):
    factors = fair_analysis['transition_prediction_factors']
    assert factors['expected_random_rate'] == pytest.approx(CHANCE_10_DRAWS, abs=1e-4)


def test_validator_counts_any_recent_bonus_ball_whatever_its_past_rate():
    """The check used to demand transition_rate > 0.65 - a past rate that predicts nothing."""
    with open('data/lotto_bonus_to_main_patterns.json', encoding='utf-8') as f:
        bonus_data = json.load(f)
    profiles = bonus_data['per_number_transition_profile']
    low_rate = [int(n) for n, p in profiles.items()
                if p['days_since_last_bonus'] < 150 and p['transition_rate'] <= 0.65]
    stale = [int(n) for n, p in profiles.items() if p['days_since_last_bonus'] >= 150]
    assert low_rate and len(stale) >= 6

    _, _, score = validate_bonus_transition([low_rate[0]] + stale[:5], bonus_data)
    assert score == 100.0
    _, _, score = validate_bonus_transition(stale[:6], bonus_data)
    assert score == 70.0


def test_fair_draws_show_no_boost(fair_analysis):
    """3000 fair draws: the rate's standard error is ~0.008, so 0.95-1.05 is ~4.5 SE wide."""
    boost = fair_analysis['transition_prediction_factors']['boost_factor']
    assert 0.95 <= boost <= 1.05
