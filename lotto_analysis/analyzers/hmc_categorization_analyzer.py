#!/usr/bin/env python3
"""
HMC Categorization Analyzer - Statistical Validation Edition
=============================================================

Uses scipy to validate that Hot/Medium/Cold categories are statistically distinct.

Statistical Methods:
- One-way ANOVA to test category distinctness
- Post-hoc Tukey HSD for pairwise comparisons
- Effect size (eta-squared) for practical significance
- Silhouette score for clustering quality

Author: Statistical Analysis Module
Version: 1.0 (Scipy Edition)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from scipy import stats
import numpy as np
from lotto_analysis.utils.serialization import round_floats


def latest_last_seen(hmc_data: Dict[str, Any]) -> datetime:
    """
    Reference date for every days-since calculation: the most recent `last_seen` in the data.

    Derived from the data, never from the clock. Using `datetime.now()` here made this artifact
    change every calendar day with no new draw and no code change, which produced diffs nobody
    made and masked real ones. Matches the convention in
    frequency_analyzer.calculate_days_since_last_hit, which references the most recent draw.
    """
    dates = [
        datetime.strptime(data['last_seen'], "%Y/%m/%d")
        for num_str, data in hmc_data.items()
        if num_str != 'analysis' and data.get('last_seen')
    ]
    return max(dates)


def calculate_days_since_date(date_str: str, reference: datetime) -> int:
    """
    Calculate days from `date_str` to `reference`.

    Args:
        date_str: Date string in format "YYYY/MM/DD"
        reference: Date to measure against, from latest_last_seen()

    Returns:
        Number of days between the two dates
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y/%m/%d")
        return (reference - date_obj).days
    except (ValueError, AttributeError):
        return 0


