"""
The scraper must accept only the main Lotto draw, and must not trust one source alone.

Both result pages carry Lotto Plus 1 and Plus 2 alongside the main draw, sharing its
date. Deduplication is by date, so whichever game parsed first used to win and nothing
checked which game it was (C-14).

Fixtures in `tests/fixtures/` are verbatim markup captured from the two live pages on
2026-09-17; the Plus variants below are produced by editing that real markup, not by
inventing a shape the sites do not use.
"""

from datetime import datetime
from pathlib import Path

import pytest

from scripts.scrape_lotto import (
    build_draw,
    cross_check,
    parse_archive_table,
    parse_lottery_ie,
)

FIXTURES = Path(__file__).parent / 'fixtures'
ARCHIVE = (FIXTURES / 'archive_rows.html').read_text(encoding='utf-8')
LOTTERY_IE = (FIXTURES / 'lottery_ie_section.html').read_text(encoding='utf-8')

# The draw each fixture's first section describes, confirmed against both sources
FIRST_ARCHIVE_DRAW = ('16 Sep 2026', [4, 7, 19, 20, 35, 42], 31)
LOTTERY_IE_DRAW = ('14 Sep 2026', [9, 14, 20, 22, 26, 29], 4)


def test_archive_rows_parse_to_main_draws():
    draws = parse_archive_table(ARCHIVE)

    assert len(draws) == 3
    date_str, main, bonus = FIRST_ARCHIVE_DRAW
    assert draws[0]['date_str'] == date_str
    assert sorted(draws[0]['main']) == main
    assert draws[0]['bonus'] == bonus


def test_archive_rejects_a_plus_row_sharing_the_draw_date():
    """A Plus row carries the same date but 'irish-lotto-plus-1' on its balls."""
    plus_only = ARCHIVE.replace('irish-lotto ball', 'irish-lotto-plus-1 ball')

    assert parse_archive_table(plus_only) == []


def test_archive_skips_a_row_holding_two_games():
    """With two ball lists in one row, the date link cannot say which game is which."""
    doubled = ARCHIVE.replace('</ul>', '</ul><ul class="balls">'
                                        '<li class="result medium irish-lotto ball dark ball">1</li>'
                                        '</ul>', 1)
    draws = parse_archive_table(doubled)

    assert len(draws) == 2  # the ambiguous row is dropped, the other two survive
    assert FIRST_ARCHIVE_DRAW[0] not in [d['date_str'] for d in draws]


def test_lottery_ie_takes_the_main_draw_not_plus_1():
    """The section holds three games in order; only the first is the Lotto draw."""
    draws = parse_lottery_ie(LOTTERY_IE)

    assert len(draws) == 1
    date_str, main, bonus = LOTTERY_IE_DRAW
    assert draws[0]['date_str'] == date_str
    assert sorted(draws[0]['main']) == main
    assert draws[0]['bonus'] == bonus


def test_lottery_ie_skips_a_section_whose_games_are_reordered():
    """If a Plus marker precedes the first block, the main draw is no longer first."""
    reordered = LOTTERY_IE.replace('<h2 aria-label="Draw, Monday, September 14th, 2026"',
                                   '<h2 aria-label="Draw, Monday, September 14th, 2026">'
                                   '<span>Lotto Plus 1</span></h2><h2 hidden', 1)

    assert parse_lottery_ie(reordered) == []


def test_cross_check_flags_sources_that_disagree():
    truth = parse_archive_table(ARCHIVE)
    tampered = [dict(d) for d in truth]
    tampered[0] = {**tampered[0], 'main': [1, 2, 3, 4, 5, 6]}

    agreed, mismatches = cross_check(truth, tampered)

    assert agreed == 2
    assert len(mismatches) == 1
    assert FIRST_ARCHIVE_DRAW[0] in mismatches[0]


def test_cross_check_ignores_dates_only_one_source_has():
    """The fallback page carries only the most recent draws; that is not a mismatch."""
    draws = parse_archive_table(ARCHIVE)

    agreed, mismatches = cross_check(draws, draws[:1])

    assert agreed == 1
    assert mismatches == []


@pytest.mark.parametrize('main,bonus', [
    ([1, 2, 3, 4, 5], [6]),           # five main balls
    ([1, 2, 3, 4, 5, 6], []),         # no bonus
    ([1, 2, 3, 4, 5, 48], [6]),       # out of range
    ([1, 2, 3, 4, 5, 6], [6]),        # bonus duplicates a main ball
])
def test_malformed_draws_are_rejected(main, bonus):
    assert build_draw(datetime(2026, 9, 16), main, bonus) is None
