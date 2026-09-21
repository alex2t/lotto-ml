"""
test_hyperparameter_tuning.py
==============================
Test script for hyperparameter tuning module.

Tests:
1. Quick tuning with Logistic Regression
2. Quick tuning with Random Forest
3. Parameter grid generation
4. Time-series cross-validation
5. Results saving and loading
"""

import numpy as np
import sys
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

from ml_lotto.models.hyperparameter_tuning import (
    get_logistic_regression_grid,
    get_random_forest_grid,
    get_xgboost_grid,
    quick_tune,
    extensive_tune,
    tune_hyperparameters,
    save_tuning_results,
    extract_best_params,
    get_param_importance,
    _get_grid_size
)


def test_parameter_grids():
    """Test parameter grid generation."""
    print("\n" + "="*80)
    print("TEST 1: Parameter Grid Generation")
    print("="*80)

    # Test quick grids
    print("\n--- Quick Grids ---")
    lr_quick = get_logistic_regression_grid(quick=True)
    rf_quick = get_random_forest_grid(quick=True)

    print(f"Logistic Regression (quick): {_get_grid_size(lr_quick)} combinations")
    print(f"Random Forest (quick): {_get_grid_size(rf_quick)} combinations")

    # Test extensive grids
    print("\n--- Extensive Grids ---")
    lr_full = get_logistic_regression_grid(quick=False)
    rf_full = get_random_forest_grid(quick=False)

    print(f"Logistic Regression (full): {_get_grid_size(lr_full)} combinations")
    print(f"Random Forest (full): {_get_grid_size(rf_full)} combinations")

    # Verify grids have required parameters (with estimator__ for CalibratedClassifierCV)
    assert 'classifier__estimator__C' in lr_quick, "Missing C in LR grid"
    assert 'classifier__estimator__n_estimators' in rf_quick, "Missing n_estimators in RF grid"

    print(f"\nPASS: Parameter grids generated correctly")
    return True


def test_quick_tuning_logistic():
    """Test quick tuning with Logistic Regression."""
    print("\n" + "="*80)
    print("TEST 2: Quick Tuning - Logistic Regression")
    print("="*80)

    # Create synthetic lottery-like data
    np.random.seed(42)
    n_samples = 300
    n_features = 10

    X_train = np.random.randn(n_samples, n_features)
    # Imbalanced (15% positive class like lottery)
    y_train = np.random.choice([0, 1], size=n_samples, p=[0.85, 0.15])

    print(f"\nTraining data:")
    print(f"  Samples: {n_samples}")
    print(f"  Features: {n_features}")
    print(f"  Positive class: {sum(y_train)} ({sum(y_train)/len(y_train)*100:.1f}%)")

    # Create pipeline (matching production structure with CalibratedClassifierCV)
    base_clf = LogisticRegression(random_state=42, max_iter=1000)
    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method='isotonic', cv=3)
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', calibrated_clf)
    ])

    # Quick tune
    best_pipeline, tuning_results = quick_tune(
        pipeline=pipeline,
        X_train=X_train,
        y_train=y_train,
        model_type='logistic',
        model_name='TestLogistic',
        cv_splits=3,
        scoring='f1',
        n_jobs=1  # Use 1 for testing to avoid warnings
    )

    # Verify results
    assert 'best_params' in tuning_results, "Missing best_params in results"
    assert 'best_score' in tuning_results, "Missing best_score in results"
    assert tuning_results['best_score'] >= 0, "Best score should be non-negative"

    print(f"\nPASS: Quick tuning completed successfully")
    print(f"   Best Score: {tuning_results['best_score']:.4f}")
    print(f"   Total Fits: {tuning_results['total_fits']}")
    print(f"   Time: {tuning_results['elapsed_time']:.1f}s")

    return True


def test_quick_tuning_random_forest():
    """Test quick tuning with Random Forest."""
    print("\n" + "="*80)
    print("TEST 3: Quick Tuning - Random Forest")
    print("="*80)

    # Create synthetic data
    np.random.seed(42)
    n_samples = 300
    n_features = 10

    X_train = np.random.randn(n_samples, n_features)
    y_train = np.random.choice([0, 1], size=n_samples, p=[0.85, 0.15])

    print(f"\nTraining data:")
    print(f"  Samples: {n_samples}")
    print(f"  Features: {n_features}")
    print(f"  Positive class: {sum(y_train)} ({sum(y_train)/len(y_train)*100:.1f}%)")

    # Create pipeline (matching production structure with CalibratedClassifierCV)
    base_clf = RandomForestClassifier(random_state=42, n_jobs=1)
    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method='isotonic', cv=3)
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', calibrated_clf)
    ])

    # Quick tune
    best_pipeline, tuning_results = quick_tune(
        pipeline=pipeline,
        X_train=X_train,
        y_train=y_train,
        model_type='random_forest',
        model_name='TestRandomForest',
        cv_splits=3,
        scoring='f1',
        n_jobs=1
    )

    # Verify results
    assert 'best_params' in tuning_results, "Missing best_params in results"
    assert tuning_results['best_score'] >= 0, "Best score should be non-negative"

    # Verify RF-specific parameters
    best_params = tuning_results['best_params']
    assert any('n_estimators' in k for k in best_params.keys()), "Missing n_estimators in best params"

    print(f"\nPASS: Random Forest tuning completed successfully")
    print(f"   Best Score: {tuning_results['best_score']:.4f}")
    print(f"   Total Fits: {tuning_results['total_fits']}")

    return True