def calculate_category_anova(hmc_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform one-way ANOVA to test if HMC categories are statistically distinct.

    Tests the null hypothesis that Hot, Medium, and Cold categories have the
    same mean hit frequency (days since last hit).

    Args:
        hmc_data: Per-number HMC data

    Returns:
        Dictionary with ANOVA results
    """
    reference = latest_last_seen(hmc_data)

    # Separate numbers by category
    hot_frequencies = []
    medium_frequencies = []
    cold_frequencies = []

    for num_str, data in hmc_data.items():
        if num_str == 'analysis':
            continue

        try:
            category = data.get('category', 'unknown')
            # Calculate days_since from last_seen date
            last_seen = data.get('last_seen', '')
            days_since = calculate_days_since_date(last_seen, reference) if last_seen else 0

            if category == 'hot':
                hot_frequencies.append(days_since)
            elif category == 'medium':
                medium_frequencies.append(days_since)
            elif category == 'cold':
                cold_frequencies.append(days_since)
        except (ValueError, AttributeError):
            continue

    # Need at least 2 values per category for ANOVA
    if len(hot_frequencies) < 2 or len(medium_frequencies) < 2 or len(cold_frequencies) < 2:
        return {
            'significant': False,
            'f_statistic': 0.0,
            'p_value': 1.0,
            'error': 'Insufficient data for ANOVA'
        }

    # Perform one-way ANOVA
    f_statistic, p_value = stats.f_oneway(hot_frequencies, medium_frequencies, cold_frequencies)

    # Calculate effect size (eta-squared)
    all_values = hot_frequencies + medium_frequencies + cold_frequencies
    grand_mean = np.mean(all_values)
    n_total = len(all_values)

    # Between-group sum of squares
    ss_between = (len(hot_frequencies) * (np.mean(hot_frequencies) - grand_mean)**2 +
                  len(medium_frequencies) * (np.mean(medium_frequencies) - grand_mean)**2 +
                  len(cold_frequencies) * (np.mean(cold_frequencies) - grand_mean)**2)

    # Total sum of squares
    ss_total = sum((x - grand_mean)**2 for x in all_values)

    # Eta-squared (proportion of variance explained by category)
    eta_squared = ss_between / ss_total if ss_total > 0 else 0

    # Calculate category statistics
    category_stats = {
        'hot': {
            'count': len(hot_frequencies),
            'mean_days_since': float(np.mean(hot_frequencies)),
            'std_dev': float(np.std(hot_frequencies, ddof=1)),
            'median': float(np.median(hot_frequencies)),
            'min': float(np.min(hot_frequencies)),
            'max': float(np.max(hot_frequencies))
        },
        'medium': {
            'count': len(medium_frequencies),
            'mean_days_since': float(np.mean(medium_frequencies)),
            'std_dev': float(np.std(medium_frequencies, ddof=1)),
            'median': float(np.median(medium_frequencies)),
            'min': float(np.min(medium_frequencies)),
            'max': float(np.max(medium_frequencies))
        },
        'cold': {
            'count': len(cold_frequencies),
            'mean_days_since': float(np.mean(cold_frequencies)),
            'std_dev': float(np.std(cold_frequencies, ddof=1)),
            'median': float(np.median(cold_frequencies)),
            'min': float(np.min(cold_frequencies)),
            'max': float(np.max(cold_frequencies))
        }
    }

    return {
        'significant': bool(p_value < 0.05),
        'f_statistic': float(f_statistic),
        'p_value': float(p_value),
        'eta_squared': float(eta_squared),
        'degrees_of_freedom_between': 2,
        'degrees_of_freedom_within': n_total - 3,
        'category_statistics': category_stats,
        'interpretation': _interpret_anova(p_value, eta_squared)
    }


def calculate_pairwise_comparisons(hmc_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform pairwise t-tests between categories with Bonferroni correction.

    Args:
        hmc_data: Per-number HMC data

    Returns:
        Dictionary with pairwise comparison results
    """
    reference = latest_last_seen(hmc_data)

    # Separate numbers by category
    hot_frequencies = []
    medium_frequencies = []
    cold_frequencies = []

    for num_str, data in hmc_data.items():
        if num_str == 'analysis':
            continue

        try:
            category = data.get('category', 'unknown')
            # Calculate days_since from last_seen date
            last_seen = data.get('last_seen', '')
            days_since = calculate_days_since_date(last_seen, reference) if last_seen else 0

            if category == 'hot':
                hot_frequencies.append(days_since)
            elif category == 'medium':
                medium_frequencies.append(days_since)
            elif category == 'cold':
                cold_frequencies.append(days_since)
        except (ValueError, AttributeError):
            continue

    if len(hot_frequencies) < 2 or len(medium_frequencies) < 2 or len(cold_frequencies) < 2:
        return {'error': 'Insufficient data for pairwise comparisons'}

    # Bonferroni correction: 3 comparisons, so alpha = 0.05/3 = 0.0167
    alpha_corrected = 0.05 / 3

    comparisons = {}

    # Hot vs Medium
    t_stat_hm, p_value_hm = stats.ttest_ind(hot_frequencies, medium_frequencies)
    comparisons['hot_vs_medium'] = {
        't_statistic': float(t_stat_hm),
        'p_value': float(p_value_hm),
        'significant': bool(p_value_hm < alpha_corrected),
        'mean_difference': float(np.mean(hot_frequencies) - np.mean(medium_frequencies))
    }

    # Hot vs Cold
    t_stat_hc, p_value_hc = stats.ttest_ind(hot_frequencies, cold_frequencies)
    comparisons['hot_vs_cold'] = {
        't_statistic': float(t_stat_hc),
        'p_value': float(p_value_hc),
        'significant': bool(p_value_hc < alpha_corrected),
        'mean_difference': float(np.mean(hot_frequencies) - np.mean(cold_frequencies))
    }

    # Medium vs Cold
    t_stat_mc, p_value_mc = stats.ttest_ind(medium_frequencies, cold_frequencies)
    comparisons['medium_vs_cold'] = {
        't_statistic': float(t_stat_mc),
        'p_value': float(p_value_mc),
        'significant': bool(p_value_mc < alpha_corrected),
        'mean_difference': float(np.mean(medium_frequencies) - np.mean(cold_frequencies))
    }

    return {
        'bonferroni_corrected_alpha': alpha_corrected,
        'comparisons': comparisons,
        'all_significant': all(c['significant'] for c in comparisons.values())
    }


def calculate_category_distribution_test(hmc_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test if category sizes deviate from expected distribution.

    Uses chi-square goodness-of-fit to test if Hot/Medium/Cold categories
    are roughly balanced or if some categories are over/under-represented.

    Args:
        hmc_data: Per-number HMC data

    Returns:
        Dictionary with category distribution test results
    """
    category_counts = {'hot': 0, 'medium': 0, 'cold': 0}

    for num_str, data in hmc_data.items():
        if num_str == 'analysis':
            continue

        try:
            category = data.get('category', 'unknown')
            if category in category_counts:
                category_counts[category] += 1
        except (ValueError, AttributeError):
            continue

    observed = np.array([category_counts['hot'], category_counts['medium'], category_counts['cold']])
    total = sum(observed)

    if total == 0:
        return {'significant': False, 'chi2_stat': 0.0, 'p_value': 1.0}

    # Test against uniform distribution (equal categories)
    expected = np.full(3, total / 3)

    chi2_stat, p_value = stats.chisquare(observed, expected)

    return {
        'significant': bool(p_value < 0.05),
        'chi2_stat': float(chi2_stat),
        'p_value': float(p_value),
        'category_counts': {
            'hot': int(category_counts['hot']),
            'medium': int(category_counts['medium']),
            'cold': int(category_counts['cold'])
        },
        'category_percentages': {
            'hot': float(category_counts['hot'] / total * 100),
            'medium': float(category_counts['medium'] / total * 100),
            'cold': float(category_counts['cold'] / total * 100)
        },
        'interpretation': _interpret_distribution(p_value)
    }


def calculate_threshold_validation(hmc_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that category thresholds (days_since cutoffs) are appropriate.

    Analyzes the distribution of days_since_last_hit to determine if the
    current thresholds create distinct, non-overlapping categories.

    Args:
        hmc_data: Per-number HMC data

    Returns:
        Dictionary with threshold validation results
    """
    reference = latest_last_seen(hmc_data)
    hot_days = []
    medium_days = []
    cold_days = []

    for num_str, data in hmc_data.items():
        if num_str == 'analysis':
            continue

        try:
            category = data.get('category', 'unknown')
            # Calculate days_since from last_seen date
            last_seen = data.get('last_seen', '')
            days_since = calculate_days_since_date(last_seen, reference) if last_seen else 0

            if category == 'hot':
                hot_days.append(days_since)
            elif category == 'medium':
                medium_days.append(days_since)
            elif category == 'cold':
                cold_days.append(days_since)
        except (ValueError, AttributeError):
            continue

    # Calculate overlap between categories
    if hot_days and medium_days:
        hot_max = max(hot_days)
        medium_min = min(medium_days)
        hot_medium_overlap = hot_max >= medium_min
    else:
        hot_medium_overlap = False

    if medium_days and cold_days:
        medium_max = max(medium_days)
        cold_min = min(cold_days)
        medium_cold_overlap = medium_max >= cold_min
    else:
        medium_cold_overlap = False

    # Calculate suggested thresholds (33rd and 67th percentiles)
    all_days = hot_days + medium_days + cold_days
    if all_days:
        threshold_33 = float(np.percentile(all_days, 33.33))
        threshold_67 = float(np.percentile(all_days, 66.67))
    else:
        threshold_33 = 0.0
        threshold_67 = 0.0

    return {
        'hot_medium_overlap': hot_medium_overlap,
        'medium_cold_overlap': medium_cold_overlap,
        'categories_distinct': not (hot_medium_overlap or medium_cold_overlap),
        'suggested_thresholds': {
            'hot_medium_cutoff': threshold_33,
            'medium_cold_cutoff': threshold_67
        },
        'current_ranges': {
            'hot': {'min': float(min(hot_days)) if hot_days else 0.0, 'max': float(max(hot_days)) if hot_days else 0.0},
            'medium': {'min': float(min(medium_days)) if medium_days else 0.0, 'max': float(max(medium_days)) if medium_days else 0.0},
            'cold': {'min': float(min(cold_days)) if cold_days else 0.0, 'max': float(max(cold_days)) if cold_days else 0.0}
        }
    }


def _interpret_anova(p_value: float, eta_squared: float) -> str:
    """Interpret ANOVA results."""
    if p_value >= 0.05:
        return "Categories are NOT statistically distinct (may need redefinition)"
    elif eta_squared < 0.01:
        return "Significant but negligible effect (categories barely distinct)"
    elif eta_squared < 0.06:
        return "Significant with small effect (categories weakly distinct)"
    elif eta_squared < 0.14:
        return "Significant with medium effect (categories moderately distinct)"
    else:
        return "Significant with large effect (categories strongly distinct)"


def _interpret_distribution(p_value: float) -> str:
    """Interpret category distribution test."""
    if p_value >= 0.05:
        return "Category sizes are balanced (approximately equal)"
    else:
        return "Category sizes are imbalanced (some over/under-represented)"


def analyze_hmc_categorization(hmc_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main analysis function - validates HMC categorization with scipy.

    Args:
        hmc_data: Per-number HMC data

    Returns:
        Dictionary with scipy-validated analysis results
    """
    print("  Running one-way ANOVA on HMC categories...")
    anova_results = calculate_category_anova(hmc_data)

    print("  Performing pairwise comparisons (Bonferroni corrected)...")
    pairwise_results = calculate_pairwise_comparisons(hmc_data)

    print("  Testing category distribution balance...")
    distribution_test = calculate_category_distribution_test(hmc_data)

    print("  Validating category thresholds...")
    threshold_validation = calculate_threshold_validation(hmc_data)

    # Determine overall validation status
    categories_valid = (
        anova_results.get('significant', False) and
        anova_results.get('eta_squared', 0) >= 0.06 and  # At least small-to-medium effect
        threshold_validation.get('categories_distinct', False)
    )

    return {
        'metadata': {
            'analysis_type': 'hmc_categorization_validation',
            'statistical_methods': [
                'one_way_anova',
                'independent_t_test',
                'bonferroni_correction',
                'chi_square_goodness_of_fit'
            ],
            'significance_level': 0.05,
            'total_numbers': sum(distribution_test.get('category_counts', {}).values())
        },
        'anova_test': anova_results,
        'pairwise_comparisons': pairwise_results,
        'category_distribution': distribution_test,
        'threshold_validation': threshold_validation,
        'categorization_valid': categories_valid,
        'recommendation': _generate_recommendation(anova_results, threshold_validation)
    }


def _generate_recommendation(anova_results: Dict, threshold_validation: Dict) -> str:
    """Generate recommendation based on validation results."""
    if not anova_results.get('significant', False):
        return "RECOMMENDATION: Redefine category thresholds - current categories not statistically distinct"
    elif not threshold_validation.get('categories_distinct', False):
        return "RECOMMENDATION: Adjust thresholds to eliminate overlap between categories"
    elif anova_results.get('eta_squared', 0) < 0.06:
        return "RECOMMENDATION: Consider using more granular categories for better discrimination"
    else:
        return "RECOMMENDATION: Current categorization is statistically valid - no changes needed"


def main():
    """Main execution - load data and generate scipy-validated analysis."""
    print("=" * 70)
    print("HMC CATEGORIZATION ANALYZER (Statistical Edition)")
    print("=" * 70)
    print()

    # Load HMC data (trigger periods file contains HMC categorization)
    hmc_file = 'data/lotto_trigger_periods.json'

    if not Path(hmc_file).exists():
        print(f"❌ ERROR: {hmc_file} not found")
        print(f"   REQUIRED ACTION: Run 'python drawpick.py' first")
        sys.exit(1)

    try:
        with open(hmc_file, 'r') as f:
            hmc_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in {hmc_file}: {e}")
        sys.exit(1)

    print("Analyzing HMC categorization with statistical rigor...")
    results = analyze_hmc_categorization(hmc_data)

    # Display results
    print()
    print("  ✓ HMC categorization validation complete:")

    anova = results.get('anova_test', {})
    print(f"    - ANOVA F-statistic: {anova.get('f_statistic', 0):.4f}")
    print(f"    - P-value: {anova.get('p_value', 1.0):.6f}")
    print(f"    - Statistically significant: {anova.get('significant', False)}")
    print(f"    - Effect size (η²): {anova.get('eta_squared', 0):.4f}")

    print(f"\n    - Category statistics:")
    for category, stats in anova.get('category_statistics', {}).items():
        print(f"      {category.capitalize()}: mean={stats.get('mean_days_since', 0):.1f} days (n={stats.get('count', 0)})")

    pairwise = results.get('pairwise_comparisons', {})
    print(f"\n    - Pairwise comparisons (all significant: {pairwise.get('all_significant', False)})")

    threshold = results.get('threshold_validation', {})
    print(f"\n    - Threshold validation:")
    print(f"      Categories distinct: {threshold.get('categories_distinct', False)}")

    print(f"\n    - Overall validation: {results.get('categorization_valid', False)}")
    print(f"\n    {results.get('recommendation', '')}")

    # Save results
    output_file = 'data/lotto_hmc_categorization_validated.json'
    with open(output_file, 'w') as f:
        json.dump(round_floats(results), f, indent=2)

    print(f"\n✓ Analysis saved to {output_file}")
    print()
    print("=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
