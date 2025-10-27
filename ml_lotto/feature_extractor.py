"""
feature_extractor.py
====================
Extracts and processes features from HMC JSON data for ML training.
Handles dynamic feature detection and feature selection.
"""

import re
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple
from ml_lotto.config import MAX_NUMBER


def get_dynamic_recent_keys(hmc_data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Dynamically identify all unique 'last_N' keys used for recent counts.
    
    Returns:
        List of tuples: (json_key, ml_feature_name)
        Example: [('last_4', 'recent_4'), ('last_6', 'recent_6')]
    """
    all_recent_keys = set()
    # Iterate over sample number data to find all 'last_N' keys
    for num_key, num_data in hmc_data.items():
        if num_key.isdigit() and 'recent' in num_data:
            all_recent_keys.update(num_data['recent'].keys())
            if len(all_recent_keys) >= 4: # Optimization: Stop after finding enough keys
                break
    
    dynamic_keys = []
    for data_key in all_recent_keys:
        match = re.match(r'last_(\d+)$', data_key)
        if match:
            window_size = match.group(1)
            ml_feature_key = f'recent_{window_size}'
            dynamic_keys.append((data_key, ml_feature_key))
    
    # Sort by window size (smallest to largest)
    dynamic_keys.sort(key=lambda x: int(x[1].split('_')[1]))
    return dynamic_keys


def calculate_days_since_bonus(all_draws: List[Dict[str, Any]]) -> Dict[int, int]:
    """
    Calculate the days since each number was last drawn as a bonus ball.
    
    NEW FEATURE: days_since_bonus
    
    Args:
        all_draws: List of draw dictionaries (from lotto_draw_history.json)
    
    Returns:
        Dictionary mapping number to days since it was the bonus ball.
    """
    now = datetime.now()
    days_since_bonus = {num: 999 for num in range(1, MAX_NUMBER + 1)}
    last_seen_date = {num: None for num in range(1, MAX_NUMBER + 1)}
    
    # Find the most recent date a number was drawn as a bonus ball
    for draw in reversed(all_draws):
        draw_date = datetime.strptime(draw['date'], "%Y-%m-%d")
        bonus_num = draw.get('bonus_number')
        
        if bonus_num is not None and 1 <= bonus_num <= MAX_NUMBER:
            # Only update if we haven't seen it more recently
            if last_seen_date[bonus_num] is None:
                last_seen_date[bonus_num] = draw_date

    # Calculate days since that date
    for num in range(1, MAX_NUMBER + 1):
        if last_seen_date[num] is not None:
            days_since = (now - last_seen_date[num]).days
            days_since_bonus[num] = max(0, days_since)
    
    print(f"✓ Custom feature 'days_since_bonus' calculated based on draw history.")
    return days_since_bonus


def extract_features_from_hmc_json(hmc_data: Dict[str, Any], 
                                   dynamic_recent_keys: List[Tuple[str, str]],
                                   days_since_bonus_data: Dict[int, int]) -> Dict[int, Dict[str, Any]]:
    """
    Extract ML features for each number, incorporating the new calculated feature.
    """
    features = {}
    # Use Pandas for easy date handling, assuming 'now' is the date of prediction
    current_timestamp = pd.Timestamp.now()
    ml_feature_names = [ml_key for data_key, ml_key in dynamic_recent_keys]
    
    print(f"✓ Extracting features from HMC data:")
    print(f"  Static features: ['total_count', 'days_since_last', 'series_total', 'series_recent', 'days_since_bonus']")
    print(f"  Dynamic features: {ml_feature_names}")
    
    for num_str in range(1, MAX_NUMBER + 1):
        num = num_str
        num_key = str(num)
        recent_fields = {f: 0 for f in ml_feature_names}
        
        # Default features for missing number or fallback
        default_features = {
            'total_count': 0,
            'category': 'cold',
            'days_since_last': 999,
            'series_total': 0,
            'series_recent': 0,
            'days_since_bonus': days_since_bonus_data.get(num, 999), # Add new feature
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
                # Assuming 'last_seen' is in YYYY/MM/DD or similar format
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
                # Count total occurrences across all patterns
                for occurrence in occurrences:
                    series_total += occurrence.get('count', 0)
                    
                    # Check if pattern is recent (within last 60 days)
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
            'days_since_bonus': days_since_bonus_data.get(num, 999), # Add new feature
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
    # Exclude 'category' as it's used for number selection, not ML training
    return [key for key in sample_features.keys() if key != 'category']


def expand_feature_selection(feature_spec: Any, all_features: List[str]) -> List[str]:
    """
    Expand feature specification into actual feature list.
    """
    # Define custom feature keywords mapping
    recent_features = sorted([f for f in all_features if f.startswith('recent_')],
                             key=lambda x: int(x.split('_')[1]))
                             
    custom_keywords = {
        'ALL': all_features,
        'RECENT_ALL': recent_features,
        'RECENT_SHORT': recent_features[:1],
        'RECENT_LONG': recent_features[-1:],
        'BONUS_AWARE': ['days_since_bonus'] # New keyword for new feature
    }

    # If it's a string keyword
    if isinstance(feature_spec, str):
        return custom_keywords.get(feature_spec, [])

    # If it's a list, process it
    if isinstance(feature_spec, list):
        expanded = []
        for item in feature_spec:
            if item in custom_keywords:
                expanded.extend(custom_keywords[item])
            else:
                if item in all_features:
                    expanded.append(item)
        return list(set(expanded))  # Remove duplicates

    return []