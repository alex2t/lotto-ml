"""
The draw history carries each draw's numbers where the website reads them (F-25).

`view/pages/pattern_comparison.py` and `view/utils/anomaly_detector.py` read `main_numbers` and
`bonus_number` from `data/lotto_draw_history.json`. The file never had them, and `.get(key, [])`
turned that into an empty list, so Pattern Comparison found no match for any line - even a real
past draw - and the repeat alert could never fire.
"""

import json

import pytest

from view.pages.pattern_comparison import (
    find_similar_draws,
    get_hmc_pattern,
    get_odd_even_pattern,
    get_range_pattern,
    has_consecutive_numbers,
)

DRAW_HISTORY = 'data/lotto_draw_history.json'
TRIGGER_PERIODS = 'data/lotto_trigger_periods.json'


@pytest.fixture(scope='module')
def history():
    with open(DRAW_HISTORY, encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def trigger_data():
    with open(TRIGGER_PERIODS, encoding='utf-8') as f:
        return json.load(f)


def test_every_draw_has_six_main_numbers_and_a_bonus(history):
    for date, draw in history.items():
        main, bonus = draw['main_numbers'], draw['bonus_number']
        assert len(main) == 6 and len(set(main)) == 6, date
        assert all(1 <= n <= 47 for n in main), date
        assert 1 <= bonus <= 47 and bonus not in main, date


def test_numbers_agree_with_the_winning_number_details(history):
    for date, draw in history.items():
        details = draw['winning_numbers_details']
        assert draw['main_numbers'] == [d['number'] for d in details if not d['is_bonus']], date
        assert draw['bonus_number'] == next(d['number'] for d in details if d['is_bonus']), date


def pattern_of(numbers, trigger_data):
    return {
        'hmc': get_hmc_pattern(numbers, trigger_data),
        'odd_even': get_odd_even_pattern(numbers),
        'sum': sum(numbers),
        'range_dist': get_range_pattern(numbers),
        'has_consecutive': has_consecutive_numbers(numbers)[0],
    }


@pytest.mark.parametrize('pick', ['latest', 'earliest'])
def test_pattern_comparison_finds_a_past_draw_among_its_best_matches(history, trigger_data, pick):
    """A line that was actually drawn must come back with the top similarity score."""
    dates = sorted(history)
    date = dates[-1] if pick == 'latest' else dates[0]
    numbers = history[date]['main_numbers']

    matches = find_similar_draws(pattern_of(numbers, trigger_data), history, trigger_data,
                                 top_n=len(history))

    assert matches, "no historical draw matched at all"
    best = matches[0]['similarity']
    own = next(m for m in matches if m['date'] == date)
    assert own['similarity'] == best
    assert own['numbers'] == numbers and own['bonus'] == history[date]['bonus_number']
