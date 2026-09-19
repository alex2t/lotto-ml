"""
Bonus statistics use the 10 bonus balls BEFORE each draw, against the right chance baseline (F-33).

A draw's stored `recent_bonus_numbers` ends with that draw's own bonus - it is the window for the
next draw. Read as the window before the draw, every bonus "repeated" (rate 1.0), the recency
"penalty" came out 4.7x, and all ten recent bonus balls topped `predicted_bonus_score`. The baseline
10/47 also assumed 10 distinct balls; a 10-draw window averages ~9.2.
"""

import datetime
import json
import random

import pytest

from lotto_analysis.analyzers.bonus_analyzer import (
    calculate_main_from_recent_bonus,
    calculate_per_number_bonus_profile,
    calculate_recent_bonus_exclusion,
    pre_draw_bonus_window,
)
from view.pages.draw_history import create_draw_table_html


def fair_history(n_draws, seed):
    """Fair draws in the shape hmc_analyzer writes: the list is updated after each draw."""
    rng = random.Random(seed)
    start = datetime.date(2010, 1, 1)
    history, window = {}, []
    for i in range(n_draws):
        balls = rng.sample(range(1, 48), 7)
        before = set(window)
        window = (window + [balls[6]])[-10:]
        history[(start + datetime.timedelta(days=3 * i)).isoformat()] = {
            'draw_index': i,
            'recent_bonus_numbers': window[:],
            'winning_numbers_details': [
                {'number': b, 'is_bonus': j == 6, 'category': 'medium', 'current_freshness_bin': 0,
                 'is_recent_bonus_hit': b in before}
                for j, b in enumerate(balls)
            ],
        }
    return history


@pytest.fixture(scope='module')
def fair():
    return fair_history(3000, seed=11)


def test_pre_draw_window_is_the_ten_bonus_balls_before_the_draw():
    with open('data/lotto_draw_history.json', encoding='utf-8') as f:
        history = json.load(f)
    draws = sorted(history.items(), key=lambda x: x[1]['draw_index'])
    for idx in range(10, len(draws)):
        before = [d['bonus_number'] for _, d in draws[idx - 10:idx]]
        assert pre_draw_bonus_window(draws, idx) == before, draws[idx][0]


def test_bonus_repeat_rate_matches_chance_on_fair_draws(fair):
    """The old code read 1.0 here: the list always held the draw's own bonus."""
    result = calculate_recent_bonus_exclusion(fair, len(fair))['was_bonus_last_10']
    assert result['rate'] == pytest.approx(result['expected_if_random'], abs=0.03)
    assert result['expected_if_random'] < 10 / 47


def test_main_from_recent_bonus_shows_no_boost_on_fair_draws(fair):
    """SE of the rate over 18,000 main numbers is ~0.003; the old 10/47 baseline gave ~0.92."""
    assert 0.95 <= calculate_main_from_recent_bonus(fair)['boost_factor'] <= 1.05


def test_recency_penalty_is_neutral_on_fair_draws(fair):
    """The old code gave 4.7, boosting every recent bonus ball's predicted score."""
    profiles = calculate_per_number_bonus_profile(fair, 47)
    penalty = next(iter(profiles.values()))['data_driven_weights']['recency_penalty']
    assert 0.85 <= penalty <= 1.15


def test_draw_history_shows_the_window_before_each_draw():
    with open('data/lotto_draw_history.json', encoding='utf-8') as f:
        history = json.load(f)
    dates = sorted(history)
    html = create_draw_table_html(history, dates[-1])
    previous = ', '.join(str(n) for n in history[dates[-2]]['recent_bonus_numbers'])
    assert 'Last 10 Bonus Balls Before This Draw' in html
    assert f'value="{previous}"' in html
