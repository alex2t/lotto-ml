"""
predictor.py
============
Generates predictions from trained models with DUAL constraints:
1. HMC (Hot/Medium/Cold) - Based on total historical frequency
2. Freshness Pattern (C0/C1/C2/C>=X) - Based on recent activity
3. Phase 1 Filters - Odd/Even, Sum, Range validation

UPDATED: v3.3 - Added Phase 1 post-generation filters
"""

import numpy as np
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict
from ml_lotto.config import MAX_NUMBER, SHOW_DETAILED_PENALTIES


# ==================== PHASE 1 FILTER IMPORTS ====================
# Import filter functions from predictor_filters module
try:
   
    FILTERS_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: predictor_filters module not found. Phase 1 filters disabled.")
    FILTERS_AVAILABLE = False
    
    # Dummy functions if filters not available
    def validate_line(numbers):
        return (True, [])
    
    def rebalance_line(numbers, probabilities, features_dict, max_iterations=3):
        return numbers
    
    def get_filter_statistics():
        return {}


def get_optimal_pattern_distribution(freshness_data: Dict[str, Any], c_max_threshold: int) -> Dict[int, int]:
    """
    Get the optimal C0/C1/.../C>=X distribution from freshness data dynamically.
    
    Args:
        freshness_data: Raw JSON data from lotto_7_number_freshness_results.json
        c_max_threshold: The dynamic threshold (e.g., 2)
        
    Returns:
        Dictionary mapping bin_index (0 to C_max) -> expected_count (e.g., {0: 3, 1: 3, 2: 1})
    """
    if not freshness_data or 'distribution_analysis_7_numbers' not in freshness_data:
        # Default to a generic balanced pattern for 7 numbers
        print("Warning: Freshness data empty. Using default pattern (4x C0/C1, 2x C2, 1x C3+).")
        return {0: 3, 1: 2, 2: 1, 3: 1} # Max C_max=3 for default pattern
    
    top_pattern_data = freshness_data['distribution_analysis_7_numbers'][0]
    
    # The structure of the top pattern is already dynamic due to dynamic binning
    target_dist = {}
    for i in range(c_max_threshold + 1):
        if i < c_max_threshold:
            # C0, C1, ..., C_max-1 bins
            count_key = f'C{i}'
        else:
            # C_max bin (C>=C_max)
            count_key = f'C_GE_{c_max_threshold}'
        
        target_dist[i] = top_pattern_data.get(count_key, 0)
        
    return target_dist


