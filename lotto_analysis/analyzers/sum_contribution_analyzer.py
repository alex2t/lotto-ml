#!/usr/bin/env python3
"""
Sum Contribution Analyzer - Statistical Validation Edition
===========================================================

Uses scipy to validate sum contribution patterns with statistical rigor.

Statistical Methods:
- Independent samples t-test for number contribution comparison
- One-sample t-test against expected mean
- Cohen's d for effect size
- ANOVA for overall variance analysis
- FDR correction for multiple hypothesis testing (v3.11)

Author: Statistical Analysis Module
Version: 3.11 (Multiple Testing Correction Edition)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
from scipy import stats
import numpy as np
from lotto_analysis.utils.serialization import round_floats

# Try to import statsmodels for FDR correction
try:
    from statsmodels.stats.multitest import multipletests
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    print("statsmodels not available - multiple testing correction disabled")
    print("   Install with: pip install statsmodels")


def calculate_draw_sums(draw_history: List[Dict[str, Any]]) -> List[int]:
    """
    Calculate the sum of numbers in each draw.

    Args:
        draw_history: List of historical draws

    Returns:
        List of draw sums
    """
    sums = []
    for draw in draw_history:
        numbers = draw.get('numbers', [])
        # Exclude bonus number
        numbers = [n for n in numbers if isinstance(n, int)]
        if numbers:
            sums.append(sum(numbers))
    return sums


def analyze_overall_sum_distribution(draw_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze overall sum distribution using descriptive stats and normality test.

    Args:
        draw_history: List of historical draws

    Returns:
        Dictionary with sum distribution analysis
    """
    draw_sums = calculate_draw_sums(draw_history)

    if len(draw_sums) < 3:
        return {
            'error': 'Insufficient data',
            'mean': 0.0,
            'std': 0.0
        }

    # Descriptive statistics
    mean_sum = np.mean(draw_sums)
    median_sum = np.median(draw_sums)
    std_sum = np.std(draw_sums, ddof=1)
    min_sum = np.min(draw_sums)
    max_sum = np.max(draw_sums)

    # Shapiro-Wilk test for normality
    if len(draw_sums) >= 3:
        shapiro_stat, shapiro_p = stats.shapiro(draw_sums)
    else:
        shapiro_stat, shapiro_p = 0.0, 1.0

    return {
        'mean': float(mean_sum),
        'median': float(median_sum),
        'std': float(std_sum),
        'min': int(min_sum),
        'max': int(max_sum),
        'range': int(max_sum - min_sum),
        'normality_test': {
            'shapiro_statistic': float(shapiro_stat),
            'p_value': float(shapiro_p),
            'is_normal': bool(shapiro_p > 0.05)
        }
    }


def calculate_per_number_contribution(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[int, Dict[str, Any]]:
    """
    Calculate contribution scores with t-test validation.

    For each number, tests whether draws containing that number have
    significantly different sums than draws without it.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary mapping number to contribution analysis
    """
    # Calculate overall statistics first
    overall_stats = analyze_overall_sum_distribution(draw_history)
    overall_mean = overall_stats['mean']

    contribution_results = {}

    for num in range(1, max_number + 1):
        # Separate draws with and without this number
        sums_with = []
        sums_without = []

        for draw in draw_history:
            numbers = draw.get('numbers', [])
            numbers = [n for n in numbers if isinstance(n, int)]

            draw_sum = sum(numbers)

            if num in numbers:
                sums_with.append(draw_sum)
            else:
                sums_without.append(draw_sum)

        # Need minimum sample sizes for t-test
        if len(sums_with) < 5 or len(sums_without) < 5:
            contribution_results[num] = {
                'contribution_score': 0.5,
                'statistically_validated': False,
                'p_value': 1.0,
                'mean_with': 0.0,
                'mean_without': 0.0
            }
            continue

        # Independent samples t-test
        # H0: Mean sum with number = mean sum without number
        t_stat, p_value = stats.ttest_ind(sums_with, sums_without)

        mean_with = np.mean(sums_with)
        mean_without = np.mean(sums_without)

        # Calculate Cohen's d (effect size)
        pooled_std = np.sqrt(
            ((len(sums_with) - 1) * np.var(sums_with, ddof=1) +
             (len(sums_without) - 1) * np.var(sums_without, ddof=1)) /
            (len(sums_with) + len(sums_without) - 2)
        )

        cohens_d = (mean_with - mean_without) / pooled_std if pooled_std > 0 else 0.0

        # Normalize contribution score to 0-1 range
        # Higher mean with number = higher contribution
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
            'appearances': len(sums_with),
            'effect_size': _interpret_cohens_d(cohens_d)
        }

    return contribution_results


