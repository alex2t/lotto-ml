"""
hyperparameter_tuning.py
=========================
Hyperparameter tuning utilities for lottery prediction models.

Uses time-series aware cross-validation to respect temporal ordering of draws.
Supports GridSearchCV and RandomizedSearchCV for different model types.

Features:
- Pre-defined parameter grids for common models
- TimeSeriesSplit for temporal validation
- Class imbalance handling (scale_pos_weight)
- Results analysis and visualization
- Best parameter extraction and storage
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, TimeSeriesSplit
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import make_scorer, f1_score
import time
import json


# ============================================================================
# PARAMETER GRIDS FOR DIFFERENT MODEL TYPES
# ============================================================================

def get_logistic_regression_grid(quick: bool = False) -> Dict[str, List]:
    """
    Get parameter grid for Logistic Regression.

    Args:
        quick: If True, use smaller grid for faster search

    Returns:
        Parameter grid dictionary
    """
    if quick:
        return {
            'classifier__estimator__C': [0.1, 1.0, 10.0],
            'classifier__estimator__class_weight': ['balanced', None],
            'classifier__estimator__max_iter': [1000]
        }
    else:
        return {
            'classifier__estimator__C': [0.01, 0.1, 1.0, 10.0, 100.0],
            'classifier__estimator__penalty': ['l2'],
            'classifier__estimator__class_weight': ['balanced', None],
            'classifier__estimator__solver': ['lbfgs', 'liblinear'],
            'classifier__estimator__max_iter': [1000, 2000]
        }


def get_random_forest_grid(quick: bool = False) -> Dict[str, List]:
    """
    Get parameter grid for Random Forest.

    Args:
        quick: If True, use smaller grid for faster search

    Returns:
        Parameter grid dictionary
    """
    # Every candidate is capacity-constrained. CV scores here sit at chance (~0.51),
    # so the search cannot tell the candidates apart and its pick is effectively
    # arbitrary - an unconstrained candidate in the grid means an unconstrained model
    # gets picked, which is how the 0.383 train/val gap survived (C-15b). Leaves in
    # the hundreds are ~2-4% of the 15,800 training rows.
    if quick:
        return {
            'classifier__estimator__n_estimators': [100],
            'classifier__estimator__max_depth': [4, 6],
            'classifier__estimator__min_samples_leaf': [200, 300, 500],
            'classifier__estimator__max_features': [0.5, 'sqrt'],
            'classifier__estimator__class_weight': ['balanced_subsample']
        }
    else:
        return {
            'classifier__estimator__n_estimators': [100, 200, 300],
            'classifier__estimator__max_depth': [3, 4, 5, 6],
            'classifier__estimator__min_samples_leaf': [100, 200, 300, 500],
            'classifier__estimator__max_features': [0.3, 0.5, 'sqrt'],
            'classifier__estimator__class_weight': ['balanced', 'balanced_subsample']
        }


def get_xgboost_grid(quick: bool = False) -> Dict[str, List]:
    """
    Get parameter grid for XGBoost.

    Args:
        quick: If True, use smaller grid for faster search

    Returns:
        Parameter grid dictionary
    """
    # Constrained for the same reason as the random-forest grid: the CV scores here
    # sit at chance (~0.511), so the search picks arbitrarily among its candidates and
    # an unconstrained one wins as often as not. `scale_pos_weight` stays at 1 because
    # that is the operating point the gap was measured at; isotonic calibration handles
    # the class ratio downstream.
    if quick:
        return {
            'classifier__estimator__n_estimators': [50, 100],
            'classifier__estimator__max_depth': [2, 3],
            'classifier__estimator__learning_rate': [0.03, 0.05],
            'classifier__estimator__min_child_weight': [200, 500],
            'classifier__estimator__reg_lambda': [20],
            'classifier__estimator__scale_pos_weight': [1]
        }
    else:
        return {
            'classifier__estimator__n_estimators': [50, 100, 200],
            'classifier__estimator__max_depth': [2, 3, 4],
            'classifier__estimator__learning_rate': [0.01, 0.03, 0.05],
            'classifier__estimator__min_child_weight': [100, 200, 500],
            'classifier__estimator__reg_lambda': [10, 20, 50],
            'classifier__estimator__subsample': [0.6, 0.8],
            'classifier__estimator__colsample_bytree': [0.6, 0.8],
            'classifier__estimator__scale_pos_weight': [1]
        }


def get_catboost_grid(quick: bool = False) -> Dict[str, List]:
    """
    Get parameter grid for CatBoost.

    Args:
        quick: If True, use smaller grid for faster search

    Returns:
        Parameter grid dictionary
    """
    if quick:
        return {
            'classifier__estimator__iterations': [50, 100],
            'classifier__estimator__depth': [4, 6],
            'classifier__estimator__learning_rate': [0.01, 0.1],
            'classifier__estimator__scale_pos_weight': [1, 3, 5]
        }
    else:
        return {
            'classifier__estimator__iterations': [50, 100, 200, 300],
            'classifier__estimator__depth': [4, 6, 8, 10],
            'classifier__estimator__learning_rate': [0.01, 0.05, 0.1, 0.2],
            'classifier__estimator__l2_leaf_reg': [1, 3, 5, 7],
            'classifier__estimator__scale_pos_weight': [1, 2, 3, 5, 7]
        }


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def get_scoring_metric(scoring: str):
    """
    Get appropriate scoring metric, handling edge cases for imbalanced data.

    For F1 score, uses zero_division=0 to handle cases where precision/recall
    are undefined (e.g., when model predicts all negatives).

    Args:
        scoring: Scoring metric name

    Returns:
        Scorer object or string
    """
    if scoring == 'f1':
        # Use zero_division=0 to return 0 instead of raising warning/error
        # when there are no positive predictions
        return make_scorer(f1_score, zero_division=0)
    else:
        # For other metrics (roc_auc, precision, recall, etc.), use string
        return scoring


# ============================================================================
# HYPERPARAMETER TUNING FUNCTIONS
# ============================================================================

def tune_hyperparameters(
    pipeline: Pipeline,
    X_train: np.ndarray,
    y_train: np.ndarray,
    param_grid: Dict[str, List],
    model_name: str,
    search_type: str = 'grid',
    cv_splits: int = 5,
    scoring: str = 'f1',
    n_jobs: int = -1,
    verbose: int = 1,
    n_iter: int = 50
) -> Tuple[Pipeline, Dict[str, Any]]:
    """
    Perform hyperparameter tuning with time-series aware cross-validation.

    Args:
        pipeline: Sklearn pipeline with scaler and classifier
        X_train: Training features
        y_train: Training labels
        param_grid: Parameter grid for search
        model_name: Name of the model (for display)
        search_type: 'grid' for GridSearchCV, 'random' for RandomizedSearchCV
        cv_splits: Number of CV splits for TimeSeriesSplit
        scoring: Scoring metric ('f1', 'roc_auc', 'precision', 'recall')
        n_jobs: Number of parallel jobs (-1 for all CPUs)
        verbose: Verbosity level
        n_iter: Number of iterations for RandomizedSearchCV

    Returns:
        Tuple of (best_pipeline, tuning_results)
    """
    print(f"\n{'='*80}")
    print(f"  HYPERPARAMETER TUNING: {model_name}")
    print(f"{'='*80}")
    print(f"  Search Type: {search_type.upper()}")
    print(f"  CV Strategy: TimeSeriesSplit (n_splits={cv_splits})")
    print(f"  Scoring Metric: {scoring}")
    print(f"  Parameter Grid Size: {_get_grid_size(param_grid)} combinations")

    # Get appropriate scoring metric (handles imbalanced data edge cases)
    scorer = get_scoring_metric(scoring)

    # Use TimeSeriesSplit for time-series aware CV
    tscv = TimeSeriesSplit(n_splits=cv_splits)

    # Choose search strategy
    start_time = time.time()

    if search_type == 'grid':
        search = GridSearchCV(
            estimator=pipeline,
            param_grid=param_grid,
            cv=tscv,
            scoring=scorer,
            n_jobs=n_jobs,
            verbose=verbose,
            return_train_score=True
        )
    elif search_type == 'random':
        search = RandomizedSearchCV(
            estimator=pipeline,
            param_distributions=param_grid,
            n_iter=n_iter,
            cv=tscv,
            scoring=scorer,
            n_jobs=n_jobs,
            verbose=verbose,
            return_train_score=True,
            random_state=42
        )
    else:
        raise ValueError(f"Unknown search_type: {search_type}. Use 'grid' or 'random'")

    # Fit the search
    print(f"\n  Starting hyperparameter search...")
    search.fit(X_train, y_train)

    elapsed_time = time.time() - start_time

    # Extract results
    best_pipeline = search.best_estimator_
    best_params = search.best_params_
    best_score = search.best_score_

    print(f"\n  Tuning Complete! (elapsed: {elapsed_time:.1f}s)")
    print(f"\n  Best Parameters:")
    for param, value in best_params.items():
        print(f"     {param}: {value}")

    print(f"\n  Best CV Score ({scoring}): {best_score:.4f}")

    # Analyze results
    results_df = pd.DataFrame(search.cv_results_)

    # Check if all scores are zero or very low
    if best_score < 0.001:
        print(f"\n  WARNING: Best score is {best_score:.6f} - Model may be predicting all negatives!")
        print(f"     This is common with highly imbalanced data (lottery predictions).")
        print(f"")
        print(f"     RECOMMENDATIONS:")
        print(f"     1. Use 'roc_auc' scoring: Better for imbalanced data, doesn't require positive predictions")
        print(f"        Example: tuning_scoring='roc_auc'")
        print(f"     2. Use 'average_precision' scoring: Works well with rare positive class")
        print(f"        Example: tuning_scoring='average_precision'")
        print(f"     3. Verify class weights: Ensure 'balanced' or custom weights are set")
        print(f"     4. Check positive class ratio: If <1%, consider adjusting scale_pos_weight")
        print(f"")

        # Show train scores to check for fitting issues
        if 'mean_train_score' in results_df.columns:
            best_train = results_df.loc[search.best_index_, 'mean_train_score']
            print(f"     Training score: {best_train:.4f}")
            if best_train < 0.001:
                print(f"        Training score also ~0 - Model isn't learning from data!")
                print(f"        Check: feature quality, target distribution, model capacity")
            else:
                print(f"        Model is learning (train > 0), but not generalizing to validation")
                print(f"        This suggests severe overfitting or data distribution issues")

    # Get top 5 configurations by actual score (not rank)
    # Sort by mean_test_score descending, then by std ascending (prefer stable models)
    top_configs = results_df.sort_values(
        by=['mean_test_score', 'std_test_score'],
        ascending=[False, True]
    ).head(5)[
        ['rank_test_score', 'mean_test_score', 'std_test_score', 'params']
    ]

    print(f"\n  Top 5 Configurations:")
    print(f"     {'Rank':<6} {'Mean Score':<12} {'Std':<10} {'Parameters'}")
    print(f"     {'-'*70}")
    for _, row in top_configs.iterrows():
        rank = int(row['rank_test_score'])
        mean = row['mean_test_score']
        std = row['std_test_score']
        params_str = str(row['params'])[:40] + "..." if len(str(row['params'])) > 40 else str(row['params'])
        print(f"     {rank:<6} {mean:<12.4f} {std:<10.4f} {params_str}")

    # If all scores are the same, show score distribution
    unique_scores = results_df['mean_test_score'].nunique()
    if unique_scores <= 3:
        print(f"\n  ℹ Only {unique_scores} unique score(s) found across {len(results_df)} configurations")
        score_dist = results_df['mean_test_score'].value_counts().head(5)
        print(f"     Score distribution:")
        for score, count in score_dist.items():
            print(f"       {score:.6f}: {count} configurations")

    # Package results
    tuning_results = {
        'best_params': best_params,
        'best_score': best_score,
        'best_index': search.best_index_,
        'cv_results': search.cv_results_,
        'search_type': search_type,
        'scoring': scoring,
        'cv_splits': cv_splits,
        'elapsed_time': elapsed_time,
        'total_fits': len(results_df)
    }

    print(f"{'='*80}\n")

    return best_pipeline, tuning_results


def quick_tune(
    pipeline: Pipeline,
    X_train: np.ndarray,
    y_train: np.ndarray,
    model_type: str,
    model_name: str = "Model",
    cv_splits: int = 3,
    scoring: str = 'f1',
    n_jobs: int = -1
) -> Tuple[Pipeline, Dict[str, Any]]:
    """
    Quick hyperparameter tuning with pre-defined grids.

    This is a convenience function for common model types.

    Args:
        pipeline: Sklearn pipeline with scaler and classifier
        X_train: Training features
        y_train: Training labels
        model_type: Type of model ('logistic', 'random_forest', 'xgboost', 'catboost')
        model_name: Name of the model (for display)
        cv_splits: Number of CV splits (default: 3 for quick tuning)
        scoring: Scoring metric
        n_jobs: Number of parallel jobs

    Returns:
        Tuple of (best_pipeline, tuning_results)
    """
    # Get parameter grid based on model type
    model_type = model_type.lower()

    if 'logistic' in model_type:
        param_grid = get_logistic_regression_grid(quick=True)
    elif 'random_forest' in model_type or 'rf' in model_type:
        param_grid = get_random_forest_grid(quick=True)
    elif 'xgb' in model_type or 'xgboost' in model_type:
        param_grid = get_xgboost_grid(quick=True)
    elif 'catboost' in model_type or 'cat' in model_type:
        param_grid = get_catboost_grid(quick=True)
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    return tune_hyperparameters(
        pipeline=pipeline,
        X_train=X_train,
        y_train=y_train,
        param_grid=param_grid,
        model_name=model_name,
        search_type='grid',
        cv_splits=cv_splits,
        scoring=scoring,
        n_jobs=n_jobs,
        verbose=0
    )


def extensive_tune(
    pipeline: Pipeline,
    X_train: np.ndarray,
    y_train: np.ndarray,
    model_type: str,
    model_name: str = "Model",
    cv_splits: int = 5,
    scoring: str = 'f1',
    n_jobs: int = -1,
    use_random: bool = False,
    n_iter: int = 100
) -> Tuple[Pipeline, Dict[str, Any]]:
    """
    Extensive hyperparameter tuning with larger parameter grids.

    Args:
        pipeline: Sklearn pipeline with scaler and classifier
        X_train: Training features
        y_train: Training labels
        model_type: Type of model ('logistic', 'random_forest', 'xgboost', 'catboost')
        model_name: Name of the model (for display)
        cv_splits: Number of CV splits (default: 5)
        scoring: Scoring metric
        n_jobs: Number of parallel jobs
        use_random: If True, use RandomizedSearchCV instead of GridSearchCV
        n_iter: Number of iterations for RandomizedSearchCV

    Returns:
        Tuple of (best_pipeline, tuning_results)
    """
    # Get parameter grid based on model type
    model_type = model_type.lower()

    if 'logistic' in model_type:
        param_grid = get_logistic_regression_grid(quick=False)
    elif 'random_forest' in model_type or 'rf' in model_type:
        param_grid = get_random_forest_grid(quick=False)
    elif 'xgb' in model_type or 'xgboost' in model_type:
        param_grid = get_xgboost_grid(quick=False)
    elif 'catboost' in model_type or 'cat' in model_type:
        param_grid = get_catboost_grid(quick=False)
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    search_type = 'random' if use_random else 'grid'

    return tune_hyperparameters(
        pipeline=pipeline,
        X_train=X_train,
        y_train=y_train,
        param_grid=param_grid,
        model_name=model_name,
        search_type=search_type,
        cv_splits=cv_splits,
        scoring=scoring,
        n_jobs=n_jobs,
        verbose=1,
        n_iter=n_iter
    )


def save_tuning_results(
    tuning_results: Dict[str, Any],
    model_name: str,
    output_dir: str = "model_metrics"
) -> None:
    """
    Save tuning results to JSON file.

    Args:
        tuning_results: Results dictionary from tune_hyperparameters
        model_name: Name of the model
        output_dir: Directory to save results
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    # Prepare results for JSON serialization
    json_results = {
        'model_name': model_name,
        'best_params': tuning_results['best_params'],
        'best_score': float(tuning_results['best_score']),
        'search_type': tuning_results['search_type'],
        'scoring': tuning_results['scoring'],
        'cv_splits': tuning_results['cv_splits'],
        'elapsed_time': tuning_results['elapsed_time'],
        'total_fits': tuning_results['total_fits']
    }

    filename = f"{output_dir}/{model_name}_tuning_results.json"
    with open(filename, 'w') as f:
        json.dump(json_results, f, indent=2)

    print(f"Saved tuning results to {filename}")


