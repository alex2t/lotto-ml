"""
filters.py
==========
Phase 1 validation filters for lottery picks.

Implements odd/even balance constraint based on historical data:
- 3 odd / 3 even: 32.03% (most common)
- 2 odd / 4 even: 23.47%
- 4 odd / 2 even: 23.23%
- Valid range: 2-4 odd numbers (78.73% of historical draws)
"""

from typing import List, Tuple, Dict, Any
import numpy as np


# Global flag indicating if actual filters are available
FILTERS_AVAILABLE = True


def validate_line(numbers: List[int]) -> Tuple[bool, List[str]]:
    """
    Validate a line of numbers against all Phase 1 filters.

    Args:
        numbers: Sorted list of 6-7 numbers

    Returns:
        Tuple of (is_valid, list_of_failures)

    Filters:
        1. Odd/Even Balance: Must have 2-4 odd numbers (optimal: 3)
    """
    failures = []

    # Filter 1: Odd/Even Balance
    odd_count = sum(1 for n in numbers if n % 2 == 1)
    even_count = len(numbers) - odd_count

    # Valid range: 2-4 odd numbers (covers 78.73% of historical draws)
    if odd_count < 2 or odd_count > 4:
        failures.append(f'odd_even_balance ({odd_count} odd / {even_count} even)')

    return (len(failures) == 0, failures)


def rebalance_line(
    numbers: List[int],
    probabilities: Any,  # numpy array
    features_dict: Dict[int, Dict[str, Any]],
    max_iterations: int = 3
) -> List[int]:
    """
    Attempt to fix a line that failed validation filters.

    Strategy:
        - If too few odd numbers: swap lowest-prob even for highest-prob odd
        - If too many odd numbers: swap lowest-prob odd for highest-prob even
        - Target: 3 odd / 3 even (most common pattern at 32.03%)

    Args:
        numbers: Original line that failed validation
        probabilities: Model probability scores for all numbers (1-47)
        features_dict: Feature data for making intelligent swaps
        max_iterations: Maximum rebalancing attempts

    Returns:
        Rebalanced line (may still fail validation if unfixable)
    """
    numbers = list(numbers)  # Make a copy to avoid modifying original

    for iteration in range(max_iterations):
        is_valid, failures = validate_line(numbers)

        if is_valid:
            return sorted(numbers)

        # Check odd/even balance
        odd_count = sum(1 for n in numbers if n % 2 == 1)
        even_count = len(numbers) - odd_count
        target_odd = 3  # Optimal pattern: 3 odd / 3 even

        if odd_count < 2:
            # Too few odd numbers - swap lowest-prob even for highest-prob odd
            evens_in_line = sorted([(probabilities[n-1], n) for n in numbers if n % 2 == 0])
            if not evens_in_line:
                continue

            # Find odd numbers not in line, sorted by probability
            odds_available = sorted(
                [(probabilities[n-1], n) for n in range(1, len(probabilities)+1)
                 if n % 2 == 1 and n not in numbers],
                reverse=True
            )

            if odds_available:
                # Swap lowest-prob even for highest-prob odd
                _, even_to_remove = evens_in_line[0]
                prob_odd, odd_to_add = odds_available[0]

                numbers.remove(even_to_remove)
                numbers.append(odd_to_add)

        elif odd_count > 4:
            # Too many odd numbers - swap lowest-prob odd for highest-prob even
            odds_in_line = sorted([(probabilities[n-1], n) for n in numbers if n % 2 == 1])
            if not odds_in_line:
                continue

            # Find even numbers not in line, sorted by probability
            evens_available = sorted(
                [(probabilities[n-1], n) for n in range(1, len(probabilities)+1)
                 if n % 2 == 0 and n not in numbers],
                reverse=True
            )

            if evens_available:
                # Swap lowest-prob odd for highest-prob even
                _, odd_to_remove = odds_in_line[0]
                prob_even, even_to_add = evens_available[0]

                numbers.remove(odd_to_remove)
                numbers.append(even_to_add)

        elif odd_count == 2 and target_odd == 3:
            # 2 odd / 4 even - acceptable but try to get to optimal 3/3
            evens_in_line = sorted([(probabilities[n-1], n) for n in numbers if n % 2 == 0])

            odds_available = sorted(
                [(probabilities[n-1], n) for n in range(1, len(probabilities)+1)
                 if n % 2 == 1 and n not in numbers],
                reverse=True
            )

            if evens_in_line and odds_available:
                # Only swap if the odd has significantly higher probability
                _, even_to_remove = evens_in_line[0]
                prob_odd, odd_to_add = odds_available[0]
                prob_even = probabilities[even_to_remove - 1]

                if prob_odd > prob_even * 1.2:  # 20% threshold
                    numbers.remove(even_to_remove)
                    numbers.append(odd_to_add)
                else:
                    # Already valid, don't force the swap
                    break

        elif odd_count == 4 and target_odd == 3:
            # 4 odd / 2 even - acceptable but try to get to optimal 3/3
            odds_in_line = sorted([(probabilities[n-1], n) for n in numbers if n % 2 == 1])

            evens_available = sorted(
                [(probabilities[n-1], n) for n in range(1, len(probabilities)+1)
                 if n % 2 == 0 and n not in numbers],
                reverse=True
            )

            if odds_in_line and evens_available:
                # Only swap if the even has significantly higher probability
                _, odd_to_remove = odds_in_line[0]
                prob_even, even_to_add = evens_available[0]
                prob_odd = probabilities[odd_to_remove - 1]

                if prob_even > prob_odd * 1.2:  # 20% threshold
                    numbers.remove(odd_to_remove)
                    numbers.append(even_to_add)
                else:
                    # Already valid, don't force the swap
                    break

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
            'description': 'Sum Constraint Filter (not implemented)',
            'expected_elimination': 'N/A'
        },
        'range_distribution': {
            'description': 'Range Distribution Filter (not implemented)',
            'expected_elimination': 'N/A'
        },
        'combined_impact': {
            'total_elimination': '21.27% (odd/even filter only)'
        }
    }