"""
The website describes how typical a line looks, never how likely it is to win (F-26, F-28).

Every line in a fair draw is equally likely to win. The Prediction Validator told a high scorer to
"Play with confidence" (F-26); Pattern Comparison graded lines STRONG / WEAK, Trigger Periods gave a
"Validation Confidence", and the anomaly alerts called lines risky, advised "diversification" and
quoted false frequencies (F-28). Pages are rendered with real input through Streamlit's AppTest.
"""

import json

import pytest
from streamlit.testing.v1 import AppTest

from view.utils.anomaly_detector import detect_anomalies

ADVICE = ['play with confidence', 'recommended', 'regenerate', 'risk', 'improvement',
          'statistically sound', 'excellent', 'poor', 'strong', 'weak', 'realistic', 'confidence',
          'consider', 'success rate', 'astronomically', 'diversif']
EQUAL_CHANCE = 'equally likely to win'

TYPICAL_LINE = '5, 12, 23, 31, 38, 44'
UNUSUAL_LINE = '1, 2, 3, 4, 5, 6'


def page_text(at):
    """Every piece of text the rendered page shows, lower-cased."""
    parts = [e.value for kind in ('title', 'header', 'subheader', 'markdown', 'caption',
                                  'success', 'info', 'warning', 'error')
             for e in getattr(at, kind)]
    parts += [f"{m.label} {m.value} {m.delta}" for m in at.metric]
    return ' '.join(str(p) for p in parts).lower()


PAGE_TEMPLATE = "from view.pages import {page}; {page}.show()"


def render(page, line=None, sidebar=False):
    at = AppTest.from_string(PAGE_TEMPLATE.format(page=page), default_timeout=60)
    at.run()
    if line:
        box = at.sidebar.text_input[0] if sidebar else at.text_input[0]
        box.input(line).run()
    assert not at.exception
    return at


def assert_no_advice(text):
    for phrase in ADVICE:
        assert phrase not in text, phrase


def final_score(at):
    return int(next(m.value for m in at.metric if m.label == 'Final Score').split('/')[0])


@pytest.mark.parametrize('line, band', [(TYPICAL_LINE, 'high'), (UNUSUAL_LINE, 'low')])
def test_validator_verdict_describes_typicality_not_a_chance_of_winning(line, band):
    at = render('prediction_validator', line)
    score = final_score(at)
    assert score >= 80 if band == 'high' else score < 60
    text = page_text(at)
    assert_no_advice(text)
    assert EQUAL_CHANCE in text
    assert 'typical of past draws' in text if band == 'high' else 'unusual next to past draws' in text


def test_validator_grade_legend_gives_no_advice_to_play_or_regenerate():
    text = page_text(render('prediction_validator'))
    assert 'overall score' in text
    assert_no_advice(text)
    assert EQUAL_CHANCE in text


SHAPE_VERDICTS = ['very typical shape', 'typical shape', 'less typical shape', 'unusual shape']


@pytest.mark.parametrize('line', [TYPICAL_LINE, UNUSUAL_LINE])
def test_pattern_comparison_grades_the_shape_not_the_line(line):
    text = page_text(render('pattern_comparison', line))
    assert any(f"**{v}** (score" in text for v in SHAPE_VERDICTS)
    assert_no_advice(text)
    assert EQUAL_CHANCE in text


@pytest.mark.parametrize('line, verdict', [(TYPICAL_LINE, 'typical sum'), (UNUSUAL_LINE, 'sum never seen before')])
def test_trigger_periods_sum_check_gives_no_confidence_verdict(line, verdict):
    text = page_text(render('trigger_analysis', line, sidebar=True))
    assert verdict in text
    assert_no_advice(text)
    assert EQUAL_CHANCE in text


NUMBER_ADVICE = ADVICE + ['overdue', 'pick', 'avoid', 'candidate', 'is due', 'likely to appear',
                          'high-probability', 'strategy', 'indicator']


def latest_bonus_ball():
    with open('data/lotto_draw_history.json', encoding='utf-8') as f:
        history = json.load(f)
    return history[max(history)]['bonus_number']


