"""
The draw history carries each draw's numbers where the website reads them (F-25).

The site reads `main_numbers` and `bonus_number` from `data/lotto_draw_history.json`. The file
once lacked them, and an empty default turned that into "no similar draws" for every line.

A past draw's hot/medium/cold pattern must use the categories in force before that draw, not the
latest ones (F-27). Numbers just drawn are hot today, so the latest categories made recent draws
look all-hot.
"""

import json
from pathlib import Path

import pytest

DRAW_HISTORY = 'data/lotto_draw_history.json'
CATEGORIES = ('hot', 'medium', 'cold')


@pytest.fixture(scope='module')
def history():
    with open(DRAW_HISTORY, encoding='utf-8') as f:
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


def test_each_drawn_number_has_exactly_one_pre_draw_category(history):
    """The pre-draw lists partition the numbers, so a draw's HMC pattern sums to 6 (F-27)."""
    for date, draw in history.items():
        cats = draw['categories_pre_draw']
        for n in draw['main_numbers']:
            assert sum(n in cats[f'{c}_numbers'] for c in CATEGORIES) == 1, (date, n)


def test_each_ball_is_labelled_with_its_pre_draw_category(history):
    """A ball's `category` is the one in force before its draw, not today's (F-27)."""
    for date, draw in history.items():
        cats = draw['categories_pre_draw']
        for d in draw['winning_numbers_details']:
            expected = next(c for c in CATEGORIES if d['number'] in cats[f'{c}_numbers'])
            assert d['category'] == expected, (date, d['number'])


def test_no_frontend_module_reads_the_draw_csv():
    """
    The site reads data/*.json only; the CSV is drawpick.py's input (F-35). One documented
    exception: the admin download route, where the owner retrieves their own input file.
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
