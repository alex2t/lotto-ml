"""
EXAMPLE: How to integrate AUC-ROC and comprehensive metrics into trainer.py

This shows the modifications needed to replace lines 307-340 in your trainer.py
with comprehensive metric evaluation.

CHANGES NEEDED:
1. Add import at top of trainer.py
2. Replace validation section with comprehensive metrics
3. Store metrics for model comparison
"""

# ============================================================================
# STEP 1: Add this import at the top of trainer.py (around line 10-18)
# ============================================================================

from ml_lotto.models.model_metrics import (
    calculate_comprehensive_metrics,
    compare_models,
    plot_model_comparison
)


# ============================================================================
# STEP 2: Replace lines 307-340 in train_model() function
# ============================================================================

def train_model_UPDATED(
    model_config: Dict[str, Any],
    train_df: pd.DataFrame,
    all_feature_names: List[str],
    model_index: int,
    exclude_bonus: bool = False,
    val_df: pd.DataFrame = None
) -> Tuple[Any, List[str], Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """
    Train a single model with comprehensive metric evaluation.

    CHANGES:
    - Added return of metrics dictionary
    - Replaced basic accuracy with comprehensive metrics
    """
    print(f"\n→ Model {model_index}: {model_config['name']}")
    print(f"  Description: {model_config['description']}")
    print(f"  Algorithm: {model_config['algorithm']}")

    if exclude_bonus:
        print(f"  ⭐ SPECIAL TRAINING: Optimized for MAIN 6 BALLS (jackpot focus)")

    # Expand feature selection
    from ml_lotto.features.extractor import expand_feature_selection
    selected_features = expand_feature_selection(
        model_config['features'],
        all_feature_names
    )

    if not selected_features:
        raise ValueError(f"No features selected for Model {model_index}")

    print(f"  Selected features ({len(selected_features)}): {selected_features}")
    print(f"  HMC Configuration: {model_config['hot_count']}H-{model_config['medium_count']}M-"
          f"{model_config['cold_count']}C+{model_config['generic_count']}G")
    print(f"  Diversity Penalty: {model_config['diversity_penalty']*100:.0f}%")

    # Prepare training data
    X_train = train_df[selected_features].values
    y_train = train_df['hit'].values

    # Calculate class imbalance for XGBoost
    scale_pos_weight = None
    if model_config['algorithm'] == 'xgboost':
        scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)

    # Create and train pipeline
    from ml_lotto.models.pipelines import create_model_pipeline
    pipeline = create_model_pipeline(model_config, scale_pos_weight)
    pipeline.fit(X_train, y_train)

    print(f"  ✓ Training complete")

    feature_importance_data = None
    metrics = None

    # ========================================================================
    # REPLACE OLD VALIDATION CODE (lines 307-340) WITH THIS:
    # ========================================================================
    if val_df is not None and len(val_df) > 0:
        X_val = val_df[selected_features].values
        y_val = val_df['hit'].values

        # 🆕 NEW: Calculate comprehensive metrics including AUC-ROC
        metrics = calculate_comprehensive_metrics(
            pipeline=pipeline,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            model_name=model_config['name'],
            save_plots=True,  # Set to False to disable plot generation
            output_dir='model_metrics'
        )

        # Feature Importance Analysis (keep existing)
        from ml_lotto.models.trainer import analyze_feature_importance
        feature_importance_data = analyze_feature_importance(
            pipeline,
            selected_features,
            model_config['name']
        )

    # 🆕 NEW: Return metrics as 4th element
    return pipeline, selected_features, feature_importance_data, metrics


# ============================================================================
# STEP 3: Update train_all_models() to collect and compare metrics
# ============================================================================

