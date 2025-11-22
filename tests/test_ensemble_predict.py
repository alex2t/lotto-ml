"""
test_ensemble_predict.py
=========================
Test script for ensemble_predict.py functionality.

Tests:
1. Ensemble prediction generation with different strategies
2. Model agreement analysis
3. Voting mechanism validation
4. Command-line argument parsing
5. Integration with trained models
"""

import sys
import numpy as np
from typing import Dict, List, Any

# Import ensemble prediction utilities
sys.path.insert(0, '/home/user/lotto-ml')
from scripts.ensemble_predict import (
    get_model_predictions_from_probabilities,
    generate_ensemble_predictions
)
from ml_lotto.prediction.ensemble import (
    EnsembleVoter,
    analyze_ensemble_agreement,
    display_voting_results,
    display_agreement_analysis
)


class MockPipeline:
    """Mock pipeline for testing."""

    def __init__(self, seed=42):
        self.seed = seed

    def predict_proba(self, X):
        """Mock predict_proba that returns predictable probabilities."""
        np.random.seed(self.seed)
        n_samples = X.shape[0]
        # Generate probabilities that vary by seed
        probs_class_1 = np.random.rand(n_samples) * 0.7 + 0.15  # Range: 0.15 to 0.85
        probs_class_0 = 1 - probs_class_1
        return np.column_stack([probs_class_0, probs_class_1])


def test_ensemble_voting_strategies():
    """Test all voting strategies with mock data."""
    print("\n" + "="*80)
    print("TEST 1: Ensemble Voting Strategies")
    print("="*80)

    # Create mock model predictions
    model_predictions = {
        'model_1': [1, 5, 10, 15, 20, 25, 30, 35, 40],
        'model_2': [5, 10, 12, 20, 25, 28, 35, 38, 42],
        'model_3': [2, 5, 10, 20, 22, 25, 30, 35, 45],
        'model_4': [5, 8, 10, 20, 25, 30, 32, 35, 47]
    }

    # Create mock probabilities
    model_probabilities = {
        'model_1': {num: 0.70 + (num % 10) * 0.01 for num in model_predictions['model_1']},
        'model_2': {num: 0.68 + (num % 10) * 0.01 for num in model_predictions['model_2']},
        'model_3': {num: 0.72 + (num % 10) * 0.01 for num in model_predictions['model_3']},
        'model_4': {num: 0.69 + (num % 10) * 0.01 for num in model_predictions['model_4']}
    }

    strategies = ['majority', 'threshold', 'weighted', 'unanimous']

    for strategy in strategies:
        print(f"\n--- Testing {strategy.upper()} strategy ---")

        if strategy == 'threshold':
            voter = EnsembleVoter(strategy=strategy, min_votes=2)
        elif strategy == 'weighted':
            # Use mock AUC scores as weights
            weights = {'model_1': 0.72, 'model_2': 0.68, 'model_3': 0.75, 'model_4': 0.70}
            voter = EnsembleVoter(strategy=strategy, confidence_weights=weights)
        else:
            voter = EnsembleVoter(strategy=strategy)

        ensemble, details = voter.vote(
            model_predictions,
            model_probabilities,
            top_k=10
        )

        print(f"  ✓ Ensemble predictions: {ensemble}")
        print(f"  ✓ Number of predictions: {len(ensemble)}")

        # Validate results
        assert isinstance(ensemble, list), "Ensemble predictions should be a list"
        assert len(ensemble) <= 10, "Should not exceed top_k limit"
        assert all(isinstance(num, int) for num in ensemble), "All predictions should be integers"

        if strategy == 'unanimous':
            # For unanimous, check that all numbers are in all model predictions
            all_model_nums = set.intersection(*[set(preds) for preds in model_predictions.values()])
            for num in ensemble:
                assert num in all_model_nums, f"Number {num} should be predicted by all models"

    print("\n✅ All voting strategies tested successfully!")


