"""
feature_extractor.py
====================
Extracts and processes features from HMC JSON data for ML training.
Handles dynamic feature detection and feature selection.

NEW APPROACH FOR FRESHNESS PATTERNS:
Instead of scoring individual numbers, we create features that indicate
which freshness category (C0/C1/C2/C>=3) each number belongs to RIGHT NOW.
The ML model learns that certain distributions (e.g., 3xC0 + 3xC1 + 1xC2)
have historically higher success rates.
"""

import re
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple
from collections import defaultdict, Counter
from ml_lotto.config import MAX_NUMBER, FRESHNESS_JSON_INPUT


def get_dynamic_recent_keys(hmc_data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Dynamically identify all unique 'last_N' keys used for recent counts.
    
    Returns:
        List of tuples: (json_key, ml_feature_name)
        Example: [('last_4', 'recent_4'), ('last_6', 'recent_6')]
    """
    all_recent_keys = set()
    for num_key, num_data in hmc_data.items():
        if num_key.isdigit() and 'recent' in num_data:
            all_recent_keys.update(num_data['recent'].keys())
            if len(all_recent_keys) >= 4:
                break
    
    dynamic_keys = []
    for data_key in all_recent_keys:
        match = re.match(r'last_(\d+)$', data_key)
        if match:
            window_size = match.group(1)
            ml_feature_key = f'recent_{window_size}'
            dynamic_keys.append((data_key, ml_feature_key))
    
    dynamic_keys.sort(key=lambda x: int(x[1].split('_')[1]))
    return dynamic_keys


def calculate_days_since_bonus(all_draws: List[Dict[str, Any]]) -> Dict[int, int]:
    """
    Calculate the days since each number was last drawn as a bonus ball.
    """
    now = datetime.now()
    days_since_bonus = {num: 999 for num in range(1, MAX_NUMBER + 1)}
    last_seen_date = {num: None for num in range(1, MAX_NUMBER + 1)}
    
    for draw in reversed(all_draws):
        draw_date = datetime.strptime(draw['date'], "%Y-%m-%d")
        bonus_num = draw.get('bonus_number')
        
        if bonus_num is not None and 1 <= bonus_num <= MAX_NUMBER:
            if last_seen_date[bonus_num] is None:
                last_seen_date[bonus_num] = draw_date

    for num in range(1, MAX_NUMBER + 1):
        if last_seen_date[num] is not None:
            days_since = (now - last_seen_date[num]).days
            days_since_bonus[num] = max(0, days_since)
    
    print(f"✓ Custom feature 'days_since_bonus' calculated.")
    return days_since_bonus


def calculate_freshness_category_features(
    all_draws: List[Dict[str, Any]],
    freshness_data: dict,
    hmc_data: Dict[str, Any],
    target_window: int = 5
) -> Dict[int, Dict[str, float]]:
    """
    Calculate freshness category features for each number.
    
    NEW APPROACH: Instead of a single score, create multiple features:
    - freshness_c0_weight: How much this pattern favors C0 numbers (0.0-1.0)
    - freshness_c1_weight: How much this pattern favors C1 numbers (0.0-1.0)
    - freshness_c2_weight: How much this pattern favors C2 numbers (0.0-1.0)
    - freshness_c3_weight: How much this pattern favors C>=3 numbers (0.0-1.0)
    - current_freshness_category: Which category (0-3) this number is in NOW
    
    The ML model learns: "Pick 3 numbers from C0, 3 from C1, 1 from C2" = winning pattern
    
    Args:
        all_draws: Historical draws
        freshness_data: Pattern distribution data
        hmc_data: Current number statistics
        target_window: Window size for counting (5 = last 4 draws)
    
    Returns:
        Dict mapping number -> {freshness_c0_weight, freshness_c1_weight, ...}
    """
    
    if not freshness_data or 'distribution_analysis_7_numbers' not in freshness_data:
        print("⚠️  Warning: Freshness data not available.")
        return {num: {
            'freshness_c0_weight': 0.0,
            'freshness_c1_weight': 0.0,
            'freshness_c2_weight': 0.0,
            'freshness_c3_weight': 0.0,
            'current_freshness_bin': 0
        } for num in range(1, MAX_NUMBER + 1)}

    # 1. Calculate weights for each category based on top patterns
    analysis_list = freshness_data['distribution_analysis_7_numbers']
    
    # Weight each category by how often it appears in top patterns
    category_weights = defaultdict(float)
    total_weight = 0.0
    
    # Use top 5 patterns weighted by their percentage
    for item in analysis_list[:5]:
        weight = item['percentage']
        category_weights['C0'] += item['C0'] * weight
        category_weights['C1'] += item['C1'] * weight
        category_weights['C2'] += item['C2'] * weight
        category_weights['C3'] += item['C_ge_3'] * weight
        total_weight += weight
    
    # Normalize to get average distribution
    if total_weight > 0:
        for key in category_weights:
            category_weights[key] /= total_weight
    
    # Normalize to 0-1 scale (7 numbers total)
    c0_weight = category_weights['C0'] / 7.0
    c1_weight = category_weights['C1'] / 7.0
    c2_weight = category_weights['C2'] / 7.0
    c3_weight = category_weights['C3'] / 7.0
    
    print(f"\n✓ Freshness Pattern Analysis:")
    print(f"  Top pattern ideal distribution (out of 7 numbers):")
    print(f"    C0 (Very Cold):    {category_weights['C0']:.2f} numbers ({c0_weight*100:.1f}%)")
    print(f"    C1 (Lukewarm):     {category_weights['C1']:.2f} numbers ({c1_weight*100:.1f}%)")
    print(f"    C2 (Warm):         {category_weights['C2']:.2f} numbers ({c2_weight*100:.1f}%)")
    print(f"    C>=3 (Very Hot):   {category_weights['C3']:.2f} numbers ({c3_weight*100:.1f}%)")
    
    # 2. Determine current freshness category for each number
    # Use the 'recent' data from HMC JSON
    number_categories = {}
    recent_key = f"last_{target_window - 1}"
    
    category_counts = Counter()
    
    for num in range(1, MAX_NUMBER + 1):
        num_key = str(num)
        recent_count = 0
        
        if num_key in hmc_data and 'recent' in hmc_data[num_key]:
            recent_count = hmc_data[num_key]['recent'].get(recent_key, 0)
        
        # Categorize based on recent count
        if recent_count == 0:
            category = 0  # C0
        elif recent_count == 1:
            category = 1  # C1
        elif recent_count == 2:
            category = 2  # C2
        else:  # >= 3
            category = 3  # C>=3
        
        number_categories[num] = category
        category_counts[category] += 1
    
    print(f"\n  Current number distribution across freshness bins:")
    print(f"    C0 (count=0): {category_counts[0]} numbers")
    print(f"    C1 (count=1): {category_counts[1]} numbers")
    print(f"    C2 (count=2): {category_counts[2]} numbers")
    print(f"    C>=3 (≥3):    {category_counts[3]} numbers")
    
    # 3. Create features for each number
    features = {}
    for num in range(1, MAX_NUMBER + 1):
        current_cat = number_categories[num]
        
        # Assign weight based on which category this number is in
        # Higher weight = this category is preferred in winning patterns
        features[num] = {
            'freshness_c0_weight': c0_weight if current_cat == 0 else 0.0,
            'freshness_c1_weight': c1_weight if current_cat == 1 else 0.0,
            'freshness_c2_weight': c2_weight if current_cat == 2 else 0.0,
            'freshness_c3_weight': c3_weight if current_cat == 3 else 0.0,
            'current_freshness_bin': current_cat
        }
    
    # Show examples
    print(f"\n  Example number classifications:")
    for cat in range(4):
        examples = [n for n in range(1, MAX_NUMBER + 1) if number_categories[n] == cat][:5]
        cat_name = ['C0 (Very Cold)', 'C1 (Lukewarm)', 'C2 (Warm)', 'C>=3 (Very Hot)'][cat]
        print(f"    {cat_name}: {examples}")
    
    return features


def calculate_recency_weighted_pattern_score(
    all_draws: List[Dict[str, Any]],
    freshness_data: dict, 
    target_window: int = 5, 
    recency_days: int = 60
) -> Dict[int, float]:
    """
    DEPRECATED: Replaced by calculate_freshness_category_features.
    Kept for backward compatibility - returns zero scores.
    """
    print(f"⚠️  Note: pattern_score_recency is deprecated.")
    print(f"    Use freshness_c0/c1/c2/c3_weight features instead.")
    return {num: 0.0 for num in range(1, MAX_NUMBER + 1)}


def extract_features_from_hmc_json(
    hmc_data: Dict[str, Any], 
    dynamic_recent_keys: List[Tuple[str, str]],
    days_since_bonus_data: Dict[int, int],
    pattern_score_data: Dict[int, float],
    freshness_features: Dict[int, Dict[str, float]] = None
) -> Dict[int, Dict[str, Any]]:
    """
    Extract ML features for each number, incorporating all custom features.
    """
    features = {}
    current_timestamp = pd.Timestamp.now()
    ml_feature_names = [ml_key for data_key, ml_key in dynamic_recent_keys]
    
    if freshness_features is None:
        freshness_features = {}
    
    print(f"\n✓ Extracting features from HMC data:")
    base_features = ['total_count', 'days_since_last', 'series_total', 'series_recent', 'days_since_bonus']
    fresh_features = ['freshness_c0_weight', 'freshness_c1_weight', 'freshness_c2_weight', 'freshness_c3_weight', 'current_freshness_bin']
    print(f"  Static features: {base_features}")
    print(f"  Freshness features: {fresh_features}")
    print(f"  Dynamic features: {ml_feature_names}")
    
    for num_str in range(1, MAX_NUMBER + 1):
        num = num_str
        num_key = str(num)
        recent_fields = {f: 0 for f in ml_feature_names}
        
        # Get freshness features for this number
        fresh_feat = freshness_features.get(num, {
            'freshness_c0_weight': 0.0,
            'freshness_c1_weight': 0.0,
            'freshness_c2_weight': 0.0,
            'freshness_c3_weight': 0.0,
            'current_freshness_bin': 0
        })
        
        # Default features
        default_features = {
            'total_count': 0,
            'category': 'cold',
            'days_since_last': 999,
            'series_total': 0,
            'series_recent': 0,
            'days_since_bonus': days_since_bonus_data.get(num, 999),
            **fresh_feat,
            **recent_fields,
        }
        
        if num_key not in hmc_data:
            features[num] = default_features
            continue
        
        num_data = hmc_data[num_key]
        category = num_data.get('category', 'unknown')
        total_count = num_data.get('total_count', 0)
        days_since = 999
        
        # Calculate days since last hit
        if 'last_seen' in num_data:
            try:
                last_date_str = num_data['last_seen'].replace('/', '-')
                last_date = pd.to_datetime(last_date_str)
                days_since = (current_timestamp - last_date).days
            except Exception:
                pass
        
        # Populate dynamic recent counts
        recent_data = num_data.get('recent', {})
        for data_key, ml_feature_key in dynamic_recent_keys:
            recent_fields[ml_feature_key] = recent_data.get(data_key, 0)
        
        # Extract series pattern features
        series_total = 0
        series_recent = 0
        
        if 'series' in num_data and 'series' in num_data['series']:
            series_patterns = num_data['series']['series']
            
            for pattern_name, occurrences in series_patterns.items():
                for occurrence in occurrences:
                    series_total += occurrence.get('count', 0)
                    
                    try:
                        end_date_str = occurrence.get('end_date', '').replace('/', '-')
                        end_date = pd.to_datetime(end_date_str)
                        days_ago = (current_timestamp - end_date).days
                        if days_ago <= 60:
                            series_recent += occurrence.get('count', 0)
                    except:
                        pass
        
        features[num] = {
            'total_count': total_count,
            'category': category,
            'days_since_last': days_since,
            'series_total': series_total,
            'series_recent': series_recent,
            'days_since_bonus': days_since_bonus_data.get(num, 999),
            **fresh_feat,
            **recent_fields,
        }
    
    return features


def get_all_feature_names(features_dict: Dict[int, Dict[str, Any]]) -> List[str]:
    """
    Get list of all available feature names (excluding 'category').
    """
    if not features_dict:
        return []
    
    sample_features = next(iter(features_dict.values()))
    return [key for key in sample_features.keys() if key != 'category']


def expand_feature_selection(feature_spec: Any, all_features: List[str]) -> List[str]:
    """
    Expand feature specification into actual feature list.
    """
    recent_features = sorted([f for f in all_features if f.startswith('recent_')],
                             key=lambda x: int(x.split('_')[1]))
    
    freshness_features = [f for f in all_features if f.startswith('freshness_')]
                             
    custom_keywords = {
        'ALL': all_features,
        'RECENT_ALL': recent_features,
        'RECENT_SHORT': recent_features[:1] if recent_features else [],
        'RECENT_LONG': recent_features[-1:] if recent_features else [],
        'BONUS_AWARE': ['days_since_bonus'], 
        'FRESHNESS_PATTERN': freshness_features  # Now expands to all freshness features
    }

    if isinstance(feature_spec, str):
        return custom_keywords.get(feature_spec, [])

    if isinstance(feature_spec, list):
        expanded = []
        for item in feature_spec:
            if item in custom_keywords:
                expanded.extend(custom_keywords[item])
            else:
                if item in all_features:
                    expanded.append(item)
        return list(set(expanded))

    return []