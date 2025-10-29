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

# ==================== FEATURE ANALYSIS ====================
"""
FEATURE GROUPS:

1. FRESHNESS FEATURES (Recent Pattern - Last 4 Draws):
   - current_freshness_bin: Categorical 0-3 (C0/C1/C2/C>=3)
   - freshness_c0_weight: Pattern weight for C0 numbers (0.0-0.6)
   - freshness_c1_weight: Pattern weight for C1 numbers (0.0-0.6)
   - freshness_c2_weight: Pattern weight for C2 numbers (0.0-0.6)
   - freshness_c3_weight: Pattern weight for C>=3 numbers (0.0-0.6)
   → HIGH CORRELATION: All derive from recent_4
   → BEST USE: Pick 1-2 of these, not all 5

2. RECENT ACTIVITY FEATURES:
   - recent_4: Count in last 4 draws (0-4)
   - recent_6: Count in last 6 draws (0-6)
   - recent_9: Count in last 9 draws (0-9)
   - recent_14: Count in last 14 draws (0-14)
   → MODERATE CORRELATION: Progressive windows
   → BEST USE: Use recent_4 OR recent_14, not all

3. HISTORICAL FEATURES:
   - total_count: All-time frequency (60-95)
   - days_since_last: Days since last hit (0-999)
   → LOW CORRELATION with freshness
   → BEST USE: Good for long-term patterns

4. SPECIAL FEATURES:
   - days_since_bonus: Days since bonus hit (0-999)
   - series_total: Total streak occurrences (0-20)
   - series_recent: Recent streaks (0-10)
   → LOW CORRELATION with others
   → BEST USE: Niche patterns, may add noise

RECOMMENDATION: Use 3-5 features per model, avoiding redundancy
"""

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
    
    # Feature Selection - MINIMAL, SHORT-TERM FOCUSED
    # Only use recent_4 + one freshness weight (avoid redundancy)
    'features': ['recent_4', 'freshness_c0_weight', 'days_since_last'],
    
    # Low diversity penalty (first model sets baseline)
    'diversity_penalty': 0.0,
    
    # Algorithm parameters - Simple model
    'algorithm_params': {
        'penalty': 'l2',
        'solver': 'liblinear',
        'max_iter': 1000,
        'class_weight': 'balanced',
        'random_state': 42,
        'C': 1.0  # Moderate regularization
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
    # Completely different signal from Model 1
    'features': ['total_count', 'days_since_last', 'days_since_bonus', 'recent_14'],
    
    # Medium diversity penalty
    'diversity_penalty': 0.15,
    
    # Algorithm parameters
    'algorithm_params': {
        'penalty': 'l2',
        'solver': 'liblinear',
        'max_iter': 1000,
        'class_weight': 'balanced',
        'random_state': 42,
        'C': 0.5  # Stronger regularization for stable patterns
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
    # XGBoost can handle correlations better via tree splits
    'features': [
        'total_count',
        'days_since_last', 
        'recent_4',
        'recent_14',
        'freshness_c0_weight',
        'freshness_c1_weight',
        'days_since_bonus',
        'series_recent'
    ],
    
    # High diversity penalty (maximize difference from other models)
    'diversity_penalty': 0.25,
    
    # Algorithm parameters - More complex model
    'algorithm_params': {
        'n_estimators': 150,
        'max_depth': 4,  # Shallow trees to prevent overfitting
        'learning_rate': 0.1,
        'use_label_encoder': False,
        'eval_metric': 'logloss',
        'random_state': 123,
        'n_jobs': -1,
        'subsample': 0.8,
        'colsample_bytree': 0.7,  # Feature sampling to reduce correlation impact
        'min_child_weight': 3  # Regularization
    },
    
    'calibration': {
        'method': 'sigmoid',
        'cv': 3
    }
}

# ==================== ALTERNATIVE: SPECIALIZED MODELS ====================
# Uncomment these if you want more specialized approaches

MODEL_4_CONFIG_ALTERNATIVE = {
    'name': 'Anti-Pattern Model',
    'description': 'Contrarian - picks numbers AVOIDING top patterns',
    'algorithm': 'logistic_regression',
    
    'hot_count': 1,
    'medium_count': 1,
    'cold_count': 3,
    'generic_count': 1,
    
    # Feature Selection - INVERSE FRESHNESS
    # Higher weights on C2/C3 (warm/hot recent) instead of C0/C1
    'features': ['recent_6', 'freshness_c2_weight', 'freshness_c3_weight', 'total_count'],
    
    'diversity_penalty': 0.30,  # Very high to force difference
    
    'algorithm_params': {
        'penalty': 'l2',
        'solver': 'liblinear',
        'max_iter': 1000,
        'class_weight': 'balanced',
        'random_state': 99,
        'C': 0.3
    },
    
    'calibration': {
        'method': 'sigmoid',
        'cv': 3
    }
}

MODEL_5_CONFIG_ALTERNATIVE = {
    'name': 'Streak Hunter',
    'description': 'Focus on numbers in active series/streaks',
    'algorithm': 'logistic_regression',
    
    'hot_count': 2,
    'medium_count': 1,
    'cold_count': 1,
    'generic_count': 2,
    
    # Feature Selection - SERIES FOCUSED
    'features': ['series_recent', 'series_total', 'recent_9', 'days_since_last'],
    
    'diversity_penalty': 0.20,
    
    'algorithm_params': {
        'penalty': 'l1',  # L1 for feature selection
        'solver': 'liblinear',
        'max_iter': 1000,
        'class_weight': 'balanced',
        'random_state': 77,
        'C': 0.8
    },
    
    'calibration': {
        'method': 'sigmoid',
        'cv': 3
    }
}

# ==================== ML MODEL REGISTRY ====================
# Choose which models to activate

ACTIVE_MODELS = [
    MODEL_1_CONFIG,  # Short-term momentum
    MODEL_2_CONFIG,  # Long-term value
    MODEL_3_CONFIG,  # Complex patterns
]

# For maximum diversity, use all 5:
# ACTIVE_MODELS = [
#     MODEL_1_CONFIG,
#     MODEL_2_CONFIG,
#     MODEL_3_CONFIG,
#     MODEL_4_CONFIG_ALTERNATIVE,
#     MODEL_5_CONFIG_ALTERNATIVE
# ]

# ==================== DISPLAY SETTINGS ====================
SHOW_DETAILED_PENALTIES = True  
SHOW_OVERLAP_ANALYSIS = True    
SHOW_DATA_SOURCE_SUMMARY = False  # Reduced verbosity