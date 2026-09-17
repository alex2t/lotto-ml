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

        def best_available(fresh_cat: int, allow_penalized: bool) -> Optional[int]:
            """Highest-probability unused number in this bin, or None if the bin is exhausted."""
            for prob, num in pools[hmc_cat].get(fresh_cat, []):
                if num in line or num in picked or num in all_excluded:
                    continue
                if not allow_penalized and num in penalty_numbers:
                    continue
                return num
            return None

        # Pass 1 takes unpenalized numbers, pass 2 allows penalized ones if the pool ran short.
        for allow_penalized in (False, True):
            while len(picked) < count_needed:
                # Re-rank the bins before every pick. Ranking once and draining the top bin is
                # what let bin 0 - which holds roughly half the candidates - absorb every slot
                # and made the target advisory rather than binding (F-8). freshness_counts is
                # shared across the hot/medium/cold calls, so the target applies to the line.
                ranked = sorted(
                    freshness_needed.keys(),
                    key=lambda f: freshness_needed[f] - freshness_counts[f],
                    reverse=True
                )

                chosen = None
                for fresh_cat in ranked:
                    chosen = best_available(fresh_cat, allow_penalized)
                    if chosen is not None:
                        freshness_counts[fresh_cat] += 1
                        break

                if chosen is None:
                    break  # this HMC category is exhausted at this penalty level
                picked.append(chosen)

        return picked
    
    # Pick Hot, Medium, Cold - most freshness-constrained category first.
    #
    # The categories do not span the freshness bins evenly: at the time of writing every bin 1 and
    # bin 2 candidate is hot, while medium and cold are entirely bin 0. Picking hot first spends
    # the bin 0 quota on the only category that could have supplied the scarce bins, and medium
    # and cold then overshoot bin 0 because they have nowhere else to go. Taking the constrained
    # categories first leaves the flexible one to fill what is actually still needed (F-8).
    #
    # HMC categories are disjoint, so the order changes only which freshness bins get claimed,
    # never which numbers are available to a category.
    requests = [('hot', h), ('medium', m), ('cold', c)]
    requests.sort(key=lambda req: sum(1 for entries in pools[req[0]].values() if entries))

    for hmc_cat, count_for_cat in requests:
        line.extend(pick_from_hmc_pool(hmc_cat, count_for_cat))
    
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