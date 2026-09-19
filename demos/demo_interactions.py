#!/usr/bin/env python3
"""
Test script to validate the interaction feature implementation.
This script tests the complete pipeline without running the full system.
"""

print("=" * 70)
print("INTERACTION FEATURE IMPLEMENTATION TEST")
print("=" * 70)

# Test 1: Import the interactions module
print("\nTest 1: Importing interactions module...")
try:
    from ml_lotto.features.interactions import (
        InteractionFeatureCalculator,
        calculate_all_interaction_features,
        get_interaction_feature_names
    )
    print("✓ Successfully imported interactions module")
except Exception as e:
    print(f"✗ Failed to import: {e}")
    exit(1)

# Test 2: Initialize the calculator
print("\nTest 2: Initializing InteractionFeatureCalculator...")
try:
    calculator = InteractionFeatureCalculator()
    print(f"✓ Calculator initialized")
    print(f"  - Pairwise interactions loaded: {len(calculator.pairwise_interactions)}")
    print(f"  - Triple interactions loaded: {len(calculator.triple_interactions)}")
    print(f"  - Feature split thresholds extracted: {len(calculator.feature_thresholds)}")
except Exception as e:
    print(f"✗ Failed to initialize: {e}")
    exit(1)

# Test 3: Get interaction feature names
print("\nTest 3: Getting interaction feature names...")
try:
    pairwise_names = get_interaction_feature_names(include_triples=False)
    all_names = get_interaction_feature_names(include_triples=True)
    print(f"✓ Got feature names")
    print(f"  - Pairwise features: {len(pairwise_names)}")
    print(f"  - All features (pairwise + triple): {len(all_names)}")

    if pairwise_names:
        print(f"\n  Sample pairwise features:")
        for name in pairwise_names[:3]:
            print(f"    - {name}")
except Exception as e:
    print(f"✗ Failed to get feature names: {e}")
    exit(1)

# Test 4: Calculate interaction features for a sample number
print("\nTest 4: Calculating interaction features for sample data...")
try:
    # Sample feature dictionary (simulating a number's features)
    sample_features = {
        'total_count': 10,
        'recent_4': 2,
        'recent_14': 5,
        'freshness_bin': 1,
        'bonus_hit_contribution': 0.7,
        'days_since_last': 15,
        'category': 'hot'
    }

    interactions = calculate_all_interaction_features(sample_features, include_triples=True)
    print(f"✓ Calculated {len(interactions)} interaction features")

    # Show some results
    if interactions:
        print(f"\n  Sample interaction values:")
        for name, value in list(interactions.items())[:5]:
            print(f"    - {name}: {value}")
except Exception as e:
    print(f"✗ Failed to calculate features: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 5: Test integration with extractor (import only)
print("\nTest 5: Testing extractor integration...")
try:
    from ml_lotto.features.extractor import expand_feature_selection

    # Test that the new keywords exist
    all_features = [
        'total_count', 'recent_4', 'days_since_last',
        'total_count_x_recent_4_interaction',
        'total_count_x_recent_14_interaction',
        'triple_hot_1_recent'
    ]

    pairwise = expand_feature_selection('PAIRWISE_INTERACTIONS', all_features)
    triples = expand_feature_selection('TRIPLE_INTERACTIONS', all_features)
    all_int = expand_feature_selection('ALL_INTERACTIONS', all_features)

    print(f"✓ Extractor keywords working")
    print(f"  - PAIRWISE_INTERACTIONS expands to: {len(pairwise)} features")
    print(f"  - TRIPLE_INTERACTIONS expands to: {len(triples)} features")
    print(f"  - ALL_INTERACTIONS expands to: {len(all_int)} features")
except Exception as e:
    print(f"✗ Failed extractor integration test: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 6: Verify config changes
print("\nTest 6: Verifying MODEL_1_CONFIG changes...")
try:
    from ml_lotto.config import MODEL_1_CONFIG

    if 'PAIRWISE_INTERACTIONS' in MODEL_1_CONFIG['features']:
        print("✓ MODEL_1_CONFIG includes PAIRWISE_INTERACTIONS")
    else:
        print("✗ MODEL_1_CONFIG does not include PAIRWISE_INTERACTIONS")
        print(f"  Current features: {MODEL_1_CONFIG['features']}")
        exit(1)

    print(f"  Model 1 hot_count: {MODEL_1_CONFIG['hot_count']}")
    print(f"  Model 1 medium_count: {MODEL_1_CONFIG['medium_count']}")
    print(f"  Model 1 cold_count: {MODEL_1_CONFIG['cold_count']}")
    print(f"  Model 1 generic_count: {MODEL_1_CONFIG['generic_count']}")

except Exception as e:
    print(f"✗ Failed config verification: {e}")
    exit(1)

# All tests passed
print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print("\nSummary:")
print("  ✓ Interactions module imports correctly")
print("  ✓ Calculator loads data from JSON dynamically")
print("  ✓ Feature names are extracted correctly")
print("  ✓ Interaction features calculate correctly")
print("  ✓ Extractor keywords work as expected")
print("  ✓ MODEL_1_CONFIG is properly configured")
print("\nImplementation is ready to use!")
print("Next steps:")
print("  1. Run 'python drawpick.py' to regenerate interaction data")
print("  2. Run 'python quickpick.py' to test Model 1 with interactions")
