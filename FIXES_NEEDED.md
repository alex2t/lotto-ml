# Lottery ML System - Recommended Improvements

## ✅ CRITICAL FIXES COMPLETED (This Branch)

### 1. Win Bias Ratio Look-Ahead Bias Fixed ✓
**File:** `lotto_analysis/analyzers/hmc_analyzer.py:181-203`

**Issue:** The win bias ratio was calculated using current draw categories, causing data leakage.

**Fix Applied:** Now uses categories calculated from ONLY preceding draws:
- For recency method: Calculates `preceding_days_since` from preceding draws only
- For frequency method: Calculates `preceding_freq` from preceding draws only
- Eliminates look-ahead bias completely

**Impact:** More accurate feature values, better model generalization.

---

### 2. Bonus Ball Contamination Fixed ✓
**File:** `lotto_analysis/analyzers/hmc_analyzer.py:267-274`

**Issue:** `recent_4`, `recent_5`, etc. features counted ALL 7 numbers including bonus, inflating counts when a number appeared as bonus.

**Fix Applied:** Changed from:
```python
count = sum(1 for draw in window_draws if number in draw["numbers"])
```

To:
```python
count = sum(1 for draw in window_draws if number in draw["numbers"][:6])
```

**Impact:** Recent count features now accurately reflect MAIN number appearances only.

---

### 3. SCENARIOS Config Synchronized ✓
**Files:**
- `lotto_analysis/config/config.py:40-45`
- `ml_lotto/config.py:42-49`

**Issue:** Different window sizes between analysis and ML caused feature mismatch.

**Fix Applied:** Both configs now use identical SCENARIOS:
```python
SCENARIOS = [
    {"window": 5,  "targets": [2]},
    {"window": 6,  "targets": [3]},
    {"window": 10, "targets": [4]},
    {"window": 25, "targets": [8]}
]
```

**Impact:** Feature extraction and model training now aligned.

---

## 🔧 HIGH PRIORITY IMPROVEMENTS (To Be Implemented)

### 4. Multiple Hypothesis Testing Correction
**Priority:** HIGH
**Effort:** Medium
**Files:** All scipy analyzers in `lotto_analysis/analyzers/*_analyzer.py`

**Problem:**
Running 47 hypothesis tests (one per number) at p < 0.05 without correction leads to ~2.35 expected false positives by chance alone (Type I error inflation).

**Recommended Fix:**
```python
from statsmodels.stats.multitest import multipletests

# After running all tests
p_values = [test_result['p_value'] for num in range(1, 48)]
rejected, p_adjusted, _, _ = multipletests(
    p_values,
    method='fdr_bh'  # Benjamini-Hochberg FDR correction
)

# Use p_adjusted instead of raw p-values
for i, num in enumerate(range(1, 48)):
    test_results[num]['p_value_adjusted'] = p_adjusted[i]
    test_results[num]['significant'] = rejected[i]
```

**Files to Update:**
- `lotto_analysis/analyzers/consecutive_pair_analyzer.py`
- `lotto_analysis/analyzers/odd_even_analyzer.py`
- `lotto_analysis/analyzers/range_spread_analyzer.py`
- `lotto_analysis/analyzers/sum_contribution_analyzer.py`

**Expected Impact:** Reduces false positive feature importance, more robust statistical validation.

---

### 5. Feature Importance Analysis
**Priority:** HIGH
**Effort:** Low
**File:** `ml_lotto/models/trainer.py`

**Problem:**
Models use fixed feature sets without validation of which features actually contribute to predictions.

