"""
model_metrics.py
================
Comprehensive model evaluation metrics for lottery prediction.

Includes:
- AUC-ROC curves
- Precision/Recall/F1
- Calibration curves
- Classification reports
"""

import numpy as np
import pandas as pd
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


def calculate_comprehensive_metrics(
    pipeline: Any,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    model_name: str,
    save_plots: bool = True,
    output_dir: str = "model_metrics"
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

    Returns:
        Dictionary containing all metrics
    """
    import os
    if save_plots:
        os.makedirs(output_dir, exist_ok=True)

    metrics = {}

    # ========================================
    # 1. BASIC ACCURACY METRICS
    # ========================================
    train_pred = pipeline.predict(X_train)
    val_pred = pipeline.predict(X_val)

    train_accuracy = (train_pred == y_train).sum() / len(y_train)
    val_accuracy = (val_pred == y_val).sum() / len(y_val)

    metrics['train_accuracy'] = train_accuracy
    metrics['val_accuracy'] = val_accuracy
    metrics['overfitting_gap'] = train_accuracy - val_accuracy

    print(f"\n{'='*70}")
    print(f"  📊 MODEL EVALUATION: {model_name}")
    print(f"{'='*70}")
    print(f"  Train Accuracy: {train_accuracy:.4f}")
    print(f"  Val Accuracy:   {val_accuracy:.4f}")
    print(f"  Overfit Gap:    {metrics['overfitting_gap']:.4f}")

    # ========================================
    # 2. PROBABILITY-BASED PREDICTIONS
    # ========================================
    train_proba = pipeline.predict_proba(X_train)[:, 1]
    val_proba = pipeline.predict_proba(X_val)[:, 1]

    # ========================================
    # 3. AUC-ROC METRICS ⭐
    # ========================================
    # Calculate ROC curve
    fpr_train, tpr_train, thresholds_train = roc_curve(y_train, train_proba)
    fpr_val, tpr_val, thresholds_val = roc_curve(y_val, val_proba)

    # Calculate AUC
    auc_train = auc(fpr_train, tpr_train)
    auc_val = auc(fpr_val, tpr_val)

    metrics['auc_train'] = auc_train
    metrics['auc_val'] = auc_val

    print(f"\n  🎯 AUC-ROC Scores:")
    print(f"     Train AUC: {auc_train:.4f}")
    print(f"     Val AUC:   {auc_val:.4f}")

    # Interpret AUC
    if auc_val < 0.6:
        print(f"     ⚠️  Poor discrimination (barely better than random)")
    elif auc_val < 0.7:
        print(f"     ⚡ Acceptable discrimination")
    elif auc_val < 0.8:
        print(f"     ✅ Good discrimination")
    else:
        print(f"     🌟 Excellent discrimination")

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
        print(f"     💾 Saved ROC curve to {output_dir}/{model_name}_roc_curve.png")

    # ========================================
    # 4. PRECISION-RECALL METRICS
    # ========================================
    precision_val = precision_score(y_val, val_pred, zero_division=0)
    recall_val = recall_score(y_val, val_pred, zero_division=0)
    f1_val = f1_score(y_val, val_pred, zero_division=0)
    avg_precision_val = average_precision_score(y_val, val_proba)

    metrics['precision'] = precision_val
    metrics['recall'] = recall_val
    metrics['f1_score'] = f1_val
    metrics['avg_precision'] = avg_precision_val

    print(f"\n  📈 Precision-Recall Metrics:")
    print(f"     Precision: {precision_val:.4f}  (When model predicts 1, how often correct?)")
    print(f"     Recall:    {recall_val:.4f}  (Of all winning numbers, how many caught?)")
    print(f"     F1-Score:  {f1_val:.4f}  (Harmonic mean of precision & recall)")
    print(f"     Avg Precision: {avg_precision_val:.4f}  (Area under PR curve)")

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
        print(f"     💾 Saved PR curve to {output_dir}/{model_name}_pr_curve.png")

    # ========================================
    # 5. CONFUSION MATRIX
    # ========================================
    cm = confusion_matrix(y_val, val_pred)
    tn, fp, fn, tp = cm.ravel()

    metrics['confusion_matrix'] = {
        'true_negatives': int(tn),
        'false_positives': int(fp),
        'false_negatives': int(fn),
        'true_positives': int(tp)
    }

    print(f"\n  🔢 Confusion Matrix:")
    print(f"     ┌────────────────────┬──────────┬──────────┐")
    print(f"     │                    │ Pred=0   │ Pred=1   │")
    print(f"     ├────────────────────┼──────────┼──────────┤")
    print(f"     │ Actual=0 (No win)  │  {tn:5d}   │  {fp:5d}   │")
    print(f"     │ Actual=1 (Win)     │  {fn:5d}   │  {tp:5d}   │")
    print(f"     └────────────────────┴──────────┴──────────┘")

    # Calculate specificity and sensitivity
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0  # Same as recall

    print(f"\n     Sensitivity (Recall):  {sensitivity:.4f}")
    print(f"     Specificity:           {specificity:.4f}")

    # ========================================
    # 6. CALIBRATION ANALYSIS
    # ========================================
    prob_true_val, prob_pred_val = calibration_curve(
        y_val, val_proba, n_bins=10, strategy='quantile'
    )

    calibration_error = np.mean(np.abs(prob_true_val - prob_pred_val))
    metrics['calibration_error'] = calibration_error

    print(f"\n  🎯 Calibration Analysis:")
    print(f"     Mean Calibration Error: {calibration_error:.4f}")

    if calibration_error > 0.1:
        print(f"     ⚠️  High calibration error - probabilities unreliable")
    elif calibration_error > 0.05:
        print(f"     ⚡ Moderate calibration - acceptable")
    else:
        print(f"     ✅ Good calibration")

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
        print(f"     💾 Saved calibration curve to {output_dir}/{model_name}_calibration.png")

    # ========================================
    # 7. THRESHOLD ANALYSIS
    # ========================================
    # Find optimal threshold that maximizes F1
    precisions, recalls, pr_thresholds = precision_recall_curve(y_val, val_proba)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    optimal_idx = np.argmax(f1_scores)
    optimal_threshold = pr_thresholds[optimal_idx] if optimal_idx < len(pr_thresholds) else 0.5
    optimal_f1 = f1_scores[optimal_idx]

    metrics['optimal_threshold'] = optimal_threshold
    metrics['optimal_f1'] = optimal_f1

    print(f"\n  ⚙️  Threshold Analysis:")
    print(f"     Default threshold: 0.5")
    print(f"     Optimal threshold: {optimal_threshold:.4f} (maximizes F1 = {optimal_f1:.4f})")

    # ========================================
    # 8. DETAILED CLASSIFICATION REPORT
    # ========================================
    print(f"\n  📋 Detailed Classification Report:")
    report = classification_report(y_val, val_pred, target_names=['No Win', 'Win'], digits=4)
    print("     " + "\n     ".join(report.split('\n')))

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
            'Val Accuracy': metrics.get('val_accuracy', 0),
            'Val AUC-ROC': metrics.get('auc_val', 0),
            'Precision': metrics.get('precision', 0),
            'Recall': metrics.get('recall', 0),
            'F1-Score': metrics.get('f1_score', 0),
            'Avg Precision': metrics.get('avg_precision', 0),
            'Calibration Error': metrics.get('calibration_error', 0),
            'Overfit Gap': metrics.get('overfitting_gap', 0)
        })

    comparison_df = pd.DataFrame(comparison_data)

    # Sort by AUC-ROC (most important metric)
    comparison_df = comparison_df.sort_values('Val AUC-ROC', ascending=False)

    # Save to CSV
    comparison_df.to_csv(f"{output_dir}/model_comparison.csv", index=False)

    # Print comparison table
    print("\n" + "="*100)
    print("  🏆 MODEL COMPARISON SUMMARY")
    print("="*100)
    print(comparison_df.to_string(index=False))
    print("="*100)
    print(f"\n💾 Saved comparison to {output_dir}/model_comparison.csv\n")

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
        ('val_accuracy', 'Validation Accuracy'),
        ('auc_val', 'AUC-ROC'),
        ('f1_score', 'F1-Score'),
        ('avg_precision', 'Average Precision')
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.ravel()

    for idx, (metric_key, metric_label) in enumerate(metrics_to_plot):
        values = [all_metrics[model][metric_key] for model in model_names]

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

    print(f"💾 Saved comparison chart to {output_dir}/model_comparison_chart.png")
