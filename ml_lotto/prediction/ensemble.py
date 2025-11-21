"""
ensemble.py
===========
Ensemble voting strategies for combining predictions from multiple models.

VERSION: 1.0
- Majority voting (2+ models agree)
- Weighted voting (by model confidence)
- Unanimous voting (all models agree)
- Flexible threshold voting (N+ models agree)
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter


class EnsembleVoter:
    """
    Combines predictions from multiple models using various voting strategies.

    Strategies:
    - 'majority': Requires majority (>50%) of models to agree
    - 'weighted': Weights votes by model probabilities
    - 'unanimous': Requires all models to agree
    - 'threshold': Requires N+ models to agree (configurable)
    """

    def __init__(
        self,
        strategy: str = 'majority',
        min_votes: int = 2,
        confidence_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize ensemble voter.

        Args:
            strategy: Voting strategy ('majority', 'weighted', 'unanimous', 'threshold')
            min_votes: Minimum votes required for 'threshold' strategy
            confidence_weights: Optional model weights for 'weighted' strategy
                               Format: {'model_1': 0.3, 'model_2': 0.25, ...}
        """
        self.strategy = strategy
        self.min_votes = min_votes
        self.confidence_weights = confidence_weights or {}

        # Normalize weights if provided
        if self.confidence_weights:
            total_weight = sum(self.confidence_weights.values())
            self.confidence_weights = {
                k: v / total_weight for k, v in self.confidence_weights.items()
            }

    def vote(
        self,
        model_predictions: Dict[str, List[int]],
        model_probabilities: Optional[Dict[str, Dict[int, float]]] = None,
        top_k: Optional[int] = None
    ) -> Tuple[List[int], Dict[int, Dict[str, Any]]]:
        """
        Combine predictions from multiple models using voting strategy.

        Args:
            model_predictions: Dictionary mapping model_name -> list of predicted numbers
                              Example: {'model_1': [1, 5, 10], 'model_2': [5, 10, 15]}
            model_probabilities: Optional probabilities for each prediction
                                Format: {'model_1': {1: 0.8, 5: 0.7, ...}}
            top_k: Optional limit on number of predictions to return

        Returns:
            Tuple of (ensemble_predictions, voting_details)
            - ensemble_predictions: List of numbers selected by ensemble
            - voting_details: Dict mapping number -> voting information
              Format: {number: {'votes': 3, 'models': ['model_1', 'model_2'],
                               'avg_prob': 0.75, 'weighted_score': 0.8}}
        """
        if not model_predictions:
            return [], {}

        # Collect all candidate numbers
        all_candidates = set()
        for predictions in model_predictions.values():
            all_candidates.update(predictions)

        # Calculate voting details for each candidate
        voting_details = {}

        for number in all_candidates:
            # Count votes
            voting_models = [
                model for model, preds in model_predictions.items()
                if number in preds
            ]
            vote_count = len(voting_models)

            # Calculate average probability if available
            avg_prob = None
            if model_probabilities:
                probs = [
                    model_probabilities[model].get(number, 0.0)
                    for model in voting_models
                    if model in model_probabilities
                ]
                avg_prob = np.mean(probs) if probs else 0.0

            # Calculate weighted score
            weighted_score = vote_count
            if self.confidence_weights and voting_models:
                weighted_score = sum(
                    self.confidence_weights.get(model, 1.0 / len(model_predictions))
                    for model in voting_models
                )

            voting_details[number] = {
                'votes': vote_count,
                'models': voting_models,
                'avg_prob': avg_prob,
                'weighted_score': weighted_score,
                'vote_percentage': vote_count / len(model_predictions) * 100
            }

        # Apply voting strategy
        ensemble_predictions = self._apply_strategy(
            voting_details,
            len(model_predictions)
        )

        # Sort by voting score (votes or weighted score)
        if self.strategy == 'weighted' and self.confidence_weights:
            ensemble_predictions.sort(
                key=lambda x: voting_details[x]['weighted_score'],
                reverse=True
            )
        else:
            # Sort by vote count, then by average probability
            ensemble_predictions.sort(
                key=lambda x: (
                    voting_details[x]['votes'],
                    voting_details[x].get('avg_prob', 0)
                ),
                reverse=True
            )

        # Apply top_k limit if specified
        if top_k is not None:
            ensemble_predictions = ensemble_predictions[:top_k]

        return ensemble_predictions, voting_details

    def _apply_strategy(
        self,
        voting_details: Dict[int, Dict[str, Any]],
        total_models: int
    ) -> List[int]:
        """
        Apply voting strategy to filter predictions.

        Args:
            voting_details: Voting information for each number
            total_models: Total number of models

        Returns:
            List of numbers passing the voting threshold
        """
        selected = []

        for number, details in voting_details.items():
            if self.strategy == 'majority':
                # Requires > 50% of models
                if details['votes'] > total_models / 2:
                    selected.append(number)

            elif self.strategy == 'unanimous':
                # Requires all models
                if details['votes'] == total_models:
                    selected.append(number)

            elif self.strategy == 'threshold':
                # Requires min_votes or more
                if details['votes'] >= self.min_votes:
                    selected.append(number)

            elif self.strategy == 'weighted':
                # Requires weighted score above threshold
                threshold = 0.5  # Can be made configurable
                if details['weighted_score'] >= threshold:
                    selected.append(number)

            else:
                raise ValueError(f"Unknown voting strategy: {self.strategy}")

        return selected


