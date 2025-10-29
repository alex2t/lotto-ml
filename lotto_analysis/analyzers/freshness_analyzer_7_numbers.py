"""
Comprehensive freshness distribution analysis for 7 winning numbers.
"""

from collections import defaultdict
from typing import Dict, Tuple

# We target Window 5 from SCENARIOS, which corresponds to the 'last_4' metric.
TARGET_WINDOW = 5
RECENT_KEY = f"last_{TARGET_WINDOW - 1}" # 'last_4'


def analyze_7_number_freshness(draw_history_log: dict, target_window: int) -> Tuple[Dict[str, int], int]:
    """
    Analyzes the full distribution of recent hit counts (0, 1, 2, >=3) 
    among the 7 winning numbers for a specific window.
    
    Args:
        draw_history_log: The output of hmc_analyzer.py (containing recent_counts for 7 numbers)
        target_window: The window size (e.g., 5 for last_4)
        
    Returns:
        Tuple of (distribution_counts, total_draws_analyzed)
    """
    
    recent_key = f"last_{target_window - 1}"
    
    analysis_draws = draw_history_log.values()
    total_draws_analyzed = len(analysis_draws)
    
    distribution_counts = defaultdict(int)
    
    for draw in analysis_draws:
        # winning_numbers_details holds data for all 7 winning numbers
        winning_numbers_details = draw.get('winning_numbers_details', [])
        
        # We must confirm 7 total winning numbers were analyzed
        if len(winning_numbers_details) != 7:
            continue
            
        # Initialize counts for the 4 bins
        # Index 0: C=0, Index 1: C=1, Index 2: C=2, Index 3: C>=3
        counts = [0, 0, 0, 0] 
        
        # Iterate over all 7 winning numbers details
        for winner in winning_numbers_details:
            # Safely retrieve the count for the current key (e.g., 'last_4')
            recent_count = winner['recent_counts'].get(recent_key, -1)
            
            if recent_count == 0:
                counts[0] += 1
            elif recent_count == 1:
                counts[1] += 1
            elif recent_count == 2:
                counts[2] += 1
            elif recent_count >= 3:
                counts[3] += 1
        
        # Since we only iterate over 7 numbers, sum(counts) should be 7
        if sum(counts) == 7:
            distribution_key = (
                f"C0={counts[0]}, C1={counts[1]}, C2={counts[2]}, C>=3={counts[3]}"
            )
            distribution_counts[distribution_key] += 1
                 
    return dict(distribution_counts), total_draws_analyzed


def format_freshness_output(counts: Dict[str, int], total_draws: int, target_window: int) -> Dict:
    """Formats the final output structure and calculates percentages."""
    distribution_list = []
    recent_key = f"last_{target_window - 1}"
    
    # Sort the patterns by count (descending)
    sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    
    for key, count in sorted_counts:
        percentage = round((count / total_draws) * 100, 2) if total_draws > 0 else 0.0
        
        # Extract C values for cleaner display
        parts = key.split(', ')
        c_values = {p.split('=')[0]: int(p.split('=')[1]) for p in parts}
        
        distribution_list.append({
            "pattern": key,
            "C0": c_values.get('C0', 0),
            "C1": c_values.get('C1', 0),
            "C2": c_values.get('C2', 0),
            "C_ge_3": c_values.get('C>=3', 0),
            "draws_matched": count,
            "percentage": percentage
        })

    return {
        "window_size_W": target_window,
        "recent_count_key": recent_key,
        "total_draws_analyzed": total_draws,
        "distribution_analysis_7_numbers": distribution_list
    }