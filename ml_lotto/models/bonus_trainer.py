# ml_lotto/models/bonus_trainer.py
"""
bonus_trainer.py
================
Trains ML model specifically for bonus ball prediction.

Uses bonus-specific features from lotto_bonus_analysis.json to train
a logistic regression model that predicts which numbers are most likely
to be drawn as bonus balls.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline


def build_bonus_training_dataset(
    all_draws: List[Dict[str, Any]],
    bonus_features_dict: Dict[int, Dict[str, Any]],
    training_start_draw: int = 100
) -> pd.DataFrame:
    """
    Build training dataset for bonus ball prediction.
    
    For each historical draw:
        For each number 1-47:
            X (features) = bonus-specific features from JSON
            y (label) = 1 if number was bonus ball, 0 otherwise
    
    Args:
        all_draws: Historical draw data with bonus balls
        bonus_features_dict: Bonus feature values for each number
        training_start_draw: Starting draw index for training
        
    Returns:
        DataFrame with bonus features + 'is_bonus' label column
    """
    print("\n  Building bonus training dataset...")
    records = []
    
    feature_names = [
        'category_weight',
        'was_bonus_last_10',
        'freshness_weight',
        'timing_zone_weight',
        'days_since_last_bonus',
        'bonus_frequency_ratio',
        'total_bonus_count',
        'avg_days_between_bonus'
    ]
    
    for draw_idx in range(training_start_draw, len(all_draws)):
        bonus_number = all_draws[draw_idx].get('bonus_number')
        
        for num in range(1, 48):
            if num in bonus_features_dict:
                feat = bonus_features_dict[num]
                record = {fname: feat.get(fname, 0) for fname in feature_names}
                record['is_bonus'] = 1 if num == bonus_number else 0
                records.append(record)
    
    train_df = pd.DataFrame(records)
    bonus_count = train_df['is_bonus'].sum()
    print(f"    Training records: {len(train_df)}")
    print(f"    Bonus ball occurrences: {bonus_count}")
    print(f"    Class balance: {bonus_count}/{len(train_df)} ({bonus_count/len(train_df)*100:.2f}%)")
    
    return train_df


def train_bonus_model(
    bonus_model_config: Dict[str, Any],
    all_draws: List[Dict[str, Any]],
    bonus_features_dict: Dict[int, Dict[str, Any]],
    training_start_draw: int = 100
) -> Tuple[Pipeline, List[str]]:
    """
    Train bonus ball prediction model.
    
    Args:
        bonus_model_config: Bonus model configuration
        all_draws: Historical draw data
        bonus_features_dict: Bonus feature values
        training_start_draw: Starting draw index
        
    Returns:
        Tuple of (trained_pipeline, selected_features)
    """
    print("\n" + "="*70)
    print("TRAINING BONUS BALL PREDICTION MODEL")
    print("="*70)
    print(f"Model: {bonus_model_config['name']}")
    print(f"Algorithm: {bonus_model_config['algorithm']}")
    print(f"Features: {bonus_model_config['features']}")
    
    train_df = build_bonus_training_dataset(
        all_draws,
        bonus_features_dict,
        training_start_draw
    )
    
    selected_features = bonus_model_config['features']
    
    X = train_df[selected_features].values
    y = train_df['is_bonus'].values
    
    algo_params = bonus_model_config['algorithm_params'].copy()
    base_clf = LogisticRegression(**algo_params)
    
    cal_params = bonus_model_config['calibration']
    calibrated_clf = CalibratedClassifierCV(
        estimator=base_clf,
        method=cal_params['method'],
        cv=cal_params['cv']
    )
    
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', calibrated_clf)
    ])
    
    print(f"\n  Training bonus model...")
    pipeline.fit(X, y)
    print(f"  ✓ Bonus model training complete")
    
    return pipeline, selected_features