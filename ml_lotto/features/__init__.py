"""
features package
================
Handles all feature extraction and calculation logic.

This package is organized into specialized modules:
- extractor: Main orchestrator for feature extraction
- base: Basic features (total_count, days_since_last, category)
- timing: Time-based features (days_since_bonus, recency_zone_score)
- patterns: Pattern-based features (consecutive partners, pair affinity)
- bonus: Bonus-related features (was_recent_bonus, bonus_alignment)
- freshness: Freshness category features and pattern weighting
- realism: Priority 3 realism features (odd/even, sum, range) using JSON data
- history: Historical data features (win_bias_ratio)
"""

from ml_lotto.features.extractor import (
    extract_features_from_hmc_json,
    get_all_feature_names,
    expand_feature_selection
)

from ml_lotto.features.base import (
    get_dynamic_recent_keys
)

from ml_lotto.features.timing import (
    calculate_days_since_bonus,
    calculate_recency_zone_score
)

from ml_lotto.features.patterns import (
    calculate_has_consecutive_partner,
    calculate_consecutive_pair_affinity
)

from ml_lotto.features.bonus import (
    calculate_was_recent_bonus,
    calculate_bonus_hit_target_alignment
)

from ml_lotto.features.freshness import (
    calculate_freshness_category_features,
    calculate_recency_weighted_pattern_score
)

from ml_lotto.features.realism import (
    calculate_odd_even_affinity,
    calculate_sum_contribution_score,
    calculate_range_spread_affinity
)

from ml_lotto.features.history import (
    extract_win_bias_ratio_from_history
)

__all__ = [
    # Main extractor functions
    'extract_features_from_hmc_json',
    'get_all_feature_names',
    'expand_feature_selection',
    
    # Base functions
    'get_dynamic_recent_keys',
    
    # Timing features
    'calculate_days_since_bonus',
    'calculate_recency_zone_score',
    
    # Pattern features
    'calculate_has_consecutive_partner',
    'calculate_consecutive_pair_affinity',
    
    # Bonus features
    'calculate_was_recent_bonus',
    'calculate_bonus_hit_target_alignment',
    
    # Freshness features
    'calculate_freshness_category_features',
    'calculate_recency_weighted_pattern_score',
    
    # Realism features (Priority 3, JSON-based)
    'calculate_odd_even_affinity',
    'calculate_sum_contribution_score',
    'calculate_range_spread_affinity',
    
    # History features
    'extract_win_bias_ratio_from_history'
]