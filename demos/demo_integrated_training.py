"""
test_integrated_training.py
============================
Test script to verify that all ML features are properly integrated into the trainer.

Tests:
1. Train model with default settings (no tuning)
2. Train model with hyperparameter tuning enabled
3. Verify all features work together (SMOTE + Feature Selection + Tuning)
"""

import numpy as np
import pandas as pd
import sys
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from ml_lotto.models.trainer import train_model


def create_synthetic_lottery_data(n_draws=200, n_numbers=47):
    """Create synthetic lottery data for testing."""
    np.random.seed(42)

    # Create features for each number
    all_feature_names = [
        'total_count', 'days_since_last', 'gap_consistency',
        'rolling_rate_10', 'rolling_rate_20', 'rolling_trend_10'
    ]

    features_dict = {}
    for num in range(1, n_numbers + 1):
        features_dict[num] = {
            'total_count': np.random.randint(20, 100),
            'days_since_last': np.random.randint(1, 50),
            'gap_consistency': np.random.rand(),
            'rolling_rate_10': np.random.rand() * 0.2,
            'rolling_rate_20': np.random.rand() * 0.15,
            'rolling_trend_10': np.random.rand() * 0.1 - 0.05
        }

    # Create draws
    all_draws = []
    for draw_idx in range(100, 100 + n_draws):
        # 7 random winning numbers (imbalanced - only 14.9% of numbers win)
        winning_numbers = np.random.choice(range(1, n_numbers + 1), size=7, replace=False).tolist()
        all_draws.append({
            'draw_index': draw_idx,
            'numbers': winning_numbers,
            'bonus_number': winning_numbers[-1]
        })

    # Build dataset
    records = []
    for draw in all_draws:
        for num in range(1, n_numbers + 1):
            record = {'number': num}
            record.update(features_dict[num])
            record['hit'] = 1 if num in draw['numbers'] else 0
            records.append(record)

    df = pd.DataFrame(records)
    return df, all_feature_names


def test_default_training():
    """Test training with default settings (no tuning)."""
    print("\n" + "="*80)
    print("TEST 1: Default Training (No Tuning)")
    print("="*80)

    # Create synthetic data
    df, all_feature_names = create_synthetic_lottery_data(n_draws=200)

    # Split into train/val
    train_size = int(len(df) * 0.8)
    train_df = df.iloc[:train_size]
    val_df = df.iloc[train_size:]

    print(f"\nData:")
    print(f"  Train samples: {len(train_df)}")
    print(f"  Val samples: {len(val_df)}")
    print(f"  Features: {len(all_feature_names)}")

    # Model config - specify explicit features instead of 'all'
    model_config = {
        'name': 'Test_RF_Default',
        'description': 'Test Random Forest without tuning',
        'algorithm': 'random_forest',
        'features': all_feature_names  # Use explicit feature list
    }

    # Train with SMOTE and feature selection (no tuning)
    pipeline, features, importance, metrics, tuning_results = train_model(
        model_config=model_config,
        train_df=train_df,
        all_feature_names=all_feature_names,
        model_index=1,
        exclude_bonus=False,
        val_df=val_df,
        use_smote=True,
        smote_sampling_strategy=0.3,
        enable_feature_selection=True,
        enable_hyperparameter_tuning=False  # No tuning
    )

    # Verify results
    assert pipeline is not None, "Pipeline should be trained"
    assert len(features) > 0, "Should have selected features"
    assert metrics is not None, "Should have metrics"
    assert tuning_results is None, "Should not have tuning results when disabled"

    print(f"\nPASS: Default training works")
    print(f"   Features selected: {len(features)}")
    print(f"   Val F1-Score: {metrics.get('f1_score_optimal', 0):.4f}")

    return True