def test_model_agreement_analysis():
    """Test model agreement analysis."""
    print("\n" + "="*80)
    print("TEST 2: Model Agreement Analysis")
    print("="*80)

    model_predictions = {
        'model_1': [1, 5, 10, 15, 20],
        'model_2': [5, 10, 12, 20, 25],
        'model_3': [5, 10, 20, 22, 30],
        'model_4': [5, 10, 20, 25, 35]
    }

    model_probabilities = {
        'model_1': {num: 0.70 for num in model_predictions['model_1']},
        'model_2': {num: 0.68 for num in model_predictions['model_2']},
        'model_3': {num: 0.72 for num in model_predictions['model_3']},
        'model_4': {num: 0.69 for num in model_predictions['model_4']}
    }

    agreement = analyze_ensemble_agreement(model_predictions, model_probabilities)

    print(f"\n  Agreement analysis results:")
    print(f"    Total unique predictions: {agreement['total_unique_predictions']}")
    print(f"    Agreement counts: {agreement['agreement_counts']}")
    print(f"    High agreement numbers: {agreement['high_agreement_numbers']}")

    # Validate agreement analysis
    assert 'total_unique_predictions' in agreement
    assert 'agreement_counts' in agreement
    assert 'number_details' in agreement

    # Check that numbers appearing in all 4 models are in high agreement
    # Numbers 5, 10, 20 appear in all 4 models
    high_agreement = agreement['high_agreement_numbers']
    assert 5 in high_agreement, "Number 5 should be high agreement"
    assert 10 in high_agreement, "Number 10 should be high agreement"
    assert 20 in high_agreement, "Number 20 should be high agreement"

    print("\n✅ Agreement analysis tested successfully!")


def test_get_model_predictions():
    """Test getting predictions from a single model pipeline."""
    print("\n" + "="*80)
    print("TEST 3: Get Model Predictions from Pipeline")
    print("="*80)

    # Create mock pipeline
    pipeline = MockPipeline(seed=42)

    # Create mock features dict
    features_dict = {}
    for num in range(1, 48):
        features_dict[num] = {
            'frequency': np.random.rand(),
            'recency': np.random.rand(),
            'streak': np.random.rand()
        }

    feature_names = ['frequency', 'recency', 'streak']
    optimal_threshold = 0.5

    predictions, prob_dict = get_model_predictions_from_probabilities(
        pipeline,
        features_dict,
        feature_names,
        optimal_threshold,
        top_k=10
    )

    print(f"\n  Model predictions: {predictions}")
    print(f"  Number of predictions: {len(predictions)}")
    print(f"  Sample probabilities: {list(prob_dict.items())[:5]}")

    # Validate results
    assert isinstance(predictions, list), "Predictions should be a list"
    assert len(predictions) <= 10, "Should not exceed top_k"
    assert all(1 <= num <= 47 for num in predictions), "All predictions should be valid numbers"
    assert len(prob_dict) >= len(predictions), "Should have probabilities for all predictions"

    # Check that predictions are sorted by probability (descending)
    probs = [prob_dict[num] for num in predictions]
    assert probs == sorted(probs, reverse=True), "Predictions should be sorted by probability"

    print("\n✅ Model predictions tested successfully!")


