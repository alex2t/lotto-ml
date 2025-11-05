"""
penalties.py
============
Handles diversity penalty calculations with rank-aware adjustments.
"""

import numpy as np
from typing import Set, Tuple, List, Dict, Any
from ml_lotto.config import MAX_NUMBER


def apply_rank_aware_penalty(
    probabilities: np.ndarray,
    penalty_numbers: Set[int],
    penalty_factor: float
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Apply rank-aware diversity penalties to probabilities.
    
    Args:
        probabilities: Base probability array for all numbers
        penalty_numbers: Set of numbers to penalize (from previous models)
        penalty_factor: Base penalty factor (0.0 to 1.0)
    
    Returns:
        Tuple of (adjusted_probabilities, penalty_details)
        
    Logic:
        - Top-ranked numbers get higher penalties (full strength)
        - Low-ranked numbers get lower penalties (more flexibility)
        - Formula: penalty = base × (0.5 + 0.5 × rank_weight)
    """
    adjusted_probs = probabilities.copy()
    penalty_details = []
    
    if not penalty_numbers or penalty_factor <= 0:
        return adjusted_probs, penalty_details
    
    # Create rank mapping (1 = highest probability, MAX_NUMBER = lowest)
    prob_rank_pairs = sorted(
        [(probabilities[i], i + 1) for i in range(MAX_NUMBER)],
        key=lambda x: x[0],
        reverse=True
    )
    ranks = {num: rank for rank, (_, num) in enumerate(prob_rank_pairs, start=1)}
    
    # Apply rank-aware penalties
    for num in penalty_numbers:
        if 1 <= num <= MAX_NUMBER:
            # Calculate rank weight (1.0 for rank #1, decreasing to ~0.0 for rank #47)
            rank_weight = 1.0 - (ranks[num] - 1) / (MAX_NUMBER - 1)
            
            # Adaptive penalty: higher for top-ranked, lower for low-ranked
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