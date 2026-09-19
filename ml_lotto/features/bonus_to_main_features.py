"""
bonus_to_main_features.py
==========================
Extract features for bonus-to-main transition prediction.

Features track which numbers from recent bonus draws are likely to appear as main numbers.

UPDATED v3.10: Uses LIVE bonus window calculation instead of stale JSON data
"""

from typing import Dict, Any, List


def extract_bonus_to_main_features_dict(
    bonus_to_main_data: Dict[str, Any],
    features_dict: Dict[int, Dict[str, Any]],
    current_bonus_window: List[Dict[str, Any]] = None
) -> Dict[int, Dict[str, float]]:
    """
    Extract bonus-to-main transition features for all numbers.

    Args:
        bonus_to_main_data: Loaded JSON from lotto_bonus_to_main_patterns.json
        features_dict: Existing features dictionary (for category, freshness)
        current_bonus_window: LIVE bonus window from calculate_current_bonus_window()
                              If None, falls back to JSON data (NOT RECOMMENDED)

    Returns:
        Dictionary mapping number -> bonus-to-main features

    Features extracted:
        - is_in_bonus_window: Binary flag (1 if in last 10 bonus numbers)
        - draws_since_bonus: How many draws ago it was bonus (0-9, or -1 if not in window)
        - historical_transition_rate: This number's historical transition success rate
        - category_multiplier: Category weight (hot/medium/cold)
        - freshness_multiplier: Freshness weight (C0/C1/C2+)
        - timing_decay_weight: Time-based decay weight for current position
        - composite_transition_score: Combined probability score
        - avg_draws_to_transition: Average timing when this number transitions
        - recent_4: Recent appearance count (from main features)
        - recent_9: Recent appearance count (from main features)
        - total_count: Total appearance count (from main features)
    """
    bonus_to_main_features = {}

    # Get data structures
    per_number_profiles = bonus_to_main_data.get('per_number_transition_profile', {})
    category_weights = bonus_to_main_data.get('category_transition_weights', {})
    freshness_weights = bonus_to_main_data.get('freshness_transition_weights', {})
    timing_weights = bonus_to_main_data.get('timing_decay_weights', {})
    base_rate = bonus_to_main_data.get('transition_prediction_factors', {}).get('base_rate', 0.74)

    # Use LIVE bonus window if provided, otherwise fall back to JSON
    if current_bonus_window is not None:
        print("  ✓ Using LIVE bonus window (dynamically calculated from recent draws)")
    else:
        print("  ⚠️  Using stale JSON bonus window (consider passing live window)")
        current_bonus_window = bonus_to_main_data.get('current_bonus_window', {}).get('last_10_bonus_numbers', [])

    # Build lookup for current bonus window
    bonus_window_lookup = {}
    for entry in current_bonus_window:
        num = entry['number']
        bonus_window_lookup[num] = {
            'draws_ago': entry['draws_ago'],
            'category': entry.get('category', 'medium'),
            'freshness': entry.get('freshness', 0)
        }

    # Extract features for all numbers
    for num in range(1, 48):
        # Get number's transition profile
        profile = per_number_profiles.get(str(num), {})

        # Check if in recent bonus window
        is_in_window = num in bonus_window_lookup

        # Get draws_since_bonus
        draws_since_bonus = bonus_window_lookup[num]['draws_ago'] if is_in_window else -1

        # Get historical transition rate
        historical_rate = profile.get('transition_rate', 0.0)

        # Get category and freshness from main features
        if num in features_dict:
            category = features_dict[num].get('category', 'medium')
            freshness_bin = features_dict[num].get('current_freshness_bin', 0)
            recent_4 = features_dict[num].get('recent_4', 0)
            recent_9 = features_dict[num].get('recent_9', 0)
            total_count = features_dict[num].get('total_count', 0)
        else:
            category = 'medium'
            freshness_bin = 0
            recent_4 = 0
            recent_9 = 0
            total_count = 0

        # Convert freshness_bin to key
        freshness_key = f'C{freshness_bin}' if freshness_bin < 2 else 'C2+'

        # Get multipliers
        category_multiplier = category_weights.get(category, {}).get('weight', 1.0)
        freshness_multiplier = freshness_weights.get(freshness_key, {}).get('weight', 1.0)

        # Get timing weight
        timing_decay_weight = 0.0
        if is_in_window:
            draw_offset = draws_since_bonus + 1  # draws_ago=0 → draw_1
            timing_decay_weight = timing_weights.get(f'draw_{draw_offset}', 0.0)

        # Calculate composite score
        if is_in_window:
            composite_score = (
                base_rate *
                category_multiplier *
                freshness_multiplier *
                (1 + timing_decay_weight)
            )
        else:
            composite_score = 0.0

        # Get average draws to transition
        avg_draws_to_transition = profile.get('avg_draws_to_transition', 0.0)

        # Build feature dictionary
        bonus_to_main_features[num] = {
            'is_in_bonus_window': 1.0 if is_in_window else 0.0,
            'draws_since_bonus': float(draws_since_bonus),
            'historical_transition_rate': historical_rate,
            'category_multiplier': category_multiplier,
            'freshness_multiplier': freshness_multiplier,
            'timing_decay_weight': timing_decay_weight,
            'composite_transition_score': composite_score,
            'avg_draws_to_transition': avg_draws_to_transition,
            'recent_4': float(recent_4),
            'recent_9': float(recent_9),
            'total_count': float(total_count)
        }

    return bonus_to_main_features


