"""
Validation Script: Check if was_recent_bonus Feature is Working
================================================================

Run this AFTER you've run quickpick.py at least once.

This script will:
1. Show which numbers have was_recent_bonus = 1
2. Show their prediction probabilities across all models
3. Compare with non-bonus numbers
4. Track actual wins (if you have new draw results)
"""

import json
import pandas as pd
from ml_lotto.data_loader import load_draw_history_with_bias_ratios
from ml_lotto.feature_extractor import calculate_was_recent_bonus
from ml_lotto.config import DRAW_HISTORY_JSON, MAX_NUMBER

def validate_bonus_feature():
    """Main validation function."""
    print("=" * 80)
    print("BONUS FEATURE VALIDATION")
    print("=" * 80)
    
    # Load draw history
    all_draws, _ = load_draw_history_with_bias_ratios(DRAW_HISTORY_JSON)
    
    # Calculate was_recent_bonus
    was_recent_bonus = calculate_was_recent_bonus(all_draws, lookback_draws=10)
    
    # Get recent bonus numbers
    recent_bonus_nums = [num for num in range(1, MAX_NUMBER + 1) if was_recent_bonus[num] == 1]
    non_bonus_nums = [num for num in range(1, MAX_NUMBER + 1) if was_recent_bonus[num] == 0]
    
    print(f"\n1. FEATURE STATUS")
    print(f"   Recent bonus numbers (last 10 draws): {recent_bonus_nums}")
    print(f"   Count: {len(recent_bonus_nums)}/47")
    
    # Show which draws they came from
    print(f"\n2. BONUS BALL HISTORY (Last 10 Draws)")
    recent_10 = all_draws[-10:]
    for i, draw in enumerate(recent_10, 1):
        bonus = draw.get('bonus_number')
        print(f"   Draw {i} ({draw['date']}): Bonus = {bonus}")
    
    # Check if picks favor recent bonus numbers
    print(f"\n3. CHECKING LATEST PREDICTIONS (lottery_picks.txt)")
    try:
        with open('lottery_picks.txt', 'r') as f:
            content = f.read()
            
        # Extract numbers from each line
        import re
        lines = content.split('\n')
        
        all_picks = []
        for line in lines:
            if 'Numbers:' in line:
                # Extract numbers from format: "Numbers: [1, 5, 12, 23, 31, 39, 44]"
                match = re.search(r'Numbers: \[(.*?)\]', line)
                if match:
                    nums = [int(x.strip()) for x in match.group(1).split(',')]
                    all_picks.append(nums)
        
        if all_picks:
            print(f"\n   Found {len(all_picks)} prediction lines")
            
            for idx, picks in enumerate(all_picks, 1):
                bonus_in_picks = [n for n in picks if n in recent_bonus_nums]
                print(f"\n   Line {idx}: {picks}")
                print(f"   → Contains {len(bonus_in_picks)} recent bonus numbers: {bonus_in_picks}")
                print(f"   → Bonus representation: {len(bonus_in_picks)}/6 = {len(bonus_in_picks)/6*100:.1f}%")
            
            # Calculate overall statistics
            total_picks = sum(len(picks) for picks in all_picks)
            total_bonus_picks = sum(len([n for n in picks if n in recent_bonus_nums]) for picks in all_picks)
            
            print(f"\n   OVERALL STATISTICS:")
            print(f"   - Total numbers picked: {total_picks}")
            print(f"   - Recent bonus numbers picked: {total_bonus_picks}")
            print(f"   - % of picks that are recent bonus: {total_bonus_picks/total_picks*100:.1f}%")
            print(f"   - Expected if random (no feature): {len(recent_bonus_nums)/47*100:.1f}%")
            print(f"   - Expected with 3.42x lift: ~{len(recent_bonus_nums)/47*3.42*100:.1f}%")
            
            if total_bonus_picks/total_picks > len(recent_bonus_nums)/47 * 1.5:
                print(f"   ✓ FEATURE IS WORKING! Models favor recent bonus numbers.")
            else:
                print(f"   ⚠️  WARNING: Feature might not be working as expected.")
        else:
            print("   ⚠️  Could not find predictions in lottery_picks.txt")
            
    except FileNotFoundError:
        print("   ⚠️  lottery_picks.txt not found. Run quickpick.py first.")
    
    # Historical validation
    print(f"\n4. HISTORICAL VALIDATION (Check if bonus → winner pattern exists)")
    
    if len(all_draws) >= 20:
        wins_after_bonus = 0
        total_checks = 0
        
        # For each draw (except last 5), check if bonus numbers won in next 5 draws
        for i in range(len(all_draws) - 15):
            # Get bonus numbers from draws i to i+10
            bonus_window = all_draws[i:i+10]
            bonus_nums = set()
            for draw in bonus_window:
                bn = draw.get('bonus_number')
                if bn:
                    bonus_nums.add(bn)
            
            # Check if any appeared as winners in next 5 draws
            future_window = all_draws[i+10:i+15]
            future_winners = set()
            for draw in future_window:
                # Only main numbers (first 6)
                future_winners.update(draw['numbers'][:6])
            
            # Count overlap
            overlap = len(bonus_nums & future_winners)
            wins_after_bonus += overlap
            total_checks += len(bonus_nums)
        
        if total_checks > 0:
            win_rate = wins_after_bonus / total_checks
            baseline_rate = 6 / 47  # Random chance
            lift = win_rate / baseline_rate if baseline_rate > 0 else 0
            
            print(f"   Bonus numbers analyzed: {total_checks}")
            print(f"   Won as main number in next 5 draws: {wins_after_bonus}")
            print(f"   Win rate: {win_rate*100:.1f}%")
            print(f"   Baseline (random): {baseline_rate*100:.1f}%")
            print(f"   Lift: {lift:.2f}x")
            
            if lift > 1.2:
                print(f"   ✓ CONFIRMED: Pattern exists in your data!")
            else:
                print(f"   ⚠️  Pattern weaker than expected from trend analyzer")
    
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    validate_bonus_feature()