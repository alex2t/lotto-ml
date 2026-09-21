"""
display.py
==========
Handles all output display formatting and analysis visualization.
"""

from typing import List, Dict, Any
from ml_lotto.config import SHOW_OVERLAP_ANALYSIS, SHOW_DATA_SOURCE_SUMMARY
from ml_lotto.prediction.wheel import WHEEL_SIZE


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


def display_data_source_summary():
    """Display comprehensive data source explanation."""
    if not SHOW_DATA_SOURCE_SUMMARY:
        return
    
    print("\n" + "=" * 70)
    print("DATA SOURCE SUMMARY")
    print("=" * 70)
    print("\nFILE: lotto_draw_history.json (REPLACING irish500.csv)")
    print("   PURPOSE: Training Labels (y) and Custom Feature Source")
    print("   USAGE: Provides draw dates, winning numbers, and bonus numbers")
    print("   EXAMPLE: Draw #250 → Numbers [2, 9, 24, 28, 33, 43] + Bonus [3]")
    print("            Creates labels: y(2)=1, y(3)=1, ..., y(43)=1, etc.")
    print("            Custom Feature: Calculates 'days_since_bonus' for all numbers")
    
    print("\nFILE: lotto_trigger_periods.json")
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
    print("     • category        - Hot/Medium/Cold classification")
    
    print("\nFILE: lotto_odds_results.json")
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


def display_pool_analysis(pool_data: Dict[str, Any]):
    """
    Display pool with dynamic sizing based on pool_data['pool_size'].

    Show:
    - Hot/Medium/Cold candidates with probabilities
    - Freshness distribution (C0/C1/C2 counts)
    - Quality score (0-100)
    - Full ranked pool list
    """
    print("\n" + "=" * 70)
    print("MODEL 4: CANDIDATE POOL ANALYSIS")
    print("=" * 70)
    print(f"Pool Configuration: {pool_data['pool_config']}")
    print(f"Total Candidates: {pool_data['pool_size']}")

    # Display HOT candidates
    hot_candidates = pool_data['hot_candidates']
    if hot_candidates:
        print(f"\nHOT CANDIDATES ({len(hot_candidates)} numbers):")
        print(f"{'Rank':<6} {'Number':<8} {'Prob':<10} {'Fresh':<8} {'Recent_4':<10} {'Days_Since':<12}")
        print("-" * 70)
        for idx, candidate in enumerate(hot_candidates, 1):
            print(f"{idx:<6} #{candidate['number']:<6} {candidate['probability']:<10.4f} "
                  f"C{candidate['freshness_bin']:<7} {candidate['recent_4']:<10} "
                  f"{candidate['days_since_last']:<12}")

    # Display MEDIUM candidates
    medium_candidates = pool_data['medium_candidates']
    if medium_candidates:
        print(f"\nMEDIUM CANDIDATES ({len(medium_candidates)} numbers):")
        print(f"{'Rank':<6} {'Number':<8} {'Prob':<10} {'Fresh':<8} {'Recent_4':<10} {'Days_Since':<12}")
        print("-" * 70)
        for idx, candidate in enumerate(medium_candidates, 1):
            print(f"{idx:<6} #{candidate['number']:<6} {candidate['probability']:<10.4f} "
                  f"C{candidate['freshness_bin']:<7} {candidate['recent_4']:<10} "
                  f"{candidate['days_since_last']:<12}")

    # Display COLD candidates
    cold_candidates = pool_data['cold_candidates']
    if cold_candidates:
        print(f"\nCOLD CANDIDATES ({len(cold_candidates)} numbers):")
        print(f"{'Rank':<6} {'Number':<8} {'Prob':<10} {'Fresh':<8} {'Recent_4':<10} {'Days_Since':<12}")
        print("-" * 70)
        for idx, candidate in enumerate(cold_candidates, 1):
            print(f"{idx:<6} #{candidate['number']:<6} {candidate['probability']:<10.4f} "
                  f"C{candidate['freshness_bin']:<7} {candidate['recent_4']:<10} "
                  f"{candidate['days_since_last']:<12}")

    # Display freshness distribution
    freshness_dist = pool_data['freshness_distribution']
    pool_size = pool_data['pool_size']
    print(f"\nFRESHNESS DISTRIBUTION:")

    # Expected targets
    expected_targets = {0: 0.43, 1: 0.29, 2: 0.28}

    for bin_val in sorted(freshness_dist.keys()):
        count = freshness_dist[bin_val]
        pct = (count / pool_size * 100) if pool_size > 0 else 0
        target_pct = expected_targets.get(bin_val, 0) * 100

        # Check if within 10% of target
        deviation = abs(pct - target_pct)
        status = "" if deviation < 10 else "~"

        print(f"C{bin_val}:  {count:2d} numbers ({pct:5.1f}%)  Target: ~{target_pct:.0f}%  {status}")

    # Display quality score
    quality_score = pool_data['quality_score']
    if quality_score >= 90:
        quality_label = "Excellent"
    elif quality_score >= 75:
        quality_label = "Very Good"
    elif quality_score >= 60:
        quality_label = "Good"
    elif quality_score >= 50:
        quality_label = "Fair"
    else:
        quality_label = "Poor"

    print(f"\nPOOL QUALITY: {quality_score:.0f}/100 ({quality_label})")

    # Display full pool (sorted by probability)
    pool_numbers = pool_data['pool']
    print(f"\nFULL POOL (ranked by probability): {pool_numbers}")

    print(f"\nWHEEL (top {WHEEL_SIZE} of pool, every 3-subset covered):")
    for idx, line in enumerate(pool_data['wheel_lines'], 1):
        print(f"  Wheel Line {idx}: {line}")
    print(f"  Guarantee: 3+ winners in the top {WHEEL_SIZE} -> some line matches 3+ (about 5.3% of draws).")
    print("  Not an edge: expected value is unchanged; lines are not filtered.")
    print("=" * 70)


def display_completion_message():
    """Display completion message."""
    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)