def create_unified_bonus_to_main_features(
    bonus_to_main_data: Dict[str, Any],
    main_features_dict: Dict[int, Dict[str, Any]],
    current_bonus_window: List[Dict[str, Any]] = None,
    include_interactions: bool = True
) -> Dict[int, Dict[str, Any]]:
    """
    Create unified bonus-to-main feature dictionary combining:
    - 12 bonus-to-main specific features (transition patterns, timing, etc.)
    - 8 main features (days_since_last, rolling stats, gap patterns, volatility)
    - ~13 interaction features (if enabled)

    This provides a comprehensive feature set for bonus→main transition prediction,
    especially important for logistic regression which cannot discover interactions
    automatically.

    Args:
        bonus_to_main_data: Data from lotto_bonus_to_main_patterns.json
        main_features_dict: Main feature dictionary from extract_features_from_hmc_json
        current_bonus_window: LIVE bonus window (recommended over JSON data)
        include_interactions: Whether to include pairwise/triple interactions (default: True)

    Returns:
        Dictionary mapping number -> unified bonus-to-main feature dictionary

    Features included:
        - 12 bonus-to-main specific features
        - 8 main features (temporal patterns, gaps, volatility)
        - ~13 interaction features (if enabled)
        Total: 12 + 8 + 13 = ~33 features
    """
    print("\n" + "="*70)
    print("CREATING UNIFIED BONUS-TO-MAIN FEATURES")
    print("="*70)
    print("Combining: Bonus-to-main + Main features + Interactions")

    # Step 1: Extract base bonus-to-main features
    bonus_to_main_base = extract_bonus_to_main_features_dict(
        bonus_to_main_data,
        main_features_dict,
        current_bonus_window
    )

    # Step 2: Merge with additional main features
    unified_features = {}

    for num in range(1, 48):
        # Start with bonus-to-main specific features
        features = bonus_to_main_base.get(num, {}).copy()
        main_feat = main_features_dict.get(num, {})

        # Add critical temporal features
        features.update({
            # CRITICAL: Saturation indicator (was missing!)
            'days_since_last': float(main_feat.get('days_since_last', 0)),

            # Rolling statistics (momentum)
            'rolling_rate_10': float(main_feat.get('rolling_rate_10', 0)),
            'rolling_rate_20': float(main_feat.get('rolling_rate_20', 0)),
            'rolling_trend_10': float(main_feat.get('rolling_trend_10', 0)),

            # Gap patterns (predictability)
            'gap_consistency_score': float(main_feat.get('gap_consistency_score', 0)),
            'gap_variance': float(main_feat.get('gap_variance', 0)),
            'max_gap_ratio': float(main_feat.get('max_gap_ratio', 0)),

            # Volatility
            'appearance_volatility': float(main_feat.get('appearance_volatility', 0)),

            # Category/freshness for interactions
            'category': main_feat.get('category', 'medium'),
            'freshness_bin': int(main_feat.get('freshness_bin', 0)),
        })

        # Step 3: Add interaction features if requested
        if include_interactions:
            try:
                from ml_lotto.features.interactions import calculate_all_interaction_features
                interaction_feat = calculate_all_interaction_features(
                    features,  # Use merged features as input
                    include_triples=True
                )
                features.update(interaction_feat)
            except Exception as e:
                print(f"  ⚠️  Warning: Could not add interaction features: {e}")
                print(f"     Continuing with base features only")

        unified_features[num] = features

    # Report results
    sample_features = unified_features[1]
    base_count = 12  # bonus-to-main specific features
    main_count = 10  # additional main features (days_since_last + rolling + gaps + volatility + category/freshness)
    interaction_count = sum(1 for k in sample_features.keys() if 'interaction' in k or 'triple_' in k)

    print(f"\n✓ Created unified bonus-to-main features for 47 numbers")
    print(f"  Bonus-to-main specific features: {base_count}")
    print(f"  Main features: {main_count}")
    print(f"  Interaction features: {interaction_count}")
    print(f"  Total features per number: {len(sample_features)}")

    return unified_features


def get_unified_bonus_to_main_feature_names(include_interactions: bool = True) -> List[str]:
    """
    Get complete list of unified bonus-to-main feature names.

    Args:
        include_interactions: Whether to include interaction features (default: True)

    Returns:
        List of all feature names in unified bonus-to-main features
    """
    # Base bonus-to-main features (11)
    base_features = [
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
    ]

    # Main features (10)
    main_features = [
        'days_since_last',           # CRITICAL: Was missing!
        'rolling_rate_10',
        'rolling_rate_20',
        'rolling_trend_10',
        'gap_consistency_score',
        'gap_variance',
        'max_gap_ratio',
        'appearance_volatility',
        'category',
        'freshness_bin'
    ]

    all_features = base_features + main_features

    # Interaction features (~13 if enabled)
    if include_interactions:
        try:
            from ml_lotto.features.interactions import get_interaction_feature_names
            interaction_features = get_interaction_feature_names(include_triples=True)
            all_features.extend(interaction_features)
        except Exception as e:
            print(f"  ⚠️  Warning: Could not get interaction feature names: {e}")

    return all_features