def compare_tuning_results(
    results_dict: Dict[str, Dict[str, Any]],
    output_dir: str = "model_metrics"
) -> pd.DataFrame:
    """
    Compare tuning results across multiple models.

    Args:
        results_dict: Dictionary mapping model names to tuning results
        output_dir: Directory to save comparison

    Returns:
        DataFrame with comparison
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    comparison_data = []

    for model_name, results in results_dict.items():
        comparison_data.append({
            'Model': model_name,
            'Best Score': results['best_score'],
            'Search Type': results['search_type'],
            'CV Splits': results['cv_splits'],
            'Total Fits': results['total_fits'],
            'Time (s)': results['elapsed_time'],
            'Best Params': str(results['best_params'])[:50] + "..."
        })

    comparison_df = pd.DataFrame(comparison_data)
    comparison_df = comparison_df.sort_values('Best Score', ascending=False)

    # Save to CSV
    comparison_df.to_csv(f"{output_dir}/tuning_comparison.csv", index=False)

    # Print comparison
    print("\n" + "="*100)
    print("  HYPERPARAMETER TUNING COMPARISON")
    print("="*100)
    print(comparison_df.to_string(index=False))
    print("="*100)
    print(f"\nSaved comparison to {output_dir}/tuning_comparison.csv\n")

    return comparison_df


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_grid_size(param_grid: Dict[str, List]) -> int:
    """Calculate total number of combinations in parameter grid."""
    size = 1
    for values in param_grid.values():
        size *= len(values)
    return size


def extract_best_params(tuning_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract best parameters from tuning results.

    Args:
        tuning_results: Results from tune_hyperparameters

    Returns:
        Best parameters dictionary
    """
    return tuning_results['best_params']


