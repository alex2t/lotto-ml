#!/usr/bin/env python3
"""
test_model_metrics.py
=====================
Standalone script to evaluate existing trained models with comprehensive metrics.

Usage:
    python test_model_metrics.py

Prerequisites:
    1. Run 'python drawpick.py' to generate data files
    2. Run 'python quickpick.py' to train models
    3. Then run this script

This will:
1. Load your existing models (if available)
2. Load training/validation datasets (if saved)
3. Evaluate them with AUC-ROC and other metrics
4. Generate comparison charts
5. Save results to model_metrics/
"""

import sys
import os
import pickle
import pandas as pd
import numpy as np
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from ml_lotto.models.model_metrics import (
    calculate_comprehensive_metrics,
    compare_models,
    plot_model_comparison
)


def load_saved_datasets():
    """
    Try to load pre-saved training/validation datasets.
    Returns dict of datasets or None if not found.
    """
    dataset_files = {
        'train_standard': 'train_df_standard.pkl',
        'val_standard': 'val_df_standard.pkl',
        'train_model2': 'train_df_model2.pkl',
        'val_model2': 'val_df_model2.pkl'
    }

    datasets = {}
    all_found = True

    for key, filename in dataset_files.items():
        if os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    datasets[key] = pickle.load(f)
            except Exception as e:
                print(f"⚠️  Could not load {filename}: {e}")
                all_found = False
        else:
            all_found = False

    if all_found:
        return datasets
    else:
        return None


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
        print("\nTo use this script, you need to:")
        print("  1. Run 'python drawpick.py' to generate data files")
        print("  2. Run 'python quickpick.py' to train models")
        print("  3. Modify quickpick.py to save datasets (see instructions below)")
        print("\nOr integrate metrics directly into trainer.py (see EXAMPLE_trainer_with_metrics.py)\n")
        return

    print(f"\n✓ Found {len(available_models)} trained models")

    # Try to load pre-saved datasets
    print("\n📊 Looking for saved datasets...")
    datasets = load_saved_datasets()

    if datasets is None:
        print("\n❌ Saved datasets not found!")
        print("\nThis script requires training/validation datasets to be saved.")
        print("\nTo save datasets, add this code at the end of quickpick.py (after training):")
        print("\n" + "="*70)
        print("# Save datasets for metrics evaluation")
        print("import pickle")
        print("with open('train_df_standard.pkl', 'wb') as f:")
        print("    pickle.dump(train_df_standard, f)")
        print("with open('val_df_standard.pkl', 'wb') as f:")
        print("    pickle.dump(val_df_standard, f)")
        print("with open('train_df_model2.pkl', 'wb') as f:")
        print("    pickle.dump(train_df_model2, f)")
        print("with open('val_df_model2.pkl', 'wb') as f:")
        print("    pickle.dump(val_df_model2, f)")
        print("print('✓ Datasets saved for metrics evaluation')")
        print("="*70)
        print("\nAlternatively, integrate metrics directly into trainer.py")
        print("(See EXAMPLE_trainer_with_metrics.py for details)\n")
        return

    print("✓ Loaded pre-saved datasets")

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
        selected_features = None
        try:
            with open(config['features_file'], 'rb') as f:
                selected_features = pickle.load(f)
        except Exception as e:
            print(f"⚠️  Could not load features from {config['features_file']}: {e}")

        # Select appropriate dataset
        if config['dataset'] == 'model2':
            train_df = datasets['train_model2']
            val_df = datasets['val_model2']
        else:
            train_df = datasets['train_standard']
            val_df = datasets['val_standard']

        # Get features
        if selected_features is None:
            # Try to infer from dataset columns (exclude 'hit' label)
            selected_features = [col for col in train_df.columns if col != 'hit']
            print(f"⚠️  Using all available features from dataset: {len(selected_features)}")
        else:
            # Filter features that exist in dataset
            available_features = [f for f in selected_features if f in train_df.columns]
            if len(available_features) < len(selected_features):
                print(f"⚠️  {len(selected_features) - len(available_features)} features not in dataset")
            selected_features = available_features

        if len(selected_features) == 0:
            print(f"❌ No valid features found for {config['name']}")
            continue

        print(f"Using {len(selected_features)} features")

        # Prepare data
        X_train = train_df[selected_features].values
        y_train = train_df['hit'].values
        X_val = val_df[selected_features].values
        y_val = val_df['hit'].values

        # Calculate comprehensive metrics
        try:
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
        except Exception as e:
            print(f"❌ Error evaluating {config['name']}: {e}")
            import traceback
            traceback.print_exc()

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
