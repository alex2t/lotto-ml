"""
trainer.py
==========
Handles ML model training with configurable algorithms and features.

VERSION: 3.12 (Comprehensive Metrics Edition)
- Added AUC-ROC curves and comprehensive evaluation metrics
- Integrated model comparison and visualization
- Enhanced validation with precision/recall/F1 metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from sklearn.calibration import calibration_curve
from ml_lotto.config import MAX_NUMBER, TRAINING_START_DRAW, VALIDATION_SPLIT_RATIO
from ml_lotto.models.pipelines import create_model_pipeline
from ml_lotto.features.extractor import expand_feature_selection, get_all_feature_names
from ml_lotto.models.model_metrics import (
    calculate_comprehensive_metrics,
    compare_models,
    plot_model_comparison
)


def calculate_train_val_split(total_draws: int, split_ratio: float = VALIDATION_SPLIT_RATIO) -> Tuple[int, int]:
    """
    Calculate train/validation split indices to prevent data leakage.

    Args:
        total_draws: Total number of draws available
        split_ratio: Ratio of data to use for training (default: 0.80)

    Returns:
        Tuple of (train_end_index, val_start_index)
        - train_end_index: Last index for training (exclusive)
        - val_start_index: First index for validation
    """
    available_draws = total_draws - TRAINING_START_DRAW
    train_size = int(available_draws * split_ratio)
    train_end_index = TRAINING_START_DRAW + train_size
    val_start_index = train_end_index

    return train_end_index, val_start_index


def build_training_dataset(
    all_draws: List[Dict[str, Any]],
    features_dict: Dict[int, Dict[str, Any]],
    all_feature_names: List[str],
    exclude_bonus: bool = False,
    start_index: int = TRAINING_START_DRAW,
    end_index: int = None
) -> pd.DataFrame:
    """
    Build training dataset by combining features and labels with proper train/validation split.

    INPUT SOURCES:
        all_draws (from lotto_draw_history.json) → LABELS (y = did number win?)
        features_dict (from lotto_trigger_periods.json) → FEATURES (X = number statistics)

    TRAINING PROCESS:
        For each historical draw in specified range:
            For each number 1-47:
                X (features) ← [total_count, days_since_last, ..., days_since_bonus]
                y (label)    ← 1 if number won that draw, 0 if not

    Args:
        all_draws: Historical draw data with winning numbers
        features_dict: Feature values for each number
        all_feature_names: List of all available feature names
        exclude_bonus: If True, only main 6 numbers are labeled as hits (for Model 2)
        start_index: First draw index to include (default: TRAINING_START_DRAW)
        end_index: Last draw index to include (exclusive). If None, uses all available draws.

    Returns:
        DataFrame with all features + 'hit' column (label)
    """
    if end_index is None:
        end_index = len(all_draws)

    dataset_type = "training" if end_index < len(all_draws) else "full"
    print(f"\nBuilding {dataset_type} dataset (exclude_bonus={exclude_bonus})...")
    print(f"  Draw range: {start_index} to {end_index-1} ({end_index - start_index} draws)")
    records = []

    # Build training data by combining FEATURES + LABELS
    for draw_idx in range(start_index, end_index):
        # CRITICAL CHANGE: Different labeling strategy based on exclude_bonus
        if exclude_bonus:
            # Model 2: ONLY the first 6 numbers (main balls, exclude bonus)
            target_numbers = set(all_draws[draw_idx]['numbers'][:6])
            if draw_idx == TRAINING_START_DRAW:
                print("  Model 2: Training on MAIN 6 ONLY (excluding bonus ball)")
        else:
            # Models 1 & 3: All 7 numbers (including bonus)
            target_numbers = set(all_draws[draw_idx]['numbers'])
            if draw_idx == TRAINING_START_DRAW:
                print("  Standard: Training on ALL 7 positions")

        for num in range(1, MAX_NUMBER + 1):
            if num in features_dict:
                # FEATURES: Get statistics from JSON
                feat = features_dict[num]
                record = {}

                # Add all features
                for feature_name in all_feature_names:
                    record[feature_name] = feat.get(feature_name, 0)

                # LABEL: Did this number win in this draw?
                record['hit'] = 1 if num in target_numbers else 0

                records.append(record)

    train_df = pd.DataFrame(records)
    print(f"✓ Training dataset created: {len(train_df)} records")
    return train_df


def analyze_feature_importance(
    pipeline: Any,
    feature_names: List[str],
    model_name: str,
    top_n: int = 10
) -> Optional[List[Dict[str, Any]]]:
    """
    Analyze and display feature importance after training.

    Args:
        pipeline: Trained sklearn pipeline
        feature_names: List of feature names used in training
        model_name: Name of the model for display
        top_n: Number of top features to display

    Returns:
        List of dicts with top N feature importance data, or None if not applicable
        Format: [{'feature': name, 'importance': value, 'abs_importance': value}, ...]
    """
    try:
        # Get the calibrated classifier from pipeline
        calibrated_clf = pipeline.named_steps['clf']

        # Extract the base estimator from CalibratedClassifierCV
        # After fitting, calibrated_classifiers_ contains the fitted models
        if hasattr(calibrated_clf, 'calibrated_classifiers_'):
            # Use the first calibrated classifier (they should be similar across folds)
            base_estimator = calibrated_clf.calibrated_classifiers_[0].estimator
        else:
            # Fallback to the original estimator
            base_estimator = calibrated_clf.estimator

        # Extract importance based on model type
        if hasattr(base_estimator, 'coef_'):
            # Linear models (Logistic Regression)
            importances = base_estimator.coef_[0]
        elif hasattr(base_estimator, 'feature_importances_'):
            # Tree-based models (XGBoost, Random Forest)
            importances = base_estimator.feature_importances_
        else:
            return None

        # Create importance dataframe
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances,
            'abs_importance': np.abs(importances)
        }).sort_values('abs_importance', ascending=False)

        print(f"\n  📊 Feature Importance Analysis:")
        print(f"  Top {top_n} Most Important Features:")
        for idx, row in importance_df.head(top_n).iterrows():
            print(f"    {row['feature']:30s} : {row['abs_importance']:8.4f}")

        # Identify low-importance features
        threshold = 0.01
        low_importance = importance_df[importance_df['abs_importance'] < threshold]
        if len(low_importance) > 0:
            print(f"\n  ⚠️  {len(low_importance)} features with importance < {threshold}:")
            print(f"      {', '.join(low_importance['feature'].tolist()[:5])}")
            if len(low_importance) > 5:
                print(f"      ... and {len(low_importance) - 5} more")

        # Return top N as list of dicts for file output
        top_features = []
        for idx, row in importance_df.head(top_n).iterrows():
            top_features.append({
                'feature': row['feature'],
                'importance': float(row['importance']),
                'abs_importance': float(row['abs_importance'])
            })

        return top_features

    except Exception as e:
        print(f"  ⚠️  Could not analyze feature importance: {e}")
        import traceback
        traceback.print_exc()
        return None


def validate_calibration(
    pipeline: Any,
    X_val: np.ndarray,
    y_val: np.ndarray,
    model_name: str
) -> float:
    """
    Validate probability calibration quality.

    Args:
        pipeline: Trained sklearn pipeline
        X_val: Validation features
        y_val: Validation labels
        model_name: Name of the model for display

    Returns:
        Mean calibration error
    """
    try:
        # Get predicted probabilities
        y_pred_proba = pipeline.predict_proba(X_val)[:, 1]

        # Calculate calibration curve
        prob_true, prob_pred = calibration_curve(
            y_val,
            y_pred_proba,
            n_bins=10,
            strategy='quantile'
        )

        # Calculate calibration error
        calibration_error = np.mean(np.abs(prob_true - prob_pred))

        print(f"\n  🎯 Calibration Analysis:")
        print(f"     Mean Calibration Error: {calibration_error:.4f}")

        if calibration_error > 0.1:
            print(f"     ⚠️  High calibration error - consider different calibration method")
        elif calibration_error > 0.05:
            print(f"     ⚡ Moderate calibration - acceptable but could improve")
        else:
            print(f"     ✅ Good calibration")

        return calibration_error

    except Exception as e:
        print(f"  ⚠️  Could not validate calibration: {e}")
        return -1.0


def train_model(
    model_config: Dict[str, Any],
    train_df: pd.DataFrame,
    all_feature_names: List[str],
    model_index: int,
    exclude_bonus: bool = False,
    val_df: pd.DataFrame = None
) -> Tuple[Any, List[str], Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """
    Train a single model based on its configuration with comprehensive validation metrics.

    Args:
        model_config: Model configuration dictionary
        train_df: Training DataFrame with features and labels
        all_feature_names: All available feature names
        model_index: Model number (for display)
        exclude_bonus: If True, model is trained on main 6 only
        val_df: Optional validation DataFrame for evaluation

    Returns:
        Tuple of (trained_pipeline, selected_features, feature_importance_data, metrics)
    """
    print(f"\n→ Model {model_index}: {model_config['name']}")
    print(f"  Description: {model_config['description']}")
    print(f"  Algorithm: {model_config['algorithm']}")

    if exclude_bonus:
        print(f"  ⭐ SPECIAL TRAINING: Optimized for MAIN 6 BALLS (jackpot focus)")

    # Expand feature selection
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
    pipeline = create_model_pipeline(model_config, scale_pos_weight)
    pipeline.fit(X_train, y_train)

    print(f"  ✓ Training complete")

    feature_importance_data = None
    metrics = None

    # Evaluate on validation set if provided
    if val_df is not None and len(val_df) > 0:
        X_val = val_df[selected_features].values
        y_val = val_df['hit'].values

        # Calculate comprehensive metrics including AUC-ROC
        metrics = calculate_comprehensive_metrics(
            pipeline=pipeline,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            model_name=model_config['name'],
            save_plots=True,
            output_dir='model_metrics'
        )

        # Feature Importance Analysis
        feature_importance_data = analyze_feature_importance(
            pipeline,
            selected_features,
            model_config['name']
        )

    return pipeline, selected_features, feature_importance_data, metrics


def train_all_models(
    model_configs: List[Dict[str, Any]],
    all_draws: List[Dict[str, Any]],
    features_dict: Dict[int, Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, List[str]], Dict[str, Optional[List[Dict[str, Any]]]], Dict[str, Dict[str, Any]]]:
    """
    Train all configured models with comprehensive validation metrics and model comparison.

    Args:
        model_configs: List of model configuration dictionaries
        all_draws: Historical draw data
        features_dict: Feature values for all numbers

    Returns:
        Tuple of (models_dict, model_features_dict, feature_importance_dict, all_metrics_dict)
        - models_dict: {model_name: {'pipeline': pipeline, 'config': config}}
        - model_features_dict: {model_name: [feature_names]}
        - feature_importance_dict: {model_name: [top feature importance data]}
        - all_metrics_dict: {model_name: comprehensive metrics dict with AUC-ROC, etc.}
    """
    print("\n" + "="*70)
    print("TRAINING MULTIPLE ML MODELS WITH SPECIALIZED OBJECTIVES")
    print("="*70)
    print("\nMODEL SPECIALIZATION:")
    print("  Model 1: Momentum specialist (all 7 positions)")
    print("  Model 2: Jackpot optimizer (main 6 ONLY) ⭐")
    print("  Model 3: Complexity explorer (all 7 positions)")
    print("\nDATA SOURCES:")
    print("  Features (X) ← lotto_trigger_periods.json + custom calculations")
    print("  Labels (y)   ← lotto_draw_history.json")

    # Calculate train/validation split to prevent data leakage
    train_end_idx, val_start_idx = calculate_train_val_split(len(all_draws))
    total_available = len(all_draws) - TRAINING_START_DRAW
    train_size = train_end_idx - TRAINING_START_DRAW
    val_size = len(all_draws) - val_start_idx

    print(f"\n📊 TRAIN/VALIDATION SPLIT:")
    print(f"  Total available draws: {total_available}")
    print(f"  Training draws: {train_size} ({train_size/total_available*100:.1f}%)")
    print(f"  Validation draws: {val_size} ({val_size/total_available*100:.1f}%)")
    print(f"  Split ratio: {VALIDATION_SPLIT_RATIO:.2f}")
    print(f"  ✓ Validation set held out to prevent data leakage")

    # Get all available feature names
    all_feature_names = get_all_feature_names(features_dict)
    print(f"  Available features: {all_feature_names}\n")

    # Build FOUR datasets: train/val for standard models and train/val for model2
    print("\n1. Building standard TRAINING dataset (Models 1, 3, 4)...")
    train_df_standard = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=False,  # All 7 positions
        start_index=TRAINING_START_DRAW,
        end_index=train_end_idx
    )

    print("\n2. Building standard VALIDATION dataset (Models 1, 3, 4)...")
    val_df_standard = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=False,  # All 7 positions
        start_index=val_start_idx,
        end_index=len(all_draws)
    )

    print("\n3. Building specialized TRAINING dataset (Model 2)...")
    train_df_model2 = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=True,  # Main 6 only ⭐
        start_index=TRAINING_START_DRAW,
        end_index=train_end_idx
    )

    print("\n4. Building specialized VALIDATION dataset (Model 2)...")
    val_df_model2 = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=True,  # Main 6 only ⭐
        start_index=val_start_idx,
        end_index=len(all_draws)
    )

    # Train each model with proper train/validation split
    models = {}
    model_features = {}
    feature_importance = {}
    all_metrics = {}

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

        pipeline, selected_features, importance_data, metrics = train_model(
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

        # Store metrics for comparison
        if metrics is not None:
            all_metrics[model_config['name']] = metrics

    print("\n" + "="*70)
    print("✓ ALL MODELS TRAINED WITH COMPREHENSIVE VALIDATION")
    print("="*70)

    # Generate model comparison report
    if len(all_metrics) > 0:
        print("\n" + "="*70)
        print("GENERATING MODEL COMPARISON REPORT")
        print("="*70)

        comparison_df = compare_models(all_metrics, output_dir='model_metrics')
        plot_model_comparison(all_metrics, output_dir='model_metrics')

        print("\n📁 Metrics and visualizations saved to model_metrics/")

    return models, model_features, feature_importance, all_metrics