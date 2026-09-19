# view/utils/anomaly_detector.py
"""
Flags where a line looks unlike past draws.

An alert describes how unusual a line's shape is. It is never a warning about its chance of winning:
every line is equally likely to win (F-28).
"""

import json
from typing import List, Dict, Tuple, Any


def load_anomaly_detection_data() -> Dict[str, Any]:
    """Load all necessary data for anomaly detection."""
    data = {}

    try:
        with open('data/lotto_trigger_periods.json', 'r') as f:
            data['trigger'] = json.load(f)
    except FileNotFoundError:
        data['trigger'] = {}

    try:
        with open('data/lotto_sum_contribution_validated.json', 'r') as f:
            data['sum'] = json.load(f)
    except FileNotFoundError:
        data['sum'] = {}

    try:
        with open('data/lotto_odd_even_validated.json', 'r') as f:
            data['odd_even'] = json.load(f)
    except FileNotFoundError:
        data['odd_even'] = {}

    try:
        with open('data/lotto_advanced_patterns.json', 'r') as f:
            data['advanced'] = json.load(f)
    except FileNotFoundError:
        data['advanced'] = {}

    try:
        with open('data/lotto_bonus_to_main_patterns.json', 'r') as f:
            data['bonus_transition'] = json.load(f)
    except FileNotFoundError:
        data['bonus_transition'] = {}

    try:
        with open('data/lotto_draw_history.json', 'r') as f:
            data['draw_history'] = json.load(f)
    except FileNotFoundError:
        data['draw_history'] = {}

    return data


