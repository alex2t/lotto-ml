# quickpick.py
"""
quickpick.py (main.py)
======================
Main entry point for the Lottery Prediction System V3.9

VERSION: 3.9 (Scipy Statistical Validation Edition)
- Complete scipy statistical validation across all features
- Concise output mode for essential information only
- Set VERBOSE = False for clean, focused output
"""

import warnings
warnings.filterwarnings('ignore')
import json
import time
import sys
from pathlib import Path


# OUTPUT MODE: Set to False for concise, essential output only
VERBOSE = False

import os
import contextlib

@contextlib.contextmanager
def suppress_output():
    """Suppress stdout when not in verbose mode."""
    if VERBOSE:
        yield
    else:
        with open(os.devnull, 'w') as devnull:
            old_stdout = sys.stdout
            sys.stdout = devnull
            try:
                yield
            finally:
                sys.stdout = old_stdout

from ml_lotto.config import (
    DRAW_HISTORY_JSON,
    HMC_JSON_INPUT,
    ODDS_JSON_INPUT,
    FRESHNESS_JSON_INPUT,
    DISTRIBUTION_STATS_JSON,
    BONUS_ANALYSIS_JSON,
    BONUS_TO_MAIN_JSON,
    LONG_TERM_PATTERNS_JSON,
    ADVANCED_PATTERNS_JSON,
    FRESHNESS_PATTERNS_VALIDATED_JSON,
    HMC_CATEGORIZATION_VALIDATED_JSON,
    CONSECUTIVE_PAIRS_VALIDATED_JSON,
    ODD_EVEN_VALIDATED_JSON,
    SUM_CONTRIBUTION_VALIDATED_JSON,
    RANGE_SPREAD_VALIDATED_JSON,
    ACTIVE_MODELS,
    BONUS_MODEL_CONFIG,
    BONUS_TO_MAIN_MODEL_CONFIG,
    MAX_NUMBER,
    TRAINING_START_DRAW,
    ENSEMBLE_MODE,
    ENSEMBLE_RUNS,
    RANDOM_SEED_BASE
)

from ml_lotto.data.loader import (
    load_hmc_json,
    load_odds_json,
    get_most_likely_hmc_pattern,
    load_draw_history_with_bias_ratios,
    load_freshness_config,
    load_bonus_hit_analysis,
    load_freshness_weights,
    load_number_pair_frequency,
    load_range_spread_analysis,
    load_odd_even_analysis,
    load_sum_contribution_analysis,
    load_bonus_analysis,
    load_bonus_to_main_patterns,
    load_long_term_patterns,
    load_advanced_patterns,
    load_freshness_patterns_validated,
    load_hmc_categorization_validated,
    load_consecutive_pairs_validated,
    load_odd_even_validated,
    load_sum_contribution_validated,
    load_range_spread_validated
)

from ml_lotto.features.extractor import (
    extract_features_from_hmc_json,
    get_all_feature_names,
    expand_feature_selection
)

from ml_lotto.features.base import get_dynamic_recent_keys

from ml_lotto.features.timing import (
    calculate_days_since_bonus,
    calculate_recency_zone_score
)

from ml_lotto.features.patterns import (
    calculate_has_consecutive_partner,
    calculate_consecutive_pair_affinity
)

from ml_lotto.features.bonus import (
    calculate_was_recent_bonus
)

from ml_lotto.features.freshness import (
    calculate_freshness_category_features,
    calculate_recency_weighted_pattern_score
)

# NOTE: Removed duplicate calculated features - using JSON versions instead:
# - calculate_bonus_hit_target_alignment → bonus_hit_contribution
# - calculate_odd_even_affinity → odd_even_json
# - calculate_sum_contribution_score → sum_contribution_json
# - calculate_range_spread_affinity → range_spread_json

from ml_lotto.features.history import extract_win_bias_ratio_from_history

from ml_lotto.features.bonus_features import extract_bonus_features_from_json

from ml_lotto.models.trainer import train_all_models
from ml_lotto.models.bonus_trainer import train_bonus_model
from ml_lotto.models.bonus_to_main_trainer import train_bonus_to_main_model

from ml_lotto.prediction.predictor import generate_predictions, generate_all_picks, generate_pool_picks
from ml_lotto.prediction.bonus_predictor import generate_bonus_predictions, assign_bonus_to_models
from ml_lotto.prediction.bonus_to_main_predictor import generate_bonus_to_main_predictions, assign_bonus_to_main_to_models

