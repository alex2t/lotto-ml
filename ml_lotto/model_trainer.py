"""
model_trainer.py
================
Handles ML model training with configurable algorithms and features.
Supports Logistic Regression and XGBoost with calibration.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from typing import Dict, Any, List, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

from ml_lotto.config import MAX_NUMBER, TRAINING_START_DRAW
from ml_lotto.feature_extractor import expand_feature_selection, get_all_feature_names


def build_training_dataset(all_draws: List[Dict[str, Any]], 
                           features_dict: Dict[int, Dict[str, Any]],
                           all_feature_names: List[str]) -> pd.DataFrame:
    """
    Build training dataset by combining features and labels.
    
    INPUT SOURCES:
        all_draws (from lotto_draw_history.json) → LABELS (y = did number win?)
        features_dict (from lotto_trigger_periods.json) → FEATURES (X = number statistics)
    
    TRAINING PROCESS:
        For each historical draw #100 onwards:
            For each number 1-47:
                X (features) ← [total_count, days_since_last, ..., days_since_bonus]
                y (label)    ← 1 if number won that draw, 0 if not
    
    Returns:
        DataFrame with all features + 'hit' column (label)
    """
    print("\nBuilding training dataset...")
    records = []
    
    # Build training data by combining FEATURES + LABELS
    for draw_idx in range(TRAINING_START_DRAW, len(all_draws)):
        # LABELS: Get winning numbers from Draw History JSON (stored under 'numbers')
        # Note: 'numbers' contains both main and bonus balls.
        target_numbers = set(all_draws[draw_idx]['numbers'])
        
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


def create_model_pipeline(model_config: Dict[str, Any], 
                          scale_pos_weight: float = None) -> Pipeline:
    """
    Create a model pipeline based on configuration.
    """
    algorithm = model_config['algorithm']
    algo_params = model_config['algorithm_params'].copy()
    cal_params = model_config['calibration']
    
    if algorithm == 'logistic_regression':
        base_clf = LogisticRegression(**algo_params)
    
    elif algorithm == 'xgboost':
        if scale_pos_weight is not None:
            algo_params['scale_pos_weight'] = scale_pos_weight
        base_clf = xgb.XGBClassifier(**algo_params)
    
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    
    # Calibrate the classifier
    calibrated_clf = CalibratedClassifierCV(
        estimator=base_clf,
        method=cal_params['method'],
        cv=cal_params['cv']
    )
    
    # Create pipeline with scaling
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', calibrated_clf)
    ])
    
    return pipeline


def train_model(model_config: Dict[str, Any],
                train_df: pd.DataFrame,
                all_feature_names: List[str],
                model_index: int) -> Tuple[Pipeline, List[str]]:
    """
    Train a single model based on its configuration.
    """
    print(f"\n→ Model {model_index}: {model_config['name']}")
    print(f"  Description: {model_config['description']}")
    print(f"  Algorithm: {model_config['algorithm']}")
    
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
    X = train_df[selected_features].values
    y = train_df['hit'].values
    
    # Calculate class imbalance for XGBoost
    scale_pos_weight = None
    if model_config['algorithm'] == 'xgboost':
        scale_pos_weight = (len(y) - sum(y)) / sum(y)
    
    # Create and train pipeline
    pipeline = create_model_pipeline(model_config, scale_pos_weight)
    pipeline.fit(X, y)
    
    print(f"  ✓ Training complete")
    
    return pipeline, selected_features


def train_all_models(model_configs: List[Dict[str, Any]],
                     all_draws: List[Dict[str, Any]],
                     features_dict: Dict[int, Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, List[str]]]:
    """
    Train all configured models.
    """
    print("\n" + "="*70)
    print("TRAINING MULTIPLE ML MODELS WITH DIFFERENT STRATEGIES")
    print("="*70)
    print("\nDATA SOURCES:")
    print("  Features (X) ← lotto_trigger_periods.json + custom calculations")
    print("  Labels (y)   ← lotto_draw_history.json")
    
    # Get all available feature names
    all_feature_names = get_all_feature_names(features_dict)
    
    # Build training dataset once
    train_df = build_training_dataset(all_draws, features_dict, all_feature_names)
    print(f"  Available features: {all_feature_names}\n")
    
    # Train each model
    models = {}
    model_features = {}
    
    for idx, model_config in enumerate(model_configs, 1):
        model_name = f"model_{idx}"
        
        pipeline, selected_features = train_model(
            model_config,
            train_df,
            all_feature_names,
            idx
        )
        
        models[model_name] = {
            'pipeline': pipeline,
            'config': model_config
        }
        model_features[model_name] = selected_features
    
    return models, model_features