"""
long_term_patterns.py
====================
Long-term pattern analysis features for identifying stable trends.

This module analyzes long-term patterns that are stable across many draws,
complementing the short-term FRESHNESS_PATTERN_WEIGHTS.

Features in this module:
- HMC pattern alignment weights
- Category-based long-term recency weights
- Historical performance weights

All features use data from lotto_statistics_analysis.json and draw history.
"""

from typing import Dict, Any, List
from collections import Counter
from ml_lotto.config import MAX_NUMBER


def calculate_long_term_hmc_pattern_weights(
    hmc_data: Dict[str, Any],
    statistics_data: Dict[str, Any]
) -> Dict[int, Dict[str, float]]:
    """
    Calculate long-term HMC pattern alignment weights for each number.

    Analyzes the historical HMC distribution patterns (e.g., "2-3-2", "2-2-3")
    and assigns weights to numbers based on which category they belong to
    and how well that aligns with historically successful patterns.

    Args:
        hmc_data: HMC statistics from lotto_trigger_periods.json
        statistics_data: Long-term statistics from lotto_statistics_analysis.json

    Returns:
        Dictionary mapping number -> long-term pattern feature dictionary
        Each feature dict contains:
        - lt_hot_weight: Weight for hot numbers based on HMC patterns
        - lt_medium_weight: Weight for medium numbers based on HMC patterns
        - lt_cold_weight: Weight for cold numbers based on HMC patterns
        - lt_category_alignment: Overall alignment score for number's category
    """
    # Extract HMC pattern distribution from statistics
    hmc_patterns = statistics_data.get('hmc_distribution', {}).get('hmc_pattern_distribution', {})

    if not hmc_patterns:
        print("\n⚠️  WARNING: No HMC pattern data found in statistics")
        return {num: {
            'lt_hot_weight': 0.33,
            'lt_medium_weight': 0.34,
            'lt_cold_weight': 0.33,
            'lt_category_alignment': 0.5
        } for num in range(1, MAX_NUMBER + 1)}

    # Calculate weighted average count for each category position
    hot_weights = []  # Position 0 in pattern
    medium_weights = []  # Position 1 in pattern
    cold_weights = []  # Position 2 in pattern

    for pattern, percentage in hmc_patterns.items():
        parts = pattern.split('-')
        if len(parts) == 3:
            try:
                hot_count = int(parts[0])
                medium_count = int(parts[1])
                cold_count = int(parts[2])

                weight = percentage / 100.0  # Convert percentage to weight

                # Weight by counts (e.g., pattern "3-2-2" suggests 3 hot is good)
                hot_weights.append((hot_count, weight))
                medium_weights.append((medium_count, weight))
                cold_weights.append((cold_count, weight))
            except (ValueError, IndexError):
                continue

    # Calculate normalized weights for each category
    # Higher counts in successful patterns = higher weight
    def calculate_category_weight(count_weight_pairs: List[tuple]) -> float:
        if not count_weight_pairs:
            return 0.33

        # Weight average: sum(count * pattern_weight) / sum(pattern_weights)
        total_weighted = sum(count * weight for count, weight in count_weight_pairs)
        total_weight = sum(weight for _, weight in count_weight_pairs)

        if total_weight == 0:
            return 0.33

        avg = total_weighted / total_weight
        # Normalize to 0-1 range (max typical count is 6)
        return min(1.0, avg / 6.0)

    hot_weight = calculate_category_weight(hot_weights)
    medium_weight = calculate_category_weight(medium_weights)
    cold_weight = calculate_category_weight(cold_weights)

    # Normalize weights to sum to 1.0
    total = hot_weight + medium_weight + cold_weight
    if total > 0:
        hot_weight /= total
        medium_weight /= total
        cold_weight /= total

    print(f"\n✓ Long-Term HMC Pattern Analysis:")
    print(f"  Analyzed {len(hmc_patterns)} historical HMC patterns")
    print(f"  Hot weight: {hot_weight*100:.1f}%")
    print(f"  Medium weight: {medium_weight*100:.1f}%")
    print(f"  Cold weight: {cold_weight*100:.1f}%")

    # Assign weights to each number based on their category
    features = {}
    category_counts = Counter()

    for num in range(1, MAX_NUMBER + 1):
        num_key = str(num)
        category = 'cold'  # Default

        if num_key in hmc_data:
            category = hmc_data[num_key].get('category', 'cold')

        category_counts[category] += 1

        # All numbers get all weights, but alignment shows which applies
        category_alignment = {
            'hot': hot_weight,
            'medium': medium_weight,
            'cold': cold_weight
        }.get(category, 0.33)

        features[num] = {
            'lt_hot_weight': hot_weight,
            'lt_medium_weight': medium_weight,
            'lt_cold_weight': cold_weight,
            'lt_category_alignment': category_alignment,
            'lt_category': category
        }

    print(f"\n  Current number distribution:")
    print(f"    Hot: {category_counts['hot']} numbers")
    print(f"    Medium: {category_counts['medium']} numbers")
    print(f"    Cold: {category_counts['cold']} numbers")

    return features


