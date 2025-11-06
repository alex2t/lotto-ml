"""
history.py
==========
Historical draw data feature extraction.

Features in this module:
- win_bias_ratio: Category performance ratio from historical draws

Uses data from lotto_draw_history.json
"""

from typing import Dict, Any


def extract_win_bias_ratio_from_history(
    draw_history_log: Dict[str, Any],
    max_number: int
) -> Dict[int, float]:
    """
    Extract the MOST RECENT win_bias_ratio from draw history.
    
    The win_bias_ratio indicates how well each number's HMC category
    (hot/medium/cold) has been performing relative to expectations.
    
    Args:
        draw_history_log: Full draw history with bias ratios
        max_number: Maximum lottery number (typically 47)
        
    Returns:
        Dictionary mapping number -> win_bias_ratio
        
    Raises:
        ValueError: If draw history is empty or missing required data
    """
    if not draw_history_log:
        print(f"\n❌ CRITICAL ERROR: Draw history log is empty.")
        raise ValueError("Cannot extract win_bias_ratio from empty draw history")
    
    sorted_dates = sorted(
        draw_history_log.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )
    
    if not sorted_dates:
        print(f"\n❌ CRITICAL ERROR: No draws found in history log.")
        raise ValueError("Draw history contains no draws")
    
    latest_date, latest_data = sorted_dates[-1]
    bias_ratios = latest_data.get('all_numbers_bias_ratios', {})
    
    if not bias_ratios:
        print(f"\n❌ CRITICAL ERROR: 'all_numbers_bias_ratios' missing from latest draw.")
        raise ValueError("Latest draw missing required bias ratio data")
    
    result = {}
    for num in range(1, max_number + 1):
        result[num] = bias_ratios.get(num, 1.0)
    
    print(f"✓ Extracted 'win_bias_ratio' from latest draw ({latest_date})")
    return result