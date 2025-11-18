"""
Bonus-to-Main Number Predictor
===============================
Generates predictions for which numbers from recent bonus list will appear as main numbers.

UPDATED v3.10: Accepts bonus window as dict entries for better metadata
"""

import numpy as np
from typing import Dict, List, Tuple, Any


def generate_bonus_to_main_predictions(
    model_pipeline,
    feature_names: List[str],
    bonus_to_main_features: Dict,
    current_bonus_window: List[Any],
    category_dict: Dict,
    num_predictions: int = 3
) -> Tuple[List[int], List[Dict[str, Any]]]:
    """
    Generate predictions for numbers from recent bonus window that will appear as main.

    Args:
        model_pipeline: Trained bonus-to-main model
        feature_names: List of feature names
        bonus_to_main_features: Feature dictionary for all numbers
        current_bonus_window: List of bonus entries (numbers or dicts) in window
        category_dict: Dictionary mapping number to category
        num_predictions: Number of predictions to generate (default 3)

    Returns:
        Tuple of (selected_numbers, all_predictions_data)
        - selected_numbers: List of predicted numbers (length = num_predictions)
        - all_predictions_data: List of dicts with number, probability, category for top 6
    """
    if not current_bonus_window:
        print("\n⚠️  No numbers in current bonus window")
        return []

    # Extract numbers from window (handle both list of ints and list of dicts)
    if isinstance(current_bonus_window[0], dict):
        bonus_numbers = [entry['number'] for entry in current_bonus_window]
    else:
        bonus_numbers = current_bonus_window

    print(f"\n{'='*70}")
    print("GENERATING BONUS-TO-MAIN PREDICTIONS")
    print(f"{'='*70}")
    print(f"Current bonus window: {bonus_numbers}")

    # Deduplicate bonus window (same number can appear multiple times in last 10 draws)
    unique_bonus_numbers = list(dict.fromkeys(bonus_numbers))  # Preserves order
    print(f"Unique candidates: {len(unique_bonus_numbers)} numbers (after deduplication)")

    # Predict for all numbers in window
    predictions = []

    for num in unique_bonus_numbers:
        if num not in bonus_to_main_features:
            continue

        features = bonus_to_main_features[num]
        feature_vector = []

        for fname in feature_names:
            val = features.get(fname, 0.0)
            if isinstance(val, (int, float, np.number)):
                feature_vector.append(float(val))
            else:
                feature_vector.append(0.0)

        # Get probability
        prob = model_pipeline.predict_proba([feature_vector])[0][1]

        category = category_dict.get(num, 'unknown')

        predictions.append({
            'number': num,
            'probability': prob,
            'category': category,
            'draws_since_bonus': features.get('draws_since_bonus', 10),
            'composite_score': features.get('composite_transition_score', 0.0)
        })

    # Sort by probability
    predictions.sort(key=lambda x: x['probability'], reverse=True)

    print(f"\nTop candidates from bonus window:")
    for i, pred in enumerate(predictions[:min(10, len(predictions))]):
        print(f"  {i+1}. Number {pred['number']:2d}: "
              f"{pred['probability']*100:5.1f}% "
              f"[{pred['category']:6s}] "
              f"({pred['draws_since_bonus']} draws ago)")

    # Select top N with diversity (but ensure we get N numbers)
    selected = []
    category_counts = {'hot': 0, 'medium': 0, 'cold': 0}

    # First pass: try with diversity constraint (max 2 per category)
    for pred in predictions:
        if len(selected) >= num_predictions:
            break

        num = pred['number']
        category = pred['category']

        # Apply light category balance (prefer medium, but don't force)
        if category in category_counts and category_counts[category] >= 2:
            continue

        selected.append(num)
        if category in category_counts:
            category_counts[category] += 1

    # Second pass: if we don't have enough, add top remaining regardless of category
    if len(selected) < num_predictions:
        for pred in predictions:
            if len(selected) >= num_predictions:
                break

            num = pred['number']
            if num not in selected:
                selected.append(num)
                category = pred['category']
                if category in category_counts:
                    category_counts[category] += 1

    print(f"\n✓ Selected {len(selected)} numbers from recent bonus window:")
    for i, num in enumerate(selected):
        pred = next(p for p in predictions if p['number'] == num)
        print(f"  Pick {i+1}: Number {num:2d} - "
              f"{pred['probability']*100:.1f}% "
              f"[{pred['category']:6s}] "
              f"({pred['draws_since_bonus']} draws ago)")

    # Prepare top 6 predictions data for file output
    top_6_data = []
    for i, pred in enumerate(predictions[:6]):
        top_6_data.append({
            'number': pred['number'],
            'probability': pred['probability'],
            'category': pred['category'],
            'draws_since_bonus': pred['draws_since_bonus'],
            'rank': i + 1
        })

    return selected, top_6_data


def assign_bonus_to_main_to_models(
    bonus_to_main_predictions: List[int],
    num_models: int = 3
) -> Dict[int, int]:
    """
    Assign bonus-to-main predictions to models.

    Strategy:
    - Model 1 gets prediction 0 (highest probability)
    - Model 2 gets prediction 1 (second highest)
    - Model 3 gets prediction 2 (third highest)

    Args:
        bonus_to_main_predictions: List of predicted numbers
        num_models: Number of models

    Returns:
        Dictionary mapping model_index (1-based) -> bonus_to_main_number
    """
    assignments = {}

    # Use 1-based indexing to match quickpick.py model indexing
    for model_idx in range(1, num_models + 1):
        pred_idx = model_idx - 1
        if pred_idx < len(bonus_to_main_predictions):
            assignments[model_idx] = bonus_to_main_predictions[pred_idx]
        else:
            # If we don't have enough predictions, assign None
            assignments[model_idx] = None

    print(f"\n{'='*70}")
    print("BONUS-TO-MAIN ASSIGNMENTS TO MODELS")
    print(f"{'='*70}")

    for model_idx, number in assignments.items():
        if number is not None:
            print(f"Model {model_idx}: Number {number:2d}")
        else:
            print(f"Model {model_idx}: No assignment")

    return assignments
