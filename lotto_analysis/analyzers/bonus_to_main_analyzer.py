"""
Bonus-to-Main Transition Analysis Module
==========================================
Analyzes patterns where bonus numbers transition to main numbers within 10 draws.

All weights and statistics are data-driven from historical patterns.
No hardcoded values.
"""

from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime


def calculate_per_number_transition_profiles(
    draw_history_log: Dict,
    max_number: int = 47
) -> Dict:
    """
    Calculate transition profile for each number based on historical data.

    Args:
        draw_history_log: Full draw history
        max_number: Maximum lottery number

    Returns:
        Dictionary with per-number transition profiles
    """
    sorted_draws = sorted(
        draw_history_log.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    # Track for each number
    number_profiles = {}

    for num in range(1, max_number + 1):
        number_profiles[num] = {
            'total_bonus_appearances': 0,
            'transitioned_to_main': 0,
            'transition_draws': [],
            'last_bonus_date': None,
            'category_when_bonus': [],
            'freshness_when_bonus': []
        }

    # First pass: Track ALL bonus appearances (including last 10) for last_bonus_date and total count
    for idx in range(len(sorted_draws)):
        date, draw = sorted_draws[idx]
        details = draw.get('winning_numbers_details', [])

        if len(details) < 7:
            continue

        bonus_detail = details[6]
        bonus_num = bonus_detail['number']

        # Always update last_bonus_date and count for ANY bonus appearance
        number_profiles[bonus_num]['last_bonus_date'] = date
        number_profiles[bonus_num]['total_bonus_appearances'] += 1

    # Second pass: Calculate transitions AND category/freshness stats (only up to -10 since we need future window)
    for idx in range(len(sorted_draws) - 10):
        date, draw = sorted_draws[idx]
        details = draw.get('winning_numbers_details', [])

        if len(details) < 7:
            continue

        bonus_detail = details[6]
        bonus_num = bonus_detail['number']
        bonus_category = bonus_detail.get('category', 'unknown')
        bonus_freshness = bonus_detail.get('current_freshness_bin', 0)

        # Track category and freshness stats (for transition analysis)
        number_profiles[bonus_num]['category_when_bonus'].append(bonus_category)
        number_profiles[bonus_num]['freshness_when_bonus'].append(bonus_freshness)

        # Check if transitions in next 10
        for future_offset in range(1, 11):
            if idx + future_offset >= len(sorted_draws):
                break

            future_date, future_draw = sorted_draws[idx + future_offset]
            future_details = future_draw.get('winning_numbers_details', [])

            if len(future_details) < 7:
                continue

            future_main = [future_details[i]['number'] for i in range(6)]

            if bonus_num in future_main:
                number_profiles[bonus_num]['transitioned_to_main'] += 1
                number_profiles[bonus_num]['transition_draws'].append(future_offset)
                break

    # Calculate final stats
    latest_date = sorted_draws[-1][0] if sorted_draws else "2024-01-01"
    latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d")

    final_profiles = {}

    for num, profile in number_profiles.items():
        if profile['total_bonus_appearances'] > 0:
            profile['transition_rate'] = round(
                profile['transitioned_to_main'] / profile['total_bonus_appearances'],
                4
            )
        else:
            profile['transition_rate'] = 0.0

        if profile['transition_draws']:
            profile['avg_draws_to_transition'] = round(
                sum(profile['transition_draws']) / len(profile['transition_draws']),
                2
            )
        else:
            profile['avg_draws_to_transition'] = None

        if profile['last_bonus_date']:
            last_bonus_obj = datetime.strptime(profile['last_bonus_date'], "%Y-%m-%d")
            profile['days_since_last_bonus'] = (latest_date_obj - last_bonus_obj).days
        else:
            profile['days_since_last_bonus'] = None

        # Most common category/freshness when bonus
        if profile['category_when_bonus']:
            profile['most_common_category'] = max(
                set(profile['category_when_bonus']),
                key=profile['category_when_bonus'].count
            )
        else:
            profile['most_common_category'] = 'unknown'

        if profile['freshness_when_bonus']:
            profile['most_common_freshness'] = max(
                set(profile['freshness_when_bonus']),
                key=profile['freshness_when_bonus'].count
            )
        else:
            profile['most_common_freshness'] = 0

        # Build timing distribution
        timing_dist = defaultdict(int)
        for draw_offset in profile['transition_draws']:
            if draw_offset <= 3:
                timing_dist['draw_1_3'] += 1
            elif draw_offset <= 5:
                timing_dist['draw_4_5'] += 1
            else:
                timing_dist['draw_6_10'] += 1

        profile['transition_timing_distribution'] = dict(timing_dist)

        # Clean up for JSON
        del profile['category_when_bonus']
        del profile['freshness_when_bonus']
        del profile['transition_draws']

        final_profiles[str(num)] = profile

    return final_profiles


def calculate_category_transition_weights(draw_history_log: Dict) -> Dict:
    """
    Calculate category transition weights from historical data.

    Args:
        draw_history_log: Full draw history

    Returns:
        Dictionary with category transition weights
    """
    sorted_draws = sorted(
        draw_history_log.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    category_stats = {
        'hot': {'total': 0, 'transitioned': 0},
        'medium': {'total': 0, 'transitioned': 0},
        'cold': {'total': 0, 'transitioned': 0}
    }

    for idx in range(len(sorted_draws) - 10):
        date, draw = sorted_draws[idx]
        details = draw.get('winning_numbers_details', [])

        if len(details) < 7:
            continue

        bonus_detail = details[6]
        bonus_num = bonus_detail['number']
        bonus_category = bonus_detail.get('category', 'unknown')

        if bonus_category not in ['hot', 'medium', 'cold']:
            continue

        category_stats[bonus_category]['total'] += 1

        # Check transition
        for future_offset in range(1, 11):
            if idx + future_offset >= len(sorted_draws):
                break

            future_date, future_draw = sorted_draws[idx + future_offset]
            future_details = future_draw.get('winning_numbers_details', [])

            if len(future_details) < 7:
                continue

            future_main = [future_details[i]['number'] for i in range(6)]

            if bonus_num in future_main:
                category_stats[bonus_category]['transitioned'] += 1
                break

    # Calculate weights (normalized to medium = 1.0)
    weights = {}
    medium_rate = (category_stats['medium']['transitioned'] /
                  category_stats['medium']['total']) if category_stats['medium']['total'] > 0 else 1.0

    for category, stats in category_stats.items():
        total = stats['total']
        transitioned = stats['transitioned']
        rate = transitioned / total if total > 0 else 0

        weights[category] = {
            'total': total,
            'transitioned': transitioned,
            'rate': round(rate, 4),
            'weight': round(rate / medium_rate if medium_rate > 0 else 1.0, 2)
        }

    return weights


def calculate_freshness_transition_weights(draw_history_log: Dict) -> Dict:
    """
    Calculate freshness bin transition weights from historical data.

    Args:
        draw_history_log: Full draw history

    Returns:
        Dictionary with freshness transition weights
    """
    sorted_draws = sorted(
        draw_history_log.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    freshness_stats = defaultdict(lambda: {'total': 0, 'transitioned': 0})

    for idx in range(len(sorted_draws) - 10):
        date, draw = sorted_draws[idx]
        details = draw.get('winning_numbers_details', [])

        if len(details) < 7:
            continue

        bonus_detail = details[6]
        bonus_num = bonus_detail['number']
        bonus_freshness = bonus_detail.get('current_freshness_bin', 0)

        freshness_key = f'C{bonus_freshness}' if bonus_freshness < 2 else 'C2+'
        freshness_stats[freshness_key]['total'] += 1

        # Check transition
        for future_offset in range(1, 11):
            if idx + future_offset >= len(sorted_draws):
                break

            future_date, future_draw = sorted_draws[idx + future_offset]
            future_details = future_draw.get('winning_numbers_details', [])

            if len(future_details) < 7:
                continue

            future_main = [future_details[i]['number'] for i in range(6)]

            if bonus_num in future_main:
                freshness_stats[freshness_key]['transitioned'] += 1
                break

    # Calculate weights (normalized to C1 = 1.0, or best performing)
    # Find best performing freshness bin
    best_rate = 0.0
    for stats in freshness_stats.values():
        if stats['total'] > 0:
            rate = stats['transitioned'] / stats['total']
            if rate > best_rate:
                best_rate = rate

    if best_rate == 0:
        best_rate = 1.0

    weights = {}
    for freshness, stats in freshness_stats.items():
        total = stats['total']
        transitioned = stats['transitioned']
        rate = transitioned / total if total > 0 else 0

        weights[freshness] = {
            'total': total,
            'transitioned': transitioned,
            'rate': round(rate, 4),
            'weight': round(rate / best_rate if best_rate > 0 else 1.0, 2)
        }

    return weights


def calculate_timing_decay_weights(draw_history_log: Dict) -> Dict:
    """
    Calculate timing distribution for decay weights from historical data.

    Args:
        draw_history_log: Full draw history

    Returns:
        Dictionary with timing decay weights
    """
    sorted_draws = sorted(
        draw_history_log.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    timing_counts = defaultdict(int)
    total_transitions = 0

    for idx in range(len(sorted_draws) - 10):
        date, draw = sorted_draws[idx]
        details = draw.get('winning_numbers_details', [])

        if len(details) < 7:
            continue

        bonus_num = details[6]['number']

        # Check transition timing
        for future_offset in range(1, 11):
            if idx + future_offset >= len(sorted_draws):
                break

            future_date, future_draw = sorted_draws[idx + future_offset]
            future_details = future_draw.get('winning_numbers_details', [])

            if len(future_details) < 7:
                continue

            future_main = [future_details[i]['number'] for i in range(6)]

            if bonus_num in future_main:
                timing_counts[future_offset] += 1
                total_transitions += 1
                break

    # Calculate weights
    weights = {}
    for draw_offset in range(1, 11):
        count = timing_counts[draw_offset]
        weight = count / total_transitions if total_transitions > 0 else 0
        weights[f'draw_{draw_offset}'] = round(weight, 4)

    return weights


def get_current_bonus_window(draw_history_log: Dict) -> List[Dict]:
    """
    Get current 10-draw bonus window from historical data.

    Args:
        draw_history_log: Full draw history

    Returns:
        List of last 10 bonus numbers with metadata
    """
    sorted_draws = sorted(
        draw_history_log.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    # Get last 10 bonus numbers
    bonus_window = []

    for idx in range(max(0, len(sorted_draws) - 10), len(sorted_draws)):
        date, draw = sorted_draws[idx]
        details = draw.get('winning_numbers_details', [])

        if len(details) < 7:
            continue

        bonus_detail = details[6]

        bonus_window.append({
            'number': bonus_detail['number'],
            'bonus_date': date,
            'draws_ago': len(sorted_draws) - idx - 1,
            'category': bonus_detail.get('category', 'unknown'),
            'freshness': bonus_detail.get('current_freshness_bin', 0)
        })

    # Reverse to get most recent first
    bonus_window.reverse()

    return bonus_window


def generate_bonus_to_main_analysis(
    draw_history_log: Dict,
    max_number: int = 47
) -> Dict:
    """
    Generate complete bonus-to-main transition analysis.

    All weights and statistics are calculated from historical data.
    No hardcoded values.

    Args:
        draw_history_log: Full draw history
        max_number: Maximum lottery number

    Returns:
        Complete bonus-to-main analysis dictionary
    """
    print("\n  Calculating per-number transition profiles...")
    per_number_profiles = calculate_per_number_transition_profiles(
        draw_history_log, max_number
    )

    print("  Calculating category transition weights...")
    category_weights = calculate_category_transition_weights(draw_history_log)

    print("  Calculating freshness transition weights...")
    freshness_weights = calculate_freshness_transition_weights(draw_history_log)

    print("  Calculating timing decay weights...")
    timing_weights = calculate_timing_decay_weights(draw_history_log)

    print("  Getting current bonus window...")
    current_window = get_current_bonus_window(draw_history_log)

    # Calculate overall statistics from data
    total_bonuses = sum(
        int(p['total_bonus_appearances'])
        for p in per_number_profiles.values()
    )

    total_transitions = sum(
        int(p['transitioned_to_main'])
        for p in per_number_profiles.values()
    )

    overall_rate = total_transitions / total_bonuses if total_bonuses > 0 else 0
    expected_random = 10 / max_number  # 10 positions in window / total numbers
    boost_factor = overall_rate / expected_random if expected_random > 0 else 1.0

    # Find peak timing draws (top 2)
    if timing_weights:
        timing_sorted = sorted(
            timing_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )
        peak_draws = [int(k.split('_')[1]) for k, v in timing_sorted[:2]]
    else:
        peak_draws = [1, 2]

    # Determine critical window (cumulative > 60%)
    cumulative = 0.0
    critical_window_end = 5
    for draw_offset in range(1, 11):
        cumulative += timing_weights.get(f'draw_{draw_offset}', 0)
        if cumulative >= 0.60:
            critical_window_end = draw_offset
            break

    return {
        "metadata": {
            "description": "Bonus-to-Main transition patterns for ML prediction",
            "total_bonus_appearances": total_bonuses,
            "overall_transition_rate": round(overall_rate, 4),
            "numbers_with_transitions": len([
                p for p in per_number_profiles.values()
                if p['transitioned_to_main'] > 0
            ])
        },

        "per_number_transition_profile": per_number_profiles,

        "category_transition_weights": category_weights,

        "freshness_transition_weights": freshness_weights,

        "timing_decay_weights": timing_weights,

        "current_bonus_window": {
            "last_10_bonus_numbers": current_window
        },

        "transition_prediction_factors": {
            "base_rate": round(overall_rate, 4),
            "category_multipliers": {
                cat: weights['weight']
                for cat, weights in category_weights.items()
            },
            "freshness_multipliers": {
                fresh: weights['weight']
                for fresh, weights in freshness_weights.items()
            },
            "timing_peak": peak_draws,
            "timing_critical_window": [1, critical_window_end],
            "expected_random_rate": round(expected_random, 4),
            "boost_factor": round(boost_factor, 2)
        }
    }
