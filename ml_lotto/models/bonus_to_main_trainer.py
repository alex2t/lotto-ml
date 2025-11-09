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


def train_bonus_to_main_model(
    model_config: Dict,
    all_draws: List[Dict],
    bonus_to_main_features: Dict,
    training_start_draw: int
) -> Tuple:
    """
    Train model to predict which numbers from recent bonus list will appear as main.

    Args:
        model_config: Model configuration dictionary
        all_draws: List of all historical draws
        bonus_to_main_features: Feature dictionary for all numbers
        training_start_draw: Index to start training from

    Returns:
        Tuple of (trained_pipeline, feature_list)
    """
    print(f"\n{'='*70}")
    print(f"TRAINING BONUS-TO-MAIN PREDICTOR: {model_config['name']}")
    print(f"{'='*70}")

    feature_names = model_config['features']
    print(f"Features: {len(feature_names)}")
    for fname in feature_names:
        print(f"  - {fname}")

    # Build training data
    X_train = []
    y_train = []

    print(f"\nBuilding training dataset...")
    print(f"  Total draws available: {len(all_draws)}")
    print(f"  Training start index: {training_start_draw}")
    print(f"  Training draws: {len(all_draws) - training_start_draw}")

    # Check first draw structure
    if all_draws:
        print(f"  Sample draw keys: {list(all_draws[0].keys())}")

    # For each draw starting from training_start_draw
    for draw_idx in range(training_start_draw, len(all_draws)):
        current_draw = all_draws[draw_idx]

        # Get numbers in recent bonus window for this draw
        # We need to look at previous draw's recent bonus list
        if draw_idx < 10:
            continue

        # Get recent bonus list from current draw metadata
        recent_bonus_numbers = []
        recent_bonus_positions = {}  # track position in window

        # Build recent bonus list from previous 10 draws
        lookback_start = max(0, draw_idx - 10)
        for prev_idx in range(lookback_start, draw_idx):
            prev_draw = all_draws[prev_idx]
            # Check both 'bonus_number' and 'bonus' keys for compatibility
            bonus_num = prev_draw.get('bonus_number') or prev_draw.get('bonus')
            if bonus_num:
                # Only add if not already in window (most recent appearance matters)
                if bonus_num not in recent_bonus_numbers:
                    recent_bonus_numbers.append(bonus_num)
                    # Position: 0 = most recent, 9 = 10 draws ago
                    draws_ago = draw_idx - prev_idx - 1
                    recent_bonus_positions[bonus_num] = draws_ago

        # For each number in recent bonus list, check if it appeared as main
        current_main_numbers = current_draw.get('numbers', [])

        for num in recent_bonus_numbers:
            if num not in bonus_to_main_features:
                continue

            # Get base features for this number
            base_features = bonus_to_main_features[num]

            # Override window-specific features for this historical point
            draws_since_bonus = recent_bonus_positions.get(num, -1)

            # Build feature vector with overridden values
            feature_vector = []
            for fname in feature_names:
                if fname == 'is_in_bonus_window':
                    feature_vector.append(1.0)  # It's in the window
                elif fname == 'draws_since_bonus':
                    feature_vector.append(float(draws_since_bonus))
                elif fname == 'timing_decay_weight':
                    # Calculate timing weight for this position
                    timing_weights = bonus_to_main_features.get(1, {})  # Any number has timing data
                    draw_offset = draws_since_bonus + 1
                    timing_key = f'timing_decay_weight'
                    # We need to get this from the config, but for now use base feature
                    val = base_features.get(fname, 0.0)
                    feature_vector.append(float(val) if isinstance(val, (int, float, np.number)) else 0.0)
                else:
                    val = base_features.get(fname, 0.0)
                    feature_vector.append(float(val) if isinstance(val, (int, float, np.number)) else 0.0)

            X_train.append(feature_vector)

            # Label: 1 if appeared as main, 0 otherwise
            y_train.append(1 if num in current_main_numbers else 0)

    X_train = np.array(X_train)
    y_train = np.array(y_train)

    print(f"\nTraining data: {len(X_train)} samples")
    print(f"  Positive class (appeared as main): {sum(y_train)} ({sum(y_train)/len(y_train)*100:.1f}%)")
    print(f"  Negative class: {len(y_train) - sum(y_train)} ({(len(y_train)-sum(y_train))/len(y_train)*100:.1f}%)")

    if len(X_train) == 0:
        raise ValueError("No training data generated")

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

    # Calculate training accuracy
    train_pred = pipeline.predict(X_train)
    train_acc = np.mean(train_pred == y_train)

    print(f"\n✓ Training complete!")
    print(f"  Training accuracy: {train_acc*100:.1f}%")

    return pipeline, feature_names


