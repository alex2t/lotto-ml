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
from collections import defaultdict


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

def load_draw_history_with_bias_ratios(filename: str) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Load draw history and return both the draw list and the full history log.
    
    Returns:
        Tuple of (draw_list, full_history_log)
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Convert dictionary to list (for compatibility)
        draw_list = []
        for draw_date, draw_data in data.items():
            winning_numbers = []
            bonus_number = None
            
            for detail in draw_data.get('winning_numbers_details', []):
                number = detail['number']
                winning_numbers.append(number)
                if detail['is_bonus']:
                    bonus_number = number
            
            draw_list.append({
                'date': draw_date,
                'draw_index': draw_data['draw_index'],
                'numbers': winning_numbers,
                'bonus_number': bonus_number
            })
        
        draw_list.sort(key=lambda x: x['draw_index'])
        
        print(f"✓ Loaded {len(draw_list)} historical draws from {filename}")
        return draw_list, data  # Return BOTH
    
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return [], {}


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


def load_freshness_config(filename: str) -> Tuple[int, int, str, Dict[int, float]]:
    """
    Load and extract dynamic freshness parameters and the top pattern distribution.
    
    Returns:
        Tuple of (W, C_max, recent_key, top_pattern_dist)
        top_pattern_dist: {bin_index: normalized_weight}
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # 1. Extract dynamic configuration
        W = data.get('window_size_W', 5)
        C_max = data.get('c_max_threshold', 3)
        recent_key = data.get('recent_count_key', 'last_4')
        
        # 2. Extract top pattern and calculate normalized distribution weights
        analysis_list = data.get('distribution_analysis_7_numbers', [])
        if not analysis_list:
            raise ValueError("Freshness distribution analysis is empty.")
            
        top_pattern = analysis_list[0]
        
        # Calculate total count of numbers in the top pattern (should be 7)
        total_numbers = sum(top_pattern.get(f'C{i}', 0) for i in range(C_max)) + top_pattern.get(f'C_GE_{C_max}', 0)
        
        if total_numbers != 7:
            print(f"Warning: Top pattern total is {total_numbers}, expected 7.")
            total_numbers = 7.0 # Use 7 for normalization even if error is found
            
        # Create dynamic distribution map: {bin_index: normalized_weight}
        top_pattern_dist = {}
        for i in range(C_max + 1):
            if i < C_max:
                # C0, C1, ..., C_max-1 bins
                count_key = f'C{i}'
            else:
                # C_max bin (C>=C_max)
                count_key = f'C_GE_{C_max}'
                
            count = top_pattern.get(count_key, 0)
            # Normalize to 0-1 scale (count / 7)
            top_pattern_dist[i] = count / total_numbers
            
        print(f"✓ Loaded Freshness Config: W={W}, C_max={C_max}")
        return W, C_max, recent_key, top_pattern_dist
        
    except FileNotFoundError:
        print(f"Error: {filename} not found. Using default freshness config.")
        # Default to W=5, C_max=3, recent_key='last_4', and a balanced distribution
        return 5, 3, 'last_4', {0: 0.4, 1: 0.4, 2: 0.1, 3: 0.1} # Default weights

    except Exception as e:
        print(f"Error loading freshness config: {e}. Using default config.")
        return 5, 3, 'last_4', {0: 0.4, 1: 0.4, 2: 0.1, 3: 0.1}


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