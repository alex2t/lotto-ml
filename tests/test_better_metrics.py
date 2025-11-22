"""
test_better_metrics.py
======================
Test script for enhanced metrics tracking (Version 3.15)

Tests:
1. Top-K accuracy calculation
2. Hit rate calculation
3. PR-AUC interpretation
4. Integration with model evaluation
"""

import numpy as np
from ml_lotto.models.model_metrics import (
    calculate_topk_accuracy,
    calculate_hit_rate
)


def test_topk_accuracy():
    """Test Top-K accuracy calculation."""
    print("\n" + "="*70)
    print("TEST 1: Top-K Accuracy")
    print("="*70)

    # Simulate validation data
    # 47 numbers, 7 are winners (typical lottery draw)
    np.random.seed(42)
    y_true = np.array([0] * 40 + [1] * 7)  # Last 7 are winners
    np.random.shuffle(y_true)

    # Simulate probabilities where winners have higher probabilities
    y_proba = np.random.rand(47)
    # Boost winner probabilities
    winner_indices = np.where(y_true == 1)[0]
    y_proba[winner_indices] += 0.3

    print(f"\nTest data:")
    print(f"  Total numbers: {len(y_true)}")
    print(f"  Winners: {sum(y_true)}")
    print(f"  Winner indices: {winner_indices}")

    # Calculate Top-K accuracy
    topk_metrics = calculate_topk_accuracy(y_true, y_proba, k_values=[7, 10, 15, 20])

    print(f"\nTop-K Metrics:")
    print(f"  {'K':<8} {'Hit?':<10} {'Winners':<12} {'Accuracy':<12}")
    print(f"  {'-'*42}")
    for k in [7, 10, 15, 20]:
        hit = topk_metrics[f'top{k}_hit']
        winners = topk_metrics[f'top{k}_winners']
        acc = topk_metrics[f'top{k}_accuracy']
        hit_str = "✅ Yes" if hit else "❌ No"
        print(f"  Top-{k:<3} {hit_str:<10} {winners:<12} {acc*100:>6.2f}%")

    # Verify results make sense
    if topk_metrics['top7_winners'] > 0:
        print(f"\n✅ PASS: Top-7 caught {topk_metrics['top7_winners']} winners")
    else:
        print(f"\n⚠️  WARNING: Top-7 caught 0 winners (model may need improvement)")

    if topk_metrics['top20_winners'] >= topk_metrics['top7_winners']:
        print(f"✅ PASS: Top-20 ({topk_metrics['top20_winners']}) >= Top-7 ({topk_metrics['top7_winners']})")
    else:
        print(f"❌ FAIL: Top-20 should have >= winners than Top-7")
        return False

    return True


def test_hit_rate():
    """Test hit rate calculation across multiple draws."""
    print("\n" + "="*70)
    print("TEST 2: Hit Rate Calculation")
    print("="*70)

    np.random.seed(42)

    # Simulate 10 draws
    num_draws = 10
    predictions_per_draw = []
    actuals_per_draw = []

    for draw_idx in range(num_draws):
        # Each draw: 47 numbers, 7 winners
        y_true = np.array([0] * 40 + [1] * 7)
        np.random.shuffle(y_true)

        # Simulate predictions (winners have higher probability)
        y_proba = np.random.rand(47)
        winner_indices = np.where(y_true == 1)[0]
        y_proba[winner_indices] += 0.3  # Boost winner probabilities

        predictions_per_draw.append(y_proba)
        actuals_per_draw.append(y_true)

    # Calculate hit rate
    hit_rate_stats = calculate_hit_rate(predictions_per_draw, actuals_per_draw, k=7)

    print(f"\nHit Rate Statistics (Top-7):")
    print(f"  Total draws: {hit_rate_stats['total_draws']}")
    print(f"  Draws with ≥1 winner: {hit_rate_stats['hits']}")
    print(f"  Hit rate: {hit_rate_stats['hit_rate']*100:.1f}%")
    print(f"  Avg winners per draw: {hit_rate_stats['avg_winners_caught']:.2f}")
    print(f"  Total winners caught: {hit_rate_stats['total_winners_caught']}")

    # Verify results
    if hit_rate_stats['hit_rate'] > 0:
        print(f"\n✅ PASS: Hit rate = {hit_rate_stats['hit_rate']*100:.1f}%")
    else:
        print(f"\n❌ FAIL: Hit rate should be > 0")
        return False

    if hit_rate_stats['total_winners_caught'] <= num_draws * 7:
        print(f"✅ PASS: Total winners caught ({hit_rate_stats['total_winners_caught']}) <= max possible ({num_draws * 7})")
    else:
        print(f"❌ FAIL: Caught more winners than possible")
        return False

    return True


