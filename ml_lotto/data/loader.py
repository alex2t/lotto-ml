# ml_lotto/data/loader.py
"""
data_loader.py
==============
Handles loading and parsing of all data files with strict validation.

VERSION: 3.4 (Bonus Ball Edition)
- Added load_bonus_analysis function
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
        [OK] ML Training Labels (y = 1 if number won, 0 if not)
        [OK] Custom Feature Generation (days since bonus hit)
        [OK] NEW: Bonus hit analysis features
    
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
        print(f"\n[ERROR] CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains historical draw data required for training.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n[ERROR] CRITICAL ERROR: {filename} is empty.")
        print(f"   The file exists but contains no data.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
    draw_list = []
    for draw_date, draw_data in data.items():
        winning_numbers = []
        bonus_number = None
        
        winning_numbers_details = draw_data.get('winning_numbers_details', [])
        
        if not winning_numbers_details:
            print(f"\n[WARNING] WARNING: Draw {draw_date} has no winning_numbers_details")
            continue
        
        for detail in winning_numbers_details:
            number = detail.get('number')
            if number is None:
                continue
            winning_numbers.append(number)
            if detail.get('is_bonus', False):
                bonus_number = number
        
        if not winning_numbers:
            print(f"\n[WARNING] WARNING: Draw {draw_date} has no valid winning numbers")
            continue
        
        draw_list.append({
            'date': draw_date,
            'draw_index': draw_data.get('draw_index', 0),
            'numbers': winning_numbers,
            'bonus_number': bonus_number
        })
    
    if not draw_list:
        print(f"\n[ERROR] CRITICAL ERROR: No valid draws found in {filename}")
        print(f"   The file contains data but no parseable draw records.")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"No valid draws in data file: {filename}")
    
    draw_list.sort(key=lambda x: x['draw_index'])
    
    print(f"[OK] Loaded {len(draw_list)} historical draws from {filename}")
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
        print(f"\n[ERROR] CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains per-number statistics required for features.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n[ERROR] CRITICAL ERROR: {filename} is empty.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
    filtered_data = {k: v for k, v in data.items() if k != 'analysis'}
    
    if not filtered_data:
        print(f"\n[ERROR] CRITICAL ERROR: No number data found in {filename}")
        print(f"   Expected data for numbers 1-{MAX_NUMBER}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"No number data in file: {filename}")
    
    print(f"[OK] Loaded HMC data from {filename}")
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
        print(f"\n[ERROR] CRITICAL ERROR: {filename} not found.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n[ERROR] CRITICAL ERROR: {filename} is empty.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
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
        print(f"\n[ERROR] CRITICAL ERROR: No valid draws found in {filename}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"No valid draws in data file: {filename}")
    
    draw_list.sort(key=lambda x: x['draw_index'])
    
    print(f"[OK] Loaded {len(draw_list)} historical draws from {filename}")
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
        print(f"\n[ERROR] CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains HMC patterns and consecutive analysis.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n[ERROR] CRITICAL ERROR: {filename} is empty.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
    if 'hmc' not in data:
        print(f"\n[WARNING] WARNING: 'hmc' section missing from {filename}")
    if 'patterns' not in data:
        print(f"\n[WARNING] WARNING: 'patterns' section missing from {filename}")
    
    print(f"[OK] Loaded odds data from {filename}")
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
        print(f"\n[ERROR] CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains freshness pattern analysis required for predictions.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n[ERROR] CRITICAL ERROR: {filename} is empty.")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to regenerate data.")
        raise ValueError(f"Empty data file: {filename}")
    
    W = data.get('window_size_W')
    C_max = data.get('c_max_threshold')
    recent_key = data.get('recent_count_key')
    
    if W is None or C_max is None or recent_key is None:
        print(f"\n[ERROR] CRITICAL ERROR: Missing required configuration in {filename}")
        print(f"   Expected: window_size_W, c_max_threshold, recent_count_key")
        print(f"   Found: W={W}, C_max={C_max}, recent_key={recent_key}")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"Incomplete configuration in {filename}")
    
    analysis_list = data.get('distribution_analysis_7_numbers', [])
    if not analysis_list:
        print(f"\n[ERROR] CRITICAL ERROR: 'distribution_analysis_7_numbers' is empty in {filename}")
        print(f"   No pattern data found for freshness analysis.")
        print(f"\n   REQUIRED ACTION: Delete {filename} and run 'python drawpick.py'")
        raise ValueError(f"No pattern data in {filename}")
    
    top_pattern = analysis_list[0]
    
    total_numbers = 0
    for i in range(C_max + 1):
        if i < C_max:
            count_key = f'C{i}'
        else:
            count_key = f'C_GE_{C_max}'
        
        count = top_pattern.get(count_key, 0)
        total_numbers += count
    
    if total_numbers != 7:
        print(f"\n[WARNING] WARNING: Top pattern total is {total_numbers}, expected 7.")
        print(f"   Pattern: {top_pattern.get('pattern', 'unknown')}")
        print(f"   Continuing with normalization anyway...")
        if total_numbers == 0:
            total_numbers = 7.0
    
    top_pattern_dist = {}
    for i in range(C_max + 1):
        if i < C_max:
            count_key = f'C{i}'
        else:
            count_key = f'C_GE_{C_max}'
        
        count = top_pattern.get(count_key, 0)
        top_pattern_dist[i] = count / total_numbers
    
    print(f"[OK] Loaded Freshness Config: W={W}, C_max={C_max}, key={recent_key}")
    print(f"  Top pattern: {top_pattern.get('pattern', 'unknown')}")
    print(f"  Pattern weights: {top_pattern_dist}")
    
    return W, C_max, recent_key, top_pattern_dist


def load_bonus_analysis(filename: str) -> Dict[str, Any]:
    """
    NEW: Load bonus ball analysis JSON.
    
    Args:
        filename: Path to lotto_bonus_analysis.json
        
    Returns:
        Dictionary with bonus ball analysis data
        
    Raises:
        FileNotFoundError: If the data file doesn't exist
        ValueError: If the data is invalid
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n[ERROR] CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains bonus ball analysis required for bonus prediction.")
        print(f"\n   REQUIRED ACTION: Ensure lotto_bonus_analysis.json is available.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        raise ValueError(f"Corrupted JSON file: {filename}")
    
    if not data:
        print(f"\n[ERROR] CRITICAL ERROR: {filename} is empty.")
        raise ValueError(f"Empty data file: {filename}")
    
    required_keys = ['per_number_bonus_profile', 'bonus_category_preference', 
                     'bonus_freshness_preference', 'bonus_timing_by_category']
    
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        print(f"\n[WARNING] WARNING: Missing keys in {filename}: {missing_keys}")
    
    print(f"[OK] Loaded bonus analysis from {filename}")
    print(f"  Purpose: Bonus ball prediction features")
    print(f"  Numbers tracked: {len(data.get('per_number_bonus_profile', {}))}")
    
    return data


def load_bonus_hit_analysis(draw_history_log: Dict[str, Any]) -> Dict[int, float]:
    """
    Extract bonus hit contribution scores from draw history.
    
    Returns:
        Dictionary mapping number -> bonus_hit_contribution (0.0 or 1.0)
    """
    latest_draw = None
    max_index = -1
    
    for draw_date, draw_data in draw_history_log.items():
        draw_index = draw_data.get('draw_index', -1)
        if draw_index > max_index:
            max_index = draw_index
            latest_draw = draw_data
    
    if not latest_draw:
        print(f"\n[WARNING] WARNING: No draws found in history for bonus hit analysis")
        return {num: 0.5 for num in range(1, MAX_NUMBER + 1)}
    
    bonus_contribution = {}
    winning_details = latest_draw.get('winning_numbers_details', [])
    
    for detail in winning_details:
        num = detail.get('number')
        if num:
            bonus_contribution[num] = detail.get('bonus_hit_contribution', 0.5)
    
    for num in range(1, MAX_NUMBER + 1):
        if num not in bonus_contribution:
            bonus_contribution[num] = 0.5
    
    print(f"[OK] Loaded bonus hit contributions from latest draw")
    return bonus_contribution


def load_freshness_weights(filename: str) -> Dict[int, float]:
    """
    Extract freshness weight calculation from freshness JSON.
    
    Returns:
        Dictionary mapping bin_index -> normalized_weight
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"\n[WARNING] WARNING: Could not load freshness weights from {filename}")
        return {0: 0.33, 1: 0.33, 2: 0.34}
    
    weight_calc = data.get('freshness_weight_calculation', {})
    
    if not weight_calc:
        print(f"\n[WARNING] WARNING: No freshness_weight_calculation in {filename}")
        return {0: 0.33, 1: 0.33, 2: 0.34}
    
    weights = {}
    for key, value in weight_calc.items():
        if key.startswith('C'):
            try:
                if key.startswith('C_GE_'):
                    bin_idx = int(key.split('_')[-1])
                else:
                    bin_idx = int(key[1:])
                weights[bin_idx] = value.get('normalized_weight', 0.0)
            except (ValueError, AttributeError):
                continue
    
    print(f"[OK] Loaded freshness weights: {weights}")
    return weights


def load_number_pair_frequency(filename: str) -> Dict[int, float]:
    """
    Extract number pair frequency scores from odds JSON.
    
    Returns:
        Dictionary mapping number -> normalized_pair_score
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"\n[WARNING] WARNING: Could not load pair frequency from {filename}")
        return {num: 0.5 for num in range(1, MAX_NUMBER + 1)}
    
    pair_freq = data.get('number_pair_frequency', {})
    
    if not pair_freq:
        print(f"\n[WARNING] WARNING: No number_pair_frequency in {filename}")
        return {num: 0.5 for num in range(1, MAX_NUMBER + 1)}
    
    scores = {}
    for num_str, stats in pair_freq.items():
        try:
            num = int(num_str)
            scores[num] = stats.get('normalized_score', 0.5)
        except (ValueError, AttributeError):
            continue
    
    for num in range(1, MAX_NUMBER + 1):
        if num not in scores:
            scores[num] = 0.5
    
    print(f"[OK] Loaded number pair frequencies")
    return scores


