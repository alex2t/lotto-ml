#!/usr/bin/env python3
"""
Feature Interaction Explorer
=============================
Discovers non-linear feature interactions and combinations that are most
predictive of lottery number wins.

This script analyzes:
1. Which feature combinations are most predictive (pairwise interactions)
2. Interaction effects (e.g., high total_count + low days_since_last)
3. Threshold effects (does behavior change at specific values?)
4. Multi-feature interactions (category × freshness × recency)
5. Conditional win rates (win probability given feature combination)

Usage:
    From project root:
        python analysis/feature_interaction_explorer.py

    From analysis folder:
        python feature_interaction_explorer.py

Output:
    - data/lotto_feature_interactions.json (full interaction analysis)
    - data/lotto_interaction_summary.csv (top interactions, Excel-ready)
    - data/lotto_composite_features.json (recommended composite features)
    - Console output with key findings
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
import math

def load_draw_history() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Load draw history JSON and convert to sorted list."""
    try:
        # Try relative path from analysis folder first
        for path in ['../data/lotto_draw_history.json', 'data/lotto_draw_history.json']:
            if Path(path).exists():
                with open(path, 'r') as f:
                    data = json.load(f)

                # Convert to sorted list
                sorted_draws = []
                for date, draw_data in data.items():
                    winning_details = draw_data.get('winning_numbers_details', [])
                    if len(winning_details) >= 7:
                        sorted_draws.append({
                            'date': date,
                            'draw_index': draw_data.get('draw_index', 0),
                            'winning_details': winning_details,
                            'hmc_summary': draw_data.get('hmc_summary', {})
                        })

                sorted_draws.sort(key=lambda x: x['draw_index'])
                return data, sorted_draws

        print("ERROR: data/lotto_draw_history.json not found")
        print("Run this script from either the project root or the analysis folder")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        sys.exit(1)


def extract_features_from_draw(winning_details: List[Dict]) -> Dict[int, Dict[str, Any]]:
    """
    Extract features for all numbers from a draw's winning_numbers_details.

    Returns:
        Dict mapping number -> feature dict
    """
    features = {}

    for detail in winning_details:
        num = detail['number']

        # Extract available features
        features[num] = {
            'total_count': detail.get('total_count', 0),
            'days_since_last': detail.get('days_since_last_hit', 0),
            'category': detail.get('category', 'unknown'),
            'freshness_bin': detail.get('current_freshness_bin', 0),
            'recent_4': detail.get('recent_counts', {}).get('last_4', 0),
            'recent_9': detail.get('recent_counts', {}).get('last_9', 0),
            'recent_14': detail.get('recent_counts', {}).get('last_14', 0),
            'is_bonus': detail.get('is_bonus', False),
            'bonus_hit_contribution': detail.get('bonus_hit_contribution', 0.0),
            'is_recent_bonus_hit': detail.get('is_recent_bonus_hit', False),
            'win_bias_ratio': detail.get('win_bias_ratio', 1.0)
        }

    return features


def build_feature_matrix(sorted_draws: List[Dict[str, Any]], max_number: int = 47) -> List[Dict[str, Any]]:
    """
    Build a feature matrix with win labels.

    Returns:
        List of records: {number, features, is_winner, is_main_winner, is_bonus_winner}
    """
    records = []

    for draw in sorted_draws:
        winning_details = draw['winning_details']
        features_dict = extract_features_from_draw(winning_details)

        # Get winners (first 6 are main, 7th is bonus)
        main_winners = set([winning_details[i]['number'] for i in range(min(6, len(winning_details)))])
        bonus_winner = winning_details[6]['number'] if len(winning_details) >= 7 else None
        all_winners = main_winners | ({bonus_winner} if bonus_winner else set())

        # Create record for each number
        for num, features in features_dict.items():
            records.append({
                'draw_index': draw['draw_index'],
                'number': num,
                'features': features,
                'is_winner': num in all_winners,
                'is_main_winner': num in main_winners,
                'is_bonus_winner': num == bonus_winner
            })

    return records