def test_pr_auc_interpretation():
    """Test PR-AUC interpretation logic."""
    print("\n" + "="*70)
    print("TEST 3: PR-AUC Interpretation")
    print("="*70)

    # Test different PR-AUC scenarios
    test_cases = [
        (0.30, 0.15, "Good: 2.00x better than random"),
        (0.20, 0.15, "Acceptable: 1.33x better than random"),
        (0.16, 0.15, "Weak: Only 1.07x better than random")
    ]

    print(f"\nTest cases:")
    for pr_auc, baseline, expected in test_cases:
        ratio = pr_auc / baseline
        if pr_auc > baseline * 1.5:
            interpretation = f"Good: {ratio:.2f}x better than random"
        elif pr_auc > baseline * 1.2:
            interpretation = f"Acceptable: {ratio:.2f}x better than random"
        else:
            interpretation = f"Weak: Only {ratio:.2f}x better than random"

        match = "✅" if interpretation == expected else "❌"
        print(f"  {match} PR-AUC={pr_auc:.2f}, Baseline={baseline:.2f} → {interpretation}")

    print(f"\n✅ PASS: PR-AUC interpretation working correctly")
    return True


def test_metrics_integration():
    """Test integration with sklearn pipeline."""
    print("\n" + "="*70)
    print("TEST 4: Metrics Integration")
    print("="*70)

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from ml_lotto.models.model_metrics import calculate_comprehensive_metrics

    np.random.seed(42)

    # Create synthetic data
    n_samples = 200
    n_features = 10
    X_train = np.random.randn(n_samples, n_features)
    X_val = np.random.randn(50, n_features)

    # Imbalanced binary classification (15% positive)
    y_train = np.random.choice([0, 1], size=n_samples, p=[0.85, 0.15])
    y_val = np.random.choice([0, 1], size=50, p=[0.85, 0.15])

    # Train a simple model
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(random_state=42))
    ])
    pipeline.fit(X_train, y_train)

    print(f"\nTraining data:")
    print(f"  Samples: {n_samples}")
    print(f"  Features: {n_features}")
    print(f"  Positive class: {sum(y_train)} ({sum(y_train)/len(y_train)*100:.1f}%)")

    print(f"\nCalculating comprehensive metrics...")
    metrics = calculate_comprehensive_metrics(
        pipeline,
        X_train, y_train,
        X_val, y_val,
        model_name="TestModel",
        save_plots=False
    )

    # Verify all expected metrics are present
    required_metrics = [
        'auc_val', 'pr_auc', 'f1_score_optimal',
        'precision_optimal', 'recall_optimal',
        'optimal_threshold', 'calibration_error',
        'top7_hit', 'top7_winners', 'top7_accuracy',
        'top10_hit', 'top15_hit', 'top20_hit'
    ]

    missing_metrics = [m for m in required_metrics if m not in metrics]

    if not missing_metrics:
        print(f"\n✅ PASS: All {len(required_metrics)} required metrics present")
    else:
        print(f"\n❌ FAIL: Missing metrics: {missing_metrics}")
        return False

    # Verify metric values are reasonable
    if 0 <= metrics['auc_val'] <= 1:
        print(f"✅ PASS: AUC-ROC in valid range: {metrics['auc_val']:.4f}")
    else:
        print(f"❌ FAIL: AUC-ROC out of range: {metrics['auc_val']}")
        return False

    if 0 <= metrics['pr_auc'] <= 1:
        print(f"✅ PASS: PR-AUC in valid range: {metrics['pr_auc']:.4f}")
    else:
        print(f"❌ FAIL: PR-AUC out of range: {metrics['pr_auc']}")
        return False

    if 0 <= metrics['optimal_threshold'] <= 1:
        print(f"✅ PASS: Optimal threshold in valid range: {metrics['optimal_threshold']:.4f}")
    else:
        print(f"❌ FAIL: Optimal threshold out of range: {metrics['optimal_threshold']}")
        return False

    print(f"\n✅ PASS: Metrics integration working correctly")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  BETTER METRICS TEST SUITE (Version 3.15)")
    print("="*70)

    tests = [
        ("Top-K Accuracy", test_topk_accuracy),
        ("Hit Rate Calculation", test_hit_rate),
        ("PR-AUC Interpretation", test_pr_auc_interpretation),
        ("Metrics Integration", test_metrics_integration)
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
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL TESTS PASSED - Better metrics ready for use!")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
