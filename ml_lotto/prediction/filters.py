"""
filters.py
==========
Phase 1 validation filters for lottery picks.

Implements three core filters based on Irish Lotto 6/47 historical statistics:
1. Odd/Even Balance:
   - 3 odd / 3 even: 32.03% (most common)
   - 2 odd / 4 even: 23.47%
   - 4 odd / 2 even: 23.23%
   - Valid range: 2-4 odd numbers (78.73% of historical draws)
2. Sum Constraint:
   - Valid range: 84 to 206 (captures ~95% of historical draws; mean ~144)
3. Range Distribution / Dispersion:
   - Minimum span: max(numbers) - min(numbers) >= 20 (eliminates unrealistic clusters)
"""

from typing import List, Tuple, Dict, Any


# Global flag indicating if actual filters are available
FILTERS_AVAILABLE = True

# Mathematical bounds for Irish Lotto 6/47
MIN_SUM = 84
MAX_SUM = 206
MIN_SPAN = 20
MIN_ODD = 2
MAX_ODD = 4


def validate_line(numbers: List[int]) -> Tuple[bool, List[str]]:
    """
    Validate a line of numbers against all Phase 1 filters.

    Args:
        numbers: Sorted list of 6-7 numbers

    Returns:
        Tuple of (is_valid, list_of_failures)

    Filters:
        1. Odd/Even Balance: Must have 2-4 odd numbers (optimal: 3)
        2. Sum Constraint: Sum must be between 84 and 206
        3. Range Distribution: Span (max - min) must be at least 20
    """
    failures = []
    if not numbers:
        return (False, ["empty_line"])

    # Filter 1: Odd/Even Balance
    odd_count = sum(1 for n in numbers if n % 2 == 1)
    even_count = len(numbers) - odd_count
    if odd_count < MIN_ODD or odd_count > MAX_ODD:
        failures.append(f'odd_even_balance ({odd_count} odd / {even_count} even)')

    # Filter 2: Sum Constraint Filter
    line_sum = sum(numbers[:6])
    if line_sum < MIN_SUM or line_sum > MAX_SUM:
        failures.append(f'sum_constraint (sum={line_sum}, valid: [{MIN_SUM}, {MAX_SUM}])')

    # Filter 3: Range Distribution Filter
    line_span = max(numbers[:6]) - min(numbers[:6])
    if line_span < MIN_SPAN:
        failures.append(f'range_distribution (span={line_span}, min required: {MIN_SPAN})')

    return (len(failures) == 0, failures)


def get_filter_statistics() -> Dict[str, Any]:
    """
    Get statistics about filter coverage and expected elimination rates.

    Returns:
        Dictionary with filter statistics based on historical data analysis
    """
    return {
        'odd_even_filter': {
            'description': 'Enforces 2-4 odd numbers (optimal: 3 odd / 3 even)',
            'expected_elimination': '21.27% (eliminates extreme patterns: 0-1 odd, 5-6 odd)'
        },
        'sum_constraint': {
            'description': f'Enforces sum between {MIN_SUM} and {MAX_SUM} (empirical ~95% historical range)',
            'expected_elimination': '5.2% (eliminates uncharacteristically low or high totals)'
        },
        'range_distribution': {
            'description': f'Enforces minimum span of {MIN_SPAN} across selected main balls',
            'expected_elimination': '2.8% (eliminates tight single-decade clumps)'
        },
        'combined_impact': {
            'total_elimination': '~26.5% of mathematically possible 6-number combinations eliminated'
        }
    }