**Recommended Implementation:**
```python
def analyze_feature_importance(pipeline, feature_names, model_name):
    """Analyze and display feature importance after training."""

    if hasattr(pipeline.named_steps['classifier'], 'coef_'):
        # Linear models (Logistic Regression)
        importances = abs(pipeline.named_steps['classifier'].coef_[0])
    elif hasattr(pipeline.named_steps['classifier'], 'feature_importances_'):
        # Tree-based models (XGBoost, Random Forest)
        importances = pipeline.named_steps['classifier'].feature_importances_
    else:
        return None

    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances,
        'abs_importance': abs(importances)
    }).sort_values('abs_importance', ascending=False)

    print(f"\n📊 Feature Importance for {model_name}:")
    print(importance_df.head(10))

    # Identify low-importance features
    threshold = 0.01
    low_importance = importance_df[importance_df['abs_importance'] < threshold]
    if len(low_importance) > 0:
        print(f"\n⚠️  {len(low_importance)} features with importance < {threshold}:")
        print(low_importance['feature'].tolist())

    return importance_df

# Add to train_model() function after line 165
importance_df = analyze_feature_importance(
    pipeline,
    selected_features,
    model_config['name']
)
```

**Expected Impact:**
- Identify redundant features
- Reduce model complexity
- Improve interpretability
- Potential performance gains

---

### 6. Calibration Validation
**Priority:** HIGH
**Effort:** Low
**File:** `ml_lotto/models/trainer.py`

**Problem:**
Probability calibration is applied but never validated. Miscalibrated probabilities lead to poor selection decisions.

**Recommended Implementation:**
```python
from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt

def validate_calibration(pipeline, X_val, y_val, model_name):
    """Validate probability calibration quality."""

    # Get predicted probabilities
    y_pred_proba = pipeline.predict_proba(X_val)[:, 1]

    # Calculate calibration curve
    prob_true, prob_pred = calibration_curve(
        y_val,
        y_pred_proba,
        n_bins=10,
        strategy='quantile'
    )

    # Calculate calibration error
    calibration_error = np.mean(np.abs(prob_true - prob_pred))

    print(f"\n🎯 Calibration Analysis for {model_name}:")
    print(f"  Mean Calibration Error: {calibration_error:.4f}")
    print(f"  Perfect calibration: 0.0000")

    if calibration_error > 0.1:
        print(f"  ⚠️  High calibration error - consider different calibration method")
    elif calibration_error > 0.05:
        print(f"  ⚡ Moderate calibration - acceptable but could improve")
    else:
        print(f"  ✅ Good calibration")

    return calibration_error

# Add to train_model() after validation accuracy (line 181)
if val_df is not None and len(val_df) > 0:
    cal_error = validate_calibration(
        pipeline,
        X_val,
        y_val,
        model_config['name']
    )
```

**Expected Impact:**
- Identify miscalibrated models
- Better probability-based selection
- More reliable confidence scores

---

## 📊 MEDIUM PRIORITY IMPROVEMENTS

### 7. Ensemble Weighting Strategy
**Priority:** MEDIUM
**Effort:** Medium
**File:** `ml_lotto/prediction/predictor.py`

**Problem:**
All models contribute equally to diversity penalties regardless of performance.

**Recommended Approach:**
```python
def calculate_model_weights(models, val_accuracies):
    """Calculate performance-based model weights."""

    total_accuracy = sum(val_accuracies.values())
    weights = {
        name: acc / total_accuracy
        for name, acc in val_accuracies.items()
    }

    return weights

# In generate_all_picks() function
model_weights = calculate_model_weights(models, validation_results)

# Apply weighted diversity penalty
for model_idx, (model_name, model_data) in enumerate(models.items()):
    base_penalty = model_config['diversity_penalty']
    weighted_penalty = base_penalty * model_weights[model_name]
    # Use weighted_penalty instead of base_penalty
```

**Expected Impact:**
- Better models get more weight
- Improved ensemble diversity
- More robust predictions

---

### 8. Temporal Walk-Forward Validation
**Priority:** MEDIUM
**Effort:** High
**File:** `ml_lotto/models/trainer.py`

**Problem:**
Single 80/20 split may not detect temporal instability. Models might only work on recent data.

