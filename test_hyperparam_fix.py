"""
Quick test to verify hyperparameter tuning improvements.
This simulates imbalanced lottery data to test the zero-score handling.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

from ml_lotto.models.hyperparameter_tuning import quick_tune

# Create highly imbalanced synthetic data (like lottery)
np.random.seed(42)
n_samples = 500
n_features = 15

X_train = np.random.randn(n_samples, n_features)
# Very imbalanced: 2% positive class (similar to lottery odds)
y_train = np.random.choice([0, 1], size=n_samples, p=[0.98, 0.02])

print(f"\n{'='*80}")
print(f"Testing Hyperparameter Tuning with Imbalanced Data")
print(f"{'='*80}")
print(f"Training samples: {n_samples}")
print(f"Features: {n_features}")
print(f"Positive class: {sum(y_train)} ({sum(y_train)/len(y_train)*100:.1f}%)")
print(f"Negative class: {len(y_train) - sum(y_train)} ({(len(y_train) - sum(y_train))/len(y_train)*100:.1f}%)")

# Create pipeline
base_clf = LogisticRegression(random_state=42, max_iter=1000)
calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method='isotonic', cv=3)
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', calibrated_clf)
])

print(f"\n{'='*80}")
print(f"Test 1: Using F1 scoring (likely to show zero scores)")
print(f"{'='*80}")

# Test with F1 (likely to get zeros)
best_pipeline_f1, results_f1 = quick_tune(
    pipeline=pipeline,
    X_train=X_train,
    y_train=y_train,
    model_type='logistic',
    model_name='TestLogistic_F1',
    cv_splits=3,
    scoring='f1',
    n_jobs=1
)

print(f"\n{'='*80}")
print(f"Test 2: Using ROC-AUC scoring (should show meaningful differences)")
print(f"{'='*80}")

# Test with ROC-AUC (should work better)
pipeline2 = Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', CalibratedClassifierCV(
        estimator=LogisticRegression(random_state=42, max_iter=1000),
        method='isotonic',
        cv=3
    ))
])

best_pipeline_auc, results_auc = quick_tune(
    pipeline=pipeline2,
    X_train=X_train,
    y_train=y_train,
    model_type='logistic',
    model_name='TestLogistic_ROCAUC',
    cv_splits=3,
    scoring='roc_auc',
    n_jobs=1
)

print(f"\n{'='*80}")
print(f"COMPARISON")
print(f"{'='*80}")
print(f"F1 Score Results:")
print(f"  Best Score: {results_f1['best_score']:.6f}")
print(f"  Total Configurations: {results_f1['total_fits']}")
print(f"\nROC-AUC Score Results:")
print(f"  Best Score: {results_auc['best_score']:.6f}")
print(f"  Total Configurations: {results_auc['total_fits']}")
print(f"\n{'='*80}")
print(f"✅ Test Complete - Check output above for warnings and recommendations")
print(f"{'='*80}\n")
