"""
quickpick.py (main.py)
======================
Main entry point for the Lottery Prediction System V3.1
Orchestrates the entire prediction workflow.

IMPROVEMENTS:
- Added comprehensive error handling
- Added data validation
- Added performance timing
- Improved logging and progress indicators

USAGE:
    python quickpick.py

CONFIGURATION:
    Edit config.py to customize:
    - Model configurations (features, HMC ratios, penalties)
    - File paths
    - Display settings
"""

import warnings
warnings.filterwarnings('ignore')
import json
import time
import sys
from pathlib import Path

# --- Configuration Imports ---
from ml_lotto.config import (
    DRAW_HISTORY_JSON,
    HMC_JSON_INPUT,
    ODDS_JSON_INPUT,
    FRESHNESS_JSON_INPUT,
    ACTIVE_MODELS
)

# --- Data Loader Imports ---
from ml_lotto.data_loader import (
    load_draw_history_json,
    load_hmc_json,
    load_odds_json,
    get_most_likely_hmc_pattern,
    # REMOVED load_freshness_config here to clean up
)

# --- Feature Extractor Imports (FIXED) ---
from ml_lotto.feature_extractor import (
    get_dynamic_recent_keys,
    extract_features_from_hmc_json,
    calculate_days_since_bonus,
    calculate_freshness_category_features,
    calculate_win_bias_ratio # ADDED NEW FUNCTION IMPORT
)
# Note: Re-adding the missing load_freshness_config from the correct source
from ml_lotto.data_loader import load_freshness_config # Re-importing from data_loader as it's the source

# --- Model Imports ---
from ml_lotto.model_trainer import train_all_models
from ml_lotto.predictor import generate_predictions, generate_all_picks
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
        FRESHNESS_JSON_INPUT
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("\n❌ ERROR: Missing required data files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nPlease ensure all data files are present before running.")
        return False
    
    return True


