"""
Output generation utilities for analysis results
"""

import json
from collections import defaultdict
from typing import Dict
from ..config import RANGE_BINS


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
                                 total_analyzed_draws: int) -> Dict:
    """Generates the Draw Range Analysis data."""
    range_counts = defaultdict(int)
    
    for draw_data in categorization_history.values():
        draw_range = draw_data['draw_range']
        
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


def write_json_file(filepath: str, data: Dict, description: str = ""):
    """Write data to JSON file with optional description."""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)
    print(f"✅ Wrote: {filepath}")
    if description:
        print(f"   - {description}")
