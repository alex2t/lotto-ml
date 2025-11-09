"""
bonus.py
========
Bonus ball related feature calculations.

Features in this module:
- was_recent_bonus: Binary indicator if number was bonus in recent draws

NOTE: Removed duplicate feature:
- bonus_hit_target_alignment → use bonus_hit_contribution (JSON version)

All features use data from lotto_draw_history.json
"""

from typing import Dict, Any, List
from ml_lotto.config import MAX_NUMBER


def calculate_was_recent_bonus(
    all_draws: List[Dict[str, Any]],
    lookback_draws: int = 10
) -> Dict[int, int]:
    """
    Binary indicator: Was this number a bonus ball in the last N draws?

    CRITICAL FEATURE: 71.28% of draws have ≥1 recent bonus hit!

    Args:
        all_draws: List of draw dictionaries from lotto_draw_history.json
        lookback_draws: Number of recent draws to consider (default: 10)

    Returns:
        Dictionary mapping number -> 1 (was recent bonus) or 0 (was not)
    """
    recent_draws = all_draws[-lookback_draws:] if len(all_draws) >= lookback_draws else all_draws

    recent_bonus_numbers = set()
    for draw in recent_draws:
        bonus_num = draw.get('bonus_number')
        if bonus_num is not None and 1 <= bonus_num <= MAX_NUMBER:
            recent_bonus_numbers.add(bonus_num)

    was_recent_bonus = {}
    for num in range(1, MAX_NUMBER + 1):
        was_recent_bonus[num] = 1 if num in recent_bonus_numbers else 0

    print(f"✓ Custom feature 'was_recent_bonus' calculated (last {lookback_draws} draws).")
    print(f"  {len(recent_bonus_numbers)} numbers were recent bonus balls: {sorted(recent_bonus_numbers)}")

    return was_recent_bonus