def validate_loaded_data(all_draws, hmc_data, odds_data, freshness_data) -> bool:
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
    
    if issues:
        print("\n❌ DATA VALIDATION ERRORS:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    return True


def main():
    """Main execution function with improved error handling."""
    start_time = time.time()
    
    print("=" * 70)
    print("INTELLIGENT LOTTO SYSTEM V3.1: Rank-Aware Diversity Penalties")
    print("=" * 70)
    print(f"Active Models: {len(ACTIVE_MODELS)}")
    
    try:
        # ==================== STEP 0: VALIDATE FILES ====================
        print("\nStep 0: Validating data files...")
        if not validate_data_files():
            sys.exit(1)
        print("✓ All required files present")
        
        # ==================== STEP 1: LOAD DATA ====================
        print("\nStep 1: Loading data files...")
        
        # Load draw history
        all_draws = load_draw_history_json(DRAW_HISTORY_JSON)
        
        # Load HMC data
        hmc_data = load_hmc_json(HMC_JSON_INPUT)
        
        # Load odds data
        odds_data = load_odds_json(ODDS_JSON_INPUT)
        
        # Load freshness data (raw JSON for validation/passing to predictor)
        freshness_data = {}
        try:
            with open(FRESHNESS_JSON_INPUT, 'r') as f:
                freshness_data = json.load(f)
            print(f"✓ Loaded freshness data from {FRESHNESS_JSON_INPUT}")
            print(f"  Contains {len(freshness_data.get('distribution_analysis_7_numbers', []))} pattern distributions")
        except FileNotFoundError:
            print(f"❌ Error: {FRESHNESS_JSON_INPUT} not found. Pattern score feature will be 0.")
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in {FRESHNESS_JSON_INPUT}: {e}")
        
        # Validate loaded data
        if not validate_loaded_data(all_draws, hmc_data, odds_data, freshness_data):
            sys.exit(1)
    

        # Load dynamic freshness configuration
        W, C_max, recent_key, top_pattern_dist = load_freshness_config(FRESHNESS_JSON_INPUT)
        
        # Get final HMC categories (needed for win bias ratio calculation)
        # NOTE: We can extract this from the last draw's data in the history log,
        # but for simplicity, we assume the categories in lotto_trigger_periods are FINAL.
        
        # A safer approach for the final HMC is needed.
        # ASSUMPTION: The category in lotto_trigger_periods.json is the FINAL CATEGORY.
        final_categories = {}
        for num, data in hmc_data.items():
            if 'category' in data:
                # Map back to standard structure {'hot_numbers': [1, 2, ...]}
                cat_name = f"{data['category']}_numbers"
                if cat_name not in final_categories:
                    final_categories[cat_name] = []
                final_categories[cat_name].append(int(num))
        
        print(f"\n✓ Data Loading Summary:")
        print(f"  - Historical draws: {len(all_draws)}")
        print(f"  - HMC numbers tracked: {len(hmc_data)}")
        print(f"  - Freshness patterns: {len(freshness_data.get('distribution_analysis_7_numbers', []))}")
        print(f"  - Freshness Config: W={W}, C_max={C_max}, Key={recent_key}")
        
# ==================== STEP 2: EXTRACT FEATURES ====================
        print("\nStep 2: Extracting features from HMC data...")
        feature_start = time.time()
        
        # Calculate custom features
        print("  Calculating 'days_since_bonus' feature...")
        days_since_bonus_data = calculate_days_since_bonus(all_draws)
        
        # NEW: Calculate Win Bias Ratio (Requires final categories)
        print("  Calculating 'win_bias_ratio' feature...")
        win_bias_ratio_data = calculate_win_bias_ratio(all_draws, final_categories)
        
        print("  Calculating 'freshness_category' features...")
        freshness_category_features = calculate_freshness_category_features(
            hmc_data=hmc_data,
            c_max_threshold=C_max,
            recent_key=recent_key,
            top_pattern_dist=top_pattern_dist
        )
        pattern_score_data = {num: 0.0 for num in range(1, 47 + 1)}  # Deprecated
        
        # Extract static and dynamic features
        print("  Extracting dynamic recent count keys...")
        dynamic_recent_keys = get_dynamic_recent_keys(hmc_data)
        print(f"    Found {len(dynamic_recent_keys)} dynamic features: {[k[1] for k in dynamic_recent_keys]}")
        
        # Extract all features
        print("  Combining all features...")
        try:
            features_dict = extract_features_from_hmc_json(
                hmc_data, 
                dynamic_recent_keys, 
                days_since_bonus_data,
                pattern_score_data,
                freshness_category_features,
                win_bias_ratio_data # ADDED NEW DATA
            )
            print(f"  ✓ Features extracted for {len(features_dict)} numbers")
        except Exception as e:
            print(f"  ❌ Error extracting features: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        feature_time = time.time() - feature_start
        print(f"✓ Feature extraction completed in {feature_time:.2f} seconds")
        
        # ==================== STEP 3: ANALYZE HMC PATTERNS ====================
        print("\nStep 3: Analyzing HMC distribution patterns...")
        hot_count, medium_count, cold_count, pattern_percentage = get_most_likely_hmc_pattern(odds_data)
        
        # ==================== STEP 4: TRAIN MODELS ====================
        print("\nStep 4: Training ML models...")
        training_start = time.time()
        
        try:
            models, model_features = train_all_models(ACTIVE_MODELS, all_draws, features_dict)
            print(f"\n✓ Model training completed in {time.time() - training_start:.2f} seconds")
        except Exception as e:
            print(f"\n❌ Error during model training: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # ==================== STEP 5: GENERATE PREDICTIONS ====================
        print("\nStep 5: Generating predictions...")
        try:
            all_probabilities = generate_predictions(models, model_features, features_dict)
            print(f"✓ Predictions generated for {len(all_probabilities)} models")
        except Exception as e:
            print(f"❌ Error generating predictions: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # ==================== STEP 6: GENERATE PICKS ====================
        print("\nStep 6: Selecting optimal numbers...")
        try:
            lines = generate_all_picks(models, all_probabilities, features_dict, freshness_data)
            print(f"✓ Generated {len(lines)} lines of picks")
        except Exception as e:
            print(f"❌ Error generating picks: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # ==================== STEP 7: DISPLAY RESULTS ====================
        print("\nStep 7: Displaying results...")
        try:
            display_final_picks(lines)
            display_overlap_analysis(lines)
            display_rank_aware_explanation(ACTIVE_MODELS)
            display_feature_configuration(ACTIVE_MODELS)
            display_data_source_summary()
            
            # Save results to file
            try:
                with open('lottery_picks.txt', 'w') as f:
                    f.write("=" * 70 + "\n")
                    f.write("LOTTERY PICKS - GENERATED " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write("=" * 70 + "\n\n")
                    for line in lines:
                        f.write(f"Line {line['model_index']}: {line['model_name']} [{line['config_str']}]\n")
                        f.write(f"Numbers: {line['numbers']}\n")
                        f.write(f"Description: {line['description']}\n\n")
                print("\n✓ Results saved to 'lottery_picks.txt'")
            except Exception as e:
                print(f"⚠️  Could not save to file: {e}")
            
            # Display timing information
            total_time = time.time() - start_time
            print("\n" + "=" * 70)
            print("PERFORMANCE SUMMARY")
            print("=" * 70)
            print(f"Feature extraction: {feature_time:.2f}s")
            print(f"Model training: {time.time() - training_start:.2f}s")
            print(f"Total execution time: {total_time:.2f}s")
            
            display_completion_message()
        except Exception as e:
            print(f"❌ Error displaying results: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        print("\nStack trace:")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()