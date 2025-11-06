"""
patterns.py
===========
Pattern-based feature calculations.

Features in this module:
- has_consecutive_partner: Binary indicator if number has hot consecutive neighbor
- consecutive_pair_affinity: Historical frequency of appearing in consecutive pairs

Both features use data from lotto_odds_results.json (consecutive patterns analysis)
"""

from typing import Dict, Any, List, Tuple
from collections import defaultdict
from ml_lotto.config import MAX_NUMBER


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
    
    Args:
        hmc_data: HMC statistics from lotto_trigger_periods.json
        dynamic_recent_keys: List of (data_key, ml_key) tuples
        
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
    
    Args:
        consecutive_patterns: Consecutive patterns data from lotto_odds_results.json
        
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