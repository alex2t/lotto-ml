#!/usr/bin/env python3
"""
Correlation Matrix Analyzer
============================
Discovers which lottery numbers frequently appear together (positive correlation)
or avoid each other (negative correlation).

This script analyzes:
1. Number co-occurrence patterns (pair analysis)
2. Positive correlations (numbers that "attract" each other)
3. Negative correlations (numbers that "repel" each other)
4. HMC category correlations (hot-hot, hot-cold, etc.)
5. Temporal correlations (does appearing in draw N predict N+1?)
6. Statistical significance testing (chi-square tests)

Usage:
    From project root:
        python analysis/correlation_matrix_analyzer.py

    From analysis folder:
        python correlation_matrix_analyzer.py

Output:
    - data/analysis/lotto_correlation_matrix.json (full correlation data)
    - data/analysis/lotto_correlation_summary.csv (top correlations)
    - Console output with key findings
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
import math

def load_draw_history() -> Dict[str, Any]:
    """Load draw history JSON."""
    try:
        # Try relative path from analysis folder first
        for path in ['../data/lotto_draw_history.json', 'data/lotto_draw_history.json']:
            if Path(path).exists():
                with open(path, 'r') as f:
                    return json.load(f)
        print("ERROR: data/lotto_draw_history.json not found")
        print("Run this script from either the project root or the analysis folder")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        sys.exit(1)


def calculate_expected_cooccurrence(total_draws: int, max_number: int = 47) -> float:
    """
    Calculate expected co-occurrence probability for random lottery.

    In a random lottery with 7 numbers from 47:
    P(both A and B appear) = P(A appears) * P(B appears | A appeared)
    = (7/47) * (6/46) ≈ 0.0193
    """
    p_first = 7 / max_number
    p_second_given_first = 6 / (max_number - 1)
    return p_first * p_second_given_first * total_draws


def build_cooccurrence_matrix(draw_history: Dict[str, Any], max_number: int = 47) -> Tuple[Dict, Dict, int]:
    """
    Build co-occurrence matrix for all number pairs.

    Returns:
        Tuple of:
        - cooccurrence_counts: {(num1, num2): count}
        - single_counts: {num: count}
        - total_draws: int
    """
    sorted_draws = sorted(
        draw_history.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    cooccurrence_counts = defaultdict(int)
    single_counts = defaultdict(int)

    for date, draw_data in sorted_draws:
        winning_details = draw_data.get('winning_numbers_details', [])

        if len(winning_details) < 7:
            continue

        # Get all 7 numbers (main + bonus)
        numbers = [detail['number'] for detail in winning_details]

        # Count single occurrences
        for num in numbers:
            single_counts[num] += 1

        # Count co-occurrences (pairs)
        for i in range(len(numbers)):
            for j in range(i + 1, len(numbers)):
                num1, num2 = sorted([numbers[i], numbers[j]])
                cooccurrence_counts[(num1, num2)] += 1

    return dict(cooccurrence_counts), dict(single_counts), len(sorted_draws)


def calculate_correlation_metrics(
    cooccurrence_counts: Dict[Tuple[int, int], int],
    single_counts: Dict[int, int],
    total_draws: int,
    max_number: int = 47
) -> List[Dict[str, Any]]:
    """
    Calculate correlation metrics for each number pair.

    Uses multiple correlation measures:
    - Lift: observed / expected ratio
    - PMI: Pointwise Mutual Information
    - Phi coefficient: correlation coefficient for binary variables
    - Chi-square statistic
    """
    results = []
    expected = calculate_expected_cooccurrence(total_draws, max_number)

    for (num1, num2), observed_count in cooccurrence_counts.items():
        # Skip if either number never appeared
        if num1 not in single_counts or num2 not in single_counts:
            continue

        count1 = single_counts[num1]
        count2 = single_counts[num2]

        # Calculate probabilities
        p1 = count1 / total_draws
        p2 = count2 / total_draws
        p_both = observed_count / total_draws
        p_expected = p1 * p2

        # Lift (observed / expected)
        lift = (p_both / p_expected) if p_expected > 0 else 0

        # PMI (Pointwise Mutual Information)
        pmi = math.log2(p_both / p_expected) if p_both > 0 and p_expected > 0 else 0

        # Phi coefficient (correlation for binary variables)
        # Contingency table:
        # both_appear, only_1, only_2, neither
        both = observed_count
        only_1 = count1 - both
        only_2 = count2 - both
        neither = total_draws - count1 - count2 + both

        n = total_draws
        phi_numerator = (both * neither) - (only_1 * only_2)
        phi_denominator = math.sqrt((both + only_1) * (both + only_2) *
                                   (only_1 + neither) * (only_2 + neither))
        phi = phi_numerator / phi_denominator if phi_denominator > 0 else 0

        # Chi-square statistic
        chi_square = calculate_chi_square(both, only_1, only_2, neither, n)

        # Determine significance (chi-square > 3.84 for p < 0.05, df=1)
        significant = chi_square > 3.84

        results.append({
            'number_1': num1,
            'number_2': num2,
            'observed_count': observed_count,
            'expected_count': round(expected, 2),
            'count_1': count1,
            'count_2': count2,
            'lift': round(lift, 3),
            'pmi': round(pmi, 3),
            'phi_coefficient': round(phi, 3),
            'chi_square': round(chi_square, 2),
            'significant': significant,
            'relationship': 'attract' if lift > 1 else 'repel' if lift < 1 else 'neutral'
        })

    return results


def calculate_chi_square(both: int, only_1: int, only_2: int, neither: int, n: int) -> float:
    """Calculate chi-square statistic for 2x2 contingency table."""
    # Expected frequencies
    e_both = (both + only_1) * (both + only_2) / n
    e_only_1 = (both + only_1) * (only_1 + neither) / n
    e_only_2 = (both + only_2) * (only_2 + neither) / n
    e_neither = (only_1 + neither) * (only_2 + neither) / n

    chi_sq = 0
    for observed, expected in [(both, e_both), (only_1, e_only_1),
                                (only_2, e_only_2), (neither, e_neither)]:
        if expected > 0:
            chi_sq += (observed - expected) ** 2 / expected

    return chi_sq


def analyze_hmc_correlations(draw_history: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze correlations between HMC categories.

    Questions:
    - Do hot numbers appear with other hot numbers?
    - Do hot and cold numbers avoid each other?
    """
    sorted_draws = sorted(
        draw_history.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    category_pairs = defaultdict(int)
    total_pairs = 0

    for date, draw_data in sorted_draws:
        winning_details = draw_data.get('winning_numbers_details', [])

        if len(winning_details) < 7:
            continue

        categories = [detail.get('category', 'unknown') for detail in winning_details]

        # Count category pairs
        for i in range(len(categories)):
            for j in range(i + 1, len(categories)):
                cat1, cat2 = sorted([categories[i], categories[j]])
                category_pairs[(cat1, cat2)] += 1
                total_pairs += 1

    # Calculate percentages
    category_percentages = {}
    for pair, count in category_pairs.items():
        percentage = (count / total_pairs * 100) if total_pairs > 0 else 0
        category_percentages[f"{pair[0]}-{pair[1]}"] = {
            'count': count,
            'percentage': round(percentage, 2)
        }

    return {
        'category_pair_distribution': category_percentages,
        'total_pairs': total_pairs,
        'interpretation': {
            'hot-hot': 'Hot numbers appearing together',
            'hot-medium': 'Hot and medium numbers appearing together',
            'hot-cold': 'Hot and cold numbers appearing together',
            'medium-medium': 'Medium numbers appearing together',
            'medium-cold': 'Medium and cold numbers appearing together',
            'cold-cold': 'Cold numbers appearing together'
        }
    }


def analyze_temporal_correlations(draw_history: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze if appearing in draw N predicts appearing in draw N+1.

    For each number, calculate:
    - Probability of appearing in next draw given it appeared in current draw
    - Probability of appearing in next draw given it didn't appear in current draw
    - Autocorrelation coefficient
    """
    sorted_draws = sorted(
        draw_history.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    temporal_stats = defaultdict(lambda: {
        'appeared_then_appeared': 0,
        'appeared_then_not': 0,
        'not_appeared_then_appeared': 0,
        'not_appeared_then_not': 0
    })

    for i in range(len(sorted_draws) - 1):
        current_draw = sorted_draws[i][1]
        next_draw = sorted_draws[i + 1][1]

        current_numbers = set([d['number'] for d in current_draw.get('winning_numbers_details', [])])
        next_numbers = set([d['number'] for d in next_draw.get('winning_numbers_details', [])])

        for num in range(1, 48):
            in_current = num in current_numbers
            in_next = num in next_numbers

            if in_current and in_next:
                temporal_stats[num]['appeared_then_appeared'] += 1
            elif in_current and not in_next:
                temporal_stats[num]['appeared_then_not'] += 1
            elif not in_current and in_next:
                temporal_stats[num]['not_appeared_then_appeared'] += 1
            else:
                temporal_stats[num]['not_appeared_then_not'] += 1

    # Calculate autocorrelation for each number
    autocorrelations = {}
    for num, stats in temporal_stats.items():
        total_appeared = stats['appeared_then_appeared'] + stats['appeared_then_not']
        total_not_appeared = stats['not_appeared_then_appeared'] + stats['not_appeared_then_not']

        if total_appeared > 0 and total_not_appeared > 0:
            p_appear_given_appeared = stats['appeared_then_appeared'] / total_appeared
            p_appear_given_not = stats['not_appeared_then_appeared'] / total_not_appeared

            # Autocorrelation (difference in probabilities)
            autocorr = p_appear_given_appeared - p_appear_given_not

            autocorrelations[str(num)] = {
                'autocorrelation': round(autocorr, 4),
                'p_appear_given_appeared': round(p_appear_given_appeared, 4),
                'p_appear_given_not': round(p_appear_given_not, 4),
                'interpretation': 'positive' if autocorr > 0 else 'negative' if autocorr < 0 else 'neutral'
            }

    return autocorrelations


def generate_summary_insights(correlations: List[Dict[str, Any]],
                              hmc_correlations: Dict[str, Any],
                              temporal_correlations: Dict[str, Any]) -> Dict[str, Any]:
    """Generate human-readable insights from correlation analysis."""

    # Sort by different metrics
    by_lift = sorted(correlations, key=lambda x: x['lift'], reverse=True)
    by_phi = sorted(correlations, key=lambda x: abs(x['phi_coefficient']), reverse=True)

    # Top attractors (lift > 1, significant)
    top_attractors = [c for c in by_lift if c['lift'] > 1 and c['significant']][:20]

    # Top repellers (lift < 1, significant)
    top_repellers = sorted(
        [c for c in correlations if c['lift'] < 1 and c['significant']],
        key=lambda x: x['lift']
    )[:20]

    # Strongest correlations (by phi coefficient)
    strongest_correlations = by_phi[:20]

    # Overall statistics
    total_pairs = len(correlations)
    significant_pairs = len([c for c in correlations if c['significant']])
    attract_pairs = len([c for c in correlations if c['lift'] > 1])
    repel_pairs = len([c for c in correlations if c['lift'] < 1])

    return {
        'summary_statistics': {
            'total_pairs_analyzed': total_pairs,
            'significant_correlations': significant_pairs,
            'significant_percentage': round(significant_pairs / total_pairs * 100, 2) if total_pairs > 0 else 0,
            'attraction_pairs': attract_pairs,
            'repulsion_pairs': repel_pairs,
            'neutral_pairs': total_pairs - attract_pairs - repel_pairs
        },
        'top_20_attractors': top_attractors,
        'top_20_repellers': top_repellers,
        'strongest_20_correlations': strongest_correlations,
        'hmc_category_correlations': hmc_correlations,
        'temporal_autocorrelations': temporal_correlations
    }


def save_csv_summary(correlations: List[Dict[str, Any]]):
    """Save CSV summary of top correlations."""
    # Try both paths
    for path in ['../data/analysis/lotto_correlation_summary.csv', 'data/analysis/lotto_correlation_summary.csv']:
        try:
            with open(path, 'w') as f:
                # Header
                f.write("Number_1,Number_2,Observed,Expected,Lift,Phi,Chi_Square,Significant,Relationship\n")

                # Sort by absolute phi coefficient
                sorted_corr = sorted(correlations, key=lambda x: abs(x['phi_coefficient']), reverse=True)

                for corr in sorted_corr[:100]:  # Top 100
                    f.write(f"{corr['number_1']},{corr['number_2']},{corr['observed_count']},"
                           f"{corr['expected_count']},{corr['lift']},{corr['phi_coefficient']},"
                           f"{corr['chi_square']},{corr['significant']},{corr['relationship']}\n")

            print(f"CSV summary saved to {path}")
            return
        except:
            continue

    print("Could not save CSV summary")


def print_results(insights: Dict[str, Any]):
    """Print analysis results to console."""
    print("\n" + "=" * 80)
    print("LOTTERY NUMBER CORRELATION ANALYSIS")
    print("=" * 80)

    stats = insights['summary_statistics']
    print(f"\nOVERALL STATISTICS:")
    print(f"  Total number pairs analyzed: {stats['total_pairs_analyzed']}")
    print(f"  Statistically significant: {stats['significant_correlations']} ({stats['significant_percentage']}%)")
    print(f"  Attraction pairs (lift > 1): {stats['attraction_pairs']}")
    print(f"  Repulsion pairs (lift < 1): {stats['repulsion_pairs']}")
    print(f"  Neutral pairs: {stats['neutral_pairs']}")

    print("\n" + "-" * 80)
    print("TOP 10 NUMBER PAIRS THAT ATTRACT (appear together more than expected)")
    print("-" * 80)
    print(f"{'Pair':<12} {'Observed':<10} {'Expected':<10} {'Lift':<8} {'Phi':<8} {'Sig?':<6}")
    print("-" * 80)

    for i, corr in enumerate(insights['top_20_attractors'][:10], 1):
        pair = f"{corr['number_1']}-{corr['number_2']}"
        sig = "" if corr['significant'] else ""
        print(f"{pair:<12} {corr['observed_count']:<10} {corr['expected_count']:<10} "
              f"{corr['lift']:<8.3f} {corr['phi_coefficient']:<8.3f} {sig:<6}")

    print("\n" + "-" * 80)
    print("TOP 10 NUMBER PAIRS THAT REPEL (appear together less than expected)")
    print("-" * 80)
    print(f"{'Pair':<12} {'Observed':<10} {'Expected':<10} {'Lift':<8} {'Phi':<8} {'Sig?':<6}")
    print("-" * 80)

    for i, corr in enumerate(insights['top_20_repellers'][:10], 1):
        pair = f"{corr['number_1']}-{corr['number_2']}"
        sig = "" if corr['significant'] else ""
        print(f"{pair:<12} {corr['observed_count']:<10} {corr['expected_count']:<10} "
              f"{corr['lift']:<8.3f} {corr['phi_coefficient']:<8.3f} {sig:<6}")

    print("\n" + "-" * 80)
    print("HMC CATEGORY CORRELATIONS")
    print("-" * 80)

    hmc = insights['hmc_category_correlations']['category_pair_distribution']
    for pair, data in sorted(hmc.items(), key=lambda x: x[1]['percentage'], reverse=True):
        print(f"  {pair:<20} : {data['percentage']:>6.2f}% ({data['count']} occurrences)")

    print("\n" + "-" * 80)
    print("TEMPORAL AUTOCORRELATION (Top 10 numbers)")
    print("-" * 80)
    print(f"{'Number':<8} {'Autocorr':<12} {'P(appear|appeared)':<20} {'P(appear|not)':<20}")
    print("-" * 80)

    temporal = insights['temporal_autocorrelations']
    sorted_temporal = sorted(
        temporal.items(),
        key=lambda x: abs(x[1]['autocorrelation']),
        reverse=True
    )[:10]

    for num, data in sorted_temporal:
        print(f"{num:<8} {data['autocorrelation']:<12.4f} {data['p_appear_given_appeared']:<20.4f} "
              f"{data['p_appear_given_not']:<20.4f}")

    print("\n" + "=" * 80)
    print("INTERPRETATION GUIDE")
    print("=" * 80)
    print("Lift > 1.0:  Numbers appear together MORE than random chance")
    print("Lift < 1.0:  Numbers appear together LESS than random chance")
    print("Lift ≈ 1.0:  Numbers appear together at random chance")
    print("\nPhi coefficient: Ranges from -1 (perfect negative) to +1 (perfect positive)")
    print("Chi-square > 3.84: Statistically significant at p < 0.05")
    print("\nAutocorrelation > 0: Number more likely to appear again in next draw")
    print("Autocorrelation < 0: Number less likely to appear again in next draw")
    print("=" * 80)


def main():
    """Main execution function."""
    print("Loading draw history...")
    draw_history = load_draw_history()
    print(f"Loaded {len(draw_history)} draws")

    print("\n1. Building co-occurrence matrix...")
    cooccurrence_counts, single_counts, total_draws = build_cooccurrence_matrix(draw_history)
    print(f"Analyzed {len(cooccurrence_counts)} number pairs")

    print("\n2. Calculating correlation metrics...")
    correlations = calculate_correlation_metrics(cooccurrence_counts, single_counts, total_draws)
    print(f"Calculated correlations for {len(correlations)} pairs")

    print("\n3. Analyzing HMC category correlations...")
    hmc_correlations = analyze_hmc_correlations(draw_history)
    print(f"Analyzed {hmc_correlations['total_pairs']} category pairs")

    print("\n4. Analyzing temporal correlations...")
    temporal_correlations = analyze_temporal_correlations(draw_history)
    print(f"Calculated autocorrelations for 47 numbers")

    print("\n5. Generating insights...")
    insights = generate_summary_insights(correlations, hmc_correlations, temporal_correlations)

    # Save full results
    output_data = {
        'metadata': {
            'total_draws': total_draws,
            'total_pairs': len(correlations),
            'analysis_type': 'correlation_matrix',
            'methods': ['lift', 'pmi', 'phi_coefficient', 'chi_square', 'temporal_autocorrelation']
        },
        'all_correlations': correlations,
        'insights': insights
    }

    # Save JSON (try both paths)
    for path in ['../data/analysis/lotto_correlation_matrix.json', 'data/analysis/lotto_correlation_matrix.json']:
        try:
            with open(path, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"Full results saved to {path}")
            break
        except:
            continue

    # Save CSV summary
    save_csv_summary(correlations)

    # Print results
    print_results(insights)


if __name__ == "__main__":
    main()
