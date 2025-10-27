"""
Hot-Medium-Cold (HMC) analysis for lottery draws
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple
from ..config import TRAINING_DATA, MAX_NUMBER, SCENARIOS # Import SCENARIOS
from .frequency_analyzer import calculate_frequency, get_hot_cold, get_draw_metrics


# Derive the actual window sizes from SCENARIOS
HISTORY_WINDOWS_DATA = [s["window"] for s in SCENARIOS] # [5, 7, 10, 15]


def get_days_difference(date_str_latest: str, date_str_oldest: str) -> int:
    """
    Calculate the number of days between two 'YYYY-MM-DD' date strings.
    """
    try:
        d1 = datetime.strptime(date_str_latest, "%Y-%m-%d")
        d2 = datetime.strptime(date_str_oldest, "%Y-%m-%d")
        return (d1 - d2).days
    except ValueError:
        return None


def process_hmc_analysis(all_draws: List[Dict]) -> Tuple[Dict, Dict, Dict, Dict, Dict]:
    """
    Performs HMC and draw range analysis on all draws, 
    and collects per-draw history data.
    """
    # Pre-analysis Setup
    last_seen_date = {}
    first_draw_date = all_draws[0]["date"]
    
    for num in range(1, MAX_NUMBER + 1):
        last_seen_date[num] = first_draw_date

    # Phase 1: Training
    training_draws = all_draws[:TRAINING_DATA]
    frequency_count = calculate_frequency(training_draws)
    
    # Update last_seen_date based on training draws
    for draw in training_draws:
        for number in draw["numbers"]:
            last_seen_date[number] = draw["date"]

    # Phase 2: Rolling analysis and History Logging
    categorization_history = {}
    hmc_distribution_counts = defaultdict(int)
    draw_history_log = {}
    
    max_history_window = max(HISTORY_WINDOWS_DATA)
    
    for i in range(TRAINING_DATA, len(all_draws)):
        current_draw = all_draws[i]
        draw_date = current_draw["date"]
        winning_numbers = current_draw["numbers"]
        
        # Categorize based on current frequency counts (PRIOR to this draw)
        categories = get_hot_cold(frequency_count)
        
        # Calculate Draw Metrics
        draw_range, rating_counts, hmc_dist = get_draw_metrics(winning_numbers, categories)
        
        # Record the HMC distribution
        hmc_distribution_counts[hmc_dist] += 1
        
        # Store result
        categorization_history[draw_date] = {
            "draw_range": draw_range,
            "frequency_rating": rating_counts,
            "hmc_distribution": hmc_dist,
            **categories
        }

        # Build winning_numbers_details for draw history
        winning_numbers_details = []
        hot_set = set(categories['hot_numbers'])
        medium_set = set(categories['medium_numbers'])
        
        # Draws preceding the current one (for recent counts)
        # Use the actual window size derived from SCENARIOS
        preceding_draws = all_draws[max(0, i - max_history_window): i]
        
        # Determine the bonus number (it is the last number in the list from data_loader)
        bonus_number = winning_numbers[-1] if winning_numbers else None
        
        for number in winning_numbers:
            # 1. Determine Category
            category = 'cold'
            if number in hot_set:
                category = 'hot'
            elif number in medium_set:
                category = 'medium'
            
            # 2. Days Since Last Hit
            last_hit_date = last_seen_date.get(number, first_draw_date)
            days_since_last_hit = get_days_difference(draw_date, last_hit_date)
            
            # 3. Recent Counts (FIXED LOGIC: Key name is window_size - 1)
            recent_counts = {}
            for w in HISTORY_WINDOWS_DATA:
                window_draws = preceding_draws[-w:]
                count = sum(1 for draw in window_draws if number in draw["numbers"])
                
                # The feature name uses the window size minus 1, e.g., 'last_4' for window 5
                recent_counts[f"last_{w - 1}"] = count 
            
            # 4. Determine if Bonus (only True if the number is the last one AND we expect a bonus)
            is_bonus = (number == bonus_number)
            
            winning_numbers_details.append({
                "number": number,
                "is_bonus": is_bonus,
                "category": category,
                "days_since_last_hit": days_since_last_hit,
                "recent_counts": recent_counts
            })
        
        # Store Draw History Log Entry
        draw_history_log[draw_date] = {
            "draw_index": i,
            "draw_date": draw_date,
            "hmc_summary": {
                "hot_count": rating_counts['hot'],
                "medium_count": rating_counts['medium'],
                "cold_count": rating_counts['cold'],
                "hmc_distribution": hmc_dist,
                "draw_range": draw_range
            },
            "categories_pre_draw": {
                'hot_numbers': list(categories['hot_numbers']),
                'medium_numbers': list(categories['medium_numbers']),
                'cold_numbers': list(categories['cold_numbers'])
            },
            "winning_numbers_details": winning_numbers_details
        }
        
        # Update Frequency and Last Seen Date (POST-DRAW)
        for number in winning_numbers:
            frequency_count[number] += 1
            last_seen_date[number] = draw_date

    # Final categories
    final_categories = get_hot_cold(frequency_count)
    
    return (categorization_history, frequency_count, dict(hmc_distribution_counts), 
            final_categories, draw_history_log)