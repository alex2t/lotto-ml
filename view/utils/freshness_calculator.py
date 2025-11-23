# view/utils/freshness_calculator.py
"""
Utility to calculate 6-ball and 7-ball freshness pattern probabilities.
When a player picks 6 balls with a specific freshness pattern,
we calculate the probability that any of the 7-ball draws would match,
considering the 7th ball could fall into any freshness category.
"""

from typing import Dict, List, Tuple, Any


def calculate_6_ball_freshness_probabilities(
    freshness_data: Dict[str, Any],
    c_max: int
) -> List[Dict]:
    """
    Calculate probabilities for all possible 6-ball freshness patterns.

    For each 6-ball pattern, calculate the combined probability by summing
    the probabilities of all 7-ball patterns that could result from it.

    Args:
        freshness_data: Dictionary with freshness analysis data
        c_max: Maximum freshness count threshold (e.g., 2 for C_GE_2)

    Returns:
        List of dictionaries containing 6-ball patterns and their probabilities,
        sorted by probability descending
    """
    distributions = freshness_data.get("distribution_analysis_7_numbers", [])

    # Build a lookup dictionary for 7-ball patterns
    pattern_lookup = {}
    for pattern in distributions:
        # Create a tuple key based on c_max
        if c_max == 2:
            key = (pattern.get("C0", 0), pattern.get("C1", 0), pattern.get("C_GE_2", 0))
        else:
            # For other c_max values, dynamically build key
            key_parts = []
            for i in range(c_max):
                key_parts.append(pattern.get(f"C{i}", 0))
            key_parts.append(pattern.get(f"C_GE_{c_max}", 0))
            key = tuple(key_parts)

        pattern_lookup[key] = {
            'percentage': pattern.get('percentage', 0.0),
            'draws_matched': pattern.get('draws_matched', 0),
            'pattern_str': pattern.get('pattern', '')
        }

    # Generate all possible 6-ball combinations
    # For c_max=2: c0 + c1 + c_ge_2 = 6
    six_ball_patterns = []
    num_categories = c_max + 1  # e.g., C0, C1, C_GE_2 = 3 categories

    # Generate all combinations that sum to 6
    for counts in _generate_combinations(num_categories, 6):
        six_ball_patterns.append(counts)

    results = []

    for pattern_6 in six_ball_patterns:
        # Calculate the possible 7-ball outcomes (adding 1 to each category)
        seven_ball_outcomes = []

        for cat_idx in range(num_categories):
            # Add 1 to this category
            pattern_7 = list(pattern_6)
            pattern_7[cat_idx] += 1
            seven_ball_outcomes.append(tuple(pattern_7))

        # Get percentages and counts for each outcome
        total_percentage = 0.0
        total_count = 0
        breakdown = []

        for i, pattern_7 in enumerate(seven_ball_outcomes):
            pattern_info = pattern_lookup.get(pattern_7, {
                'percentage': 0.0,
                'draws_matched': 0,
                'pattern_str': 'Not found'
            })

            pct = pattern_info['percentage']
            count = pattern_info['draws_matched']

            total_percentage += pct
            total_count += count

            # Build category label
            if c_max == 2:
                cat_labels = ['C0', 'C1', f'C≥{c_max}']
            else:
                cat_labels = [f'C{i}' for i in range(c_max)] + [f'C≥{c_max}']

            breakdown.append({
                'scenario': f'If 7th ball is {cat_labels[i]}',
                'pattern_7_ball': pattern_7,
                'pattern_str': pattern_info['pattern_str'],
                'percentage': pct,
                'count': count
            })

        # Build pattern string for 6-ball
        if c_max == 2:
            pattern_6_str = f"{pattern_6[0]}C0-{pattern_6[1]}C1-{pattern_6[2]}C≥{c_max}"
        else:
            parts = [f"{pattern_6[i]}C{i}" for i in range(c_max)]
            parts.append(f"{pattern_6[c_max]}C≥{c_max}")
            pattern_6_str = "-".join(parts)

        result = {
            'pattern_6_ball': pattern_6_str,
            'pattern_tuple': pattern_6,
            'total_percentage': total_percentage,
            'total_count': total_count,
            'breakdown': breakdown
        }

        results.append(result)

    # Sort by total percentage descending
    results.sort(key=lambda x: x['total_percentage'], reverse=True)

    return results


