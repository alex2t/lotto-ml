"""
Bonus-to-Main Model Trainer
============================
Trains ML model to predict which numbers from recent bonus list will appear as main numbers.

Pattern: 74% of bonus numbers appear as main within 10 draws (3.48x boost over random)
"""

import numpy as np
from typing import Dict, List, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from collections import defaultdict
from ml_lotto.features.extractor import expand_feature_selection
from ml_lotto.features.walk_forward import PointInTimeFeatureEngine
from ml_lotto.models.model_metrics import calculate_comprehensive_metrics


def _build_bonus_to_main_dataset(
    engine: PointInTimeFeatureEngine,
    all_draws: List[Dict],
    bonus_to_main_features: Dict,
    feature_names: List[str],
    start_draw: int,
    end_draw: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build a point-in-time dataset over draws [start_draw, end_draw).

    One row per number in each draw's 10-draw bonus window, labelled 1 if that
    number was drawn as a main number.

    Returns:
        Tuple of (X, y, draw_index) where draw_index gives each row's draw, so
        Top-K can be scored within a draw despite the variable window size.
    """
    X = []
    y = []
    draw_index = []

    for draw_idx in range(max(start_draw, 10), end_draw):
        current_draw = all_draws[draw_idx]
        feats_at_draw = engine.extract_features_at_draw(draw_idx)

        # Build recent bonus list from previous 10 draws
        recent_bonus_numbers = []
        recent_bonus_positions = {}  # number -> draws since it was the bonus
        for prev_idx in range(max(0, draw_idx - 10), draw_idx):
            prev_draw = all_draws[prev_idx]
            # Check both 'bonus_number' and 'bonus' keys for compatibility
            bonus_num = prev_draw.get('bonus_number') or prev_draw.get('bonus')
            if bonus_num and bonus_num not in recent_bonus_numbers:
                recent_bonus_numbers.append(bonus_num)
                recent_bonus_positions[bonus_num] = draw_idx - prev_idx - 1

        current_main_numbers = current_draw.get('numbers', [])

        for num in recent_bonus_numbers:
            base_features = feats_at_draw.get(num) or bonus_to_main_features.get(num, {})
            if not base_features:
                continue

            draws_since_bonus = recent_bonus_positions.get(num, -1)

            # Override window-specific features for this historical point
            feature_vector = []
            for fname in feature_names:
                if fname == 'is_in_bonus_window':
                    feature_vector.append(1.0)
                elif fname == 'draws_since_bonus':
                    feature_vector.append(float(draws_since_bonus))
                else:
                    val = base_features.get(fname, 0.0)
                    feature_vector.append(float(val) if isinstance(val, (int, float, np.number)) else 0.0)

            X.append(feature_vector)
            y.append(1 if num in current_main_numbers else 0)
            draw_index.append(draw_idx)

    return np.array(X), np.array(y), np.array(draw_index)


def train_bonus_to_main_model(
    model_config: Dict,
    all_draws: List[Dict],
    base_engine: PointInTimeFeatureEngine,
    bonus_to_main_features: Dict,
    training_start_draw: int,
    training_end_draw: int = None,
    validation_start_draw: int = None
) -> Tuple:
    """
    Train model to predict which numbers from recent bonus list will appear as main.

    Args:
        model_config: Model configuration dictionary
        all_draws: List of all historical draws
        base_engine: The run's shared feature engine over all_draws
        bonus_to_main_features: Feature dictionary for all numbers
        training_start_draw: Index to start training from
        training_end_draw: Index to end training (exclusive). If None, uses all available draws.
        validation_start_draw: Index to start validation from

    Returns:
        Tuple of (trained_pipeline, feature_list, validation_metrics).
        validation_metrics is None when no validation_start_draw was given.
    """
    if training_end_draw is None:
        training_end_draw = len(all_draws)

    print(f"\n{'='*70}")
    print(f"TRAINING BONUS-TO-MAIN PREDICTOR: {model_config['name']}")
    print(f"{'='*70}")

    # Get all available features from a sample feature dict
    sample_num = next(iter(bonus_to_main_features.keys()))
    all_available_features = list(bonus_to_main_features[sample_num].keys())

    # Expand feature selection (handles placeholders like PAIRWISE_INTERACTIONS, TRIPLE_INTERACTIONS)
    feature_spec = model_config['features']
    feature_names = expand_feature_selection(feature_spec, all_available_features)

    print(f"Feature expansion: {len(feature_spec)} spec items -> {len(feature_names)} actual features")
    print(f"Features: {len(feature_names)}")
    for fname in feature_names:
        print(f"  - {fname}")

    print(f"\nBuilding TRAINING dataset...")
    print(f"  Total draws available: {len(all_draws)}")
    print(f"  Training start index: {training_start_draw}")
    print(f"  Training end index: {training_end_draw}")
    print(f"  Training draws: {training_end_draw - training_start_draw}")

    engine = base_engine.with_base_features(bonus_to_main_features)

    X_train, y_train, _ = _build_bonus_to_main_dataset(
        engine, all_draws, bonus_to_main_features, feature_names,
        training_start_draw, training_end_draw
    )

    if len(X_train) == 0:
        raise ValueError("No training data generated")

    print(f"\nTraining data: {len(X_train)} samples")
    print(f"  Positive class (appeared as main): {sum(y_train)} ({sum(y_train)/len(y_train)*100:.1f}%)")
    print(f"  Negative class: {len(y_train) - sum(y_train)} ({(len(y_train)-sum(y_train))/len(y_train)*100:.1f}%)")

    # Train model
    algorithm = model_config['algorithm']
    params = model_config.get('algorithm_params', {})

    print(f"\nTraining {algorithm}...")

    if algorithm == 'logistic_regression':
        base_model = LogisticRegression(**params)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    # Calibrate probabilities
    calibration_config = model_config.get('calibration', {})
    if calibration_config:
        print(f"Applying {calibration_config.get('method', 'sigmoid')} calibration...")
        pipeline = CalibratedClassifierCV(
            base_model,
            method=calibration_config.get('method', 'sigmoid'),
            cv=calibration_config.get('cv', 5)
        )
    else:
        pipeline = base_model

    pipeline.fit(X_train, y_train)
    print(f"\nTraining complete")

    # Evaluate on the held-out validation set, with the same metrics as the main models
    metrics = None
    if validation_start_draw is not None:
        print(f"\nBuilding VALIDATION dataset...")
        print(f"  Validation start index: {validation_start_draw}")
        print(f"  Validation draws: {len(all_draws) - validation_start_draw}")

        X_val, y_val, val_draw_index = _build_bonus_to_main_dataset(
            engine, all_draws, bonus_to_main_features, feature_names,
            validation_start_draw, len(all_draws)
        )

        if len(X_val) > 0:
            print(f"  Validation samples: {len(X_val)}")
            metrics = calculate_comprehensive_metrics(
                pipeline=pipeline,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                model_name=model_config['name'],
                save_plots=True,
                output_dir='model_metrics',
                topk_groups=val_draw_index
            )
        else:
            print("  No validation samples generated")

    return pipeline, feature_names, metrics
