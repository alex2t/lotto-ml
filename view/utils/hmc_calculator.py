# view/utils/hmc_calculator.py
"""
Utility to calculate 6-ball HMC pattern probabilities.
When a player picks 6 balls with a specific HMC pattern,
we calculate the probability that any of the 7-ball draws would match,
considering the 7th ball could be Hot, Medium, or Cold.
"""

from typing import Dict, List, Tuple


def calculate_6_ball_hmc_probabilities(hmc_data: Dict[str, Dict]) -> List[Dict]:
    """
    Calculate probabilities for all possible 6-ball HMC patterns.

    For each 6-ball pattern (e.g., 2H-2M-2C), calculate the combined probability
    by summing the probabilities of all 7-ball patterns that could result from it:
    - 2H-2M-2C + Hot ball = 3H-2M-2C
    - 2H-2M-2C + Medium ball = 2H-3M-2C
    - 2H-2M-2C + Cold ball = 2H-2M-3C

    Args:
        hmc_data: Dictionary with 7-ball HMC patterns as keys (e.g., "4-1-2")
                  and their statistics as values (count, percentage)

    Returns:
        List of dictionaries containing 6-ball patterns and their probabilities,
        sorted by probability descending
    """
    # Generate all possible 6-ball combinations (hot + medium + cold = 6)
    six_ball_patterns = []

    for hot in range(0, 7):  # 0 to 6 hot balls
        for medium in range(0, 7 - hot):  # remaining can be medium
            cold = 6 - hot - medium  # rest are cold
            if cold >= 0:
                six_ball_patterns.append((hot, medium, cold))

    results = []

    for h, m, c in six_ball_patterns:
        # Calculate the 3 possible 7-ball outcomes
        pattern_7h = f"{h+1}-{m}-{c}"  # 7th ball is Hot
        pattern_7m = f"{h}-{m+1}-{c}"  # 7th ball is Medium
        pattern_7c = f"{h}-{m}-{c+1}"  # 7th ball is Cold

        # Get percentages for each pattern (default to 0 if not found)
        pct_7h = hmc_data.get(pattern_7h, {}).get('percentage', 0.0)
        pct_7m = hmc_data.get(pattern_7m, {}).get('percentage', 0.0)
        pct_7c = hmc_data.get(pattern_7c, {}).get('percentage', 0.0)

        # Get counts for each pattern
        count_7h = hmc_data.get(pattern_7h, {}).get('count', 0)
        count_7m = hmc_data.get(pattern_7m, {}).get('count', 0)
        count_7c = hmc_data.get(pattern_7c, {}).get('count', 0)

        # Total probability is the sum
        total_percentage = pct_7h + pct_7m + pct_7c
        total_count = count_7h + count_7m + count_7c

        results.append({
            'pattern_6_ball': f"{h}H-{m}M-{c}C",
            'hot': h,
            'medium': m,
            'cold': c,
            'total_percentage': total_percentage,
            'total_count': total_count,
            'breakdown': {
                'if_7th_is_hot': {
                    'pattern': pattern_7h,
                    'percentage': pct_7h,
                    'count': count_7h
                },
                'if_7th_is_medium': {
                    'pattern': pattern_7m,
                    'percentage': pct_7m,
                    'count': count_7m
                },
                'if_7th_is_cold': {
                    'pattern': pattern_7c,
                    'percentage': pct_7c,
                    'count': count_7c
                }
            }
        })

    # Sort by total percentage descending
    results.sort(key=lambda x: x['total_percentage'], reverse=True)

    return results


def get_6_ball_pattern_breakdown(hot: int, medium: int, cold: int,
                                   hmc_data: Dict[str, Dict]) -> Dict:
    """
    Get detailed breakdown for a specific 6-ball HMC pattern.

    Args:
        hot: Number of hot balls in the 6-ball selection
        medium: Number of medium balls in the 6-ball selection
        cold: Number of cold balls in the 6-ball selection
        hmc_data: Dictionary with 7-ball HMC patterns

    Returns:
        Dictionary with detailed breakdown and probability
    """
    if hot + medium + cold != 6:
        raise ValueError("Hot + Medium + Cold must equal 6")

    pattern_7h = f"{hot+1}-{medium}-{cold}"
    pattern_7m = f"{hot}-{medium+1}-{cold}"
    pattern_7c = f"{hot}-{medium}-{cold+1}"

    pct_7h = hmc_data.get(pattern_7h, {}).get('percentage', 0.0)
    pct_7m = hmc_data.get(pattern_7m, {}).get('percentage', 0.0)
    pct_7c = hmc_data.get(pattern_7c, {}).get('percentage', 0.0)

    count_7h = hmc_data.get(pattern_7h, {}).get('count', 0)
    count_7m = hmc_data.get(pattern_7m, {}).get('count', 0)
    count_7c = hmc_data.get(pattern_7c, {}).get('count', 0)

    total_percentage = pct_7h + pct_7m + pct_7c
    total_count = count_7h + count_7m + count_7c

    return {
        'pattern_6_ball': f"{hot}H-{medium}M-{cold}C",
        'total_percentage': total_percentage,
        'total_count': total_count,
        'breakdown': [
            {
                'scenario': 'If 7th ball is HOT',
                'pattern_7_ball': pattern_7h,
                'percentage': pct_7h,
                'count': count_7h
            },
            {
                'scenario': 'If 7th ball is MEDIUM',
                'pattern_7_ball': pattern_7m,
                'percentage': pct_7m,
                'count': count_7m
            },
            {
                'scenario': 'If 7th ball is COLD',
                'pattern_7_ball': pattern_7c,
                'percentage': pct_7c,
                'count': count_7c
            }
        ]
    }
