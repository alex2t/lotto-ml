#!/usr/bin/env python3
"""
main.py
=======
Main entry point for the Lottery Prediction System V3.1
Orchestrates the entire prediction workflow.

USAGE:
    python main.py

CONFIGURATION:
    Edit config.py to customize:
    - Model configurations (features, HMC ratios, penalties)
    - File paths
    - Display settings
"""

import warnings
warnings.filterwarnings('ignore')

from ml_lotto.config import (
    DRAW_HISTORY_JSON,  # Updated to use new JSON source
    HMC_JSON_INPUT,
    ODDS_JSON_INPUT,
    ACTIVE_MODELS
)
from ml_lotto.data_loader import (
    load_draw_history_json, # Updated to use new loader
    load_hmc_json,
    load_odds_json,
    get_most_likely_hmc_pattern
)
from ml_lotto.feature_extractor import (
    get_dynamic_recent_keys,
    extract_features_from_hmc_json,
    calculate_days_since_bonus # New import for the custom feature
)
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


def main():
    """Main execution function."""
    print("=" * 70)
    print("INTELLIGENT LOTTO SYSTEM V3.1: Rank-Aware Diversity Penalties")
    print("=" * 70)
    print(f"Active Models: {len(ACTIVE_MODELS)}")
    
    # ==================== STEP 1: LOAD DATA ====================
    print("\nStep 1: Loading data files...")
    # Load draw history from new JSON file (replaces CSV)
    all_draws = load_draw_history_json(DRAW_HISTORY_JSON)
    hmc_data = load_hmc_json(HMC_JSON_INPUT)
    odds_data = load_odds_json(ODDS_JSON_INPUT)
    
    if not all_draws or not hmc_data or not odds_data:
        print("\n✗ Fatal Error: Data files failed to load.")
        return
    
    print(f"✓ Loaded {len(all_draws)} historical draws")
    
    # ==================== STEP 2: EXTRACT FEATURES ====================
    print("\nStep 2: Extracting features from HMC data...")
    
    # Calculate the new custom feature from the comprehensive draw history
    days_since_bonus_data = calculate_days_since_bonus(all_draws)
    
    # Extract static and dynamic features
    dynamic_recent_keys = get_dynamic_recent_keys(hmc_data)
    
    # Pass the new custom feature data to the extractor
    features_dict = extract_features_from_hmc_json(
        hmc_data, 
        dynamic_recent_keys, 
        days_since_bonus_data
    )
    
    # ==================== STEP 3: ANALYZE HMC PATTERNS ====================
    print("\nStep 3: Analyzing HMC distribution patterns...")
    hot_count, medium_count, cold_count, pattern_percentage = get_most_likely_hmc_pattern(odds_data)
    
    # ==================== STEP 4: TRAIN MODELS ====================
    models, model_features = train_all_models(ACTIVE_MODELS, all_draws, features_dict)
    
    # ==================== STEP 5: GENERATE PREDICTIONS ====================
    all_probabilities = generate_predictions(models, model_features, features_dict)
    
    # ==================== STEP 6: GENERATE PICKS ====================
    lines = generate_all_picks(models, all_probabilities, features_dict)
    
    # ==================== STEP 7: DISPLAY RESULTS ====================
    display_final_picks(lines)
    display_overlap_analysis(lines)
    display_rank_aware_explanation(ACTIVE_MODELS)
    display_feature_configuration(ACTIVE_MODELS)
    display_data_source_summary()
    display_completion_message()


if __name__ == "__main__":
    main()