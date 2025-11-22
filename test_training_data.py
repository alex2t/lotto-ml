#!/usr/bin/env python3
"""
Test to verify which draws are used for training.
"""
import json
from ml_lotto.config import TRAINING_START_DRAW, VALIDATION_SPLIT_RATIO
from ml_lotto.data.loader import load_draw_history_with_bias_ratios
from ml_lotto.models.trainer import calculate_train_val_split

print("="*70)
print("TESTING: Which draws are used for MODEL TRAINING?")
print("="*70)

# Load draw history
all_draws, _ = load_draw_history_with_bias_ratios('data/lotto_draw_history.json')

print(f"\n1. Total draws loaded: {len(all_draws)}")
print(f"   First draw: {all_draws[0]['date']}")
print(f"   Last draw: {all_draws[-1]['date']}")

print(f"\n2. Training configuration:")
print(f"   TRAINING_START_DRAW: {TRAINING_START_DRAW} (skip first {TRAINING_START_DRAW} draws)")
print(f"   VALIDATION_SPLIT_RATIO: {VALIDATION_SPLIT_RATIO}")

# Calculate train/val split
train_end_idx, val_start_idx = calculate_train_val_split(len(all_draws))

print(f"\n3. Training/Validation split:")
print(f"   Available draws: {len(all_draws)} - {TRAINING_START_DRAW} = {len(all_draws) - TRAINING_START_DRAW}")
print(f"   Training range: draws {TRAINING_START_DRAW} to {train_end_idx-1}")
print(f"   Validation range: draws {val_start_idx} to {len(all_draws)-1}")

print(f"\n4. Training set uses draws from:")
print(f"   Start: {all_draws[TRAINING_START_DRAW]['date']} (index {TRAINING_START_DRAW})")
print(f"   End:   {all_draws[train_end_idx-1]['date']} (index {train_end_idx-1})")

print(f"\n5. Validation set uses draws from:")
print(f"   Start: {all_draws[val_start_idx]['date']} (index {val_start_idx})")
print(f"   End:   {all_draws[-1]['date']} (index {len(all_draws)-1})")

print(f"\n6. CRITICAL CHECK:")
latest_in_training = train_end_idx - 1
latest_date_training = all_draws[latest_in_training]['date']
actual_latest = all_draws[-1]['date']

print(f"   Latest draw overall: {actual_latest}")
print(f"   Latest draw in training: {latest_date_training}")

if latest_date_training == actual_latest:
    print(f"   ✓ Training uses the LATEST draw!")
else:
    print(f"   ✗ Training STOPS at {latest_date_training}")
    print(f"   ✗ New draws ({actual_latest}) go to VALIDATION, not training!")
    print(f"\n   This means:")
    print(f"   - Model doesn't learn from new draws")
    print(f"   - Predictions use OLD patterns")
    print(f"   - Adding 1 draw doesn't help (need to add {len(all_draws) - train_end_idx + 1}+ draws)")

print("\n" + "="*70)
