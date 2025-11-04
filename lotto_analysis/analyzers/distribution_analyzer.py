"""
Distribution analysis for odd/even patterns and sum contributions
Analyzes both 6 main numbers and all 7 numbers (6 main + bonus)
"""

from collections import defaultdict
from typing import Dict, List, Tuple
from ..config import (
    SUM_BINS_6_NUMBERS, SUM_BINS_7_NUMBERS,
    ODD_EVEN_PATTERNS_6_NUMBERS, ODD_EVEN_PATTERNS_7_NUMBERS
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