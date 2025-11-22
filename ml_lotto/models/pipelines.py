"""
pipelines.py
============
Creates ML model pipelines with scaling and calibration.
"""

import xgboost as xgb
from catboost import CatBoostClassifier
from typing import Dict, Any, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline


def create_model_pipeline(
    model_config: Dict[str, Any],
    scale_pos_weight: Optional[float] = None
) -> Pipeline:
    """
    Create a model pipeline based on configuration.

    Args:
        model_config: Model configuration dictionary containing:
            - algorithm: 'logistic_regression', 'random_forest', 'xgboost', or 'catboost'
            - algorithm_params: Parameters for the base estimator
            - calibration: Calibration method and CV folds
        scale_pos_weight: Optional class imbalance weight for XGBoost

    Returns:
        Pipeline with scaler and calibrated classifier

    Pipeline Structure:
        1. StandardScaler: Normalizes features to zero mean, unit variance
        2. CalibratedClassifierCV: Wraps base classifier for probability calibration
           - Uses isotonic or sigmoid method
           - Cross-validated to prevent overfitting
    """
    algorithm = model_config['algorithm']
    algo_params = model_config.get('algorithm_params', {}).copy()
    cal_params = model_config.get('calibration', {'method': 'isotonic', 'cv': 3})
    
    # Create base classifier
    if algorithm == 'logistic_regression' or algorithm == 'logistic':
        base_clf = LogisticRegression(**algo_params)

    elif algorithm == 'random_forest' or 'forest' in algorithm.lower():
        base_clf = RandomForestClassifier(**algo_params)

    elif algorithm == 'xgboost' or algorithm == 'xgb':
        # Add scale_pos_weight for class imbalance if provided
        if scale_pos_weight is not None:
            algo_params['scale_pos_weight'] = scale_pos_weight
        base_clf = xgb.XGBClassifier(**algo_params)

    elif algorithm == 'catboost':
        base_clf = CatBoostClassifier(**algo_params)

    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    
    # Wrap with calibration
    calibrated_clf = CalibratedClassifierCV(
        estimator=base_clf,
        method=cal_params['method'],
        cv=cal_params['cv']
    )
    
    # Create full pipeline
    # Note: Step name 'classifier' matches hyperparameter tuning grids
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', calibrated_clf)
    ])

    return pipeline