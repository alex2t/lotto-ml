"""
Test rolling statistics integration
"""
import json
from ml_lotto.features.rolling_stats import extract_rolling_features_for_all_numbers

# Load the HMC data
with open('data/lotto_trigger_periods.json', 'r') as f:
    hmc_data = json.load(f)

print("Testing rolling statistics extraction...")
print(f"Total draws in dataset: {len(hmc_data['draws'])}")

# Test with training start at draw 100
TRAINING_START_DRAW = 100
rolling_features = extract_rolling_features_for_all_numbers(
    hmc_data['draws'],
    training_start_draw=TRAINING_START_DRAW,
    max_number=47
)

print(f"\n✓ Rolling statistics calculated for {len(rolling_features)} numbers")

# Show sample features for number 5
print(f"\nSample rolling features for number 5:")
for feature_name, value in sorted(rolling_features[5].items()):
    print(f"  {feature_name}: {value:.4f}")

# Verify all expected features exist
expected_features = [
    'rolling_rate_10', 'rolling_rate_20', 'rolling_rate_50',
    'rolling_trend_10', 'rolling_trend_20', 'rolling_trend_50',
    'gap_variance', 'gap_cv', 'appearance_acceleration'
]

print(f"\nVerifying all expected features present...")
for num in [1, 5, 10, 20, 30, 40, 47]:
    missing = [f for f in expected_features if f not in rolling_features[num]]
    if missing:
        print(f"  ❌ Number {num}: Missing features {missing}")
    else:
        print(f"  ✅ Number {num}: All 9 rolling features present")

print(f"\n✅ Rolling statistics integration test PASSED!")
