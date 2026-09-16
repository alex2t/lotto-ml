"""
The freshness target must describe a 6-number line (issue F-1).

`lotto_7_number_freshness_results.json` carries two distributions: the split of all 7
drawn balls, which the dashboard reports, and the split of the 6 main balls, which is
what a generated line actually has to hit. Targeting the 7-ball one overstates demand by
one number's worth and skews which freshness bin selection prioritises.
"""

import json

import pytest

from lotto_analysis.analyzers.freshness_analyzer_7_numbers import (
    analyze_6_main_freshness,
    analyze_7_number_freshness,
    format_freshness_output,
)
from ml_lotto.prediction.constraints import LINE_SIZE, get_optimal_pattern_distribution

FRESHNESS_JSON = 'data/lotto_7_number_freshness_results.json'
C_MAX, WINDOW = 2, 5


@pytest.fixture(scope='module')
def freshness_data():
    with open(FRESHNESS_JSON, encoding='utf-8') as f:
        return json.load(f)


def bin_total(pattern, c_max=C_MAX):
    return sum(pattern[f'C{i}'] for i in range(c_max)) + pattern[f'C_GE_{c_max}']


def test_target_sums_to_the_line_size(freshness_data):
    target = get_optimal_pattern_distribution(freshness_data, freshness_data['c_max_threshold'])
    assert sum(target.values()) == LINE_SIZE == 6, (
        f"target {target} sums to {sum(target.values())}, but a line has {LINE_SIZE} slots"
    )


def test_every_main_pattern_describes_six_numbers(freshness_data):
    patterns = freshness_data['distribution_analysis_6_main']
    assert patterns, "distribution_analysis_6_main is missing - re-run drawpick.py"
    bad = [p['pattern'] for p in patterns if bin_total(p) != 6]
    assert not bad, f"main-ball patterns not summing to 6: {bad}"


def test_the_seven_ball_distribution_is_still_produced(freshness_data):
    """The dashboard and freshness_pattern_analyzer read this one; it must stay 7-wide."""
    patterns = freshness_data['distribution_analysis_7_numbers']
    assert patterns
    bad = [p['pattern'] for p in patterns if bin_total(p) != 7]
    assert not bad, f"7-ball patterns not summing to 7: {bad}"


def test_the_two_distributions_are_not_the_same(freshness_data):
    seven = {p['pattern'] for p in freshness_data['distribution_analysis_7_numbers']}
    six = {p['pattern'] for p in freshness_data['distribution_analysis_6_main']}
    assert seven and six and seven != six


def test_missing_main_distribution_raises_rather_than_silently_using_seven():
    with pytest.raises(ValueError, match='distribution_analysis_6_main'):
        get_optimal_pattern_distribution(
            {'distribution_analysis_7_numbers': [{'C0': 4, 'C1': 2, 'C_GE_2': 1}]}, C_MAX)


def test_a_target_of_the_wrong_width_raises():
    with pytest.raises(ValueError, match='sums to 7'):
        get_optimal_pattern_distribution(
            {'distribution_analysis_6_main': [
                {'pattern': 'C0=4, C1=2, C_GE_2=1', 'C0': 4, 'C1': 2, 'C_GE_2': 1}]}, C_MAX)


# --- the analyzer itself -----------------------------------------------------------

def make_draw(main_bins, bonus_bin):
    """One draw: six main balls in the given bins, plus a bonus ball."""
    key = f'last_{WINDOW - 1}'
    details = [{'number': i + 1, 'is_bonus': False, 'recent_counts': {key: b}}
               for i, b in enumerate(main_bins)]
    details.append({'number': 47, 'is_bonus': True, 'recent_counts': {key: bonus_bin}})
    return {'winning_numbers_details': details}


@pytest.fixture
def log():
    # every main ball in bin 0, bonus in bin 1 -> the two views must disagree
    return {f'2026-01-{i:02d}': make_draw([0] * 6, 1) for i in range(1, 13)}


def test_main_only_excludes_the_bonus_ball(log):
    counts, total = analyze_6_main_freshness(log, WINDOW, C_MAX)
    assert total == 12
    assert counts == {'C0=6, C1=0, C_GE_2=0': 12}, counts


def test_all_seven_includes_the_bonus_ball(log):
    counts, _ = analyze_7_number_freshness(log, WINDOW, C_MAX)
    assert counts == {'C0=6, C1=1, C_GE_2=0': 12}, counts


def test_format_output_carries_both_distributions(log):
    seven, total = analyze_7_number_freshness(log, WINDOW, C_MAX)
    six, _ = analyze_6_main_freshness(log, WINDOW, C_MAX)
    out = format_freshness_output(seven, total, WINDOW, C_MAX, main_counts=six)

    assert bin_total(out['distribution_analysis_7_numbers'][0]) == 7
    assert bin_total(out['distribution_analysis_6_main'][0]) == 6
    assert get_optimal_pattern_distribution(out, C_MAX) == {0: 6, 1: 0, 2: 0}
