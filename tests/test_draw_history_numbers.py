"""
The draw history carries each draw's numbers where the website reads them (F-25).

`view/pages/pattern_comparison.py` and `view/utils/anomaly_detector.py` read `main_numbers` and
`bonus_number` from `data/lotto_draw_history.json`. The file never had them, and `.get(key, [])`
turned that into an empty list, so Pattern Comparison found no match for any line - even a real
past draw - and the repeat alert could never fire.

A past draw's hot/medium/cold pattern must use the categories in force before that draw, not the
latest ones (F-27). Numbers just drawn are hot today, so the latest categories made recent draws
look all-hot.
"""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from view.pages.pattern_comparison import (
    find_similar_draws,
    get_draw_hmc_pattern,
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


def pattern_of(numbers, hmc):
    return {
        'hmc': hmc,
        'odd_even': get_odd_even_pattern(numbers),
        'sum': sum(numbers),
        'range_dist': get_range_pattern(numbers),
        'has_consecutive': has_consecutive_numbers(numbers)[0],
    }


def pre_draw_pattern(draw):
    """HMC of the main 6, counted from the draw's `categories_pre_draw` lists."""
    cats = draw['categories_pre_draw']
    return tuple(sum(n in cats[f'{c}_numbers'] for n in draw['main_numbers'])
                 for c in ('hot', 'medium', 'cold'))


@pytest.mark.parametrize('pick', ['latest', 'earliest'])
def test_pattern_comparison_finds_a_past_draw_as_its_exact_match(history, pick):
    """A drawn line with that draw's own pattern must come back at 100% similarity."""
    dates = sorted(history)
    date = dates[-1] if pick == 'latest' else dates[0]
    draw = history[date]
    numbers = draw['main_numbers']

    matches = find_similar_draws(pattern_of(numbers, pre_draw_pattern(draw)), history,
                                 top_n=len(history))

    own = next(m for m in matches if m['date'] == date)
    assert own['similarity'] == 100
    assert matches[0]['similarity'] == 100
    assert own['numbers'] == numbers and own['bonus'] == draw['bonus_number']


def test_past_draws_are_classified_with_their_pre_draw_categories(history):
    """Every historical match carries the HMC in force before its draw, main 6 only (F-27)."""
    matches = find_similar_draws(pattern_of([1, 2, 3, 4, 5, 6], (2, 2, 2)), history,
                                 top_n=len(history))
    assert len(matches) == len(history)
    for m in matches:
        assert m['pattern']['hmc'] == pre_draw_pattern(history[m['date']]), m['date']
        assert sum(m['pattern']['hmc']) == 6, m['date']


def test_recent_draws_are_not_all_hot(history, trigger_data):
    """The latest categories make the latest draw all-hot; its pre-draw pattern need not be."""
    latest = history[max(history)]
    assert get_hmc_pattern(latest['main_numbers'], trigger_data) == (6, 0, 0)
    assert get_draw_hmc_pattern(latest) == pre_draw_pattern(latest)


def test_player_line_with_an_unknown_number_raises(trigger_data):
    """A number missing from the categories is a bug, not a medium (F-27)."""
    with pytest.raises(KeyError):
        get_hmc_pattern([1, 2, 3, 4, 5, 99], trigger_data)


def test_post_draw_autofill_uses_the_latest_draw_in_the_draw_history(history):
    """Post Draw Analysis autofills the newest draw in lotto_draw_history.json (F-35)."""
    latest = history[max(history, key=lambda d: history[d]['draw_index'])]
    at = AppTest.from_string("from view.pages import post_draw_analysis; post_draw_analysis.show()",
                             default_timeout=60)
    at.run()
    next(b for b in at.button if b.label.startswith('📥 Autofill')).click().run()
    assert not at.exception
    assert at.text_input(key='input_main_numbers').value == ', '.join(map(str, sorted(latest['main_numbers'])))
    assert at.text_input(key='input_bonus_number').value == str(latest['bonus_number'])


def test_no_website_module_reads_the_draw_csv():
    """
    The website reads data/*.json only; the CSV is drawpick.py's input (F-35).

    Regression: Post Draw Analysis parsed data/irish500.csv itself to find the latest draw.
    """
    readers = [str(p) for p in Path('view').rglob('*.py') if 'irish500' in p.read_text(encoding='utf-8')]
    assert not readers, f"website modules reading the CSV: {readers}"


def test_no_frontend_module_reads_the_draw_csv():
    """
    The same rule for the Next.js site, with one documented exception: the admin download
    route, where the owner retrieves their own input file (nextStep/web.md 3.3).
    """
    allowed = {Path('frontend/app/api/download/data/route.ts')}
    sources = [
        p
        for pattern in ('*.ts', '*.tsx')
        for p in Path('frontend').rglob(pattern)
        if 'node_modules' not in p.parts and '.next' not in p.parts and 'test' not in p.parts
    ]
    readers = [str(p) for p in sources if 'irish500' in p.read_text(encoding='utf-8') and p not in allowed]
    assert not readers, f"frontend modules reading the CSV: {readers}"
