"""
Configuration settings for lottery analysis
"""

# =============== ANALYSIS CONFIGURATION (for the Analysis Generation System, drawpick.py) ===============
TOTAL_DRAWS = 600          # Total number of draws to analyze
TRAINING_DATA = 100        # Initial training window size for HMC analysis
NUM_DRAWS = TOTAL_DRAWS - TRAINING_DATA  # Draws used for pattern analysis
TRAINING_START_DRAW = TRAINING_DATA

# =============== FILE PATHS ===============
# CSV_FILE = 'data/irish500.csv'  # Path to CSV file (DEPRECATED FOR ML SYSTEM)
DRAW_HISTORY_JSON = 'data/lotto_draw_history.json' # Comprehensive Draw History (New ML Source)
HMC_JSON_INPUT = 'data/lotto_trigger_periods.json'  # Per-number stats
ODDS_JSON_INPUT = 'data/lotto_odds_results.json'    # HMC patterns

# =============== LOTTERY PARAMETERS ===============
MAX_NUMBER = 47            # Maximum lottery number
HOT_COUNT = 15             # Number of hot numbers
COLD_COUNT = 15           # Number of cold numbers

# =============== ANALYSIS SCENARIOS (Master definition for analysis windows) ===============
# Window sizes and target repetition counts to detect
SCENARIOS = [
    {"window": 5,  "targets": [3]},
    {"window": 7,  "targets": [4]},
    {"window": 10, "targets": [4]},
    {"window": 15, "targets": [5]}
]

# Window sizes for per-draw historical 'recent_counts'
# Derived from SCENARIOS, ensuring consistency: [5, 7, 10, 15]
# Note: The key name uses window-1 (e.g., last_4 for window 5), which is handled in hmc_analyzer.py
ACTUAL_HISTORY_WINDOWS = [s["window"] for s in SCENARIOS] 

# =============== RANGE BINS ===============
# Define the Range Bins for draw range analysis
RANGE_BINS = {
    "20-25": (20, 25),
    "25-30": (25, 30),
    "30-35": (30, 35),
    "35-40": (35, 40),
    "40-45": (40, 45)
}

# ==================== ML MODEL CONFIGURATIONS (Duplicated from ML system config) ====================
# This is a placeholder for the ML config if it were in this file, but we include 
# the necessary constants to ensure the ML system runs.

# ==================== AVAILABLE FEATURES (Placeholder documentation for ML) ====================
"""
...
NEW CUSTOM FEATURE (calculated in feature_extractor.py from Draw History):
    - 'days_since_bonus': Days since the number was last drawn as the bonus ball.

SPECIAL VALUES:
    ...
    - 'BONUS_AWARE': Expands to the 'days_since_bonus' feature
"""

# ==================== EXAMPLE ML MODEL CONFIGURATIONS ====================

MODEL_1_CONFIG = {
    'name': 'Standard Model',
    'description': 'Comprehensive Linear Model - Focus on Recent Activity',
    'algorithm': 'logistic_regression',
    
    # HMC Selection (Hot-Medium-Cold-Generic)
    'hot_count': 0,
    'medium_count': 3,
    'cold_count': 2,
    'generic_count': 1,  # Auto-fill from top probabilities
    
    # Feature Selection
    # Options: List of features, 'ALL', 'RECENT_ALL', 'RECENT_SHORT', 'RECENT_LONG', 'BONUS_AWARE'
    'features': 'ALL',  # Use all available features
    
    # Diversity Penalty
    'diversity_penalty': 0.0,  # No penalty (baseline model)
    
    # Algorithm-specific parameters
    'algorithm_params': {
        'penalty': 'l2',
        'solver': 'liblinear',
        'max_iter': 1000,
        'class_weight': 'balanced',
        'random_state': 42,
        'C': 0.3
    },
    
    # Calibration settings
    'calibration': {
        'method': 'sigmoid',
        'cv': 3
    }
}

MODEL_2_CONFIG = {
    'name': 'Historical Model',
    'description': 'Conservative Model - Focus on Long-term Patterns + Bonus Avoidance',
    'algorithm': 'logistic_regression',
    
    # HMC Selection
    'hot_count': 1,
    'medium_count': 2,
    'cold_count': 1,
    'generic_count': 2,
    
    # Feature Selection - Focus on historical patterns, adding new feature
    'features': ['total_count', 'days_since_last', 'series_total', 'RECENT_LONG', 'BONUS_AWARE'],
    
    # Diversity Penalty
    'diversity_penalty': 0.15,  # 15% base penalty (rank-adjusted)
    
    # Algorithm-specific parameters
    'algorithm_params': {
        'penalty': 'l2',
        'solver': 'liblinear',
        'max_iter': 1000,
        'class_weight': 'balanced',
        'random_state': 42,
        'C': 1.0
    },
    
    # Calibration settings
    'calibration': {
        'method': 'sigmoid',
        'cv': 3
    }
}

MODEL_3_CONFIG = {
    'name': 'Contrarian Model',
    'description': 'XGBoost Model - Tree-based Pattern Discovery',
    'algorithm': 'xgboost',
    
    # HMC Selection
    'hot_count': 2,
    'medium_count': 2,
    'cold_count': 2,
    'generic_count': 0,
    
    # Feature Selection
    'features': 'ALL',  # Uses all available features, implicitly including 'days_since_bonus'
    
    # Diversity Penalty
    'diversity_penalty': 0.25,  # 25% base penalty (rank-adjusted)
    
    # Algorithm-specific parameters
    'algorithm_params': {
        'n_estimators': 150,
        'max_depth': 6,
        'learning_rate': 0.1,
        'use_label_encoder': False,
        'eval_metric': 'logloss',
        'random_state': 123,
        'n_jobs': -1
    },
    
    # Calibration settings
    'calibration': {
        'method': 'sigmoid',
        'cv': 3
    }
}

# ==================== ML MODEL REGISTRY ====================
ACTIVE_MODELS = [
    MODEL_1_CONFIG,
    MODEL_2_CONFIG,
    MODEL_3_CONFIG
]

# ==================== DISPLAY SETTINGS (Placeholder for ML) ====================
SHOW_DETAILED_PENALTIES = True  
SHOW_OVERLAP_ANALYSIS = True    
SHOW_DATA_SOURCE_SUMMARY = True