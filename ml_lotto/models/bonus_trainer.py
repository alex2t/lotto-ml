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
    training_start_draw: int = 100,
    training_end_draw: int = None
) -> pd.DataFrame:
    """
    Build training dataset for bonus ball prediction with proper train/validation split.

    For each historical draw:
        For each number 1-47:
            X (features) = bonus-specific features from JSON
            y (label) = 1 if number was bonus ball, 0 otherwise

    Args:
        all_draws: Historical draw data with bonus balls
        bonus_features_dict: Bonus feature values for each number
        training_start_draw: Starting draw index for training
        training_end_draw: Ending draw index (exclusive). If None, uses all available draws.

    Returns:
        DataFrame with bonus features + 'is_bonus' label column
    """
    if training_end_draw is None:
        training_end_draw = len(all_draws)

    dataset_type = "training" if training_end_draw < len(all_draws) else "full"
    print(f"\n  Building bonus {dataset_type} dataset...")
    print(f"    Draw range: {training_start_draw} to {training_end_draw-1} ({training_end_draw - training_start_draw} draws)")
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

    for draw_idx in range(training_start_draw, training_end_draw):
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
    training_start_draw: int = 100,
    training_end_draw: int = None,
    validation_start_draw: int = None
) -> Tuple[Pipeline, List[str]]:
    """
    Train bonus ball prediction model with optional validation evaluation.

    Args:
        bonus_model_config: Bonus model configuration
        all_draws: Historical draw data
        bonus_features_dict: Bonus feature values
        training_start_draw: Starting draw index for training
        training_end_draw: Ending draw index for training (exclusive)
        validation_start_draw: Starting draw index for validation

    Returns:
        Tuple of (trained_pipeline, selected_features)
    """
    print("\n" + "="*70)
    print("TRAINING BONUS BALL PREDICTION MODEL")
    print("="*70)
    print(f"Model: {bonus_model_config['name']}")
    print(f"Algorithm: {bonus_model_config['algorithm']}")
    print(f"Features: {bonus_model_config['features']}")

    # Build training dataset
    train_df = build_bonus_training_dataset(
        all_draws,
        bonus_features_dict,
        training_start_draw,
        training_end_draw
    )

    # Build validation dataset if specified
    val_df = None
    if validation_start_draw is not None:
        val_df = build_bonus_training_dataset(
            all_draws,
            bonus_features_dict,
            validation_start_draw,
            None  # Use all remaining draws
        )

    selected_features = bonus_model_config['features']

    X_train = train_df[selected_features].values
    y_train = train_df['is_bonus'].values

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
    pipeline.fit(X_train, y_train)
    print(f"  ✓ Bonus model training complete")

    # Evaluate on validation set if provided
    if val_df is not None and len(val_df) > 0:
        X_val = val_df[selected_features].values
        y_val = val_df['is_bonus'].values

        val_predictions = pipeline.predict(X_val)
        val_accuracy = (val_predictions == y_val).sum() / len(y_val)

        train_predictions = pipeline.predict(X_train)
        train_accuracy = (train_predictions == y_train).sum() / len(y_train)

        print(f"  📊 Train Accuracy: {train_accuracy:.4f}")
        print(f"  📊 Validation Accuracy: {val_accuracy:.4f}")

        if train_accuracy - val_accuracy > 0.05:
            print(f"  ⚠️  Warning: Possible overfitting detected (diff: {train_accuracy - val_accuracy:.4f})")

    return pipeline, selected_features