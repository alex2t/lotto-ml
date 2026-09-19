# Scripts Directory

This directory contains standalone utility scripts for advanced ML lottery prediction tasks.

## 📁 Contents

- **train_with_all_features.py** - Comprehensive training demonstration script

---

## 🚀 train_with_all_features.py

### Description

A comprehensive training demonstration script that showcases all advanced ML features available in the lotto-ml system. This script serves as both a working example and a template for implementing sophisticated ML pipelines.

### Features Demonstrated

1. **✅ SMOTE** - Class balancing for imbalanced datasets
2. **✅ Optimal Threshold Selection** - Find best decision boundaries
3. **✅ Feature Selection** - Correlation and importance-based filtering
4. **✅ Rolling Statistics** - Temporal feature engineering (9 features per number)
5. **✅ Hyperparameter Tuning** - TimeSeriesSplit cross-validation
6. **✅ Enhanced Metrics** - Top-K accuracy, PR-AUC, calibration

### Usage

#### Basic Run

```bash
python scripts/train_with_all_features.py
```

The script will:
- Load lottery draw history
- Extract all features including rolling statistics
- Train multiple models with all optimizations enabled
- Compare model performance
- Save results to `model_metrics/` directory

### Configuration

Edit the script to customize:

```python
# Model configurations (lines 34-48)
MODEL_CONFIGS = [
    {
        'name': 'Model1_RF_Tuned',
        'description': 'Random Forest with all features enabled',
        'algorithm': 'random_forest',
        'features': ['all']
    },
    {
        'name': 'Model2_Logistic_Tuned',
        'description': 'Logistic Regression with all features enabled',
        'algorithm': 'logistic',
        'features': ['all']
    }
]

# Training parameters (lines 147-166)
pipeline, features, importance, metrics, tuning_results = train_model(
    model_config=model_config,
    train_df=train_df,
    all_feature_names=all_feature_names,
    model_index=idx,
    exclude_bonus=False,
    val_df=val_df,
    # SMOTE settings
    use_smote=True,
    smote_sampling_strategy=0.3,
    # Feature selection settings
    enable_feature_selection=True,
    correlation_threshold=0.95,
    importance_threshold=0.005,
    # Hyperparameter tuning settings
    enable_hyperparameter_tuning=True,
    tuning_mode='quick',  # or 'extensive' for comprehensive search
    tuning_cv_splits=3,
    tuning_scoring='f1'
)
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_smote` | `True` | Enable SMOTE oversampling |
| `smote_sampling_strategy` | `0.3` | Ratio of minority to majority class |
| `enable_feature_selection` | `True` | Enable automatic feature selection |
| `correlation_threshold` | `0.95` | Remove features with correlation > threshold |
| `importance_threshold` | `0.005` | Remove features with importance < threshold |
| `enable_hyperparameter_tuning` | `True` | Enable grid/random search |
| `tuning_mode` | `'quick'` | 'quick' or 'extensive' |
| `tuning_cv_splits` | `3` | Cross-validation folds |
| `tuning_scoring` | `'f1'` | Scoring metric for tuning |

### Output Files

The script generates multiple output files in `model_metrics/`:

```
model_metrics/
├── model_comparison.csv              # Model performance comparison
├── tuning_comparison.csv             # Hyperparameter tuning results
├── Model1_RF_Tuned_tuning_results.json
├── Model2_Logistic_Tuned_tuning_results.json
├── Model1_RF_Tuned_roc_curve.png
├── Model1_RF_Tuned_pr_curve.png
├── Model1_RF_Tuned_calibration.png
└── ... (similar files for each model)
```

### Example Output

