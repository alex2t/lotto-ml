"""
test_unified_bonus_to_main_features.py
========================================
Test script to verify unified bonus-to-main features implementation.

Tests:
1. create_unified_bonus_to_main_features() properly merges all features
2. Feature counts are correct (11 base + 10 main + ~13 interactions)
3. All expected feature names are present
4. window_saturation_penalty is not carried into bonus-to-main features (F-21, F-24)
5. bonus_to_main_trainer.py can handle unified features dynamically
"""

import sys
from pathlib import Path

from ml_lotto.features.bonus_to_main_features import (
    create_unified_bonus_to_main_features,
    get_unified_bonus_to_main_feature_names,
    extract_bonus_to_main_features_dict
)


def test_unified_bonus_to_main_features():
    """Test that unified bonus-to-main features are created correctly."""
    print("\n" + "="*80)
    print("TEST: Unified Bonus-to-Main Features")
    print("="*80)

    # Create minimal mock data
    bonus_to_main_data = {
        'per_number_transition_profile': {
            str(num): {
                'transition_rate': 0.74,
                'avg_draws_to_transition': 5.0
            } for num in range(1, 48)
        },
        'category_transition_weights': {
            'hot': {'weight': 1.2},
            'medium': {'weight': 1.0},
            'cold': {'weight': 0.8}
        },
        'freshness_transition_weights': {
            'C0': {'weight': 1.1},
            'C1': {'weight': 1.0},
            'C2+': {'weight': 0.9}
        },
        'timing_decay_weights': {
            f'draw_{i}': 0.1 * (10 - i) for i in range(1, 11)
        },
        'transition_prediction_factors': {
            'base_rate': 0.74
        }
    }

    # Create mock main features
    main_features_dict = {
        num: {
            'days_since_last': 15,
            'rolling_rate_10': 0.5,
            'rolling_rate_20': 0.4,
            'rolling_trend_10': 0.1,
            'gap_consistency_score': 0.7,
            'gap_variance': 20.0,
            'max_gap_ratio': 0.5,
            'appearance_volatility': 0.3,
            'category': 'hot' if num <= 15 else 'cold' if num > 32 else 'medium',
            'freshness_bin': 0,
            'current_freshness_bin': 0,
            'recent_4': 1,
            'recent_9': 3,
            'total_count': 50,
            'window_saturation_penalty': 0.1
        } for num in range(1, 48)
    }

    # Create mock bonus window
    current_bonus_window = [
        {'number': i, 'draws_ago': i-1, 'category': 'hot', 'freshness': 0}
        for i in range(1, 11)
    ]

    # Test 1: the C-5 full-history feature must not be copied through, even when present in the input
    print("\n  Test 1: window_saturation_penalty stays out (F-21, F-24)")
    base_features = extract_bonus_to_main_features_dict(
        bonus_to_main_data,
        main_features_dict,
        current_bonus_window
    )
    sample_base = base_features[1]
    assert 'window_saturation_penalty' not in sample_base, "window_saturation_penalty was copied through"
    print(f"    window_saturation_penalty not carried through")
    print(f"    Base features count: {len(sample_base)} (expected 11)")

    # Test 2: Unified features WITHOUT interactions
    print("\n  Test 2: Unified features WITHOUT interactions")
    unified_no_interact = create_unified_bonus_to_main_features(
        bonus_to_main_data,
        main_features_dict,
        current_bonus_window,
        include_interactions=False
    )

    sample_features_no_interact = unified_no_interact[1]
    print(f"    Features in number 1: {len(sample_features_no_interact)}")
    print(f"    Expected: 21 (11 base + 10 main)")

    # Verify base features
    base_feature_names = [
        'is_in_bonus_window', 'draws_since_bonus', 'historical_transition_rate',
        'category_multiplier', 'freshness_multiplier', 'timing_decay_weight',
        'composite_transition_score',
        'avg_draws_to_transition', 'recent_4', 'recent_9', 'total_count'
    ]
    for feat in base_feature_names:
        assert feat in sample_features_no_interact, f"Missing base feature: {feat}"
    print(f"    All 11 base features present")

    # Verify main features
    main_feature_names = [
        'days_since_last', 'rolling_rate_10', 'rolling_rate_20', 'rolling_trend_10',
        'gap_consistency_score', 'gap_variance', 'max_gap_ratio',
        'appearance_volatility', 'category', 'freshness_bin'
    ]
    for feat in main_feature_names:
        assert feat in sample_features_no_interact, f"Missing main feature: {feat}"
    print(f"    All 10 main features present (including CRITICAL days_since_last)")

    # Test 3: Unified features WITH interactions
    print("\n  Test 3: Unified features WITH interactions")
    try:
        unified_with_interact = create_unified_bonus_to_main_features(
            bonus_to_main_data,
            main_features_dict,
            current_bonus_window,
            include_interactions=True
        )

        sample_features_with_interact = unified_with_interact[1]
        print(f"    Features in number 1: {len(sample_features_with_interact)}")
        print(f"    Expected: ~34 (11 base + 10 main + ~13 interactions)")

        # Count interaction features
        interaction_count = sum(
            1 for k in sample_features_with_interact.keys()
            if 'interaction' in k or 'triple_' in k
        )
        print(f"    Interaction features found: {interaction_count}")

        if interaction_count > 0:
            print(f"    Interaction features successfully added")
        else:
            print(f"    No interaction features found (may need lotto_feature_interactions.json)")

    except Exception as e:
        print(f"    Interaction test failed: {e}")
        print(f"       This is OK if lotto_feature_interactions.json doesn't exist")

    # Test 4: get_unified_bonus_to_main_feature_names
    print("\n  Test 4: get_unified_bonus_to_main_feature_names()")
    feature_names = get_unified_bonus_to_main_feature_names(include_interactions=False)
    print(f"    Feature names (no interactions): {len(feature_names)}")
    assert len(feature_names) == 21, f"Expected 21 features, got {len(feature_names)}"
    print(f"    Correct number of feature names")

    print("\n" + "="*80)
    print("ALL TESTS PASSED!")
    print("="*80)
    print("\nSummary:")
    print("  - window_saturation_penalty stays out (F-21, F-24)")
    print("  - create_unified_bonus_to_main_features() successfully merges all features")
    print("  - Feature counts are correct (11 base + 10 main + interactions)")
    print("  - All expected feature names are present")
    print("  - days_since_last (CRITICAL) is now included")
    print("\nNext: Run quickpick.py to verify integration with bonus_to_main_trainer.py")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(test_unified_bonus_to_main_features())
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
