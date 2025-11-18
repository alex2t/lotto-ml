#!/usr/bin/env python3
"""
test_model_metrics.py
=====================
Standalone script to evaluate existing trained models with comprehensive metrics.

Usage:
    python test_model_metrics.py

This will:
1. Load your existing models (if available)
2. Evaluate them with AUC-ROC and other metrics
3. Generate comparison charts
4. Save results to model_metrics/
"""

import sys
import os
import pickle
import pandas as pd
import numpy as np
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from ml_lotto.config import MAX_NUMBER, TRAINING_START_DRAW, VALIDATION_SPLIT_RATIO
from ml_lotto.data.loader import load_lottery_data
from ml_lotto.features.extractor import extract_features, get_all_feature_names
from ml_lotto.models.trainer import (
    build_training_dataset,
    calculate_train_val_split
)
from ml_lotto.models.model_metrics import (
    calculate_comprehensive_metrics,
    compare_models,
    plot_model_comparison
)


def evaluate_saved_models():
    """
    Evaluate saved models with comprehensive metrics.
    """
    print("="*70)
    print("LOTTERY MODEL COMPREHENSIVE EVALUATION")
    print("="*70)

    # Check if models exist
    model_files = [
        'model_1_pipeline.pkl',
        'model_2_pipeline.pkl',
        'model_3_pipeline.pkl',
        'model_4_pipeline.pkl'
    ]

    available_models = {}
    for model_file in model_files:
        if os.path.exists(model_file):
            model_num = model_file.split('_')[1]
            available_models[f'model_{model_num}'] = model_file
        else:
            print(f"⚠️  Model not found: {model_file}")

    if not available_models:
        print("\n❌ No trained models found!")
        print("Please run quickpick.py or drawpick.py first to train models.\n")
        return

    print(f"\n✓ Found {len(available_models)} trained models")

    # Load data
    print("\n📊 Loading lottery data...")
    all_draws = load_lottery_data()
    print(f"   Loaded {len(all_draws)} historical draws")

    # Extract features
    print("\n🔧 Extracting features...")
    features_dict = extract_features(all_draws)
    all_feature_names = get_all_feature_names()
    print(f"   Extracted {len(all_feature_names)} features")

    # Calculate split
    train_end_idx, val_start_idx = calculate_train_val_split(len(all_draws))

    print(f"\n📊 Dataset Split:")
    print(f"   Total draws: {len(all_draws)}")
    print(f"   Training: {TRAINING_START_DRAW} to {train_end_idx-1} ({train_end_idx - TRAINING_START_DRAW} draws)")
    print(f"   Validation: {val_start_idx} to {len(all_draws)-1} ({len(all_draws) - val_start_idx} draws)")

    # Build datasets
    print("\n🏗️  Building datasets...")

    # Standard dataset (for models 1, 3, 4)
    train_df_standard = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=False,
        start_index=TRAINING_START_DRAW,
        end_index=train_end_idx
    )

    val_df_standard = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=False,
        start_index=val_start_idx,
        end_index=len(all_draws)
    )

    # Model 2 dataset (main 6 only)
    train_df_model2 = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=True,
        start_index=TRAINING_START_DRAW,
        end_index=train_end_idx
    )

    val_df_model2 = build_training_dataset(
        all_draws,
        features_dict,
        all_feature_names,
        exclude_bonus=True,
        start_index=val_start_idx,
        end_index=len(all_draws)
    )

    # Model configurations
    model_configs = {
        'model_1': {
            'name': 'Timing Pattern Specialist',
            'dataset': 'standard',
            'features_file': 'model_1_features.pkl'
        },
        'model_2': {
            'name': 'Jackpot Optimizer',
            'dataset': 'model2',
            'features_file': 'model_2_features.pkl'
        },
        'model_3': {
            'name': 'Complexity Explorer (XGBoost)',
            'dataset': 'standard',
            'features_file': 'model_3_features.pkl'
        },
        'model_4': {
            'name': 'Pool Generator',
            'dataset': 'standard',
            'features_file': 'model_4_features.pkl'
        }
    }

    # Evaluate each model
    all_metrics = {}

    for model_key, model_file in available_models.items():
        if model_key not in model_configs:
            continue

        config = model_configs[model_key]

        print(f"\n{'='*70}")
        print(f"EVALUATING: {config['name']}")
        print(f"{'='*70}")

        # Load model
        try:
            with open(model_file, 'rb') as f:
                pipeline = pickle.load(f)
        except Exception as e:
            print(f"❌ Failed to load {model_file}: {e}")
            continue

        # Load features
        try:
            with open(config['features_file'], 'rb') as f:
                selected_features = pickle.load(f)
        except Exception as e:
            print(f"⚠️  Could not load features from {config['features_file']}: {e}")
            print(f"   Using all available features")
            selected_features = all_feature_names

        # Select appropriate dataset
        if config['dataset'] == 'model2':
            train_df = train_df_model2
            val_df = val_df_model2
        else:
            train_df = train_df_standard
            val_df = val_df_standard

        # Filter features that exist in dataset
        available_features = [f for f in selected_features if f in train_df.columns]

        if len(available_features) == 0:
            print(f"❌ No valid features found for {config['name']}")
            continue

        print(f"Using {len(available_features)} features")

        # Prepare data
        X_train = train_df[available_features].values
        y_train = train_df['hit'].values
        X_val = val_df[available_features].values
        y_val = val_df['hit'].values

        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            pipeline=pipeline,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            model_name=config['name'],
            save_plots=True,
            output_dir='model_metrics'
        )

        all_metrics[config['name']] = metrics

    # Generate comparison
    if len(all_metrics) > 0:
        print("\n" + "="*70)
        print("GENERATING MODEL COMPARISON")
        print("="*70)

        comparison_df = compare_models(all_metrics, output_dir='model_metrics')
        plot_model_comparison(all_metrics, output_dir='model_metrics')

        print("\n✅ Evaluation complete!")
        print(f"\n📁 Results saved to model_metrics/:")
        print(f"   - Individual ROC curves: *_roc_curve.png")
        print(f"   - Precision-Recall curves: *_pr_curve.png")
        print(f"   - Calibration curves: *_calibration.png")
        print(f"   - Model comparison: model_comparison.csv")
        print(f"   - Comparison chart: model_comparison_chart.png")

    else:
        print("\n❌ No models successfully evaluated")


if __name__ == '__main__':
    try:
        evaluate_saved_models()
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