def extract_bonus_to_main_features_for_number(
    number: int,
    bonus_to_main_data: Dict,
    hmc_data: Dict,
    current_bonus_window: List[int]
) -> Dict:
    """
    Extract features for bonus-to-main prediction for a specific number.

    Args:
        number: The lottery number
        bonus_to_main_data: Loaded bonus-to-main patterns JSON
        hmc_data: HMC trigger periods data
        current_bonus_window: List of numbers in current bonus window

    Returns:
        Dictionary of features
    """
    # Get number's transition profile
    profile = bonus_to_main_data.get('per_number_transition_profile', {}).get(str(number), {})

    # Get number's HMC data
    hmc_info = hmc_data.get(str(number), {})
    category = hmc_info.get('category', 'unknown')
    recent_data = hmc_info.get('recent', {})

    # Check if number is in current bonus window
    is_in_window = number in current_bonus_window

    # Get position in window (0 = most recent)
    draws_since_bonus = -1
    if is_in_window:
        try:
            draws_since_bonus = current_bonus_window.index(number)
        except ValueError:
            draws_since_bonus = -1

    # Get transition weights
    category_weights = bonus_to_main_data.get('category_transition_weights', {})
    freshness_weights = bonus_to_main_data.get('freshness_transition_weights', {})
    timing_weights = bonus_to_main_data.get('timing_decay_weights', {})

    # Category multiplier
    category_multiplier = category_weights.get(category, {}).get('weight', 1.0)

    # Freshness (assuming C0 for simplicity, should get from HMC data)
    freshness_multiplier = freshness_weights.get('C0', {}).get('weight', 1.0)

    # Timing decay weight
    timing_weight = 0.0
    if draws_since_bonus >= 0 and draws_since_bonus < 10:
        timing_key = f'draw_{draws_since_bonus + 1}'
        timing_weight = timing_weights.get(timing_key, 0.0)

    # Historical transition rate for this number
    historical_transition_rate = profile.get('transition_rate', 0.0)
    avg_draws_to_transition = profile.get('avg_draws_to_transition', 5.0)

    # Calculate composite score
    base_rate = bonus_to_main_data.get('transition_prediction_factors', {}).get('base_rate', 0.74)

    if is_in_window:
        composite_score = (
            base_rate *
            category_multiplier *
            freshness_multiplier *
            (1 + timing_weight)
        )
    else:
        composite_score = 0.0

    return {
        'is_in_bonus_window': 1 if is_in_window else 0,
        'draws_since_bonus': draws_since_bonus if draws_since_bonus >= 0 else 10,
        'historical_transition_rate': historical_transition_rate,
        'category_multiplier': category_multiplier,
        'freshness_multiplier': freshness_multiplier,
        'timing_decay_weight': timing_weight,
        'composite_transition_score': composite_score,
        'avg_draws_to_transition': avg_draws_to_transition if avg_draws_to_transition else 5.0,
        'recent_4': recent_data.get('last_4', 0),
        'recent_9': recent_data.get('last_9', 0),
        'total_count': hmc_info.get('total_count', 0)
    }