def train_all_models_UPDATED(
    model_configs: List[Dict[str, Any]],
    all_draws: List[Dict[str, Any]],
    features_dict: Dict[int, Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, List[str]], Dict[str, Any], Dict[str, Any]]:
    """
    Train all models and generate comparison report.

    CHANGES:
    - Added metrics collection for each model
    - Added model comparison at the end
    - Returns metrics as 4th element
    """
    from ml_lotto.features.extractor import get_all_feature_names
    from ml_lotto.models.trainer import (
        calculate_train_val_split,
        build_training_dataset
    )
    from ml_lotto.config import TRAINING_START_DRAW

    print("\n" + "="*70)
    print("TRAINING PIPELINE: Multi-Model Ensemble with Comprehensive Metrics")
    print("="*70)

    all_feature_names = get_all_feature_names()
    train_end_idx, val_start_idx = calculate_train_val_split(len(all_draws))

    print(f"\n📊 Dataset Split:")
    print(f"   Total draws: {len(all_draws)}")
    print(f"   Training: {TRAINING_START_DRAW} to {train_end_idx-1} ({train_end_idx - TRAINING_START_DRAW} draws)")
    print(f"   Validation: {val_start_idx} to {len(all_draws)-1} ({len(all_draws) - val_start_idx} draws)")

    # Build datasets (same as before)
    print("\n1. Building standard TRAINING dataset (Models 1, 3, 4)...")
    train_df_standard = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=False,
        start_index=TRAINING_START_DRAW,
        end_index=train_end_idx
    )

    print("\n2. Building standard VALIDATION dataset (Models 1, 3, 4)...")
    val_df_standard = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=False,
        start_index=val_start_idx,
        end_index=len(all_draws)
    )

    print("\n3. Building specialized TRAINING dataset (Model 2)...")
    train_df_model2 = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=True,
        start_index=TRAINING_START_DRAW,
        end_index=train_end_idx
    )

    print("\n4. Building specialized VALIDATION dataset (Model 2)...")
    val_df_model2 = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=True,
        start_index=val_start_idx,
        end_index=len(all_draws)
    )

    # Train each model
    models = {}
    model_features = {}
    feature_importance = {}
    all_metrics = {}  # 🆕 NEW: Store metrics for comparison

    for idx, model_config in enumerate(model_configs, 1):
        model_name = f"model_{idx}"

        # Use specialized dataset for Model 2
        if idx == 2:
            train_df_to_use = train_df_model2
            val_df_to_use = val_df_model2
            exclude_bonus = True
        else:
            train_df_to_use = train_df_standard
            val_df_to_use = val_df_standard
            exclude_bonus = False

        # 🆕 UPDATED: Now returns 4 values including metrics
        pipeline, selected_features, importance_data, metrics = train_model_UPDATED(
            model_config,
            train_df_to_use,
            all_feature_names,
            idx,
            exclude_bonus=exclude_bonus,
            val_df=val_df_to_use
        )

        models[model_name] = {
            'pipeline': pipeline,
            'config': model_config
        }
        model_features[model_name] = selected_features
        feature_importance[model_name] = importance_data

        # 🆕 NEW: Store metrics
        if metrics is not None:
            all_metrics[model_config['name']] = metrics

    print("\n" + "="*70)
    print("✓ ALL MODELS TRAINED WITH COMPREHENSIVE VALIDATION")
    print("="*70)

    # 🆕 NEW: Generate model comparison
    if len(all_metrics) > 0:
        print("\n" + "="*70)
        print("GENERATING MODEL COMPARISON REPORT")
        print("="*70)

        # Create comparison table
        comparison_df = compare_models(all_metrics, output_dir='model_metrics')

        # Create comparison visualizations
        plot_model_comparison(all_metrics, output_dir='model_metrics')

    # 🆕 NEW: Return metrics as 4th element
    return models, model_features, feature_importance, all_metrics


# ============================================================================
# STEP 4: Update quickpick.py to handle new return value
# ============================================================================

# In quickpick.py, change this:
# models, model_features, feature_importance = train_all_models(...)

# To this:
# models, model_features, feature_importance, all_metrics = train_all_models(...)

# Then optionally save metrics to file:
# import json
# with open('lottery_model_metrics.json', 'w') as f:
#     json.dump(all_metrics, f, indent=2)


# ============================================================================
# EXAMPLE OUTPUT
# ============================================================================

"""
When you run this, you'll see output like:

======================================================================
  📊 MODEL EVALUATION: Timing Pattern Specialist
======================================================================
  Train Accuracy: 0.1523
  Val Accuracy:   0.1456
  Overfit Gap:    0.0067

  🎯 AUC-ROC Scores:
     Train AUC: 0.6834
     Val AUC:   0.6512
     ✅ Good discrimination
     💾 Saved ROC curve to model_metrics/Timing_Pattern_Specialist_roc_curve.png

  📈 Precision-Recall Metrics:
     Precision: 0.1723  (When model predicts 1, how often correct?)
     Recall:    0.5234  (Of all winning numbers, how many caught?)
     F1-Score:  0.2598  (Harmonic mean of precision & recall)
     Avg Precision: 0.1987  (Area under PR curve)
     💾 Saved PR curve to model_metrics/Timing_Pattern_Specialist_pr_curve.png

  🔢 Confusion Matrix:
     ┌────────────────────┬──────────┬──────────┐
     │                    │ Pred=0   │ Pred=1   │
     ├────────────────────┼──────────┼──────────┤
     │ Actual=0 (No win)  │  3856    │   578    │
     │ Actual=1 (Win)     │   423    │   467    │
     └────────────────────┴──────────┴──────────┘

     Sensitivity (Recall):  0.5234
     Specificity:           0.8697

  🎯 Calibration Analysis:
     Mean Calibration Error: 0.0324
     ✅ Good calibration
     💾 Saved calibration curve to model_metrics/Timing_Pattern_Specialist_calibration.png

  ⚙️  Threshold Analysis:
     Default threshold: 0.5
     Optimal threshold: 0.1234 (maximizes F1 = 0.2845)

  📋 Detailed Classification Report:
                   precision    recall  f1-score   support

          No Win     0.9011    0.8697    0.8851      4434
             Win     0.4470    0.5234    0.4822       890

        accuracy                         0.8234      5324
       macro avg     0.6741    0.6966    0.6837      5324
    weighted avg     0.8356    0.8234    0.8288      5324

======================================================================

[... same for other 3 models ...]

====================================================================================================
  🏆 MODEL COMPARISON SUMMARY
====================================================================================================
                           Model  Val Accuracy  Val AUC-ROC  Precision    Recall  F1-Score  Avg Precision  Calibration Error  Overfit Gap
Complexity Explorer (XGBoost)       0.8534        0.7234      0.5123    0.6234    0.5623         0.4234             0.0234       0.0123
    Timing Pattern Specialist       0.8234        0.6512      0.4470    0.5234    0.4822         0.3987             0.0324       0.0067
         Jackpot Optimizer          0.8123        0.6345      0.4234    0.5123    0.4634         0.3756             0.0456       0.0234
           Pool Generator           0.7956        0.6123      0.3987    0.4987    0.4423         0.3456             0.0567       0.0345
====================================================================================================

💾 Saved comparison to model_metrics/model_comparison.csv
💾 Saved comparison chart to model_metrics/model_comparison_chart.png
"""
