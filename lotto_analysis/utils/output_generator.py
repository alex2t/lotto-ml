"""
Output generation utilities for analysis results
"""

import json
from collections import defaultdict
from typing import Dict
from ..config import RANGE_BINS
from lotto_analysis.utils.serialization import round_floats


def format_date_iso(date_str: str) -> str:
    """Convert YYYY-MM-DD to YYYY/MM/DD format."""
    return date_str.replace("-", "/")


def generate_hmc_analysis(hmc_counts: Dict, total_analyzed_draws: int) -> Dict:
    """Generates the HMC Distribution Analysis data."""
    hmc_analysis = {}
    for distribution, count in sorted(hmc_counts.items(), 
                                     key=lambda item: item[1], reverse=True):
        percentage = (count / total_analyzed_draws) * 100
        hmc_analysis[distribution] = {
            "count": count,
            "percentage": round(percentage, 2)
        }
    return hmc_analysis


def generate_draw_range_analysis(categorization_history: Dict, 
                                 total_analyzed_draws: int,
                                 range_key: str = 'draw_range') -> Dict:
    """
    Generates the Draw Range Analysis data.

    `range_key` picks which spread to bin: 'draw_range' spans all 7 balls, 'draw_range_6'
    the main 6. A six-number line can only be compared with the second (F-63).
    """
    range_counts = defaultdict(int)
    
    for draw_data in categorization_history.values():
        draw_range = draw_data[range_key]
        
        # Categorize the draw range into the defined bins
        is_counted = False
        for bin_name, (lower, upper) in RANGE_BINS.items():
            if lower <= draw_range < upper or (bin_name == "40-45" and draw_range == upper):
                range_counts[bin_name] += 1
                is_counted = True
                break
        
        if not is_counted:
            if draw_range < min(b[0] for b in RANGE_BINS.values()):
                range_counts['<20'] += 1
            elif draw_range > max(b[1] for b in RANGE_BINS.values()):
                range_counts['>45'] += 1

    range_analysis = {}
    sorted_bin_names = sorted([k for k in range_counts.keys() if k not in ['<20', '>45']])
    if '<20' in range_counts: 
        sorted_bin_names.insert(0, '<20')
    if '>45' in range_counts: 
        sorted_bin_names.append('>45')

    for bin_name in sorted_bin_names:
        count = range_counts[bin_name]
        percentage = (count / total_analyzed_draws) * 100
        range_analysis[bin_name] = {
            "count": count,
            "percentage": round(percentage, 2)
        }
        
    return range_analysis


def generate_range_spread_analysis(draw_history_log: Dict, max_number: int = 47) -> Dict:
    """
    Generate per-number range spread analysis.
    
    Args:
        draw_history_log: Full draw history with range data
        max_number: Maximum lottery number
        
    Returns:
        Dictionary with per-number range contribution statistics
    """
    from collections import defaultdict
    
    # Track range stats per number
    number_ranges = defaultdict(list)
    
    # Scan all draws
    for draw_date, draw_data in draw_history_log.items():
        winning_details = draw_data.get('winning_numbers_details', [])
        
        if len(winning_details) < 6:
            continue
        
        # Get main 6 numbers
        main_numbers = [w['number'] for w in winning_details[:6]]
        
        if not main_numbers:
            continue
        
        draw_range = max(main_numbers) - min(main_numbers)
        
        # Record range for each number in this draw
        for num in main_numbers:
            number_ranges[num].append(draw_range)
    
    # Calculate statistics per number
    range_spread_analysis = {}
    
    for num in range(1, max_number + 1):
        ranges = number_ranges.get(num, [])
        
        if ranges:
            avg_range = sum(ranges) / len(ranges)
            min_range = min(ranges)
            max_range = max(ranges)
            appearances = len(ranges)
        else:
            avg_range = 0
            min_range = 0
            max_range = 0
            appearances = 0
        
        range_spread_analysis[str(num)] = {
            "appearances_in_draws": appearances,
            "average_range_contribution": round(avg_range, 2),
            "min_range": min_range,
            "max_range": max_range,
            "spread_affinity_score": 0.0
        }
    
    # Calculate spread affinity (normalized to 0-1)
    # Numbers with avg_range 30-40 get highest scores
    for num in range(1, max_number + 1):
        num_key = str(num)
        avg_range = range_spread_analysis[num_key]["average_range_contribution"]
        
        if 30 <= avg_range <= 40:
            score = 1.0
        elif 25 <= avg_range < 30:
            score = 0.8
        elif 20 <= avg_range < 25:
            score = 0.6
        elif 40 < avg_range <= 45:
            score = 0.8
        else:
            score = 0.4
        
        range_spread_analysis[num_key]["spread_affinity_score"] = round(score, 2)
    
    return range_spread_analysis


def write_json_file(filepath: str, data: Dict, description: str = ""):
    """Write data to JSON file with optional description."""
    with open(filepath, "w") as f:
        json.dump(round_floats(data), f, indent=4)
    print(f"✅ Wrote: {filepath}")
    if description:
        print(f"   - {description}")