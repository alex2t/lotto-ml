"""
test_ensemble.py
================
Test script to verify ensemble voting implementation.

Tests:
1. Basic ensemble voting with simulated model predictions
2. All voting strategies (majority, threshold, weighted, unanimous)
3. Agreement analysis
4. Edge cases
"""

import sys
from ml_lotto.prediction.ensemble import (
    EnsembleVoter,
    analyze_ensemble_agreement,
    display_voting_results,
    display_agreement_analysis
)


def test_basic_voting():
    """Test basic ensemble voting with simulated predictions."""
    print("\n" + "="*80)
    print("TEST 1: Basic Ensemble Voting")
    print("="*80)

    # Simulate 4 model predictions
    model_predictions = {
        'model_1': [1, 5, 10, 15, 20, 25, 30],
        'model_2': [5, 10, 12, 20, 25, 28, 35],
        'model_3': [2, 5, 10, 20, 22, 25, 30],
        'model_4': [5, 8, 10, 20, 25, 30, 32]
    }

    # Simulate probabilities
    model_probabilities = {
        'model_1': {1: 0.75, 5: 0.82, 10: 0.68, 15: 0.61, 20: 0.79, 25: 0.71, 30: 0.65},
        'model_2': {5: 0.79, 10: 0.71, 12: 0.65, 20: 0.77, 25: 0.73, 28: 0.62, 35: 0.58},
        'model_3': {2: 0.66, 5: 0.81, 10: 0.69, 20: 0.78, 22: 0.64, 25: 0.72, 30: 0.67},
        'model_4': {5: 0.80, 8: 0.63, 10: 0.70, 20: 0.76, 25: 0.74, 30: 0.68, 32: 0.60}
    }

    # Test majority voting
    voter = EnsembleVoter(strategy='majority')
    ensemble, details = voter.vote(model_predictions, model_probabilities)

    print(f"\n✓ Ensemble predictions (majority): {ensemble}")
    print(f"\nVoting details:")
    for num in ensemble:
        d = details[num]
        print(f"  #{num}: {d['votes']} votes ({d['vote_percentage']:.1f}%) "
              f"by {[m.split('_')[1] for m in d['models']]}, avg_prob={d['avg_prob']:.3f}")

    # Expected: Numbers with >2 votes (majority of 4)
    expected_majority = {5, 10, 20, 25, 30}  # All have 3-4 votes
    if set(ensemble) == expected_majority:
        print(f"\n✅ PASS: Majority voting working correctly")
    else:
        print(f"\n❌ FAIL: Expected {expected_majority}, got {set(ensemble)}")
        return False

    return True


def test_all_strategies():
    """Test all voting strategies."""
    print("\n" + "="*80)
    print("TEST 2: All Voting Strategies")
    print("="*80)

    model_predictions = {
        'model_1': [1, 5, 10, 15, 20, 25, 30],
        'model_2': [5, 10, 12, 20, 25, 28, 35],
        'model_3': [2, 5, 10, 20, 22, 25, 30],
        'model_4': [5, 8, 10, 20, 25, 30, 32]
    }

    # Test unanimous voting
    print("\n--- Unanimous Voting (all 4 models must agree) ---")
    voter_unanimous = EnsembleVoter(strategy='unanimous')
    ensemble_unanimous, _ = voter_unanimous.vote(model_predictions)
    print(f"Unanimous predictions: {ensemble_unanimous}")
    expected_unanimous = [5, 10, 20, 25]  # Only numbers all 4 models agree on
    if ensemble_unanimous == expected_unanimous:
        print("✅ PASS: Unanimous voting correct")
    else:
        print(f"❌ FAIL: Expected {expected_unanimous}, got {ensemble_unanimous}")
        return False

    # Test threshold voting (min_votes=2)
    print("\n--- Threshold Voting (min_votes=2) ---")
    voter_threshold = EnsembleVoter(strategy='threshold', min_votes=2)
    ensemble_threshold, _ = voter_threshold.vote(model_predictions)
    print(f"Threshold predictions (≥2 votes): {ensemble_threshold}")
    # Should include all numbers with 2+ votes
    if len(ensemble_threshold) > len(ensemble_unanimous):
        print("✅ PASS: Threshold voting working (more predictions than unanimous)")
    else:
        print("❌ FAIL: Threshold should have more predictions than unanimous")
        return False

    # Test weighted voting
    print("\n--- Weighted Voting (by model confidence) ---")
    confidence_weights = {
        'model_1': 0.55,  # Best model
        'model_2': 0.52,
        'model_3': 0.51,
        'model_4': 0.50   # Weakest model
    }
    voter_weighted = EnsembleVoter(strategy='weighted', confidence_weights=confidence_weights)
    ensemble_weighted, _ = voter_weighted.vote(model_predictions)
    print(f"Weighted predictions: {ensemble_weighted}")
    print("✅ PASS: Weighted voting executed successfully")

    return True