**Recommended Implementation:**
```python
def walk_forward_validation(
    model_config,
    all_draws,
    features_dict,
    n_windows=3
):
    """
    Perform walk-forward validation over multiple time windows.

    Tests model stability across different time periods.
    """

    total_draws = len(all_draws)
    window_size = (total_draws - TRAINING_START_DRAW) // (n_windows + 1)

    results = []

    for i in range(n_windows):
        train_end = TRAINING_START_DRAW + (i + 1) * window_size
        val_start = train_end
        val_end = train_end + window_size

        print(f"\n  Window {i+1}: Train={train_end}, Val={val_start}-{val_end}")

        # Train on this window
        train_df = build_training_dataset(
            all_draws,
            features_dict,
            all_feature_names,
            start_index=TRAINING_START_DRAW,
            end_index=train_end
        )

        val_df = build_training_dataset(
            all_draws,
            features_dict,
            all_feature_names,
            start_index=val_start,
            end_index=val_end
        )

        pipeline, _ = train_model(
            model_config,
            train_df,
            all_feature_names,
            model_index=1,
            val_df=val_df
        )

        # Evaluate
        X_val = val_df[selected_features].values
        y_val = val_df['hit'].values
        accuracy = pipeline.score(X_val, y_val)

        results.append({
            'window': i + 1,
            'accuracy': accuracy,
            'period': f"{val_start}-{val_end}"
        })

    # Check stability
    accuracies = [r['accuracy'] for r in results]
    std_dev = np.std(accuracies)

    print(f"\n📊 Walk-Forward Validation Results:")
    for r in results:
        print(f"  Window {r['window']}: {r['accuracy']:.4f}")

    print(f"\n  Mean Accuracy: {np.mean(accuracies):.4f}")
    print(f"  Std Deviation: {std_dev:.4f}")

    if std_dev > 0.05:
        print(f"  ⚠️  High variance - model may be unstable over time")
    else:
        print(f"  ✅ Stable performance across time windows")

    return results
```

**Expected Impact:**
- Detect temporal instability
- Identify overfitting to recent patterns
- More robust model selection

---

### 9. Dynamic HMC Category Rebalancing
**Priority:** MEDIUM
**Effort:** Medium
**Files:**
- `lotto_analysis/analyzers/hmc_analyzer.py`
- `ml_lotto/config.py`

**Problem:**
Current recency-based HMC creates imbalanced categories (Hot=22, Medium=14, Cold=11), but models are configured for balanced selection (e.g., 2H-2M-2C).

**Option A: Balance Category Sizes**
```python
def get_balanced_hmc_categories(days_since, target_size=16):
    """
    Create balanced HMC categories using dynamic thresholds.

    Args:
        days_since: Days since last hit for each number
        target_size: Target numbers per category (~MAX_NUMBER/3)

    Returns:
        Balanced hot/medium/cold categories
    """

    sorted_numbers = sorted(
        days_since.items(),
        key=lambda x: x[1]
    )

    hot_numbers = [num for num, _ in sorted_numbers[:target_size]]
    medium_numbers = [num for num, _ in sorted_numbers[target_size:2*target_size]]
    cold_numbers = [num for num, _ in sorted_numbers[2*target_size:]]

    return {
        'hot_numbers': hot_numbers,
        'medium_numbers': medium_numbers,
        'cold_numbers': cold_numbers
    }
```

**Option B: Proportional Model Selection**
```python
def calculate_proportional_hmc_counts(categories, total_picks=6):
    """
    Adjust model HMC counts based on actual category distribution.
    """

    total_numbers = sum(len(nums) for nums in categories.values())

    hot_ratio = len(categories['hot_numbers']) / total_numbers
    medium_ratio = len(categories['medium_numbers']) / total_numbers
    cold_ratio = len(categories['cold_numbers']) / total_numbers

    return {
        'hot_count': round(total_picks * hot_ratio),
        'medium_count': round(total_picks * medium_ratio),
        'cold_count': round(total_picks * cold_ratio)
    }
```

**Expected Impact:**
- Better alignment between categories and selection strategy
- More realistic number distributions
- Improved model performance

---

## 💡 CONCEPTUAL IMPROVEMENTS

### 10. Lottery Prediction Reality Check