def longest_gap_number():
    """The number whose last appearance is furthest back - the one the old page called OVERDUE."""
    with open('data/lotto_draw_history.json', encoding='utf-8') as f:
        history = json.load(f)
    last_seen = {}
    for date in sorted(history):
        for d in history[date]['winning_numbers_details']:
            last_seen[d['number']] = date
    return min(last_seen, key=last_seen.get)


@pytest.mark.parametrize('pick', ['latest_bonus', 'longest_gap'])
def test_number_insights_is_a_profile_without_a_verdict(pick):
    """F-30: no STRONG PICK / AVOID score, no "overdue", no "strong candidate"."""
    number = latest_bonus_ball() if pick == 'latest_bonus' else longest_gap_number()
    at = AppTest.from_string(PAGE_TEMPLATE.format(page='number_insights'), default_timeout=60)
    at.run()
    at.number_input[0].set_value(number).run()
    assert not at.exception
    text = page_text(at)
    assert 'profile' in text
    for phrase in NUMBER_ADVICE:
        assert phrase not in text, phrase
    assert '6 in 47' in text
    assert 'does not make a number due' in text


def test_draw_history_shows_the_transition_rate_next_to_chance():
    """F-30: the bonus-to-main rate is shown with the fair-draw rate from the artifact, no tip."""
    with open('data/lotto_bonus_to_main_patterns.json', encoding='utf-8') as f:
        chance = json.load(f)['transition_prediction_factors']['expected_random_rate']
    at = render('draw_history')
    text = page_text(at)
    assert f"{chance*100:.1f}%" in text
    assert 'no likelier than any other number' in text
    for phrase in NUMBER_ADVICE:
        assert phrase not in text, phrase


def alert_lines():
    """Lines that between them fire every alert that can fire on the current data."""
    with open('data/lotto_trigger_periods.json', encoding='utf-8') as f:
        trigger = json.load(f)
    with open('data/lotto_advanced_patterns.json', encoding='utf-8') as f:
        per_number = json.load(f)['per_number_features']
    with open('data/lotto_draw_history.json', encoding='utf-8') as f:
        history = json.load(f)
    cold = sorted(int(n) for n, v in trigger.items() if v['category'] == 'cold')[:6]
    cooling = sorted(int(n) for n, v in per_number.items() if v['recent_vs_baseline'] < 0.8)[:6]
    return [[1, 2, 3, 4, 5, 6], [1, 3, 5, 7, 9, 11], [1, 3, 5, 7, 9, 12],
            cold, cooling, history[max(history)]['main_numbers']]


def test_anomaly_alerts_describe_the_line_without_advice():
    alerts = [a for line in alert_lines() for a in detect_anomalies(line)[0]]
    fired = {a['category'] for a in alerts}
    assert fired >= {'Sum Analysis', 'Odd/Even Balance', 'HMC Distribution', 'Range Distribution',
                     'Consecutive Numbers', 'Temperature Analysis', 'Momentum Analysis',
                     'Pattern Repetition', 'Number Distribution'}
    for a in alerts:
        assert_no_advice(f"{a['message']} {a['details']}".lower())


def test_odd_even_alerts_quote_no_frequency():
    """The old alerts quoted '<0.5%' and '~5%' for shares that are really ~2% and ~19%."""
    alerts = [a for line in ([1, 3, 5, 7, 9, 11], [1, 3, 5, 7, 9, 12]) for a in detect_anomalies(line)[0]
              if a['category'] == 'Odd/Even Balance']
    assert len(alerts) == 2
    for a in alerts:
        assert '%' not in a['details']


def test_repeat_alert_says_a_repeat_is_as_likely_as_any_line():
    with open('data/lotto_draw_history.json', encoding='utf-8') as f:
        history = json.load(f)
    alerts = detect_anomalies(history[max(history)]['main_numbers'])[0]
    repeat = next(a for a in alerts if a['category'] == 'Pattern Repetition')
    assert 'as likely' in repeat['details']
