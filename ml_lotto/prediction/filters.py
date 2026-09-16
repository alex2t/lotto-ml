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
import numpy as np


# Global flag indicating if actual filters are available
FILTERS_AVAILABLE = True

# Mathematical bounds for Irish Lotto 6/47
MIN_SUM = 84
MAX_SUM = 206
MIN_SPAN = 20


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
    if odd_count < 2 or odd_count > 4:
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


def rebalance_line(
    numbers: List[int],
    probabilities: Any,  # numpy array
    features_dict: Dict[int, Dict[str, Any]],
    max_iterations: int = 5
) -> List[int]:
    """
    Attempt to fix a line that failed validation filters.

    Strategy:
        1. Correct odd/even balance to 2-4 odds (target: 3)
        2. Correct sum constraint violations by swapping same-parity candidates
        3. Correct range span violations by widening extremes

    Args:
        numbers: Original line that failed validation
        probabilities: Model probability scores for all numbers (1-47)
        features_dict: Feature data for making intelligent swaps
        max_iterations: Maximum rebalancing attempts

    Returns:
        Rebalanced line (may still fail validation if unfixable)
    """
    numbers = list(numbers)

    for iteration in range(max_iterations):
        is_valid, failures = validate_line(numbers)
        if is_valid:
            return sorted(numbers)

        # 1. Address Odd/Even failures first
        odd_count = sum(1 for n in numbers if n % 2 == 1)
        if odd_count < 2:
            evens_in_line = sorted([(probabilities[n-1], n) for n in numbers if n % 2 == 0])
            odds_available = sorted(
                [(probabilities[n-1], n) for n in range(1, len(probabilities)+1)
                 if n % 2 == 1 and n not in numbers],
                reverse=True
            )
            if evens_in_line and odds_available:
                numbers.remove(evens_in_line[0][1])
                numbers.append(odds_available[0][1])
                continue

        elif odd_count > 4:
            odds_in_line = sorted([(probabilities[n-1], n) for n in numbers if n % 2 == 1])
            evens_available = sorted(
                [(probabilities[n-1], n) for n in range(1, len(probabilities)+1)
                 if n % 2 == 0 and n not in numbers],
                reverse=True
            )
            if odds_in_line and evens_available:
                numbers.remove(odds_in_line[0][1])
                numbers.append(evens_available[0][1])
                continue

        # 2. Address Sum Constraint failures
        line_sum = sum(numbers[:6])
        if line_sum < MIN_SUM:
            # Too low: swap lowest-prob small number with a higher number of the same parity
            low_candidates = sorted([(probabilities[n-1], n) for n in numbers if n <= 20])
            if low_candidates:
                _, num_to_remove = low_candidates[0]
                parity = num_to_remove % 2
                high_available = sorted(
                    [(probabilities[n-1], n) for n in range(25, len(probabilities)+1)
                     if n % 2 == parity and n not in numbers],
                    reverse=True
                )
                if high_available:
                    numbers.remove(num_to_remove)
                    numbers.append(high_available[0][1])
                    continue

        elif line_sum > MAX_SUM:
            # Too high: swap lowest-prob large number with a smaller number of the same parity
            high_candidates = sorted([(probabilities[n-1], n) for n in numbers if n >= 30])
            if high_candidates:
                _, num_to_remove = high_candidates[0]
                parity = num_to_remove % 2
                low_available = sorted(
                    [(probabilities[n-1], n) for n in range(1, 25)
                     if n % 2 == parity and n not in numbers],
                    reverse=True
                )
                if low_available:
                    numbers.remove(num_to_remove)
                    numbers.append(low_available[0][1])
                    continue

        # 3. Address Range Distribution failures (span < MIN_SPAN)
        line_span = max(numbers) - min(numbers)
        if line_span < MIN_SPAN:
            # Clustered: if clustered high, swap one for a low number; if clustered low, swap for a high number
            midpoint = np.mean(numbers)
            if midpoint > 24:
                high_candidates = sorted([(probabilities[n-1], n) for n in numbers])
                _, num_to_remove = high_candidates[0]
                parity = num_to_remove % 2
                low_available = sorted(
                    [(probabilities[n-1], n) for n in range(1, 15)
                     if n % 2 == parity and n not in numbers],
                    reverse=True
                )
                if low_available:
                    numbers.remove(num_to_remove)
                    numbers.append(low_available[0][1])
                    continue
            else:
                low_candidates = sorted([(probabilities[n-1], n) for n in numbers])
                _, num_to_remove = low_candidates[0]
                parity = num_to_remove % 2
                high_available = sorted(
                    [(probabilities[n-1], n) for n in range(35, len(probabilities)+1)
                     if n % 2 == parity and n not in numbers],
                    reverse=True
                )
                if high_available:
                    numbers.remove(num_to_remove)
                    numbers.append(high_available[0][1])
                    continue

    return sorted(numbers)


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