def analyze_ensemble_agreement(
    model_predictions: Dict[str, List[int]],
    model_probabilities: Optional[Dict[str, Dict[int, float]]] = None
) -> Dict[str, Any]:
    """
    Analyze agreement between models without making predictions.

    Args:
        model_predictions: Dictionary mapping model_name -> list of predicted numbers
        model_probabilities: Optional probabilities for each prediction

    Returns:
        Dictionary with analysis statistics
    """
    if not model_predictions:
        return {}

    # Collect all predictions
    all_predictions = []
    for predictions in model_predictions.values():
        all_predictions.extend(predictions)

    # Count frequency
    prediction_counts = Counter(all_predictions)
    total_models = len(model_predictions)

    # Categorize by agreement level
    unanimous = [num for num, count in prediction_counts.items() if count == total_models]
    high_agreement = [num for num, count in prediction_counts.items()
                      if count >= total_models * 0.75 and count < total_models]
    majority = [num for num, count in prediction_counts.items()
                if count > total_models / 2 and count < total_models * 0.75]
    minority = [num for num, count in prediction_counts.items() if count <= total_models / 2]

    # Calculate overlap matrix
    overlap_matrix = {}
    model_names = list(model_predictions.keys())
    for i, model1 in enumerate(model_names):
        for model2 in model_names[i+1:]:
            overlap = set(model_predictions[model1]) & set(model_predictions[model2])
            overlap_pct = len(overlap) / len(set(model_predictions[model1]) | set(model_predictions[model2])) * 100
            overlap_matrix[f"{model1}_vs_{model2}"] = {
                'overlap_count': len(overlap),
                'overlap_percentage': overlap_pct,
                'common_numbers': sorted(overlap)
            }

    return {
        'total_models': total_models,
        'unique_predictions': len(prediction_counts),
        'unanimous': sorted(unanimous),
        'high_agreement': sorted(high_agreement),
        'majority': sorted(majority),
        'minority': sorted(minority),
        'overlap_matrix': overlap_matrix,
        'agreement_stats': {
            'unanimous_count': len(unanimous),
            'high_agreement_count': len(high_agreement),
            'majority_count': len(majority),
            'minority_count': len(minority)
        }
    }


def display_voting_results(
    ensemble_predictions: List[int],
    voting_details: Dict[int, Dict[str, Any]],
    model_names: List[str],
    top_n: int = 10
):
    """
    Display voting results in a formatted table.

    Args:
        ensemble_predictions: List of numbers selected by ensemble
        voting_details: Voting information for each number
        model_names: List of model names
        top_n: Number of top predictions to display
    """
    print(f"\n{'='*80}")
    print(f"  🎯 ENSEMBLE VOTING RESULTS")
    print(f"{'='*80}")

    if not ensemble_predictions:
        print("  ⚠️  No predictions passed the voting threshold")
        return

    print(f"\n  Total models: {len(model_names)}")
    print(f"  Ensemble predictions: {len(ensemble_predictions)}")
    print(f"\n  Top {min(top_n, len(ensemble_predictions))} Predictions:")
    print(f"  {'Rank':<6} {'Number':<8} {'Votes':<8} {'%':<10} {'Avg Prob':<12} {'Models':<30}")
    print(f"  {'-'*78}")

    for rank, number in enumerate(ensemble_predictions[:top_n], 1):
        details = voting_details[number]
        votes = details['votes']
        vote_pct = details['vote_percentage']
        avg_prob = details.get('avg_prob')
        models_str = ', '.join([m.split('_')[1] if '_' in m else m for m in details['models']])

        prob_str = f"{avg_prob:.4f}" if avg_prob is not None else "N/A"

        print(f"  {rank:<6} #{number:<7} {votes:<8} {vote_pct:<9.1f}% {prob_str:<12} {models_str:<30}")

    print(f"{'='*80}\n")


def display_agreement_analysis(analysis: Dict[str, Any]):
    """
    Display agreement analysis in a formatted report.

    Args:
        analysis: Output from analyze_ensemble_agreement()
    """
    print(f"\n{'='*80}")
    print(f"  📊 MODEL AGREEMENT ANALYSIS")
    print(f"{'='*80}")

    stats = analysis['agreement_stats']
    print(f"\n  Total models participating: {analysis['total_models']}")
    print(f"  Unique numbers predicted: {analysis['unique_predictions']}")

    print(f"\n  Agreement Levels:")
    print(f"    🟢 Unanimous ({analysis['total_models']}/{analysis['total_models']} models): {stats['unanimous_count']} numbers")
    if analysis['unanimous']:
        print(f"       Numbers: {analysis['unanimous']}")

    print(f"    🟡 High Agreement (≥75% models): {stats['high_agreement_count']} numbers")
    if analysis['high_agreement']:
        print(f"       Numbers: {analysis['high_agreement']}")

    print(f"    🟠 Majority (>50% models): {stats['majority_count']} numbers")
    if len(analysis['majority']) <= 10:
        print(f"       Numbers: {analysis['majority']}")
    else:
        print(f"       Numbers: {analysis['majority'][:10]} ... ({len(analysis['majority'])} total)")

    print(f"    🔴 Minority (≤50% models): {stats['minority_count']} numbers")

    print(f"\n  Pairwise Model Overlap:")
    for pair, overlap_info in analysis['overlap_matrix'].items():
        model1, model2 = pair.split('_vs_')
        print(f"    {model1} ∩ {model2}: {overlap_info['overlap_count']} numbers "
              f"({overlap_info['overlap_percentage']:.1f}% overlap)")

    print(f"{'='*80}\n")