from ml_lotto.display import (
    display_final_picks,
    display_overlap_analysis,
    display_rank_aware_explanation,
    display_data_source_summary,
    display_feature_configuration,
    display_completion_message,
    display_pool_analysis
)


def validate_data_files() -> bool:
    """Validate that all required data files exist."""
    required_files = [
        DRAW_HISTORY_JSON,
        HMC_JSON_INPUT,
        ODDS_JSON_INPUT,
        FRESHNESS_JSON_INPUT,
        DISTRIBUTION_STATS_JSON,
        BONUS_ANALYSIS_JSON,
        BONUS_TO_MAIN_JSON
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("\n✗ ERROR: Missing required data files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nPlease run 'python drawpick.py' to generate all data files.")
        return False
    
    return True


def validate_loaded_data(all_draws, hmc_data, odds_data, freshness_data, distribution_stats, bonus_data) -> bool:
    """Validate that loaded data is valid and sufficient."""
    issues = []
    
    if not all_draws or len(all_draws) < 100:
        issues.append(f"Insufficient draw history: {len(all_draws) if all_draws else 0} draws (need at least 100)")
    
    if not hmc_data:
        issues.append("HMC data is empty or invalid")
    
    if not odds_data:
        issues.append("Odds data is empty or invalid")
    
    if not freshness_data or 'distribution_analysis_7_numbers' not in freshness_data:
        issues.append("Freshness data is missing or invalid")
    
    if not distribution_stats:
        issues.append("Distribution stats data is missing or invalid")
    
    if not bonus_data or 'per_number_bonus_profile' not in bonus_data:
        issues.append("Bonus analysis data is missing or invalid")
    
    if issues:
        print("\n✗ DATA VALIDATION ERRORS:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    return True


def print_scipy_validation_summary(scipy_data):
    """Print concise scipy validation status."""
    print("\n" + "=" * 70)
    print("SCIPY STATISTICAL VALIDATION STATUS")
    print("=" * 70)

    validations = [
        ("Freshness Patterns", scipy_data.get('freshness'), 'pattern_distribution_test'),
        ("HMC Categorization", scipy_data.get('hmc'), 'anova_test'),
        ("Consecutive Pairs", scipy_data.get('pairs'), 'overall_chi_square_test'),
        ("Odd/Even Distribution", scipy_data.get('odd_even'), 'overall_distribution_test'),
        ("Sum Contribution", scipy_data.get('sum'), 'anova_analysis'),
        ("Range Spread", scipy_data.get('range'), 'levene_analysis'),
    ]

    successful = []
    failed = []

    for name, data, test_key in validations:
        if data and test_key in data:
            test = data[test_key]
            p_value = test.get('p_value', 1.0)
            significant = test.get('significant', False)

            if significant and p_value < 0.05:
                successful.append(f"  ✓ {name:25} (p={p_value:.4f})")
            else:
                failed.append(f"  ✗ {name:25} (p={p_value:.4f}) - using standard fallback")
        else:
            failed.append(f"  ✗ {name:25} - file not found")

    if successful:
        print("\nSCIPY-VALIDATED Features:")
        for item in successful:
            print(item)

    if failed:
        print("\nStandard (non-validated) Features:")
        for item in failed:
            print(item)

    print()


def print_model_picks_detailed(model_name, model_desc, picks, bonus, bonus_to_main, hmc_data, probabilities, algorithm):
    """Print detailed model picks with HMC categories and probabilities."""
    print(f"\n{'=' * 70}")
    print(f"{model_name}")
    print(f"{'=' * 70}")
    print(f"Algorithm: {algorithm}")
    print(f"Description: {model_desc}")
    print()

    # Pre-assigned numbers
    print("PRE-ASSIGNED (from models):")
    bonus_cat = hmc_data.get(str(bonus), {}).get('category', 'unknown')
    bonus_prob = probabilities.get(bonus, 0.0) if probabilities else 0.0
    print(f"  Bonus Ball:      #{bonus:2d}  [{bonus_cat:6}]  prob={bonus_prob:.1%}")

    btm_cat = hmc_data.get(str(bonus_to_main), {}).get('category', 'unknown')
    btm_prob = probabilities.get(bonus_to_main, 0.0) if probabilities else 0.0
    print(f"  Bonus-to-Main:   #{bonus_to_main:2d}  [{btm_cat:6}]  prob={btm_prob:.1%}")

    # ML-selected numbers
    ml_picks = [p for p in picks if p not in [bonus, bonus_to_main]]
    print("\nML-SELECTED (4 numbers):")
    for i, num in enumerate(ml_picks, 1):
        cat = hmc_data.get(str(num), {}).get('category', 'unknown')
        prob = probabilities.get(num, 0.0) if probabilities else 0.0
        print(f"  Pick {i}:          #{num:2d}  [{cat:6}]  prob={prob:.1%}")

    # Final line
    print(f"\nFINAL LINE: {sorted(picks)} + BONUS {bonus}")

    # HMC distribution
    hmc_counts = {'hot': 0, 'medium': 0, 'cold': 0}
    for num in picks:
        cat = hmc_data.get(str(num), {}).get('category', 'unknown')
        if cat in hmc_counts:
            hmc_counts[cat] += 1

    print(f"HMC Distribution: {hmc_counts['hot']}H-{hmc_counts['medium']}M-{hmc_counts['cold']}C")
    print()


def main():
    """Main execution function with bonus ball prediction."""
    start_time = time.time()

    # Initialize random seed based on mode
    import numpy as np
    import random

    print("=" * 70)
    print("INTELLIGENT LOTTO SYSTEM V3.16: INTERACTION FEATURES EDITION")
    print("=" * 70)

    if ENSEMBLE_MODE:
        print(f"MODE: Ensemble Voting ({ENSEMBLE_RUNS} runs per model)")
        print(f"  Each model runs {ENSEMBLE_RUNS}x with different seeds")
        print(f"  Numbers ranked by consistency across runs")
        print(f"  Base seed: {RANDOM_SEED_BASE}")
    else:
        print(f"MODE: Single Deterministic Run (seed: {RANDOM_SEED_BASE})")
        np.random.seed(RANDOM_SEED_BASE)
        random.seed(RANDOM_SEED_BASE)

    print(f"Active Models: {len(ACTIVE_MODELS)} main models + 1 bonus model + 1 bonus-to-main model")
    print("V3.16 FEATURES: Pairwise & triple interaction features for Model 1")
    print("  Model 1: ML-Optimized (6 main + 1 bonus) - PAIRWISE & TRIPLE INTERACTIONS")
    print("  Model 2: Jackpot optimizer - MAIN 6 ONLY (NO BONUS)")
    print("  Model 3: Complexity explorer (6 main + 1 bonus)")
    print("  Model 4: Pool generator (configurable candidate pool)")
    
    try:
        if VERBOSE:
            print("\nStep 0: Validating data files...")
        if not validate_data_files():
            sys.exit(1)
        if VERBOSE:
            print("✓ All required files present")

        if not VERBOSE:
            print("\nLoading data files...")
        else:
            print("\nStep 1: Loading data files...")

        with suppress_output():
            all_draws, draw_history_log_raw = load_draw_history_with_bias_ratios(DRAW_HISTORY_JSON)
            hmc_data = load_hmc_json(HMC_JSON_INPUT)
            odds_data = load_odds_json(ODDS_JSON_INPUT)
        
        freshness_data = {}
        with suppress_output():
            try:
                with open(FRESHNESS_JSON_INPUT, 'r') as f:
                    freshness_data = json.load(f)
                if VERBOSE:
                    print(f"✓ Loaded freshness data from {FRESHNESS_JSON_INPUT}")
                    print(f"  Contains {len(freshness_data.get('distribution_analysis_7_numbers', []))} pattern distributions")
            except FileNotFoundError:
                if VERBOSE:
                    print(f"✗ Error: {FRESHNESS_JSON_INPUT} not found.")
            except json.JSONDecodeError as e:
                if VERBOSE:
                    print(f"✗ Error: Invalid JSON in {FRESHNESS_JSON_INPUT}: {e}")

        distribution_stats = {}
        with suppress_output():
            try:
                with open(DISTRIBUTION_STATS_JSON, 'r') as f:
                    distribution_stats = json.load(f)
                if VERBOSE:
                    print(f"✓ Loaded distribution stats from {DISTRIBUTION_STATS_JSON}")
                    print(f"  Total draws analyzed: {distribution_stats.get('total_draws_analyzed', 0)}")
            except FileNotFoundError:
                if VERBOSE:
                    print(f"✗ Error: {DISTRIBUTION_STATS_JSON} not found.")
            except json.JSONDecodeError as e:
                if VERBOSE:
                    print(f"✗ Error: Invalid JSON in {DISTRIBUTION_STATS_JSON}: {e}")

        with suppress_output():
            bonus_analysis_data = load_bonus_analysis(BONUS_ANALYSIS_JSON)
            bonus_to_main_data = load_bonus_to_main_patterns(BONUS_TO_MAIN_JSON)
            long_term_analysis = load_long_term_patterns(LONG_TERM_PATTERNS_JSON)
            advanced_patterns_analysis = load_advanced_patterns(ADVANCED_PATTERNS_JSON)

        # Load scipy-validated feature analyses
        if VERBOSE:
            print("\nStep 1c: Loading scipy-validated feature analyses...")

        with suppress_output():
            freshness_validated = load_freshness_patterns_validated(FRESHNESS_PATTERNS_VALIDATED_JSON)
            hmc_categorization_validated = load_hmc_categorization_validated(HMC_CATEGORIZATION_VALIDATED_JSON)
            consecutive_pairs_validated = load_consecutive_pairs_validated(CONSECUTIVE_PAIRS_VALIDATED_JSON)
            odd_even_validated = load_odd_even_validated(ODD_EVEN_VALIDATED_JSON)
            sum_contribution_validated = load_sum_contribution_validated(SUM_CONTRIBUTION_VALIDATED_JSON)
            range_spread_validated = load_range_spread_validated(RANGE_SPREAD_VALIDATED_JSON)

        # Print concise scipy validation summary (non-verbose mode)
        if not VERBOSE:
            scipy_summary_data = {
                'freshness': freshness_validated,
                'hmc': hmc_categorization_validated,
                'pairs': consecutive_pairs_validated,
                'odd_even': odd_even_validated,
                'sum': sum_contribution_validated,
                'range': range_spread_validated
            }
            print_scipy_validation_summary(scipy_summary_data)

        if not validate_loaded_data(all_draws, hmc_data, odds_data, freshness_data, distribution_stats, bonus_analysis_data):
            sys.exit(1)

        W, C_max, recent_key, top_pattern_dist = load_freshness_config(FRESHNESS_JSON_INPUT)

        if VERBOSE:
            print("\nStep 1b: Loading NEW JSON features...")
        with suppress_output():
            bonus_hit_contribution_data = load_bonus_hit_analysis(draw_history_log_raw)
            freshness_weight_data = load_freshness_weights(FRESHNESS_JSON_INPUT)
            pair_frequency_data = load_number_pair_frequency(ODDS_JSON_INPUT)

        # Use scipy-validated scores if available, otherwise fall back to standard analysis
        if odd_even_validated and 'validated_scores' in odd_even_validated:
            odd_even_json_data = {int(k): v for k, v in odd_even_validated['validated_scores'].items()}
            if VERBOSE:
                print("  ✓ Using SCIPY-VALIDATED odd/even scores")
        else:
            odd_even_json_data = load_odd_even_analysis(DISTRIBUTION_STATS_JSON)
            if VERBOSE:
                print("  ⚠️  Using standard odd/even scores (scipy validation not available)")

        if sum_contribution_validated and 'validated_scores' in sum_contribution_validated:
            sum_contribution_json_data = {int(k): v for k, v in sum_contribution_validated['validated_scores'].items()}
            if VERBOSE:
                print("  ✓ Using SCIPY-VALIDATED sum contribution scores")
        else:
            sum_contribution_json_data = load_sum_contribution_analysis(DISTRIBUTION_STATS_JSON)
            if VERBOSE:
                print("  ⚠️  Using standard sum contribution scores (scipy validation not available)")

        if range_spread_validated and 'validated_scores' in range_spread_validated:
            range_spread_json_data = {int(k): v for k, v in range_spread_validated['validated_scores'].items()}
            if VERBOSE:
                print("  ✓ Using SCIPY-VALIDATED range spread scores")
        else:
            range_spread_json_data = load_range_spread_analysis(ODDS_JSON_INPUT)
            if VERBOSE:
                print("  ⚠️  Using standard range spread scores (scipy validation not available)")

        if VERBOSE:
            print(f"\n✓ Data Loading Summary:")
            print(f"  - Historical draws: {len(all_draws)}")
            print(f"  - HMC numbers tracked: {len(hmc_data)}")
            print(f"  - Freshness patterns: {len(freshness_data.get('distribution_analysis_7_numbers', []))}")
            print(f"  - Freshness Config: W={W}, C_max={C_max}, Key={recent_key}")
            print(f"  - Distribution stats: {distribution_stats.get('total_draws_analyzed', 0)} draws")
            print(f"  - Bonus analysis: {len(bonus_analysis_data.get('per_number_bonus_profile', {}))} numbers")
            print(f"  - Long-term patterns: {long_term_analysis.get('metadata', {}).get('total_draws', 0)} draws analyzed (scipy-validated)")
            print(f"  - NEW JSON features loaded: 6 feature sets")

        if VERBOSE:
            print("\nStep 2: Extracting MAIN NUMBER features from HMC data...")
        else:
            print("\nExtracting features and training models...")
        feature_start = time.time()

        consecutive_patterns = odds_data.get('patterns', {})
        if consecutive_patterns:
            print(f"  ✓ Loaded consecutive patterns data")
        else:
            print(f"  ⚠️  No consecutive patterns found in odds_data")

        print("  Calculating 'days_since_bonus' feature...")
        days_since_bonus_data = calculate_days_since_bonus(all_draws)

        print("  Calculating 'was_recent_bonus' feature...")
        was_recent_bonus_data = calculate_was_recent_bonus(all_draws, lookback_draws=10)

        print("  Extracting 'win_bias_ratio' from draw history...")
        win_bias_ratio_data = extract_win_bias_ratio_from_history(
            draw_history_log_raw,
            MAX_NUMBER
        )

        print("  Calculating 'freshness_category' features...")
        # Extract validated weights if available
        validated_freshness_weights = freshness_validated.get('validated_weights') if freshness_validated else None

        freshness_category_features = calculate_freshness_category_features(
            hmc_data=hmc_data,
            c_max_threshold=C_max,
            recent_key=recent_key,
            top_pattern_dist=top_pattern_dist,
            validated_weights=validated_freshness_weights
        )

        print("  Calculating 'long_term_pattern' features...")
        from ml_lotto.features.long_term_patterns import expand_long_term_features
        long_term_pattern_features = expand_long_term_features(
            hmc_data=hmc_data,
            long_term_analysis=long_term_analysis,
            all_draws=all_draws
        )

        print("  Extracting 'advanced_pattern' features (volatility + trend)...")
        # Extract per-number features from advanced_patterns_analysis
        advanced_pattern_features_dict = {}
        if advanced_patterns_analysis and 'per_number_features' in advanced_patterns_analysis:
            for num_str, features in advanced_patterns_analysis['per_number_features'].items():
                num = int(num_str)
                advanced_pattern_features_dict[num] = features
            print(f"    ✓ Loaded advanced features for {len(advanced_pattern_features_dict)} numbers")
        else:
            print("    ⚠️  No advanced pattern features found - using defaults")
            advanced_pattern_features_dict = {}

        pattern_score_data = {num: 0.0 for num in range(1, MAX_NUMBER + 1)}

        print("  Extracting dynamic recent count keys...")
        dynamic_recent_keys = get_dynamic_recent_keys(hmc_data)
        print(f"    Found {len(dynamic_recent_keys)} dynamic features: {[k[1] for k in dynamic_recent_keys]}")

        print("  Combining all MAIN NUMBER features...")
        try:
            features_dict = extract_features_from_hmc_json(
                hmc_data,
                dynamic_recent_keys,
                days_since_bonus_data,
                pattern_score_data,
                freshness_category_features,
                win_bias_ratio_data,
                was_recent_bonus_data,
                consecutive_patterns,
                distribution_stats,
                odds_data,
                TRAINING_START_DRAW,
                bonus_hit_contribution_data,
                freshness_weight_data,
                pair_frequency_data,
                range_spread_json_data,
                odd_even_json_data,
                sum_contribution_json_data,
                long_term_pattern_features,
                advanced_pattern_features_dict,
                consecutive_pairs_validated
            )
            print(f"  ✓ Main number features extracted for {len(features_dict)} numbers")
        except Exception as e:
            print(f"  ✗ Error extracting features: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        feature_time = time.time() - feature_start
        print(f"✓ Main feature extraction completed in {feature_time:.2f} seconds")
        
        print("\nStep 2b: Extracting BONUS BALL features from JSON...")
        bonus_feature_start = time.time()
        
        try:
            bonus_features_dict = extract_bonus_features_from_json(bonus_analysis_data)
            print(f"  ✓ Bonus features extracted for {len(bonus_features_dict)} numbers")
        except Exception as e:
            print(f"  ✗ Error extracting bonus features: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        bonus_feature_time = time.time() - bonus_feature_start
        print(f"✓ Bonus feature extraction completed in {bonus_feature_time:.2f} seconds")
        
        print("\nStep 3: Training BONUS BALL prediction model...")
        bonus_training_start = time.time()
        
        try:
            bonus_pipeline, bonus_features = train_bonus_model(
                BONUS_MODEL_CONFIG,
                all_draws,
                bonus_features_dict,
                TRAINING_START_DRAW
            )
            print(f"✓ Bonus model training completed in {time.time() - bonus_training_start:.2f} seconds")
        except Exception as e:
            print(f"✗ Error training bonus model: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        print("\nStep 4: Generating 3 BONUS BALL predictions...")
        
        category_dict = {num: features_dict[num]['category'] for num in range(1, 48) if num in features_dict}
        
        try:
            bonus_predictions = generate_bonus_predictions(
                bonus_pipeline,
                bonus_features,
                bonus_features_dict,
                category_dict,
                num_predictions=3
            )
            print(f"✓ Generated {len(bonus_predictions)} bonus predictions")
        except Exception as e:
            print(f"✗ Error generating bonus predictions: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        bonus_assignments = assign_bonus_to_models(bonus_predictions, len(ACTIVE_MODELS))

        print("\nStep 4b: Calculating LIVE bonus window and extracting BONUS-TO-MAIN features...")
        bonus_to_main_feature_start = time.time()

        try:
            # Import helpers
            from ml_lotto.utils.bonus_window import calculate_current_bonus_window
            from ml_lotto.features.bonus_to_main_features import extract_bonus_to_main_features_dict

            # Calculate LIVE bonus window from recent draws
            print("  Calculating current bonus window from recent draws...")
            live_bonus_window = calculate_current_bonus_window(
                all_draws,
                window_size=10,
                hmc_data=hmc_data
            )
            print(f"  ✓ Live bonus window calculated: {len(live_bonus_window)} entries")

            # Extract features using LIVE window
            bonus_to_main_features_dict = extract_bonus_to_main_features_dict(
                bonus_to_main_data,
                features_dict,
                current_bonus_window=live_bonus_window
            )
            print(f"  ✓ Bonus-to-main features extracted for {len(bonus_to_main_features_dict)} numbers")
        except Exception as e:
            print(f"  ✗ Error extracting bonus-to-main features: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        bonus_to_main_feature_time = time.time() - bonus_to_main_feature_start
        print(f"✓ Bonus-to-main feature extraction completed in {bonus_to_main_feature_time:.2f} seconds")

        print("\nStep 4c: Training BONUS-TO-MAIN prediction model...")
        bonus_to_main_training_start = time.time()

        try:
            bonus_to_main_pipeline, bonus_to_main_features = train_bonus_to_main_model(
                BONUS_TO_MAIN_MODEL_CONFIG,
                all_draws,
                bonus_to_main_features_dict,
                TRAINING_START_DRAW
            )
            print(f"✓ Bonus-to-main model training completed in {time.time() - bonus_to_main_training_start:.2f} seconds")
        except Exception as e:
            print(f"✗ Error training bonus-to-main model: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        print("\nStep 4d: Generating 3 BONUS-TO-MAIN predictions...")

        # Use LIVE bonus window (already calculated in Step 4b)
        current_bonus_numbers = [b['number'] for b in live_bonus_window]

        print(f"  Current bonus window (last 10 draws): {current_bonus_numbers}")
        print(f"  Using LIVE window (adapts to most recent draws)")

        try:
            bonus_to_main_predictions = generate_bonus_to_main_predictions(
                bonus_to_main_pipeline,
                bonus_to_main_features,
                bonus_to_main_features_dict,
                live_bonus_window,  # Pass full window with metadata
                category_dict,
                num_predictions=3
            )
            print(f"✓ Generated {len(bonus_to_main_predictions)} bonus-to-main predictions: {bonus_to_main_predictions}")
        except Exception as e:
            print(f"✗ Error generating bonus-to-main predictions: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        bonus_to_main_assignments = assign_bonus_to_main_to_models(bonus_to_main_predictions, len(ACTIVE_MODELS))

        print("\nStep 5: Analyzing HMC distribution patterns...")
        hot_count, medium_count, cold_count, pattern_percentage = get_most_likely_hmc_pattern(odds_data)
        
        print("\nStep 6: Training MAIN NUMBER prediction models...")
        training_start = time.time()
        
        try:
            models, model_features = train_all_models(ACTIVE_MODELS, all_draws, features_dict)
            print(f"\n✓ Main model training completed in {time.time() - training_start:.2f} seconds")

            # Model training validation
            print("\n" + "="*70)
            print("MODEL TRAINING VALIDATION")
            print("="*70)
            print(f"Model 1: Trained on ALL 7 positions (momentum capture)")
            print(f"Model 2: Trained on MAIN 6 ONLY (jackpot optimization) ⭐")
            print(f"Model 3: Trained on ALL 7 positions (complexity)")
            print(f"\nModel 2 Key Differences:")
            print(f"  - Excludes bonus ball from training labels")
            print(f"  - Uses long-term stability features")
            print(f"  - No pre-assigned numbers")
            print(f"  - Optimizes for 6-ball main prize")

        except Exception as e:
            print(f"\n✗ Error during model training: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        print("\nStep 7: Generating MAIN NUMBER predictions...")
        try:
            all_probabilities = generate_predictions(models, model_features, features_dict)
            print(f"✓ Main number predictions generated for {len(all_probabilities)} models")
        except Exception as e:
            print(f"✗ Error generating predictions: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        print("\nStep 8: Preparing models for number selection...")
        # ALL models (1, 2, 3) select their numbers via ML
        # Model 1: Optimized with pairwise & triple interactions - selects 5 numbers
        # Model 2: Jackpot optimizer - selects 6 numbers (no bonus)
        # Model 3: Complexity explorer - selects 6 numbers
        # Model 4: Pool generator - doesn't pick specific numbers

        # Filter out Model 4 (pool generator) from pick generation
        pick_models = {}
        pick_probabilities = {}
        for model_name, model_data in models.items():
            if 'Pool Generator' not in model_data['config']['name']:
                pick_models[model_name] = model_data
                pick_probabilities[model_name] = all_probabilities[model_name]

        # No pre-assignment for any model - all numbers selected via ML
        pre_assigned_numbers = {}
        for model_idx in range(1, len(pick_models) + 1):
            pre_assigned_numbers[model_idx] = []
            print(f"  Model {model_idx}: ML selects 6 numbers (all ML-selected)")

        print("\nStep 9: Selecting optimal MAIN NUMBERS per model (Models 1-3 only, Model 4 generates pool)...")
        try:
            lines = generate_all_picks(
                pick_models,
                pick_probabilities,
                features_dict,
                freshness_data,
                pre_assigned_numbers=pre_assigned_numbers
            )
            print(f"✓ Generated {len(lines)} lines of main number picks")
        except Exception as e:
            print(f"✗ Error generating picks: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        print("\nStep 10: Final assembly - adding separate bonus balls...")
        for line in lines:
            model_idx = line['model_index']
            # Model 2 does NOT get a bonus ball - it only predicts 6 main numbers
            if model_idx == 2:
                line['bonus_for_draw'] = None  # No bonus for jackpot optimizer
            else:
                # Models 1 & 3 get bonus balls from BONUS_MODEL
                line['bonus_for_draw'] = bonus_assignments.get(model_idx)

        print("\nStep 11: Generating Model 4 candidate pool...")
        try:
            pool_data = generate_pool_picks(models, all_probabilities, features_dict)
        except Exception as e:
            print(f"⚠️  Error generating pool: {e}")
            pool_data = None

        print("\nStep 12: Displaying complete results (6 main + 1 bonus)...")
        try:
            print("\n" + "=" * 70)
            print("FINAL RECOMMENDED PICKS")
            print("=" * 70)
            print("V3.16 MODEL ARCHITECTURE (Interaction Features Edition):")
            print("  Model 1: 6 main numbers (ML-optimized) + 1 bonus - PAIRWISE & TRIPLE INTERACTIONS")
            print("  Model 2: 6 main numbers ONLY (jackpot optimizer - NO BONUS)")
            print("  Model 3: 6 main numbers (complexity explorer) + 1 bonus")
            print("  Model 4: Candidate pool generator (configurable pool size)")
            print("=" * 70)

            for line in lines:
                print(f"\nLine {line['model_index']}: {line['model_name']} [{line['config_str']}]")
                print(f"Description: {line['description']}")
                print(f"Main Numbers (6): {sorted(line['numbers'])}")

                # Model 2 does not have a bonus ball
                if line['bonus_for_draw'] is not None:
                    print(f"Bonus Ball: {line['bonus_for_draw']}")
                    print(f"Complete Line: {sorted(line['numbers'])} + BONUS {line['bonus_for_draw']}")
                else:
                    print(f"Bonus Ball: None (jackpot optimizer - main 6 only)")
                    print(f"Complete Line: {sorted(line['numbers'])} (6 main numbers only)")

            # Display Model 4 pool analysis
            if pool_data:
                display_pool_analysis(pool_data)

            display_overlap_analysis(lines)
            display_rank_aware_explanation(ACTIVE_MODELS)
            display_feature_configuration(ACTIVE_MODELS)
            display_data_source_summary()
            
            try:
                with open('lottery_picks.txt', 'w') as f:
                    f.write("=" * 70 + "\n")
                    f.write("LOTTERY PICKS - GENERATED " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write("=" * 70 + "\n")
                    f.write("INTERACTION FEATURES EDITION V3.16\n")
                    f.write("Model 1: 6 main (ML-optimized with interactions) + 1 bonus\n")
                    f.write("Model 2: 6 main ONLY (jackpot optimizer - NO BONUS)\n")
                    f.write("Model 3: 6 main (complexity explorer) + 1 bonus\n")
                    f.write("Model 4: Candidate pool generator (configurable pool size)\n")
                    f.write("=" * 70 + "\n\n")
                    for line in lines:
                        f.write(f"Line {line['model_index']}: {line['model_name']} [{line['config_str']}]\n")
                        f.write(f"Main Numbers (6): {sorted(line['numbers'])}\n")

                        # Model 2 does not have a bonus ball
                        if line['bonus_for_draw'] is not None:
                            f.write(f"Bonus Ball: {line['bonus_for_draw']}\n")
                            f.write(f"Complete: {sorted(line['numbers'])} + BONUS {line['bonus_for_draw']}\n")
                        else:
                            f.write(f"Bonus Ball: None (jackpot optimizer - main 6 only)\n")
                            f.write(f"Complete: {sorted(line['numbers'])} (6 main only)\n")
                        f.write(f"Description: {line['description']}\n\n")

                    # Add Model 4 pool data
                    if pool_data:
                        f.write("=" * 70 + "\n")
                        f.write("MODEL 4: CANDIDATE POOL ANALYSIS\n")
                        f.write("=" * 70 + "\n")
                        f.write(f"Pool Configuration: {pool_data['pool_config']}\n")
                        f.write(f"Total Candidates: {pool_data['pool_size']}\n")
                        f.write(f"Quality Score: {pool_data['quality_score']:.0f}/100\n\n")
                        f.write(f"Full Pool (ranked by probability): {pool_data['pool']}\n\n")

                        # Freshness distribution
                        f.write("Freshness Distribution:\n")
                        for bin_val in sorted(pool_data['freshness_distribution'].keys()):
                            count = pool_data['freshness_distribution'][bin_val]
                            pct = (count / pool_data['pool_size'] * 100) if pool_data['pool_size'] > 0 else 0
                            f.write(f"  C{bin_val}: {count:2d} numbers ({pct:5.1f}%)\n")
                        f.write("\n")

                print("\n✓ Results saved to 'lottery_picks.txt'")
            except Exception as e:
                print(f"⚠️  Could not save to file: {e}")
            
            total_time = time.time() - start_time
            print("\n" + "=" * 70)
            print("PERFORMANCE SUMMARY")
            print("=" * 70)
            print(f"Main feature extraction: {feature_time:.2f}s")
            print(f"Bonus feature extraction: {bonus_feature_time:.2f}s")
            print(f"Bonus model training: {time.time() - bonus_training_start:.2f}s")
            print(f"Main model training: {time.time() - training_start:.2f}s")
            print(f"Total execution time: {total_time:.2f}s")
            
            display_completion_message()
        except Exception as e:
            print(f"✗ Error displaying results: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {str(e)}")
        print("\nStack trace:")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()