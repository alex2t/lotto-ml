"""
Frequency analysis utilities for lottery numbers
"""

from collections import defaultdict
from typing import Dict, List
from datetime import datetime
from ..config import MAX_NUMBER, HOT_COUNT, COLD_COUNT


def calculate_days_since_last_hit(draws: List[Dict]) -> Dict[int, int]:
    """
    Calculate days since last hit for each number.

    Args:
        draws: List of draw dictionaries (sorted chronologically, oldest first)

    Returns:
        Dictionary mapping number to days since last appearance
    """
    days_since = {}

    # Get reference date (most recent draw)
    if draws and 'date' in draws[-1]:
        # Use the last draw date as reference (newest)
        date_str = draws[-1]['date']
        try:
            # Try YYYY-MM-DD format first
            most_recent = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                # Try YYYY/MM/DD format
                most_recent = datetime.strptime(date_str, "%Y/%m/%d")
            except ValueError:
                most_recent = datetime.now()
    else:
        most_recent = datetime.now()

    # Track last seen date for each number (iterate backwards to get most recent)
    last_seen = {}

    for draw in reversed(draws):
        date_str = draw.get('date', '')
        if not date_str:
            continue

        try:
            # Try YYYY-MM-DD format first
            draw_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                # Try YYYY/MM/DD format
                draw_date = datetime.strptime(date_str, "%Y/%m/%d")
            except ValueError:
                continue

        for number in draw["numbers"]:
            if number not in last_seen:
                last_seen[number] = draw_date

    # Calculate days since for all numbers
    for num in range(1, MAX_NUMBER + 1):
        if num in last_seen:
            delta = most_recent - last_seen[num]
            days_since[num] = delta.days
        else:
            days_since[num] = 9999  # Never appeared

    return days_since


def calculate_frequency(draws: List[Dict]) -> Dict[int, int]:
    """
    Calculate frequency counts for all numbers, including the Bonus number.
    
    Args:
        draws: List of draw dictionaries
        
    Returns:
        Dictionary mapping number to frequency count
    """
    frequency_count = defaultdict(int)
    for draw in draws:
        for number in draw["numbers"]:
            frequency_count[number] += 1
    
    # Ensure all numbers 1-MAX_NUMBER exist
    for num in range(1, MAX_NUMBER + 1):
        if num not in frequency_count:
            frequency_count[num] = 0
    
    return dict(frequency_count)


def get_hot_cold(frequency_count: Dict[int, int]) -> Dict[str, List[int]]:
    """
    Categorize numbers as Hot, Cold, or Medium based on frequency.

    Args:
        frequency_count: Dictionary of number frequencies

    Returns:
        Dictionary with hot_numbers, cold_numbers, and medium_numbers lists
    """
    sorted_numbers = sorted(frequency_count.items(), key=lambda x: (-x[1], x[0]))
    numbers_by_freq = [num for num, count in sorted_numbers]

    hot = numbers_by_freq[:HOT_COUNT]
    cold = numbers_by_freq[-COLD_COUNT:]
    medium = numbers_by_freq[HOT_COUNT:-COLD_COUNT]

    return {
        'hot_numbers': hot,
        'cold_numbers': cold,
        'medium_numbers': medium
    }


def get_hot_cold_by_recency(days_since: Dict[int, int], hot_threshold: int = 13, cold_threshold: int = 27) -> Dict[str, List[int]]:
    """
    Categorize numbers as Hot, Cold, or Medium based on RECENCY (days since last hit).

    VALIDATED THRESHOLDS from scipy ANOVA analysis:
    - Hot: appeared in last 13 days (33rd percentile)
    - Medium: appeared 13-27 days ago
    - Cold: appeared 27+ days ago (67th percentile)

    Args:
        days_since: Dictionary mapping number to days since last appearance
        hot_threshold: Maximum days for hot category (default: 13)
        cold_threshold: Minimum days for cold category (default: 27)

    Returns:
        Dictionary with hot_numbers, cold_numbers, and medium_numbers lists
    """
    hot_numbers = []
    medium_numbers = []
    cold_numbers = []

    for num, days in days_since.items():
        if days <= hot_threshold:
            hot_numbers.append(num)
        elif days >= cold_threshold:
            cold_numbers.append(num)
        else:
            medium_numbers.append(num)

    # Sort for consistency
    hot_numbers.sort()
    medium_numbers.sort()
    cold_numbers.sort()

    return {
        'hot_numbers': hot_numbers,
        'cold_numbers': cold_numbers,
        'medium_numbers': medium_numbers
    }


# In lotto_analysis/analyzers/frequency_analyzer.py

def get_draw_metrics(winning_numbers: List[int], categories: Dict) -> tuple:
    """
    Calculates Draw Range, Frequency Rating (Counts), and the HMC Distribution string.
    
    Args:
        winning_numbers: List of winning numbers
        categories: Dictionary containing hot/medium/cold number lists
        
    Returns:
        Tuple of (draw_range, rating_counts, hmc_distribution_string)
    """
    # 1. Draw Range
    draw_range = max(winning_numbers) - min(winning_numbers)
    
    # 2. Frequency Rating (Counts)
    rating_counts = {'hot': 0, 'medium': 0, 'cold': 0}
    
    hot_set = set(categories['hot_numbers'])
    medium_set = set(categories['medium_numbers'])
    
    for number in winning_numbers:
        if number in hot_set:
            rating_counts['hot'] += 1
        elif number in medium_set:
            rating_counts['medium'] += 1
        else:  # Must be Cold
            rating_counts['cold'] += 1
            
    # 3. HMC Distribution String (e.g., "2-3-2")
    # FIX: Use a simple, correct f-string syntax directly.
    hmc_distribution_string = (
        f"{rating_counts['hot']}-"
        f"{rating_counts['medium']}-"
        f"{rating_counts['cold']}"
    )
            
    return draw_range, rating_counts, hmc_distribution_string