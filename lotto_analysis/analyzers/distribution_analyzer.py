"""
Distribution analysis for odd/even patterns and sum contributions
Analyzes both 6 main numbers and all 7 numbers (6 main + bonus)
"""

from collections import defaultdict
from math import comb
from typing import Dict, List, Tuple
from ..config import (
    SUM_BINS_6_NUMBERS, SUM_BINS_7_NUMBERS,
    ODD_EVEN_PATTERNS_6_NUMBERS, ODD_EVEN_PATTERNS_7_NUMBERS,
    HIGH_NUMBER_FROM, MAX_NUMBER
)


def analyze_odd_even_pattern(numbers: List[int]) -> str:
    """
    Analyze odd/even pattern for a set of numbers.
    
    Args:
        numbers: List of winning numbers (6 or 7)
        
    Returns:
        String pattern like "4_3" (4 odd, 3 even)
    """
    odd_count = sum(1 for n in numbers if n % 2 == 1)
    even_count = len(numbers) - odd_count
    return f"{odd_count}_{even_count}"


def get_sum_bin(total_sum: int, use_7_numbers: bool = True) -> str:
    """
    Determine which sum bin a total belongs to.
    
    Args:
        total_sum: Sum of numbers
        use_7_numbers: If True, use 7-number bins, else use 6-number bins
        
    Returns:
        Bin label string
    """
    bins = SUM_BINS_7_NUMBERS if use_7_numbers else SUM_BINS_6_NUMBERS
    
    for bin_name, (lower, upper) in bins.items():
        if lower <= total_sum < upper:
            return bin_name
    
    # Fallback for edge cases
    if total_sum < min(b[0] for b in bins.values()):
        return list(bins.keys())[0]
    else:
        return list(bins.keys())[-1]