class AnomalyDetector:
    """Detects anomalies in lottery number selections."""

    def __init__(self):
        self.data = load_anomaly_detection_data()
        self.alerts = []

    def detect_all_anomalies(self, numbers: List[int]) -> List[Dict[str, Any]]:
        """
        Run all anomaly detection checks on a set of numbers.
        Returns a list of alert dictionaries.
        """
        self.alerts = []

        # Run all detection methods
        self._check_sum_anomaly(numbers)
        self._check_odd_even_anomaly(numbers)
        self._check_hmc_anomaly(numbers)
        self._check_range_anomaly(numbers)
        self._check_consecutive_anomaly(numbers)
        self._check_all_cold_numbers(numbers)
        self._check_all_hot_numbers(numbers)
        self._check_cooling_down_numbers(numbers)
        self._check_extreme_volatility(numbers)
        self._check_duplicate_recent_pattern(numbers)
        self._check_all_same_parity_range(numbers)

        return self.alerts

    def _add_alert(self, severity: str, category: str, message: str, details: str = ""):
        """Add an alert to the list."""
        self.alerts.append({
            'severity': severity,  # 'critical', 'warning', 'info'
            'category': category,
            'message': message,
            'details': details
        })

    def _check_sum_anomaly(self, numbers: List[int]):
        """Check if sum is extremely unusual."""
        total_sum = sum(numbers)
        sum_data = self.data.get('sum', {})
        summary_stats = sum_data.get('summary_statistics', {})

        sum_mean = summary_stats.get('mean', 144.87)
        sum_std = summary_stats.get('std', 30.4)

        # Critical: Beyond 3 standard deviations
        if total_sum < sum_mean - 3 * sum_std or total_sum > sum_mean + 3 * sum_std:
            self._add_alert(
                'critical',
                'Sum Analysis',
                f'Extreme sum detected: {total_sum}',
                f'This sum is more than 3 standard deviations from the mean ({sum_mean:.1f}). '
                f'Very few past draws had a sum outside {sum_mean - 3*sum_std:.0f} - {sum_mean + 3*sum_std:.0f}.'
            )
        # Warning: Beyond 2.5 standard deviations
        elif total_sum < sum_mean - 2.5 * sum_std or total_sum > sum_mean + 2.5 * sum_std:
            self._add_alert(
                'warning',
                'Sum Analysis',
                f'Unusual sum: {total_sum}',
                f'This sum is more than 2.5 standard deviations from the mean ({sum_mean:.1f}). '
                f'Few past draws had a sum this far out.'
            )

    def _check_odd_even_anomaly(self, numbers: List[int]):
        """Check for extreme odd/even imbalance."""
        odd_count = sum(1 for n in numbers if n % 2 == 1)
        even_count = 6 - odd_count

        # Critical: All odd or all even (extremely rare)
        if odd_count == 0 or odd_count == 6:
            self._add_alert(
                'critical',
                'Odd/Even Balance',
                f'All {"even" if odd_count == 0 else "odd"} numbers!',
                f'Few past draws were all odd or all even; most had 2-4 odd numbers.'
            )
        # Warning: 5-1 or 1-5 split
        elif odd_count == 1 or odd_count == 5:
            self._add_alert(
                'warning',
                'Odd/Even Balance',
                f'Severe odd/even imbalance: {odd_count} odd, {even_count} even',
                f'Less common in past draws than 2-4 odd numbers.'
            )

    def _check_hmc_anomaly(self, numbers: List[int]):
        """Check for unusual HMC distribution."""
        trigger_data = self.data.get('trigger', {})

        hot_count = sum(1 for n in numbers if trigger_data.get(str(n), {}).get('category') == 'hot')
        medium_count = sum(1 for n in numbers if trigger_data.get(str(n), {}).get('category') == 'medium')
        cold_count = sum(1 for n in numbers if trigger_data.get(str(n), {}).get('category') == 'cold')

        # Critical: All from one category
        if hot_count == 6 or cold_count == 6:
            category_name = 'hot' if hot_count == 6 else 'cold'
            self._add_alert(
                'critical',
                'HMC Distribution',
                f'All 6 numbers are {category_name.upper()}!',
                f'Few past draws had all six numbers in one category; most mixed hot, medium and cold.'
            )
        # Warning: 5 from one category
        elif hot_count == 5 or cold_count == 5:
            category_name = 'hot' if hot_count == 5 else 'cold'
            self._add_alert(
                'warning',
                'HMC Distribution',
                f'5 out of 6 numbers are {category_name.upper()}',
                f'Five numbers in one category is uncommon in past draws.'
            )

    def _check_range_anomaly(self, numbers: List[int]):
        """Check for poor range distribution."""
        ranges = {
            "1-10": sum(1 for n in numbers if 1 <= n <= 10),
            "11-20": sum(1 for n in numbers if 11 <= n <= 20),
            "21-30": sum(1 for n in numbers if 21 <= n <= 30),
            "31-40": sum(1 for n in numbers if 31 <= n <= 40),
            "41-47": sum(1 for n in numbers if 41 <= n <= 47),
        }

        empty_ranges = [r for r, count in ranges.items() if count == 0]
        max_in_one_range = max(ranges.values())

        # Critical: All numbers in 2 or fewer ranges
        covered_ranges = sum(1 for count in ranges.values() if count > 0)
        if covered_ranges <= 2:
            self._add_alert(
                'critical',
                'Range Distribution',
                f'All numbers concentrated in only {covered_ranges} range(s)!',
                f'Past draws typically spread across 4-5 number ranges. '
                f'Current distribution: {", ".join(f"{r}: {c}" for r, c in ranges.items() if c > 0)}'
            )
        # Warning: 4+ numbers in one range
        elif max_in_one_range >= 4:
            max_range = [r for r, c in ranges.items() if c == max_in_one_range][0]
            self._add_alert(
                'warning',
                'Range Distribution',
                f'{max_in_one_range} numbers in range {max_range}',
                f'Past draws typically have at most 3 numbers in one range.'
            )

    def _check_consecutive_anomaly(self, numbers: List[int]):
        """Check for unusual consecutive number patterns."""
        sorted_nums = sorted(numbers)
        consecutive_runs = []
        current_run = [sorted_nums[0]]

        for i in range(1, len(sorted_nums)):
            if sorted_nums[i] == sorted_nums[i-1] + 1:
                current_run.append(sorted_nums[i])
            else:
                if len(current_run) >= 2:
                    consecutive_runs.append(current_run.copy())
                current_run = [sorted_nums[i]]

        if len(current_run) >= 2:
            consecutive_runs.append(current_run)

        # Critical: 4+ consecutive numbers
        max_consecutive = max([len(run) for run in consecutive_runs], default=0)
        if max_consecutive >= 4:
            run = [r for r in consecutive_runs if len(r) == max_consecutive][0]
            self._add_alert(
                'critical',
                'Consecutive Numbers',
                f'{max_consecutive} consecutive numbers: {", ".join(str(n) for n in run)}',
                f'A run of {max_consecutive} consecutive numbers is rare in past draws; '
                f'most have at most 2.'
            )

    def _check_all_cold_numbers(self, numbers: List[int]):
        """Check if all numbers are cold."""
        trigger_data = self.data.get('trigger', {})
        cold_count = sum(1 for n in numbers if trigger_data.get(str(n), {}).get('category') == 'cold')

        if cold_count == 6:
            self._add_alert(
                'critical',
                'Temperature Analysis',
                'All 6 numbers are COLD!',
                'Past draws rarely had all six numbers cold.'
            )

    def _check_all_hot_numbers(self, numbers: List[int]):
        """Check if all numbers are hot."""
        trigger_data = self.data.get('trigger', {})
        hot_count = sum(1 for n in numbers if trigger_data.get(str(n), {}).get('category') == 'hot')

        if hot_count == 6:
            self._add_alert(
                'warning',
                'Temperature Analysis',
                'All 6 numbers are HOT!',
                'Few past draws had all six numbers hot.'
            )

    def _check_cooling_down_numbers(self, numbers: List[int]):
        """Check if multiple numbers are cooling down."""
        advanced_data = self.data.get('advanced', {})
        per_number = advanced_data.get('per_number_features', {})

        cooling_count = sum(
            1 for n in numbers
            if per_number.get(str(n), {}).get('recent_vs_baseline', 1.0) < 0.8
        )

        if cooling_count >= 4:
            self._add_alert(
                'warning',
                'Momentum Analysis',
                f'{cooling_count} numbers are cooling down',
                'These numbers have come up less often recently than over their whole history. '
                'That does not change their chance in the next draw.'
            )

    def _check_extreme_volatility(self, numbers: List[int]):
        """Check if too many high-volatility numbers."""
        advanced_data = self.data.get('advanced', {})
        per_number = advanced_data.get('per_number_features', {})

        high_volatility_count = sum(
            1 for n in numbers
            if per_number.get(str(n), {}).get('appearance_volatility', 1.0) >= 1.5
        )

        if high_volatility_count >= 4:
            self._add_alert(
                'info',
                'Volatility Analysis',
                f'{high_volatility_count} highly volatile numbers detected',
                'These numbers have come up at irregular intervals in the past. '
                'That does not change their chance in the next draw.'
            )

    def _check_duplicate_recent_pattern(self, numbers: List[int]):
        """Check if this exact pattern appeared very recently."""
        draw_history = self.data.get('draw_history', {})
        sorted_selection = sorted(numbers)

        recent_draws = sorted(draw_history.items(), reverse=True)[:20]  # Last 20 draws

        for date, draw_data in recent_draws:
            main_numbers = sorted(draw_data['main_numbers'])
            if main_numbers == sorted_selection:
                self._add_alert(
                    'critical',
                    'Pattern Repetition',
                    f'Exact same numbers drawn on {date}!',
                    'This exact line was drawn recently. It is exactly as likely to be drawn again '
                    'as any other line.'
                )
                return

    def _check_all_same_parity_range(self, numbers: List[int]):
        """Check if all numbers fall in similar parity ranges."""
        # Check if all numbers are in same decade
        decades = [n // 10 for n in numbers]
        unique_decades = len(set(decades))

        if unique_decades <= 2:
            self._add_alert(
                'warning',
                'Number Distribution',
                f'All numbers fall in only {unique_decades} decade(s)',
                f'Numbers are clustered in decades: {", ".join(f"{d}0s" for d in sorted(set(decades)))}. '
                'Past draws usually cover more decades.'
            )

    def get_alert_summary(self) -> Dict[str, int]:
        """Get summary counts of alerts by severity."""
        return {
            'critical': sum(1 for a in self.alerts if a['severity'] == 'critical'),
            'warning': sum(1 for a in self.alerts if a['severity'] == 'warning'),
            'info': sum(1 for a in self.alerts if a['severity'] == 'info')
        }


def detect_anomalies(numbers: List[int]) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Convenience function to detect anomalies in a number selection.

    Args:
        numbers: List of 6 lottery numbers

    Returns:
        Tuple of (alerts_list, summary_dict)
    """
    detector = AnomalyDetector()
    alerts = detector.detect_all_anomalies(numbers)
    summary = detector.get_alert_summary()
    return alerts, summary
