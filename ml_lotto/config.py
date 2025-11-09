# ml_lotto/config.py
"""
Configuration settings for lottery analysis

VERSION: 3.5 (Bonus Ball Edition)
- Added BONUS_MODEL_CONFIG for bonus ball prediction
- Added BONUS_ANALYSIS_JSON file path
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
BONUS_ANALYSIS_JSON = 'data/lotto_bonus_analysis.json'
BONUS_TO_MAIN_JSON = 'data/lotto_bonus_to_main_patterns.json'
STATISTICS_ANALYSIS_JSON = 'data/lotto_statistics_analysis.json'

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
LONG_TERM_PATTERN_WEIGHTS = 'LONG_TERM_PATTERN_WEIGHTS'

BONUS_MODEL_CONFIG = {
    'name': 'Bonus Ball Predictor',
    'algorithm': 'logistic_regression',
    'features': [
        'category_weight',
        'was_bonus_last_10',
        'freshness_weight',
        'timing_zone_weight',
        'days_since_last_bonus',
        'bonus_frequency_ratio',
        'total_bonus_count',
        'avg_days_between_bonus'
    ],
    'algorithm_params': {
        'penalty': 'l2',
        'C': 1.0,
        'class_weight': 'balanced',
        'solver': 'liblinear',
        'max_iter': 1000,
        'random_state': 42
    },
    'calibration': {
        'method': 'sigmoid',
        'cv': 5
    }
}

BONUS_TO_MAIN_MODEL_CONFIG = {
    'name': 'Bonus-to-Main Transition Predictor',
    'description': '74% of bonus numbers appear as main within 10 draws',
    'algorithm': 'logistic_regression',
    'features': [
        'is_in_bonus_window',
        'draws_since_bonus',
        'historical_transition_rate',
        'category_multiplier',
        'freshness_multiplier',
        'timing_decay_weight',
        'composite_transition_score',
        'avg_draws_to_transition',
        'recent_4',
        'recent_9',
        'total_count'
    ],
    'algorithm_params': {
        'penalty': 'l2',
        'C': 0.8,
        'class_weight': {0: 1.0, 1: 3.5},  # Reflect 3.5x boost over random
        'solver': 'liblinear',
        'max_iter': 1000,
        'random_state': 42
    },
    'calibration': {
        'method': 'isotonic',  # Better for skewed distributions
        'cv': 5
    }
}

MODEL_1_CONFIG = {
    'name': 'Short-Term Momentum + Patterns + JSON Bonus',
    'description': 'Immediate patterns with timing, consecutive boosts, and NEW JSON bonus features',
    'algorithm': 'logistic_regression',

    'hot_count': 1,
    'medium_count': 2,
    'cold_count': 2,
    'generic_count': 0,

    'features': [
        FRESHNESS_PATTERN_WEIGHTS,
        'days_since_last',
        'recency_zone_score',
        'total_count',
        'was_recent_bonus',
        'has_consecutive_partner',
        'odd_even_json',  # Replaced odd_even_affinity with JSON version
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
    'name': 'Long-Term Value + Sum/Range + JSON Features + LT Patterns',
    'description': 'Historical patterns with timing, bonus optimization, JSON realism features, and LONG-TERM pattern analysis',
    'algorithm': 'logistic_regression',

    'hot_count': 0,
    'medium_count': 3,
    'cold_count': 2,
    'generic_count': 0,

    'features': [
        'total_count',
        'days_since_last',
        'recency_zone_score',
        'days_since_bonus',
        'was_recent_bonus',
        'bonus_hit_contribution',  # Replaced bonus_hit_target_alignment with JSON version
        'recent_14',
        'win_bias_ratio',
        'consecutive_pair_affinity',
        'sum_contribution_json',  # Replaced sum_contribution_score with JSON version
        'range_spread_json',  # Replaced range_spread_affinity with JSON version
        'freshness_weight_score',
        LONG_TERM_PATTERN_WEIGHTS  # NEW: Long-term HMC and recency pattern analysis
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
    'name': 'Complex Pattern Discovery + All JSON Features + LT Patterns',
    'description': 'XGBoost with full feature set including ALL NEW JSON features and LONG-TERM pattern analysis',
    'algorithm': 'xgboost',

    'hot_count': 2,
    'medium_count': 2,
    'cold_count': 1,
    'generic_count': 0,

    'features': [
        'recent_4',
        FRESHNESS_PATTERN_WEIGHTS,
        LONG_TERM_PATTERN_WEIGHTS,  # NEW: Long-term HMC and recency pattern analysis
        'total_count',
        'days_since_last',
        'recency_zone_score',
        'recent_14',
        'days_since_bonus',
        'was_recent_bonus',
        'bonus_hit_contribution',  # Replaced bonus_hit_target_alignment with JSON version
        'has_consecutive_partner',
        'consecutive_pair_affinity',
        'series_recent',
        'win_bias_ratio',
        'odd_even_json',  # Replaced odd_even_affinity with JSON version
        'sum_contribution_json',  # Replaced sum_contribution_score with JSON version
        'range_spread_json',  # Replaced range_spread_affinity with JSON version
        'freshness_weight_score',
        'pair_frequency_score'
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