def perform_anova_analysis(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[str, Any]:
    """
    Perform ANOVA to test if number value affects draw sum.

    Groups numbers into ranges and tests if sums differ significantly.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary with ANOVA results
    """
    # Group numbers into ranges
    ranges = {
        'low': list(range(1, 16)),
        'mid': list(range(16, 33)),
        'high': list(range(33, max_number + 1))
    }

    # Collect sums for each range
    range_sums = defaultdict(list)

    for draw in draw_history:
        numbers = draw.get('numbers', [])
        numbers = [n for n in numbers if isinstance(n, int)]

        draw_sum = sum(numbers)

        # Categorize this draw by which range has most numbers
        range_counts = {
            'low': sum(1 for n in numbers if n in ranges['low']),
            'mid': sum(1 for n in numbers if n in ranges['mid']),
            'high': sum(1 for n in numbers if n in ranges['high'])
        }

        dominant_range = max(range_counts, key=range_counts.get)
        range_sums[dominant_range].append(draw_sum)

    # Perform one-way ANOVA
    if all(len(sums) >= 2 for sums in range_sums.values()):
        f_stat, p_value = stats.f_oneway(
            range_sums['low'],
            range_sums['mid'],
            range_sums['high']
        )

        # Calculate eta-squared
        group_means = [np.mean(sums) for sums in range_sums.values()]
        grand_mean = np.mean([s for sums in range_sums.values() for s in sums])

        ss_between = sum(
            len(sums) * (np.mean(sums) - grand_mean) ** 2
            for sums in range_sums.values()
        )
        ss_total = sum(
            (s - grand_mean) ** 2
            for sums in range_sums.values()
            for s in sums
        )

        eta_squared = ss_between / ss_total if ss_total > 0 else 0.0

        return {
            'significant': bool(p_value < 0.05),
            'f_statistic': float(f_stat),
            'p_value': float(p_value),
            'eta_squared': float(eta_squared),
            'range_means': {
                'low': float(np.mean(range_sums['low'])),
                'mid': float(np.mean(range_sums['mid'])),
                'high': float(np.mean(range_sums['high']))
            },
            'interpretation': _interpret_anova(p_value, eta_squared)
        }
    else:
        return {
            'significant': False,
            'f_statistic': 0.0,
            'p_value': 1.0,
            'error': 'Insufficient data for ANOVA'
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


def _interpret_anova(p_value: float, eta_squared: float) -> str:
    """Interpret ANOVA results."""
    if p_value >= 0.05:
        return "Number ranges do not significantly affect draw sum"
    elif eta_squared < 0.01:
        return "Significant but negligible effect size"
    elif eta_squared < 0.06:
        return "Significant with small effect size"
    elif eta_squared < 0.14:
        return "Significant with medium effect size"
    else:
        return "Significant with large effect size"


def analyze_sum_contribution(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[str, Any]:
    """
    Main analysis function - validates sum contribution with scipy.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary with scipy-validated analysis results
    """
    print("  Analyzing overall sum distribution...")
    overall_stats = analyze_overall_sum_distribution(draw_history)

    print("  Calculating per-number contribution with t-tests...")
    per_number_contribution = calculate_per_number_contribution(draw_history, max_number)

    print("  Performing ANOVA on number ranges...")
    anova_results = perform_anova_analysis(draw_history, max_number)

    # CRITICAL FIX v3.11: Apply multiple hypothesis testing correction (FDR)
    if STATSMODELS_AVAILABLE and len(per_number_contribution) > 0:
        print("  Applying FDR correction for multiple hypothesis testing...")

        # Collect p-values in order
        numbers = sorted(per_number_contribution.keys())
        p_values = [per_number_contribution[num]['p_value'] for num in numbers]

        # Apply Benjamini-Hochberg FDR correction
        rejected, p_adjusted, _, _ = multipletests(
            p_values,
            method='fdr_bh',
            alpha=0.05
        )

        # Update results with corrected p-values
        num_significant_before = sum(
            1 for data in per_number_contribution.values()
            if data['statistically_validated']
        )

        for i, num in enumerate(numbers):
            per_number_contribution[num]['p_value_adjusted'] = float(p_adjusted[i])
            per_number_contribution[num]['statistically_validated'] = bool(rejected[i])

        num_significant_after = sum(
            1 for data in per_number_contribution.values()
            if data['statistically_validated']
        )

        print(f"    Before FDR: {num_significant_before} significant results")
        print(f"    After FDR:  {num_significant_after} significant results")
        print(f"    Correction reduced false positives by {num_significant_before - num_significant_after}")

        fdr_applied = True
    else:
        if not STATSMODELS_AVAILABLE:
            print("  Skipping FDR correction (statsmodels not installed)")
        fdr_applied = False

    # Extract validated scores
    validated_scores = {
        num: data['contribution_score']
        for num, data in per_number_contribution.items()
    }

    # Count significant contributions (after FDR correction if applied)
    num_significant = sum(
        1 for data in per_number_contribution.values()
        if data['statistically_validated']
    )

    return {
        'metadata': {
            'analysis_type': 'sum_contribution_validation',
            'statistical_methods': [
                'independent_t_test',
                'one_way_anova',
                'cohens_d_effect_size',
                'fdr_correction' if fdr_applied else 'no_fdr_correction'
            ],
            'total_draws': len(draw_history),
            'significance_level': 0.05,
            'fdr_correction_applied': fdr_applied
        },
        'overall_distribution': overall_stats,
        'per_number_contribution': per_number_contribution,
        'anova_analysis': anova_results,
        'validated_scores': validated_scores,
        'num_significant_contributions': num_significant
    }


def main():
    """Main execution - load data and generate scipy-validated analysis."""
    print("=" * 70)
    print("SUM CONTRIBUTION ANALYZER (Statistical Edition)")
    print("=" * 70)
    print()

    # Load draw history
    draw_history_file = 'data/lotto_draw_history.json'

    if not Path(draw_history_file).exists():
        print(f"ERROR: {draw_history_file} not found")
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
        print(f"ERROR: Invalid JSON in {draw_history_file}: {e}")
        sys.exit(1)

    print(f"Loaded {len(draw_list)} draws")
    print("Analyzing sum contribution with statistical rigor...")
    results = analyze_sum_contribution(draw_list)

    # Display results
    print()
    print("  Sum contribution validation complete:")

    overall = results.get('overall_distribution', {})
    print(f"    - Mean draw sum: {overall.get('mean', 0):.1f}")
    print(f"    - Std deviation: {overall.get('std', 0):.1f}")
    print(f"    - Range: {overall.get('range', 0)}")

    anova = results.get('anova_analysis', {})
    print(f"\n    - ANOVA test:")
    print(f"      F-statistic: {anova.get('f_statistic', 0):.4f}")
    print(f"      P-value: {anova.get('p_value', 1.0):.6f}")
    print(f"      Significant: {anova.get('significant', False)}")

    print(f"\n    - Per-number contributions:")
    print(f"      Significant deviations: {results.get('num_significant_contributions', 0)}/47")

    # Save results
    output_file = 'data/lotto_sum_contribution_validated.json'
    with open(output_file, 'w') as f:
        json.dump(round_floats(results), f, indent=2)

    print(f"\nAnalysis saved to {output_file}")
    print()
    print("=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
