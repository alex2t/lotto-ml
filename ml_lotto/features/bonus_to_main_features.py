"""
bonus_to_main_features.py
==========================
Extract features for bonus-to-main transition prediction.

Features track which numbers from recent bonus draws are likely to appear as main numbers.
"""

from typing import Dict, Any, List


def extract_bonus_to_main_features_dict(
    bonus_to_main_data: Dict[str, Any],
    features_dict: Dict[int, Dict[str, Any]]
) -> Dict[int, Dict[str, float]]:
    """
    Extract bonus-to-main transition features for all numbers.

    Args:
        bonus_to_main_data: Loaded JSON from lotto_bonus_to_main_patterns.json
        features_dict: Existing features dictionary (for category, freshness)

    Returns:
        Dictionary mapping number -> bonus-to-main features

    Features extracted:
        - is_in_bonus_window: Binary flag (1 if in last 10 bonus numbers)
        - draws_since_bonus: How many draws ago it was bonus (0-9, or -1 if not in window)
        - historical_transition_rate: This number's historical transition success rate
        - category_multiplier: Category weight (hot/medium/cold)
        - freshness_multiplier: Freshness weight (C0/C1/C2+)
        - timing_decay_weight: Time-based decay weight for current position
        - composite_transition_score: Combined probability score
        - avg_draws_to_transition: Average timing when this number transitions
        - recent_4: Recent appearance count (from main features)
        - recent_9: Recent appearance count (from main features)
        - total_count: Total appearance count (from main features)
    """
    bonus_to_main_features = {}

    # Get data structures
    per_number_profiles = bonus_to_main_data.get('per_number_transition_profile', {})
    category_weights = bonus_to_main_data.get('category_transition_weights', {})
    freshness_weights = bonus_to_main_data.get('freshness_transition_weights', {})
    timing_weights = bonus_to_main_data.get('timing_decay_weights', {})
    current_window = bonus_to_main_data.get('current_bonus_window', {}).get('last_10_bonus_numbers', [])
    base_rate = bonus_to_main_data.get('transition_prediction_factors', {}).get('base_rate', 0.74)

    # Build lookup for current bonus window
    bonus_window_lookup = {}
    for entry in current_window:
        num = entry['number']
        bonus_window_lookup[num] = {
            'draws_ago': entry['draws_ago'],
            'category': entry.get('category', 'medium'),
            'freshness': entry.get('freshness', 0)
        }

    # Extract features for all numbers
    for num in range(1, 48):
        # Get number's transition profile
        profile = per_number_profiles.get(str(num), {})

        # Check if in recent bonus window
        is_in_window = num in bonus_window_lookup

        # Get draws_since_bonus
        draws_since_bonus = bonus_window_lookup[num]['draws_ago'] if is_in_window else -1

        # Get historical transition rate
        historical_rate = profile.get('transition_rate', 0.0)

        # Get category and freshness from main features
        if num in features_dict:
            category = features_dict[num].get('category', 'medium')
            freshness_bin = features_dict[num].get('current_freshness_bin', 0)
            recent_4 = features_dict[num].get('recent_4', 0)
            recent_9 = features_dict[num].get('recent_9', 0)
            total_count = features_dict[num].get('total_count', 0)
        else:
            category = 'medium'
            freshness_bin = 0
            recent_4 = 0
            recent_9 = 0
            total_count = 0

        # Convert freshness_bin to key
        freshness_key = f'C{freshness_bin}' if freshness_bin < 2 else 'C2+'

        # Get multipliers
        category_multiplier = category_weights.get(category, {}).get('weight', 1.0)
        freshness_multiplier = freshness_weights.get(freshness_key, {}).get('weight', 1.0)

        # Get timing weight
        timing_decay_weight = 0.0
        if is_in_window:
            draw_offset = draws_since_bonus + 1  # draws_ago=0 → draw_1
            timing_decay_weight = timing_weights.get(f'draw_{draw_offset}', 0.0)

        # Calculate composite score
        if is_in_window:
            composite_score = (
                base_rate *
                category_multiplier *
                freshness_multiplier *
                (1 + timing_decay_weight)
            )
        else:
            composite_score = 0.0

        # Get average draws to transition
        avg_draws_to_transition = profile.get('avg_draws_to_transition', 0.0)

        # Build feature dictionary
        bonus_to_main_features[num] = {
            'is_in_bonus_window': 1.0 if is_in_window else 0.0,
            'draws_since_bonus': float(draws_since_bonus),
            'historical_transition_rate': historical_rate,
            'category_multiplier': category_multiplier,
            'freshness_multiplier': freshness_multiplier,
            'timing_decay_weight': timing_decay_weight,
            'composite_transition_score': composite_score,
            'avg_draws_to_transition': avg_draws_to_transition,
            'recent_4': float(recent_4),
            'recent_9': float(recent_9),
            'total_count': float(total_count)
        }

    return bonus_to_main_features
