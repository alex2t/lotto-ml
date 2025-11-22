#!/usr/bin/env python3
"""
Test to verify that features and predictions change with new draws.
"""
import json
import numpy as np

print("="*70)
print("TESTING: Do features change when draws are added?")
print("="*70)

# 1. Check latest draw in history
with open('data/lotto_draw_history.json', 'r') as f:
    history = json.load(f)

dates = sorted(history.keys(), reverse=True)
latest_date = dates[0]
print(f"\n1. Latest draw in JSON: {latest_date}")
print(f"   Numbers: {[n['number'] for n in history[latest_date]['winning_numbers_details']]}")
print(f"   Total draws in history: {len(history)}")

# 2. Check HMC data for a specific number (let's check #12 which appears recent)
with open('data/lotto_trigger_periods.json', 'r') as f:
    hmc = json.load(f)

test_num = '12'
if test_num in hmc:
    print(f"\n2. Number {test_num} HMC data:")
    print(f"   Total count: {hmc[test_num].get('total_count', 'N/A')}")
    print(f"   Last seen: {hmc[test_num].get('last_seen', 'N/A')}")
    print(f"   Category: {hmc[test_num].get('category', 'N/A')}")
    print(f"   Recent counts: {hmc[test_num].get('recent', {})}")

# 3. Check if predictions would be deterministic
print(f"\n3. Random seed configuration:")
from ml_lotto.config import RANDOM_SEED_BASE
print(f"   RANDOM_SEED_BASE: {RANDOM_SEED_BASE}")
print(f"   Note: Fixed seed = deterministic results with SAME data")
print(f"         But predictions SHOULD change when features change!")

# 4. Simulate feature extraction for number 12
print(f"\n4. Simulating feature extraction:")
from ml_lotto.features.extractor import extract_features_from_hmc_json
from ml_lotto.data.loader import load_draw_history_with_bias_ratios

# Load minimal data needed
all_draws, history_log = load_draw_history_with_bias_ratios('data/lotto_draw_history.json')
print(f"   Loaded {len(all_draws)} draws for feature extraction")
print(f"   First draw: {all_draws[0]['date']}")
print(f"   Last draw: {all_draws[-1]['date']}")

# Check if the last draw date matches what we expect
if all_draws[-1]['date'] == latest_date:
    print(f"   ✓ Feature extraction uses latest draw!")
else:
    print(f"   ✗ WARNING: Last draw {all_draws[-1]['date']} != latest {latest_date}")

print(f"\n5. Checking number {test_num} in last 5 draws:")
for draw in all_draws[-5:]:
    has_num = test_num in [str(n) for n in draw['numbers']]
    print(f"   {draw['date']}: {'✓ HIT' if has_num else '  ---'} {draw['numbers']}")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
print("If the latest draw date matches in all places, then:")
print("  1. drawpick.py is working correctly")
print("  2. JSON files are updated")
print("  3. Feature extraction sees the new data")
print("\nIf predictions don't change, the issue might be:")
print("  A) Model training uses old data (check train/val split)")
print("  B) Features don't change enough to affect probabilities")
print("  C) Something else in the prediction pipeline")
print("="*70)
