"""
feature_extractor.py
====================
Extracts and processes features from HMC JSON data for ML training.

FIXED: Priority 3 features now use normalized contribution scores
       to avoid penalizing versatile numbers
VERSION: 3.4 (Fixed Priority 3)
"""

import re
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple
from collections import defaultdict, Counter
from ml_lotto.config import MAX_NUMBER, FRESHNESS_JSON_INPUT, FRESHNESS_PATTERN_WEIGHTS, TRAINING_START_DRAW


def get_dynamic_recent_keys(hmc_data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Dynamically identify all unique 'last_N' keys used for recent counts."""
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
    """Calculate the days since each number was last drawn as a bonus ball."""
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


def calculate_was_recent_bonus(
    all_draws: List[Dict[str, Any]],
    lookback_draws: int = 10
) -> Dict[int, int]:
    """
    Binary indicator: Was this number a bonus ball in the last N draws?
    
    CRITICAL FEATURE: 71.28% of draws have ≥1 recent bonus hit!
    """
    recent_draws = all_draws[-lookback_draws:] if len(all_draws) >= lookback_draws else all_draws
    
    recent_bonus_numbers = set()
    for draw in recent_draws:
        bonus_num = draw.get('bonus_number')
        if bonus_num is not None and 1 <= bonus_num <= MAX_NUMBER:
            recent_bonus_numbers.add(bonus_num)
    
    was_recent_bonus = {}
    for num in range(1, MAX_NUMBER + 1):
        was_recent_bonus[num] = 1 if num in recent_bonus_numbers else 0
    
    print(f"✓ Custom feature 'was_recent_bonus' calculated (last {lookback_draws} draws).")
    print(f"  {len(recent_bonus_numbers)} numbers were recent bonus balls: {sorted(recent_bonus_numbers)}")
    
    return was_recent_bonus


def calculate_recency_zone_score(days_since_last: int) -> float:
    """
    Score based on optimal recency windows from trend analysis.
    
    DATA-DRIVEN ZONES:
    - 0-14 days:   40.0% of winners → score 1.0
    - 14-30 days:  31.0% of winners → score 0.78
    - 30-60 days:  21.7% of winners → score 0.54
    - 60-120 days: 7.0% of winners  → score 0.18
    - 120+ days:   0.3% of winners  → score 0.01
    
    Returns:
        Score from 0.0 to 1.0 (higher = better timing)
    """
    if 0 <= days_since_last <= 14:
        return 1.0
    elif 14 < days_since_last <= 30:
        return 0.78
    elif 30 < days_since_last <= 60:
        return 0.54
    elif 60 < days_since_last <= 120:
        return 0.18
    else:
        return 0.01


def calculate_has_consecutive_partner(
    hmc_data: Dict[str, Any],
    dynamic_recent_keys: List[Tuple[str, str]]
) -> Dict[int, int]:
    """
    Binary feature: Does this number have a hot consecutive neighbor?
    
    LOGIC:
    - Number 35 has neighbors 34 and 36
    - If either appeared in last 4 draws → has_consecutive_partner = 1
    - Why: 57% of draws contain consecutive pairs
    
    Returns:
        Dict mapping number -> 1 (has hot neighbor) or 0 (no hot neighbor)
    """
    # Extract recent_4 counts
    recent_4_counts = {}
    recent_4_key = None
    
    for data_key, ml_key in dynamic_recent_keys:
        if ml_key == 'recent_4':
            recent_4_key = data_key
            break
    
    if not recent_4_key:
        print(f"\n⚠️  WARNING: 'recent_4' key not found in dynamic keys.")
        print(f"   Continuing with all consecutive_partner values set to 0.")
        return {num: 0 for num in range(1, MAX_NUMBER + 1)}
    
    # Get recent_4 counts for all numbers
    for num in range(1, MAX_NUMBER + 1):
        num_key = str(num)
        if num_key in hmc_data and 'recent' in hmc_data[num_key]:
            recent_4_counts[num] = hmc_data[num_key]['recent'].get(recent_4_key, 0)
        else:
            recent_4_counts[num] = 0
    
    # Calculate has_consecutive_partner
    has_partner = {}
    
    for num in range(1, MAX_NUMBER + 1):
        left_neighbor = num - 1
        right_neighbor = num + 1
        
        # Check if neighbors are hot (appeared in last 4 draws)
        left_hot = (1 <= left_neighbor <= 47) and (recent_4_counts.get(left_neighbor, 0) >= 1)
        right_hot = (1 <= right_neighbor <= 47) and (recent_4_counts.get(right_neighbor, 0) >= 1)
        
        has_partner[num] = 1 if (left_hot or right_hot) else 0
    
    hot_neighbors = sum(has_partner.values())
    print(f"✓ Custom feature 'has_consecutive_partner' calculated.")
    print(f"  {hot_neighbors}/47 numbers have hot consecutive neighbors")
    
    return has_partner


def calculate_consecutive_pair_affinity(
    consecutive_patterns: Dict[str, Any]
) -> Dict[int, float]:
    """
    Calculate affinity score: How often does this number appear in consecutive pairs?
    
    Uses "all_pairs" data showing historical pair frequencies.
    
    Returns:
        Dict mapping number -> affinity_score (0.0 to 1.0)
        
    Raises:
        ValueError: If consecutive patterns data is missing or invalid
    """
    all_pairs = consecutive_patterns.get('2_consecutive', {}).get('all_pairs', {})
    
    if not all_pairs:
        print(f"\n❌ CRITICAL ERROR: Consecutive pairs data ('all_pairs') is missing.")
        print(f"   This data should be in lotto_odds_results.json under:")
        print(f"   patterns.2_consecutive.all_pairs")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data files.")
        raise ValueError("Cannot calculate consecutive_pair_affinity without 'all_pairs' data")
    
    # Count how many times each number appears in pairs
    pair_counts = defaultdict(int)
    
    for pair_str, count in all_pairs.items():
        parts = pair_str.split('-')
        if len(parts) == 2:
            try:
                num1 = int(parts[0])
                num2 = int(parts[1])
                pair_counts[num1] += count
                pair_counts[num2] += count
            except ValueError:
                continue
    
    # Find max count for normalization
    max_count = max(pair_counts.values()) if pair_counts else 1
    
    # Calculate affinity (normalized to 0-1 scale)
    affinity = {}
    for num in range(1, MAX_NUMBER + 1):
        count = pair_counts.get(num, 0)
        affinity[num] = round(count / max_count, 3) if max_count > 0 else 0.0
    
    high_affinity = sum(1 for v in affinity.values() if v > 0.7)
    print(f"✓ Custom feature 'consecutive_pair_affinity' calculated.")
    print(f"  {high_affinity}/47 numbers have high pair affinity (>0.7)")
    
    return affinity


def calculate_bonus_hit_target_alignment(
    was_recent_bonus_data: Dict[int, int]
) -> Dict[int, float]:
    """
    Score based on helping achieve optimal bonus hit count.
    
    Returns:
        Dict mapping number -> alignment_score (0.0 to 1.0)
    """
    alignment = {}
    
    for num in range(1, MAX_NUMBER + 1):
        if was_recent_bonus_data.get(num, 0) == 1:
            alignment[num] = 0.65
        else:
            alignment[num] = 0.35
    
    return alignment


# ==================== PRIORITY 3 FEATURES (FIXED) ====================

def calculate_odd_even_affinity(
    draw_history_log: Dict[str, Any],
    training_start_draw: int = 100
) -> Dict[int, float]:
    """
    ML FEATURE: Normalized contribution to balanced draws (2-4 odds).
    
    FIXED: Now uses absolute contribution, not conditional probability.
    This prevents penalizing versatile numbers.
    
    Formula:
        score[num] = (times num appeared in balanced draws) / (max any number contributed)
    
    Args:
        draw_history_log: Full draw history with all details
        training_start_draw: Only use draws >= this index for training
        
    Returns:
        Dict mapping number -> normalized contribution score (0.0 to 1.0)
    """
    training_draws = {
        date: draw for date, draw in draw_history_log.items()
        if draw.get('draw_index', 999999) >= training_start_draw
    }
    
    if not training_draws:
        return {num: 0.5 for num in range(1, MAX_NUMBER + 1)}
    
    # Count absolute contributions
    balanced_contribution = defaultdict(int)
    
    for date, draw in training_draws.items():
        winning_details = draw.get('winning_numbers_details', [])
        main_numbers = [w['number'] for w in winning_details[:6]]
        odd_count = sum(1 for n in main_numbers if n % 2 == 1)
        is_balanced = odd_count in [2, 3, 4]
        
        # Only count contributions to balanced draws
        if is_balanced:
            for w in winning_details:
                num = w['number']
                balanced_contribution[num] += 1
    
    # Normalize by max contribution (not by total appearances)
    max_contribution = max(balanced_contribution.values()) if balanced_contribution else 1
    
    affinity = {}
    for num in range(1, MAX_NUMBER + 1):
        contribution = balanced_contribution.get(num, 0)
        # Numbers that never appeared get baseline score (not 0)
        if contribution == 0:
            affinity[num] = 0.3  # Baseline for unknown numbers
        else:
            affinity[num] = round(contribution / max_contribution, 3)
    
    print(f"✓ Calculated 'odd_even_affinity' feature (normalized contribution)")
    print(f"  Max contribution: {max_contribution} balanced draws")
    print(f"  Numbers with high contribution (>0.8): {sum(1 for v in affinity.values() if v > 0.8)}/47")
    return affinity


def calculate_sum_contribution_score(
    draw_history_log: Dict[str, Any],
    training_start_draw: int = 100
) -> Dict[int, float]:
    """
    ML FEATURE: Normalized contribution to typical-sum draws (114-174).
    
    FIXED: Now uses absolute contribution, not conditional probability.
    
    Formula:
        score[num] = (times num appeared in typical-sum draws) / (max any number contributed)
    
    Args:
        draw_history_log: Full draw history with all details
        training_start_draw: Only use draws >= this index for training
        
    Returns:
        Dict mapping number -> normalized contribution score (0.0 to 1.0)
    """
    training_draws = {
        date: draw for date, draw in draw_history_log.items()
        if draw.get('draw_index', 999999) >= training_start_draw
    }
    
    if not training_draws:
        return {num: 0.5 for num in range(1, MAX_NUMBER + 1)}
    
    SUM_MIN, SUM_MAX = 114, 174
    typical_sum_contribution = defaultdict(int)
    
    for date, draw in training_draws.items():
        winning_details = draw.get('winning_numbers_details', [])
        main_numbers = [w['number'] for w in winning_details[:6]]
        draw_sum = sum(main_numbers)
        is_typical = SUM_MIN <= draw_sum <= SUM_MAX
        
        if is_typical:
            for w in winning_details:
                num = w['number']
                typical_sum_contribution[num] += 1
    
    # Normalize by max contribution
    max_contribution = max(typical_sum_contribution.values()) if typical_sum_contribution else 1
    
    score = {}
    for num in range(1, MAX_NUMBER + 1):
        contribution = typical_sum_contribution.get(num, 0)
        if contribution == 0:
            score[num] = 0.3  # Baseline for unknown numbers
        else:
            score[num] = round(contribution / max_contribution, 3)
    
    print(f"✓ Calculated 'sum_contribution_score' feature (normalized contribution)")
    print(f"  Max contribution: {max_contribution} typical-sum draws")
    print(f"  Numbers with high contribution (>0.8): {sum(1 for v in score.values() if v > 0.8)}/47")
    return score


def calculate_range_spread_affinity(
    draw_history_log: Dict[str, Any],
    training_start_draw: int = 100
) -> Dict[int, float]:
    """
    ML FEATURE: Normalized contribution to well-distributed draws.
    
    FIXED: Now uses absolute contribution, not conditional probability.
    
    Formula:
        score[num] = (times num appeared in well-distributed draws) / (max any number contributed)
    
    Args:
        draw_history_log: Full draw history with all details
        training_start_draw: Only use draws >= this index for training
        
    Returns:
        Dict mapping number -> normalized contribution score (0.0 to 1.0)
    """
    training_draws = {
        date: draw for date, draw in draw_history_log.items()
        if draw.get('draw_index', 999999) >= training_start_draw
    }
    
    if not training_draws:
        return {num: 0.5 for num in range(1, MAX_NUMBER + 1)}
    
    RANGES = {
        '1-10': (1, 10), '11-20': (11, 20), '21-30': (21, 30),
        '31-40': (31, 40), '41-47': (41, 47)
    }
    
    well_distributed_contribution = defaultdict(int)
    
    for date, draw in training_draws.items():
        winning_details = draw.get('winning_numbers_details', [])
        main_numbers = [w['number'] for w in winning_details[:6]]
        
        range_counts = defaultdict(int)
        for num in main_numbers:
            for range_name, (low, high) in RANGES.items():
                if low <= num <= high:
                    range_counts[range_name] += 1
                    break
        
        is_well_distributed = True
        for range_name, count in range_counts.items():
            if range_name == '41-47':
                if count > 2:
                    is_well_distributed = False
                    break
            else:
                if count == 0 or count >= 4:
                    is_well_distributed = False
                    break
        
        if is_well_distributed:
            for w in winning_details:
                num = w['number']
                well_distributed_contribution[num] += 1
    
    # Normalize by max contribution
    max_contribution = max(well_distributed_contribution.values()) if well_distributed_contribution else 1
    
    affinity = {}
    for num in range(1, MAX_NUMBER + 1):
        contribution = well_distributed_contribution.get(num, 0)
        if contribution == 0:
            affinity[num] = 0.3  # Baseline for unknown numbers
        else:
            affinity[num] = round(contribution / max_contribution, 3)
    
    print(f"✓ Calculated 'range_spread_affinity' feature (normalized contribution)")
    print(f"  Max contribution: {max_contribution} well-distributed draws")
    print(f"  Numbers with high contribution (>0.8): {sum(1 for v in affinity.values() if v > 0.8)}/47")
    return affinity


# ==================== END PRIORITY 3 FEATURES (FIXED) ====================


def extract_win_bias_ratio_from_history(
    draw_history_log: Dict[str, Any],
    max_number: int
) -> Dict[int, float]:
    """Extract the MOST RECENT win_bias_ratio from draw history."""
    if not draw_history_log:
        print(f"\n❌ CRITICAL ERROR: Draw history log is empty.")
        raise ValueError("Cannot extract win_bias_ratio from empty draw history")
    
    sorted_dates = sorted(
        draw_history_log.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )
    
    if not sorted_dates:
        print(f"\n❌ CRITICAL ERROR: No draws found in history log.")
        raise ValueError("Draw history contains no draws")
    
    latest_date, latest_data = sorted_dates[-1]
    bias_ratios = latest_data.get('all_numbers_bias_ratios', {})
    
    if not bias_ratios:
        print(f"\n❌ CRITICAL ERROR: 'all_numbers_bias_ratios' missing from latest draw.")
        raise ValueError("Latest draw missing required bias ratio data")
    
    result = {}
    for num in range(1, max_number + 1):
        result[num] = bias_ratios.get(num, 1.0)
    
    print(f"✓ Extracted 'win_bias_ratio' from latest draw ({latest_date})")
    return result


def calculate_freshness_category_features(
    hmc_data: Dict[str, Any],
    c_max_threshold: int,
    recent_key: str,
    top_pattern_dist: Dict[int, float]
) -> Dict[int, Dict[str, float]]:
    """Calculate freshness category features for each number dynamically."""
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
    """DEPRECATED: Returns zero scores."""
    return {num: 0.0 for num in range(1, MAX_NUMBER + 1)}


def extract_features_from_hmc_json(
    hmc_data: Dict[str, Any], 
    dynamic_recent_keys: List[Tuple[str, str]],
    days_since_bonus_data: Dict[int, int],
    pattern_score_data: Dict[int, float],
    freshness_features: Dict[int, Dict[str, float]] = None,
    win_bias_ratio_data: Dict[int, float] = None,
    was_recent_bonus_data: Dict[int, int] = None,
    consecutive_patterns: Dict[str, Any] = None,
    draw_history_log: Dict[str, Any] = None,
    training_start_draw: int = 100
) -> Dict[int, Dict[str, Any]]:
    """
    Extract ML features for each number, incorporating ALL custom features.
    
    FIXED: Priority 3 features now use normalized contribution scores
    VERSION: 3.4 - Fixed Priority 3 implementation
    """
    features = {}
    current_timestamp = pd.Timestamp.now()
    ml_feature_names = [ml_key for data_key, ml_key in dynamic_recent_keys]
    
    if freshness_features is None:
        freshness_features = {}
    
    # Calculate Priority 2 features
    print("  Calculating Priority 2 features...")
    has_consecutive_partner_data = calculate_has_consecutive_partner(
        hmc_data,
        dynamic_recent_keys
    )
    
    consecutive_pair_affinity_data = {}
    if consecutive_patterns:
        try:
            consecutive_pair_affinity_data = calculate_consecutive_pair_affinity(
                consecutive_patterns
            )
        except ValueError as e:
            print(f"\n⚠️  Feature extraction stopped due to missing data.")
            raise
    else:
        print(f"\n❌ CRITICAL ERROR: Consecutive patterns data not provided.")
        raise ValueError("Missing consecutive_patterns data - cannot extract features")
    
    bonus_alignment_data = {}
    if was_recent_bonus_data:
        bonus_alignment_data = calculate_bonus_hit_target_alignment(
            was_recent_bonus_data
        )
    else:
        print(f"\n❌ CRITICAL ERROR: was_recent_bonus data not provided.")
        raise ValueError("Missing was_recent_bonus data - cannot extract features")
    
    # Calculate Priority 3 features (FIXED)
    print("  Calculating Priority 3 features (normalized contributions)...")
    
    if draw_history_log:
        odd_even_affinity_data = calculate_odd_even_affinity(
            draw_history_log, training_start_draw
        )
        sum_contribution_data = calculate_sum_contribution_score(
            draw_history_log, training_start_draw
        )
        range_spread_data = calculate_range_spread_affinity(
            draw_history_log, training_start_draw
        )
    else:
        print(f"\n⚠️  WARNING: draw_history_log not provided. Using default values for Priority 3 features.")
        odd_even_affinity_data = {num: 0.5 for num in range(1, MAX_NUMBER + 1)}
        sum_contribution_data = {num: 0.5 for num in range(1, MAX_NUMBER + 1)}
        range_spread_data = {num: 0.5 for num in range(1, MAX_NUMBER + 1)}
    
    print(f"\n✓ Extracting features from HMC data:")
    base_features = ['total_count', 'days_since_last', 'recency_zone_score',
                     'series_total', 'series_recent', 'days_since_bonus', 
                     'win_bias_ratio', 'was_recent_bonus', 'has_consecutive_partner',
                     'consecutive_pair_affinity', 'bonus_hit_target_alignment',
                     'odd_even_affinity', 'sum_contribution_score', 'range_spread_affinity']
    fresh_features_names = sorted([k for k in next(iter(freshness_features.values())).keys() 
                                   if k.startswith('freshness_c') and k.endswith('_weight')]) if freshness_features and next(iter(freshness_features.values())) else []
    
    print(f"  Static features: {base_features}")
    print(f"  Freshness features: {fresh_features_names + ['current_freshness_bin']}")
    print(f"  Dynamic features: {ml_feature_names}")
    
    for num_str in range(1, MAX_NUMBER + 1):
        num = num_str
        num_key = str(num)
        recent_fields = {f: 0 for f in ml_feature_names}
        
        fresh_feat = freshness_features.get(num, {})
        
        # Default features with all priorities
        default_features = {
            'total_count': 0,
            'category': 'cold',
            'days_since_last': 999,
            'recency_zone_score': calculate_recency_zone_score(999),
            'series_total': 0,
            'series_recent': 0,
            'days_since_bonus': days_since_bonus_data.get(num, 999),
            'win_bias_ratio': win_bias_ratio_data.get(num, 1.0) if win_bias_ratio_data else 1.0,
            'was_recent_bonus': was_recent_bonus_data.get(num, 0) if was_recent_bonus_data else 0,
            'has_consecutive_partner': has_consecutive_partner_data.get(num, 0),
            'consecutive_pair_affinity': consecutive_pair_affinity_data.get(num, 0.5),
            'bonus_hit_target_alignment': bonus_alignment_data.get(num, 0.35),
            'odd_even_affinity': odd_even_affinity_data.get(num, 0.5),
            'sum_contribution_score': sum_contribution_data.get(num, 0.5),
            'range_spread_affinity': range_spread_data.get(num, 0.5),
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
        
        if 'last_seen' in num_data:
            try:
                last_date_str = num_data['last_seen'].replace('/', '-')
                last_date = pd.to_datetime(last_date_str)
                days_since = (current_timestamp - last_date).days
            except Exception:
                pass
        
        recent_data = num_data.get('recent', {})
        for data_key, ml_feature_key in dynamic_recent_keys:
            recent_fields[ml_feature_key] = recent_data.get(data_key, 0)
        
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
            'recency_zone_score': calculate_recency_zone_score(days_since),
            'series_total': series_total,
            'series_recent': series_recent,
            'days_since_bonus': days_since_bonus_data.get(num, 999),
            'win_bias_ratio': win_bias_ratio_data.get(num, 1.0) if win_bias_ratio_data else 1.0,
            'was_recent_bonus': was_recent_bonus_data.get(num, 0) if was_recent_bonus_data else 0,
            'has_consecutive_partner': has_consecutive_partner_data.get(num, 0),
            'consecutive_pair_affinity': consecutive_pair_affinity_data.get(num, 0.5),
            'bonus_hit_target_alignment': bonus_alignment_data.get(num, 0.35),
            'odd_even_affinity': odd_even_affinity_data.get(num, 0.5),
            'sum_contribution_score': sum_contribution_data.get(num, 0.5),
            'range_spread_affinity': range_spread_data.get(num, 0.5),
            **fresh_feat,
            **recent_fields,
        }
    
    return features


def get_all_feature_names(features_dict: Dict[int, Dict[str, Any]]) -> List[str]:
    """Get list of all available feature names (excluding 'category')."""
    if not features_dict:
        return []
    
    sample_features = next(iter(features_dict.values()))
    return [key for key in sample_features.keys() if key != 'category']


def expand_feature_selection(feature_spec: Any, all_features: List[str]) -> List[str]:
    """Expand feature specification into actual feature list."""
    
    recent_features = sorted([f for f in all_features if f.startswith('recent_')],
                             key=lambda x: int(x.split('_')[1]))
    
    freshness_weights_features = sorted([f for f in all_features if f.startswith('freshness_c') and f.endswith('_weight')])
                             
    custom_keywords = {
        'ALL': all_features,
        'RECENT_ALL': recent_features,
        'RECENT_SHORT': recent_features[:1] if recent_features else [],
        'RECENT_LONG': recent_features[-1:] if recent_features else [],
        'BONUS_AWARE': ['days_since_bonus'], 
        'FRESHNESS_PATTERN': freshness_weights_features,
        FRESHNESS_PATTERN_WEIGHTS: freshness_weights_features
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