#!/usr/bin/env python3
"""
Range Spread Analyzer - Statistical Validation Edition
========================================================

Uses scipy to validate range spread patterns with statistical rigor.

Statistical Methods:
- F-test (Levene's test) for variance equality
- Independent samples t-test for range contribution
- Correlation analysis for number position effects
- Cohen's d for effect size

Range spread measures how spread out the numbers are in a draw (max - min).

Author: Statistical Analysis Module
Version: 1.0 (Scipy Edition)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
from scipy import stats
import numpy as np


def calculate_draw_ranges(draw_history: List[Dict[str, Any]]) -> List[int]:
    """
    Calculate the range (max - min) of numbers in each draw.

    Args:
        draw_history: List of historical draws

    Returns:
        List of draw ranges
    """
    ranges = []
    for draw in draw_history:
        numbers = draw.get('numbers', [])
        # Exclude bonus number
        numbers = [n for n in numbers if isinstance(n, int)]
        if len(numbers) >= 2:
            draw_range = max(numbers) - min(numbers)
            ranges.append(draw_range)
    return ranges


def analyze_overall_range_distribution(draw_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze overall range distribution using descriptive stats and normality test.

    Args:
        draw_history: List of historical draws

    Returns:
        Dictionary with range distribution analysis
    """
    draw_ranges = calculate_draw_ranges(draw_history)

    if len(draw_ranges) < 3:
        return {
            'error': 'Insufficient data',
            'mean': 0.0,
            'std': 0.0
        }

    # Descriptive statistics
    mean_range = np.mean(draw_ranges)
    median_range = np.median(draw_ranges)
    std_range = np.std(draw_ranges, ddof=1)
    min_range = np.min(draw_ranges)
    max_range = np.max(draw_ranges)

    # Shapiro-Wilk test for normality
    if len(draw_ranges) >= 3:
        shapiro_stat, shapiro_p = stats.shapiro(draw_ranges)
    else:
        shapiro_stat, shapiro_p = 0.0, 1.0

    return {
        'mean': float(mean_range),
        'median': float(median_range),
        'std': float(std_range),
        'min': int(min_range),
        'max': int(max_range),
        'range_of_ranges': int(max_range - min_range),
        'normality_test': {
            'shapiro_statistic': float(shapiro_stat),
            'p_value': float(shapiro_p),
            'is_normal': bool(shapiro_p > 0.05)
        }
    }


