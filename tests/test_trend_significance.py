"""
The "statistically significant trend" flag holds its 5% false-positive rate on fair draws (F-31).

It used to run Kendall's tau on a smoothed rolling series whose neighbouring points share most of
their data, and flagged 25-33 of 47 numbers on simulated fair draws. It is now Fisher's exact test on
the raw counts of the two windows the trend compares.
"""

import datetime
import random

import pytest

from lotto_analysis.analyzers.advanced_pattern_analyzer import calculate_trend_features

N_DRAWS = 498


def draw_history(draws):
    start = datetime.date(2022, 1, 1)
    return {
        (start + datetime.timedelta(days=3 * i)).isoformat(): {
            'winning_numbers_details': [{'number': b, 'is_bonus': j == 6} for j, b in enumerate(balls)]
        }
        for i, balls in enumerate(draws)
    }


def fair_draws(seed):
    rng = random.Random(seed)
    return [rng.sample(range(1, 48), 7) for _ in range(N_DRAWS)]


def test_fair_draws_flag_about_five_percent_of_numbers():
    """10 x 47 = 470 numbers with no trend: about 5% may be flagged, and some must be."""
    flagged = sum(
        f['trend_is_significant']
        for seed in range(10)
        for f in calculate_trend_features(draw_history(fair_draws(seed)), 47).values()
    )
    assert 0.005 <= flagged / 470 <= 0.06


def test_a_real_change_in_frequency_is_flagged():
    """Number 1 in 2 of the older 50 draws and 25 of the recent 50: a trend, and it is flagged."""
    rng = random.Random(0)
    draws = []
    for i in range(N_DRAWS):
        in_older = N_DRAWS - 100 <= i < N_DRAWS - 50
        in_recent = i >= N_DRAWS - 50
        want_one = (in_older and i % 25 == 0) or (in_recent and i % 2 == 0)
        others = rng.sample(range(2, 48), 7)
        draws.append(([1] + others[:6]) if want_one else others)
    features = calculate_trend_features(draw_history(draws), 47)
    assert features[1]['trend_is_significant']
    assert features[1]['appearance_trend'] > 0.2


@pytest.mark.parametrize('seed', [1, 2])
def test_significance_needs_an_older_window(seed):
    """Fewer than 100 draws: no older window to compare, so nothing is significant."""
    features = calculate_trend_features(draw_history(fair_draws(seed)[:80]), 47)
    assert not any(f['trend_is_significant'] for f in features.values())