def calculate_long_term_recency_weights(
    hmc_data: Dict[str, Any],
    statistics_data: Dict[str, Any],
    all_draws: List[Dict[str, Any]]
) -> Dict[int, float]:
    """
    Calculate long-term recency pattern weights based on days since last hit.

    Analyzes the "days_since_last_hit" patterns from historical data to
    identify which recency ranges are most successful for each category.

    Args:
        hmc_data: HMC statistics from lotto_trigger_periods.json
        statistics_data: Long-term statistics from lotto_statistics_analysis.json
        all_draws: Draw history for calculating current days since last

    Returns:
        Dictionary mapping number -> long-term recency weight (0.0 to 1.0)
    """
    days_since_data = statistics_data.get('days_since_last_hit', {}).get('main_numbers', {}).get('by_category', {})

    if not days_since_data:
        print("\n⚠️  WARNING: No days_since_last_hit data found")
        return {num: 0.5 for num in range(1, MAX_NUMBER + 1)}

    # Define recency ranges and their order (shorter = more recent)
    recency_ranges = [
        ('0-7 days', 0, 7),
        ('8-14 days', 8, 14),
        ('15-21 days', 15, 21),
        ('22-30 days', 22, 30),
        ('31-45 days', 31, 45),
        ('46-60 days', 46, 60),
        ('61-90 days', 61, 90),
        ('91-120 days', 91, 120),
        ('121+ days', 121, 999)
    ]

    # Calculate current days_since for each number
    current_days_since = {}
    latest_draw_index = max(draw['draw_index'] for draw in all_draws) if all_draws else 0

    for num in range(1, MAX_NUMBER + 1):
        num_key = str(num)
        days_since = 999  # Default: very old

        if num_key in hmc_data and 'last_seen' in hmc_data[num_key]:
            # Approximate: use draw indices as proxy for days
            # In real implementation, would use actual date calculation
            for draw in reversed(all_draws):
                if num in draw.get('numbers', []):
                    draws_ago = latest_draw_index - draw['draw_index']
                    days_since = draws_ago * 3  # Approximate: 3 days per draw
                    break

        current_days_since[num] = days_since

    # Calculate weights based on category and recency range distributions
    weights = {}

    for num in range(1, MAX_NUMBER + 1):
        num_key = str(num)
        category = 'cold'

        if num_key in hmc_data:
            category = hmc_data[num_key].get('category', 'cold')

        days_since = current_days_since[num]

        # Find which recency range this number falls into
        category_dist = days_since_data.get(category, {})

        # Find the matching range and get its historical success rate
        weight = 0.5  # Default

        for range_name, min_days, max_days in recency_ranges:
            if min_days <= days_since <= max_days:
                # Higher percentage = more common = higher weight
                percentage = category_dist.get(range_name, 0.0)
                # Normalize to 0-1 range (max typical is ~35%)
                weight = min(1.0, percentage / 35.0)
                break

        weights[num] = weight

    print(f"✓ Long-Term Recency Weights calculated")
    print(f"  Based on {len(recency_ranges)} historical recency ranges")

    return weights


def expand_long_term_features(
    hmc_data: Dict[str, Any],
    statistics_data: Dict[str, Any],
    all_draws: List[Dict[str, Any]]
) -> Dict[int, Dict[str, Any]]:
    """
    Main entry point for calculating all long-term pattern features.

    This is analogous to the freshness features but focuses on stable
    long-term patterns rather than short-term recent performance.

    Args:
        hmc_data: HMC statistics from lotto_trigger_periods.json
        statistics_data: Long-term statistics from lotto_statistics_analysis.json
        all_draws: Draw history

    Returns:
        Dictionary mapping number -> combined long-term feature dictionary
    """
    print("\n" + "="*60)
    print("LONG-TERM PATTERN ANALYSIS")
    print("="*60)

    # Calculate HMC pattern weights
    hmc_features = calculate_long_term_hmc_pattern_weights(hmc_data, statistics_data)

    # Calculate recency weights
    recency_weights = calculate_long_term_recency_weights(hmc_data, statistics_data, all_draws)

    # Combine all features
    combined = {}
    for num in range(1, MAX_NUMBER + 1):
        combined[num] = {
            **hmc_features.get(num, {}),
            'lt_recency_weight': recency_weights.get(num, 0.5)
        }

    print("\n✓ Long-term pattern features calculated for all 47 numbers")
    print("="*60 + "\n")

    return combined
