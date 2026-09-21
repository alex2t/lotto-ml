#!/usr/bin/env python3
"""
Recency Zone Analyzer - Data-Driven Recency Scoring
====================================================

Analyzes optimal recency zones from historical draw data to replace
hard-coded thresholds in timing.py.

This analyzer:
1. Analyzes historical win rates by recency bins
2. Generates optimal thresholds per category (hot/medium/cold)
3. Outputs data-driven recency zone configuration
4. Validates statistical significance using scipy

NO HARD-CODED VALUES - All scores calculated from real data.

Author: Statistical Analysis Module
Version: 1.0 (Data-Driven Edition)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from collections import defaultdict
from lotto_analysis.utils.serialization import round_floats

# Try to import scipy, fall back to basic stats if not available
try:
    from scipy import stats
    import numpy as np
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("scipy not available - using basic statistical calculations")


def analyze_recency_zones(draw_history: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze optimal recency zones from historical data.

    Args:
        draw_history: Data from lotto_draw_history.json

    Returns:
        Dictionary with recency zone analysis by category
    """
    # Define bins based on the current hard-coded thresholds
    # We'll validate if these are optimal or if different bins would work better
    bins = [
        (0, 14, "0-14"),
        (15, 30, "15-30"),
        (31, 60, "31-60"),
        (61, 120, "61-120"),
        (121, 999, "121+")
    ]

    # Track wins by category and recency bin
    category_bin_wins = {
        'hot': defaultdict(int),
        'medium': defaultdict(int),
        'cold': defaultdict(int)
    }

    # Track total wins per category for percentage calculation
    category_totals = {
        'hot': 0,
        'medium': 0,
        'cold': 0
    }

    # Combined (category-agnostic) tracking
    combined_bin_wins = defaultdict(int)
    combined_total = 0

    # Process all draws
    for draw_date, draw_data in draw_history.items():
        winning_numbers_details = draw_data.get('winning_numbers_details', [])

        for num_detail in winning_numbers_details:
            # Skip bonus numbers - we're only analyzing main numbers
            if num_detail.get('is_bonus', False):
                continue

            category = num_detail.get('category', 'medium')
            days_since = num_detail.get('days_since_last_hit', 999)

            # Find matching bin
            for min_days, max_days, bin_name in bins:
                if min_days <= days_since <= max_days:
                    category_bin_wins[category][bin_name] += 1
                    category_totals[category] += 1
                    combined_bin_wins[bin_name] += 1
                    combined_total += 1
                    break

    # Calculate win rates and scores per category
    results_by_category = {}

    for category in ['hot', 'medium', 'cold']:
        category_results = {}
        total_wins = category_totals[category]

        if total_wins == 0:
            print(f"Warning: No wins found for category '{category}'")
            continue

        # Find max win rate for normalization
        max_win_rate = 0.0
        for min_days, max_days, bin_name in bins:
            wins = category_bin_wins[category][bin_name]
            win_rate = wins / total_wins if total_wins > 0 else 0.0
            if win_rate > max_win_rate:
                max_win_rate = win_rate

        # Calculate scores for each bin
        for min_days, max_days, bin_name in bins:
            wins = category_bin_wins[category][bin_name]
            win_rate = wins / total_wins if total_wins > 0 else 0.0

            # Normalize to 0-1 score (highest win rate = 1.0)
            score = win_rate / max_win_rate if max_win_rate > 0 else 0.0

            category_results[bin_name] = {
                'wins': wins,
                'win_rate': round(win_rate, 4),
                'win_percentage': round(win_rate * 100, 2),
                'score': round(score, 4)
            }

        results_by_category[category] = category_results

    # Calculate combined (category-agnostic) zones
    combined_results = {}

    # Find max win rate for normalization
    max_combined_win_rate = 0.0
    for min_days, max_days, bin_name in bins:
        wins = combined_bin_wins[bin_name]
        win_rate = wins / combined_total if combined_total > 0 else 0.0
        if win_rate > max_combined_win_rate:
            max_combined_win_rate = win_rate

    for min_days, max_days, bin_name in bins:
        wins = combined_bin_wins[bin_name]
        win_rate = wins / combined_total if combined_total > 0 else 0.0
        score = win_rate / max_combined_win_rate if max_combined_win_rate > 0 else 0.0

        combined_results[bin_name] = {
            'wins': wins,
            'win_rate': round(win_rate, 4),
            'win_percentage': round(win_rate * 100, 2),
            'score': round(score, 4)
        }

    return {
        'by_category': results_by_category,
        'combined': combined_results,
        'totals': {
            'hot': category_totals['hot'],
            'medium': category_totals['medium'],
            'cold': category_totals['cold'],
            'combined': combined_total
        },
        'bins': [bin_name for _, _, bin_name in bins]
    }


