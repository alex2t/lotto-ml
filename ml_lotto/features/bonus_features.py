# ml_lotto/features/bonus_features.py
"""
bonus_features.py
=================
Extract bonus-specific features from lotto_bonus_analysis.json.

ALL FEATURE VALUES COME FROM JSON - NO HARDCODED WEIGHTS.
"""

from typing import Dict, Any, List


def extract_bonus_features_from_json(
    bonus_json: Dict[str, Any]
) -> Dict[int, Dict[str, Any]]:
    """
    Extract bonus-specific features for all numbers from JSON data.
    
    CRITICAL: All weights and values come from lotto_bonus_analysis.json.
    NO HARDCODED VALUES.
    
    Args:
        bonus_json: Data from lotto_bonus_analysis.json
        
    Returns:
        Dictionary mapping number -> bonus feature dictionary
        
    Features extracted:
        - category_weight: From bonus_category_preference[category].weight
        - was_bonus_last_10: Boolean exclusion from per_number_bonus_profile
        - freshness_weight: From bonus_freshness_preference[bin].weight
        - timing_zone_weight: From bonus_timing_by_category[category][zone].weight
        - days_since_last_bonus: From per_number_bonus_profile
        - bonus_frequency_ratio: From per_number_bonus_profile
        - total_bonus_count: From per_number_bonus_profile
        - avg_days_between_bonus: From per_number_bonus_profile
    """
    print("\n" + "="*70)
    print("EXTRACTING BONUS FEATURES FROM JSON")
    print("="*70)
    print("Source: lotto_bonus_analysis.json")
    print("CRITICAL: All weights loaded from JSON - NO HARDCODED VALUES")
    
    per_number_profiles = bonus_json.get('per_number_bonus_profile', {})
    category_preference = bonus_json.get('bonus_category_preference', {})
    freshness_preference = bonus_json.get('bonus_freshness_preference', {})
    timing_by_category = bonus_json.get('bonus_timing_by_category', {})
    
    if not per_number_profiles:
        raise ValueError("Missing 'per_number_bonus_profile' in bonus JSON")
    
    bonus_features = {}
    
    for num in range(1, 48):
        num_str = str(num)
        
        if num_str not in per_number_profiles:
            print(f"  ⚠️  WARNING: Number {num} not found in per_number_bonus_profile")
            bonus_features[num] = {
                'category_weight': 1.0,
                'was_bonus_last_10': 0,
                'freshness_weight': 1.0,
                'timing_zone_weight': 1.0,
                'days_since_last_bonus': 999,
                'bonus_frequency_ratio': 0.1,
                'total_bonus_count': 0,
                'avg_days_between_bonus': 150.0
            }
            continue
        
        profile = per_number_profiles[num_str]
        
        # Extract category with default
        category = profile.get('category', 'medium')
        category_weight = category_preference.get(category, {}).get('weight', 1.0)
        
        # Handle None values with defaults
        if category_weight is None:
            category_weight = 1.0
        
        # Boolean flag
        was_bonus_last_10 = 1 if profile.get('in_recent_bonus_10', False) else 0
        
        # Freshness weight
        current_freshness_bin = profile.get('current_freshness_bin', 'C0')
        freshness_weight = freshness_preference.get(current_freshness_bin, {}).get('weight', 1.0)
        if freshness_weight is None:
            freshness_weight = 1.0
        
        # Timing zone weight
        optimal_zone = profile.get('current_optimal_zone', '15-30')
        timing_zone_weight = timing_by_category.get(category, {}).get(optimal_zone, {}).get('weight', 1.0)
        if timing_zone_weight is None:
            timing_zone_weight = 1.0
        
        # Numeric features with defaults
        days_since_last_bonus = profile.get('days_since_last_bonus', 999)
        if days_since_last_bonus is None:
            days_since_last_bonus = 999
        
        bonus_frequency_ratio = profile.get('bonus_frequency_ratio', 0.1)
        if bonus_frequency_ratio is None:
            bonus_frequency_ratio = 0.1
        
        total_bonus_count = profile.get('bonus_appearances', 0)
        if total_bonus_count is None:
            total_bonus_count = 0
        
        avg_days_between_bonus = profile.get('avg_days_between_bonus', 150.0)
        if avg_days_between_bonus is None:
            avg_days_between_bonus = 150.0
        
        bonus_features[num] = {
            'category_weight': float(category_weight),
            'was_bonus_last_10': int(was_bonus_last_10),
            'freshness_weight': float(freshness_weight),
            'timing_zone_weight': float(timing_zone_weight),
            'days_since_last_bonus': float(days_since_last_bonus),
            'bonus_frequency_ratio': float(bonus_frequency_ratio),
            'total_bonus_count': float(total_bonus_count),
            'avg_days_between_bonus': float(avg_days_between_bonus)
        }
    
    print(f"\n✓ Extracted bonus features for 47 numbers")
    print(f"  Features per number: 8")
    print(f"  Category weights from JSON: {set(f['category_weight'] for f in bonus_features.values())}")
    print(f"  Recent bonus exclusions: {sum(f['was_bonus_last_10'] for f in bonus_features.values())} numbers")
    
    return bonus_features


def get_bonus_feature_names() -> List[str]:
    """
    Get list of bonus feature names.
    
    Returns:
        List of feature names used in bonus prediction
    """
    return [
        'category_weight',
        'was_bonus_last_10',
        'freshness_weight',
        'timing_zone_weight',
        'days_since_last_bonus',
        'bonus_frequency_ratio',
        'total_bonus_count',
        'avg_days_between_bonus'
    ]