def calculate_per_number_range_contribution(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[int, Dict[str, Any]]:
    """
    Calculate range contribution scores with t-test validation.

    For each number, tests whether draws containing that number have
    significantly different ranges than draws without it.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary mapping number to range contribution analysis
    """
    # Calculate overall statistics first
    overall_stats = analyze_overall_range_distribution(draw_history)
    overall_mean = overall_stats['mean']

    contribution_results = {}

    for num in range(1, max_number + 1):
        # Separate draws with and without this number
        ranges_with = []
        ranges_without = []

        for draw in draw_history:
            numbers = draw.get('numbers', [])
            numbers = [n for n in numbers if isinstance(n, int)]

            if len(numbers) < 2:
                continue

            draw_range = max(numbers) - min(numbers)

            if num in numbers:
                ranges_with.append(draw_range)
            else:
                ranges_without.append(draw_range)

        # Need minimum sample sizes for t-test
        if len(ranges_with) < 5 or len(ranges_without) < 5:
            contribution_results[num] = {
                'contribution_score': 0.5,
                'statistically_validated': False,
                'p_value': 1.0,
                'mean_with': 0.0,
                'mean_without': 0.0
            }
            continue

        # Independent samples t-test
        # H0: Mean range with number = mean range without number
        t_stat, p_value = stats.ttest_ind(ranges_with, ranges_without)

        mean_with = np.mean(ranges_with)
        mean_without = np.mean(ranges_without)

        # Calculate Cohen's d (effect size)
        pooled_std = np.sqrt(
            ((len(ranges_with) - 1) * np.var(ranges_with, ddof=1) +
             (len(ranges_without) - 1) * np.var(ranges_without, ddof=1)) /
            (len(ranges_with) + len(ranges_without) - 2)
        )

        cohens_d = (mean_with - mean_without) / pooled_std if pooled_std > 0 else 0.0

        # Normalize contribution score to 0-1 range
        # Higher mean with number = higher range contribution (more spread)
        contribution_score = (mean_with - overall_mean) / (overall_stats['std'] * 2) + 0.5
        contribution_score = max(0.0, min(1.0, contribution_score))

        contribution_results[num] = {
            'contribution_score': float(contribution_score),
            'statistically_validated': bool(p_value < 0.05),
            'p_value': float(p_value),
            't_statistic': float(t_stat),
            'cohens_d': float(cohens_d),
            'mean_with': float(mean_with),
            'mean_without': float(mean_without),
            'mean_difference': float(mean_with - mean_without),
            'appearances': len(ranges_with),
            'effect_size': _interpret_cohens_d(cohens_d)
        }

    return contribution_results


def perform_position_variance_analysis(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[str, Any]:
    """
    Perform Levene's test to check if variance differs by number position.

    Groups numbers into low/mid/high positions and tests if they produce
    different range variance.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary with Levene's test results
    """
    # Group numbers into position ranges
    position_groups = {
        'low': list(range(1, 16)),     # 1-15
        'mid': list(range(16, 33)),    # 16-32
        'high': list(range(33, max_number + 1))  # 33-47
    }

    # Collect ranges for draws dominated by each position group
    position_ranges = defaultdict(list)

    for draw in draw_history:
        numbers = draw.get('numbers', [])
        numbers = [n for n in numbers if isinstance(n, int)]

        if len(numbers) < 2:
            continue

        draw_range = max(numbers) - min(numbers)

        # Categorize this draw by which position group has most numbers
        position_counts = {
            'low': sum(1 for n in numbers if n in position_groups['low']),
            'mid': sum(1 for n in numbers if n in position_groups['mid']),
            'high': sum(1 for n in numbers if n in position_groups['high'])
        }

        dominant_position = max(position_counts, key=position_counts.get)
        position_ranges[dominant_position].append(draw_range)

    # Perform Levene's test for equality of variances
    if all(len(ranges) >= 2 for ranges in position_ranges.values()):
        # Levene's test (more robust than Bartlett's for non-normal data)
        levene_stat, p_value = stats.levene(
            position_ranges['low'],
            position_ranges['mid'],
            position_ranges['high']
        )

        # Calculate variance for each group
        variances = {
            'low': float(np.var(position_ranges['low'], ddof=1)),
            'mid': float(np.var(position_ranges['mid'], ddof=1)),
            'high': float(np.var(position_ranges['high'], ddof=1))
        }

        means = {
            'low': float(np.mean(position_ranges['low'])),
            'mid': float(np.mean(position_ranges['mid'])),
            'high': float(np.mean(position_ranges['high']))
        }

        return {
            'significant': bool(p_value < 0.05),
            'levene_statistic': float(levene_stat),
            'p_value': float(p_value),
            'position_variances': variances,
            'position_means': means,
            'interpretation': _interpret_levene(p_value)
        }
    else:
        return {
            'significant': False,
            'levene_statistic': 0.0,
            'p_value': 1.0,
            'error': 'Insufficient data for Levene test'
        }


def calculate_correlation_with_position(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[str, Any]:
    """
    Calculate correlation between number value and range contribution.

    Tests whether extreme numbers (low/high) contribute more to spread.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary with correlation analysis
    """
    # For each draw, calculate correlation between number values and their contribution to range
    correlations = []

    for draw in draw_history:
        numbers = draw.get('numbers', [])
        numbers = sorted([n for n in numbers if isinstance(n, int)])

        if len(numbers) < 3:
            continue

        # Calculate each number's distance from median
        median_num = np.median(numbers)
        distances = [abs(n - median_num) for n in numbers]

        # Correlate number value with distance from median
        if len(numbers) >= 3:
            corr, _ = stats.pearsonr(numbers, distances)
            correlations.append(corr)

    if len(correlations) >= 3:
        mean_corr = np.mean(correlations)

        # One-sample t-test: is correlation significantly different from 0?
        t_stat, p_value = stats.ttest_1samp(correlations, 0.0)

        return {
            'mean_correlation': float(mean_corr),
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'significant': bool(p_value < 0.05),
            'interpretation': _interpret_correlation(mean_corr, p_value)
        }
    else:
        return {
            'mean_correlation': 0.0,
            't_statistic': 0.0,
            'p_value': 1.0,
            'significant': False,
            'error': 'Insufficient data'
        }


def _interpret_cohens_d(d: float) -> str:
    """Interpret Cohen's d effect size."""
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"


def _interpret_levene(p_value: float) -> str:
    """Interpret Levene's test results."""
    if p_value >= 0.05:
        return "Variances are equal across position groups (homoscedastic)"
    else:
        return "Variances differ significantly across position groups (heteroscedastic)"


def _interpret_correlation(corr: float, p_value: float) -> str:
    """Interpret correlation results."""
    if p_value >= 0.05:
        return "No significant correlation between number value and spread contribution"
    elif corr > 0:
        return "Extreme numbers (low/high) significantly contribute more to spread"
    else:
        return "Middle numbers significantly contribute more to spread"


def analyze_range_spread(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[str, Any]:
    """
    Main analysis function - validates range spread with scipy.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary with scipy-validated analysis results
    """
    print("  Analyzing overall range distribution...")
    overall_stats = analyze_overall_range_distribution(draw_history)

    print("  Calculating per-number range contribution with t-tests...")
    per_number_contribution = calculate_per_number_range_contribution(draw_history, max_number)

    print("  Performing Levene's test on position variance...")
    levene_results = perform_position_variance_analysis(draw_history, max_number)

    print("  Calculating correlation with number position...")
    correlation_results = calculate_correlation_with_position(draw_history, max_number)

    # Extract validated scores
    validated_scores = {
        num: data['contribution_score']
        for num, data in per_number_contribution.items()
    }

    # Count significant contributions
    num_significant = sum(
        1 for data in per_number_contribution.values()
        if data['statistically_validated']
    )

    return {
        'metadata': {
            'analysis_type': 'range_spread_validation',
            'statistical_methods': [
                'independent_t_test',
                'levene_variance_test',
                'pearson_correlation',
                'cohens_d_effect_size'
            ],
            'total_draws': len(draw_history),
            'significance_level': 0.05
        },
        'overall_distribution': overall_stats,
        'per_number_contribution': per_number_contribution,
        'levene_analysis': levene_results,
        'correlation_analysis': correlation_results,
        'validated_scores': validated_scores,
        'num_significant_contributions': num_significant
    }


def main():
    """Main execution - load data and generate scipy-validated analysis."""
    print("=" * 70)
    print("RANGE SPREAD ANALYZER (Statistical Edition)")
    print("=" * 70)
    print()

    # Load draw history
    draw_history_file = 'data/lotto_draw_history.json'

    if not Path(draw_history_file).exists():
        print(f"❌ ERROR: {draw_history_file} not found")
        print(f"   REQUIRED ACTION: Run 'python drawpick.py' first")
        sys.exit(1)

    try:
        with open(draw_history_file, 'r') as f:
            data = json.load(f)

        # Extract draws from the JSON structure
        draw_list = []
        for draw_date, draw_data in data.items():
            winning_numbers = []
            for detail in draw_data.get('winning_numbers_details', []):
                num = detail.get('number')
                is_bonus = detail.get('is_bonus', False)
                if num and not is_bonus:  # Exclude bonus
                    winning_numbers.append(num)

            if winning_numbers:
                draw_list.append({
                    'date': draw_date,
                    'numbers': winning_numbers
                })

        draw_list.sort(key=lambda x: x['date'])

    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in {draw_history_file}: {e}")
        sys.exit(1)

    print(f"Loaded {len(draw_list)} draws")
    print("Analyzing range spread with statistical rigor...")
    results = analyze_range_spread(draw_list)

    # Display results
    print()
    print("  ✓ Range spread validation complete:")

    overall = results.get('overall_distribution', {})
    print(f"    - Mean range: {overall.get('mean', 0):.1f}")
    print(f"    - Std deviation: {overall.get('std', 0):.1f}")
    print(f"    - Range: {overall.get('min', 0)} to {overall.get('max', 0)}")

    levene = results.get('levene_analysis', {})
    print(f"\n    - Levene's test (variance equality):")
    print(f"      Levene statistic: {levene.get('levene_statistic', 0):.4f}")
    print(f"      P-value: {levene.get('p_value', 1.0):.6f}")
    print(f"      Significant: {levene.get('significant', False)}")

    corr = results.get('correlation_analysis', {})
    print(f"\n    - Correlation analysis:")
    print(f"      Mean correlation: {corr.get('mean_correlation', 0):.4f}")
    print(f"      P-value: {corr.get('p_value', 1.0):.6f}")
    print(f"      Significant: {corr.get('significant', False)}")

    print(f"\n    - Per-number contributions:")
    print(f"      Significant deviations: {results.get('num_significant_contributions', 0)}/47")

    # Save results
    output_file = 'data/lotto_range_spread_validated.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Analysis saved to {output_file}")
    print()
    print("=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
