"""
The anomaly checks read real draw statistics, and every check can fire (F-29).

The sum alerts and Pattern Comparison's typical range read `summary_statistics`, a key
`lotto_sum_contribution_validated.json` never had, so `.get` defaults put hard-coded 144.87 / 30.4 in
place of the real mean and standard deviation. The volatility alert needed 4 numbers at >= 1.5 while
no number has ever reached 1.2, so it could never fire; it was removed.
"""

import json

import pytest
from streamlit.testing.v1 import AppTest

from view.utils.anomaly_detector import AnomalyDetector

SUM_237 = [12, 43, 44, 45, 46, 47]
SUM_207 = [12, 13, 44, 45, 46, 47]


@pytest.fixture(scope='module')
def sums():
    with open('data/lotto_sum_contribution_validated.json', encoding='utf-8') as f:
        return json.load(f)['overall_distribution']


def sum_alerts(line):
    return [a for a in AnomalyDetector().detect_all_anomalies(line) if a['category'] == 'Sum Analysis']


def test_sum_alert_quotes_the_mean_of_past_draws(sums):
    alerts = sum_alerts(SUM_237)
    assert len(alerts) == 1
    assert f"({sums['mean']:.1f})" in alerts[0]['details']


def test_sum_alert_severity_follows_the_real_bands(sums):
    """237 is past 3 SD of the hard-coded figures (236.1) but not of the real ones (238.1)."""
    upper3 = sums['mean'] + 3 * sums['std']
    upper25 = sums['mean'] + 2.5 * sums['std']
    assert upper25 < sum(SUM_237) < upper3
    assert sum_alerts(SUM_237)[0]['severity'] == 'warning'


def test_pattern_comparison_typical_range_comes_from_past_draws(sums):
    """207 was outside the hard-coded typical range (84-206) and is inside the real one."""
    low, high = sums['mean'] - 2 * sums['std'], sums['mean'] + 2 * sums['std']
    assert low <= sum(SUM_207) <= high
    at = AppTest.from_string("from view.pages import pattern_comparison; pattern_comparison.show()",
                             default_timeout=60)
    at.run()
    at.text_input[0].input(', '.join(map(str, SUM_207))).run()
    assert not at.exception
    text = ' '.join(m.value for m in at.markdown)
    assert f"is within the typical range ({low:.0f}-{high:.0f})" in text


def lines_for_every_check():
    """Lines chosen from the current data so that, between them, each check has a reason to fire."""
    with open('data/lotto_trigger_periods.json', encoding='utf-8') as f:
        trigger = json.load(f)
    with open('data/lotto_advanced_patterns.json', encoding='utf-8') as f:
        per_number = json.load(f)['per_number_features']
    with open('data/lotto_draw_history.json', encoding='utf-8') as f:
        history = json.load(f)
    cold = sorted(int(n) for n, v in trigger.items() if v['category'] == 'cold')[:6]
    cooling = sorted(int(n) for n, v in per_number.items() if v['recent_vs_baseline'] < 0.8)[:6]
    return [[1, 2, 3, 4, 5, 6], [1, 3, 5, 7, 9, 11], cold, cooling, history[max(history)]['main_numbers']]


def test_every_check_can_fire_on_the_current_data():
    """A check whose condition no line can meet is dead code that looks like a safeguard."""
    detector = AnomalyDetector()
    checks = [name for name in dir(detector) if name.startswith('_check_')]
    for name in checks:
        fired = False
        for line in lines_for_every_check():
            detector.alerts = []
            getattr(detector, name)(line)
            fired = fired or bool(detector.alerts)
        assert fired, name
