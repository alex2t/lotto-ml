"""
Bonus-to-Main Number Predictor
===============================
Generates predictions for which numbers from recent bonus list will appear as main numbers.

UPDATED v3.10: Accepts bonus window as dict entries for better metadata
"""

from typing import Dict, List, Tuple, Any

from ml_lotto.features.bonus_to_main_features import bonus_to_main_row


def generate_bonus_to_main_predictions(
    model_pipeline,
    feature_names: List[str],
    point_in_time: Dict[int, Dict[str, Any]],
    bonus_positions: Dict[int, int],
    category_dict: Dict,
    num_predictions: int = 3
) -> Tuple[List[int], List[Dict[str, Any]]]:
    """
    Generate predictions for numbers from recent bonus window that will appear as main.

    Each row is built exactly as the trainer builds one (F-40): the engine's next-draw
    features with the number's place in the bonus window.

    Args:
        model_pipeline: Trained bonus-to-main model
        feature_names: Feature names the model was fitted on
        point_in_time: The engine's next-draw features, keyed by number
        bonus_positions: bonus_window_positions() over the full history
        category_dict: Dictionary mapping number to category
        num_predictions: Number of predictions to generate (default 3)

    Returns:
        Tuple of (selected_numbers, all_predictions_data)
        - selected_numbers: List of predicted numbers (length = num_predictions)
        - all_predictions_data: List of dicts with number, probability, category for top 6

    Raises:
        ValueError: the bonus window is empty (F-42).
    """
    if not bonus_positions:
        raise ValueError(
            "Empty bonus window: none of the last 10 draws has a bonus ball. "
            "The draw history is incomplete - fix it rather than predicting from nothing."
        )

    # Most recent first
    candidates = sorted(bonus_positions, key=bonus_positions.get)

    print(f"\n{'='*70}")
    print("GENERATING BONUS-TO-MAIN PREDICTIONS")
    print(f"{'='*70}")
    print(f"Unique candidates: {len(candidates)} numbers {candidates}")

    predictions = []
    for num in candidates:
        draws_since_bonus = bonus_positions[num]
        feature_vector = bonus_to_main_row(point_in_time[num], feature_names, draws_since_bonus)
        prob = model_pipeline.predict_proba([feature_vector])[0][1]

        predictions.append({
            'number': num,
            'probability': prob,
            'category': category_dict.get(num, 'unknown'),
            'draws_since_bonus': draws_since_bonus,
            'composite_score': point_in_time[num]['composite_transition_score']
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

    print(f"\nSelected {len(selected)} numbers from recent bonus window:")
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
