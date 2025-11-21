"""
ensemble_predict.py
===================
Generate ensemble predictions by combining multiple trained models.

Usage:
    python ensemble_predict.py --strategy majority
    python ensemble_predict.py --strategy threshold --min-votes 3
    python ensemble_predict.py --strategy weighted

This script loads trained models and combines their predictions using
ensemble voting to reduce false positives and improve precision.
"""

import argparse
import sys
from typing import Dict, List, Any
import numpy as np
from ml_lotto.prediction.ensemble import (
    EnsembleVoter,
    analyze_ensemble_agreement,
    display_voting_results,
    display_agreement_analysis
)


def get_model_predictions_from_probabilities(
    pipeline: Any,
    features_dict: Dict[int, Dict[str, Any]],
    feature_names: List[str],
    optimal_threshold: float,
    top_k: int = 20
) -> tuple[List[int], Dict[int, float]]:
    """
    Get predictions and probabilities for a single model.

    Args:
        pipeline: Trained model pipeline
        features_dict: Feature dictionary for all numbers
        feature_names: List of feature names
        optimal_threshold: Optimal decision threshold
        top_k: Maximum predictions to return

    Returns:
        Tuple of (predictions, probabilities)
    """
    # Prepare features for all numbers
    X = []
    numbers = []

    for num in sorted(features_dict.keys()):
        features = [features_dict[num].get(f, 0) for f in feature_names]
        X.append(features)
        numbers.append(num)

    X = np.array(X)

    # Get probabilities
    probabilities = pipeline.predict_proba(X)[:, 1]

    # Apply optimal threshold
    predictions_mask = probabilities >= optimal_threshold

    # Get predictions with probabilities
    predictions = []
    prob_dict = {}

    for i, (num, prob) in enumerate(zip(numbers, probabilities)):
        if predictions_mask[i]:
            predictions.append(num)
            prob_dict[num] = float(prob)

    # Sort by probability and take top_k
    predictions.sort(key=lambda x: prob_dict[x], reverse=True)
    predictions = predictions[:top_k]

    return predictions, prob_dict


def generate_ensemble_predictions(
    models_dict: Dict[str, Any],
    model_features_dict: Dict[str, List[str]],
    features_dict: Dict[int, Dict[str, Any]],
    all_metrics: Dict[str, Dict[str, Any]],
    strategy: str = 'majority',
    min_votes: int = 2,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Generate ensemble predictions from multiple models.

    Args:
        models_dict: Dictionary of trained models
        model_features_dict: Features used by each model
        features_dict: Feature dictionary for all numbers
        all_metrics: Metrics from training (includes optimal thresholds)
        strategy: Voting strategy ('majority', 'threshold', 'weighted', 'unanimous')
        min_votes: Minimum votes required (for 'threshold' strategy)
        top_k: Maximum ensemble predictions to return

    Returns:
        Dictionary containing ensemble results
    """
    print(f"\n{'='*80}")
    print(f"  🎯 ENSEMBLE PREDICTION GENERATION")
    print(f"{'='*80}")
    print(f"  Strategy: {strategy}")
    if strategy == 'threshold':
        print(f"  Minimum votes required: {min_votes}")
    print(f"  Number of models: {len(models_dict)}")

    # Collect predictions from each model
    model_predictions = {}
    model_probabilities = {}

    print(f"\n  Collecting predictions from each model...")

    for model_name, model_info in models_dict.items():
        pipeline = model_info['pipeline']
        config = model_info['config']
        feature_names = model_features_dict[model_name]

        # Get optimal threshold from metrics
        model_display_name = config['name']
        optimal_threshold = all_metrics.get(model_display_name, {}).get('optimal_threshold', 0.5)

        # Get predictions
        predictions, prob_dict = get_model_predictions_from_probabilities(
            pipeline,
            features_dict,
            feature_names,
            optimal_threshold,
            top_k=20  # Get top 20 from each model
        )

        model_predictions[model_name] = predictions
        model_probabilities[model_name] = prob_dict

        print(f"    {model_name}: {len(predictions)} predictions (threshold={optimal_threshold:.4f})")

    # Analyze agreement
    print(f"\n  Analyzing model agreement...")
    agreement_analysis = analyze_ensemble_agreement(
        model_predictions,
        model_probabilities
    )
    display_agreement_analysis(agreement_analysis)

    # Create ensemble voter
    # Use AUC-ROC scores as confidence weights for weighted voting
    confidence_weights = None
    if strategy == 'weighted':
        confidence_weights = {}
        for model_name, model_info in models_dict.items():
            config = model_info['config']
            model_display_name = config['name']
            auc_roc = all_metrics.get(model_display_name, {}).get('auc_val', 0.5)
            confidence_weights[model_name] = auc_roc

    voter = EnsembleVoter(
        strategy=strategy,
        min_votes=min_votes,
        confidence_weights=confidence_weights
    )

    # Generate ensemble predictions
    print(f"\n  Applying {strategy} voting...")
    ensemble_predictions, voting_details = voter.vote(
        model_predictions,
        model_probabilities,
        top_k=top_k
    )

    # Display results
    display_voting_results(
        ensemble_predictions,
        voting_details,
        list(models_dict.keys()),
        top_n=15
    )

    return {
        'ensemble_predictions': ensemble_predictions,
        'voting_details': voting_details,
        'model_predictions': model_predictions,
        'model_probabilities': model_probabilities,
        'agreement_analysis': agreement_analysis,
        'strategy': strategy,
        'min_votes': min_votes if strategy == 'threshold' else None
    }


def main():
    """Main entry point for ensemble prediction."""
    parser = argparse.ArgumentParser(
        description='Generate ensemble predictions from multiple trained models'
    )
    parser.add_argument(
        '--strategy',
        type=str,
        default='majority',
        choices=['majority', 'threshold', 'weighted', 'unanimous'],
        help='Voting strategy to use (default: majority)'
    )
    parser.add_argument(
        '--min-votes',
        type=int,
        default=2,
        help='Minimum votes required for threshold strategy (default: 2)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=10,
        help='Maximum number of ensemble predictions (default: 10)'
    )

    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"  ENSEMBLE PREDICTION - {args.strategy.upper()} VOTING")
    print(f"{'='*80}")

    print(f"\n⚠️  This script requires trained models from quickpick.py")
    print(f"⚠️  Run 'python quickpick.py' first to train models")
    print(f"\n💡 For integration, use the ensemble voting functions in your code:")
    print(f"    from ml_lotto.prediction.ensemble import EnsembleVoter")

    return 0


if __name__ == '__main__':
    sys.exit(main())
