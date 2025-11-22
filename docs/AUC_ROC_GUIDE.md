# AUC-ROC Guide for Lottery Prediction Models

## What is AUC-ROC?

**AUC-ROC** stands for **Area Under the Receiver Operating Characteristic Curve**. It's the gold standard metric for evaluating binary classification models, especially with imbalanced classes.

### Why Accuracy is Misleading for Lottery

In lottery prediction, numbers have a ~14% chance of appearing (1 in 7):
- **Positive class**: Number appears (14% of cases)
- **Negative class**: Number doesn't appear (86% of cases)

**The Accuracy Trap:**
```python
# A dumb model that always predicts "won't appear":
predictions = [0, 0, 0, 0, 0, ...]  # Always predict 0

# Accuracy = 86% ✓ (sounds great!)
# But it never catches ANY winning numbers! ✗
```

### How AUC-ROC Fixes This

AUC-ROC measures how well your model **separates** winners from non-winners across all prediction thresholds, not just one.

**ROC Curve** plots:
- **X-axis**: False Positive Rate (FPR) = How often you wrongly predict "will appear"
- **Y-axis**: True Positive Rate (TPR) = How often you correctly catch winning numbers

**AUC** = Area under this curve (0 to 1)

---

## Interpreting AUC Scores

| AUC Score | Meaning | Interpretation for Lottery |
|-----------|---------|---------------------------|
| **0.5** | Random guessing | Model is worthless - might as well flip a coin |
| **0.5 - 0.6** | Very poor | Barely better than random |
| **0.6 - 0.7** | Poor to acceptable | Model has weak signal but not reliable |
| **0.7 - 0.8** | Good | **This is realistic for lottery!** Model finds patterns |
| **0.8 - 0.9** | Excellent | Very strong predictive power (rare for lottery) |
| **0.9 - 1.0** | Outstanding | Almost perfect (suspicious for lottery - check for data leakage!) |

### Realistic Expectations for Lottery

Given the inherent randomness of lottery draws:
- **AUC = 0.65-0.75** is a **strong result** showing genuine pattern detection
- **AUC > 0.80** is exceptional and should be validated carefully (could be overfitting)
- **AUC > 0.90** is suspicious - likely data leakage or overfitting

---

## Reading the ROC Curve

### Perfect Example

```
       TPR
        │
    1.0 ├─────────┐ ← Perfect model (catches all winners, no false positives)
        │         │
        │         │
    0.5 │    ╱    │ ← Your model (good separation)
        │   ╱     │
        │  ╱      │
    0.0 ├─────────┼────── FPR
       0.0       0.5      1.0
            ^
            └── Random guessing line (AUC = 0.5)
```

**What to look for:**
- **Curve hugs top-left corner** = Good model (high TPR, low FPR)
- **Curve follows diagonal** = Random guessing (AUC = 0.5)
- **Area between curve and diagonal** = Model's predictive power

### Example Interpretation

```
Model: Timing Pattern Specialist
AUC-Train: 0.6834
AUC-Val:   0.6512

✅ Interpretation:
- Validation AUC of 0.65 shows the model has found real patterns
- Not overfitting much (train vs val gap = 0.032)
- Model can rank numbers by win probability better than random
- At optimal threshold, catches ~52% of winning numbers while
  maintaining ~87% specificity (rejects most losers correctly)
```

---

## Other Important Metrics

### 1. Precision-Recall Curves

**Better than ROC for highly imbalanced classes** (like lottery).

- **Precision**: Of numbers predicted to win, how many actually won?
  - `Precision = TP / (TP + FP)`
  - High precision = few false alarms

- **Recall** (Sensitivity): Of actual winners, how many did we catch?
  - `Recall = TP / (TP + FN)`
  - High recall = catch most winners

**Average Precision (AP)** = Area under PR curve
- Better metric than AUC for imbalanced data
- **AP > 0.25** is good for lottery (baseline is ~0.14)
- **AP > 0.35** is excellent

### 2. F1-Score

Harmonic mean of Precision and Recall:
- `F1 = 2 × (Precision × Recall) / (Precision + Recall)`
- Balances catching winners vs avoiding false positives
- **F1 > 0.25** is decent for lottery
- **F1 > 0.35** is strong

### 3. Calibration

Measures if predicted probabilities match reality:
- If model says "30% chance", does the number win 30% of the time?
- **Calibration Error < 0.05** = Well-calibrated
- **Calibration Error > 0.10** = Probabilities unreliable

---

## Confusion Matrix Explained

```
                  ┌────────────┬────────────┐
                  │  Pred = 0  │  Pred = 1  │
  ┌───────────────┼────────────┼────────────┤
  │ Actual = 0    │     TN     │     FP     │
  │ (No win)      │  (correct) │  (wrong)   │
  ├───────────────┼────────────┼────────────┤
  │ Actual = 1    │     FN     │     TP     │
  │ (Win)         │  (missed!) │  (caught!) │
  └───────────────┴────────────┴────────────┘
```

