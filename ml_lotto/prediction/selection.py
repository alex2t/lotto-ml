"""
selection.py
============
Core number selection logic with hybrid HMC + Freshness constraints.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
from collections import defaultdict
from ml_lotto.prediction.filters import (
    FILTERS_AVAILABLE,
    validate_line,
    rebalance_line
)


def pick_line_hybrid(
    model_config: Dict[str, Any],
    probabilities: Any,  # numpy array
    features_dict: Dict[int, Dict[str, Any]],
    number_categories: Dict[int, int],
    target_pattern: Dict[int, int],
    pools: Dict[str, Dict[int, List]],
    penalty_numbers: Set[int] = None,
    pre_assigned_numbers: Optional[List[int]] = None
) -> Tuple[List[int], List[Dict[str, Any]], str]:
    """
    HYBRID PICKER: Respects BOTH HMC ratios AND freshness patterns dynamically.

    Args:
        model_config: Model configuration with HMC counts and penalties
        probabilities: Base probability array (for rebalancing if needed)
        features_dict: Number features (for rebalancing if needed)
        number_categories: Freshness categorization
        target_pattern: Optimal freshness distribution {bin: count}
        pools: Pre-built dual-categorized pools {HMC: {freshness: [(prob, num)]}}
        penalty_numbers: Numbers with soft diversity penalties applied
        pre_assigned_numbers: Numbers pre-assigned to this line (excluded from selection)

    Returns:
        Tuple of (selected_numbers, penalty_details, pattern_string)
    """
    # Initialize penalty_numbers if None
    if penalty_numbers is None:
        penalty_numbers = set()
    if pre_assigned_numbers is None:
        pre_assigned_numbers = []

    h = model_config['hot_count']
    m = model_config['medium_count']
    c = model_config['cold_count']
    g = model_config['generic_count']
    
    # Get max bin index for initialization
    max_fresh_bin = max(target_pattern.keys()) if target_pattern else 0
    
    # Track results
    line = []
    freshness_counts = defaultdict(int)
    freshness_needed = target_pattern.copy()
    
    target_count = h + m + c + g
    all_excluded = set(pre_assigned_numbers)

    # PHASE 1: Pick from HMC categories, prioritizing needed freshness bins
    def pick_from_hmc_pool(hmc_cat: str, count_needed: int) -> List[int]:
        """
        Pick 'count_needed' numbers from HMC category, prioritizing target freshness.
        """
        picked = []
        if count_needed <= 0:
            return picked

        # Sort freshness bins by how much we need them (gap)
        freshness_priority = sorted(
            freshness_needed.keys(),
            key=lambda f: freshness_needed[f] - freshness_counts[f],
            reverse=True
        )

        # Pass 1: Try to pick unpenalized numbers first (C-11 fix: check bound before append)
        for fresh_cat in freshness_priority:
            if len(picked) >= count_needed:
                break
            available = pools[hmc_cat].get(fresh_cat, [])
            for prob, num in available:
                if len(picked) >= count_needed:
                    break
                if num not in line and num not in picked and num not in all_excluded and num not in penalty_numbers:
                    picked.append(num)
                    freshness_counts[fresh_cat] += 1

        # Pass 2: Fallback to penalized numbers if unpenalized pool was insufficient
        if len(picked) < count_needed:
            for fresh_cat in freshness_priority:
                if len(picked) >= count_needed:
                    break
                available = pools[hmc_cat].get(fresh_cat, [])
                for prob, num in available:
                    if len(picked) >= count_needed:
                        break
                    if num not in line and num not in picked and num not in all_excluded:
                        picked.append(num)
                        freshness_counts[fresh_cat] += 1

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
                    if num not in line and num not in all_excluded:
                        # Score by: probability + bonus if we need this freshness category
                        freshness_gap = max(0, freshness_needed[fresh_cat] - freshness_counts[fresh_cat])
                        penalty_mult = 0.6 if num in penalty_numbers else 1.0
                        score = prob * (1.0 + 0.5 * freshness_gap) * penalty_mult
                        all_remaining.append((score, prob, num, fresh_cat))

        all_remaining.sort(key=lambda x: (-x[0], x[2]))

        for score, prob, num, fresh_cat in all_remaining[:g]:
            line.append(num)
            freshness_counts[fresh_cat] += 1

    # Safety Guarantee: Ensure line has reached target_count without duplicating pre_assigned numbers (C-12 fix)
    if len(line) < target_count:
        needed = target_count - len(line)
        print(f"  ℹ️  Safety top-up: adding {needed} number(s) to reach target count of {target_count}")
        candidates = []
        for num in range(1, len(probabilities) + 1):
            if num not in line and num not in all_excluded:
                candidates.append((probabilities[num - 1], num))
        # Deterministic tie-breaking: highest probability first, then lowest number
        candidates.sort(key=lambda x: (-x[0], x[1]))
        for _, num in candidates[:needed]:
            line.append(num)
    
    # Build pattern string dynamically
    pattern_parts = []
    for i in range(max_fresh_bin + 1):
        if i < max_fresh_bin:
            pattern_parts.append(f"C{i}={freshness_counts[i]}")
        else:
            pattern_parts.append(f"C_GE_{max_fresh_bin}={freshness_counts[i]}")
    
    pattern_str = ", ".join(pattern_parts)
    
    # PHASE 3: Filter validation (optional - only if filters available)
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
    
    # Penalty details are empty here - they're calculated in penalties.py before this function
    penalty_details = []
    
    return sorted_line, penalty_details, pattern_str