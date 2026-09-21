"""
model_metrics.py
================
Comprehensive model evaluation metrics for lottery prediction.

VERSION: 3.15 (Enhanced Metrics Edition)
- Added optimal threshold selection based on F1-score maximization
- Metrics calculated with both default (0.5) and optimal thresholds
- Enhanced reporting to show improvement from threshold optimization
- Added Top-K Accuracy tracking (lottery-specific metric)
- Prominent display of PR-AUC (better for imbalanced data)
- Hit rate calculation helper function

Includes:
- AUC-ROC curves
- Precision/Recall/F1
- Top-K Accuracy (lottery-specific)
- PR-AUC (Average Precision)
- Calibration curves
- Classification reports
- Threshold optimization
- Hit rate tracking
"""

import numpy as np
import pandas as pd
import matplotlib
# All figures are written to disk; an interactive backend is never needed and
# the Tk one crashes at interpreter shutdown from a non-main thread.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, Any, Tuple, Optional
from sklearn.metrics import (
    roc_curve,
    auc,
    precision_recall_curve,
    classification_report,
    confusion_matrix,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score
)
from sklearn.calibration import calibration_curve


def split_rows_into_draws(
    n_rows: int,
    numbers_per_draw: int = 47,
    groups: np.ndarray = None
) -> list:
    """
    Partition validation rows into per-draw index arrays.

    Rows are built draw-major, so a fixed block of `numbers_per_draw` rows is one
    draw. Models whose candidate pool varies by draw pass `groups` instead, a
    per-row draw index. Falls back to a single block when neither applies.

    Returns:
        List of index arrays, one per draw, in chronological order
    """
    if groups is not None:
        groups = np.asarray(groups)
        # np.unique sorts, and draw indices increase with time
        return [np.flatnonzero(groups == g) for g in np.unique(groups)]
    if numbers_per_draw and n_rows % numbers_per_draw == 0 and n_rows >= numbers_per_draw:
        return [np.arange(i, i + numbers_per_draw) for i in range(0, n_rows, numbers_per_draw)]
    return [np.arange(n_rows)]


def split_threshold_tuning_rows(
    n_rows: int,
    groups: np.ndarray = None,
    numbers_per_draw: int = 47
) -> tuple:
    """
    Split validation rows into a threshold-tuning half and a reporting half.

    A threshold picked by maximising F1 is fitted to whatever rows it sees, so those
    rows cannot also be the ones it is scored on. The split is chronological and on
    draw boundaries: the earlier draws tune, the later draws report.

    Returns:
        Tuple of (tune_indices, report_indices)
    """
    draws = split_rows_into_draws(n_rows, numbers_per_draw, groups)

    if len(draws) < 2:
        # No draw structure to split on; fall back to halving the rows
        cut = n_rows // 2
        return np.arange(cut), np.arange(cut, n_rows)

    cut = len(draws) // 2
    return np.concatenate(draws[:cut]), np.concatenate(draws[cut:])


def calculate_topk_accuracy(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    k_values: list = [7, 10, 15, 20],
    numbers_per_draw: int = 47,
    groups: np.ndarray = None
) -> Dict[str, float]:
    """
    Calculate Top-K accuracy: whether any of the top K predictions are actual winners.

    This is particularly meaningful for lottery prediction where we pick K numbers
    from predictions and check if any of them match the actual winning numbers.

    Args:
        y_true: True binary labels (1 = winning number, 0 = not winning)
        y_proba: Predicted probabilities for each number
        k_values: List of K values to test (default: [7, 10, 15, 20])
        numbers_per_draw: Rows per draw when every draw has the same candidate pool
        groups: Per-row draw index, for models whose candidate pool varies by draw
            (the bonus-to-main model scores only the numbers in the bonus window).
            Takes precedence over numbers_per_draw.

    Returns:
        Dictionary with Top-K accuracy for each K value
    """
    topk_metrics = {}
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    n = len(y_true)

    # Top-K is only meaningful WITHIN a draw, so score each draw separately and
    # average across draws rather than taking one global top-K over the flattened
    # validation set.
    draws = split_rows_into_draws(n, numbers_per_draw, groups)

    n_draws = len(draws)

    for k in k_values:
        caught = []
        expected = []
        k_effs = []
        for idx in draws:
            size = len(idx)
            k_eff = min(k, size)
            true_d = y_true[idx]
            # Rank within each draw; stable sort makes ties deterministic
            order = np.argsort(-y_proba[idx], kind='stable')[:k_eff]
            caught.append(float(true_d[order].sum()))
            expected.append(k_eff * float(true_d.sum()) / size if size else 0.0)
            k_effs.append(k_eff)

        avg_caught = float(np.mean(caught)) if caught else 0.0
        avg_expected = float(np.mean(expected)) if expected else 0.0
        avg_k = float(np.mean(k_effs)) if k_effs else 0.0

        topk_metrics[f'top{k}_hit'] = float(np.mean([c > 0 for c in caught])) if caught else 0.0
        topk_metrics[f'top{k}_winners'] = avg_caught
        topk_metrics[f'top{k}_expected'] = avg_expected
        topk_metrics[f'top{k}_lift'] = (avg_caught / avg_expected) if avg_expected > 0 else 0.0
        topk_metrics[f'top{k}_accuracy'] = avg_caught / avg_k if avg_k else 0.0

    topk_metrics['topk_n_draws'] = n_draws
    return topk_metrics


