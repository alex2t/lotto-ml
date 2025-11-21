"""
feature_selection.py
====================
Feature selection utilities for removing redundant and low-importance features.

VERSION: 1.0
- Correlation-based feature removal
- Importance-based feature filtering
- Configurable thresholds
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any, Set
from sklearn.ensemble import RandomForestClassifier


def remove_highly_correlated_features(
    X: pd.DataFrame,
    feature_names: List[str],
    threshold: float = 0.95,
    verbose: bool = True
) -> Tuple[List[str], Dict[str, str]]:
    """
    Remove highly correlated features to reduce redundancy.

    When two features have correlation > threshold, keeps the one that appears first.

    Args:
        X: Feature matrix as DataFrame
        feature_names: List of feature names
        threshold: Correlation threshold (default: 0.95)
        verbose: Whether to print removed features

    Returns:
        Tuple of (remaining_features, removed_features_dict)
        removed_features_dict maps removed feature -> kept feature
    """
    if verbose:
        print(f"\n  🔍 Analyzing feature correlations (threshold={threshold})...")

    # Calculate correlation matrix
    corr_matrix = X.corr().abs()

    # Find pairs of highly correlated features
    upper_triangle = np.triu(np.ones_like(corr_matrix), k=1).astype(bool)
    corr_pairs = []

    for i in range(len(feature_names)):
        for j in range(i + 1, len(feature_names)):
            if corr_matrix.iloc[i, j] > threshold:
                corr_pairs.append((
                    feature_names[i],
                    feature_names[j],
                    corr_matrix.iloc[i, j]
                ))

    # Remove the second feature in each pair
    features_to_remove = set()
    removed_dict = {}

    for feat1, feat2, corr_value in corr_pairs:
        if feat2 not in features_to_remove:
            features_to_remove.add(feat2)
            removed_dict[feat2] = feat1
            if verbose:
                print(f"     ❌ Removing '{feat2}' (corr={corr_value:.3f} with '{feat1}')")

    # Keep features that weren't marked for removal
    remaining_features = [f for f in feature_names if f not in features_to_remove]

    if verbose:
        print(f"  ✓ Removed {len(features_to_remove)} highly correlated features")
        print(f"  ✓ Remaining features: {len(remaining_features)}")

    return remaining_features, removed_dict


def remove_low_importance_features(
    X_train: np.ndarray,
    y_train: np.ndarray,
    feature_names: List[str],
    threshold: float = 0.01,
    method: str = 'random_forest',
    verbose: bool = True
) -> Tuple[List[str], Dict[str, float]]:
    """
    Remove features with very low importance scores.

    Uses Random Forest to quickly assess feature importance.

    Args:
        X_train: Training feature matrix
        y_train: Training labels
        feature_names: List of feature names
        threshold: Minimum importance threshold (default: 0.01)
        method: Method to calculate importance ('random_forest')
        verbose: Whether to print removed features

    Returns:
        Tuple of (remaining_features, importance_dict)
    """
    if verbose:
        print(f"\n  🔍 Analyzing feature importance (threshold={threshold})...")

    # Quick importance estimation with Random Forest
    rf = RandomForestClassifier(
        n_estimators=50,
        max_depth=5,
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)

    importances = rf.feature_importances_
    importance_dict = dict(zip(feature_names, importances))

    # Sort by importance
    sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)

    if verbose:
        print(f"\n     Top 10 most important features:")
        for feat, imp in sorted_features[:10]:
            print(f"       {feat:35s} : {imp:.4f}")

    # Identify low-importance features
    low_importance_features = [feat for feat, imp in importance_dict.items() if imp < threshold]

    if verbose and len(low_importance_features) > 0:
        print(f"\n     Features with importance < {threshold}:")
        for feat in low_importance_features[:10]:
            print(f"       ❌ {feat:35s} : {importance_dict[feat]:.4f}")
        if len(low_importance_features) > 10:
            print(f"       ... and {len(low_importance_features) - 10} more")

    # Keep features above threshold
    remaining_features = [f for f in feature_names if importance_dict[f] >= threshold]

    if verbose:
        print(f"  ✓ Removed {len(low_importance_features)} low-importance features")
        print(f"  ✓ Remaining features: {len(remaining_features)}")

    return remaining_features, importance_dict


def select_features(
    train_df: pd.DataFrame,
    feature_names: List[str],
    enable_correlation_filter: bool = True,
    enable_importance_filter: bool = True,
    correlation_threshold: float = 0.95,
    importance_threshold: float = 0.01,
    verbose: bool = True
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Apply multiple feature selection methods.

    Args:
        train_df: Training DataFrame with features + 'hit' label
        feature_names: List of feature names to consider
        enable_correlation_filter: Whether to remove correlated features
        enable_importance_filter: Whether to remove low-importance features
        correlation_threshold: Correlation threshold (default: 0.95)
        importance_threshold: Importance threshold (default: 0.01)
        verbose: Whether to print selection details

    Returns:
        Tuple of (selected_features, selection_info)
    """
    selection_info = {
        'original_count': len(feature_names),
        'correlation_removed': [],
        'importance_removed': [],
        'final_count': 0
    }

    selected_features = feature_names.copy()

    # Step 1: Remove highly correlated features
    if enable_correlation_filter:
        X = train_df[selected_features]
        selected_features, corr_removed = remove_highly_correlated_features(
            X,
            selected_features,
            threshold=correlation_threshold,
            verbose=verbose
        )
        selection_info['correlation_removed'] = list(corr_removed.keys())

    # Step 2: Remove low-importance features
    if enable_importance_filter:
        X_train = train_df[selected_features].values
        y_train = train_df['hit'].values

        selected_features, importance_dict = remove_low_importance_features(
            X_train,
            y_train,
            selected_features,
            threshold=importance_threshold,
            verbose=verbose
        )
        selection_info['importance_removed'] = [
            f for f in importance_dict.keys()
            if importance_dict[f] < importance_threshold
        ]
        selection_info['importance_dict'] = importance_dict

    selection_info['final_count'] = len(selected_features)

    if verbose:
        print(f"\n  📊 Feature Selection Summary:")
        print(f"     Original features: {selection_info['original_count']}")
        if enable_correlation_filter:
            print(f"     Removed (correlation): {len(selection_info['correlation_removed'])}")
        if enable_importance_filter:
            print(f"     Removed (importance): {len(selection_info['importance_removed'])}")
        print(f"     Final features: {selection_info['final_count']}")
        print(f"     Reduction: {selection_info['original_count'] - selection_info['final_count']} "
              f"({(selection_info['original_count'] - selection_info['final_count'])/selection_info['original_count']*100:.1f}%)")

    return selected_features, selection_info