def load_bonus_to_main_patterns(filename: str) -> Dict[str, Any]:
    """
    NEW: Load bonus-to-main transition patterns JSON file.

    Args:
        filename: Path to bonus-to-main patterns JSON

    Returns:
        Dictionary containing:
        - per_number_transition_profile: Transition history per number
        - category_transition_weights: Category-specific weights
        - freshness_transition_weights: Freshness-specific weights
        - timing_decay_weights: Time-decay weights for 10-draw window
        - current_bonus_window: Last 10 bonus numbers
        - transition_prediction_factors: Calculated prediction factors
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        print(f"[OK] Loaded bonus-to-main transition patterns from {filename}")

        if 'metadata' in data:
            meta = data['metadata']
            print(f"  Transition rate: {meta.get('overall_transition_rate', 0)*100:.1f}%")
            print(f"  Bonus appearances: {meta.get('total_bonus_appearances', 0)}")

        return data
    except FileNotFoundError:
        print(f"\n[ERROR] ERROR: {filename} not found")
        print(f"   REQUIRED ACTION: Run 'python drawpick.py' to generate this file")
        return {}
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] ERROR: Invalid JSON in {filename}: {e}")
        return {}


def load_advanced_patterns(filename: str) -> Dict[str, Any]:
    """
    Load advanced pattern features (volatility, trend, temporal).

    This loads the output from lotto_analysis/analyzers/advanced_pattern_analyzer.py
    which provides volatility and trend features for improved ML prediction.

    Args:
        filename: Path to lotto_advanced_patterns.json

    Returns:
        Dictionary containing:
        - metadata: Analysis metadata
        - summary_statistics: Overall volatility and trend stats
        - per_number_features: Features for each number including:
            * appearance_volatility: Coefficient of variation of gaps
            * gap_consistency_score: 1/(1+volatility), bounded [0-1]
            * max_gap_ratio: Max gap / avg gap
            * appearance_trend: Recent vs older frequency change
            * appearance_acceleration: Very recent trend change

    Raises:
        FileNotFoundError: If the data file doesn't exist
        ValueError: If the data is invalid
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n[ERROR] CRITICAL ERROR: {filename} not found.")
        print(f"   This file contains advanced pattern features (volatility, trend).")
        print(f"\n   REQUIRED ACTION: Run 'python drawpick.py' to generate all data files.")
        raise FileNotFoundError(f"Missing required file: {filename}")
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] CRITICAL ERROR: Invalid JSON in {filename}")
        print(f"   Error details: {e}")
        raise ValueError(f"Corrupted JSON file: {filename}")

    if not data:
        print(f"\n[ERROR] CRITICAL ERROR: {filename} is empty.")
        raise ValueError(f"Empty data file: {filename}")

    # Validate structure
    required_keys = ['per_number_features', 'metadata']
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        print(f"\n[WARNING] WARNING: Missing keys in {filename}: {missing_keys}")

    print(f"[OK] Loaded advanced pattern features from {filename}")
    print(f"  Purpose: Volatility and trend features for ML prediction")

    # Display summary info
    if 'metadata' in data:
        meta = data['metadata']
        print(f"  Feature types: {', '.join(meta.get('feature_types', []))}")
        print(f"  Total numbers: {meta.get('total_numbers', 0)}")
        print(f"  Total draws: {meta.get('total_draws', 0)}")

    if 'summary_statistics' in data:
        summary = data['summary_statistics']
        if 'volatility' in summary:
            vol_stats = summary['volatility']
            print(f"  Volatility range: {vol_stats.get('min', 0):.2f} - {vol_stats.get('max', 0):.2f}")
        if 'trend' in summary:
            trend_stats = summary['trend']
            print(f"  Trending up: {trend_stats.get('trending_up_count', 0)} numbers")
            print(f"  Trending down: {trend_stats.get('trending_down_count', 0)} numbers")

    return data