def calculate_hit_rate(
    predictions_per_draw: list,
    actuals_per_draw: list,
    k: int = 7
) -> Dict[str, Any]:
    """
    Calculate hit rate across multiple draws.

    Hit rate = percentage of draws where at least 1 of our top K predictions won.

    Args:
        predictions_per_draw: List of prediction arrays (probabilities) for each draw
        actuals_per_draw: List of actual binary labels for each draw
        k: Number of top predictions to consider (default: 7 for lottery)

    Returns:
        Dictionary with hit rate statistics
    """
    total_draws = len(predictions_per_draw)
    hits = 0
    total_winners_caught = 0

    for pred_proba, actual in zip(predictions_per_draw, actuals_per_draw):
        # Get top K predictions
        top_k_indices = np.argsort(pred_proba)[::-1][:k]

        # Check if any winners in top K
        if np.any(actual[top_k_indices] == 1):
            hits += 1

        # Count winners caught
        total_winners_caught += int(np.sum(actual[top_k_indices]))

    hit_rate = hits / total_draws if total_draws > 0 else 0
    avg_winners_per_draw = total_winners_caught / total_draws if total_draws > 0 else 0

    return {
        'hit_rate': hit_rate,
        'hits': hits,
        'total_draws': total_draws,
        'avg_winners_caught': avg_winners_per_draw,
        'total_winners_caught': total_winners_caught
    }


