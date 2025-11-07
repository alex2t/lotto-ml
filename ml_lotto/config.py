# ml_lotto/config.py
"""
Configuration settings for lottery analysis

VERSION: 3.4 (New JSON Features Edition)
- Added new JSON features to model configs
"""

TOTAL_DRAWS = 600
TRAINING_DATA = 100
NUM_DRAWS = TOTAL_DRAWS - TRAINING_DATA
TRAINING_START_DRAW = TRAINING_DATA

DRAW_HISTORY_JSON = 'data/lotto_draw_history.json'
HMC_JSON_INPUT = 'data/lotto_trigger_periods.json'
ODDS_JSON_INPUT = 'data/lotto_odds_results.json'
FRESHNESS_JSON_INPUT = 'data/lotto_7_number_freshness_results.json'
DISTRIBUTION_STATS_JSON = 'data/lotto_distribution_stats.json'

MAX_NUMBER = 47
HOT_COUNT = 15
COLD_COUNT = 15

SCENARIOS = [
    {"window": 5,  "targets": [3]},
    {"window": 7,  "targets": [4]},
    {"window": 10, "targets": [4]},
    {"window": 15, "targets": [5]}
]

ACTUAL_HISTORY_WINDOWS = [s["window"] for s in SCENARIOS]

RANGE_BINS = {
    "20-25": (20, 25),
    "25-30": (25, 30),
    "30-35": (30, 35),
    "35-40": (35, 40),
    "40-45": (40, 45)
}

FRESHNESS_PATTERN_WEIGHTS = 'FRESHNESS_PATTERN_WEIGHTS' 

MODEL_1_CONFIG = {
    'name': 'Short-Term Momentum + Patterns + JSON Bonus',
    'description': 'Immediate patterns with timing, consecutive boosts, and NEW JSON bonus features',
    'algorithm': 'logistic_regression',
    
    'hot_count': 1,
    'medium_count': 2,
    'cold_count': 2,
    'generic_count': 1,
    
    'features': [
        FRESHNESS_PATTERN_WEIGHTS,
        'days_since_last',
        'recency_zone_score',
        'total_count',
        'was_recent_bonus',
        'has_consecutive_partner',
        'odd_even_affinity',
        'bonus_hit_contribution',
        'pair_frequency_score'
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
    'name': 'Long-Term Value + Sum/Range + JSON Features',
    'description': 'Historical patterns with timing, bonus optimization, and NEW JSON realism features',
    'algorithm': 'logistic_regression',
    
    'hot_count': 0,
    'medium_count': 3,
    'cold_count': 2,
    'generic_count': 1,
    
    'features': [
        'total_count',
        'days_since_last',
        'recency_zone_score',
        'days_since_bonus',
        'was_recent_bonus',
        'bonus_hit_target_alignment',
        'recent_14',
        'win_bias_ratio',
        'consecutive_pair_affinity',
        'sum_contribution_score',
        'range_spread_affinity',
        'freshness_weight_score',
        'range_spread_json',
        'sum_contribution_json'
    ],
    
    'diversity_penalty': 0.15,
    
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
    'name': 'Complex Pattern Discovery + All JSON Features',
    'description': 'XGBoost with full feature set including ALL NEW JSON features',
    'algorithm': 'xgboost',
    
    'hot_count': 2,
    'medium_count': 2,
    'cold_count': 1,
    'generic_count': 1,
    
    'features': [
        'recent_4',
        FRESHNESS_PATTERN_WEIGHTS,
        'total_count',
        'days_since_last',
        'recency_zone_score',
        'recent_14',
        'days_since_bonus',
        'was_recent_bonus',
        'bonus_hit_target_alignment',
        'has_consecutive_partner',
        'consecutive_pair_affinity',
        'series_recent',
        'win_bias_ratio',
        'odd_even_affinity',
        'sum_contribution_score',
        'range_spread_affinity',
        'bonus_hit_contribution',
        'freshness_weight_score',
        'pair_frequency_score',
        'range_spread_json',
        'odd_even_json',
        'sum_contribution_json'
    ],
    
    'diversity_penalty': 0.25,
    
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

ACTIVE_MODELS = [
    MODEL_1_CONFIG,
    MODEL_2_CONFIG,
    MODEL_3_CONFIG,
]

SHOW_DETAILED_PENALTIES = True
SHOW_OVERLAP_ANALYSIS = True
SHOW_DATA_SOURCE_SUMMARY = False