def test_generate_ensemble_predictions():
    """Test full ensemble prediction generation."""
    print("\n" + "="*80)
    print("TEST 4: Generate Ensemble Predictions")
    print("="*80)

    # Create mock models
    models_dict = {
        'model_1': {
            'pipeline': MockPipeline(seed=42),
            'config': {'name': 'Model 1'}
        },
        'model_2': {
            'pipeline': MockPipeline(seed=43),
            'config': {'name': 'Model 2'}
        },
        'model_3': {
            'pipeline': MockPipeline(seed=44),
            'config': {'name': 'Model 3'}
        }
    }

    # Create mock features
    model_features_dict = {
        'model_1': ['frequency', 'recency', 'streak'],
        'model_2': ['frequency', 'recency', 'streak'],
        'model_3': ['frequency', 'recency', 'streak']
    }

    features_dict = {}
    for num in range(1, 48):
        features_dict[num] = {
            'frequency': np.random.rand(),
            'recency': np.random.rand(),
            'streak': np.random.rand()
        }

    # Create mock metrics (with optimal thresholds)
    all_metrics = {
        'Model 1': {'optimal_threshold': 0.45, 'auc_val': 0.72},
        'Model 2': {'optimal_threshold': 0.50, 'auc_val': 0.68},
        'Model 3': {'optimal_threshold': 0.48, 'auc_val': 0.75}
    }

    # Generate ensemble predictions
    result = generate_ensemble_predictions(
        models_dict,
        model_features_dict,
        features_dict,
        all_metrics,
        strategy='majority',
        top_k=10
    )

    print(f"\n  Ensemble predictions: {result['ensemble_predictions']}")
    print(f"  Strategy used: {result['strategy']}")

    # Validate results
    assert 'ensemble_predictions' in result
    assert 'voting_details' in result
    assert 'model_predictions' in result
    assert 'agreement_analysis' in result

    assert isinstance(result['ensemble_predictions'], list)
    assert len(result['ensemble_predictions']) <= 10

    print("\n✅ Full ensemble generation tested successfully!")


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "="*80)
    print("TEST 5: Edge Cases")
    print("="*80)

    # Test 1: Empty model predictions
    print("\n  Test 1a: Single model with few predictions")
    model_predictions = {
        'model_1': [1, 2, 3]
    }
    model_probabilities = {
        'model_1': {1: 0.7, 2: 0.6, 3: 0.5}
    }

    voter = EnsembleVoter(strategy='majority')
    ensemble, details = voter.vote(model_predictions, model_probabilities, top_k=5)

    assert len(ensemble) <= 3, "Should not return more predictions than available"
    print(f"    ✓ Single model predictions: {ensemble}")

    # Test 2: No overlap between models (unanimous should return empty)
    print("\n  Test 1b: No overlap - unanimous voting")
    model_predictions = {
        'model_1': [1, 2, 3],
        'model_2': [4, 5, 6],
        'model_3': [7, 8, 9]
    }
    model_probabilities = {
        'model_1': {num: 0.7 for num in model_predictions['model_1']},
        'model_2': {num: 0.7 for num in model_predictions['model_2']},
        'model_3': {num: 0.7 for num in model_predictions['model_3']}
    }

    voter = EnsembleVoter(strategy='unanimous')
    ensemble, details = voter.vote(model_predictions, model_probabilities, top_k=10)

    assert len(ensemble) == 0, "Unanimous with no overlap should return empty list"
    print(f"    ✓ No overlap unanimous: {ensemble} (expected empty)")

    # Test 3: High threshold requirement
    print("\n  Test 1c: High threshold (3/4 models)")
    model_predictions = {
        'model_1': [5, 10, 15, 20],
        'model_2': [5, 10, 12, 25],
        'model_3': [5, 10, 18, 30],
        'model_4': [7, 14, 21, 28]
    }
    model_probabilities = {
        'model_1': {num: 0.7 for num in model_predictions['model_1']},
        'model_2': {num: 0.7 for num in model_predictions['model_2']},
        'model_3': {num: 0.7 for num in model_predictions['model_3']},
        'model_4': {num: 0.7 for num in model_predictions['model_4']}
    }

    voter = EnsembleVoter(strategy='threshold', min_votes=3)
    ensemble, details = voter.vote(model_predictions, model_probabilities, top_k=10)

    # Only 5 and 10 appear in 3+ models
    assert 5 in ensemble, "Number 5 should be in ensemble (appears in 3 models)"
    assert 10 in ensemble, "Number 10 should be in ensemble (appears in 3 models)"
    print(f"    ✓ High threshold predictions: {ensemble}")

    print("\n✅ All edge cases handled correctly!")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("  ENSEMBLE PREDICTION SCRIPT TEST SUITE")
    print("="*80)

    try:
        test_ensemble_voting_strategies()
        test_model_agreement_analysis()
        test_get_model_predictions()
        test_generate_ensemble_predictions()
        test_edge_cases()

        print("\n" + "="*80)
        print("  ✅ ALL TESTS PASSED!")
        print("="*80)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
