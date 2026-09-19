# ml_lotto/prediction/bonus_predictor.py
"""
bonus_predictor.py
==================
Generate 3 diverse bonus ball predictions using trained bonus model.

Outputs 3 predictions with different probability tiers and category diversity.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Set


def generate_bonus_predictions(
    bonus_pipeline: Any,
    bonus_features: List[str],
    bonus_features_dict: Dict[int, Dict[str, Any]],
    category_dict: Dict[int, str],
    num_predictions: int = 3
) -> Tuple[List[int], List[Dict[str, Any]]]:
    """
    Generate N diverse bonus ball predictions.

    Strategy:
        Prediction 1: Highest probability from optimal pool (excluding recent)
        Prediction 2: Second-tier probability with category diversity
        Prediction 3: Alternative high-probability pick with category balance

    Args:
        bonus_pipeline: Trained bonus prediction model
        bonus_features: Feature names used by model
        bonus_features_dict: Feature values for all numbers
        category_dict: HMC category for each number
        num_predictions: Number of predictions to generate (default: 3)

    Raises:
        ValueError: if fewer than num_predictions numbers remain after excluding recent bonus balls.

    Returns:
        Tuple of (selected_numbers, all_predictions_data)
        - selected_numbers: List of predicted bonus numbers (length = num_predictions)
        - all_predictions_data: List of dicts with number, probability, category for top 6
    """
    print("\n" + "="*70)
    print("GENERATING BONUS BALL PREDICTIONS")
    print("="*70)
    
    X_pred_list = []
    valid_numbers = []
    
    for num in range(1, 48):
        if num in bonus_features_dict:
            feat = bonus_features_dict[num]
            # feat[col], never feat.get(col, 0) - see F-9. A missing column must raise here
            # rather than be served as a constant the model was never fitted on.
            record = [feat[col] for col in bonus_features]
            X_pred_list.append(record)
            valid_numbers.append(num)
    
    X_pred = np.array(X_pred_list)
    probabilities = bonus_pipeline.predict_proba(X_pred)[:, 1]
    
    num_to_prob = {num: prob for num, prob in zip(valid_numbers, probabilities)}
    
    recent_bonus_exclusions = set()
    for num in range(1, 48):
        if bonus_features_dict.get(num, {}).get('was_bonus_last_10', 0) == 1:
            recent_bonus_exclusions.add(num)
    
    print(f"\n  Total candidates: {len(valid_numbers)}")
    print(f"  Recent bonus exclusions: {len(recent_bonus_exclusions)} numbers")
    print(f"  Available pool: {len(valid_numbers) - len(recent_bonus_exclusions)} numbers")
    
    available_pool = [
        (num, num_to_prob[num], category_dict.get(num, 'medium'))
        for num in valid_numbers
        if num not in recent_bonus_exclusions
    ]
    
    # Deterministic ordering: highest probability first, ties broken by lowest number
    available_pool.sort(key=lambda x: (-x[1], x[0]))

    # F-5: fail here, clearly, rather than with a bare IndexError in the selection loop.
    if len(available_pool) < num_predictions:
        raise ValueError(
            f"Bonus pool has {len(available_pool)} numbers after recent-bonus exclusions; "
            f"{num_predictions} predictions requested"
        )
    
    predictions = []
    used_categories = set()
    
    print(f"\n  Selecting {num_predictions} diverse predictions...")
    
    for i in range(num_predictions):
        if i == 0:
            selected_num, selected_prob, selected_cat = available_pool[0]
            print(f"    Prediction {i+1}: #{selected_num} (prob={selected_prob:.4f}, cat={selected_cat}) - Highest probability")
        
        elif i == 1:
            for num, prob, cat in available_pool[1:]:
                if num not in predictions and cat not in used_categories:
                    selected_num, selected_prob, selected_cat = num, prob, cat
                    print(f"    Prediction {i+1}: #{selected_num} (prob={selected_prob:.4f}, cat={selected_cat}) - Category diversity")
                    break
            else:
                selected_num, selected_prob, selected_cat = available_pool[i]
                print(f"    Prediction {i+1}: #{selected_num} (prob={selected_prob:.4f}, cat={selected_cat}) - Second tier")
        
        else:
            candidates = [
                (num, prob, cat) 
                for num, prob, cat in available_pool 
                if num not in predictions
            ]
            
            for num, prob, cat in candidates:
                if cat not in used_categories:
                    selected_num, selected_prob, selected_cat = num, prob, cat
                    print(f"    Prediction {i+1}: #{selected_num} (prob={selected_prob:.4f}, cat={selected_cat}) - Alternative category")
                    break
            else:
                selected_num, selected_prob, selected_cat = candidates[0]
                print(f"    Prediction {i+1}: #{selected_num} (prob={selected_prob:.4f}, cat={selected_cat}) - High probability alternative")
        
        predictions.append(selected_num)
        used_categories.add(selected_cat)
    
    print(f"\n✓ Generated {len(predictions)} bonus predictions: {predictions}")
    print(f"  Category distribution: {[category_dict.get(p, 'unknown') for p in predictions]}")

    # Prepare top 6 predictions data for file output
    top_6_data = []
    for i, (num, prob, cat) in enumerate(available_pool[:6]):
        top_6_data.append({
            'number': num,
            'probability': prob,
            'category': cat,
            'rank': i + 1
        })

    return predictions, top_6_data


def assign_bonus_to_models(
    bonus_predictions: List[int],
    num_models: int
) -> Dict[int, int]:
    """
    Assign bonus predictions to main models.
    
    Args:
        bonus_predictions: List of predicted bonus numbers
        num_models: Number of main models
        
    Returns:
        Dictionary mapping model_index -> bonus_number
    """
    assignments = {}
    
    for model_idx in range(1, num_models + 1):
        bonus_idx = (model_idx - 1) % len(bonus_predictions)
        assignments[model_idx] = bonus_predictions[bonus_idx]
    
    print(f"\n  Bonus assignments:")
    for model_idx, bonus_num in assignments.items():
        print(f"    Model {model_idx} → Bonus #{bonus_num}")
    
    return assignments