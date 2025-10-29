"""
predictor.py
============
Generates predictions from trained models with DUAL constraints:
1. HMC (Hot/Medium/Cold) - Based on total historical frequency
2. Freshness Pattern (C0/C1/C2/C>=3) - Based on recent activity (last 4 draws)

HYBRID SELECTION: Respects BOTH HMC ratios AND freshness patterns
"""

import numpy as np
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict
from ml_lotto.config import MAX_NUMBER, SHOW_DETAILED_PENALTIES


def get_optimal_pattern_distribution(freshness_data: Dict[str, Any]) -> Tuple[int, int, int, int]:
    """
    Get the optimal C0/C1/C2/C>=3 distribution from freshness data.
    
    Returns the most common pattern, e.g., (3, 3, 1, 0) for C0=3, C1=3, C2=1, C>=3=0
    """
    if not freshness_data or 'distribution_analysis_7_numbers' not in freshness_data:
        return (3, 3, 1, 0)  # Default to most common pattern
    
    top_pattern = freshness_data['distribution_analysis_7_numbers'][0]
    return (top_pattern['C0'], top_pattern['C1'], top_pattern['C2'], top_pattern['C_ge_3'])


def categorize_numbers_by_freshness(features_dict: Dict[int, Dict[str, Any]]) -> Dict[int, int]:
    """
    Categorize each number into C0/C1/C2/C>=3 based on current freshness bin.
    
    Returns:
        Dictionary mapping number -> freshness_category (0, 1, 2, or 3)
    """
    number_categories = {}
    for num in range(1, MAX_NUMBER + 1):
        if num in features_dict:
            number_categories[num] = int(features_dict[num].get('current_freshness_bin', 0))
        else:
            number_categories[num] = 0
    return number_categories


def generate_predictions(models: Dict[str, Any],
                        model_features: Dict[str, List[str]],
                        features_dict: Dict[int, Dict[str, Any]]) -> Dict[str, np.ndarray]:
    """
    Generate predictions from all trained models.
    """
    print("\n" + "="*70)
    print("GENERATING PREDICTIONS")
    print("="*70)
    
    all_probabilities = {}
    
    for model_name, model_data in models.items():
        pipeline = model_data['pipeline']
        features_for_model = model_features[model_name]
        
        # Prepare input data
        X_pred_list = []
        for num in range(1, MAX_NUMBER + 1):
            if num in features_dict:
                feat = features_dict[num]
                record = [feat.get(col, 0) for col in features_for_model]
                X_pred_list.append(record)
        
        X_pred = np.array(X_pred_list)
        
        # Generate probabilities
        probabilities = pipeline.predict_proba(X_pred)[:, 1]
        all_probabilities[model_name] = probabilities
        print(f"  ✓ {model_name} predictions generated")
    
    return all_probabilities