def load_freshness_patterns_validated(filename: str) -> Dict[str, Any]:
    """
    Load scipy-validated freshness pattern analysis.

    Args:
        filename: Path to lotto_freshness_patterns_validated.json

    Returns:
        Dictionary containing:
        - metadata: Analysis metadata and statistical methods
        - pattern_distribution_test: Chi-square test results
        - bin_distribution_test: Bin counts tested against a fair draw (F-69)
        - top_pattern_validation: Top pattern significance
        - validated_weights: Statistically validated freshness weights
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n[WARNING] WARNING: {filename} not found.")
        print(f"   Using non-validated freshness weights as fallback")
        print(f"   RECOMMENDATION: Run 'python lotto_analysis/analyzers/freshness_pattern_analyzer.py'")
        return {}
    except json.JSONDecodeError as e:
        print(f"\n[WARNING] WARNING: Invalid JSON in {filename}: {e}")
        return {}

    if not data:
        return {}

    print(f"[OK] Loaded scipy-validated freshness patterns from {filename}")

    if 'pattern_distribution_test' in data:
        pattern_test = data['pattern_distribution_test']
        print(f"  Pattern chi-square p-value: {pattern_test.get('p_value', 1.0):.4f}")
        print(f"  Statistically significant: {pattern_test.get('significant', False)}")

    return data


def load_hmc_categorization_validated(filename: str) -> Dict[str, Any]:
    """
    Load scipy-validated HMC categorization analysis.

    Args:
        filename: Path to lotto_hmc_categorization_validated.json

    Returns:
        Dictionary containing:
        - metadata: Analysis metadata
        - anova_test: ANOVA results for category distinctness
        - pairwise_comparisons: Bonferroni-corrected t-tests
        - threshold_validation: Category overlap analysis
        - categorization_valid: Overall validation status
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n[WARNING] WARNING: {filename} not found.")
        print(f"   Using non-validated HMC categories as fallback")
        print(f"   RECOMMENDATION: Run 'python lotto_analysis/analyzers/hmc_categorization_analyzer.py'")
        return {}
    except json.JSONDecodeError as e:
        print(f"\n[WARNING] WARNING: Invalid JSON in {filename}: {e}")
        return {}

    if not data:
        return {}

    print(f"[OK] Loaded scipy-validated HMC categorization from {filename}")

    if 'anova_test' in data:
        anova = data['anova_test']
        print(f"  ANOVA p-value: {anova.get('p_value', 1.0):.4f}")
        print(f"  Categories statistically distinct: {anova.get('significant', False)}")
        print(f"  Effect size (eta^2): {anova.get('eta_squared', 0.0):.4f}")

    return data


