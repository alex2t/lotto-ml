"""
constraints.py
==============
Handles HMC and freshness pattern constraints for number selection.
"""

from typing import Dict, Any, List
from collections import defaultdict
from ml_lotto.config import MAX_NUMBER


LINE_SIZE = 6  # a generated line is 6 main numbers


def get_optimal_pattern_distribution(
    freshness_data: Dict[str, Any],
    c_max_threshold: int
) -> Dict[int, int]:
    """
    Get the optimal C0/C1/.../C>=X distribution for a generated line.

    Reads `distribution_analysis_6_main`, the observed freshness split of the 6 MAIN
    balls. The sibling `distribution_analysis_7_numbers` describes all 7 drawn balls and
    sums to 7; using it as the target for a 6-number line overstates demand by one
    number's worth and skews which freshness bin selection prioritises.

    Args:
        freshness_data: Raw JSON from lotto_7_number_freshness_results.json
        c_max_threshold: The dynamic threshold (e.g., 2)

    Returns:
        Dictionary mapping bin_index (0 to C_max) -> expected_count, summing to 6.
    """
    distributions = (freshness_data or {}).get('distribution_analysis_6_main') or []

    if not distributions:
        raise ValueError(
            "lotto_7_number_freshness_results.json has no 'distribution_analysis_6_main'. "
            "Re-run drawpick.py to regenerate it."
        )

    top_pattern_data = distributions[0]

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

    total = sum(target_dist.values())
    if total != LINE_SIZE:
        raise ValueError(
            f"Freshness target {target_dist} sums to {total}, expected {LINE_SIZE}. "
            f"Pattern was {top_pattern_data.get('pattern')!r}."
        )

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

    # Sort each pool by probability (highest first), with deterministic tie-break
    for hmc_cat in pools:
        for fresh_cat in pools[hmc_cat]:
            pools[hmc_cat][fresh_cat].sort(key=lambda x: (-x[0], x[1]))

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

def reachable_pattern(
    target_pattern: Dict[int, int],
    pools: Dict[str, Dict[int, List]],
    model_config: Dict[str, Any]
) -> Dict[int, int]:
    """
    The part of `target_pattern` a model can actually achieve, given its HMC quotas.

    The freshness bins are not spread evenly across the HMC categories, so a target can be
    unreachable however selection is ordered. At the time of writing every bin 1 and bin 2
    candidate is hot, so a model with 2 hot slots cannot place 3 non-bin-0 numbers no matter
    what the target asks for. Feeding selection a target it cannot meet makes the miss look
    like a selection failure and hides the real constraint (F-13).

    Allocates scarce bins first, and within a bin draws on the most constrained HMC category
    first, so the result is attainable rather than merely optimistic. Leftover slots fall to
    whichever bins can still absorb them. `ilp_selection.solve_line` enforces the result as
    per-bin lower bounds and raises if it cannot be met alongside the ticket rules.

    Returns a pattern summing to the same number of slots as the model's quotas.
    """
    quotas = {
        'hot': model_config['hot_count'],
        'medium': model_config['medium_count'],
        'cold': model_config['cold_count'],
    }
    supply = {
        hmc: {b: len(pools.get(hmc, {}).get(b, [])) for b in target_pattern}
        for hmc in quotas
    }

    # How many bins each category can serve, and how many categories each bin has.
    bin_suppliers = {b: sum(1 for hmc in quotas if supply[hmc][b]) for b in target_pattern}
    cat_breadth = {hmc: sum(1 for b in target_pattern if supply[hmc][b]) for hmc in quotas}

    remaining = dict(quotas)
    achieved = {b: 0 for b in target_pattern}

    def draw(bin_index: int, wanted: int) -> None:
        """Fill up to `wanted` slots in this bin, most constrained category first."""
        for hmc in sorted(quotas, key=lambda h: (cat_breadth[h], h)):
            if wanted <= 0:
                return
            take = min(wanted, remaining[hmc], supply[hmc][bin_index])
            if take > 0:
                remaining[hmc] -= take
                supply[hmc][bin_index] -= take
                achieved[bin_index] += take
                wanted -= take

    # Scarce bins first: a bin only one category can serve must claim its slots before a
    # flexible bin spends that category's quota.
    for bin_index in sorted(target_pattern, key=lambda b: (bin_suppliers[b], b)):
        draw(bin_index, target_pattern[bin_index])

    # Slots the target could not place still have to go somewhere.
    leftover = sum(remaining.values())
    if leftover:
        for bin_index in sorted(target_pattern, key=lambda b: (bin_suppliers[b], b)):
            draw(bin_index, leftover)
            leftover = sum(remaining.values())
            if not leftover:
                break

    return achieved