def calculate_comprehensive_metrics(
    pipeline: Any,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    model_name: str,
    save_plots: bool = True,
    output_dir: str = "model_metrics",
    topk_groups: np.ndarray = None
) -> Dict[str, Any]:
    """
    Calculate comprehensive evaluation metrics for a trained model.

    Args:
        pipeline: Trained sklearn pipeline
        X_train: Training features
        y_train: Training labels
        X_val: Validation features
        y_val: Validation labels
        model_name: Name of the model (for display and saving)
        save_plots: Whether to save visualization plots
        output_dir: Directory to save plots
        topk_groups: Per-row draw index for Top-K, when the candidate pool varies by draw

    Returns:
        Dictionary containing all metrics. Threshold-dependent entries (accuracy,
        precision, recall, F1, confusion matrices) are measured on the later half of
        the validation window, which the tuned threshold never saw; AUC, PR-AUC,
        Top-K and calibration use the whole window.
    """
    import os
    if save_plots:
        os.makedirs(output_dir, exist_ok=True)

    metrics = {}

    # ========================================
    # 1. PROBABILITY-BASED PREDICTIONS (DO THIS FIRST)
    # ========================================
    train_proba = pipeline.predict_proba(X_train)[:, 1]
    val_proba = pipeline.predict_proba(X_val)[:, 1]

    # ========================================
    # 2. FIND OPTIMAL THRESHOLD (EARLY)
    # ========================================
    # The threshold is fitted, so it cannot be scored on the rows it was fitted to.
    # Split the validation window chronologically: pick the threshold on the earlier
    # half, report every threshold-dependent number on the later half, which neither
    # the model nor the threshold has seen. Threshold-free metrics (AUC, PR-AUC,
    # Top-K, calibration) still use the whole window.
    tune_idx, report_idx = split_threshold_tuning_rows(len(y_val), topk_groups)

    y_tune, proba_tune = y_val[tune_idx], val_proba[tune_idx]
    y_report, proba_report = y_val[report_idx], val_proba[report_idx]

    precisions_temp, recalls_temp, pr_thresholds_temp = precision_recall_curve(y_tune, proba_tune)
    f1_scores_temp = 2 * (precisions_temp * recalls_temp) / (precisions_temp + recalls_temp + 1e-10)
    optimal_idx = np.argmax(f1_scores_temp)
    optimal_threshold = pr_thresholds_temp[optimal_idx] if optimal_idx < len(pr_thresholds_temp) else 0.5

    metrics['threshold_tune_rows'] = len(tune_idx)
    metrics['threshold_report_rows'] = len(report_idx)

    print(f"\n{'='*70}")
    print(f"  MODEL EVALUATION: {model_name}")
    print(f"{'='*70}")
    print(f"  Optimal Threshold: {optimal_threshold:.4f} "
          f"(maximizes F1 on {len(tune_idx)} tuning rows)")
    print(f"  Default Threshold: 0.5")
    print(f"  Operating-point metrics reported on {len(report_idx)} held-out rows")

    # ========================================
    # 3. BASIC ACCURACY METRICS - WITH BOTH THRESHOLDS
    # ========================================
    # Both operating points are scored on the same held-out rows, so the comparison
    # below is like-for-like.
    train_pred_default = pipeline.predict(X_train)
    val_pred_default = (proba_report >= 0.5).astype(int)

    # Optimal threshold
    train_pred_optimal = (train_proba >= optimal_threshold).astype(int)
    val_pred_optimal = (proba_report >= optimal_threshold).astype(int)

    train_accuracy_default = (train_pred_default == y_train).sum() / len(y_train)
    val_accuracy_default = (val_pred_default == y_report).sum() / len(y_report)

    train_accuracy_optimal = (train_pred_optimal == y_train).sum() / len(y_train)
    val_accuracy_optimal = (val_pred_optimal == y_report).sum() / len(y_report)

    # Store default threshold metrics (for backwards compatibility)
    metrics['train_accuracy'] = train_accuracy_default
    metrics['val_accuracy'] = val_accuracy_default
    metrics['overfitting_gap_accuracy'] = train_accuracy_default - val_accuracy_default

    # Store optimal threshold metrics
    metrics['train_accuracy_optimal'] = train_accuracy_optimal
    metrics['val_accuracy_optimal'] = val_accuracy_optimal
    metrics['optimal_threshold'] = optimal_threshold

    print(f"\n  Accuracy Comparison:")
    print(f"     {'Metric':<20} {'Default (0.5)':<15} {'Optimal':<15} {'Improvement':<15}")
    print(f"     {'-'*65}")
    print(f"     {'Train Accuracy':<20} {train_accuracy_default:<15.4f} {train_accuracy_optimal:<15.4f} {train_accuracy_optimal-train_accuracy_default:+.4f}")
    print(f"     {'Val Accuracy':<20} {val_accuracy_default:<15.4f} {val_accuracy_optimal:<15.4f} {val_accuracy_optimal-val_accuracy_default:+.4f}")

    # ========================================
    # 3. AUC-ROC METRICS
    # ========================================
    # Calculate ROC curve
    fpr_train, tpr_train, thresholds_train = roc_curve(y_train, train_proba)
    fpr_val, tpr_val, thresholds_val = roc_curve(y_val, val_proba)

    # Calculate AUC
    auc_train = auc(fpr_train, tpr_train)
    auc_val = auc(fpr_val, tpr_val)

    metrics['auc_train'] = auc_train
    metrics['auc_val'] = auc_val
    # Overfitting measured on a ranking metric. The 0.5-threshold accuracy gap is
    # meaningless here: no probability reaches 0.5, so both sides equal the
    # all-negative rate and the difference is always exactly zero.
    metrics['overfitting_gap_auc'] = auc_train - auc_val

    print(f"\n  AUC-ROC Scores:")
    print(f"     Train AUC: {auc_train:.4f}")
    print(f"     Val AUC:   {auc_val:.4f}")

    # Interpret AUC
    if auc_val < 0.6:
        print(f"     Poor discrimination (barely better than random)")
    elif auc_val < 0.7:
        print(f"     Acceptable discrimination")
    elif auc_val < 0.8:
        print(f"     Good discrimination")
    else:
        print(f"     Excellent discrimination")

    # Plot ROC curve
    if save_plots:
        plt.figure(figsize=(10, 6))
        plt.plot(fpr_train, tpr_train, label=f'Train (AUC = {auc_train:.3f})', linewidth=2)
        plt.plot(fpr_val, tpr_val, label=f'Validation (AUC = {auc_val:.3f})', linewidth=2)
        plt.plot([0, 1], [0, 1], 'k--', label='Random Chance (AUC = 0.5)', linewidth=1)
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate', fontsize=12)
        plt.title(f'ROC Curve - {model_name}', fontsize=14, fontweight='bold')
        plt.legend(loc="lower right", fontsize=11)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{model_name}_roc_curve.png", dpi=150)
        plt.close()
        print(f"     Saved ROC curve to {output_dir}/{model_name}_roc_curve.png")

    # ========================================
    # 4. PRECISION-RECALL METRICS - WITH BOTH THRESHOLDS
    # ========================================
    # Default threshold (0.5)
    precision_val_default = precision_score(y_report, val_pred_default, zero_division=0)
    recall_val_default = recall_score(y_report, val_pred_default, zero_division=0)
    f1_val_default = f1_score(y_report, val_pred_default, zero_division=0)

    # Optimal threshold
    precision_val_optimal = precision_score(y_report, val_pred_optimal, zero_division=0)
    recall_val_optimal = recall_score(y_report, val_pred_optimal, zero_division=0)
    f1_val_optimal = f1_score(y_report, val_pred_optimal, zero_division=0)

    # Average precision (independent of threshold) - PR-AUC
    avg_precision_val = average_precision_score(y_val, val_proba)

    # Store default threshold metrics (for backwards compatibility)
    metrics['precision'] = precision_val_default
    metrics['recall'] = recall_val_default
    metrics['f1_score'] = f1_val_default
    metrics['avg_precision'] = avg_precision_val
    metrics['pr_auc'] = avg_precision_val  # Alias for clarity
    # PR-AUC must be read against the positive-class rate, not against 0.5.
    # For this task the baseline is 7/47 (all positions) or 6/47 (main only).
    pr_baseline = float(sum(y_val)) / len(y_val) if len(y_val) else 0.0
    metrics['pr_auc_baseline'] = pr_baseline
    metrics['pr_auc_lift'] = (avg_precision_val / pr_baseline) if pr_baseline > 0 else 0.0

    # Store optimal threshold metrics
    metrics['precision_optimal'] = precision_val_optimal
    metrics['recall_optimal'] = recall_val_optimal
    metrics['f1_score_optimal'] = f1_val_optimal

    print(f"\n  Precision-Recall-F1 Comparison:")
    print(f"     {'Metric':<20} {'Default (0.5)':<15} {'Optimal':<15} {'Improvement':<15}")
    print(f"     {'-'*65}")
    print(f"     {'Precision':<20} {precision_val_default:<15.4f} {precision_val_optimal:<15.4f} {precision_val_optimal-precision_val_default:+.4f}")
    print(f"     {'Recall':<20} {recall_val_default:<15.4f} {recall_val_optimal:<15.4f} {recall_val_optimal-recall_val_default:+.4f}")
    print(f"     {'F1-Score':<20} {f1_val_default:<15.4f} {f1_val_optimal:<15.4f} {f1_val_optimal-f1_val_default:+.4f}")

    print(f"\n  PR-AUC (Precision-Recall AUC) - Better for Imbalanced Data:")
    print(f"     PR-AUC: {avg_precision_val:<15.4f} (threshold-independent)")

    # Interpret PR-AUC
    baseline_ratio = sum(y_val) / len(y_val)
    print(f"     Baseline (random): {baseline_ratio:.4f}")
    if avg_precision_val > baseline_ratio * 1.5:
        print(f"     Good: {(avg_precision_val/baseline_ratio):.2f}x better than random")
    elif avg_precision_val > baseline_ratio * 1.2:
        print(f"     Acceptable: {(avg_precision_val/baseline_ratio):.2f}x better than random")
    else:
        print(f"     Weak: Only {(avg_precision_val/baseline_ratio):.2f}x better than random")

    print(f"\n  Interpretation:")
    print(f"     Precision: When model predicts WIN, how often is it correct?")
    print(f"     Recall:    Of all actual WINS, how many did model catch?")
    print(f"     F1-Score:  Harmonic mean of precision & recall")
    print(f"     PR-AUC:    Overall precision-recall trade-off (better than ROC-AUC for imbalanced data)")

    # ========================================
    # 4.5. TOP-K ACCURACY (LOTTERY-SPECIFIC)
    # ========================================
    print(f"\n  Top-K Accuracy (per draw, averaged over the validation period):")
    topk_metrics = calculate_topk_accuracy(
        y_val, val_proba, k_values=[7, 10, 15, 20], groups=topk_groups
    )

    # Store in main metrics dict
    metrics.update(topk_metrics)

    n_draws = topk_metrics.get('topk_n_draws', 1)
    print(f"     Validation draws: {n_draws}")
    print(f"     {'K':<8} {'HitRate':<10} {'AvgCaught':<12} {'Expected':<12} {'Lift':<8}")
    print(f"     {'-'*52}")
    for k in [7, 10, 15, 20]:
        print(f"     Top-{k:<3} "
              f"{topk_metrics[f'top{k}_hit']*100:>6.1f}%   "
              f"{topk_metrics[f'top{k}_winners']:<12.3f} "
              f"{topk_metrics[f'top{k}_expected']:<12.3f} "
              f"{topk_metrics[f'top{k}_lift']:<8.3f}")

    print(f"\n  Top-K Interpretation:")
    print(f"     HitRate:   Share of draws with at least 1 winner in the top K")
    print(f"     AvgCaught: Mean winners caught in top K, per draw")
    print(f"     Expected:  Hypergeometric expectation if picks were random")
    print(f"     Lift:      AvgCaught / Expected. 1.00 means no skill.")

    # Precision-Recall curve
    precision_curve, recall_curve, pr_thresholds = precision_recall_curve(y_val, val_proba)

    if save_plots:
        plt.figure(figsize=(10, 6))
        plt.plot(recall_curve, precision_curve, linewidth=2, label=f'PR curve (AP = {avg_precision_val:.3f})')
        baseline = sum(y_val) / len(y_val)  # Baseline = positive class ratio
        plt.axhline(y=baseline, color='k', linestyle='--', label=f'Baseline (ratio = {baseline:.3f})')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('Recall', fontsize=12)
        plt.ylabel('Precision', fontsize=12)
        plt.title(f'Precision-Recall Curve - {model_name}', fontsize=14, fontweight='bold')
        plt.legend(loc="best", fontsize=11)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{model_name}_pr_curve.png", dpi=150)
        plt.close()
        print(f"     Saved PR curve to {output_dir}/{model_name}_pr_curve.png")

    # ========================================
    # 5. CONFUSION MATRIX - WITH BOTH THRESHOLDS
    # ========================================
    # Default threshold
    cm_default = confusion_matrix(y_report, val_pred_default)
    tn_default, fp_default, fn_default, tp_default = cm_default.ravel()

    # Optimal threshold
    cm_optimal = confusion_matrix(y_report, val_pred_optimal)
    tn_optimal, fp_optimal, fn_optimal, tp_optimal = cm_optimal.ravel()

    # Store default threshold confusion matrix (for backwards compatibility)
    metrics['confusion_matrix'] = {
        'true_negatives': int(tn_default),
        'false_positives': int(fp_default),
        'false_negatives': int(fn_default),
        'true_positives': int(tp_default)
    }

    # Store optimal threshold confusion matrix
    metrics['confusion_matrix_optimal'] = {
        'true_negatives': int(tn_optimal),
        'false_positives': int(fp_optimal),
        'false_negatives': int(fn_optimal),
        'true_positives': int(tp_optimal)
    }

    print(f"\n  Confusion Matrix Comparison:")
    print(f"\n     Default Threshold (0.5):")
    print(f"     ┌────────────────────┬──────────┬──────────┐")
    print(f"     │                    │ Pred=0   │ Pred=1   │")
    print(f"     ├────────────────────┼──────────┼──────────┤")
    print(f"     │ Actual=0 (No win)  │  {tn_default:5d}   │  {fp_default:5d}   │")
    print(f"     │ Actual=1 (Win)     │  {fn_default:5d}   │  {tp_default:5d}   │")
    print(f"     └────────────────────┴──────────┴──────────┘")

    print(f"\n     Optimal Threshold ({optimal_threshold:.4f}):")
    print(f"     ┌────────────────────┬──────────┬──────────┐")
    print(f"     │                    │ Pred=0   │ Pred=1   │")
    print(f"     ├────────────────────┼──────────┼──────────┤")
    print(f"     │ Actual=0 (No win)  │  {tn_optimal:5d}   │  {fp_optimal:5d}   │")
    print(f"     │ Actual=1 (Win)     │  {fn_optimal:5d}   │  {tp_optimal:5d}   │")
    print(f"     └────────────────────┴──────────┴──────────┘")

    # Calculate specificity and sensitivity for both thresholds
    specificity_default = tn_default / (tn_default + fp_default) if (tn_default + fp_default) > 0 else 0
    sensitivity_default = tp_default / (tp_default + fn_default) if (tp_default + fn_default) > 0 else 0

    specificity_optimal = tn_optimal / (tn_optimal + fp_optimal) if (tn_optimal + fp_optimal) > 0 else 0
    sensitivity_optimal = tp_optimal / (tp_optimal + fn_optimal) if (tp_optimal + fn_optimal) > 0 else 0

    print(f"\n     Sensitivity/Specificity:")
    print(f"     {'Metric':<20} {'Default (0.5)':<15} {'Optimal':<15}")
    print(f"     {'-'*50}")
    print(f"     {'Sensitivity (Recall)':<20} {sensitivity_default:<15.4f} {sensitivity_optimal:<15.4f}")
    print(f"     {'Specificity':<20} {specificity_default:<15.4f} {specificity_optimal:<15.4f}")

    # ========================================
    # 6. CALIBRATION ANALYSIS
    # ========================================
    prob_true_val, prob_pred_val = calibration_curve(
        y_val, val_proba, n_bins=10, strategy='quantile'
    )

    calibration_error = np.mean(np.abs(prob_true_val - prob_pred_val))
    metrics['calibration_error'] = calibration_error

    print(f"\n  Calibration Analysis:")
    print(f"     Mean Calibration Error: {calibration_error:.4f}")

    if calibration_error > 0.1:
        print(f"     High calibration error - probabilities unreliable")
    elif calibration_error > 0.05:
        print(f"     Moderate calibration - acceptable")
    else:
        print(f"     Good calibration")

    if save_plots:
        plt.figure(figsize=(10, 6))
        plt.plot(prob_pred_val, prob_true_val, marker='o', linewidth=2, markersize=8, label='Model calibration')
        plt.plot([0, 1], [0, 1], 'k--', label='Perfect calibration', linewidth=1)
        plt.xlabel('Mean Predicted Probability', fontsize=12)
        plt.ylabel('Fraction of Positives (True Probability)', fontsize=12)
        plt.title(f'Calibration Curve - {model_name}', fontsize=14, fontweight='bold')
        plt.legend(loc="best", fontsize=11)
        plt.grid(alpha=0.3)
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.0])
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{model_name}_calibration.png", dpi=150)
        plt.close()
        print(f"     Saved calibration curve to {output_dir}/{model_name}_calibration.png")

    # ========================================
    # 7. DETAILED CLASSIFICATION REPORT (OPTIMAL THRESHOLD)
    # ========================================
    print(f"\n  Detailed Classification Report (Using Optimal Threshold {optimal_threshold:.4f}):")
    report = classification_report(y_report, val_pred_optimal, target_names=['No Win', 'Win'], digits=4)
    print("     " + "\n     ".join(report.split('\n')))

    # ========================================
    # 8. KEY TAKEAWAYS
    # ========================================
    print(f"\n  KEY TAKEAWAYS:")
    if f1_val_optimal > f1_val_default:
        improvement = ((f1_val_optimal - f1_val_default) / (f1_val_default + 1e-10)) * 100
        print(f"     Optimal threshold improves F1-score by {improvement:.1f}%")
        print(f"     Use threshold={optimal_threshold:.4f} for predictions")
    else:
        print(f"     ℹ Default threshold (0.5) is already near-optimal")

    if tp_optimal > 0:
        print(f"     Model successfully predicts {tp_optimal} winning numbers")
    else:
        print(f"     Model predicts 0 winning numbers - needs improvement")

    print(f"{'='*70}\n")

    return metrics


