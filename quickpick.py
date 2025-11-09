# quickpick.py
"""
quickpick.py (main.py)
======================
Main entry point for the Lottery Prediction System V3.8

VERSION: 3.8 (Bonus Ball Prediction Edition)
- Added bonus ball prediction model training
- Integrated 3 bonus predictions assigned to main models
- Modified main models to pick 5 numbers + 1 assigned bonus
"""

import warnings
warnings.filterwarnings('ignore')
import json
import time
import sys
from pathlib import Path

from ml_lotto.config import (
    DRAW_HISTORY_JSON,
    HMC_JSON_INPUT,
    ODDS_JSON_INPUT,
    FRESHNESS_JSON_INPUT,
    DISTRIBUTION_STATS_JSON,
    BONUS_ANALYSIS_JSON,
    BONUS_TO_MAIN_JSON,
    LONG_TERM_PATTERNS_JSON,
    ACTIVE_MODELS,
    BONUS_MODEL_CONFIG,
    BONUS_TO_MAIN_MODEL_CONFIG,
    MAX_NUMBER,
    TRAINING_START_DRAW
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
    load_long_term_patterns
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

from ml_lotto.prediction.predictor import generate_predictions, generate_all_picks
from ml_lotto.prediction.bonus_predictor import generate_bonus_predictions, assign_bonus_to_models
from ml_lotto.prediction.bonus_to_main_predictor import generate_bonus_to_main_predictions, assign_bonus_to_main_to_models

from ml_lotto.display import (
    display_final_picks,
    display_overlap_analysis,
    display_rank_aware_explanation,
    display_data_source_summary,
    display_feature_configuration,
    display_completion_message
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


def main():
    """Main execution function with bonus ball prediction."""
    start_time = time.time()
    
    print("=" * 70)
    print("INTELLIGENT LOTTO SYSTEM V3.9: BONUS-TO-MAIN PREDICTION EDITION")
    print("=" * 70)
    print(f"Active Models: {len(ACTIVE_MODELS)} main models + 1 bonus model + 1 bonus-to-main model")
    print("NEW: Pre-assignment system - each model gets 2 numbers (bonus + bonus-to-main)")
    print("Each model then selects 4 additional numbers for 6 total main numbers")
    
    try:
        print("\nStep 0: Validating data files...")
        if not validate_data_files():
            sys.exit(1)
        print("✓ All required files present")
        
        print("\nStep 1: Loading data files...")
        
        all_draws, draw_history_log_raw = load_draw_history_with_bias_ratios(DRAW_HISTORY_JSON)
        hmc_data = load_hmc_json(HMC_JSON_INPUT)
        odds_data = load_odds_json(ODDS_JSON_INPUT)
        
        freshness_data = {}
        try:
            with open(FRESHNESS_JSON_INPUT, 'r') as f:
                freshness_data = json.load(f)
            print(f"✓ Loaded freshness data from {FRESHNESS_JSON_INPUT}")
            print(f"  Contains {len(freshness_data.get('distribution_analysis_7_numbers', []))} pattern distributions")
        except FileNotFoundError:
            print(f"✗ Error: {FRESHNESS_JSON_INPUT} not found.")
        except json.JSONDecodeError as e:
            print(f"✗ Error: Invalid JSON in {FRESHNESS_JSON_INPUT}: {e}")
        
        distribution_stats = {}
        try:
            with open(DISTRIBUTION_STATS_JSON, 'r') as f:
                distribution_stats = json.load(f)
            print(f"✓ Loaded distribution stats from {DISTRIBUTION_STATS_JSON}")
            print(f"  Total draws analyzed: {distribution_stats.get('total_draws_analyzed', 0)}")
        except FileNotFoundError:
            print(f"✗ Error: {DISTRIBUTION_STATS_JSON} not found.")
        except json.JSONDecodeError as e:
            print(f"✗ Error: Invalid JSON in {DISTRIBUTION_STATS_JSON}: {e}")
        
        bonus_analysis_data = load_bonus_analysis(BONUS_ANALYSIS_JSON)

        bonus_to_main_data = load_bonus_to_main_patterns(BONUS_TO_MAIN_JSON)

        # Load long-term pattern analysis (scipy-validated)
        long_term_analysis = load_long_term_patterns(LONG_TERM_PATTERNS_JSON)

        if not validate_loaded_data(all_draws, hmc_data, odds_data, freshness_data, distribution_stats, bonus_analysis_data):
            sys.exit(1)
        
        W, C_max, recent_key, top_pattern_dist = load_freshness_config(FRESHNESS_JSON_INPUT)
        
        print("\nStep 1b: Loading NEW JSON features...")
        bonus_hit_contribution_data = load_bonus_hit_analysis(draw_history_log_raw)
        freshness_weight_data = load_freshness_weights(FRESHNESS_JSON_INPUT)
        pair_frequency_data = load_number_pair_frequency(ODDS_JSON_INPUT)
        range_spread_json_data = load_range_spread_analysis(ODDS_JSON_INPUT)
        odd_even_json_data = load_odd_even_analysis(DISTRIBUTION_STATS_JSON)
        sum_contribution_json_data = load_sum_contribution_analysis(DISTRIBUTION_STATS_JSON)
        
        print(f"\n✓ Data Loading Summary:")
        print(f"  - Historical draws: {len(all_draws)}")
        print(f"  - HMC numbers tracked: {len(hmc_data)}")
        print(f"  - Freshness patterns: {len(freshness_data.get('distribution_analysis_7_numbers', []))}")
        print(f"  - Freshness Config: W={W}, C_max={C_max}, Key={recent_key}")
        print(f"  - Distribution stats: {distribution_stats.get('total_draws_analyzed', 0)} draws")
        print(f"  - Bonus analysis: {len(bonus_analysis_data.get('per_number_bonus_profile', {}))} numbers")
        print(f"  - Long-term patterns: {long_term_analysis.get('metadata', {}).get('total_draws', 0)} draws analyzed (scipy-validated)")
        print(f"  - NEW JSON features loaded: 6 feature sets")
        
        print("\nStep 2: Extracting MAIN NUMBER features from HMC data...")
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
        freshness_category_features = calculate_freshness_category_features(
            hmc_data=hmc_data,
            c_max_threshold=C_max,
            recent_key=recent_key,
            top_pattern_dist=top_pattern_dist
        )

        print("  Calculating 'long_term_pattern' features...")
        from ml_lotto.features.long_term_patterns import expand_long_term_features
        long_term_pattern_features = expand_long_term_features(
            hmc_data=hmc_data,
            long_term_analysis=long_term_analysis,
            all_draws=all_draws
        )

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
                long_term_pattern_features
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

        print("\nStep 4b: Extracting BONUS-TO-MAIN features from JSON...")
        bonus_to_main_feature_start = time.time()

        try:
            # Import feature extractor
            from ml_lotto.features.bonus_to_main_features import extract_bonus_to_main_features_dict

            bonus_to_main_features_dict = extract_bonus_to_main_features_dict(
                bonus_to_main_data,
                features_dict
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

        current_bonus_window = bonus_to_main_data['current_bonus_window']['last_10_bonus_numbers']
        current_bonus_numbers = [b['number'] for b in current_bonus_window]

        print(f"  Current bonus window (last 10 draws): {current_bonus_numbers}")

        try:
            bonus_to_main_predictions = generate_bonus_to_main_predictions(
                bonus_to_main_pipeline,
                bonus_to_main_features,
                bonus_to_main_features_dict,
                current_bonus_numbers,
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
        
        print("\nStep 8: Creating pre-assigned number combinations (bonus + bonus-to-main)...")
        # Combine bonus and bonus-to-main assignments into pre_assigned_numbers
        pre_assigned_numbers = {}
        for model_idx in range(1, len(ACTIVE_MODELS) + 1):
            bonus_num = bonus_assignments.get(model_idx)
            bonus_to_main_num = bonus_to_main_assignments.get(model_idx)
            pre_assigned_numbers[model_idx] = [bonus_num, bonus_to_main_num]
            print(f"  Model {model_idx}: Pre-assigned [Bonus: {bonus_num}, Bonus-to-Main: {bonus_to_main_num}]")

        print("\nStep 9: Selecting optimal 4 MAIN NUMBERS per model (+ 2 pre-assigned = 6 total)...")
        try:
            lines = generate_all_picks(
                models,
                all_probabilities,
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
            # Note: bonus is already in the main numbers as one of the pre-assigned
            # But we still track it separately for display purposes
            line['bonus_for_draw'] = bonus_assignments.get(model_idx)

        print("\nStep 11: Displaying complete results (6 main + 1 bonus)...")
        try:
            print("\n" + "=" * 70)
            print("FINAL RECOMMENDED PICKS (6 MAIN + 1 BONUS)")
            print("=" * 70)
            print("NEW ARCHITECTURE: Each line has:")
            print("  - 2 pre-assigned numbers (exempt from diversity penalties)")
            print("  - 4 ML-selected numbers")
            print("  - 1 separate bonus ball for the draw")
            print("=" * 70)

            for line in lines:
                print(f"\nLine {line['model_index']}: {line['model_name']} [{line['config_str']}]")
                print(f"Description: {line['description']}")
                if line.get('pre_assigned'):
                    print(f"Pre-assigned (exempt): {sorted(line['pre_assigned'])}")
                    print(f"ML-selected: {sorted(line['selected'])}")
                print(f"Main Numbers (6): {sorted(line['numbers'])}")
                print(f"Bonus Ball: {line['bonus_for_draw']}")
                print(f"Complete Line: {sorted(line['numbers'])} + BONUS {line['bonus_for_draw']}")
            
            display_overlap_analysis(lines)
            display_rank_aware_explanation(ACTIVE_MODELS)
            display_feature_configuration(ACTIVE_MODELS)
            display_data_source_summary()
            
            try:
                with open('lottery_picks.txt', 'w') as f:
                    f.write("=" * 70 + "\n")
                    f.write("LOTTERY PICKS - GENERATED " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write("=" * 70 + "\n")
                    f.write("BONUS-TO-MAIN PREDICTION EDITION V3.9\n")
                    f.write("Each line: 6 main numbers (2 pre-assigned + 4 selected) + 1 bonus ball\n")
                    f.write("Pre-assigned numbers are EXEMPT from diversity penalties\n")
                    f.write("=" * 70 + "\n\n")
                    for line in lines:
                        f.write(f"Line {line['model_index']}: {line['model_name']} [{line['config_str']}]\n")
                        if line.get('pre_assigned'):
                            f.write(f"Pre-assigned (exempt): {sorted(line['pre_assigned'])}\n")
                            f.write(f"ML-selected: {sorted(line['selected'])}\n")
                        f.write(f"Main Numbers (6): {sorted(line['numbers'])}\n")
                        f.write(f"Bonus Ball: {line['bonus_for_draw']}\n")
                        f.write(f"Complete: {sorted(line['numbers'])} + BONUS {line['bonus_for_draw']}\n")
                        f.write(f"Description: {line['description']}\n\n")
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