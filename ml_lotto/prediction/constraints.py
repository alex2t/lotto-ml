"""
constraints.py
==============
Handles HMC and freshness pattern constraints for number selection.
"""

from typing import Dict, Any, List
from collections import defaultdict
from ml_lotto.config import MAX_NUMBER


def get_optimal_pattern_distribution(
    freshness_data: Dict[str, Any],
    c_max_threshold: int
) -> Dict[int, int]:
    """
    Get the optimal C0/C1/.../C>=X distribution from freshness data dynamically.
    
    Args:
        freshness_data: Raw JSON data from lotto_7_number_freshness_results.json
        c_max_threshold: The dynamic threshold (e.g., 2)
        
    Returns:
        Dictionary mapping bin_index (0 to C_max) -> expected_count
        Example: {0: 3, 1: 3, 2: 1} means 3x C0, 3x C1, 1x C2
    """
    if not freshness_data or 'distribution_analysis_7_numbers' not in freshness_data:
        # Default to a generic balanced pattern for 7 numbers
        print("Warning: Freshness data empty. Using default pattern (4x C0/C1, 2x C2, 1x C3+).")
        return {0: 3, 1: 2, 2: 1, 3: 1}  # Max C_max=3 for default pattern
    
    top_pattern_data = freshness_data['distribution_analysis_7_numbers'][0]
    
    # Build target distribution dynamically
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


def categorize_numbers_by_freshness(
    features_dict: Dict[int, Dict[str, Any]]
) -> Dict[int, int]:
    """
    Categorize each number into freshness bin (0 to C_max) based on current features.
    
    Args:
        features_dict: Dictionary mapping number -> feature values
        
    Returns:
        Dictionary mapping number -> freshness_category (0, 1, ..., C_max)
        
    Example:
        {1: 0, 2: 1, 3: 0, ...} means number 1 is C0, number 2 is C1, etc.
    """
    number_categories = {}
    
    for num in range(1, MAX_NUMBER + 1):
        if num in features_dict:
            # The 'current_freshness_bin' feature holds the dynamic bin index
            number_categories[num] = int(features_dict[num].get('current_freshness_bin', 0))
        else:
            number_categories[num] = 0
    
    return number_categories


def build_dual_categorized_pools(
    features_dict: Dict[int, Dict[str, Any]],
    number_categories: Dict[int, int],
    adjusted_probs: Any,  # numpy array
    exclude_numbers: set = None
) -> Dict[str, Dict[int, List]]:
    """
    Build dual-categorized pools: HMC categories subdivided by freshness bins.

    Args:
        features_dict: Number features including HMC category
        number_categories: Freshness bin for each number
        adjusted_probs: Adjusted probability array
        exclude_numbers: Optional set of numbers to exclude from pools (e.g., pre-assigned)

    Returns:
        Nested dict: {HMC: {freshness: [(prob, num), ...]}}
        Example: {'hot': {0: [(0.85, 5), (0.82, 12)], 1: [(0.78, 3)]}, ...}
    """
    if exclude_numbers is None:
        exclude_numbers = set()

    pools = {
        'hot': defaultdict(list),
        'medium': defaultdict(list),
        'cold': defaultdict(list)
    }

    for num in range(1, MAX_NUMBER + 1):
        if num not in features_dict:
            continue

        # Skip excluded numbers
        if num in exclude_numbers:
            continue

        hmc_cat = features_dict[num].get('category', 'cold')
        fresh_cat = number_categories.get(num, 0)
        prob = adjusted_probs[num - 1]

        if hmc_cat in pools:
            pools[hmc_cat][fresh_cat].append((prob, num))

    # Sort each pool by probability (highest first)
    for hmc_cat in pools:
        for fresh_cat in pools[hmc_cat]:
            pools[hmc_cat][fresh_cat].sort(reverse=True)

    return pools


def display_available_numbers(
    features_dict: Dict[int, Dict[str, Any]],
    number_categories: Dict[int, int],
    c_max_threshold: int
):
    """
    Display statistics about available numbers by HMC and freshness categories.
    
    Args:
        features_dict: Number features
        number_categories: Freshness categorization
        c_max_threshold: Maximum freshness bin threshold
    """
    # Count by HMC
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