def compare_models(
    all_metrics: Dict[str, Dict[str, Any]],
    output_dir: str = "model_metrics"
) -> pd.DataFrame:
    """
    Compare multiple models and create summary table.

    Args:
        all_metrics: Dictionary mapping model names to their metrics
        output_dir: Directory to save comparison table

    Returns:
        DataFrame with model comparison
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    comparison_data = []

    for model_name, metrics in all_metrics.items():
        comparison_data.append({
            'Model': model_name,
            'Val Accuracy': metrics.get('val_accuracy_optimal', metrics.get('val_accuracy', 0)),
            'Val AUC-ROC': metrics.get('auc_val', 0),
            'PR-AUC': metrics.get('pr_auc', metrics.get('avg_precision', 0)),
            'Precision': metrics.get('precision_optimal', metrics.get('precision', 0)),
            'Recall': metrics.get('recall_optimal', metrics.get('recall', 0)),
            'F1-Score': metrics.get('f1_score_optimal', metrics.get('f1_score', 0)),
            'PR-AUC Baseline': metrics.get('pr_auc_baseline', 0),
            'PR-AUC Lift': metrics.get('pr_auc_lift', 0),
            'Top-7 AvgCaught': metrics.get('top7_winners', 0),
            'Top-7 Expected': metrics.get('top7_expected', 0),
            'Top-7 Lift': metrics.get('top7_lift', 0),
            'Top-7 HitRate': metrics.get('top7_hit', 0),
            'Val Draws': metrics.get('topk_n_draws', 0),
            'Calibration Error': metrics.get('calibration_error', 0),
            'Overfit Gap (AUC)': metrics.get('overfitting_gap_auc', 0),
            'Optimal Threshold': metrics.get('optimal_threshold', 0.5)
        })

    comparison_df = pd.DataFrame(comparison_data)

    # Sort by F1-Score (most balanced metric for lottery prediction)
    comparison_df = comparison_df.sort_values('F1-Score', ascending=False)

    # Save to CSV
    comparison_df.to_csv(f"{output_dir}/model_comparison.csv", index=False)

    # Print comparison table
    print("\n" + "="*100)
    print("  MODEL COMPARISON SUMMARY")
    print("="*100)
    print(comparison_df.to_string(index=False))
    print("="*100)
    print(f"\nSaved comparison to {output_dir}/model_comparison.csv\n")

    return comparison_df


def plot_model_comparison(
    all_metrics: Dict[str, Dict[str, Any]],
    output_dir: str = "model_metrics"
):
    """
    Create visual comparison of all models.

    Args:
        all_metrics: Dictionary mapping model names to their metrics
        output_dir: Directory to save plots
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    model_names = list(all_metrics.keys())

    metrics_to_plot = [
        ('val_accuracy_optimal', 'Validation Accuracy (Optimal)'),
        ('auc_val', 'AUC-ROC'),
        ('pr_auc', 'PR-AUC (Better for Imbalanced)'),
        ('f1_score_optimal', 'F1-Score (Optimal)')
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.ravel()

    for idx, (metric_key, metric_label) in enumerate(metrics_to_plot):
        # Get metric value with fallback to alternative keys
        values = []
        for model in model_names:
            if metric_key in all_metrics[model]:
                values.append(all_metrics[model][metric_key])
            elif metric_key == 'val_accuracy_optimal':
                values.append(all_metrics[model].get('val_accuracy', 0))
            elif metric_key == 'pr_auc':
                values.append(all_metrics[model].get('avg_precision', 0))
            elif metric_key == 'f1_score_optimal':
                values.append(all_metrics[model].get('f1_score', 0))
            else:
                values.append(0)

        colors = ['#2ecc71' if v == max(values) else '#3498db' for v in values]

        axes[idx].bar(range(len(model_names)), values, color=colors, alpha=0.8)
        axes[idx].set_xticks(range(len(model_names)))
        axes[idx].set_xticklabels(model_names, rotation=45, ha='right')
        axes[idx].set_ylabel(metric_label, fontsize=11)
        axes[idx].set_title(f'{metric_label} Comparison', fontsize=12, fontweight='bold')
        axes[idx].grid(axis='y', alpha=0.3)
        axes[idx].set_ylim([0, 1])

        # Add value labels on bars
        for i, v in enumerate(values):
            axes[idx].text(i, v + 0.02, f'{v:.3f}', ha='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig(f"{output_dir}/model_comparison_chart.png", dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved comparison chart to {output_dir}/model_comparison_chart.png")
