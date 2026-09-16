# ml_lotto/prediction/pool_generator.py
"""
pool_generator.py
=================
Generate ranked pool of candidate numbers for Model 4 (Configurable Pool Generator).

Unlike Models 1-3 which pick exactly 6 numbers, Model 4 creates an expanded pool
where users can manually/automatically select combinations.
"""

import numpy as np
from typing import Dict, Any, List


def generate_pool_from_model(
    model_config: Dict[str, Any],
    all_probabilities: np.ndarray,
    features_dict: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate pool using hot_count, medium_count, cold_count from config.

    Args:
        model_config: Model configuration with hot_count, medium_count, cold_count
        all_probabilities: Probability array for all 47 numbers (indices 0-46 for numbers 1-47)
        features_dict: Current feature values for all numbers

    Returns:
        {
            'pool': [sorted numbers by probability],
            'hot_candidates': [metadata for hot numbers],
            'medium_candidates': [metadata for medium numbers],
            'cold_candidates': [metadata for cold numbers],
            'pool_size': total count,
            'pool_config': "6H+8M+4C=18",
            'freshness_distribution': {0: count, 1: count, ...},
            'quality_score': 0-100
        }
    """
    hot_count = model_config['hot_count']
    medium_count = model_config['medium_count']
    cold_count = model_config['cold_count']

    pool_size = hot_count + medium_count + cold_count
    pool_config = f"{hot_count}H+{medium_count}M+{cold_count}C={pool_size}"

    # Categorize numbers by HMC category
    hot_numbers = []
    medium_numbers = []
    cold_numbers = []

    for num in range(1, 48):  # Numbers 1-47
        if num in features_dict:
            category = features_dict[num].get('category', 'medium')
            prob = all_probabilities[num - 1]  # Convert to 0-indexed

            number_data = {
                'number': num,
                'probability': prob,
                'category': category,
                'freshness_bin': features_dict[num].get('current_freshness_bin', 0),
                'recent_4': features_dict[num].get('recent_4', 0),
                'days_since_last': features_dict[num].get('days_since_last', 999)
            }

            if category == 'hot':
                hot_numbers.append(number_data)
            elif category == 'medium':
                medium_numbers.append(number_data)
            elif category == 'cold':
                cold_numbers.append(number_data)

    # Sort each category by probability (descending), tie-break by number (ascending)
    hot_numbers.sort(key=lambda x: (-x['probability'], x['number']))
    medium_numbers.sort(key=lambda x: (-x['probability'], x['number']))
    cold_numbers.sort(key=lambda x: (-x['probability'], x['number']))

    # Take top N from each category
    hot_candidates = hot_numbers[:hot_count]
    medium_candidates = medium_numbers[:medium_count]
    cold_candidates = cold_numbers[:cold_count]

    # Combine all candidates
    all_candidates = hot_candidates + medium_candidates + cold_candidates

    # Sort combined pool by probability (descending), tie-break by number (ascending)
    all_candidates.sort(key=lambda x: (-x['probability'], x['number']))

    # Extract pool numbers (sorted by probability)
    pool_numbers = [c['number'] for c in all_candidates]

    # Calculate freshness distribution
    freshness_distribution = {}
    for candidate in all_candidates:
        bin_val = candidate['freshness_bin']
        freshness_distribution[bin_val] = freshness_distribution.get(bin_val, 0) + 1

    # Calculate quality score (0-100)
    quality_score = calculate_pool_quality(
        all_candidates,
        hot_candidates,
        medium_candidates,
        cold_candidates,
        freshness_distribution,
        pool_size
    )

    return {
        'pool': pool_numbers,
        'hot_candidates': hot_candidates,
        'medium_candidates': medium_candidates,
        'cold_candidates': cold_candidates,
        'pool_size': pool_size,
        'pool_config': pool_config,
        'freshness_distribution': freshness_distribution,
        'quality_score': quality_score,
        'all_candidates': all_candidates  # For detailed display
    }


def calculate_pool_quality(
    all_candidates: List[Dict[str, Any]],
    hot_candidates: List[Dict[str, Any]],
    medium_candidates: List[Dict[str, Any]],
    cold_candidates: List[Dict[str, Any]],
    freshness_distribution: Dict[int, int],
    pool_size: int
) -> float:
    """
    Calculate quality score for the pool (0-100).

    Quality factors:
    - Probability spread (higher is better)
    - Freshness diversity (closer to expected distribution is better)
    - Category balance (having all categories is better)

    Returns:
        Quality score 0-100
    """
    score = 0.0

    # Factor 1: Probability spread (40 points)
    # Higher average probability = better quality
    if all_candidates:
        avg_prob = np.mean([c['probability'] for c in all_candidates])
        prob_score = min(40, avg_prob * 400)  # Scale to max 40 points
        score += prob_score

    # Factor 2: Freshness diversity (30 points)
    # Expected distribution: C0 ~43%, C1 ~29%, C2 ~28%
    # Actual freshness distribution alignment
    expected_dist = {0: 0.43, 1: 0.29, 2: 0.28}
    if pool_size > 0:
        freshness_score = 0
        for bin_val, expected_pct in expected_dist.items():
            actual_count = freshness_distribution.get(bin_val, 0)
            actual_pct = actual_count / pool_size

            # Calculate deviation from expected
            deviation = abs(actual_pct - expected_pct)
            bin_score = max(0, 10 - (deviation * 30))  # Max 10 points per bin
            freshness_score += bin_score

        score += freshness_score

    # Factor 3: Category balance (30 points)
    # Having all three categories represented is good
    categories_present = 0
    if hot_candidates:
        categories_present += 1
        score += 10
    if medium_candidates:
        categories_present += 1
        score += 10
    if cold_candidates:
        categories_present += 1
        score += 10

    return min(100, max(0, score))


def get_freshness_target_display(pool_size: int) -> Dict[int, str]:
    """
    Get expected freshness targets for display.

    Args:
        pool_size: Size of the pool

    Returns:
        Dict mapping freshness bin -> target percentage string
    """
    # Based on statistical analysis: C0 ~43%, C1 ~29%, C2 ~28%
    expected_dist = {
        0: 0.43,
        1: 0.29,
        2: 0.28
    }

    targets = {}
    for bin_val, pct in expected_dist.items():
        targets[bin_val] = f"~{int(pct * 100)}%"

    return targets
