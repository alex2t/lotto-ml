"""
freshness.py
============
Freshness category and pattern-based feature calculations.

Features in this module:
- freshness_c0_weight, freshness_c1_weight, freshness_c2_weight, freshness_c3_weight
- current_freshness_bin
- recency_weighted_pattern_score (deprecated)

All features use data from lotto_7_number_freshness_results.json
"""

from typing import Dict, Any, List
from collections import Counter
from ml_lotto.config import MAX_NUMBER


def calculate_freshness_category_features(
    hmc_data: Dict[str, Any],
    c_max_threshold: int,
    recent_key: str,
    top_pattern_dist: Dict[int, float]
) -> Dict[int, Dict[str, float]]:
    """
    Calculate freshness category features for each number dynamically.
    
    Categorizes each number based on how many times it appeared in recent draws
    (the "freshness" of the number), then assigns pattern weights based on
    historical winning patterns.
    
    Args:
        hmc_data: HMC statistics from lotto_trigger_periods.json
        c_max_threshold: Maximum freshness category (e.g., 3 for C0/C1/C2/C3+)
        recent_key: Key to use for recent counts (e.g., 'last_4')
        top_pattern_dist: Pattern distribution weights from freshness JSON
        
    Returns:
        Dictionary mapping number -> freshness feature dictionary
        Each feature dict contains:
        - freshness_c0_weight, freshness_c1_weight, etc.
        - current_freshness_bin
    """
    number_categories = {}
    category_counts = Counter()
    
    for num in range(1, MAX_NUMBER + 1):
        num_key = str(num)
        recent_count = 0
        
        if num_key in hmc_data and 'recent' in hmc_data[num_key]:
            recent_count = hmc_data[num_key]['recent'].get(recent_key, 0)
        
        if recent_count >= c_max_threshold:
            category = c_max_threshold
        else:
            category = recent_count
        
        number_categories[num] = category
        category_counts[category] += 1
    
    features = {}
    
    print(f"\n✓ Freshness Pattern Analysis (W-1 key: {recent_key}, C_max: {c_max_threshold}):")
    
    bin_names = [f'C{i}' for i in range(c_max_threshold)] + [f'C>={c_max_threshold}']
    print(f"  Target bins: {bin_names}")
    
    for i in range(c_max_threshold + 1):
        name = bin_names[i]
        weight = top_pattern_dist.get(i, 0.0)
        print(f"    {name} weight: {weight*100:.1f}%")
    
    print(f"\n  Current number distribution:")
    for i in range(c_max_threshold + 1):
        print(f"    {bin_names[i]}: {category_counts[i]} numbers")
        
    for num in range(1, MAX_NUMBER + 1):
        current_cat = number_categories[num]
        
        fresh_features = {
            f'freshness_c{i}_weight': 0.0 for i in range(c_max_threshold + 1)
        }
        
        feature_name = f'freshness_c{current_cat}_weight'
        fresh_features[feature_name] = top_pattern_dist.get(current_cat, 0.0)
        
        features[num] = {
            **fresh_features,
            'current_freshness_bin': current_cat
        }
    
    return features


def calculate_recency_weighted_pattern_score(
    all_draws: List[Dict[str, Any]],
    freshness_data: dict, 
    target_window: int = 5, 
    recency_days: int = 60
) -> Dict[int, float]:
    """
    DEPRECATED: Returns zero scores.
    
    This function is kept for backward compatibility but no longer
    performs any calculations. It returns 0.0 for all numbers.
    
    Returns:
        Dictionary mapping number -> 0.0
    """
    return {num: 0.0 for num in range(1, MAX_NUMBER + 1)}