"""
Configuration settings for lottery analysis

OPTIMIZED: Reduced feature redundancy and clearer model specialization
Each model focuses on different aspects to maximize diversity
"""

# =============== ANALYSIS CONFIGURATION ===============
TOTAL_DRAWS = 600
TRAINING_DATA = 100
NUM_DRAWS = TOTAL_DRAWS - TRAINING_DATA
TRAINING_START_DRAW = TRAINING_DATA

# =============== FILE PATHS ===============
DRAW_HISTORY_JSON = 'data/lotto_draw_history.json'
HMC_JSON_INPUT = 'data/lotto_trigger_periods.json'
ODDS_JSON_INPUT = 'data/lotto_odds_results.json'
FRESHNESS_JSON_INPUT = 'data/lotto_7_number_freshness_results.json'

# =============== LOTTERY PARAMETERS ===============
MAX_NUMBER = 47
HOT_COUNT = 15
COLD_COUNT = 15

# =============== ANALYSIS SCENARIOS ===============
SCENARIOS = [
    {"window": 5,  "targets": [3]},
    {"window": 7,  "targets": [4]},
    {"window": 10, "targets": [4]},
    {"window": 15, "targets": [5]}
]

ACTUAL_HISTORY_WINDOWS = [s["window"] for s in SCENARIOS]

# =============== RANGE BINS ===============
RANGE_BINS = {
    "20-25": (20, 25),
    "25-30": (25, 30),
    "30-35": (30, 35),
    "35-40": (35, 40),
    "40-45": (40, 45)
}

# ==================== FEATURE GROUPS & KEYWORDS ====================

# DYNAMIC KEYWORD: Replaced hardcoded list of freshness weights
# This will be dynamically expanded by feature_extractor.py based on C_max_threshold
FRESHNESS_PATTERN_WEIGHTS = 'FRESHNESS_PATTERN_WEIGHTS' 

# ==================== ML MODEL CONFIGURATIONS ====================

MODEL_1_CONFIG = {
    'name': 'Short-Term Momentum Model',
    'description': 'Focus on immediate patterns (last 4 draws only)',
    'algorithm': 'logistic_regression',
    
    # HMC Selection - Balanced
    'hot_count': 1,
    'medium_count': 2,
    'cold_count': 2,
    'generic_count': 1,
    
    # Feature Selection - DYNAMICALLY RESOLVED
     'features': [
        FRESHNESS_PATTERN_WEIGHTS, # Dynamic weights (C0, C1, C_GE_2, etc.)
        'recent_14',         # Independent timing signal
        'total_count'              # Independent historical signal
    ],
    
    'diversity_penalty': 0.0,
    
    'algorithm_params': {
        'penalty': 'l2',
        'solver': 'liblinear',
        'max_iter': 1000,
        'class_weight': 'balanced',
        'random_state': 42,
        'C': 1.0
    },
    
    'calibration': {
        'method': 'sigmoid',
        'cv': 5
    }
}

MODEL_2_CONFIG = {
    'name': 'Long-Term Value Model',
    'description': 'Historical patterns + avoiding recent bonus hits',
    'algorithm': 'logistic_regression',
    
    # HMC Selection - Conservative (more cold/medium)
    'hot_count': 0,
    'medium_count': 3,
    'cold_count': 2,
    'generic_count': 1,
    
    # Feature Selection - HISTORICAL FOCUSED (no freshness features)
    'features': [
        'total_count', 
        'days_since_last', 
        'days_since_bonus', 
        'recent_14',
        'win_bias_ratio' # ADDED NEW FEATURE
    ],
    
    'diversity_penalty': 0.0,
    
    'algorithm_params': {
        'penalty': 'l2',
        'solver': 'liblinear',
        'max_iter': 1000,
        'class_weight': 'balanced',
        'random_state': 42,
        'C': 0.5
    },
    
    'calibration': {
        'method': 'sigmoid',
        'cv': 3
    }
}

MODEL_3_CONFIG = {
    'name': 'Complex Pattern Discovery',
    'description': 'XGBoost with full feature set for non-linear patterns',
    'algorithm': 'xgboost',
    
    # HMC Selection - Aggressive (more hot)
    'hot_count': 2,
    'medium_count': 2,
    'cold_count': 1,
    'generic_count': 1,
    
    # Feature Selection - COMPREHENSIVE
   'features': [
        'recent_4',              # Short-term raw count
        FRESHNESS_PATTERN_WEIGHTS, # Dynamic weights
        'total_count',           # Historical frequency
        'days_since_last',       # Timing
        'recent_14',             # Long-term trend
        'days_since_bonus',      # Bonus patterns
        'series_recent',          # Streak activity
        'win_bias_ratio' # ADDED NEW FEATURE
    ],
    
    'diversity_penalty': 0.0,
    
    'algorithm_params': {
        'n_estimators': 150,
        'max_depth': 4,
        'learning_rate': 0.1,
        'use_label_encoder': False,
        'eval_metric': 'logloss',
        'random_state': 123,
        'n_jobs': -1,
        'subsample': 0.8,
        'colsample_bytree': 0.7,
        'min_child_weight': 3
    },
    
    'calibration': {
        'method': 'sigmoid',
        'cv': 3
    }
}

# ==================== ML MODEL REGISTRY ====================

ACTIVE_MODELS = [
    MODEL_1_CONFIG,
    MODEL_2_CONFIG,
    MODEL_3_CONFIG,
]

# ==================== DISPLAY SETTINGS ====================
SHOW_DETAILED_PENALTIES = True
SHOW_OVERLAP_ANALYSIS = True
SHOW_DATA_SOURCE_SUMMARY = False