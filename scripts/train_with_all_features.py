"""
train_with_all_features.py
===========================
Comprehensive training script that demonstrates all ML improvements:

1. ✅ SMOTE (class balancing)
2. ✅ Optimal threshold selection
3. ✅ Feature selection (correlation + importance)
4. ✅ Rolling statistics (temporal features)
5. ✅ Hyperparameter tuning (TimeSeriesSplit CV)
6. ✅ Enhanced metrics (Top-K accuracy, PR-AUC)
7. ✅ Ensemble voting (multiple strategies)

This script shows how to integrate all features into your training pipeline.
"""

import json
import sys
from ml_lotto.data.loader import load_draw_history_with_bias_ratios, load_hmc_json
from ml_lotto.features.rolling_stats import extract_rolling_features_for_all_numbers
from ml_lotto.features.extractor import extract_features_from_hmc_json, get_all_feature_names
from ml_lotto.features.base import get_dynamic_recent_keys
from ml_lotto.models.trainer import build_training_dataset, calculate_train_val_split
from ml_lotto.models.trainer import train_model
from ml_lotto.models.model_metrics import compare_models
from ml_lotto.models.hyperparameter_tuning import compare_tuning_results
from ml_lotto.prediction.ensemble import EnsembleVoter, display_voting_results, analyze_ensemble_agreement, display_agreement_analysis
from ml_lotto.config import MAX_NUMBER, TRAINING_START_DRAW

# Configuration
DRAW_HISTORY_JSON = 'data/lotto_draw_history.json'
HMC_JSON = 'data/lotto_trigger_periods.json'

# Model configurations (example with Random Forest and Logistic Regression)
MODEL_CONFIGS = [
    {
        'name': 'Model1_RF_Tuned',
        'description': 'Random Forest with all features enabled',
        'algorithm': 'random_forest',
        'features': ['all']
    },
    {
        'name': 'Model2_Logistic_Tuned',
        'description': 'Logistic Regression with all features enabled',
        'algorithm': 'logistic',
        'features': ['all']
    }
]