def load_consecutive_pairs_validated(filename: str) -> Dict[str, Any]:
    """
    Load scipy-validated consecutive pair analysis.

    Args:
        filename: Path to lotto_consecutive_pairs_validated.json

    Returns:
        Dictionary containing:
        - metadata: Analysis metadata
        - overall_chi_square_test: Chi-square test for independence
        - top_pairs_validation: Binomial tests for top pairs
        - number_pair_scores: Per-number validated pair scores
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n[WARNING] WARNING: {filename} not found.")
        print(f"   Using non-validated pair scores as fallback")
        print(f"   RECOMMENDATION: Run 'python lotto_analysis/analyzers/consecutive_pair_analyzer.py'")
        return {}
    except json.JSONDecodeError as e:
        print(f"\n[WARNING] WARNING: Invalid JSON in {filename}: {e}")
        return {}

    if not data:
        return {}

    print(f"[OK] Loaded scipy-validated consecutive pairs from {filename}")

    if 'overall_chi_square_test' in data:
        chi2 = data['overall_chi_square_test']
        print(f"  Chi-square p-value: {chi2.get('p_value', 1.0):.4f}")
        print(f"  Pairs deviate from independence: {chi2.get('significant', False)}")

    if 'top_pairs_validation' in data:
        top_pairs = data['top_pairs_validation']
        print(f"  Significant pairs found: {top_pairs.get('num_significant', 0)}")

    return data


def load_odd_even_validated(filename: str) -> Dict[str, Any]:
    """
    Load scipy-validated odd/even distribution analysis.

    Args:
        filename: Path to lotto_odd_even_validated.json

    Returns:
        Dictionary containing:
        - metadata: Analysis metadata
        - overall_distribution_test: Chi-square test for odd/even balance
        - per_number_affinity: Binomial tests for each number's odd/even affinity
        - validated_scores: Per-number validated odd/even scores
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n[WARNING] WARNING: {filename} not found.")
        print(f"   Using non-validated odd/even scores as fallback")
        print(f"   RECOMMENDATION: Run 'python lotto_analysis/analyzers/odd_even_analyzer.py'")
        return {}
    except json.JSONDecodeError as e:
        print(f"\n[WARNING] WARNING: Invalid JSON in {filename}: {e}")
        return {}

    if not data:
        return {}

    print(f"[OK] Loaded scipy-validated odd/even distribution from {filename}")

    if 'overall_distribution_test' in data:
        overall = data['overall_distribution_test']
        print(f"  Chi-square p-value: {overall.get('p_value', 1.0):.4f}")
        print(f"  Distribution balanced: {not overall.get('significant', True)}")
        print(f"  Odd: {overall.get('odd_percentage', 50.0):.1f}%, Even: {overall.get('even_percentage', 50.0):.1f}%")

    if 'num_significant_deviations' in data:
        print(f"  Significant deviations: {data.get('num_significant_deviations', 0)}/47")

    return data


