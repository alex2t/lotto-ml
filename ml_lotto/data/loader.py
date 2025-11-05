"""
data_loader.py
==============
Handles loading and parsing of all data files with strict validation.

VERSION: 3.2 (Strict Validation Edition)
- Removed fallback defaults
- Added comprehensive error handling
- Clear user instructions on failure
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
        
    Raises:
        FileNotFoundError: If the data file doesn't exist
        ValueError: If the data is invalid or corrupted
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n❌ CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains historical draw data required for training.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n❌ CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n❌ CRITICAL ERROR: {filename} is empty.")
        print(f"   The file exists but contains no data.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
    # Convert dictionary (keyed by date) to a list of draw records
    draw_list = []
    for draw_date, draw_data in data.items():
        # Combine main and bonus winning numbers into a single list
        winning_numbers = []
        bonus_number = None
        
        # The structure is in 'winning_numbers_details'
        winning_numbers_details = draw_data.get('winning_numbers_details', [])
        
        if not winning_numbers_details:
            print(f"\n⚠️  WARNING: Draw {draw_date} has no winning_numbers_details")
            continue
        
        for detail in winning_numbers_details:
            number = detail.get('number')
            if number is None:
                continue
            winning_numbers.append(number)
            if detail.get('is_bonus', False):
                bonus_number = number
        
        if not winning_numbers:
            print(f"\n⚠️  WARNING: Draw {draw_date} has no valid winning numbers")
            continue
        
        draw_list.append({
            'date': draw_date,
            'draw_index': draw_data.get('draw_index', 0),
            'numbers': winning_numbers,
            'bonus_number': bonus_number
        })
    
    if not draw_list:
        print(f"\n❌ CRITICAL ERROR: No valid draws found in {filename}")
        print(f"   The file contains data but no parseable draw records.")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"No valid draws in data file: {filename}")
    
    # Sort chronologically by draw index (ensures correct order for lookback calculations)
    draw_list.sort(key=lambda x: x['draw_index'])
    
    print(f"✓ Loaded {len(draw_list)} historical draws from {filename}")
    print(f"  Purpose: ML training labels + custom feature generation")
    print(f"  Date range: {draw_list[0]['date']} to {draw_list[-1]['date']}")
    
    return draw_list


def load_hmc_json(filename: str) -> Dict[str, Any]:
    """
    Load per-number HMC data.
    
    Returns:
        Dictionary mapping number -> statistics
        
    Raises:
        FileNotFoundError: If the data file doesn't exist
        ValueError: If the data is invalid
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n❌ CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains per-number statistics required for features.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n❌ CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n❌ CRITICAL ERROR: {filename} is empty.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
    # Filter out analysis section if present
    filtered_data = {k: v for k, v in data.items() if k != 'analysis'}
    
    if not filtered_data:
        print(f"\n❌ CRITICAL ERROR: No number data found in {filename}")
        print(f"   Expected data for numbers 1-{MAX_NUMBER}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"No number data in file: {filename}")
    
    print(f"✓ Loaded HMC data from {filename}")
    print(f"  Purpose: ML training features + number categorization")
    print(f"  Numbers tracked: {len(filtered_data)}")
    
    return filtered_data


def load_draw_history_with_bias_ratios(filename: str) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Load draw history and return both the draw list and the full history log.
    
    Returns:
        Tuple of (draw_list, full_history_log)
        
    Raises:
        FileNotFoundError: If the data file doesn't exist
        ValueError: If the data is invalid
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n❌ CRITICAL ERROR: {filename} not found.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n❌ CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n❌ CRITICAL ERROR: {filename} is empty.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
    # Convert dictionary to list (for compatibility)
    draw_list = []
    for draw_date, draw_data in data.items():
        winning_numbers = []
        bonus_number = None
        
        winning_numbers_details = draw_data.get('winning_numbers_details', [])
        
        for detail in winning_numbers_details:
            number = detail.get('number')
            if number is None:
                continue
            winning_numbers.append(number)
            if detail.get('is_bonus', False):
                bonus_number = number
        
        if winning_numbers:
            draw_list.append({
                'date': draw_date,
                'draw_index': draw_data.get('draw_index', 0),
                'numbers': winning_numbers,
                'bonus_number': bonus_number
            })
    
    if not draw_list:
        print(f"\n❌ CRITICAL ERROR: No valid draws found in {filename}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"No valid draws in data file: {filename}")
    
    draw_list.sort(key=lambda x: x['draw_index'])
    
    print(f"✓ Loaded {len(draw_list)} historical draws from {filename}")
    print(f"  Includes: bias ratios, freshness patterns, and full draw details")
    
    return draw_list, data


def load_odds_json(filename: str) -> Dict[str, Any]:
    """
    Load HMC distribution and odds data.
    
    Returns:
        Dictionary with HMC patterns and consecutive data
        
    Raises:
        FileNotFoundError: If the data file doesn't exist
        ValueError: If the data is invalid
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n❌ CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains HMC patterns and consecutive analysis.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n❌ CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n❌ CRITICAL ERROR: {filename} is empty.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
    # Validate essential sections
    if 'hmc' not in data:
        print(f"\n⚠️  WARNING: 'hmc' section missing from {filename}")
    if 'patterns' not in data:
        print(f"\n⚠️  WARNING: 'patterns' section missing from {filename}")
    
    print(f"✓ Loaded odds data from {filename}")
    print(f"  Purpose: Display HMC patterns + consecutive pair analysis")
    
    return data


def load_freshness_config(filename: str) -> Tuple[int, int, str, Dict[int, float]]:
    """
    Load and extract dynamic freshness parameters and the top pattern distribution.
    
    Returns:
        Tuple of (W, C_max, recent_key, top_pattern_dist)
        top_pattern_dist: {bin_index: normalized_weight}
        
    Raises:
        FileNotFoundError: If the data file doesn't exist
        ValueError: If the data is invalid or incomplete
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n❌ CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains freshness pattern analysis required for predictions.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n❌ CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n❌ CRITICAL ERROR: {filename} is empty.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
    # 1. Extract dynamic configuration
    W = data.get('window_size_W')
    C_max = data.get('c_max_threshold')
    recent_key = data.get('recent_count_key')
    
    if W is None or C_max is None or recent_key is None:
        print(f"\n❌ CRITICAL ERROR: Missing required configuration in {filename}")
        print(f"   Expected: window_size_W, c_max_threshold, recent_count_key")
        print(f"   Found: W={W}, C_max={C_max}, recent_key={recent_key}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Incomplete configuration in {filename}")
    
    # 2. Extract top pattern and calculate normalized distribution weights
    analysis_list = data.get('distribution_analysis_7_numbers', [])
    if not analysis_list:
        print(f"\n❌ CRITICAL ERROR: 'distribution_analysis_7_numbers' is empty in {filename}")
        print(f"   No pattern data found for freshness analysis.")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"No pattern data in {filename}")
    
    top_pattern = analysis_list[0]
    
    # Calculate total count of numbers in the top pattern (should be 7)
    total_numbers = 0
    for i in range(C_max + 1):
        if i < C_max:
            count_key = f'C{i}'
        else:
            count_key = f'C_GE_{C_max}'
        
        count = top_pattern.get(count_key, 0)
        total_numbers += count
    
    if total_numbers != 7:
        print(f"\n⚠️  WARNING: Top pattern total is {total_numbers}, expected 7.")
        print(f"   Pattern: {top_pattern.get('pattern', 'unknown')}")
        print(f"   Continuing with normalization anyway...")
        if total_numbers == 0:
            total_numbers = 7.0
    
    # Create dynamic distribution map: {bin_index: normalized_weight}
    top_pattern_dist = {}
    for i in range(C_max + 1):
        if i < C_max:
            count_key = f'C{i}'
        else:
            count_key = f'C_GE_{C_max}'
        
        count = top_pattern.get(count_key, 0)
        top_pattern_dist[i] = count / total_numbers
    
    print(f"✓ Loaded Freshness Config: W={W}, C_max={C_max}, key={recent_key}")
    print(f"  Top pattern: {top_pattern.get('pattern', 'unknown')}")
    print(f"  Pattern weights: {top_pattern_dist}")
    
    return W, C_max, recent_key, top_pattern_dist


def get_most_likely_hmc_pattern(odds_data: Dict[str, Any]) -> Tuple[int, int, int, float]:
    """
    Extract the most likely HMC distribution pattern.
    
    Returns:
        Tuple of (hot_count, medium_count, cold_count, percentage)
    """
    if 'hmc' not in odds_data:
        print(f"\n⚠️  WARNING: HMC distribution not found in odds data.")
        print(f"   Using neutral default pattern: 2-3-2")
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
        if len(parts) != 3:
            print(f"\n⚠️  WARNING: Invalid HMC pattern format: {best_pattern}")
            return (2, 3, 2, 0.0)
        
        try:
            hot_count = int(parts[0])
            medium_count = int(parts[1])
            cold_count = int(parts[2])
            print(f"✓ Most likely HMC pattern: {best_pattern} ({best_percentage:.2f}%)")
            return (hot_count, medium_count, cold_count, best_percentage)
        except ValueError:
            print(f"\n⚠️  WARNING: Could not parse HMC pattern: {best_pattern}")
            return (2, 3, 2, 0.0)
    
    print(f"\n⚠️  WARNING: No HMC patterns found. Using default: 2-3-2")
    return (2, 3, 2, 0.0)