def validate_statistical_significance(
    draw_history: Dict[str, Any],
    recency_zones: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use scipy to validate that recency zone differences are statistically significant.

    Args:
        draw_history: Data from lotto_draw_history.json
        recency_zones: Calculated recency zone data

    Returns:
        Statistical validation results
    """
    # Collect recency values by category for statistical testing
    hot_recency_values = []
    medium_recency_values = []
    cold_recency_values = []

    for draw_date, draw_data in draw_history.items():
        winning_numbers_details = draw_data.get('winning_numbers_details', [])

        for num_detail in winning_numbers_details:
            if num_detail.get('is_bonus', False):
                continue

            category = num_detail.get('category', 'medium')
            days_since = num_detail.get('days_since_last_hit', 999)

            if category == 'hot':
                hot_recency_values.append(days_since)
            elif category == 'medium':
                medium_recency_values.append(days_since)
            elif category == 'cold':
                cold_recency_values.append(days_since)

    # Calculate basic statistics
    def calc_stats(values):
        if not values:
            return {'mean': 0, 'median': 0, 'std': 0}
        return {
            'mean': round(sum(values) / len(values), 2),
            'median': round(sorted(values)[len(values) // 2], 2),
            'std': round((sum((x - sum(values)/len(values))**2 for x in values) / len(values))**0.5, 2)
        }

    hot_stats = calc_stats(hot_recency_values)
    medium_stats = calc_stats(medium_recency_values)
    cold_stats = calc_stats(cold_recency_values)

    # Perform statistical tests if scipy available
    if HAS_SCIPY and len(hot_recency_values) >= 10 and len(medium_recency_values) >= 10 and len(cold_recency_values) >= 10:
        # Kruskal-Wallis H-test (non-parametric version of ANOVA)
        # Good for non-normal distributions
        h_statistic, p_value = stats.kruskal(hot_recency_values, medium_recency_values, cold_recency_values)

        # Also perform pairwise comparisons
        hot_vs_medium_u, hot_vs_medium_p = stats.mannwhitneyu(hot_recency_values, medium_recency_values, alternative='two-sided')
        hot_vs_cold_u, hot_vs_cold_p = stats.mannwhitneyu(hot_recency_values, cold_recency_values, alternative='two-sided')
        medium_vs_cold_u, medium_vs_cold_p = stats.mannwhitneyu(medium_recency_values, cold_recency_values, alternative='two-sided')

        return {
            'test': 'Kruskal-Wallis H-test',
            'h_statistic': float(h_statistic),
            'p_value': float(p_value),
            'significant': bool(p_value < 0.05),
            'interpretation': f"Category recency distributions are {'significantly' if p_value < 0.05 else 'not significantly'} different (p={p_value:.4f})",
            'category_stats': {
                'hot': {**hot_stats, 'n': len(hot_recency_values)},
                'medium': {**medium_stats, 'n': len(medium_recency_values)},
                'cold': {**cold_stats, 'n': len(cold_recency_values)}
            },
            'pairwise_comparisons': {
                'hot_vs_medium': {
                    'u_statistic': float(hot_vs_medium_u),
                    'p_value': float(hot_vs_medium_p),
                    'significant': bool(hot_vs_medium_p < 0.05)
                },
                'hot_vs_cold': {
                    'u_statistic': float(hot_vs_cold_u),
                    'p_value': float(hot_vs_cold_p),
                    'significant': bool(hot_vs_cold_p < 0.05)
                },
                'medium_vs_cold': {
                    'u_statistic': float(medium_vs_cold_u),
                    'p_value': float(medium_vs_cold_p),
                    'significant': bool(medium_vs_cold_p < 0.05)
                }
            }
        }
    else:
        # Basic validation without scipy
        return {
            'test': 'Basic comparison',
            'method': 'mean_differences',
            'category_stats': {
                'hot': {**hot_stats, 'n': len(hot_recency_values)},
                'medium': {**medium_stats, 'n': len(medium_recency_values)},
                'cold': {**cold_stats, 'n': len(cold_recency_values)}
            },
            'significant': bool(hot_stats['mean'] < medium_stats['mean'] < cold_stats['mean']),
            'interpretation': f"Hot numbers have shorter recency (mean={hot_stats['mean']}d) than cold (mean={cold_stats['mean']}d)"
        }


def compare_with_hardcoded_values(recency_zones: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare calculated scores with the current hard-coded values.

    Args:
        recency_zones: Calculated recency zone data

    Returns:
        Comparison results
    """
    # Current hard-coded scores from timing.py
    hardcoded_scores = {
        "0-14": 1.0,
        "15-30": 0.78,
        "31-60": 0.54,
        "61-120": 0.18,
        "121+": 0.01
    }

    combined = recency_zones['combined']

    comparison = {}
    for bin_name, data in combined.items():
        calculated_score = data['score']
        hardcoded_score = hardcoded_scores.get(bin_name, 0.0)

        # Calculate difference
        difference = calculated_score - hardcoded_score
        percent_diff = (difference / hardcoded_score * 100) if hardcoded_score > 0 else 0

        comparison[bin_name] = {
            'calculated_score': round(calculated_score, 4),
            'hardcoded_score': hardcoded_score,
            'difference': round(difference, 4),
            'percent_difference': round(percent_diff, 2),
            'alignment': 'good' if abs(difference) < 0.1 else 'needs_adjustment'
        }

    return comparison


def generate_recency_zones_data(draw_history_file: str, output_file: str):
    """
    Main function: Generate data-driven recency zone configuration.

    Args:
        draw_history_file: Path to lotto_draw_history.json
        output_file: Path to output JSON file
    """
    print("\n" + "=" * 70)
    print("  RECENCY ZONE ANALYZER - DATA-DRIVEN EDITION")
    print("=" * 70)

    # Load draw history
    print("\nLoading Draw History...")
    with open(draw_history_file, 'r') as f:
        draw_history = json.load(f)
    print(f"  Loaded {len(draw_history)} draws from {draw_history_file}")

    # Analyze recency zones
    print("\nAnalyzing Recency Zones from Real Data...")
    recency_zones = analyze_recency_zones(draw_history)

    print("\n  Combined (Category-Agnostic) Zones:")
    for bin_name, data in recency_zones['combined'].items():
        print(f"    {bin_name} days: {data['win_percentage']}% of wins → score {data['score']:.4f}")

    print("\n  By Category:")
    for category in ['hot', 'medium', 'cold']:
        if category in recency_zones['by_category']:
            print(f"\n    {category.upper()}:")
            for bin_name, data in recency_zones['by_category'][category].items():
                print(f"      {bin_name} days: {data['win_percentage']}% → score {data['score']:.4f}")

    # Statistical validation
    print("\nStatistical Validation...")
    validation = validate_statistical_significance(draw_history, recency_zones)
    print(f"  Test: {validation['test']}")
    if 'h_statistic' in validation:
        print(f"  H-statistic: {validation['h_statistic']:.4f}")
        print(f"  P-value: {validation['p_value']:.6f}")
    print(f"  Significant: {validation['significant']}")
    print(f"  {validation['interpretation']}")

    if 'category_stats' in validation:
        print("\n  Category Recency Statistics:")
        for cat, stats in validation['category_stats'].items():
            print(f"    {cat.upper()}: mean={stats['mean']}d, median={stats['median']}d, std={stats['std']}d (n={stats['n']})")

    # Compare with hard-coded values
    print("\nComparing with Hard-Coded Values...")
    comparison = compare_with_hardcoded_values(recency_zones)

    print("\n  Bin         | Calculated | Hard-Coded | Difference | Status")
    print("  " + "-" * 65)
    for bin_name, comp in comparison.items():
        status_symbol = "" if comp['alignment'] == 'good' else ""
        print(f"  {bin_name:11} | {comp['calculated_score']:10.4f} | {comp['hardcoded_score']:10.2f} | "
              f"{comp['difference']:+10.4f} | {status_symbol} {comp['alignment']}")

    # Build final output
    output_data = {
        'metadata': {
            'analysis_type': 'recency_zone_optimization',
            'description': 'Data-driven recency zone scoring to replace hard-coded thresholds',
            'version': '1.0',
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_draws': len(draw_history),
            'calculation_method': 'empirical_win_rate',
            'bins': recency_zones['bins'],
            'data_source': draw_history_file
        },
        'recency_zones_by_category': recency_zones['by_category'],
        'recency_zones_combined': recency_zones['combined'],
        'totals': recency_zones['totals'],
        'statistical_validation': validation,
        'comparison_with_hardcoded': comparison,
        'usage_notes': {
            'category_aware': 'Use recency_zones_by_category for category-specific scoring',
            'category_agnostic': 'Use recency_zones_combined for simplified scoring',
            'fallback': 'System will fallback to hard-coded values if JSON not available',
            'score_interpretation': 'Scores are normalized 0-1, where 1.0 = highest win rate'
        }
    }

    # Save
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(round_floats(output_data), f, indent=2)

    print(f"  Saved {output_file}")
    print("\n" + "=" * 70)
    print("DATA-DRIVEN ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nAll recency zone scores calculated from {recency_zones['totals']['combined']} winning numbers.")
    print(f"Statistical significance: {validation['significant']}")
    print("\nNext steps:")
    print("  1. Review the generated JSON file")
    print("  2. Update ml_lotto/features/timing.py to load from this JSON")
    print("  3. Test the updated implementation")
    print()


if __name__ == '__main__':
    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    draw_history_file = project_root / 'data' / 'lotto_draw_history.json'
    output_file = project_root / 'data' / 'lotto_recency_zones_calculated.json'

    generate_recency_zones_data(str(draw_history_file), str(output_file))