def test_agreement_analysis():
    """Test agreement analysis."""
    print("\n" + "="*80)
    print("TEST 3: Agreement Analysis")
    print("="*80)

    model_predictions = {
        'model_1': [1, 5, 10, 15, 20, 25, 30],
        'model_2': [5, 10, 12, 20, 25, 28, 35],
        'model_3': [2, 5, 10, 20, 22, 25, 30],
        'model_4': [5, 8, 10, 20, 25, 30, 32]
    }

    model_probabilities = {
        'model_1': {1: 0.75, 5: 0.82, 10: 0.68, 15: 0.61, 20: 0.79, 25: 0.71, 30: 0.65},
        'model_2': {5: 0.79, 10: 0.71, 12: 0.65, 20: 0.77, 25: 0.73, 28: 0.62, 35: 0.58},
        'model_3': {2: 0.66, 5: 0.81, 10: 0.69, 20: 0.78, 22: 0.64, 25: 0.72, 30: 0.67},
        'model_4': {5: 0.80, 8: 0.63, 10: 0.70, 20: 0.76, 25: 0.74, 30: 0.68, 32: 0.60}
    }

    analysis = analyze_ensemble_agreement(model_predictions, model_probabilities)

    print(f"\nTotal models: {analysis['total_models']}")
    print(f"Unique predictions: {analysis['unique_predictions']}")
    print(f"Unanimous: {analysis['unanimous']}")
    print(f"High agreement: {analysis['high_agreement']}")
    print(f"Majority: {analysis['majority']}")

    # Verify unanimous predictions
    expected_unanimous = [5, 10, 20, 25]
    if analysis['unanimous'] == expected_unanimous:
        print(f"\n✅ PASS: Agreement analysis correct (unanimous={expected_unanimous})")
    else:
        print(f"\n❌ FAIL: Expected unanimous={expected_unanimous}, got {analysis['unanimous']}")
        return False

    return True


def test_edge_cases():
    """Test edge cases."""
    print("\n" + "="*80)
    print("TEST 4: Edge Cases")
    print("="*80)

    # Case 1: Single model
    print("\n--- Single Model ---")
    single_model = {'model_1': [1, 5, 10]}
    voter = EnsembleVoter(strategy='majority')
    ensemble, _ = voter.vote(single_model)
    print(f"Single model result: {ensemble}")
    if set(ensemble) == {1, 5, 10}:
        print("✅ PASS: Single model handled correctly")
    else:
        print(f"❌ FAIL: Single model should return all predictions, got {set(ensemble)}")
        return False

    # Case 2: No common predictions
    print("\n--- No Common Predictions ---")
    no_overlap = {
        'model_1': [1, 2, 3],
        'model_2': [4, 5, 6],
        'model_3': [7, 8, 9]
    }
    voter_unanimous = EnsembleVoter(strategy='unanimous')
    ensemble_unanimous, _ = voter_unanimous.vote(no_overlap)
    print(f"Unanimous with no overlap: {ensemble_unanimous}")
    if ensemble_unanimous == []:
        print("✅ PASS: No overlap handled correctly")
    else:
        print("❌ FAIL: Should return empty list when no overlap")
        return False

    # Case 3: All models agree
    print("\n--- All Models Agree ---")
    all_agree = {
        'model_1': [5, 10, 15],
        'model_2': [5, 10, 15],
        'model_3': [5, 10, 15]
    }
    voter = EnsembleVoter(strategy='majority')
    ensemble, details = voter.vote(all_agree)
    print(f"All agree result: {ensemble}")
    if set(ensemble) == {5, 10, 15} and all(d['votes'] == 3 for d in details.values()):
        print("✅ PASS: Perfect agreement handled correctly")
    else:
        print(f"❌ FAIL: All models agree case failed - ensemble={set(ensemble)}, all votes=3? {all(d['votes'] == 3 for d in details.values())}")
        return False

    return True


def test_display_functions():
    """Test display functions."""
    print("\n" + "="*80)
    print("TEST 5: Display Functions")
    print("="*80)

    model_predictions = {
        'model_1': [1, 5, 10, 15, 20],
        'model_2': [5, 10, 12, 20, 25],
        'model_3': [2, 5, 10, 20, 22]
    }

    model_probabilities = {
        'model_1': {1: 0.75, 5: 0.82, 10: 0.68, 15: 0.61, 20: 0.79},
        'model_2': {5: 0.79, 10: 0.71, 12: 0.65, 20: 0.77, 25: 0.73},
        'model_3': {2: 0.66, 5: 0.81, 10: 0.69, 20: 0.78, 22: 0.64}
    }

    # Test voting results display
    voter = EnsembleVoter(strategy='majority')
    ensemble, details = voter.vote(model_predictions, model_probabilities)

    print("\n--- Display Voting Results ---")
    display_voting_results(ensemble, details, list(model_predictions.keys()), top_n=10)

    # Test agreement analysis display
    print("\n--- Display Agreement Analysis ---")
    analysis = analyze_ensemble_agreement(model_predictions, model_probabilities)
    display_agreement_analysis(analysis)

    print("✅ PASS: Display functions executed successfully")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("  ENSEMBLE VOTING TEST SUITE")
    print("="*80)

    tests = [
        ("Basic Voting", test_basic_voting),
        ("All Strategies", test_all_strategies),
        ("Agreement Analysis", test_agreement_analysis),
        ("Edge Cases", test_edge_cases),
        ("Display Functions", test_display_functions)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL TESTS PASSED - Ensemble voting ready for use!")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
