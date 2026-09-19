<!-- Status: background reading, not project spec. Written 2025-11. -->
<!-- Audience: human. General ML explanation (logistic regression, XGBoost, statistical testing). -->
<!-- It describes ML concepts in general, NOT what this system currently does or achieves. -->
<!-- For what this system does: models.md, features.md, metrics.md. Those win on any conflict. -->

# Machine Learning Concepts Guide for Lottery Prediction System

**A Comprehensive Guide for Students New to Machine Learning**

Version: 1.0
Last Updated: 2025-11-16
Audience: Students with no prior ML experience

---

## Table of Contents

1. [Introduction to Machine Learning](#1-introduction-to-machine-learning)
2. [Logistic Regression](#2-logistic-regression)
3. [XGBoost (Extreme Gradient Boosting)](#3-xgboost)
4. [Statistical Testing](#4-statistical-testing)
5. [Feature Engineering](#5-feature-engineering)
6. [Model Training & Evaluation](#6-model-training--evaluation)
7. [Ensemble Methods](#7-ensemble-methods)
8. [Advanced Concepts](#8-advanced-concepts)
9. [Glossary](#9-glossary)

---

## 1. Introduction to Machine Learning

### What is Machine Learning?

**Machine Learning (ML)** is a method of teaching computers to learn patterns from data without being explicitly programmed. Instead of writing rules like "if X happens, do Y," we show the computer many examples, and it learns the patterns automatically.

### How Does This Lottery System Use ML?

Our system uses ML to:
1. **Analyze historical lottery draws** (past winning numbers)
2. **Find patterns** in how numbers appear
3. **Predict which numbers** are more likely to appear in the next draw

### Key ML Concepts in This System

- **Features**: Characteristics of each number (e.g., how often it appeared recently, its HMC category)
- **Labels**: What we're trying to predict (whether a number will appear in the next draw)
- **Training**: Teaching the model using historical data
- **Prediction**: Using the trained model to predict future draws

---

## 2. Logistic Regression

### What is Logistic Regression?

**Logistic Regression** is a fundamental ML algorithm used for **classification** (predicting yes/no, true/false outcomes).

#### Real-World Analogy
Imagine you're a doctor predicting if a patient will recover based on their symptoms. You look at:
- Temperature (feature 1)
- Blood pressure (feature 2)
- Age (feature 3)

Based on past patients, you learned that:
- High temp + high blood pressure = less likely to recover
- Normal temp + normal blood pressure = more likely to recover

Logistic regression works the same way but with math!

### How It Works (Simplified)

```
For each lottery number:
  Score = (weight1 × feature1) + (weight2 × feature2) + ... + bias
  Probability = 1 / (1 + e^(-Score))

If Probability > 0.5: Predict "Will appear"
Else: Predict "Won't appear"
```

### Parameters Explained

#### 1. **penalty: 'l1' or 'l2'**

**What it does:** Prevents overfitting by penalizing complex models.

**Analogy:**
- You're studying for an exam
- **No penalty**: Memorize every single detail (including noise) → Overfitting
- **L1 penalty**: Focus on the most important topics, ignore trivial details
- **L2 penalty**: Consider all topics but don't obsess over any one

**Technical Details:**
- **L1 (Lasso)**:
  - Adds penalty: `|weight1| + |weight2| + ...`
  - Forces some weights to become exactly 0 (feature selection)
  - Use when: You have many features and want the model to ignore useless ones

- **L2 (Ridge)**:
  - Adds penalty: `weight1² + weight2² + ...`
  - Shrinks all weights but keeps them non-zero
  - Use when: All features might be somewhat useful

**In our code:**
```python
'penalty': 'l2'  # We use L2 because we believe all features contribute
```

**When to change:**
- Use `'l1'` if you suspect many features are useless
- Use `'l2'` (default) if all features seem relevant
- Use `'elasticnet'` to combine both

---

#### 2. **solver: 'liblinear'**

**What it does:** The optimization algorithm used to find the best weights.

**Analogy:**
Different ways to climb a mountain (find the best solution):
- **liblinear**: Good for small mountains (small datasets)
- **lbfgs**: Good for large mountains (large datasets)
- **saga**: Can handle very large mountains efficiently

**Technical Details:**

| Solver | Best For | Supports |
|--------|----------|----------|
| **liblinear** | Small datasets (<10K samples) | L1, L2 |
| **lbfgs** | Large datasets, faster | L2 only |
| **saga** | Very large datasets | L1, L2, elasticnet |
| **sag** | Large datasets | L2, elasticnet |

**In our code:**
```python
'solver': 'liblinear'  # Good for our dataset size (~800 draws)
```

**When to change:**
- Use `'lbfgs'` if you have >10,000 draws
- Use `'saga'` if you have >100,000 draws and want L1 penalty
- Use `'newton-cg'` for very precise solutions (slower)

---

#### 3. **max_iter: 1000**

**What it does:** Maximum number of iterations (attempts) to find the best solution.

**Analogy:**
You're solving a puzzle:
- Each iteration = one attempt to improve your solution
- max_iter = how many attempts you're willing to make before giving up

**Technical Details:**
- The solver tries to minimize error iteratively
- Each iteration improves the weights slightly
- Stops when:
  - Error is minimized (convergence) ✓ Good
  - OR max_iter reached ✗ May need more iterations

**In our code:**
```python
'max_iter': 1000  # Usually converges in <100 iterations
```

**What happens if you change it:**
- **Increase to 5000**: More attempts if model doesn't converge
  - Pro: Ensures convergence
  - Con: Slower training

- **Decrease to 100**: Fewer attempts
  - Pro: Faster training
  - Con: May not converge (warning message)

**Warning sign:**
```
ConvergenceWarning: Maximum iterations reached
→ Increase max_iter to 2000 or 5000
```

---

#### 4. **class_weight: 'balanced'**

**What it does:** Handles imbalanced datasets by adjusting the importance of each class.

**Analogy:**
You're grading exams:
- Class A: 100 students
- Class B: 10 students

If you grade normally, you might ignore Class B's patterns because they're rare.

**class_weight='balanced'** tells the model: "Pay extra attention to the rare class!"

**Technical Details:**

In lottery prediction:
- **Class 0 (doesn't appear)**: ~41 numbers per draw
- **Class 1 (appears)**: ~6 numbers per draw

This is **highly imbalanced** (6:41 ratio).

**How 'balanced' works:**
```python
weight_for_class_1 = total_samples / (num_classes × count_of_class_1)
weight_for_class_0 = total_samples / (num_classes × count_of_class_0)

# In our case (simplified):
weight_for_appearing = 800 / (2 × 120) = 3.33  # Higher weight
weight_for_not_appearing = 800 / (2 × 680) = 0.59  # Lower weight
```

**In our code:**
```python
'class_weight': 'balanced'  # CRITICAL for lottery prediction
```

**Alternatives:**
- `None`: No adjustment (BAD for imbalanced data)
  - Model would predict "won't appear" for everything

- `{0: 1, 1: 10}`: Manual weights
  - You control the exact importance

- `'balanced'`: Automatic (RECOMMENDED)
  - Let sklearn calculate optimal weights

---

#### 5. **random_state: 42**

**What it does:** Controls randomness for reproducibility.

**Analogy:**
Imagine shuffling a deck of cards:
- Without random_state: Different shuffle every time
- With random_state=42: Same shuffle every time

**Technical Details:**
Many ML algorithms use randomness:
- Splitting data into train/test sets
- Initializing weights
- Cross-validation folds

**random_state** is a **seed** that makes randomness reproducible.

**In our code:**
```python
'random_state': 42  # The answer to life, universe, and everything!
```

**Why 42?**
- It's a convention (from "Hitchhiker's Guide to the Galaxy")
- Could be any number (0, 1, 123, 9999)
- Just pick one and stick with it

**What happens if you change it:**
```python
'random_state': 42   → Results: [3, 7, 12, 19, 28, 35]
'random_state': 123  → Results: [5, 9, 14, 21, 30, 37]  # Different!
'random_state': 42   → Results: [3, 7, 12, 19, 28, 35]  # Same as first!
```

**When to change:**
- **Never change for production** (want consistent results)
- **Change for testing** (verify model isn't overfitting to one seed)

---

#### 6. **C: 1.0** (Regularization Strength)

**What it does:** Controls how strict the penalty is (inverse of regularization strength).

**Analogy:**
You're teaching a student:
- **High C (e.g., 100)**: Strict teacher - forces exact memorization
  - Student learns details perfectly (may overfit)

- **Low C (e.g., 0.01)**: Lenient teacher - encourages generalization
  - Student learns general concepts (may underfit)

**Technical Details:**

C is the **inverse** of regularization:
- **C = ∞**: No regularization (no penalty)
- **C = 1.0**: Moderate regularization (default)
- **C = 0.001**: Strong regularization (heavy penalty)

**Mathematical formula:**
```
Loss = Error + (1/C) × Penalty
```

**In our code:**
```python
'C': 1.0  # Balanced regularization
```

**What happens if you change C:**

| C Value | Effect | When to Use |
|---------|--------|-------------|
| **0.001** | Strong regularization<br>Simple model<br>Ignores noise | - Small dataset<br>- Many features<br>- Overfitting detected |
| **0.1** | Moderate regularization<br>Balanced model | - Medium dataset<br>- Some overfitting |
| **1.0** | Default<br>Standard balance | - Most cases (START HERE) |
| **10** | Weak regularization<br>Complex model | - Large dataset<br>- Underfitting detected |
| **100** | Minimal regularization<br>Very complex | - Very large dataset<br>- Very confident in data |

**How to tune C:**

1. **Start with C=1.0** (default)
2. **Check validation error:**
   - If overfitting (training good, validation bad): **Decrease C to 0.1**
   - If underfitting (both bad): **Increase C to 10**
3. **Grid search:**
   ```python
   C_values = [0.001, 0.01, 0.1, 1.0, 10, 100]
   # Try each and pick best validation score
   ```

**Visual Example:**
```
C = 0.01 (Strong regularization)
  ▁▂▂▃▃▃▄▄▄   ← Simple decision boundary

C = 1.0 (Moderate)
  ▁▂▃▄▅▄▃▂▁   ← Reasonable boundary

C = 100 (Weak regularization)
  ▁▂▃▄▅▆▅▄▃▂▁ ← Complex boundary (may overfit)
```

---

### 7. **calibration: {'method': 'sigmoid', 'cv': 5}**

**What it does:** Adjusts predicted probabilities to be more accurate.

**Analogy:**
Your weather app says "70% chance of rain":
- **Uncalibrated**: It rains 40% of the time when app says 70%
- **Calibrated**: It rains 70% of the time when app says 70%

Calibration makes sure "70% probability" actually means 70%!

**Technical Details:**

#### Method: 'sigmoid'

Two calibration methods:

1. **'sigmoid' (Platt Scaling)**:
   - Fits a logistic curve to probabilities
   - Formula: `calibrated_prob = 1 / (1 + exp(A×prob + B))`
   - Works well when model is roughly correct but probabilities are off

2. **'isotonic'**:
   - Fits a non-parametric monotonic function
   - More flexible but needs more data
   - Works better for very miscalibrated models

**In our code:**
```python
'method': 'sigmoid'  # Works well for logistic regression
```

**When to use which:**
- **Use 'sigmoid'**:
  - Model is logistic regression or similar
  - Medium dataset (100-10,000 samples)
  - Probabilities are somewhat reasonable

- **Use 'isotonic'**:
  - Large dataset (>10,000 samples)
  - Severely miscalibrated model
  - Tree-based models (Random Forest, XGBoost)

#### cv: 5 (Cross-Validation Folds)

**What it does:** Splits data into 5 parts for calibration.

**Process:**
```
Fold 1: Train on [2,3,4,5] → Calibrate on [1]
Fold 2: Train on [1,3,4,5] → Calibrate on [2]
Fold 3: Train on [1,2,4,5] → Calibrate on [3]
Fold 4: Train on [1,2,3,5] → Calibrate on [4]
Fold 5: Train on [1,2,3,4] → Calibrate on [5]

Final: Combine all 5 calibrated predictions
```

**Why 5?**
- Good balance between:
  - Computation time (more folds = slower)
  - Calibration quality (more folds = better)

**Alternatives:**
- `cv=3`: Faster but less accurate calibration
- `cv=10`: Slower but more accurate calibration
- `cv='prefit'`: Skip cross-validation (use if already trained)

---

## 3. XGBoost (Extreme Gradient Boosting)

### What is XGBoost?

**XGBoost** is a powerful ML algorithm that builds many **decision trees** and combines their predictions.

### Decision Tree Analogy

A decision tree is like a flowchart:

```
Is the number HOT?
├─ YES → Is recent_count > 2?
│        ├─ YES → Predict: Will appear (90%)
│        └─ NO  → Predict: Won't appear (60%)
└─ NO  → Is days_since_last < 30?
         ├─ YES → Predict: Might appear (50%)
         └─ NO  → Predict: Won't appear (80%)
```

### How XGBoost Differs from Logistic Regression

| Feature | Logistic Regression | XGBoost |
|---------|-------------------|---------|
| **Type** | Linear model | Tree ensemble |
| **Complexity** | Simple (straight line) | Complex (can model curves) |
| **Interpretability** | Easy (weights show importance) | Harder (many trees) |
| **Training Speed** | Fast | Slower |
| **Accuracy** | Good for linear relationships | Better for complex patterns |
| **Overfitting Risk** | Lower | Higher (needs tuning) |

### Real-World Comparison

**Logistic Regression:**
```
Predicts: Score = 0.3×is_hot + 0.2×recent_count - 0.1×days_since
          Prob = 1 / (1 + e^(-Score))

Good for: Simple, linear relationships
```

**XGBoost:**
```
Tree 1: If hot and recent_count>2 → +0.8
Tree 2: If medium and days<30 → +0.3
Tree 3: If cold and trend>0.5 → -0.2
...
Tree 150: Final adjustment → +0.05

Final: Sum all trees → Probability

Good for: Complex, non-linear interactions
```

---

### XGBoost Parameters Explained

#### 1. **n_estimators: 150**

**What it does:** Number of trees to build.

**Analogy:**
You're asking 150 experts for their opinion, then averaging:
- More experts = more accurate (but slower)
- Fewer experts = faster (but less accurate)

**In our code:**
```python
'n_estimators': 150  # Build 150 trees
```

**What happens if you change it:**

| n_estimators | Effect | Training Time |
|--------------|--------|---------------|
| **50** | Underfit, simple model | 33% faster |
| **100** | Decent accuracy | Fast |
| **150** | Good accuracy | Moderate |
| **300** | Better accuracy | 2× slower |
| **1000** | Marginal gains | 6× slower |

**How to tune:**
1. Start with 100
2. Increase until validation error stops improving
3. Stop when diminishing returns (not worth the time)

**Typical values:**
- Small dataset: 50-100
- Medium dataset: 100-300
- Large dataset: 500-1000

---

#### 2. **max_depth: 4**

**What it does:** Maximum levels in each tree.

**Analogy:**
Decision tree depth:
```
Depth 1:
  Is Hot?

Depth 2:
  Is Hot?
  ├─ Recent > 2?
  └─ Days < 30?

Depth 4:
  Is Hot?
  ├─ Recent > 2?
  │  ├─ Trend > 0?
  │  │  ├─ Volatility < 1?
  │  │  └─ ...
  └─ Days < 30?
     └─ ...
```

Deeper trees = more complex patterns = more overfitting risk

**In our code:**
```python
'max_depth': 4  # Trees can have up to 4 levels
```

**What happens if you change it:**

| max_depth | Effect | Overfitting Risk |
|-----------|--------|------------------|
| **2** | Very simple, underfit | Low |
| **3** | Simple, generalizes well | Low-Medium |
| **4** | Balanced (RECOMMENDED) | Medium |
| **6** | Complex, may overfit | Medium-High |
| **10** | Very complex, overfits | Very High |

**Rule of thumb:**
- Start with 3-4
- Increase if underfitting
- Decrease if overfitting

---

#### 3. **learning_rate: 0.1**

**What it does:** How much each tree contributes to the final prediction.

**Analogy:**
You're adjusting a recipe:
- **High learning rate (0.5)**: Make big changes each time
  - Faster to get close
  - Might overshoot the perfect taste

- **Low learning rate (0.01)**: Make tiny changes
  - Takes longer
  - More precise final result

**Technical Details:**
```
Prediction = lr × Tree1 + lr × Tree2 + ... + lr × Tree150

lr = 0.1:  Prediction = 0.1×Tree1 + 0.1×Tree2 + ...
lr = 0.01: Prediction = 0.01×Tree1 + 0.01×Tree2 + ...
```

**In our code:**
```python
'learning_rate': 0.1  # Standard learning rate
```

**What happens if you change it:**

| learning_rate | n_estimators | Training Time | Accuracy |
|---------------|--------------|---------------|----------|
| **0.01** | 1000-2000 | Very Slow | Highest |
| **0.05** | 300-500 | Slow | High |
| **0.1** | 100-300 | Moderate | Good |
| **0.3** | 50-100 | Fast | Decent |
| **1.0** | 10-30 | Very Fast | Poor |

**Trade-off:**
- Lower learning_rate + More trees = Better (but slower)
- Higher learning_rate + Fewer trees = Faster (but less accurate)

**Common combinations:**
```python
# Fast training (development)
'learning_rate': 0.3, 'n_estimators': 50

# Balanced (production)
'learning_rate': 0.1, 'n_estimators': 150

# High accuracy (competition)
'learning_rate': 0.01, 'n_estimators': 1000
```

---

#### 4. **subsample: 0.8**

**What it does:** Use only 80% of data to train each tree (random sampling).

**Analogy:**
Training 150 experts:
- **subsample=1.0**: Each expert sees ALL data
  - Experts might memorize (overfit)

- **subsample=0.8**: Each expert sees 80% of data (random)
  - Experts learn different patterns
  - Better generalization

**Technical Details:**
This is called **Stochastic Gradient Boosting**.

**In our code:**
```python
'subsample': 0.8  # Each tree uses 80% of draws
```

**What happens if you change it:**

| subsample | Effect |
|-----------|--------|
| **0.5** | High diversity, may underfit |
| **0.7** | Good diversity, prevents overfit |
| **0.8** | Balanced (RECOMMENDED) |
| **0.9** | Less diversity |
| **1.0** | No sampling, higher overfit risk |

**Benefits:**
- Reduces overfitting
- Speeds up training
- Adds randomness (better ensemble)

---

#### 5. **colsample_bytree: 0.7**

**What it does:** Use only 70% of features for each tree.

**Analogy:**
Building 150 models:
- **colsample_bytree=1.0**: All models use all features
  - Models might be too similar

- **colsample_bytree=0.7**: Each model uses 70% of features
  - Models learn different aspects
  - Like asking different questions to each expert

**In our code:**
```python
'colsample_bytree': 0.7  # Each tree uses 70% of features
```

**What happens if you change it:**

| colsample_bytree | Effect |
|------------------|--------|
| **0.3** | Very diverse trees, may lose info |
| **0.5** | High diversity |
| **0.7** | Good diversity (RECOMMENDED) |
| **0.8** | Moderate diversity |
| **1.0** | No sampling, less diversity |

**Why this helps:**
If your dataset has 50 features:
- Tree 1 might use: [recent_count, volatility, trend, ...]
- Tree 2 might use: [days_since, hmc_category, freshness, ...]
- Each tree specializes in different aspects!

---

#### 6. **min_child_weight: 3**

**What it does:** Minimum sum of sample weights needed in a child node.

**Analogy:**
Creating a new category in your decision tree:
- **min_child_weight=1**: Allow splits even if only 1 sample benefits
  - Very specific rules (overfitting)

- **min_child_weight=3**: Need at least 3 samples to create a split
  - More general rules (better generalization)

**Technical Details:**
This prevents creating overly specific rules.

**Example:**
```
Without min_child_weight:
  If number==37 AND recent_count==3 AND days==15 → Predict YES
  (Only 1 sample matches this rule → Overfitting!)

With min_child_weight=3:
  If recent_count>2 AND days<20 → Predict YES
  (Multiple samples match → Better generalization!)
```

**In our code:**
```python
'min_child_weight': 3  # Need at least 3 samples per leaf
```

**What happens if you change it:**

| min_child_weight | Effect |
|------------------|--------|
| **1** | Very detailed splits, overfit risk |
| **3** | Balanced (RECOMMENDED) |
| **5** | Conservative, prevents overfit |
| **10** | Very conservative, may underfit |

---

#### 7. **eval_metric: 'logloss'**

**What it does:** How to measure model performance during training.

**Analogy:**
Different ways to grade an exam:
- **Accuracy**: % of correct answers (simple)
- **Logloss**: Penalizes confident wrong answers more (sophisticated)

**Technical Details:**

**Logloss (Log Loss / Cross-Entropy):**
```
For each prediction:
  If actual=1: loss = -log(predicted_prob)
  If actual=0: loss = -log(1 - predicted_prob)

Average all losses = Final logloss
```

**Why logloss is better than accuracy:**

Example:
```
Model A (Accuracy=90%, Logloss=0.3):
  Number 7: Actual=YES, Predicted=90% → Good!
  Number 12: Actual=NO, Predicted=10% → Good!

Model B (Accuracy=90%, Logloss=2.5):
  Number 7: Actual=YES, Predicted=55% → Not confident
  Number 12: Actual=NO, Predicted=99% → VERY WRONG!
```

Both have 90% accuracy, but Model A is better (lower logloss).

**In our code:**
```python
'eval_metric': 'logloss'  # Optimize for probability accuracy
```

**Alternatives:**
- `'error'`: Simple classification error rate
- `'auc'`: Area under ROC curve
- `'map'`: Mean average precision

For lottery prediction, stick with **'logloss'**.

---

#### 8. **n_jobs: -1**

**What it does:** Number of CPU cores to use for training.

**Technical:**
- `-1`: Use all available CPU cores
- `1`: Use single core (slow)
- `4`: Use 4 cores

**In our code:**
```python
'n_jobs': -1  # Use all CPU cores for speed
```

**Effect on training time:**
```
1 core:  150 trees × 2 seconds = 300 seconds (5 minutes)
4 cores: 150 trees ÷ 4 = 37.5 trees × 2 seconds = 75 seconds
8 cores: 150 trees ÷ 8 = 18.75 trees × 2 seconds = 37.5 seconds
```

---

## 4. Statistical Testing

### Parametric vs Non-Parametric Tests

**Fundamental Question:** How do we know if a pattern is **real** or just **random noise**?

Statistical tests help us answer this with mathematical certainty.

---

### Parametric Tests (t-test, ANOVA)

#### What are Parametric Tests?

**Parametric tests** make **assumptions** about the data distribution (usually assume normal/Gaussian distribution).

**Analogy:**
You're comparing heights of two groups:
- Assume heights follow a bell curve (normal distribution)
- Use a t-test to see if average heights differ significantly

#### Assumptions:
1. **Normality**: Data follows a normal distribution (bell curve)
2. **Independence**: Samples are independent
3. **Homogeneity**: Equal variances between groups

#### Common Parametric Tests

##### 1. **T-Test (Compare 2 Groups)**

**Use Case:** Is there a significant difference between two groups?

**Example in Lottery:**
```
Question: Do HOT numbers have different volatility than COLD numbers?

Group 1: Volatility of HOT numbers  = [0.8, 0.9, 0.7, 0.85, ...]
Group 2: Volatility of COLD numbers = [1.2, 1.3, 1.1, 1.25, ...]

T-test result:
  t-statistic = 3.45
  p-value = 0.002

Conclusion: YES, significant difference (p < 0.05)
```

**Math (simplified):**
```
t = (mean1 - mean2) / (pooled_standard_error)

If |t| is large and p-value < 0.05:
  → Groups are significantly different
```

**Code:**
```python
from scipy.stats import ttest_ind

t_stat, p_value = ttest_ind(hot_volatility, cold_volatility)

if p_value < 0.05:
    print("Significant difference!")
```

---

##### 2. **ANOVA (Compare 3+ Groups)**

**Use Case:** Are there significant differences among 3 or more groups?

**Example in Lottery:**
```
Question: Do HOT, MEDIUM, COLD categories have different appearance rates?

Group 1 (HOT):    [15%, 18%, 16%, 17%, ...]
Group 2 (MEDIUM): [12%, 11%, 13%, 12%, ...]
Group 3 (COLD):   [8%, 7%, 9%, 8%, ...]

ANOVA result:
  F-statistic = 12.34
  p-value = 0.0001

Conclusion: YES, categories differ significantly
```

**Math (simplified):**
```
F = Variance_between_groups / Variance_within_groups

If F is large and p-value < 0.05:
  → At least one group is different
```

**Code:**
```python
from scipy.stats import f_oneway

f_stat, p_value = f_oneway(hot_rates, medium_rates, cold_rates)

if p_value < 0.05:
    print("Categories are significantly different!")
```

---

### Non-Parametric Tests (Mann-Whitney U, Kruskal-Wallis)

#### What are Non-Parametric Tests?

**Non-parametric tests** make **NO assumptions** about data distribution. They work with **ranks** instead of raw values.

**Analogy:**
Instead of comparing actual heights:
- Rank everyone from shortest (1) to tallest (N)
- Compare the ranks

This works even if heights aren't normally distributed!

#### When to Use Non-Parametric Tests

✅ **Use non-parametric when:**
1. Data is NOT normally distributed
2. Small sample size
3. Outliers are present
4. Data is ordinal (ranks, ratings)
5. You want to be safe (more robust)

#### Common Non-Parametric Tests

##### 1. **Mann-Whitney U Test (Compare 2 Groups)**

**Non-parametric alternative to t-test**

**Example:**
```
HOT numbers volatility:     [0.8, 0.9, 0.7, 15.0(outlier!), 0.85]
COLD numbers volatility:    [1.2, 1.3, 1.1, 1.25]

Problem: Outlier (15.0) violates t-test assumptions

Solution: Use Mann-Whitney U
  1. Rank all values: 0.7→1, 0.8→2, 0.85→3, ..., 15.0→9
  2. Compare rank sums instead of means

Result:
  U-statistic = 23
  p-value = 0.045

Conclusion: Significant difference (robust to outliers!)
```

**Code:**
```python
from scipy.stats import mannwhitneyu

u_stat, p_value = mannwhitneyu(hot_volatility, cold_volatility)

if p_value < 0.05:
    print("Significant difference (non-parametric)!")
```

---

##### 2. **Kruskal-Wallis Test (Compare 3+ Groups)**

**Non-parametric alternative to ANOVA**

**Example:**
```
Saturation rates (skewed distribution, not normal):

HOT:    [15%, 18%, 16%, 45%(outlier), 17%]
MEDIUM: [12%, 11%, 13%, 12%]
COLD:   [8%, 7%, 2%(outlier), 9%, 8%]

Problem: Outliers + skewed distribution

Solution: Use Kruskal-Wallis
  1. Rank all values across all groups
  2. Compare rank sums

Result:
  H-statistic = 8.72
  p-value = 0.013

Conclusion: Categories differ (robust!)
```

**Code:**
```python
from scipy.stats import kruskal

h_stat, p_value = kruskal(hot_rates, medium_rates, cold_rates)

if p_value < 0.05:
    print("Categories differ (non-parametric)!")
```

---

### Comparison: Parametric vs Non-Parametric

| Aspect | Parametric (t-test, ANOVA) | Non-Parametric (Mann-Whitney, Kruskal) |
|--------|----------------------------|----------------------------------------|
| **Assumptions** | Requires normal distribution | No distribution assumptions |
| **Data Type** | Continuous, normally distributed | Any distribution, ordinal, ranks |
| **Power** | More powerful (if assumptions met) | Less powerful but more robust |
| **Sample Size** | Works well with large samples | Works well with small samples |
| **Outliers** | Sensitive to outliers | Robust to outliers |
| **Use When** | Data is normal | Data is skewed, has outliers |

---

### Visual Comparison

```
Normal Distribution (Use Parametric):
         ╱▔▔╲
       ╱      ╲
     ╱          ╲
   ╱              ╲
 ╱                  ╲
▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁

Skewed Distribution (Use Non-Parametric):
  ╱▔▔╲
 ╱    ╲
╱      ╲▁▁▁▁▁▁▁▁▁▁▁▁
```

---

### Normality Testing (Shapiro-Wilk)

**How to check if data is normal?**

Use **Shapiro-Wilk test**:

```python
from scipy.stats import shapiro

stat, p_value = shapiro(data)

if p_value > 0.05:
    print("Data is normal → Use parametric tests")
else:
    print("Data is NOT normal → Use non-parametric tests")
```

---

### Decision Flow Chart

```
                    Have data to compare?
                           │
                           ▼
                  How many groups?
                   │              │
                   ▼              ▼
              2 groups        3+ groups
                   │              │
                   ▼              ▼
          Is data normal?    Is data normal?
           │         │        │         │
           ▼         ▼        ▼         ▼
         YES       NO       YES       NO
           │         │        │         │
           ▼         ▼        ▼         ▼
       t-test   Mann-      ANOVA   Kruskal-
                Whitney              Wallis
```

---

### P-Value Interpretation

**What is a p-value?**

The probability that the observed difference happened by random chance.

```
p-value = 0.001  → 0.1% chance of randomness → VERY significant ✓✓✓
p-value = 0.01   → 1% chance of randomness   → Significant ✓✓
p-value = 0.04   → 4% chance of randomness   → Significant ✓
p-value = 0.06   → 6% chance of randomness   → Not significant ✗
p-value = 0.50   → 50% chance of randomness  → Definitely not significant ✗✗
```

**Standard threshold:** p < 0.05 (5%)

---

## 5. Feature Engineering

### What is Feature Engineering?

**Feature engineering** is the process of creating useful input variables (features) from raw data.

**Analogy:**
Raw data = Raw ingredients (flour, eggs, sugar)
Features = Prepared ingredients (dough, frosting)
Model = Oven that bakes the cake

Good features make it easier for the model to learn!

---

### Feature Types in Lottery System

#### 1. **Temporal Features** (Time-based)

**Examples:**
- `days_since_last_appearance`: How many days since this number last appeared?
- `recent_count`: How many times appeared in last 10 draws?
- `draws_since_last`: How many draws since last appearance?

**Why useful:**
Hot numbers might appear again soon!

---

#### 2. **Statistical Features**

**Examples:**
- `appearance_volatility`: How unpredictable is this number's timing?
- `appearance_trend`: Is this number trending up or down?
- `gap_consistency_score`: How consistent are the gaps between appearances?

**Why useful:**
Identifies numbers with changing behavior patterns.

---

#### 3. **Categorical Features**

**Examples:**
- `hmc_category`: HOT, MEDIUM, or COLD
- `freshness_category`: Fresh vs Stale numbers

**Why useful:**
Different categories behave differently.

---

#### 4. **Interaction Features**

**Examples:**
- `hot_and_trending`: Is number HOT AND trending up?
- `cold_but_fresh`: Is number COLD but appeared recently?

**Why useful:**
Captures combinations that matter.

---

### Feature Scaling

**Why scale features?**

Different features have different ranges:
- `recent_count`: 0-10
- `days_since_last`: 0-500
- `volatility`: 0.1-5.0

Without scaling, features with larger ranges dominate!

**Solution: StandardScaler**

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
scaled_features = scaler.fit_transform(features)

# After scaling, all features have:
# - Mean = 0
# - Standard deviation = 1
```

**Example:**
```
Before scaling:
  recent_count: [0, 1, 5, 10]         Range: 10
  days_since:   [0, 50, 200, 500]     Range: 500  (Dominates!)

After scaling:
  recent_count: [-1.2, -0.8, 0.5, 1.5]  Range: ~3
  days_since:   [-1.3, -0.6, 0.4, 1.5]  Range: ~3  (Balanced!)
```

---

## 6. Model Training & Evaluation

### Train-Test Split

**Why split data?**

You can't test a student on questions they've already seen!

Similarly, we need to test models on **unseen data**.

**Process:**
```
All data (1000 draws):
  ├─ Training set (800 draws, 80%): Teach the model
  └─ Test set (200 draws, 20%):     Evaluate the model

Model never sees test set during training!
```

**Code:**
```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,      # 20% for testing
    random_state=42     # Reproducible split
)
```

---

### Cross-Validation

**Problem with single train-test split:**
Results might depend on which data ended up in test set.

**Solution: K-Fold Cross-Validation**

**Process (K=5):**
```
Fold 1: Train [2,3,4,5] Test [1]  → Score: 85%
Fold 2: Train [1,3,4,5] Test [2]  → Score: 87%
Fold 3: Train [1,2,4,5] Test [3]  → Score: 83%
Fold 4: Train [1,2,3,5] Test [4]  → Score: 86%
Fold 5: Train [1,2,3,4] Test [5]  → Score: 84%

Average: (85 + 87 + 83 + 86 + 84) / 5 = 85%
```

Every sample is used for testing exactly once!

**Code:**
```python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(model, X, y, cv=5)
print(f"Average score: {scores.mean():.3f} (+/- {scores.std():.3f})")
```

---

### Evaluation Metrics

#### 1. **Accuracy**

**Formula:**
```
Accuracy = (Correct Predictions) / (Total Predictions)
```

**Example:**
```
Predicted 47 numbers:
  - 5 correct (will appear)
  - 42 correct (won't appear)

Accuracy = 47/47 = 100%
```

**Problem:** Misleading for imbalanced data!

```
Always predict "won't appear":
  - 0/6 correct for appearing numbers
  - 41/41 correct for non-appearing numbers
  - Accuracy = 41/47 = 87% (looks good but useless!)
```

---

#### 2. **Precision & Recall**

**Precision:** Of all predicted positives, how many are actually positive?
```
Precision = True Positives / (True Positives + False Positives)
```

**Recall:** Of all actual positives, how many did we find?
```
Recall = True Positives / (True Positives + False Negatives)
```

**Example:**
```
Actual winning numbers: [3, 7, 12, 19, 28, 35]
Predicted: [3, 7, 9, 12, 15, 28]

True Positives: [3, 7, 12, 28] = 4
False Positives: [9, 15] = 2
False Negatives: [19, 35] = 2

Precision = 4/(4+2) = 4/6 = 67%  (Of 6 predicted, 4 were correct)
Recall = 4/(4+2) = 4/6 = 67%     (Of 6 actual, we found 4)
```

---

#### 3. **F1-Score**

**Harmonic mean of Precision and Recall**

```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

Balances precision and recall.

---

#### 4. **ROC-AUC**

**ROC Curve:** Plots True Positive Rate vs False Positive Rate
**AUC:** Area Under the ROC Curve

```
AUC = 1.0  → Perfect model
AUC = 0.9  → Excellent
AUC = 0.8  → Good
AUC = 0.7  → Fair
AUC = 0.5  → Random guessing (useless!)
```

> **This general scale does not apply to this project.** Irish Lotto is a fair draw, so ~0.50 is the
> correct and expected result, not a failure. All six models sit close to 0.50. An AUC of 0.7+ here
> would mean a bug - lookahead, leakage, or a model that has memorised the training set. Do not treat
> the scale above as a target. See `metrics.md` for the real numbers and the noise floor.

---

### Overfitting vs Underfitting

#### Overfitting (Memorization)

**Problem:** Model memorizes training data but fails on new data.

**Analogy:**
Student memorizes exact exam questions but can't solve variations.

**Signs:**
```
Training accuracy: 98%
Test accuracy: 65%
→ Overfitting!
```

**Solutions:**
- Increase regularization (lower C)
- Reduce model complexity (fewer trees, smaller max_depth)
- Add more data
- Use cross-validation

---

#### Underfitting (Too Simple)

**Problem:** Model is too simple to learn patterns.

**Analogy:**
Student only learns "all answers are A" (too simple).

**Signs:**
```
Training accuracy: 60%
Test accuracy: 58%
→ Underfitting!
```

**Solutions:**
- Decrease regularization (higher C)
- Increase model complexity (more trees, deeper trees)
- Add more features
- Try more powerful algorithm (switch from Logistic to XGBoost)

---

#### Perfect Balance

```
Training accuracy: 82%
Test accuracy: 80%
→ Good fit! ✓
```

---

## 7. Ensemble Methods

### What is an Ensemble?

**Ensemble** = Combining multiple models to make better predictions.

**Analogy:**
Instead of asking 1 expert, ask 10 experts and vote!

---

### Types of Ensembles

#### 1. **Voting Ensemble**

**Process:**
```
Model 1 predicts: [3, 7, 12, 19, 28, 35]
Model 2 predicts: [3, 9, 12, 15, 28, 35]
Model 3 predicts: [3, 7, 12, 19, 28, 30]

Voting:
  Number 3:  3 votes → Include ✓
  Number 7:  2 votes → Include ✓
  Number 9:  1 vote  → Exclude ✗
  Number 12: 3 votes → Include ✓
  ...
```

**In this project:** not used. A voting ensemble existed but was never wired into the pipeline and
was deleted (F-6, 2026-09-19). Averaging only cancels mistakes when each model has some real signal;
every model here sits at chance, so a vote between them is at chance too. Random Forest (bagging)
and XGBoost (boosting), below, are ensembles inside a single model.

---

#### 2. **Bagging (Bootstrap Aggregating)**

**Process:**
1. Create multiple datasets by random sampling with replacement
2. Train a model on each dataset
3. Average predictions

**Example: Random Forest**
- Trains many decision trees on different random subsets
- Averages their predictions

---

#### 3. **Boosting**

**Process:**
1. Train first model
2. Find mistakes
3. Train second model to fix mistakes
4. Repeat

**Example: XGBoost**
Each new tree focuses on correcting previous trees' errors.

---

### Why Ensembles Work

**Wisdom of the crowd:**
- Individual models make different mistakes
- By combining, mistakes cancel out
- Collective prediction is more accurate

**Math proof (simplified):**
```
If each model has 70% accuracy (independent):

1 model:  70% accuracy
3 models: 78% accuracy (majority vote)
5 models: 82% accuracy
10 models: 87% accuracy
```

---

## 8. Advanced Concepts

### 1. **Scipy Optimization**

**What:** Finding the best parameters automatically.

**Example in our system:**
```python
from scipy.optimize import differential_evolution

def objective(penalty_weights):
    # Calculate how good these weights are
    score = evaluate_penalties(weights)
    return score  # Lower is better

# Find optimal weights
result = differential_evolution(objective, bounds=[(0.1, 2.0)] * 9)
optimal_weights = result.x
```

**Use cases:**
- Optimize penalty weights for saturation filtering
- Find best hyperparameters
- Maximize prediction accuracy

---

### 2. **Time Series Analysis**

**Tools used:**
- `savgol_filter`: Smooth noisy data
- `detrend`: Remove long-term trends
- `find_peaks`: Find peaks and troughs
- `kendalltau`: Test trend significance

**Example:**
```python
from scipy.signal import savgol_filter

# Noisy frequency data
raw_freq = [0.1, 0.3, 0.2, 0.4, 0.35, 0.5, 0.45, ...]

# Smooth it
smoothed = savgol_filter(raw_freq, window_length=11, polyorder=3)

# Now we can detect real trends vs noise
```

---

### 3. **Calibration**

**Problem:** Model says "80% probability" but it's actually 60%.

**Solution:** Calibration adjusts probabilities to match reality.

**Calibration Curve:**
```
Predicted   Actual
10%    →    10%  ✓ Well calibrated
30%    →    30%  ✓
50%    →    45%  ✗ Slightly off
70%    →    60%  ✗ Overconfident
90%    →    85%  ✗ Overconfident
```

---

### 4. **Feature Importance**

**Which features matter most?**

**For Logistic Regression:**
- Look at coefficient weights
- Large absolute values = more important

**For XGBoost:**
```python
import matplotlib.pyplot as plt
from xgboost import plot_importance

plot_importance(model)
plt.show()

# Shows which features are used most often
```

**Example output:**
```
recent_count:        0.25  (Most important!)
hmc_category:        0.18
days_since_last:     0.15
trend:               0.12
volatility:          0.10
...
```

---

## 9. Glossary

| Term | Definition |
|------|------------|
| **Algorithm** | Set of rules/steps to solve a problem |
| **Bias** | Systematic error (model assumptions) |
| **Classification** | Predicting categories (yes/no, hot/medium/cold) |
| **Cross-Validation** | Testing model on multiple train/test splits |
| **Epoch** | One pass through entire training dataset |
| **Feature** | Input variable (attribute) used for prediction |
| **Gradient** | Direction of steepest increase (used in optimization) |
| **Hyperparameter** | Parameter set before training (e.g., learning_rate) |
| **Label** | Output variable (what we're predicting) |
| **Loss Function** | Measure of how wrong predictions are |
| **Overfitting** | Model memorizes training data, fails on new data |
| **Parameter** | Value learned during training (weights, biases) |
| **Regularization** | Technique to prevent overfitting |
| **Training** | Process of teaching model from data |
| **Validation** | Testing model on held-out data |
| **Variance** | Error from model sensitivity to training data |

---

## Quick Reference: When to Use What

### Algorithm Selection

```
┌─────────────────────────────────────────┐
│ Is relationship LINEAR?                 │
├─────────────────────────────────────────┤
│ YES → Logistic Regression              │
│  ✓ Fast, interpretable                 │
│  ✓ Good for simple patterns            │
├─────────────────────────────────────────┤
│ NO → XGBoost                           │
│  ✓ Handles complex interactions        │
│  ✓ Better accuracy (usually)           │
└─────────────────────────────────────────┘
```

### Statistical Test Selection

```
┌─────────────────────────────────────────┐
│ Is data NORMALLY distributed?          │
├─────────────────────────────────────────┤
│ YES → Parametric (t-test, ANOVA)      │
│  ✓ More powerful                       │
│  ✓ Precise p-values                    │
├─────────────────────────────────────────┤
│ NO → Non-Parametric (Mann-Whitney,    │
│      Kruskal-Wallis)                   │
│  ✓ Robust to outliers                  │
│  ✓ No assumptions needed               │
└─────────────────────────────────────────┘
```

### Hyperparameter Tuning

```
┌─────────────────────────────────────────┐
│ Model OVERFITTING?                      │
├─────────────────────────────────────────┤
│ Logistic Regression:                    │
│  → Decrease C (0.1 or 0.01)            │
│  → Use L1 penalty                       │
├─────────────────────────────────────────┤
│ XGBoost:                                │
│  → Decrease max_depth (3 or 2)         │
│  → Decrease learning_rate (0.05)       │
│  → Increase min_child_weight (5 or 10) │
│  → Decrease subsample (0.6 or 0.7)     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Model UNDERFITTING?                     │
├─────────────────────────────────────────┤
│ Logistic Regression:                    │
│  → Increase C (10 or 100)              │
│  → Add more features                    │
├─────────────────────────────────────────┤
│ XGBoost:                                │
│  → Increase max_depth (6 or 8)         │
│  → Increase n_estimators (300 or 500)  │
│  → Increase learning_rate (0.3)        │
└─────────────────────────────────────────┘
```

---

## Summary

This lottery prediction system uses:

1. **Two ML algorithms:**
   - Logistic Regression (simple, linear)
   - XGBoost (complex, non-linear)

2. **Statistical validation:**
   - Parametric tests (t-test, ANOVA) for normal data
   - Non-parametric tests (Mann-Whitney, Kruskal) for robustness

3. **Feature engineering:**
   - Temporal features (recent counts, days since)
   - Statistical features (volatility, trends)
   - Categorical features (HMC, freshness)

4. **Optimization:**
   - Scipy optimization for penalty weights
   - Time series analysis for trends
   - Calibration for accurate probabilities

5. **Ensemble methods:**
   - Multiple models voting
   - Boosting (XGBoost)
   - Stochastic sampling

All working together to predict lottery numbers based on historical patterns!

---

## Further Reading

- **Scikit-learn documentation:** https://scikit-learn.org/
- **XGBoost documentation:** https://xgboost.readthedocs.io/
- **Scipy documentation:** https://docs.scipy.org/
- **"An Introduction to Statistical Learning"** by James et al. (free PDF)
- **"Hands-On Machine Learning"** by Aurélien Géron

---

**End of Guide**

*Questions? Review the relevant section or consult the documentation links above.*
