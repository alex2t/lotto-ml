"""
display.py
==========
Handles all output display formatting and analysis visualization.
"""

from typing import List, Dict, Any
from ml_lotto.config import SHOW_OVERLAP_ANALYSIS, SHOW_DATA_SOURCE_SUMMARY


def display_final_picks(lines: List[Dict[str, Any]]):
    """Display final recommended picks."""
    print("\n" + "=" * 70)
    print("FINAL RECOMMENDED PICKS")
    print("=" * 70)
    
    for line in lines:
        print(f"\nLine {line['model_index']}: {line['model_name']} [{line['config_str']}]")
        print(f"Description: {line['description']}")
        print(f"Numbers: {line['numbers']}")


def display_overlap_analysis(lines: List[Dict[str, Any]]):
    """Display overlap statistics between models."""
    if not SHOW_OVERLAP_ANALYSIS or len(lines) < 2:
        return
    
    print("\n" + "=" * 70)
    print("DIVERSITY ANALYSIS")
    print("=" * 70)
    
    # Convert to sets
    sets = [set(line['numbers']) for line in lines]
    
    # Pairwise overlaps
    if len(sets) >= 2:
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                overlap = len(sets[i] & sets[j])
                print(f"Model {i+1} ∩ Model {j+1}: {overlap} shared numbers")
    
    # All models overlap
    if len(sets) >= 3:
        all_overlap = len(set.intersection(*sets))
        print(f"All models share: {all_overlap} numbers")
    
    # Unique coverage
    all_numbers = set.union(*sets)
    print(f"\nTotal unique numbers across all models: {len(all_numbers)}")


def display_rank_aware_explanation(model_configs: List[Dict[str, Any]]):
    """Display explanation of rank-aware penalty system."""
    # Find the highest penalty for examples
    max_penalty = max([config['diversity_penalty'] for config in model_configs])
    
    if max_penalty == 0:
        return
    
    print("\n" + "=" * 70)
    print("RANK-AWARE PENALTY EXPLANATION")
    print("=" * 70)
    print("\nHow rank-aware penalties work:")
    print("  • Top-ranked numbers (model's strongest picks) get HIGHER penalties")
    print("  • Low-ranked numbers (uncertain picks) get LOWER penalties")
    print("  • Formula: penalty = base × (0.5 + 0.5 × rank_weight)")
    print(f"\nWith {max_penalty*100:.0f}% base penalty:")
    print(f"  • Rank #1:  ~{max_penalty*100:.1f}% penalty (full strength)")
    print(f"  • Rank #10: ~{max_penalty*0.9*100:.1f}% penalty")
    print(f"  • Rank #25: ~{max_penalty*0.75*100:.1f}% penalty")
    print(f"  • Rank #40: ~{max_penalty*0.55*100:.1f}% penalty")
    print("\nBenefit: Encourages diversity while allowing flexibility for uncertain picks")


def display_data_source_summary():
    """Display comprehensive data source explanation."""
    if not SHOW_DATA_SOURCE_SUMMARY:
        return
    
    print("\n" + "=" * 70)
    print("DATA SOURCE SUMMARY")
    print("=" * 70)
    print("\n📄 FILE: lotto_draw_history.json (REPLACING irish500.csv)")
    print("   PURPOSE: Training Labels (y) and Custom Feature Source")
    print("   USAGE: Provides draw dates, winning numbers, and bonus numbers")
    print("   EXAMPLE: Draw #250 → Numbers [2, 9, 24, 28, 33, 43] + Bonus [3]")
    print("            Creates labels: y(2)=1, y(3)=1, ..., y(43)=1, etc.")
    print("            Custom Feature: Calculates 'days_since_bonus' for all numbers")
    
    print("\n📄 FILE: lotto_trigger_periods.json")
    print("   PURPOSE: Training Features (X)")
    print("   USAGE: Provides statistics for each number 1-47")
    print("   FEATURES EXTRACTED:")
    print("     • total_count     - Total times number appeared")
    print("     • days_since_last - Days since last appearance")
    print("     • days_since_bonus- Days since number was last a bonus ball (NEW)")
    print("     • recent_4        - Appearances in last 4 draws")
    print("     • recent_6        - Appearances in last 6 draws")
    print("     • recent_9        - Appearances in last 9 draws")
    print("     • recent_14       - Appearances in last 14 draws")
    print("     • series_total    - Total streak pattern occurrences")
    print("     • series_recent   - Recent streak patterns (last 60 days)")
    print("     • category        - Hot/Medium/Cold classification")
    
    print("\n📄 FILE: lotto_odds_results.json")
    print("   PURPOSE: Informational Only")
    print("   USAGE: Shows most common HMC pattern (e.g., '2-3-2' = 12.69%)")
    print("   NOTE: NOT used in ML training, just for display")
    
    print("\n" + "=" * 70)
    print("TRAINING FLOW")
    print("=" * 70)
    print("\n1. Load Draw History JSON → Extract winning numbers/dates for labels & custom feature calculation")
    print("2. Load HMC JSON → Extract statistics (basic features)")
    print("3. Combine:")
    print("   • X (features) ← JSON statistics + calculated features (like days_since_bonus)")
    print("   • y (labels)   ← Draw History JSON winning numbers")
    print("4. Train models on (X, y) pairs with different feature subsets")
    print("5. Use trained models to predict probabilities for next draw")
    print("6. Apply rank-aware penalties to encourage diversity")


def display_feature_configuration(model_configs: List[Dict[str, Any]]):
    """Display feature configuration summary."""
    print("\n" + "=" * 70)
    print("FEATURE CONFIGURATION SUMMARY")
    print("=" * 70)
    
    for idx, config in enumerate(model_configs, 1):
        print(f"\nModel {idx}: {config['name']}")
        feature_spec = config['features']
        if isinstance(feature_spec, str):
            print(f"  Features: {feature_spec}")
        else:
            print(f"  Features: {', '.join(feature_spec)}")
        print(f"  Algorithm: {config['algorithm']}")
        print(f"  Diversity Penalty: {config['diversity_penalty']*100:.0f}%")


def display_completion_message():
    """Display completion message."""
    print("\n" + "=" * 70)
    print("✓ Analysis complete!")
    print("=" * 70)