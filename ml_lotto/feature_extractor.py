"""
feature_extractor.py
====================
Extracts and processes features from HMC JSON data for ML training.
Handles dynamic feature detection and feature selection.

NEW APPROACH FOR FRESHNESS PATTERNS:
- Uses dynamic C_max threshold read from lotto_7_number_freshness_results.json.
- Dynamically creates 'freshness_c0_weight', 'freshness_c1_weight', ..., 'freshness_c{C_max}_weight' features.
"""

import re
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple
from collections import defaultdict, Counter
from ml_lotto.config import MAX_NUMBER, FRESHNESS_JSON_INPUT, FRESHNESS_PATTERN_WEIGHTS, TRAINING_START_DRAW


def get_dynamic_recent_keys(hmc_data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Dynamically identify all unique 'last_N' keys used for recent counts.
    
    Returns:
        List of tuples: (json_key, ml_feature_name)
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

def calculate_win_bias_ratio(all_draws: List[Dict[str, Any]], final_categories: Dict[str, List[int]]) -> Dict[int, float]:
    """
    Calculates the Bias-Adjusted Win Rate (BAWR) for each number based on its HMC category.
    
    BAWR = (Number's Win Rate) / (HMC Category's Average Win Rate)
    
    Args:
        all_draws: All historical draw records (used to define the training set).
        final_categories: Final HMC categorization of all 47 numbers.
        
    Returns:
        Dictionary mapping number -> win_bias_ratio (float)
    """
    
    training_draws = all_draws[:TRAINING_START_DRAW]
    num_training_draws = len(training_draws)
    
    if num_training_draws == 0:
        print("Warning: No training draws available. Win bias ratio set to 1.0.")
        return {num: 1.0 for num in range(1, MAX_NUMBER + 1)}
        
    # 1. Calculate individual number wins in the training set
    individual_wins = defaultdict(int)
    for draw in training_draws:
        # NOTE: Only count main numbers (first 6) for true win rate
        for number in draw['numbers'][:6]:
            individual_wins[number] += 1
            
    # 2. Map numbers to their current category
    num_to_category = {}
    for cat_name, num_list in final_categories.items():
        # Clean the category name (e.g., 'hot_numbers' -> 'hot')
        category = cat_name.replace('_numbers', '')
        for num in num_list:
            num_to_category[num] = category
            
    # 3. Calculate category average win rates
    category_win_totals = defaultdict(int)
    category_number_counts = defaultdict(int)
    
    for num in range(1, MAX_NUMBER + 1):
        category = num_to_category.get(num, 'cold')
        category_win_totals[category] += individual_wins[num]
        category_number_counts[category] += 1
        
    category_avg_win_rates = {}
    for category in category_win_totals:
        if category_number_counts[category] > 0:
            # Average wins per number in that category
            category_avg_win_rates[category] = category_win_totals[category] / category_number_counts[category]
        else:
            category_avg_win_rates[category] = 0.0

    # 4. Calculate Bias-Adjusted Win Ratio (BAWR)
    win_bias_ratios = {}
    
    # Calculate overall average win rate for normalization purposes if needed
    overall_avg_win_rate = sum(individual_wins.values()) / (MAX_NUMBER * num_training_draws)
    
    for num in range(1, MAX_NUMBER + 1):
        category = num_to_category.get(num, 'cold')
        num_wins = individual_wins[num]
        
        # Win Rate of this number
        num_win_rate = num_wins / num_training_draws
        
        # Average Win Rate for its group
        avg_group_rate = category_avg_win_rates.get(category, overall_avg_win_rate)
        
        if avg_group_rate > 0:
            # Ratio: >1.0 means overperforming its group
            win_bias_ratios[num] = round(num_win_rate / avg_group_rate, 4)
        else:
            # If the entire group has zero wins (highly unlikely), treat as 1.0 (neutral)
            win_bias_ratios[num] = 1.0

    print(f"✓ Custom feature 'win_bias_ratio' calculated based on {num_training_draws} draws.")
    print(f"  Example: Hot avg={category_avg_win_rates.get('hot', 0):.2f}, Cold avg={category_avg_win_rates.get('cold', 0):.2f}")

    return win_bias_ratios

def calculate_freshness_category_features(
    hmc_data: Dict[str, Any],
    c_max_threshold: int,
    recent_key: str,
    top_pattern_dist: Dict[int, float]
) -> Dict[int, Dict[str, float]]:
    """
    Calculate freshness category features for each number dynamically.
    
    Args:
        hmc_data: Current number statistics
        c_max_threshold: The dynamic threshold for the final bin (e.g., 2)
        recent_key: The dynamic recent count key (e.g., 'last_4')
        top_pattern_dist: {bin_index (0 to C_max): normalized_weight (0.0-1.0)}
        
    Returns:
        Dict mapping number -> {freshness_c0_weight, ..., current_freshness_bin}
    """
    
    # 1. Determine current freshness bin for each number
    number_categories = {}
    category_counts = Counter()
    
    for num in range(1, MAX_NUMBER + 1):
        num_key = str(num)
        recent_count = 0
        
        if num_key in hmc_data and 'recent' in hmc_data[num_key]:
            recent_count = hmc_data[num_key]['recent'].get(recent_key, 0)
        
        # Categorize based on C_max threshold
        if recent_count >= c_max_threshold:
            category = c_max_threshold # Final bin index
        else:
            category = recent_count # Exact count (0, 1, ..., C_max-1)
        
        number_categories[num] = category
        category_counts[category] += 1
    
    # 2. Create features based on dynamic weights
    features = {}
    
    print(f"\n✓ Freshness Pattern Analysis (W-1 key: {recent_key}, C_max: {c_max_threshold}):")
    
    # Dynamically generate the list of feature names for printing
    bin_names = [f'C{i}' for i in range(c_max_threshold)] + [f'C>={c_max_threshold}']
    print(f"  Target bins: {bin_names}")
    
    # Print weights for documentation
    for i in range(c_max_threshold + 1):
        name = bin_names[i]
        weight = top_pattern_dist.get(i, 0.0)
        print(f"    {name} weight: {weight*100:.1f}% (Ideal draw composition)")
    
    print(f"\n  Current number distribution across freshness bins:")
    for i in range(c_max_threshold + 1):
        print(f"    {bin_names[i]}: {category_counts[i]} numbers")
        
    for num in range(1, MAX_NUMBER + 1):
        current_cat = number_categories[num]
        
        # Initialize features dynamically
        fresh_features = {
            f'freshness_c{i}_weight': 0.0 for i in range(c_max_threshold + 1)
        }
        
        # Assign weight based on which category this number is in
        # The feature name uses the bin index (0, 1, ..., C_max)
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
    DEPRECATED: Replaced by calculate_freshness_category_features.
    Kept for backward compatibility - returns zero scores.
    """
    print(f"⚠️  Note: pattern_score_recency is deprecated.")
    print(f"    Use freshness_cX_weight features instead.")
    return {num: 0.0 for num in range(1, MAX_NUMBER + 1)}


def extract_features_from_hmc_json(
    hmc_data: Dict[str, Any], 
    dynamic_recent_keys: List[Tuple[str, str]],
    days_since_bonus_data: Dict[int, int],
    pattern_score_data: Dict[int, float],
    freshness_features: Dict[int, Dict[str, float]] = None,
    # ADDED NEW FEATURE DATA
    win_bias_ratio_data: Dict[int, float] = None
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
    base_features = ['total_count', 'days_since_last', 'series_total', 'series_recent', 'days_since_bonus', 'win_bias_ratio']
    fresh_features_names = sorted([k for k in next(iter(freshness_features.values())).keys() if k.startswith('freshness_c') and k.endswith('_weight')]) if freshness_features and next(iter(freshness_features.values())) else []
    
    print(f"  Static features: {base_features}")
    print(f"  Freshness features: {fresh_features_names + ['current_freshness_bin']}")
    print(f"  Dynamic features: {ml_feature_names}")
    
    for num_str in range(1, MAX_NUMBER + 1):
        num = num_str
        num_key = str(num)
        recent_fields = {f: 0 for f in ml_feature_names}
        
        # Get freshness features for this number
        fresh_feat = freshness_features.get(num, {})
        
        # Default features
        default_features = {
            'total_count': 0,
            'category': 'cold',
            'days_since_last': 999,
            'series_total': 0,
            'series_recent': 0,
            'days_since_bonus': days_since_bonus_data.get(num, 999),
            # ADDED WIN BIAS RATIO DEFAULT
            'win_bias_ratio': win_bias_ratio_data.get(num, 1.0) if win_bias_ratio_data else 1.0,
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
            # ADDED WIN BIAS RATIO
            'win_bias_ratio': win_bias_ratio_data.get(num, 1.0) if win_bias_ratio_data else 1.0,
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
    Handles the dynamic FRESHNESS_PATTERN_WEIGHTS keyword.
    """
    
    recent_features = sorted([f for f in all_features if f.startswith('recent_')],
                             key=lambda x: int(x.split('_')[1]))
    
    freshness_weights_features = sorted([f for f in all_features if f.startswith('freshness_c') and f.endswith('_weight')])
                             
    custom_keywords = {
        'ALL': all_features,
        'RECENT_ALL': recent_features,
        'RECENT_SHORT': recent_features[:1] if recent_features else [],
        'RECENT_LONG': recent_features[-1:] if recent_features else [],
        'BONUS_AWARE': ['days_since_bonus'], 
        'FRESHNESS_PATTERN': freshness_weights_features, # Use new dynamic list
        FRESHNESS_PATTERN_WEIGHTS: freshness_weights_features # Use dynamic list for keyword
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