```
================================================================================
  🚀 COMPREHENSIVE ML TRAINING WITH ALL FEATURES
================================================================================

Enabled Features:
  ✅ SMOTE (class balancing)
  ✅ Optimal threshold selection
  ✅ Feature selection (correlation + importance)
  ✅ Rolling statistics (9 temporal features per number)
  ✅ Hyperparameter tuning with TimeSeriesSplit CV
  ✅ Enhanced metrics (Top-K accuracy, PR-AUC)
================================================================================

📂 Loading data...
   Loaded 1500 draws

📊 Extracting rolling statistics features...
   Extracted 9 rolling features per number

🔧 Extracting all features...
   Extracted 45 features

📚 Building training and validation datasets...
   Training set: 12000 samples
   Validation set: 3000 samples

🎯 Training models with all features enabled...
================================================================================

→ Model 1: Model1_RF_Tuned
  Description: Random Forest with all features enabled
  Algorithm: random_forest

🔧 Starting hyperparameter tuning (quick mode)...
   Best parameters: {'max_depth': 10, 'n_estimators': 200}
   Best CV score (f1): 0.3456

✓ Training complete

📊 MODEL EVALUATION: Model1_RF_Tuned
======================================================================
  Train Accuracy: 0.8523
  Val Accuracy:   0.8234

  🎯 AUC-ROC Scores:
     Train AUC: 0.7234
     Val AUC:   0.6912

  📈 Top-K Accuracy:
     Top-7:  0.4285 (43% of draws hit at least 1 number)
     Top-10: 0.5714 (57% of draws hit at least 1 number)
     Top-15: 0.7142 (71% of draws hit at least 1 number)

[... similar output for Model 2 ...]

📊 Comparing all models...

================================================================================
  ✅ TRAINING COMPLETE!
================================================================================

📊 Summary:
   Models trained: 2
   Features per model: 38 (after selection)
   Hyperparameter tuning: ✅ Completed

📁 Results saved to:
   model_metrics/model_comparison.csv
   model_metrics/tuning_comparison.csv
   model_metrics/*_tuning_results.json

💡 Next steps:
   1. Review model_comparison.csv for best model
   2. Check Top-K accuracy (most relevant for lottery)
   3. Adjust tuning_mode to 'extensive' for better results
================================================================================
```

### When to Use This Script

- **Learning** - Understand how all ML features work together
- **Experimentation** - Test different configurations and parameters
- **Prototyping** - Quick testing before integrating into main pipeline
- **Benchmarking** - Compare performance with/without specific features

### Integration into Main Pipeline

To integrate these features into `quickpick.py`:

1. Import the training function with parameters:
```python
from ml_lotto.models.trainer import train_model
```

2. Add parameters to your training calls:
```python
pipeline, features, importance, metrics, tuning_results = train_model(
    model_config=config,
    train_df=train_df,
    all_feature_names=all_features,
    model_index=idx,
    val_df=val_df,
    use_smote=True,
    enable_feature_selection=True,
    enable_hyperparameter_tuning=True,
    tuning_mode='quick'
)
```

3. Handle the additional return values:
```python
# Store tuning results
all_tuning_results[model_name] = tuning_results

# Compare tuning results at the end
from ml_lotto.models.hyperparameter_tuning import compare_tuning_results
tuning_comparison = compare_tuning_results(all_tuning_results)
```

---

## 🧪 Testing

Test files for these scripts are located in the `tests/` directory:

- `demos/demo_train_with_all_features.py` - Demo of the comprehensive training pipeline (not a test)

Run tests with:

```bash
# Test comprehensive training
python -m demos.demo_train_with_all_features
```

---

## 📚 Related Documentation

- **ML Concepts** - `docs/ML_CONCEPTS_GUIDE.md`
- **Feature Reference** - `docs/ML_FEATURES_REFERENCE.md`
- **Metrics Guide** - `docs/METRICS_IMPLEMENTATION_SUMMARY.md`

---

## 💡 Tips

1. **Start with train_with_all_features.py** to understand the full ML pipeline
2. **Check model_metrics/** directory for detailed performance analysis
3. **Monitor Top-K accuracy** - this is the most relevant metric for lottery prediction

---

## 🐛 Troubleshooting

### "Module not found" errors
- Ensure you're running from the project root directory
- Install dependencies: `pip install -r requirements.txt`

### Slow performance
- Use `tuning_mode='quick'` instead of `'extensive'`
- Reduce `tuning_cv_splits` from 5 to 3
- Disable feature selection for faster training

### Out of memory errors
- Reduce training data size
- Disable SMOTE (`use_smote=False`)
- Use simpler models (logistic regression vs random forest)
