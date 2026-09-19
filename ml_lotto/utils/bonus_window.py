"""
bonus_window.py
===============
Calculate current bonus window dynamically from draw history.

This ensures bonus-to-main predictions always use the most recent bonus data
instead of relying on stale JSON files.
"""

from typing import Dict, List, Any


def calculate_current_bonus_window(
    all_draws: List[Dict[str, Any]],
    window_size: int = 10,
    hmc_data: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Calculate the current bonus window from the most recent draws.

    Args:
        all_draws: List of all historical draws
        window_size: Number of recent draws to check (default 10)
        hmc_data: Optional HMC data for category and freshness info

    Returns:
        List of bonus numbers with metadata, ordered by recency (most recent first)

    Format:
        [
            {
                'number': 35,
                'bonus_date': '2025-11-08',
                'draws_ago': 0,
                'category': 'hot',
                'freshness': 1
            },
            ...
        ]
    """
    if not all_draws:
        return []

    bonus_window = []
    draws_checked = 0

    # Start from most recent draw and work backwards
    for draw_idx in range(len(all_draws) - 1, -1, -1):
        if draws_checked >= window_size:
            break

        draw = all_draws[draw_idx]

        # Get bonus number from draw (try both keys for compatibility)
        bonus_num = draw.get('bonus_number') or draw.get('bonus')

        if bonus_num:
            # Get date
            draw_date = draw.get('date', 'unknown')

            # Get category and freshness if HMC data available
            category = 'medium'
            freshness = 0

            if hmc_data and str(bonus_num) in hmc_data:
                num_data = hmc_data[str(bonus_num)]
                category = num_data.get('category', 'medium')

                # Calculate freshness bin
                recent_data = num_data.get('recent', {})
                last_5 = recent_data.get('last_5', 0)

                # Freshness logic: C0=2+, C1=1, C2+=0
                if last_5 >= 2:
                    freshness = 0
                elif last_5 == 1:
                    freshness = 1
                else:
                    freshness = 2

            bonus_window.append({
                'number': bonus_num,
                'bonus_date': draw_date,
                'draws_ago': draws_checked,
                'category': category,
                'freshness': freshness
            })

        draws_checked += 1

    return bonus_window


def bonus_window_positions(draws: List[Dict[str, Any]], window_size: int = 10) -> Dict[int, int]:
    """
    Map each bonus ball of the last window_size draws to how many draws ago it was drawn.

    The one definition the Bonus-to-Main model uses in training (history cut at each draw)
    and serving (full history), so the two cannot drift (F-40). The loop runs oldest to
    newest and overwrites, so a ball that was the bonus twice keeps the most recent of the
    two - it kept the older one until F-36.
    """
    n = len(draws)
    positions = {}
    for prev_idx in range(max(0, n - window_size), n):
        bonus_num = draws[prev_idx].get('bonus_number') or draws[prev_idx].get('bonus')
        if bonus_num:
            positions[bonus_num] = n - prev_idx - 1
    return positions


def get_bonus_window_numbers(bonus_window: List[Dict[str, Any]]) -> List[int]:
    """
    Extract just the numbers from a bonus window.

    Args:
        bonus_window: Bonus window from calculate_current_bonus_window()

    Returns:
        List of bonus numbers (may contain duplicates)
    """
    return [entry['number'] for entry in bonus_window]


def get_unique_bonus_window_numbers(bonus_window: List[Dict[str, Any]]) -> List[int]:
    """
    Extract unique numbers from a bonus window, preserving order.

    Args:
        bonus_window: Bonus window from calculate_current_bonus_window()

    Returns:
        List of unique bonus numbers (most recent appearance kept)
    """
    seen = set()
    unique_numbers = []

    for entry in bonus_window:
        num = entry['number']
        if num not in seen:
            unique_numbers.append(num)
            seen.add(num)

    return unique_numbers


def find_number_in_bonus_window(
    number: int,
    bonus_window: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Find a specific number in the bonus window.

    Args:
        number: The number to find
        bonus_window: Bonus window from calculate_current_bonus_window()

    Returns:
        Dictionary with number's bonus window info, or None if not found
    """
    for entry in bonus_window:
        if entry['number'] == number:
            return entry

    return None
