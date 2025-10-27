# Lottery Prediction System V3.1 - Modular Architecture

## 📁 Project Structure

```
lotto-ml-system/
├── lotto_ml_analysys.py                          # Root level
├── data/                            # Data folder
│   ├── irish500.csv
│   ├── lotto_trigger_periods.json
│   └── lotto_odds_results.json
└── ml_lotto/                        # Code folder
    ├── __init__.py                  # Makes it a package
    ├── config.py
    ├── data_loader.py
    ├── feature_extractor.py
    ├── model_trainer.py
    ├── predictor.py
    └── display.py

lotto_analysis_project/
├── lotto_analysis/              # Main package
│   ├── config/
│   │   ├── config.py           # All configuration constants
│   │   └── __init__.py
│   ├── core/
│   │   ├── data_loader.py      # CSV loading & parsing
│   │   └── __init__.py
│   ├── analyzers/
│   │   ├── frequency_analyzer.py    # Frequency calculations
│   │   ├── pattern_analyzer.py      # Pattern detection
│   │   ├── consecutive_analyzer.py  # Consecutive runs
│   │   ├── hmc_analyzer.py          # HMC analysis
│   │   └── __init__.py
│   ├── utils/
│   │   ├── output_generator.py # Output generation
│   │   └── __init__.py
│   └── __init__.py
├
├── data/                            # Data folder
│   ├── irish500.csv
│   ├── lotto_trigger_periods.json
│   ├── lotto_trigger_periods.json
│   └── lotto_odds_results.json
├── main.py                      # Entry point
├── requirements.txt
├── README.md
└── .gitignore
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install pandas numpy scikit-learn xgboost
```

### 2. Run the System
```bash
python main.py
```

### 3. Customize Models
Edit `config.py` to change:
- Feature selection for each model
- HMC ratios (Hot-Medium-Cold-Generic)
- Diversity penalties
- Algorithm parameters

## 📝 Feature Selection Guide

### Available Features:
- `total_count` - Total historical appearances
- `days_since_last` - Days since last draw
- `recent_4`, `recent_6`, `recent_8`, `recent_9`, `recent_14` - Recent activity
- `series_total` - Total streak patterns
- `series_recent` - Recent streak patterns (60 days)

### Special Keywords:
- **`'ALL'`** - Use all available features
- **`'RECENT_ALL'`** - Use all recent_X features
- **`'RECENT_SHORT'`** - Use shortest recent window
- **`'RECENT_LONG'`** - Use longest recent window

### Example Configurations:

```python
# Conservative model - long-term patterns
'features': ['total_count', 'series_total', 'RECENT_LONG']

# Aggressive model - recent activity
'features': ['RECENT_SHORT', 'days_since_last']

# Balanced model - everything
'features': 'ALL'
```

## 🎯 Adding New Models

Edit `config.py`:

```python
MODEL_4_CONFIG = {
    'name': 'Experimental Model',
    'description': 'Testing new features',
    'algorithm': 'xgboost',
    'hot_count': 1,
    'medium_count': 4,
    'cold_count': 1,
    'generic_count': 1,
    'features': ['recent_4', 'recent_6', 'series_recent'],
    'diversity_penalty': 0.20,
    'algorithm_params': { ... },
    'calibration': { ... }
}

# Add to active models
ACTIVE_MODELS = [
    MODEL_1_CONFIG,
    MODEL_2_CONFIG,
    MODEL_3_CONFIG,
    MODEL_4_CONFIG  # Your new model
]
```

## 📊 Understanding Output

```
Line 1: Standard Model [0H-3M-2C+1G]
Numbers: [7, 13, 20, 28, 35, 42]
```
- **0H-3M-2C+1G**: 0 Hot, 3 Medium, 2 Cold, 1 Generic

## 🔧 Module Descriptions

- **config.py**: Edit frequently - customize models
- **data_loader.py**: Edit rarely - only if file format changes
- **feature_extractor.py**: Edit sometimes - to add new feature types
- **model_trainer.py**: Edit sometimes - to add new algorithms
- **predictor.py**: Edit sometimes - to modify penalty logic
- **display.py**: Edit sometimes - to change output format
- **main.py**: Edit rarely - only to change workflow


## 🆘 Troubleshooting

### Models predicting similar numbers
- Increase diversity_penalty values
- Use different feature sets for each model

---

**Version**: 3.1  
**Last Updated**: 2025
