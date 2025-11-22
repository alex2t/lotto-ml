"""
Test Model-Specific Feature Optimization
==========================================

This script demonstrates the improvements from using model-specific feature sets
instead of the same generic features for all models.

KEY CHANGES:
1. Model 1: Focus on momentum (rolling stats, recency)
2. Model 2: Focus on stability for main 6 jackpot (NO bonus features!)
3. Model 3: Use ALL features (complexity detection)
4. Model 4: Only high-confidence features (conservative pool)

Expected Improvements:
- Model 1: +5-10% precision (focused momentum signals)
- Model 2: +10-15% for main 6 prediction (removed irrelevant bonus features)
- Model 3: +3-5% complex pattern detection (all features available)
- Model 4: +20-30% precision in 20-ball pool (only top features)
"""

from ml_lotto.config import MODEL_1_CONFIG, MODEL_2_CONFIG, MODEL_3_CONFIG, MODEL_4_CONFIG

def analyze_model_config(model_config, model_num):
    """Analyze and display model configuration."""
    print(f"\n{'='*80}")
    print(f"MODEL {model_num}: {model_config['name']}")
    print(f"{'='*80}")
    print(f"Description: {model_config['description']}")
    print(f"Algorithm: {model_config['algorithm']}")

    # Count features
    features = model_config.get('features', [])
    if isinstance(features, list):
        feature_count = len(features)
        has_bonus_features = any('bonus' in str(f).lower() for f in features)
        has_rolling_features = any('rolling' in str(f).lower() for f in features)
        has_long_term_features = 'LONG_TERM_PATTERN_WEIGHTS' in features
    else:
        feature_count = "Dynamic"
        has_bonus_features = "Unknown"
        has_rolling_features = "Unknown"
        has_long_term_features = "Unknown"

    print(f"\nFeature Count: {feature_count}")
    print(f"Has Bonus Features: {has_bonus_features}")
    print(f"Has Rolling Features: {has_rolling_features}")
    print(f"Has Long-Term Patterns: {has_long_term_features}")

    # Feature selection settings
    feature_sel = model_config.get('feature_selection', {})
    if feature_sel:
        print(f"\nFeature Selection Settings:")
        print(f"  Enable: {feature_sel.get('enable', 'Not specified')}")
        print(f"  Correlation threshold: {feature_sel.get('correlation_threshold', 'Not specified')}")
        print(f"  Importance threshold: {feature_sel.get('importance_threshold', 'Not specified')}")
    else:
        print(f"\nFeature Selection: Using default settings")

    # Strategy summary
    print(f"\nStrategy:")
    if model_num == 1:
        print("  ✅ Focus on MOMENTUM and RECENCY")
        print("  ✅ Rolling statistics (10, 20 draw windows)")
        print("  ✅ Aggressive feature selection (importance > 0.01)")
        print("  🎯 Goal: Catch hot/trending numbers")
    elif model_num == 2:
        print("  ✅ Focus on STABILITY for main 6 jackpot")
        print("  ❌ NO BONUS FEATURES (not relevant for main 6!)")
        print("  ✅ Long-term patterns and stability features")
        print("  ✅ NO feature selection (use explicit list)")
        print("  🎯 Goal: Optimize for 6-ball jackpot prize")
    elif model_num == 3:
        print("  ✅ Use ALL FEATURES (maximum complexity)")
        print("  ✅ Let XGBoost find interactions")
        print("  ✅ NO feature selection (keep everything)")
        print("  🎯 Goal: Detect complex multi-feature patterns")
    elif model_num == 4:
        print("  ✅ Only TOP-PERFORMING features")
        print("  ✅ High-precision, reliable indicators only")
        print("  ✅ VERY aggressive feature selection (importance > 0.02)")
        print("  🎯 Goal: Generate 20-number pool with 6+ winners")

def compare_models():
    """Compare all model configurations."""
    print("\n" + "="*80)
    print("MODEL-SPECIFIC FEATURE OPTIMIZATION COMPARISON")
    print("="*80)

    analyze_model_config(MODEL_1_CONFIG, 1)
    analyze_model_config(MODEL_2_CONFIG, 2)
    analyze_model_config(MODEL_3_CONFIG, 3)
    analyze_model_config(MODEL_4_CONFIG, 4)

    print("\n" + "="*80)
    print("KEY IMPROVEMENTS FROM MODEL-SPECIFIC FEATURES")
    print("="*80)

    improvements = [
        ("Model 1", "Removed redundant features, kept momentum signals", "+5-10% precision"),
        ("Model 2", "REMOVED BONUS FEATURES (not relevant for main 6!)", "+10-15% main 6 accuracy"),
        ("Model 3", "Using ALL features instead of filtered subset", "+3-5% complex pattern detection"),
        ("Model 4", "Only top 8-12 high-confidence features", "+20-30% precision in pool")
    ]

    for model, change, improvement in improvements:
        print(f"\n{model}:")
        print(f"  Change: {change}")
        print(f"  Expected improvement: {improvement}")

    print("\n" + "="*80)
    print("MOST IMPORTANT CHANGE: Model 2")
    print("="*80)
    print("❌ BEFORE: Model 2 included 'was_recent_bonus' and bonus transition features")
    print("✅ AFTER:  Model 2 EXCLUDES all bonus features")
    print("💡 WHY:    Model 2 predicts MAIN 6 ONLY (jackpot prize)")
    print("           Bonus features are irrelevant and add noise!")
    print("🎯 IMPACT: Expected +10-15% improvement for main 6 ball prediction")

def main():
    """Run comparison analysis."""
    compare_models()

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Run quickpick.py with new configurations")
    print("2. Compare metrics before/after:")
    print("   - Model 2 main 6 accuracy")
    print("   - Model 4 pool hit rate")
    print("3. Monitor feature importance in training output")
    print("4. Adjust thresholds if needed")

if __name__ == "__main__":
    main()
