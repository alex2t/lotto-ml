"""
predictor.py
============
Generates predictions from trained models and applies rank-aware diversity penalties.
Handles number selection based on HMC (Hot-Medium-Cold) categories.
"""

import numpy as np
from typing import Dict, Any, List, Set, Tuple
from ml_lotto.config import MAX_NUMBER, SHOW_DETAILED_PENALTIES


def generate_predictions(models: Dict[str, Any],
                        model_features: Dict[str, List[str]],
                        features_dict: Dict[int, Dict[str, Any]]) -> Dict[str, np.ndarray]:
    """
    Generate predictions from all trained models.
    
    Args:
        models: Dictionary of trained model pipelines
        model_features: Dictionary mapping model names to their feature lists
        features_dict: Per-number features
    
    Returns:
        Dictionary mapping model names to probability arrays
    """
    print("\n" + "="*70)
    print("GENERATING PREDICTIONS")
    print("="*70)
    
    all_probabilities = {}
    
    for model_name, model_data in models.items():
        pipeline = model_data['pipeline']
        features_for_model = model_features[model_name]
        
        # Prepare input data with only the features this model needs
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
    
    NEW IN V3.1:
    ------------
    Rank-aware penalties: High-ranked numbers (model's top picks) receive
    stronger penalties than low-ranked numbers. This intelligently preserves
    diversity while allowing flexibility for uncertain picks.
    
    Formula: penalty = base_penalty * (0.5 + 0.5 * rank_weight)
    Where rank_weight = 1.0 for rank #1, decreasing to ~0 for rank #47
    
    Args:
        probabilities: Original probability array
        penalty_numbers: Set of numbers to penalize
        penalty_factor: Base penalty factor (0.0 to 1.0)
    
    Returns:
        Tuple of (adjusted_probabilities, penalty_details)
    """
    adjusted_probs = probabilities.copy()
    penalty_details = []
    
    if not penalty_numbers or penalty_factor <= 0:
        return adjusted_probs, penalty_details
    
    # Create rank mapping: 1 = highest probability, 47 = lowest
    prob_rank_pairs = sorted(
        [(probabilities[i], i + 1) for i in range(MAX_NUMBER)],
        key=lambda x: x[0],
        reverse=True
    )
    ranks = {num: rank for rank, (_, num) in enumerate(prob_rank_pairs, start=1)}
    
    for num in penalty_numbers:
        if 1 <= num <= MAX_NUMBER:
            # Calculate rank weight: 1.0 for rank 1, ~0 for rank 47
            rank_weight = 1.0 - (ranks[num] - 1) / (MAX_NUMBER - 1)
            
            # Scale penalty by rank: top picks get stronger penalty
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


def pick_line(model_config: Dict[str, Any],
              probabilities: np.ndarray,
              features_dict: Dict[int, Dict[str, Any]],
              penalty_numbers: Set[int] = None) -> Tuple[List[int], List[Dict[str, Any]]]:
    """
    Pick numbers respecting HMC ratio with rank-aware diversity penalties.
    
    Args:
        model_config: Model configuration with HMC counts and penalty settings
        probabilities: Model-specific probability array
        features_dict: Category info for each number
        penalty_numbers: Set of numbers to penalize (from previous models)
    
    Returns:
        Tuple of (selected_numbers, penalty_details)
    """
    h = model_config['hot_count']
    m = model_config['medium_count']
    c = model_config['cold_count']
    extra_count = model_config['generic_count']
    penalty_factor = model_config['diversity_penalty']
    
    # Apply rank-aware diversity penalty if specified
    adjusted_probs, penalty_details = apply_rank_aware_penalty(
        probabilities,
        penalty_numbers,
        penalty_factor
    )
    
    # Sort by adjusted probability
    prob_sorted = sorted(
        [(adjusted_probs[i], i + 1) for i in range(MAX_NUMBER)],
        key=lambda x: x[0],
        reverse=True
    )
    
    # Categorize numbers
    hot_nums = [n for n in range(1, MAX_NUMBER + 1)
                if n in features_dict and features_dict[n]['category'] == 'hot']
    med_nums = [n for n in range(1, MAX_NUMBER + 1)
                if n in features_dict and features_dict[n]['category'] == 'medium']
    cold_nums = [n for n in range(1, MAX_NUMBER + 1)
                 if n in features_dict and features_dict[n]['category'] == 'cold']
    
    # Sort each category by adjusted probabilities
    hot_sorted = sorted(hot_nums, key=lambda n: adjusted_probs[n - 1], reverse=True)
    med_sorted = sorted(med_nums, key=lambda n: adjusted_probs[n - 1], reverse=True)
    cold_sorted = sorted(cold_nums, key=lambda n: adjusted_probs[n - 1], reverse=True)
    
    # Pick from each category
    line = []
    line += hot_sorted[:h]
    line += med_sorted[:m]
    line += cold_sorted[:c]
    
    # Fill remaining slots
    chosen_set = set(line)
    extras = [num for _, num in prob_sorted if num not in chosen_set]
    line += extras[:extra_count]
    
    return sorted(set(line)), penalty_details


def generate_all_picks(models: Dict[str, Any],
                      all_probabilities: Dict[str, np.ndarray],
                      features_dict: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate picks from all models with cumulative diversity penalties.
    
    Returns:
        List of dictionaries with model info and selected numbers
    """
    print("\n" + "="*70)
    print("GENERATING INTELLIGENT PICKS WITH RANK-AWARE DIVERSITY")
    print("="*70)
    
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
        print(f"  Configuration: {h}H-{m}M-{c}C+{g}G")
        
        if penalty_numbers and penalty > 0:
            print(f"  Penalty: {penalty*100:.0f}% base (rank-adjusted) on {len(penalty_numbers)} previous numbers")
        else:
            print(f"  Penalty: None (baseline predictions)")
        
        # Pick line with penalties
        selected_numbers, penalty_details = pick_line(
            model_config,
            probabilities,
            features_dict,
            penalty_numbers if penalty_numbers else None
        )
        
        # Display penalty details if enabled
        if SHOW_DETAILED_PENALTIES and penalty_details:
            print(f"    Applying rank-aware penalties:")
            # Show top 5 penalized numbers sorted by rank
            penalty_details.sort(key=lambda x: x['rank'])
            for detail in penalty_details[:5]:
                print(f"      #{detail['num']} (Rank {detail['rank']}): "
                      f"{detail['penalty_pct']:.1f}% penalty "
                      f"({detail['orig_prob']:.4f} → {detail['new_prob']:.4f})")
        
        print(f"  Numbers: {selected_numbers}")
        
        lines.append({
            'model_name': model_config['name'],
            'model_index': model_idx,
            'config_str': f"{h}H-{m}M-{c}C+{g}G",
            'numbers': selected_numbers,
            'description': model_config['description']
        })
        
        # Add current model's numbers to penalty set for next model
        penalty_numbers.update(selected_numbers)
    
    return lines