def main():
    """
    Train models with all ML improvements enabled.
    """
    print("\n" + "="*80)
    print("  🚀 COMPREHENSIVE ML TRAINING WITH ALL FEATURES")
    print("="*80)
    print("\nEnabled Features:")
    print("  ✅ SMOTE (class balancing)")
    print("  ✅ Optimal threshold selection")
    print("  ✅ Feature selection (correlation + importance)")
    print("  ✅ Rolling statistics (9 temporal features per number)")
    print("  ✅ Hyperparameter tuning with TimeSeriesSplit CV")
    print("  ✅ Enhanced metrics (Top-K accuracy, PR-AUC)")
    print("  ✅ Ensemble voting (majority, weighted, unanimous)")
    print("="*80)

    # ========================================
    # 1. LOAD DATA
    # ========================================
    print("\n📂 Loading data...")
    all_draws, _ = load_draw_history_with_bias_ratios(DRAW_HISTORY_JSON)
    hmc_data = load_hmc_json(HMC_JSON)

    print(f"   Loaded {len(all_draws)} draws")

    # ========================================
    # 2. EXTRACT ROLLING STATISTICS FEATURES
    # ========================================
    print("\n📊 Extracting rolling statistics features...")
    rolling_stats_features = extract_rolling_features_for_all_numbers(
        all_draws,
        training_start_draw=TRAINING_START_DRAW,
        max_number=MAX_NUMBER
    )

    # ========================================
    # 3. EXTRACT ALL FEATURES
    # ========================================
    print("\n🔧 Extracting all features...")
    dynamic_recent_keys = get_dynamic_recent_keys(hmc_data)

    # Minimal feature extraction (add your own feature data as needed)
    days_since_bonus_data = {num: 0 for num in range(1, MAX_NUMBER + 1)}
    pattern_score_data = {num: 0.0 for num in range(1, MAX_NUMBER + 1)}

    features_dict = extract_features_from_hmc_json(
        hmc_data,
        dynamic_recent_keys,
        days_since_bonus_data,
        pattern_score_data,
        rolling_stats_features=rolling_stats_features  # Include rolling stats
    )

    all_feature_names = get_all_feature_names(hmc_data, dynamic_recent_keys)
    print(f"   Extracted {len(all_feature_names)} features")

    # ========================================
    # 4. BUILD TRAINING/VALIDATION DATASETS
    # ========================================
    print("\n📚 Building training and validation datasets...")
    train_end_idx, val_start_idx = calculate_train_val_split(len(all_draws))

    train_df = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=False,
        start_index=TRAINING_START_DRAW,
        end_index=train_end_idx
    )

    val_df = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=False,
        start_index=val_start_idx,
        end_index=len(all_draws)
    )

    print(f"   Training set: {len(train_df)} samples")
    print(f"   Validation set: {len(val_df)} samples")

    # ========================================
    # 5. TRAIN MODELS WITH ALL FEATURES
    # ========================================
    print("\n🎯 Training models with all features enabled...")
    print("="*80)

    trained_models = {}
    all_metrics = {}
    all_tuning_results = {}

    for idx, model_config in enumerate(MODEL_CONFIGS, start=1):
        # Train with ALL features enabled
        pipeline, features, importance, metrics, tuning_results = train_model(
            model_config=model_config,
            train_df=train_df,
            all_feature_names=all_feature_names,
            model_index=idx,
            exclude_bonus=False,
            val_df=val_df,
            # SMOTE settings
            use_smote=True,
            smote_sampling_strategy=0.3,
            # Feature selection settings
            enable_feature_selection=True,
            correlation_threshold=0.95,
            importance_threshold=0.005,
            # Hyperparameter tuning settings
            enable_hyperparameter_tuning=True,
            tuning_mode='quick',  # or 'extensive' for comprehensive search
            tuning_cv_splits=3,
            tuning_scoring='roc_auc'
        )

        trained_models[model_config['name']] = {
            'pipeline': pipeline,
            'features': features,
            'config': model_config
        }

        if metrics:
            all_metrics[model_config['name']] = metrics

        if tuning_results:
            all_tuning_results[model_config['name']] = tuning_results

    # ========================================
    # 6. COMPARE MODELS
    # ========================================
    print("\n📊 Comparing all models...")
    comparison_df = compare_models(all_metrics, output_dir='model_metrics')

    # ========================================
    # 7. COMPARE HYPERPARAMETER TUNING RESULTS
    # ========================================
    if all_tuning_results:
        print("\n🔧 Comparing hyperparameter tuning results...")
        tuning_comparison = compare_tuning_results(all_tuning_results, output_dir='model_metrics')

    # ========================================
    # 8. ENSEMBLE VOTING
    # ========================================
    print("\n🎲 Generating ensemble predictions...")

    # Collect predictions from all models
    model_predictions = {}
    model_probabilities = {}

    for model_name, model_info in trained_models.items():
        pipeline = model_info['pipeline']
        features = model_info['features']

        # Get validation predictions
        X_val = val_df[features].values
        val_proba = pipeline.predict_proba(X_val)[:, 1] if hasattr(pipeline, 'predict_proba') else pipeline.decision_function(X_val)

        # Get optimal threshold from metrics
        optimal_threshold = all_metrics[model_name].get('optimal_threshold', 0.5)

        # Get top predictions
        val_pred = (val_proba >= optimal_threshold).astype(int)
        top_indices = val_proba.argsort()[::-1][:15]  # Top 15 predictions

        model_predictions[model_name] = top_indices.tolist()
        model_probabilities[model_name] = {idx: val_proba[idx] for idx in top_indices}

    # Apply ensemble voting with majority strategy
    voter = EnsembleVoter(strategy='majority')
    ensemble_predictions, voting_details = voter.vote(
        model_predictions,
        model_probabilities,
        top_k=10
    )

    display_voting_results(ensemble_predictions, voting_details, list(trained_models.keys()))

    # Analyze model agreement
    agreement = analyze_ensemble_agreement(model_predictions, model_probabilities)
    display_agreement_analysis(agreement)

    # ========================================
    # 9. SUMMARY
    # ========================================
    print("\n" + "="*80)
    print("  ✅ TRAINING COMPLETE!")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   Models trained: {len(trained_models)}")
    print(f"   Features per model: {len(features)} (after selection)")
    print(f"   Hyperparameter tuning: {'✅ Completed' if all_tuning_results else '❌ Skipped'}")
    print(f"   Ensemble predictions: {len(ensemble_predictions)} numbers")

    print(f"\n📁 Results saved to:")
    print(f"   model_metrics/model_comparison.csv")
    if all_tuning_results:
        print(f"   model_metrics/tuning_comparison.csv")
        print(f"   model_metrics/*_tuning_results.json")

    print("\n💡 Next steps:")
    print("   1. Review model_comparison.csv for best model")
    print("   2. Check Top-K accuracy (most relevant for lottery)")
    print("   3. Use ensemble predictions for final number selection")
    print("   4. Adjust tuning_mode to 'extensive' for better results")
    print("="*80 + "\n")

    return trained_models, all_metrics, ensemble_predictions


if __name__ == '__main__':
    try:
        trained_models, metrics, ensemble_preds = main()
        print(f"\n🎯 Ensemble final picks: {ensemble_preds}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