**Important Philosophical Note:**

Lottery draws are designed to be **truly random**. While your system is sophisticated and well-engineered, it's important to understand what it actually does:

**What Your System Does:**
✅ Identifies historical distribution patterns
✅ Applies statistical constraints (sum ranges, odd/even balance)
✅ Generates "realistic-looking" number combinations
✅ Learns which numbers historically appear together

**What Your System Cannot Do:**
❌ Predict future random events better than chance
❌ Find "hot" or "cold" numbers that affect future draws
❌ Increase probability of winning through pattern recognition

**Key Insights:**
1. **Independence:** Each draw is independent. Past draws don't influence future ones.
2. **Gambler's Fallacy:** "Hot" and "cold" numbers are statistical illusions over small samples.
3. **Random Number Generators:** Modern lottery machines are designed to be unpredictable.

**Recommended Focus Shift:**

Instead of trying to predict "the" winning numbers, consider:

1. **Ensemble Coverage Strategy**
   - Generate diverse portfolios that maximize coverage
   - Target partial matches (3/6, 4/6) which have better odds
   - Optimize for expected value across multiple combinations

2. **Statistical Realism** (your strength!)
   - Continue matching historical distributions
   - Avoid "unrealistic" combinations (all odd, all consecutive, etc.)
   - This is valid for syndicate play aesthetics

3. **Portfolio Optimization**
   ```python
   def generate_diverse_portfolio(n_combinations=10):
       """
       Generate N combinations that maximize coverage while
       maintaining statistical realism.
       """

       combinations = []
       covered_numbers = set()

       while len(combinations) < n_combinations:
           # Generate combination avoiding excessive overlap
           combo = generate_combination(
               avoid_numbers=covered_numbers if len(covered_numbers) > 35 else set()
           )
           combinations.append(combo)
           covered_numbers.update(combo)

       return combinations
   ```

**For Educational Purposes:**
Your system is excellent for:
- Learning ML engineering
- Understanding statistical validation
- Practicing feature engineering
- Building production ML pipelines

---

## 📋 IMPLEMENTATION CHECKLIST

### Critical Fixes (Completed ✓)
- [x] Fix win bias ratio look-ahead bias
- [x] Fix bonus ball contamination in recent_counts
- [x] Synchronize SCENARIOS configuration

### High Priority (Next Sprint)
- [ ] Add multiple hypothesis testing correction
- [ ] Implement feature importance analysis
- [ ] Add calibration validation

### Medium Priority (Future Sprints)
- [ ] Implement ensemble weighting strategy
- [ ] Add temporal walk-forward validation
- [ ] Implement dynamic HMC rebalancing

### Low Priority (Nice to Have)
- [ ] Add comprehensive logging
- [ ] Create performance monitoring dashboard
- [ ] Implement A/B testing framework for model configs

---

## 🔍 TESTING RECOMMENDATIONS

After implementing each fix:

1. **Regenerate All JSON Files**
   ```bash
   python3 drawpick.py
   ```

2. **Compare Before/After Results**
   ```bash
   # Save current results
   cp -r data data_backup

   # After changes
   python3 drawpick.py
   diff -r data data_backup
   ```

3. **Run ML Training**
   ```bash
   python3 quickpick.py
   ```

4. **Validate Improvements**
   - Check validation accuracy changes
   - Compare feature importance
   - Review calibration metrics
   - Analyze prediction diversity

---

## 📚 ADDITIONAL RESOURCES

**Statistical Testing:**
- [Statsmodels Multiple Testing](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html)
- [Understanding FDR Correction](https://en.wikipedia.org/wiki/False_discovery_rate)

**Model Calibration:**
- [Scikit-learn Calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [Calibration Curves Explained](https://scikit-learn.org/stable/auto_examples/calibration/plot_calibration_curve.html)

**Walk-Forward Validation:**
- [Time Series Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-15
**Critical Fixes Branch:** `claude/critical-bug-fixes-01Frnw8XkCCbdh1zfQheB6MG`
