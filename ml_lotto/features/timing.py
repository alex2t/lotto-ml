"""
timing.py
=========
Time-based feature calculations.

Features in this module:
- days_since_bonus: Days since number was last drawn as bonus
- recency_zone_score: Score based on optimal recency windows
"""

from datetime import datetime
from typing import Dict, Any, List
from ml_lotto.config import MAX_NUMBER


def calculate_days_since_bonus(all_draws: List[Dict[str, Any]]) -> Dict[int, int]:
    """
    Calculate the days since each number was last drawn as a bonus ball.
    
    Scans historical draws in reverse order to find the most recent date
    each number appeared as the bonus ball.
    
    Args:
        all_draws: List of draw dictionaries from lotto_draw_history.json
        
    Returns:
        Dictionary mapping number -> days_since_bonus (999 if never)
    """
    now = datetime.now()
    days_since_bonus = {num: 999 for num in range(1, MAX_NUMBER + 1)}
    last_seen_date = {num: None for num in range(1, MAX_NUMBER + 1)}
    
    for draw in reversed(all_draws):
        draw_date = datetime.strptime(draw['date'], "%Y-%m-%d")
        bonus_num = draw.get('bonus_number')
        
        if bonus_num is not None and 1 <= bonus_num <= MAX_NUMBER:
            if last_seen_date[bonus_num] is None:
                last_seen_date[bonus_num] = draw_date

    for num in range(1, MAX_NUMBER + 1):
        if last_seen_date[num] is not None:
            days_since = (now - last_seen_date[num]).days
            days_since_bonus[num] = max(0, days_since)
    
    print(f"✓ Custom feature 'days_since_bonus' calculated.")
    return days_since_bonus


def calculate_recency_zone_score(days_since_last: int) -> float:
    """
    Score based on optimal recency windows from trend analysis.
    
    DATA-DRIVEN ZONES:
    - 0-14 days:   40.0% of winners → score 1.0
    - 14-30 days:  31.0% of winners → score 0.78
    - 30-60 days:  21.7% of winners → score 0.54
    - 60-120 days: 7.0% of winners  → score 0.18
    - 120+ days:   0.3% of winners  → score 0.01
    
    Args:
        days_since_last: Number of days since last appearance
        
    Returns:
        Score from 0.0 to 1.0 (higher = better timing)
    """
    if 0 <= days_since_last <= 14:
        return 1.0
    elif 14 < days_since_last <= 30:
        return 0.78
    elif 30 < days_since_last <= 60:
        return 0.54
    elif 60 < days_since_last <= 120:
        return 0.18
    else:
        return 0.01