def apply_rank_aware_penalty(probabilities: np.ndarray,
                             penalty_numbers: Set[int],
                             penalty_factor: float) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Apply rank-aware diversity penalties to probabilities.
    """
    adjusted_probs = probabilities.copy()
    penalty_details = []
    
    if not penalty_numbers or penalty_factor <= 0:
        return adjusted_probs, penalty_details
    
    # Create rank mapping
    prob_rank_pairs = sorted(
        [(probabilities[i], i + 1) for i in range(MAX_NUMBER)],
        key=lambda x: x[0],
        reverse=True
    )
    ranks = {num: rank for rank, (_, num) in enumerate(prob_rank_pairs, start=1)}
    
    for num in penalty_numbers:
        if 1 <= num <= MAX_NUMBER:
            rank_weight = 1.0 - (ranks[num] - 1) / (MAX_NUMBER - 1)
            adaptive_penalty = penalty_factor * (0.5 + 0.5 * rank_weight)
            
            original_prob = adjusted_probs[num - 1]
            adjusted_probs[num - 1] *= (1.0 - adaptive_penalty)
            
            penalty_details.append({
                'num': num,
                'rank': ranks[num],
                'penalty_pct': adaptive_penalty * 100,
                'orig_prob': original_prob,
                'new_prob': adjusted_probs[num - 1]
            })
    
    return adjusted_probs, penalty_details


def pick_line_hybrid(
    model_config: Dict[str, Any],
    probabilities: np.ndarray,
    features_dict: Dict[int, Dict[str, Any]],
    number_categories: Dict[int, int],
    target_pattern: Tuple[int, int, int, int],
    penalty_numbers: Set[int] = None
) -> Tuple[List[int], List[Dict[str, Any]], str]:
    """
    HYBRID PICKER: Respects BOTH HMC ratios AND freshness patterns.
    
    Strategy:
    1. Apply diversity penalties
    2. Group numbers by BOTH HMC category AND freshness category
    3. Select from each HMC group, preferring numbers that match target freshness
    4. Fill remaining slots to match freshness pattern
    
    Args:
        model_config: Model configuration with HMC ratios
        probabilities: Model probabilities
        features_dict: Feature data with 'category' (HMC) and 'current_freshness_bin'
        number_categories: Mapping of number -> freshness category
        target_pattern: (C0_count, C1_count, C2_count, C3_count)
        penalty_numbers: Numbers to penalize for diversity
    
    Returns:
        (selected_numbers, penalty_details, pattern_achieved)
    """
    h = model_config['hot_count']
    m = model_config['medium_count']
    c = model_config['cold_count']
    g = model_config['generic_count']
    penalty_factor = model_config['diversity_penalty']
    
    # Apply diversity penalty
    adjusted_probs, penalty_details = apply_rank_aware_penalty(
        probabilities,
        penalty_numbers,
        penalty_factor
    )
    
    # Build dual-categorized pools: {HMC: {freshness: [(prob, num), ...]}}
    pools = {
        'hot': {0: [], 1: [], 2: [], 3: []},
        'medium': {0: [], 1: [], 2: [], 3: []},
        'cold': {0: [], 1: [], 2: [], 3: []}
    }
    
    for num in range(1, MAX_NUMBER + 1):
        if num not in features_dict:
            continue
        
        hmc_cat = features_dict[num].get('category', 'cold')
        fresh_cat = number_categories.get(num, 0)
        prob = adjusted_probs[num - 1]
        
        if hmc_cat in pools:
            pools[hmc_cat][fresh_cat].append((prob, num))
    
    # Sort each pool by probability
    for hmc_cat in pools:
        for fresh_cat in pools[hmc_cat]:
            pools[hmc_cat][fresh_cat].sort(reverse=True)
    
    # Target freshness distribution
    c0_target, c1_target, c2_target, c3_target = target_pattern
    freshness_needed = {0: c0_target, 1: c1_target, 2: c2_target, 3: c3_target}
    
    line = []
    freshness_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    
    # PHASE 1: Pick from HMC categories, prioritizing needed freshness bins
    def pick_from_hmc_pool(hmc_cat, count_needed):
        """Pick 'count_needed' numbers from HMC category, prioritizing target freshness."""
        picked = []
        
        # Sort freshness bins by how much we need them
        freshness_priority = sorted(
            freshness_needed.keys(),
            key=lambda f: freshness_needed[f] - freshness_counts[f],
            reverse=True
        )
        
        for fresh_cat in freshness_priority:
            available = pools[hmc_cat][fresh_cat]
            
            for prob, num in available:
                if num not in line and len(picked) < count_needed:
                    picked.append(num)
                    freshness_counts[fresh_cat] += 1
                    
                if len(picked) >= count_needed:
                    break
            
            if len(picked) >= count_needed:
                break
        
        return picked
    
    # Pick Hot numbers
    line.extend(pick_from_hmc_pool('hot', h))
    
    # Pick Medium numbers
    line.extend(pick_from_hmc_pool('medium', m))
    
    # Pick Cold numbers
    line.extend(pick_from_hmc_pool('cold', c))
    
    # PHASE 2: Fill generic slots, prioritizing freshness gaps
    if g > 0:
        # Collect all remaining candidates
        all_remaining = []
        for hmc_cat in pools:
            for fresh_cat in pools[hmc_cat]:
                for prob, num in pools[hmc_cat][fresh_cat]:
                    if num not in line:
                        # Score by: probability + bonus if we need this freshness category
                        freshness_gap = max(0, freshness_needed[fresh_cat] - freshness_counts[fresh_cat])
                        score = prob * (1.0 + 0.5 * freshness_gap)
                        all_remaining.append((score, prob, num, fresh_cat))
        
        all_remaining.sort(reverse=True)
        
        for score, prob, num, fresh_cat in all_remaining[:g]:
            line.append(num)
            freshness_counts[fresh_cat] += 1
    
    # Build pattern string
    pattern_str = f"C0={freshness_counts[0]}, C1={freshness_counts[1]}, C2={freshness_counts[2]}, C>=3={freshness_counts[3]}"
    
    return sorted(line), penalty_details, pattern_str


def generate_all_picks(
    models: Dict[str, Any],
    all_probabilities: Dict[str, np.ndarray],
    features_dict: Dict[int, Dict[str, Any]],
    freshness_data: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Generate picks from all models with HYBRID HMC + Freshness selection.
    """
    print("\n" + "="*70)
    print("GENERATING HYBRID PICKS (HMC + Freshness Pattern)")
    print("="*70)
    
    # Get optimal pattern distribution
    target_pattern = get_optimal_pattern_distribution(freshness_data)
    print(f"\n✓ Target Freshness Pattern: C0={target_pattern[0]}, C1={target_pattern[1]}, "
          f"C2={target_pattern[2]}, C>=3={target_pattern[3]}")
    print(f"  (Based on most successful historical pattern: 10.92%)")
    
    # Categorize all numbers by current freshness
    number_categories = categorize_numbers_by_freshness(features_dict)
    
    # Show current distribution
    hmc_counts = {'hot': 0, 'medium': 0, 'cold': 0}
    fresh_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    
    for num in range(1, MAX_NUMBER + 1):
        if num in features_dict:
            hmc_counts[features_dict[num].get('category', 'cold')] += 1
            fresh_counts[number_categories.get(num, 0)] += 1
    
    print(f"\n  Available numbers by HMC:")
    print(f"    Hot:    {hmc_counts['hot']} numbers")
    print(f"    Medium: {hmc_counts['medium']} numbers")
    print(f"    Cold:   {hmc_counts['cold']} numbers")
    
    print(f"\n  Available numbers by Freshness:")
    print(f"    C0 (Very Cold): {fresh_counts[0]} numbers")
    print(f"    C1 (Lukewarm):  {fresh_counts[1]} numbers")
    print(f"    C2 (Warm):      {fresh_counts[2]} numbers")
    print(f"    C>=3 (Hot):     {fresh_counts[3]} numbers")
    
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
        
        print(f"\n→ Model {model_idx}: {model_config['name']}")
        print(f"  HMC Ratio: {h}H + {m}M + {c}C + {g}G = {h+m+c+g} numbers")
        print(f"  Freshness Target: {target_pattern[0]}C0 + {target_pattern[1]}C1 + "
              f"{target_pattern[2]}C2 + {target_pattern[3]}C3")
        
        if penalty_numbers and penalty > 0:
            print(f"  Diversity Penalty: {penalty*100:.0f}% on {len(penalty_numbers)} numbers")
        
        # Pick line with hybrid approach
        selected_numbers, penalty_details, achieved_pattern = pick_line_hybrid(
            model_config,
            probabilities,
            features_dict,
            number_categories,
            target_pattern,
            penalty_numbers if penalty_numbers else None
        )
        
        print(f"  Selected: {selected_numbers}")
        print(f"  Achieved Pattern: {achieved_pattern}")
        
        # Display penalty details if enabled
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
        
        # Add current model's numbers to penalty set
        penalty_numbers.update(selected_numbers)
    
    return lines