**Key Metrics:**
- **True Positives (TP)**: Correctly predicted winners
- **False Positives (FP)**: Wrongly predicted non-winners as winners
- **False Negatives (FN)**: Missed actual winners
- **True Negatives (TN)**: Correctly rejected non-winners

**Derived Metrics:**
- **Sensitivity (Recall)**: TP / (TP + FN) → Catch rate for winners
- **Specificity**: TN / (TN + FP) → Rejection rate for losers
- **Precision**: TP / (TP + FP) → Accuracy of positive predictions

---

## Threshold Optimization

Your model outputs probabilities (0.0 to 1.0). You need a threshold to convert to binary predictions:

```
Default threshold = 0.5
- Predict 1 if probability ≥ 0.5
- Predict 0 if probability < 0.5
```

**But 0.5 is often suboptimal!**

The metrics module finds the **optimal threshold** that maximizes F1-score:

```
Example Output:
  Default threshold: 0.5000
  Optimal threshold: 0.1234 (maximizes F1 = 0.2845)

This means:
- Lower threshold catches MORE winners (higher recall)
- But also has more false positives (lower precision)
- F1 = 0.28 is the best balance for lottery prediction
```

**For lottery, you typically want:**
- **Lower threshold** (0.10 - 0.20) to catch more winners
- Accept higher false positive rate (you're picking 7 numbers anyway)

---

## Using the Metrics

### Run Evaluation on Existing Models

```bash
python test_model_metrics.py
```

This will:
1. Load your trained models
2. Evaluate with comprehensive metrics
3. Generate ROC, PR, and calibration curves
4. Save comparison report

### Output Files

```
model_metrics/
├── Timing_Pattern_Specialist_roc_curve.png
├── Timing_Pattern_Specialist_pr_curve.png
├── Timing_Pattern_Specialist_calibration.png
├── Jackpot_Optimizer_roc_curve.png
├── ... (same for other models)
├── model_comparison.csv
└── model_comparison_chart.png
```

### Integrate into Training

See `EXAMPLE_trainer_with_metrics.py` for how to add these metrics to your training pipeline.

---

## Red Flags to Watch For

### 1. Perfect Scores (Overfitting)
```
❌ AUC-Val = 0.95+, Calibration Error > 0.10
→ Model memorized training data, won't generalize
```

### 2. Train/Val Gap (Overfitting)
```
❌ AUC-Train = 0.85, AUC-Val = 0.60
→ Model overfits to training set (gap = 0.25 too large)
```

### 3. Poor Calibration
```
❌ AUC = 0.75 but Calibration Error = 0.15
→ Rankings good but probabilities unreliable
→ Can't trust "30% chance" predictions
```

### 4. Low Recall with High Precision
```
❌ Precision = 0.80, Recall = 0.10
→ Model is too conservative (misses 90% of winners)
→ Useless for lottery where you need to catch winners
```

---

## What Good Performance Looks Like

### Strong Lottery Model
```
✅ Validation Metrics:
   AUC-ROC:          0.72
   Average Precision: 0.28
   F1-Score:         0.31
   Precision:        0.25
   Recall:           0.42
   Calibration Error: 0.04
   Train/Val Gap:    0.03

Interpretation:
- AUC of 0.72 shows genuine pattern detection
- Catches 42% of winning numbers (recall)
- When predicting wins, correct 25% of time (vs 14% baseline)
- Well-calibrated probabilities (error = 0.04)
- Minimal overfitting (gap = 0.03)
```

---

## Summary: What Matters Most

**Priority Ranking for Lottery:**

1. **AUC-ROC** → Can model separate winners from losers?
   - Target: 0.65-0.75

2. **Average Precision** → Quality of positive predictions
   - Target: 0.25-0.35

3. **Recall** → Catch rate for actual winners
   - Target: 0.40-0.60 (catch at least 40% of winners)

4. **Calibration Error** → Trust the probabilities
   - Target: < 0.05

5. **Train/Val Gap** → Overfitting check
   - Target: < 0.05

**Accuracy is least important** (can be high even for useless models).

---

## Questions?

**Q: My AUC is 0.62. Is that good?**
A: Yes for lottery! It means your model ranks numbers better than random. Compare against baseline (0.5).

**Q: Should I use the optimal threshold?**
A: For lottery, yes! Lower thresholds (0.10-0.20) catch more winners, which is what you want.

**Q: Model 3 has AUC=0.74 but Model 1 has AUC=0.68. Use Model 3?**
A: Not necessarily! Check:
- Calibration (which has better probabilities?)
- Overfitting (which generalizes better?)
- Ensemble them for best results!

**Q: Can I get AUC > 0.90 for lottery?**
A: Unlikely unless you have data leakage or overfitting. Lottery has inherent randomness.
