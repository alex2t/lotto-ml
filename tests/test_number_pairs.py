"""
Number pair co-occurrence, and the six-ball spread that goes with it.

The dossier shows the numbers a number is most often drawn with. That is a fact about past
draws, so `number_pair_analyzer.py` counts it and `drawpick.py` writes it - the website
computes nothing. A raw count is meaningless without what chance alone gives, so the
artifact carries the fair-draw expectation beside it, the way F-38 requires for odd/even.

`draw_range_6` is here too: `draw_range` beside it spans all seven balls and is
systematically wider, so comparing a six-number line with it overstated how ordinary a wide
line was (F-63).
"""

import json
from itertools import combinations
from pathlib import Path

import pytest

from lotto_analysis.analyzers.number_pair_analyzer import analyze_number_pairs

REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_NUMBER = 47


@pytest.fixture(scope='module')
def pairs():
    return json.loads(
        (REPO_ROOT / 'data' / 'lotto_number_pairs.json').read_text(encoding='utf-8')
    )


@pytest.fixture(scope='module')
def odds():
    return json.loads(
        (REPO_ROOT / 'data' / 'lotto_odds_results.json').read_text(encoding='utf-8')
    )


def test_every_number_has_partners(pairs):
    assert set(pairs['per_number']) == {str(n) for n in range(1, MAX_NUMBER + 1)}


def test_a_pair_is_counted_once_from_each_side(pairs):
    """If 7 was drawn with 23 nine times, 23 was drawn with 7 nine times."""
    per_number = pairs['per_number']
    for number, record in per_number.items():
        for partner in record['top_partners']:
            other = per_number[str(partner['number'])]['top_partners']
            back = [p for p in other if p['number'] == int(number)]
            # The partner may fall outside the other number's top list; when it is there it
            # must carry the same count.
            if back:
                assert back[0]['count'] == partner['count'], (number, partner)


def test_pair_counts_match_the_draws_they_were_counted_from(pairs):
    """Every pair count adds up to C(6,2) per draw."""
    total = sum(pairs['pair_counts'].values())
    expected = pairs['metadata']['total_draws'] * len(list(combinations(range(6), 2)))
    assert total == expected


def test_the_fair_draw_expectation_is_published_beside_the_counts(pairs):
    """
    A count on its own reads as an affinity. In a fair draw every pair is equally likely,
    so the expectation must be shown with it (F-38's rule, applied here).
    """
    total_draws = pairs['metadata']['total_draws']
    pairs_per_draw = len(list(combinations(range(6), 2)))
    possible = len(list(combinations(range(MAX_NUMBER), 2)))
    assert pairs['expected_count_per_pair'] == pytest.approx(
        total_draws * pairs_per_draw / possible, abs=0.01
    )


def test_the_top_partners_are_ordinary_sampling_noise(pairs):
    """
    The point of publishing the expectation: over this many draws the most frequent pair is
    a handful of appearances above chance, not a pattern. If this ever fails it is worth
    looking at, but it must never be presented to a player as a signal.
    """
    busiest = max(pairs['pair_counts'].values())
    assert busiest < pairs['expected_count_per_pair'] * 3


def test_the_bonus_ball_is_not_part_of_a_pair():
    """Pairs are over the six main numbers; the bonus is not part of the main draw."""
    draws = [
        {'date': '2026-01-01', 'numbers': [1, 2, 3, 4, 5, 6, 7]},
        {'date': '2026-01-02', 'numbers': [1, 2, 3, 4, 5, 6, 7]},
    ]
    result = analyze_number_pairs(draws)
    # 7 was only ever the bonus, so it has no partners at all.
    assert result['per_number']['7']['top_partners'] == []
    assert result['per_number']['7']['appearances'] == 0
    assert result['pair_counts']['1-2'] == 2
    assert '1-7' not in result['pair_counts']


def test_partners_are_ordered_without_depending_on_dict_order():
    """Ties break on the number, so two runs cannot differ (F-12)."""
    draws = [
        {'date': '2026-01-01', 'numbers': [1, 2, 3, 10, 20, 30, 40]},
        {'date': '2026-01-02', 'numbers': [1, 2, 3, 11, 21, 31, 41]},
    ]
    result = analyze_number_pairs(draws)
    partners = result['per_number']['1']['top_partners']
    counts = [p['count'] for p in partners]
    assert counts == sorted(counts, reverse=True)
    tied = [p['number'] for p in partners if p['count'] == counts[0]]
    assert tied == sorted(tied)


def test_the_six_ball_spread_is_written_beside_the_seven_ball_one(odds):
    """
    A six-number line can only be compared with a six-ball spread. The seven-ball figure is
    wider on every draw that the bonus falls outside the main range (F-63).
    """
    assert set(odds['draw_range_6']) == set(odds['draw_range'])

    six = {k: v['count'] for k, v in odds['draw_range_6'].items()}
    seven = {k: v['count'] for k, v in odds['draw_range'].items()}
    assert sum(six.values()) == sum(seven.values())
    # Adding a seventh ball can only widen a draw's span, never narrow it, so the six-ball
    # distribution must sit lower.
    assert six['<20'] + six['20-25'] > seven['<20'] + seven['20-25']


def test_the_six_ball_spread_matches_the_draw_history(odds):
    """The distribution is the one a six-number line is scored against, so recount it."""
    history = json.loads(
        (REPO_ROOT / 'data' / 'lotto_draw_history.json').read_text(encoding='utf-8')
    )
    widest = max(
        max(draw['main_numbers']) - min(draw['main_numbers'])
        for draw in history.values()
    )
    narrowest = min(
        max(draw['main_numbers']) - min(draw['main_numbers'])
        for draw in history.values()
    )
    bands = odds['draw_range_6']
    assert (bands['>45']['count'] > 0) == (widest > 45)
    assert (bands['<20']['count'] > 0) == (narrowest < 20)
