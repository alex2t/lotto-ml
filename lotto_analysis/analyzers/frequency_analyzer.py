"""
Frequency analysis utilities for lottery numbers
"""

from collections import defaultdict
from typing import Dict, List
from ..config import MAX_NUMBER, HOT_COUNT, COLD_COUNT


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