def analyze_distribution_patterns(draw_history_log: Dict) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Analyze odd/even patterns and sum distributions across all draws.
    Analyzes BOTH 6 main numbers and all 7 numbers separately.
    
    Args:
        draw_history_log: Dictionary of draw history data
        
    Returns:
        Tuple of (odd_even_6_stats, odd_even_7_stats, sum_6_stats, sum_7_stats)
    """
    # Counters for 6 main numbers
    odd_even_6_counts = defaultdict(int)
    sum_6_bin_counts = defaultdict(int)
    
    # Counters for all 7 numbers
    odd_even_7_counts = defaultdict(int)
    sum_7_bin_counts = defaultdict(int)
    
    total_draws = len(draw_history_log)
    
    for draw_date, draw_data in draw_history_log.items():
        winning_details = draw_data.get('winning_numbers_details', [])
        
        if len(winning_details) < 7:
            continue
        
        # ========== ANALYZE 6 MAIN NUMBERS (excluding bonus) ==========
        main_6_numbers = [w['number'] for w in winning_details[:6]]
        
        # Odd/even pattern for 6 numbers
        odd_even_6_pattern = analyze_odd_even_pattern(main_6_numbers)
        odd_even_6_counts[odd_even_6_pattern] += 1
        
        # Sum distribution for 6 numbers
        sum_6 = sum(main_6_numbers)
        sum_6_bin = get_sum_bin(sum_6, use_7_numbers=False)
        sum_6_bin_counts[sum_6_bin] += 1
        
        # ========== ANALYZE ALL 7 NUMBERS (6 main + bonus) ==========
        all_7_numbers = [w['number'] for w in winning_details[:7]]
        
        # Odd/even pattern for 7 numbers
        odd_even_7_pattern = analyze_odd_even_pattern(all_7_numbers)
        odd_even_7_counts[odd_even_7_pattern] += 1
        
        # Sum distribution for 7 numbers
        sum_7 = sum(all_7_numbers)
        sum_7_bin = get_sum_bin(sum_7, use_7_numbers=True)
        sum_7_bin_counts[sum_7_bin] += 1
    
    # ========== FORMAT 6-NUMBER STATISTICS ==========
    odd_even_6_stats = {}
    for pattern in ODD_EVEN_PATTERNS_6_NUMBERS:
        count = odd_even_6_counts.get(pattern, 0)
        percentage = (count / total_draws * 100) if total_draws > 0 else 0.0
        odds = (count / total_draws) if total_draws > 0 else 0.0
        
        odd_even_6_stats[pattern] = {
            "count": count,
            "percentage": round(percentage, 2),
            "odds": round(odds, 4)
        }
    
    sum_6_stats = {}
    for bin_name in SUM_BINS_6_NUMBERS.keys():
        count = sum_6_bin_counts.get(bin_name, 0)
        percentage = (count / total_draws * 100) if total_draws > 0 else 0.0
        odds = (count / total_draws) if total_draws > 0 else 0.0
        
        sum_6_stats[bin_name] = {
            "count": count,
            "percentage": round(percentage, 2),
            "odds": round(odds, 4)
        }
    
    # ========== FORMAT 7-NUMBER STATISTICS ==========
    odd_even_7_stats = {}
    for pattern in ODD_EVEN_PATTERNS_7_NUMBERS:
        count = odd_even_7_counts.get(pattern, 0)
        percentage = (count / total_draws * 100) if total_draws > 0 else 0.0
        odds = (count / total_draws) if total_draws > 0 else 0.0
        
        odd_even_7_stats[pattern] = {
            "count": count,
            "percentage": round(percentage, 2),
            "odds": round(odds, 4)
        }
    
    sum_7_stats = {}
    for bin_name in SUM_BINS_7_NUMBERS.keys():
        count = sum_7_bin_counts.get(bin_name, 0)
        percentage = (count / total_draws * 100) if total_draws > 0 else 0.0
        odds = (count / total_draws) if total_draws > 0 else 0.0
        
        sum_7_stats[bin_name] = {
            "count": count,
            "percentage": round(percentage, 2),
            "odds": round(odds, 4)
        }
    
    return odd_even_6_stats, odd_even_7_stats, sum_6_stats, sum_7_stats


def analyze_high_number_distribution(draw_history_log: Dict) -> Dict:
    """
    Count draws by how many of their 6 main numbers are >= HIGH_NUMBER_FROM.

    Keys are "0".."6". Each entry has the observed count, percentage and odds, plus
    fair_percentage - the share a fair draw gives (hypergeometric), for comparison.
    """
    main_draws = [
        [w['number'] for w in draw['winning_numbers_details'][:6]]
        for draw in draw_history_log.values()
        if len(draw['winning_numbers_details']) >= 7
    ]
    counts = defaultdict(int)
    for numbers in main_draws:
        counts[sum(1 for n in numbers if n >= HIGH_NUMBER_FROM)] += 1

    total_draws = len(main_draws)
    n_high = MAX_NUMBER - HIGH_NUMBER_FROM + 1
    stats = {}
    for k in range(7):
        count = counts.get(k, 0)
        fair = comb(n_high, k) * comb(MAX_NUMBER - n_high, 6 - k) / comb(MAX_NUMBER, 6)
        stats[str(k)] = {
            "count": count,
            "percentage": round(count / total_draws * 100, 2),
            "odds": round(count / total_draws, 4),
            "fair_percentage": round(fair * 100, 2),
        }
    return stats


def calculate_draw_distribution_features(winning_numbers_details: List[Dict]) -> Dict:
    """
    Calculate distribution features for a single draw (for ML features).
    Calculates features for BOTH 6 main numbers and all 7 numbers.
    
    Args:
        winning_numbers_details: List of winning number details for a draw
        
    Returns:
        Dictionary with distribution features
    """
    if len(winning_numbers_details) < 7:
        return {
            # 6-number features
            'odd_even_pattern_6': 'unknown',
            'sum_contribution_score_6': 0,
            'sum_bin_6': 'unknown',
            'range_spread_affinity_6': 0,
            'odd_even_affinity_6': 0,
            # 7-number features
            'odd_even_pattern_7': 'unknown',
            'sum_contribution_score_7': 0,
            'sum_bin_7': 'unknown',
            'range_spread_affinity_7': 0,
            'odd_even_affinity_7': 0
        }
    
    # Get 6 main numbers
    main_6_numbers = [w['number'] for w in winning_numbers_details[:6]]
    
    # Get all 7 numbers
    all_7_numbers = [w['number'] for w in winning_numbers_details[:7]]
    
    # ========== 6-NUMBER FEATURES ==========
    odd_even_pattern_6 = analyze_odd_even_pattern(main_6_numbers)
    sum_6 = sum(main_6_numbers)
    sum_bin_6 = get_sum_bin(sum_6, use_7_numbers=False)
    
    # Sum contribution score for 6 numbers (normalized 0-1, where 0.5 is average ~144)
    # Range: 21 to 267, midpoint = 144
    sum_contribution_score_6 = (sum_6 - 21) / (267 - 21)
    
    # Range spread affinity for 6 numbers (0-1, where larger spread = higher affinity)
    draw_range_6 = max(main_6_numbers) - min(main_6_numbers)
    range_spread_affinity_6 = draw_range_6 / 46  # Max possible range is 46 (47-1)
    
    # Odd/even affinity for 6 numbers (0-1, where balanced 3-3 = 1.0, extreme 6-0 or 0-6 = 0.0)
    odd_count_6 = sum(1 for n in main_6_numbers if n % 2 == 1)
    balance_score_6 = 1.0 - abs(odd_count_6 - 3) / 3.0
    odd_even_affinity_6 = balance_score_6
    
    # ========== 7-NUMBER FEATURES ==========
    odd_even_pattern_7 = analyze_odd_even_pattern(all_7_numbers)
    sum_7 = sum(all_7_numbers)
    sum_bin_7 = get_sum_bin(sum_7, use_7_numbers=True)
    
    # Sum contribution score for 7 numbers (normalized 0-1, where 0.5 is average ~157)
    # Range: 28 to 287, midpoint = 157.5
    sum_contribution_score_7 = (sum_7 - 28) / (287 - 28)
    
    # Range spread affinity for 7 numbers
    draw_range_7 = max(all_7_numbers) - min(all_7_numbers)
    range_spread_affinity_7 = draw_range_7 / 46
    
    # Odd/even affinity for 7 numbers (0-1, where balanced 4-3 or 3-4 = 1.0)
    odd_count_7 = sum(1 for n in all_7_numbers if n % 2 == 1)
    # For 7 numbers, perfect balance is 4-3 or 3-4 (distance from 3.5)
    balance_score_7 = 1.0 - abs(odd_count_7 - 3.5) / 3.5
    odd_even_affinity_7 = balance_score_7
    
    return {
        # 6-number features
        'odd_even_pattern_6': odd_even_pattern_6,
        'sum_contribution_score_6': round(sum_contribution_score_6, 4),
        'sum_bin_6': sum_bin_6,
        'range_spread_affinity_6': round(range_spread_affinity_6, 4),
        'odd_even_affinity_6': round(odd_even_affinity_6, 4),
        # 7-number features  
        'odd_even_pattern_7': odd_even_pattern_7,
        'sum_contribution_score_7': round(sum_contribution_score_7, 4),
        'sum_bin_7': sum_bin_7,
        'range_spread_affinity_7': round(range_spread_affinity_7, 4),
        'odd_even_affinity_7': round(odd_even_affinity_7, 4)
    }


def calculate_per_number_distribution_stats(
    draw_history_log: Dict,
    max_number: int = 47
) -> Tuple[Dict, Dict]:
    """
    Calculate per-number odd/even and sum contribution statistics.
    
    Args:
        draw_history_log: Full draw history
        max_number: Maximum lottery number
        
    Returns:
        Tuple of (odd_even_analysis, sum_contribution_analysis)
    """
    from collections import defaultdict
    
    # Track appearances by number
    number_odd_even_patterns = defaultdict(list)
    number_sum_bins = defaultdict(list)
    number_appearances = defaultdict(int)
    
    # Scan all draws
    for draw_date, draw_data in draw_history_log.items():
        winning_details = draw_data.get('winning_numbers_details', [])
        
        if len(winning_details) < 6:
            continue
        
        # Get main 6 numbers
        main_6 = [w['number'] for w in winning_details[:6]]
        
        # Get distribution features
        dist_features = draw_data.get('distribution_features', {})
        odd_even_pattern = dist_features.get('odd_even_pattern_6', 'unknown')
        sum_bin = dist_features.get('sum_bin_6', 'unknown')
        
        # Record for each number
        for num in main_6:
            number_odd_even_patterns[num].append(odd_even_pattern)
            number_sum_bins[num].append(sum_bin)
            number_appearances[num] += 1
    
    # ===== Build Odd/Even Analysis =====
    odd_even_analysis = {}
    
    for num in range(1, max_number + 1):
        patterns = number_odd_even_patterns.get(num, [])
        appearances = number_appearances.get(num, 0)
        
        # Count pattern occurrences
        pattern_counts = defaultdict(int)
        for pattern in patterns:
            pattern_counts[pattern] += 1
        
        # Find most common pattern
        most_common_pattern = "unknown"
        most_common_count = 0
        
        if pattern_counts:
            most_common_pattern = max(pattern_counts.items(), key=lambda x: x[1])[0]
            most_common_count = pattern_counts[most_common_pattern]
        
        # Calculate affinity (odd numbers contribute to odd counts, even to even counts)
        is_odd = (num % 2 == 1)
        affinity_score = 0.75 if is_odd else 0.65  # Odd numbers slightly preferred
        
        odd_even_analysis[str(num)] = {
            "total_appearances": appearances,
            "most_common_pattern": most_common_pattern,
            "pattern_frequency": most_common_count,
            "odd_even_affinity": round(affinity_score, 2)
        }
    
    # ===== Build Sum Contribution Analysis =====
    sum_contribution_analysis = {}
    
    for num in range(1, max_number + 1):
        sum_bins = number_sum_bins.get(num, [])
        appearances = number_appearances.get(num, 0)
        
        # Count bin occurrences
        bin_counts = defaultdict(int)
        for bin_name in sum_bins:
            bin_counts[bin_name] += 1
        
        # Find most common bin
        most_common_bin = "unknown"
        most_common_count = 0
        
        if bin_counts:
            most_common_bin = max(bin_counts.items(), key=lambda x: x[1])[0]
            most_common_count = bin_counts[most_common_bin]
        
        # Calculate contribution score (middle numbers 15-35 score higher)
        if 15 <= num <= 35:
            contribution_score = 0.85
        elif 11 <= num <= 39:
            contribution_score = 0.70
        else:
            contribution_score = 0.50
        
        sum_contribution_analysis[str(num)] = {
            "total_appearances": appearances,
            "most_common_sum_bin": most_common_bin,
            "bin_frequency": most_common_count,
            "sum_contribution_score": round(contribution_score, 2)
        }
    
    return odd_even_analysis, sum_contribution_analysis