def analyze_pairwise_interactions(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze pairwise feature interactions.

    For each pair of numeric features, test if their combination predicts wins
    better than either feature alone.

    Returns:
        List of interaction results sorted by strength
    """
    numeric_features = ['total_count', 'days_since_last', 'recent_4', 'recent_9',
                       'recent_14', 'freshness_bin', 'bonus_hit_contribution']

    interactions = []

    for i, feat1 in enumerate(numeric_features):
        for feat2 in numeric_features[i+1:]:
            # Analyze this pair
            interaction = analyze_feature_pair(records, feat1, feat2)
            if interaction:
                interactions.append(interaction)

    # Sort by interaction strength
    interactions.sort(key=lambda x: x['interaction_strength'], reverse=True)

    return interactions


def analyze_feature_pair(records: List[Dict[str, Any]],
                         feat1: str, feat2: str) -> Dict[str, Any]:
    """
    Analyze interaction between two features.

    Strategy:
    1. Split each feature into high/low based on median
    2. Calculate win rates for 4 quadrants: (high, high), (high, low), (low, high), (low, low)
    3. Compute interaction strength
    """
    # Extract feature values
    values1 = [r['features'][feat1] for r in records]
    values2 = [r['features'][feat2] for r in records]

    # Calculate medians
    median1 = sorted(values1)[len(values1) // 2]
    median2 = sorted(values2)[len(values2) // 2]

    # Count wins in each quadrant
    quadrants = {
        ('high', 'high'): {'wins': 0, 'total': 0},
        ('high', 'low'): {'wins': 0, 'total': 0},
        ('low', 'high'): {'wins': 0, 'total': 0},
        ('low', 'low'): {'wins': 0, 'total': 0}
    }

    for r in records:
        val1 = r['features'][feat1]
        val2 = r['features'][feat2]

        level1 = 'high' if val1 >= median1 else 'low'
        level2 = 'high' if val2 >= median2 else 'low'

        quadrants[(level1, level2)]['total'] += 1
        if r['is_main_winner']:  # Only count main winners
            quadrants[(level1, level2)]['wins'] += 1

    # Calculate win rates
    win_rates = {}
    for quad, stats in quadrants.items():
        if stats['total'] > 0:
            win_rates[quad] = stats['wins'] / stats['total']
        else:
            win_rates[quad] = 0

    # Calculate interaction strength
    # Interaction exists if (high, high) has different win rate than expected from marginals
    expected_high_high = (win_rates[('high', 'high')] + win_rates[('high', 'low')] +
                         win_rates[('low', 'high')] + win_rates[('low', 'low')]) / 4

    observed_high_high = win_rates[('high', 'high')]

    # Interaction strength: how much (high, high) deviates from average
    interaction_strength = abs(observed_high_high - expected_high_high) / (expected_high_high + 1e-10)

    # Determine interaction type
    if observed_high_high > expected_high_high * 1.1:
        interaction_type = 'synergistic'  # Both high is better than expected
    elif observed_high_high < expected_high_high * 0.9:
        interaction_type = 'antagonistic'  # Both high is worse than expected
    else:
        interaction_type = 'neutral'

    return {
        'feature_1': feat1,
        'feature_2': feat2,
        'median_1': round(median1, 2),
        'median_2': round(median2, 2),
        'win_rate_high_high': round(win_rates[('high', 'high')], 4),
        'win_rate_high_low': round(win_rates[('high', 'low')], 4),
        'win_rate_low_high': round(win_rates[('low', 'high')], 4),
        'win_rate_low_low': round(win_rates[('low', 'low')], 4),
        'interaction_strength': round(interaction_strength, 4),
        'interaction_type': interaction_type,
        'sample_sizes': {
            'high_high': quadrants[('high', 'high')]['total'],
            'high_low': quadrants[('high', 'low')]['total'],
            'low_high': quadrants[('low', 'high')]['total'],
            'low_low': quadrants[('low', 'low')]['total']
        }
    }


def analyze_threshold_effects(records: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
    """
    Find threshold effects: does win probability change sharply at certain values?

    For each numeric feature, bin values and calculate win rate per bin.
    Look for sharp changes that indicate thresholds.
    """
    numeric_features = ['total_count', 'days_since_last', 'recent_4', 'recent_9',
                       'recent_14', 'freshness_bin']

    threshold_effects = {}

    for feat in numeric_features:
        # Extract values
        values = [r['features'][feat] for r in records]
        min_val = min(values)
        max_val = max(values)

        # Create bins
        num_bins = 10
        bin_size = (max_val - min_val) / num_bins if max_val > min_val else 1

        bins = {}
        for i in range(num_bins):
            bin_start = min_val + i * bin_size
            bin_end = min_val + (i + 1) * bin_size
            bins[i] = {
                'range': (round(bin_start, 2), round(bin_end, 2)),
                'wins': 0,
                'total': 0
            }

        # Assign records to bins
        for r in records:
            val = r['features'][feat]
            bin_idx = min(int((val - min_val) / bin_size), num_bins - 1)

            bins[bin_idx]['total'] += 1
            if r['is_main_winner']:
                bins[bin_idx]['wins'] += 1

        # Calculate win rates
        bin_results = []
        for i in range(num_bins):
            if bins[i]['total'] > 0:
                win_rate = bins[i]['wins'] / bins[i]['total']
                bin_results.append({
                    'bin_index': i,
                    'range': bins[i]['range'],
                    'win_rate': round(win_rate, 4),
                    'sample_size': bins[i]['total']
                })

        # Detect sharp changes (threshold candidates)
        thresholds = []
        for i in range(len(bin_results) - 1):
            current_rate = bin_results[i]['win_rate']
            next_rate = bin_results[i + 1]['win_rate']

            # Threshold if >20% change
            if abs(next_rate - current_rate) / (current_rate + 1e-10) > 0.2:
                thresholds.append({
                    'threshold_value': bin_results[i]['range'][1],
                    'before_win_rate': current_rate,
                    'after_win_rate': next_rate,
                    'change_pct': round((next_rate - current_rate) / (current_rate + 1e-10) * 100, 1)
                })

        threshold_effects[feat] = {
            'bins': bin_results,
            'thresholds': thresholds
        }

    return threshold_effects


def analyze_triple_interactions(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze category × freshness × recency interactions.

    Question: Does the combination of category, freshness, and recency predict wins?
    """
    # Count wins for each combination
    combos = defaultdict(lambda: {'wins': 0, 'total': 0})

    for r in records:
        category = r['features']['category']
        freshness = r['features']['freshness_bin']

        # Bin days_since_last into 3 levels
        days = r['features']['days_since_last']
        if days <= 7:
            recency = 'very_recent'
        elif days <= 21:
            recency = 'recent'
        else:
            recency = 'old'

        key = (category, freshness, recency)
        combos[key]['total'] += 1
        if r['is_main_winner']:
            combos[key]['wins'] += 1

    # Calculate win rates and sort
    results = []
    overall_win_rate = sum(c['wins'] for c in combos.values()) / sum(c['total'] for c in combos.values())

    for (cat, fresh, rec), stats in combos.items():
        if stats['total'] >= 10:  # Minimum sample size
            win_rate = stats['wins'] / stats['total']
            lift = win_rate / overall_win_rate if overall_win_rate > 0 else 1

            results.append({
                'category': cat,
                'freshness_bin': fresh,
                'recency': rec,
                'win_rate': round(win_rate, 4),
                'lift_over_baseline': round(lift, 3),
                'sample_size': stats['total'],
                'wins': stats['wins']
            })

    # Sort by lift
    results.sort(key=lambda x: x['lift_over_baseline'], reverse=True)

    return results


def generate_composite_features(interactions: List[Dict],
                                threshold_effects: Dict,
                                triple_interactions: List[Dict]) -> List[Dict[str, Any]]:
    """
    Generate recommended composite features based on discovered interactions.
    """
    recommendations = []

    # From pairwise interactions
    for interaction in interactions[:10]:  # Top 10
        if interaction['interaction_strength'] > 0.1:
            feat1 = interaction['feature_1']
            feat2 = interaction['feature_2']

            recommendations.append({
                'composite_name': f"{feat1}_x_{feat2}_interaction",
                'type': 'pairwise_interaction',
                'formula': f"(1 if {feat1} >= {interaction['median_1']} else 0) * "
                          f"(1 if {feat2} >= {interaction['median_2']} else 0)",
                'description': f"Binary interaction: both {feat1} and {feat2} are high",
                'expected_win_rate_when_true': interaction['win_rate_high_high'],
                'interaction_strength': interaction['interaction_strength'],
                'interaction_type': interaction['interaction_type']
            })

    # From threshold effects
    for feat, data in threshold_effects.items():
        for threshold in data['thresholds'][:2]:  # Top 2 per feature
            if abs(threshold['change_pct']) > 30:  # Significant change
                recommendations.append({
                    'composite_name': f"{feat}_above_{int(threshold['threshold_value'])}",
                    'type': 'threshold_binary',
                    'formula': f"1 if {feat} > {threshold['threshold_value']} else 0",
                    'description': f"Binary indicator if {feat} exceeds threshold {threshold['threshold_value']}",
                    'win_rate_before': threshold['before_win_rate'],
                    'win_rate_after': threshold['after_win_rate'],
                    'change_pct': threshold['change_pct']
                })

    # From triple interactions
    for triple in triple_interactions[:5]:  # Top 5
        if triple['lift_over_baseline'] > 1.2:
            recommendations.append({
                'composite_name': f"triple_{triple['category']}_{triple['freshness_bin']}_{triple['recency']}",
                'type': 'triple_interaction',
                'formula': f"1 if (category=='{triple['category']}' AND "
                          f"freshness_bin=={triple['freshness_bin']} AND "
                          f"recency=='{triple['recency']}') else 0",
                'description': f"Combination: {triple['category']} category, "
                              f"freshness {triple['freshness_bin']}, {triple['recency']} recency",
                'win_rate': triple['win_rate'],
                'lift_over_baseline': triple['lift_over_baseline']
            })

    return recommendations


def save_outputs(interactions: List, threshold_effects: Dict,
                triple_interactions: List, composite_features: List):
    """Save all outputs to files."""

    # Full JSON
    output_data = {
        'metadata': {
            'analysis_type': 'feature_interaction_exploration',
            'total_pairwise_interactions': len(interactions),
            'total_triple_interactions': len(triple_interactions),
            'total_composite_features': len(composite_features)
        },
        'pairwise_interactions': interactions,
        'threshold_effects': threshold_effects,
        'triple_interactions': triple_interactions,
        'recommended_composite_features': composite_features
    }

    for path in ['../data/lotto_feature_interactions.json', 'data/lotto_feature_interactions.json']:
        try:
            with open(path, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"✓ Full analysis saved to {path}")
            break
        except:
            continue

    # CSV summary of interactions
    for path in ['../data/lotto_interaction_summary.csv', 'data/lotto_interaction_summary.csv']:
        try:
            with open(path, 'w') as f:
                f.write("Feature_1,Feature_2,Interaction_Strength,Type,WinRate_High_High,"
                       "WinRate_High_Low,WinRate_Low_High,WinRate_Low_Low\n")
                for inter in interactions[:50]:  # Top 50
                    f.write(f"{inter['feature_1']},{inter['feature_2']},"
                           f"{inter['interaction_strength']},{inter['interaction_type']},"
                           f"{inter['win_rate_high_high']},{inter['win_rate_high_low']},"
                           f"{inter['win_rate_low_high']},{inter['win_rate_low_low']}\n")
            print(f"✓ Interaction summary saved to {path}")
            break
        except:
            continue

    # Composite features JSON
    for path in ['../data/lotto_composite_features.json', 'data/lotto_composite_features.json']:
        try:
            with open(path, 'w') as f:
                json.dump({
                    'composite_features': composite_features,
                    'usage_notes': 'These composite features can be added to ML models for improved prediction'
                }, f, indent=2)
            print(f"✓ Composite features saved to {path}")
            break
        except:
            continue


def print_results(interactions: List, threshold_effects: Dict,
                 triple_interactions: List, composite_features: List):
    """Print comprehensive results."""

    print("\n" + "=" * 80)
    print("FEATURE INTERACTION ANALYSIS")
    print("=" * 80)

    print(f"\nOVERALL STATISTICS:")
    print(f"  Pairwise interactions analyzed: {len(interactions)}")
    print(f"  Strong interactions found: {len([i for i in interactions if i['interaction_strength'] > 0.1])}")
    print(f"  Triple interactions analyzed: {len(triple_interactions)}")
    print(f"  Composite features recommended: {len(composite_features)}")

    print("\n" + "-" * 80)
    print("TOP 10 PAIRWISE FEATURE INTERACTIONS")
    print("-" * 80)
    print(f"{'Feature 1':<20} {'Feature 2':<20} {'Strength':<10} {'Type':<15} "
          f"{'High+High Rate':<15}")
    print("-" * 80)

    for inter in interactions[:10]:
        print(f"{inter['feature_1']:<20} {inter['feature_2']:<20} "
              f"{inter['interaction_strength']:<10.4f} {inter['interaction_type']:<15} "
              f"{inter['win_rate_high_high']:<15.4f}")

    print("\n" + "-" * 80)
    print("THRESHOLD EFFECTS (Sharp Changes in Win Probability)")
    print("-" * 80)

    for feat, data in threshold_effects.items():
        if data['thresholds']:
            print(f"\n{feat.upper()}:")
            for thresh in data['thresholds'][:2]:
                print(f"  Threshold at {thresh['threshold_value']}: "
                      f"{thresh['before_win_rate']:.4f} → {thresh['after_win_rate']:.4f} "
                      f"({thresh['change_pct']:+.1f}% change)")

    print("\n" + "-" * 80)
    print("TOP 10 TRIPLE INTERACTIONS (Category × Freshness × Recency)")
    print("-" * 80)
    print(f"{'Category':<12} {'Freshness':<12} {'Recency':<15} {'Win Rate':<12} "
          f"{'Lift':<10} {'Samples':<10}")
    print("-" * 80)

    for triple in triple_interactions[:10]:
        print(f"{triple['category']:<12} {triple['freshness_bin']:<12} "
              f"{triple['recency']:<15} {triple['win_rate']:<12.4f} "
              f"{triple['lift_over_baseline']:<10.3f} {triple['sample_size']:<10}")

    print("\n" + "-" * 80)
    print("RECOMMENDED COMPOSITE FEATURES (Top 10)")
    print("-" * 80)

    for i, comp in enumerate(composite_features[:10], 1):
        print(f"\n{i}. {comp['composite_name']}")
        print(f"   Type: {comp['type']}")
        print(f"   Description: {comp['description']}")
        if comp['type'] == 'pairwise_interaction':
            print(f"   Win rate when true: {comp['expected_win_rate_when_true']:.4f}")
            print(f"   Interaction strength: {comp['interaction_strength']:.4f}")
        elif comp['type'] == 'threshold_binary':
            print(f"   Win rate change: {comp['win_rate_before']:.4f} → {comp['win_rate_after']:.4f}")
        elif comp['type'] == 'triple_interaction':
            print(f"   Win rate: {comp['win_rate']:.4f}")
            print(f"   Lift: {comp['lift_over_baseline']:.3f}x")

    print("\n" + "=" * 80)
    print("INTERPRETATION GUIDE")
    print("=" * 80)
    print("Interaction Strength: Measures how much the combination deviates from expected")
    print("  - >0.2:  Very strong interaction")
    print("  - >0.1:  Strong interaction")
    print("  - >0.05: Moderate interaction")
    print("  - <0.05: Weak interaction")
    print("\nInteraction Types:")
    print("  - Synergistic: Both features high performs better than expected")
    print("  - Antagonistic: Both features high performs worse than expected")
    print("  - Neutral: No significant interaction effect")
    print("\nLift: Ratio of win rate vs baseline")
    print("  - >1.2:  Strong positive effect")
    print("  - <0.8:  Strong negative effect")
    print("=" * 80)


def main():
    """Main execution function."""
    print("Loading draw history...")
    full_history, sorted_draws = load_draw_history()
    print(f"✓ Loaded {len(sorted_draws)} draws")

    print("\n1. Building feature matrix...")
    records = build_feature_matrix(sorted_draws)
    print(f"✓ Built matrix with {len(records)} records")

    print("\n2. Analyzing pairwise interactions...")
    interactions = analyze_pairwise_interactions(records)
    print(f"✓ Analyzed {len(interactions)} feature pairs")

    print("\n3. Detecting threshold effects...")
    threshold_effects = analyze_threshold_effects(records)
    print(f"✓ Analyzed thresholds for {len(threshold_effects)} features")

    print("\n4. Analyzing triple interactions...")
    triple_interactions = analyze_triple_interactions(records)
    print(f"✓ Found {len(triple_interactions)} triple interaction patterns")

    print("\n5. Generating composite feature recommendations...")
    composite_features = generate_composite_features(
        interactions, threshold_effects, triple_interactions
    )
    print(f"✓ Generated {len(composite_features)} composite feature recommendations")

    print("\n6. Saving outputs...")
    save_outputs(interactions, threshold_effects, triple_interactions, composite_features)

    # Print results
    print_results(interactions, threshold_effects, triple_interactions, composite_features)


if __name__ == "__main__":
    main()
