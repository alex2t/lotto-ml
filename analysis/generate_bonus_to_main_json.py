#!/usr/bin/env python3
"""
Generate Bonus-to-Main Pattern JSON
====================================
Creates lotto_bonus_to_main_patterns.json with aggregated features for ML model.

Features include:
- Per-number transition profiles
- Category transition weights
- Freshness transition weights
- Timing decay weights
- Current bonus window tracking
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

def load_draw_history():
    """Load draw history JSON."""
    try:
        with open('data/lotto_draw_history.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("ERROR: data/lotto_draw_history.json not found")
        sys.exit(1)

def calculate_per_number_profiles(draw_history, max_number=47):
    """Calculate transition profile for each number."""

    sorted_draws = sorted(
        draw_history.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    # Track for each number
    number_profiles = {}

    for num in range(1, max_number + 1):
        number_profiles[num] = {
            'total_bonus_appearances': 0,
            'transitioned_to_main': 0,
            'transition_rate': 0.0,
            'transition_draws': [],  # Which draw in window
            'last_bonus_date': None,
            'days_since_last_bonus': None,
            'category_when_bonus': [],
            'freshness_when_bonus': [],
            'avg_draws_to_transition': None
        }

    # Scan through draws
    for idx in range(len(sorted_draws) - 10):
        date, draw = sorted_draws[idx]
        details = draw.get('winning_numbers_details', [])

        if len(details) < 7:
            continue

        bonus_detail = details[6]
        bonus_num = bonus_detail['number']
        bonus_category = bonus_detail.get('category', 'unknown')
        bonus_freshness = bonus_detail.get('current_freshness_bin', 0)

        number_profiles[bonus_num]['total_bonus_appearances'] += 1
        number_profiles[bonus_num]['last_bonus_date'] = date
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

        if profile['transition_draws']:
            profile['avg_draws_to_transition'] = round(
                sum(profile['transition_draws']) / len(profile['transition_draws']),
                2
            )

        if profile['last_bonus_date']:
            last_bonus_obj = datetime.strptime(profile['last_bonus_date'], "%Y-%m-%d")
            profile['days_since_last_bonus'] = (latest_date_obj - last_bonus_obj).days

        # Most common category/freshness when bonus
        if profile['category_when_bonus']:
            profile['most_common_category'] = max(
                set(profile['category_when_bonus']),
                key=profile['category_when_bonus'].count
            )

        if profile['freshness_when_bonus']:
            profile['most_common_freshness'] = max(
                set(profile['freshness_when_bonus']),
                key=profile['freshness_when_bonus'].count
            )

        # Build timing distribution
        timing_dist = defaultdict(int)
        for draw_offset in profile['transition_draws']:
            if draw_offset <= 3:
                timing_dist[f'draw_1_3'] += 1
            elif draw_offset <= 5:
                timing_dist[f'draw_4_5'] += 1
            else:
                timing_dist[f'draw_6_10'] += 1

        profile['transition_timing_distribution'] = dict(timing_dist)

        # Clean up for JSON
        del profile['category_when_bonus']
        del profile['freshness_when_bonus']
        del profile['transition_draws']

        final_profiles[str(num)] = profile

    return final_profiles

def calculate_category_weights(draw_history):
    """Calculate category transition weights."""

    sorted_draws = sorted(
        draw_history.items(),
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

def calculate_freshness_weights(draw_history):
    """Calculate freshness bin transition weights."""

    sorted_draws = sorted(
        draw_history.items(),
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

    # Calculate weights (normalized to C1 = 1.0)
    c1_rate = (freshness_stats['C1']['transitioned'] /
              freshness_stats['C1']['total']) if freshness_stats['C1']['total'] > 0 else 1.0

    weights = {}
    for freshness, stats in freshness_stats.items():
        total = stats['total']
        transitioned = stats['transitioned']
        rate = transitioned / total if total > 0 else 0

        weights[freshness] = {
            'total': total,
            'transitioned': transitioned,
            'rate': round(rate, 4),
            'weight': round(rate / c1_rate if c1_rate > 0 else 1.0, 2)
        }

    return weights

def calculate_timing_decay_weights(draw_history):
    """Calculate timing distribution for decay weights."""

    sorted_draws = sorted(
        draw_history.items(),
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

def get_current_bonus_window(draw_history):
    """Get current 10-draw bonus window."""

    sorted_draws = sorted(
        draw_history.items(),
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

def main():
    """Generate complete JSON file."""

    print("="*70)
    print("GENERATING BONUS-TO-MAIN PATTERNS JSON")
    print("="*70)

    draw_history = load_draw_history()
    print(f"\nLoaded {len(draw_history)} draws")

    print("\n1. Calculating per-number transition profiles...")
    per_number_profiles = calculate_per_number_profiles(draw_history)
    print(f"   ✓ Generated profiles for {len(per_number_profiles)} numbers")

    print("\n2. Calculating category transition weights...")
    category_weights = calculate_category_weights(draw_history)
    print(f"   ✓ Generated weights for {len(category_weights)} categories")

    print("\n3. Calculating freshness transition weights...")
    freshness_weights = calculate_freshness_weights(draw_history)
    print(f"   ✓ Generated weights for {len(freshness_weights)} freshness bins")

    print("\n4. Calculating timing decay weights...")
    timing_weights = calculate_timing_decay_weights(draw_history)
    print(f"   ✓ Generated weights for {len(timing_weights)} draw positions")

    print("\n5. Getting current bonus window...")
    current_window = get_current_bonus_window(draw_history)
    print(f"   ✓ Tracked last {len(current_window)} bonus numbers")

    # Calculate overall stats
    total_transitions = sum(1 for p in per_number_profiles.values()
                           if p['transitioned_to_main'] > 0)
    total_bonuses = sum(p['total_bonus_appearances']
                       for p in per_number_profiles.values())
    overall_rate = sum(p['transitioned_to_main']
                       for p in per_number_profiles.values()) / total_bonuses if total_bonuses > 0 else 0

    # Build final JSON
    output = {
        "metadata": {
            "description": "Bonus-to-Main transition patterns for ML prediction",
            "total_bonus_appearances": total_bonuses,
            "overall_transition_rate": round(overall_rate, 4),
            "numbers_with_transitions": total_transitions
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
            "timing_peak": [1, 2],
            "timing_critical_window": [1, 5],
            "expected_random_rate": round(10/47, 4),
            "boost_factor": round(overall_rate / (10/47), 2)
        }
    }

    # Save to file
    output_file = 'data/lotto_bonus_to_main_patterns.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "="*70)
    print("GENERATION COMPLETE")
    print("="*70)
    print(f"Output saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  - Total bonus appearances: {total_bonuses}")
    print(f"  - Overall transition rate: {overall_rate*100:.2f}%")
    print(f"  - Numbers with transitions: {total_transitions}")
    print(f"  - Boost over random: {overall_rate / (10/47):.2f}x")
    print()

if __name__ == "__main__":
    main()