def categorize_numbers_by_freshness(features_dict: Dict[int, Dict[str, Any]]) -> Dict[int, int]:
    """
    Categorize each number into freshness bin (0 to C_max) based on the current feature.
    
    Returns:
        Dictionary mapping number -> freshness_category (0, 1, ..., C_max)
    """
    number_categories = {}
    for num in range(1, MAX_NUMBER + 1):
        if num in features_dict:
            # The 'current_freshness_bin' feature already holds the dynamic bin index (0 to C_max)
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
                # Ensure we use the exact feature set the model was trained on
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
            # Gaussian penalty logic (simplified here)
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
    target_pattern: Dict[int, int], # Dynamic target: {bin_index: count}
    penalty_numbers: Set[int] = None
) -> Tuple[List[int], List[Dict[str, Any]], str]:
    """
    HYBRID PICKER: Respects BOTH HMC ratios AND freshness patterns dynamically.
    
    UPDATED v3.3: Now includes Phase 1 filter validation and auto-correction
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
    
    # Get max bin index for initialization
    max_fresh_bin = max(target_pattern.keys()) if target_pattern else 0
    
    # Build dual-categorized pools: {HMC: {freshness: [(prob, num), ...]}}
    pools = {
        'hot': defaultdict(list),
        'medium': defaultdict(list),
        'cold': defaultdict(list)
    }
    
    for num in range(1, MAX_NUMBER + 1):
        if num not in features_dict:
            continue
        
        hmc_cat = features_dict[num].get('category', 'cold')
        # Use the dynamic bin index (0 to C_max)
        fresh_cat = number_categories.get(num, 0)
        prob = adjusted_probs[num - 1]
        
        if hmc_cat in pools:
            pools[hmc_cat][fresh_cat].append((prob, num))
    
    # Sort each pool by probability
    for hmc_cat in pools:
        for fresh_cat in pools[hmc_cat]:
            pools[hmc_cat][fresh_cat].sort(reverse=True)
    
    # Target freshness distribution
    freshness_needed = target_pattern.copy()
    
    # Track results
    line = []
    freshness_counts = defaultdict(int)
    
    # PHASE 1: Pick from HMC categories, prioritizing needed freshness bins
    def pick_from_hmc_pool(hmc_cat, count_needed):
        """Pick 'count_needed' numbers from HMC category, prioritizing target freshness."""
        picked = []
        
        # Sort freshness bins by how much we need them (gap)
        freshness_priority = sorted(
            freshness_needed.keys(),
            key=lambda f: freshness_needed[f] - freshness_counts[f],
            reverse=True
        )
        
        for fresh_cat in freshness_priority:
            available = pools[hmc_cat].get(fresh_cat, [])
            
            for prob, num in available:
                # Only pick if number hasn't been picked yet
                if num not in line and len(picked) < count_needed:
                    picked.append(num)
                    freshness_counts[fresh_cat] += 1
                    
                if len(picked) >= count_needed:
                    break
            
            if len(picked) >= count_needed:
                break
        
        return picked
    
    # Pick Hot, Medium, Cold numbers
    line.extend(pick_from_hmc_pool('hot', h))
    line.extend(pick_from_hmc_pool('medium', m))
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
    
    # Build pattern string dynamically
    pattern_parts = []
    # Loop over all possible bin indices from 0 up to max_fresh_bin
    for i in range(max_fresh_bin + 1):
        if i < max_fresh_bin:
            pattern_parts.append(f"C{i}={freshness_counts[i]}")
        else:
            pattern_parts.append(f"C_GE_{max_fresh_bin}={freshness_counts[i]}")
            
    pattern_str = ", ".join(pattern_parts)
    
    # ==================== PHASE 1 FILTER VALIDATION (NEW v3.3) ====================
    sorted_line = sorted(line)
    
    if FILTERS_AVAILABLE:
        # Check if line passes all filters
        is_valid, failures = validate_line(sorted_line)
        
        if not is_valid:
            # Line failed validation, attempt to fix it
            print(f"  ⚠️  Line failed filters: {', '.join(failures)}")
            print(f"     Original: {sorted_line}")
            
            # Attempt rebalancing
            rebalanced_line = rebalance_line(
                sorted_line,
                probabilities,
                features_dict,
                max_iterations=3
            )
            
            # Check if rebalancing worked
            is_valid_after, failures_after = validate_line(rebalanced_line)
            
            if is_valid_after:
                print(f"     ✓ Fixed: {rebalanced_line}")
                sorted_line = rebalanced_line
            else:
                print(f"     ⚠️  Partial fix: {rebalanced_line} (still fails: {', '.join(failures_after)})")
                # Use rebalanced version even if not perfect (it's better than original)
                sorted_line = rebalanced_line
        else:
            print(f"  ✓ Line passed all filters")
    
    # ==================== END PHASE 1 FILTER VALIDATION ====================
    
    return sorted_line, penalty_details, pattern_str


def generate_all_picks(
    models: Dict[str, Any],
    all_probabilities: Dict[str, np.ndarray],
    features_dict: Dict[int, Dict[str, Any]],
    freshness_data: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Generate picks from all models with HYBRID HMC + Freshness selection.
    
    UPDATED v3.3: Now displays Phase 1 filter statistics
    """
    print("\n" + "="*70)
    print("GENERATING HYBRID PICKS (HMC + Freshness Pattern)")
    print("="*70)
    
    # ==================== PHASE 1 FILTER STATISTICS (NEW v3.3) ====================
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
        print("\n⚠️  Phase 1 filters not available (predictor_filters.py not found)")
    # ==================== END PHASE 1 STATISTICS ====================
    
    # Determine the C_max threshold from the loaded data
    c_max_threshold = freshness_data.get('c_max_threshold', 3)
    
    # Get optimal pattern distribution dynamically
    target_pattern = get_optimal_pattern_distribution(freshness_data, c_max_threshold)
    
    # Build target pattern display string
    pattern_display_parts = []
    for i in sorted(target_pattern.keys()):
        if i < c_max_threshold:
            pattern_display_parts.append(f"C{i}={target_pattern[i]}")
        else:
            pattern_display_parts.append(f"C>= {i}={target_pattern[i]}")
    
    print(f"\n✓ Target Freshness Pattern: {', '.join(pattern_display_parts)}")
    
    # Categorize all numbers by current freshness
    number_categories = categorize_numbers_by_freshness(features_dict)
    
    # Show current distribution
    hmc_counts = {'hot': 0, 'medium': 0, 'cold': 0}
    fresh_counts = defaultdict(int)
    
    for num in range(1, MAX_NUMBER + 1):
        if num in features_dict:
            hmc_counts[features_dict[num].get('category', 'cold')] += 1
            fresh_counts[number_categories.get(num, 0)] += 1
    
    print(f"\n  Available numbers by HMC:")
    print(f"    Hot:    {hmc_counts['hot']} numbers")
    print(f"    Medium: {hmc_counts['medium']} numbers")
    print(f"    Cold:   {hmc_counts['cold']} numbers")
    
    print(f"\n  Available numbers by Freshness (C_max={c_max_threshold}):")
    for i in range(c_max_threshold + 1):
        name = f"C{i}" if i < c_max_threshold else f"C>={i}"
        print(f"    {name}: {fresh_counts[i]} numbers")
    
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