def test_training_with_tuning():
    """Test training with hyperparameter tuning enabled."""
    print("\n" + "="*80)
    print("TEST 2: Training with Hyperparameter Tuning")
    print("="*80)

    # Create synthetic data
    df, all_feature_names = create_synthetic_lottery_data(n_draws=200)

    # Split into train/val
    train_size = int(len(df) * 0.8)
    train_df = df.iloc[:train_size]
    val_df = df.iloc[train_size:]

    print(f"\nData:")
    print(f"  Train samples: {len(train_df)}")
    print(f"  Val samples: {len(val_df)}")

    # Model config - specify explicit features
    model_config = {
        'name': 'Test_Logistic_Tuned',
        'description': 'Test Logistic Regression with tuning',
        'algorithm': 'logistic',
        'features': all_feature_names  # Use explicit feature list
    }

    # Train with ALL features enabled including hyperparameter tuning
    pipeline, features, importance, metrics, tuning_results = train_model(
        model_config=model_config,
        train_df=train_df,
        all_feature_names=all_feature_names,
        model_index=1,
        exclude_bonus=False,
        val_df=val_df,
        use_smote=True,
        smote_sampling_strategy=0.3,
        enable_feature_selection=True,
        enable_hyperparameter_tuning=True,  # Enable tuning
        tuning_mode='quick',
        tuning_cv_splits=2,  # Fewer splits for faster testing
        tuning_scoring='f1'
    )

    # Verify results
    assert pipeline is not None, "Pipeline should be trained"
    assert len(features) > 0, "Should have selected features"
    assert metrics is not None, "Should have metrics"
    assert tuning_results is not None, "Should have tuning results when enabled"
    assert 'best_params' in tuning_results, "Should have best params"
    assert 'best_score' in tuning_results, "Should have best score"

    print(f"\nPASS: Training with tuning works")
    print(f"   Features selected: {len(features)}")
    print(f"   Val F1-Score: {metrics.get('f1_score_optimal', 0):.4f}")
    print(f"   Tuning best score: {tuning_results['best_score']:.4f}")
    print(f"   Best params: {tuning_results['best_params']}")

    return True


def test_all_features_together():
    """Test that all features work together without conflicts."""
    print("\n" + "="*80)
    print("TEST 3: All Features Together")
    print("="*80)

    # Create synthetic data
    df, all_feature_names = create_synthetic_lottery_data(n_draws=150)

    # Split into train/val
    train_size = int(len(df) * 0.8)
    train_df = df.iloc[:train_size]
    val_df = df.iloc[train_size:]

    print(f"\nEnabled:")
    print(f"  SMOTE")
    print(f"  Feature Selection")
    print(f"  Hyperparameter Tuning")
    print(f"  Enhanced Metrics")

    # Model config - specify explicit features
    model_config = {
        'name': 'Test_RF_AllFeatures',
        'description': 'Test with all features enabled',
        'algorithm': 'random_forest',
        'features': all_feature_names  # Use explicit feature list
    }

    # Train with EVERYTHING enabled
    pipeline, features, importance, metrics, tuning_results = train_model(
        model_config=model_config,
        train_df=train_df,
        all_feature_names=all_feature_names,
        model_index=1,
        exclude_bonus=False,
        val_df=val_df,
        use_smote=True,
        smote_sampling_strategy=0.3,
        enable_feature_selection=True,
        correlation_threshold=0.95,
        importance_threshold=0.01,
        enable_hyperparameter_tuning=True,
        tuning_mode='quick',
        tuning_cv_splits=2,
        tuning_scoring='f1'
    )

    # Verify all features were applied
    assert pipeline is not None, "Pipeline should be trained"
    assert tuning_results is not None, "Tuning should be applied"
    assert len(features) <= len(all_feature_names), "Feature selection should reduce features"
    assert 'top7_accuracy' in metrics, "Enhanced metrics should be calculated"
    assert 'pr_auc' in metrics, "PR-AUC should be calculated"

    print(f"\nPASS: All features work together")
    print(f"   Original features: {len(all_feature_names)}")
    print(f"   Selected features: {len(features)} (reduced by {len(all_feature_names) - len(features)})")
    print(f"   Val F1-Score: {metrics.get('f1_score_optimal', 0):.4f}")
    print(f"   Top-7 Accuracy: {metrics.get('top7_accuracy', 0)*100:.1f}%")
    print(f"   PR-AUC: {metrics.get('pr_auc', 0):.4f}")
    print(f"   Tuning improved by: {tuning_results['best_score']:.4f}")

    return True


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("  INTEGRATED TRAINING TEST SUITE")
    print("="*80)

    tests = [
        ("Default Training (No Tuning)", test_default_training),
        ("Training with Hyperparameter Tuning", test_training_with_tuning),
        ("All Features Together", test_all_features_together)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\nEXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\nALL TESTS PASSED - Integrated training pipeline ready!")
        return 0
    else:
        print(f"\n{total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