def test_time_series_cv():
    """Test that TimeSeriesSplit is used correctly."""
    print("\n" + "="*80)
    print("TEST 4: Time-Series Cross-Validation")
    print("="*80)

    # Create time-ordered data
    np.random.seed(42)
    n_samples = 200
    n_features = 5

    X_train = np.random.randn(n_samples, n_features)
    y_train = np.random.choice([0, 1], size=n_samples, p=[0.85, 0.15])

    # Create pipeline (matching production structure with CalibratedClassifierCV)
    base_clf = LogisticRegression(random_state=42, max_iter=1000)
    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method='isotonic', cv=3)
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', calibrated_clf)
    ])

    # Small parameter grid for testing
    param_grid = {
        'classifier__estimator__C': [0.1, 1.0],
        'classifier__estimator__class_weight': ['balanced', None]
    }

    # Tune with TimeSeriesSplit
    best_pipeline, tuning_results = tune_hyperparameters(
        pipeline=pipeline,
        X_train=X_train,
        y_train=y_train,
        param_grid=param_grid,
        model_name='TestTimeSeriesCV',
        search_type='grid',
        cv_splits=3,
        scoring='f1',
        n_jobs=1,
        verbose=0
    )

    # Verify CV splits
    assert tuning_results['cv_splits'] == 3, "Should use 3 CV splits"
    assert tuning_results['total_fits'] == 4, "Should have 4 unique parameter combinations"

    print(f"\nPASS: TimeSeriesSplit CV working correctly")
    print(f"   CV Splits: {tuning_results['cv_splits']}")
    print(f"   Total Fits: {tuning_results['total_fits']}")

    return True


def test_results_saving():
    """Test saving and parameter extraction."""
    print("\n" + "="*80)
    print("TEST 5: Results Saving and Extraction")
    print("="*80)

    # Create minimal tuning results
    np.random.seed(42)
    X_train = np.random.randn(100, 5)
    y_train = np.random.choice([0, 1], size=100, p=[0.85, 0.15])

    # Create pipeline (matching production structure with CalibratedClassifierCV)
    base_clf = LogisticRegression(random_state=42, max_iter=1000)
    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method='isotonic', cv=3)
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', calibrated_clf)
    ])

    param_grid = {'classifier__estimator__C': [0.1, 1.0]}

    best_pipeline, tuning_results = tune_hyperparameters(
        pipeline=pipeline,
        X_train=X_train,
        y_train=y_train,
        param_grid=param_grid,
        model_name='TestSaving',
        search_type='grid',
        cv_splits=2,
        scoring='f1',
        n_jobs=1,
        verbose=0
    )

    # Test parameter extraction
    best_params = extract_best_params(tuning_results)
    assert isinstance(best_params, dict), "Best params should be a dict"
    assert len(best_params) > 0, "Should have at least one parameter"

    print(f"\n  Extracted best params: {best_params}")

    # Test saving (use temp directory)
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        save_tuning_results(tuning_results, 'TestModel', output_dir=tmpdir)

        # Verify file was created
        saved_file = f"{tmpdir}/TestModel_tuning_results.json"
        assert os.path.exists(saved_file), f"File not created: {saved_file}"

        # Load and verify
        import json
        with open(saved_file, 'r') as f:
            loaded_results = json.load(f)

        assert 'best_params' in loaded_results, "Missing best_params in saved file"
        assert 'best_score' in loaded_results, "Missing best_score in saved file"

        print(f"\n  Results saved and loaded correctly")

    print(f"\nPASS: Results saving and extraction working")

    return True


def test_parameter_importance():
    """Test parameter importance analysis."""
    print("\n" + "="*80)
    print("TEST 6: Parameter Importance Analysis")
    print("="*80)

    # Create data
    np.random.seed(42)
    X_train = np.random.randn(200, 8)
    y_train = np.random.choice([0, 1], size=200, p=[0.85, 0.15])

    # Create pipeline (matching production structure with CalibratedClassifierCV)
    base_clf = RandomForestClassifier(random_state=42, n_jobs=1)
    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method='isotonic', cv=3)
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', calibrated_clf)
    ])

    # Use quick RF grid
    param_grid = get_random_forest_grid(quick=True)

    best_pipeline, tuning_results = tune_hyperparameters(
        pipeline=pipeline,
        X_train=X_train,
        y_train=y_train,
        param_grid=param_grid,
        model_name='TestImportance',
        search_type='grid',
        cv_splits=2,
        scoring='f1',
        n_jobs=1,
        verbose=0
    )

    # Analyze parameter importance
    importance_df = get_param_importance(tuning_results, top_n=3)

    assert len(importance_df) > 0, "Should return importance results"
    assert 'Parameter' in importance_df.columns, "Missing Parameter column"
    assert 'Score Range' in importance_df.columns, "Missing Score Range column"

    print(f"\nPASS: Parameter importance analysis working")

    return True


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("  HYPERPARAMETER TUNING TEST SUITE")
    print("="*80)

    tests = [
        ("Parameter Grid Generation", test_parameter_grids),
        ("Quick Tuning - Logistic Regression", test_quick_tuning_logistic),
        ("Quick Tuning - Random Forest", test_quick_tuning_random_forest),
        ("Time-Series Cross-Validation", test_time_series_cv),
        ("Results Saving and Extraction", test_results_saving),
        ("Parameter Importance Analysis", test_parameter_importance)
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
        print("\nALL TESTS PASSED - Hyperparameter tuning ready for use!")
        return 0
    else:
        print(f"\n{total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
