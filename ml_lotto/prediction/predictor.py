# ml_lotto/prediction/predictor.py
"""
predictor.py
============
Main prediction orchestration: generates predictions and picks from trained models.

UPDATED: v3.6 - Modified for 5 main numbers (bonus assigned separately)
"""

import numpy as np
from typing import Dict, Any, List
from ml_lotto.config import MAX_NUMBER, SHOW_DETAILED_PENALTIES
from ml_lotto.prediction.penalties import apply_rank_aware_penalty
from ml_lotto.prediction.constraints import (
    get_optimal_pattern_distribution,
    categorize_numbers_by_freshness,
    build_dual_categorized_pools,
    display_available_numbers
)
from ml_lotto.prediction.selection import pick_line_hybrid
from ml_lotto.prediction.filters import (
    FILTERS_AVAILABLE,
    get_filter_statistics
)


def generate_predictions(
    models: Dict[str, Any],
    model_features: Dict[str, List[str]],
    features_dict: Dict[int, Dict[str, Any]]
) -> Dict[str, np.ndarray]:
    """
    Generate predictions from all trained models.
    
    Args:
        models: Dictionary of trained model pipelines and configs
        model_features: Feature names used by each model
        features_dict: Current feature values for all numbers
        
    Returns:
        Dictionary mapping model_name -> probability_array
    """
    print("\n" + "="*70)
    print("GENERATING MAIN NUMBER PREDICTIONS")
    print("="*70)
    
    all_probabilities = {}
    
    for model_name, model_data in models.items():
        pipeline = model_data['pipeline']
        features_for_model = model_features[model_name]
        
        X_pred_list = []
        for num in range(1, MAX_NUMBER + 1):
            if num in features_dict:
                feat = features_dict[num]
                record = [feat.get(col, 0) for col in features_for_model]
                X_pred_list.append(record)
        
        X_pred = np.array(X_pred_list)
        
        probabilities = pipeline.predict_proba(X_pred)[:, 1]
        all_probabilities[model_name] = probabilities
        print(f"  ✓ {model_name} predictions generated")
    
    return all_probabilities


def generate_all_picks(
    models: Dict[str, Any],
    all_probabilities: Dict[str, np.ndarray],
    features_dict: Dict[int, Dict[str, Any]],
    freshness_data: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Generate 5 MAIN NUMBER picks from all models (bonus assigned separately).
    
    Args:
        models: Trained model pipelines and configs
        all_probabilities: Predicted probabilities from each model
        features_dict: Current feature values for all numbers
        freshness_data: Freshness pattern configuration from JSON
        
    Returns:
        List of pick lines with metadata (5 main numbers each)
        
    UPDATED v3.6: Picks 5 main numbers instead of 6
    """
    print("\n" + "="*70)
    print("GENERATING 5 MAIN NUMBER PICKS (Bonus Assigned Separately)")
    print("="*70)
    
    if FILTERS_AVAILABLE:
        filter_stats = get_filter_statistics()
        print("\n📋 PHASE 1 FILTERS ACTIVE:")
        print("  1️⃣  Odd/Even Balance Filter")
        print(f"     - {filter_stats['odd_even_filter']['description']}")
        print(f"     - Expected elimination: {filter_stats['odd_even_filter']['expected_elimination']}")
        
        print("  2️⃣  Sum Constraint Filter")
        print(f"     - {filter_stats['sum_constraint']['description']}")
        print(f"     - Expected elimination: {filter_stats['sum_constraint']['expected_elimination']}")
        
        print("  3️⃣  Range Distribution Filter")
        print(f"     - {filter_stats['range_distribution']['description']}")
        print(f"     - Expected elimination: {filter_stats['range_distribution']['expected_elimination']}")
        
        print(f"\n  📊 Combined Impact: {filter_stats['combined_impact']['total_elimination']}")
    else:
        print("\n⚠️  Phase 1 filters not available (running without post-generation validation)")
    
    c_max_threshold = freshness_data.get('c_max_threshold', 3) if freshness_data else 3
    
    target_pattern = get_optimal_pattern_distribution(freshness_data, c_max_threshold)
    
    pattern_display_parts = []
    for i in sorted(target_pattern.keys()):
        if i < c_max_threshold:
            pattern_display_parts.append(f"C{i}={target_pattern[i]}")
        else:
            pattern_display_parts.append(f"C>= {i}={target_pattern[i]}")
    
    print(f"\n✓ Target Freshness Pattern (for 7 numbers): {', '.join(pattern_display_parts)}")
    print(f"  NOTE: Picking 5 main numbers, so pattern will be adjusted proportionally")
    
    number_categories = categorize_numbers_by_freshness(features_dict)
    
    display_available_numbers(features_dict, number_categories, c_max_threshold)
    
    lines = []
    penalty_numbers = set()
    
    for model_idx, (model_name, model_data) in enumerate(models.items(), 1):
        model_config = model_data['config']
        probabilities = all_probabilities[model_name]
        
        h = model_config['hot_count']
        m = model_config['medium_count']
        c = model_config['cold_count']
        g = model_config['generic_count']
        penalty = model_config['diversity_penalty']
        
        total_picks = h + m + c + g
        if total_picks != 5:
            print(f"\n⚠️  WARNING: Model {model_idx} configured for {total_picks} numbers, adjusting to 5")
            if total_picks > 5:
                while h + m + c + g > 5:
                    if g > 0:
                        g -= 1
                    elif c > 0:
                        c -= 1
                    elif m > 0:
                        m -= 1
                    elif h > 0:
                        h -= 1
            else:
                g += (5 - total_picks)
        
        print(f"\n→ Model {model_idx}: {model_config['name']}")
        print(f"  HMC Ratio: {h}H + {m}M + {c}C + {g}G = {h+m+c+g} numbers")
        
        if penalty_numbers and penalty > 0:
            print(f"  Diversity Penalty: {penalty*100:.0f}% on {len(penalty_numbers)} numbers")
        
        adjusted_probs, penalty_details = apply_rank_aware_penalty(
            probabilities,
            penalty_numbers if penalty_numbers else set(),
            penalty
        )
        
        pools = build_dual_categorized_pools(
            features_dict,
            number_categories,
            adjusted_probs
        )
        
        model_config_adjusted = model_config.copy()
        model_config_adjusted['hot_count'] = h
        model_config_adjusted['medium_count'] = m
        model_config_adjusted['cold_count'] = c
        model_config_adjusted['generic_count'] = g
        
        selected_numbers, _, achieved_pattern = pick_line_hybrid(
            model_config_adjusted,
            probabilities,
            features_dict,
            number_categories,
            target_pattern,
            pools,
            penalty_numbers if penalty_numbers else set()
        )
        
        print(f"  Selected: {selected_numbers}")
        print(f"  Achieved Pattern: {achieved_pattern}")
        
        if SHOW_DETAILED_PENALTIES and penalty_details:
            print(f"  Rank-aware penalties applied:")
            penalty_details.sort(key=lambda x: x['rank'])
            for detail in penalty_details[:3]:
                print(f"    #{detail['num']} (Rank {detail['rank']}): "
                      f"{detail['penalty_pct']:.1f}% penalty")
        
        lines.append({
            'model_name': model_config['name'],
            'model_index': model_idx,
            'config_str': f"{h}H-{m}M-{c}C+{g}G | {achieved_pattern}",
            'numbers': selected_numbers,
            'description': model_config['description']
        })
        
        penalty_numbers.update(selected_numbers)
    
    return lines