"""
Quick test to verify rolling statistics integration
"""
from ml_lotto.data.loader import load_draw_history_with_bias_ratios
from ml_lotto.features.rolling_stats import extract_rolling_features_for_all_numbers

DRAW_HISTORY_JSON = 'data/lotto_draw_history.json'
TRAINING_START_DRAW = 100
MAX_NUMBER = 47

print("Loading draw history...")
all_draws, _ = load_draw_history_with_bias_ratios(DRAW_HISTORY_JSON)
print(f"✓ Loaded {len(all_draws)} draws")

# Check structure of first draw
print(f"\nFirst draw structure:")
print(f"  date: {all_draws[0]['date']}")
print(f"  draw_index: {all_draws[0]['draw_index']}")
print(f"  numbers: {all_draws[0]['numbers']}")
print(f"  bonus_number: {all_draws[0]['bonus_number']}")

print(f"\nCalculating rolling statistics...")
rolling_stats_features = extract_rolling_features_for_all_numbers(
    all_draws,
    training_start_draw=TRAINING_START_DRAW,
    max_number=MAX_NUMBER
)

print(f"✓ Calculated rolling statistics for {len(rolling_stats_features)} numbers")

# Show sample for number 5
print(f"\nSample rolling features for number 5:")
for feature_name, value in sorted(rolling_stats_features[5].items()):
    print(f"  {feature_name}: {value:.4f}")

print(f"\n✅ Rolling statistics integration SUCCESSFUL!")
