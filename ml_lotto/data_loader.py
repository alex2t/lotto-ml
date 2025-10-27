"""
data_loader.py
==============
Handles loading and parsing of all data files:
- Draw History JSON: Historical draw results (labels for ML, source for new feature)
- HMC JSON: Per-number statistics (features for ML)
- Odds JSON: HMC distribution patterns (informational)
"""

import json
import pandas as pd
from typing import Dict, Any, List, Tuple
from ml_lotto.config import MAX_NUMBER


def load_draw_history_json(filename: str) -> List[Dict[str, Any]]:
    """
    Load and parse the comprehensive lotto draw history JSON file.
    
    USED FOR:
        ✓ ML Training Labels (y = 1 if number won, 0 if not)
        ✓ Custom Feature Generation (days since bonus hit)
    
    Returns:
        List of dictionaries with draw details, sorted by draw_index.
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Convert dictionary (keyed by date) to a list of draw records
        draw_list = []
        for draw_date, draw_data in data.items():
            # Combine main and bonus winning numbers into a single list
            winning_numbers = []
            bonus_number = None
            
            # The structure is in 'winning_numbers_details'
            for detail in draw_data.get('winning_numbers_details', []):
                number = detail['number']
                winning_numbers.append(number)
                if detail['is_bonus']:
                    bonus_number = number
            
            draw_list.append({
                'date': draw_date,
                'draw_index': draw_data['draw_index'],
                'numbers': winning_numbers, # All 7 numbers
                'bonus_number': bonus_number # Only the bonus number
            })
        
        # Sort chronologically by draw index (ensures correct order for lookback calculations)
        draw_list.sort(key=lambda x: x['draw_index'])
        
        print(f"✓ Loaded {len(draw_list)} historical draws from {filename}")
        print(f"  Purpose: ML training labels + custom feature generation (replaces CSV)")
        return draw_list
    
    except FileNotFoundError:
        print(f"Error: {filename} not found. Cannot proceed without draw history.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filename}: {e}")
        return []


def load_hmc_json(filename: str) -> Dict[str, Any]:
    """
    Load per-number HMC data.
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        print(f"✓ Loaded HMC data from {filename}")
        print(f"  Purpose: ML training features + number categorization")
        return {k: v for k, v in data.items() if k != 'analysis'}
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filename}")
        return {}


def load_odds_json(filename: str) -> Dict[str, Any]:
    """
    Load HMC distribution and odds data.
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        print(f"✓ Loaded odds data from {filename}")
        print(f"  Purpose: Display most common HMC pattern (informational)")
        return data
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filename}")
        return {}


def get_most_likely_hmc_pattern(odds_data: Dict[str, Any]) -> Tuple[int, int, int, float]:
    """Extract the most likely HMC distribution pattern."""
    if 'hmc' not in odds_data:
        print("Warning: HMC distribution not found. Using default 2-3-2.")
        return (2, 3, 2, 0.0)
    
    hmc_dist = odds_data['hmc']
    best_pattern = None
    best_percentage = 0
    
    for pattern_str, data in hmc_dist.items():
        percentage = data.get('percentage', 0)
        if percentage > best_percentage:
            best_percentage = percentage
            best_pattern = pattern_str
    
    if best_pattern:
        parts = best_pattern.split('-')
        hot_count = int(parts[0])
        medium_count = int(parts[1])
        cold_count = int(parts[2])
        print(f"✓ Most likely HMC pattern: {best_pattern} ({best_percentage:.2f}%)")
        return (hot_count, medium_count, cold_count, best_percentage)
    
    return (2, 3, 2, 0.0)