def get_param_importance(tuning_results: Dict[str, Any], top_n: int = 5) -> pd.DataFrame:
    """
    Analyze parameter importance by variance in scores.

    Args:
        tuning_results: Results from tune_hyperparameters
        top_n: Number of top parameters to return

    Returns:
        DataFrame with parameter importance
    """
    cv_results = tuning_results['cv_results']
    results_df = pd.DataFrame(cv_results)

    # Extract parameter columns
    param_cols = [col for col in results_df.columns if col.startswith('param_')]

    importance_data = []

    for param_col in param_cols:
        param_name = param_col.replace('param_', '')

        # Group by parameter value and calculate mean score variance
        grouped = results_df.groupby(param_col)['mean_test_score']
        score_max = grouped.max().max()  # Overall max across all parameter values
        score_min = grouped.min().min()  # Overall min across all parameter values
        score_range = score_max - score_min

        importance_data.append({
            'Parameter': param_name,
            'Score Range': float(score_range),  # Convert to float for consistency
            'Num Values': len(grouped),
            'Best Value': results_df.loc[results_df['rank_test_score'] == 1, param_col].values[0]
        })

    importance_df = pd.DataFrame(importance_data)
    importance_df = importance_df.sort_values('Score Range', ascending=False).head(top_n)

    print(f"\n  Top {top_n} Most Important Parameters:")
    print(f"     {'Parameter':<40} {'Score Range':<15} {'Best Value'}")
    print(f"     {'-'*70}")
    for _, row in importance_df.iterrows():
        print(f"     {row['Parameter']:<40} {row['Score Range']:<15.4f} {row['Best Value']}")

    return importance_df