def get_6_ball_freshness_breakdown(
    pattern_counts: List[int],
    freshness_data: Dict[str, Any],
    c_max: int
) -> Dict:
    """
    Get detailed breakdown for a specific 6-ball freshness pattern.

    Args:
        pattern_counts: List of counts for each category (e.g., [3, 2, 1] for 3C0, 2C1, 1C_GE_2)
        freshness_data: Dictionary with freshness analysis data
        c_max: Maximum freshness count threshold

    Returns:
        Dictionary with detailed breakdown and probability
    """
    if sum(pattern_counts) != 6:
        raise ValueError(f"Pattern counts must sum to 6, got {sum(pattern_counts)}")

    distributions = freshness_data.get("distribution_analysis_7_numbers", [])

    # Build lookup
    pattern_lookup = {}
    for pattern in distributions:
        if c_max == 2:
            key = (pattern.get("C0", 0), pattern.get("C1", 0), pattern.get("C_GE_2", 0))
        else:
            key_parts = []
            for i in range(c_max):
                key_parts.append(pattern.get(f"C{i}", 0))
            key_parts.append(pattern.get(f"C_GE_{c_max}", 0))
            key = tuple(key_parts)

        pattern_lookup[key] = {
            'percentage': pattern.get('percentage', 0.0),
            'draws_matched': pattern.get('draws_matched', 0),
            'pattern_str': pattern.get('pattern', '')
        }

    # Calculate 7-ball outcomes
    num_categories = c_max + 1
    breakdown = []
    total_percentage = 0.0
    total_count = 0

    if c_max == 2:
        cat_labels = ['C0', 'C1', f'C≥{c_max}']
    else:
        cat_labels = [f'C{i}' for i in range(c_max)] + [f'C≥{c_max}']

    for cat_idx in range(num_categories):
        pattern_7 = list(pattern_counts)
        pattern_7[cat_idx] += 1
        pattern_7_tuple = tuple(pattern_7)

        pattern_info = pattern_lookup.get(pattern_7_tuple, {
            'percentage': 0.0,
            'draws_matched': 0,
            'pattern_str': 'Not found'
        })

        pct = pattern_info['percentage']
        count = pattern_info['draws_matched']

        total_percentage += pct
        total_count += count

        breakdown.append({
            'scenario': f'If 7th ball is {cat_labels[cat_idx]}',
            'pattern_7_ball': pattern_7_tuple,
            'pattern_str': pattern_info['pattern_str'],
            'percentage': pct,
            'count': count
        })

    # Build pattern string
    if c_max == 2:
        pattern_6_str = f"{pattern_counts[0]}C0-{pattern_counts[1]}C1-{pattern_counts[2]}C≥{c_max}"
    else:
        parts = [f"{pattern_counts[i]}C{i}" for i in range(c_max)]
        parts.append(f"{pattern_counts[c_max]}C≥{c_max}")
        pattern_6_str = "-".join(parts)

    return {
        'pattern_6_ball': pattern_6_str,
        'total_percentage': total_percentage,
        'total_count': total_count,
        'breakdown': breakdown
    }


def get_7_ball_freshness_details(
    pattern_counts: List[int],
    freshness_data: Dict[str, Any],
    c_max: int
) -> Dict:
    """
    Get details for a specific 7-ball freshness pattern.

    Args:
        pattern_counts: List of counts for each category (e.g., [3, 3, 1] for 3C0, 3C1, 1C_GE_2)
        freshness_data: Dictionary with freshness analysis data
        c_max: Maximum freshness count threshold

    Returns:
        Dictionary with pattern details
    """
    if sum(pattern_counts) != 7:
        raise ValueError(f"Pattern counts must sum to 7, got {sum(pattern_counts)}")

    distributions = freshness_data.get("distribution_analysis_7_numbers", [])

    # Find the pattern
    for pattern in distributions:
        if c_max == 2:
            if (pattern.get("C0", 0) == pattern_counts[0] and
                pattern.get("C1", 0) == pattern_counts[1] and
                pattern.get("C_GE_2", 0) == pattern_counts[2]):

                return {
                    'pattern_str': pattern.get('pattern', ''),
                    'percentage': pattern.get('percentage', 0.0),
                    'draws_matched': pattern.get('draws_matched', 0),
                    'found': True
                }
        else:
            match = True
            for i in range(c_max):
                if pattern.get(f"C{i}", 0) != pattern_counts[i]:
                    match = False
                    break
            if match and pattern.get(f"C_GE_{c_max}", 0) == pattern_counts[c_max]:
                return {
                    'pattern_str': pattern.get('pattern', ''),
                    'percentage': pattern.get('percentage', 0.0),
                    'draws_matched': pattern.get('draws_matched', 0),
                    'found': True
                }

    # Pattern not found
    if c_max == 2:
        pattern_6_str = f"{pattern_counts[0]}C0-{pattern_counts[1]}C1-{pattern_counts[2]}C≥{c_max}"
    else:
        parts = [f"{pattern_counts[i]}C{i}" for i in range(c_max)]
        parts.append(f"{pattern_counts[c_max]}C≥{c_max}")
        pattern_6_str = "-".join(parts)

    return {
        'pattern_str': pattern_6_str,
        'percentage': 0.0,
        'draws_matched': 0,
        'found': False
    }


def _generate_combinations(num_categories: int, target_sum: int) -> List[List[int]]:
    """
    Generate all combinations of num_categories non-negative integers that sum to target_sum.

    Args:
        num_categories: Number of categories
        target_sum: Target sum

    Returns:
        List of combinations
    """
    if num_categories == 1:
        return [[target_sum]]

    results = []
    for i in range(target_sum + 1):
        for sub_combo in _generate_combinations(num_categories - 1, target_sum - i):
            results.append([i] + sub_combo)

    return results
