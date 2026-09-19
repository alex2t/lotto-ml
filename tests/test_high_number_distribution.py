"""F-19: the count of main numbers >= 32 per draw, as drawpick.py writes it for the dashboard."""

from math import comb

import pytest

from lotto_analysis.analyzers.distribution_analyzer import analyze_high_number_distribution


def draw(main, bonus):
    """A draw-history entry in the shape drawpick.py builds: 6 main numbers, then the bonus."""
    return {'winning_numbers_details': [{'number': n} for n in main + [bonus]]}


LOG = {
    '2026/01/01': draw([1, 5, 9, 14, 22, 31], 40),    # 0 high - a high bonus must not count
    '2026/01/04': draw([2, 8, 15, 20, 33, 45], 3),    # 2 high
    '2026/01/07': draw([4, 11, 32, 38, 41, 47], 6),   # 4 high - 32 itself counts
    '2026/01/10': draw([3, 6, 12, 18, 27, 44], 30),   # 1 high
}


def test_counts_only_the_six_main_numbers_from_32_up():
    stats = analyze_high_number_distribution(LOG)
    assert {k: v['count'] for k, v in stats.items()} == {
        '0': 1, '1': 1, '2': 1, '3': 0, '4': 1, '5': 0, '6': 0}


def test_percentages_are_shares_of_the_draws():
    stats = analyze_high_number_distribution(LOG)
    assert stats['2']['percentage'] == 25.0
    assert stats['2']['odds'] == 0.25
    assert stats['3']['percentage'] == 0.0


def test_fair_share_is_the_hypergeometric_over_16_high_numbers():
    stats = analyze_high_number_distribution(LOG)
    for k in range(7):
        expected = comb(16, k) * comb(31, 6 - k) / comb(47, 6) * 100
        assert stats[str(k)]['fair_percentage'] == pytest.approx(expected, abs=0.005)
    assert sum(v['fair_percentage'] for v in stats.values()) == pytest.approx(100, abs=0.05)


def test_an_incomplete_draw_is_skipped():
    log = dict(LOG, **{'2026/01/13': {'winning_numbers_details': [{'number': 40}] * 5}})
    stats = analyze_high_number_distribution(log)
    assert sum(v['count'] for v in stats.values()) == 4