def load_sum_contribution_validated(filename: str) -> Dict[str, Any]:
    """
    Load scipy-validated sum contribution analysis.

    Args:
        filename: Path to lotto_sum_contribution_validated.json

    Returns:
        Dictionary containing:
        - metadata: Analysis metadata
        - overall_distribution: Sum distribution statistics
        - per_number_contribution: T-test results for each number
        - anova_analysis: ANOVA for number ranges
        - validated_scores: Per-number validated contribution scores
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n[WARNING] WARNING: {filename} not found.")
        print(f"   Using non-validated sum contribution scores as fallback")
        print(f"   RECOMMENDATION: Run 'python lotto_analysis/analyzers/sum_contribution_analyzer.py'")
        return {}
    except json.JSONDecodeError as e:
        print(f"\n[WARNING] WARNING: Invalid JSON in {filename}: {e}")
        return {}

    if not data:
        return {}

    print(f"[OK] Loaded scipy-validated sum contribution from {filename}")

    if 'overall_distribution' in data:
        overall = data['overall_distribution']
        print(f"  Mean sum: {overall.get('mean', 0):.1f}, Std: {overall.get('std', 0):.1f}")

    if 'anova_analysis' in data:
        anova = data['anova_analysis']
        print(f"  ANOVA p-value: {anova.get('p_value', 1.0):.4f}")
        print(f"  Number ranges significantly differ: {anova.get('significant', False)}")

    if 'num_significant_contributions' in data:
        print(f"  Significant contributions: {data.get('num_significant_contributions', 0)}/47")

    return data


def load_range_spread_validated(filename: str) -> Dict[str, Any]:
    """
    Load scipy-validated range spread analysis.

    Args:
        filename: Path to lotto_range_spread_validated.json

    Returns:
        Dictionary containing:
        - metadata: Analysis metadata
        - overall_distribution: Range distribution statistics
        - per_number_contribution: T-test results for each number
        - levene_analysis: Levene's test for variance equality
        - correlation_analysis: Position correlation results
        - validated_scores: Per-number validated range spread scores
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"\n[WARNING] WARNING: {filename} not found.")
        print(f"   Using non-validated range spread scores as fallback")
        print(f"   RECOMMENDATION: Run 'python lotto_analysis/analyzers/range_spread_analyzer.py'")
        return {}
    except json.JSONDecodeError as e:
        print(f"\n[WARNING] WARNING: Invalid JSON in {filename}: {e}")
        return {}

    if not data:
        return {}

    print(f"[OK] Loaded scipy-validated range spread from {filename}")

    if 'overall_distribution' in data:
        overall = data['overall_distribution']
        print(f"  Mean range: {overall.get('mean', 0):.1f}, Std: {overall.get('std', 0):.1f}")

    if 'levene_analysis' in data:
        levene = data['levene_analysis']
        print(f"  Levene's p-value: {levene.get('p_value', 1.0):.4f}")
        print(f"  Variances differ by position: {levene.get('significant', False)}")

    if 'num_significant_contributions' in data:
        print(f"  Significant contributions: {data.get('num_significant_contributions', 0)}/47")

    return data


def get_most_likely_hmc_pattern(odds_data: Dict[str, Any]) -> Tuple[int, int, int, float]:
    """
    Extract the most likely HMC distribution pattern.

    Returns:
        Tuple of (hot_count, medium_count, cold_count, percentage)
    """
    if 'hmc' not in odds_data:
        print(f"\n[WARNING] WARNING: HMC distribution not found in odds data.")
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
            print(f"\n[WARNING] WARNING: Invalid HMC pattern format: {best_pattern}")
            return (2, 3, 2, 0.0)

        try:
            hot_count = int(parts[0])
            medium_count = int(parts[1])
            cold_count = int(parts[2])
            print(f"[OK] Most likely HMC pattern: {best_pattern} ({best_percentage:.2f}%)")
            return (hot_count, medium_count, cold_count, best_percentage)
        except ValueError:
            print(f"\n[WARNING] WARNING: Could not parse HMC pattern: {best_pattern}")
            return (2, 3, 2, 0.0)

    print(f"\n[WARNING] WARNING: No HMC patterns found. Using default: 2-3-2")
    return (2, 3, 2, 0.0)