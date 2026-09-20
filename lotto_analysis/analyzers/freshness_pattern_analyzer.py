#!/usr/bin/env python3
"""
Freshness Pattern Analyzer - Statistical Validation Edition
============================================================

Uses scipy to validate freshness pattern distributions with statistical rigor.

Statistical Methods:
- Chi-square goodness-of-fit test for pattern significance
- Chi-square test for bin distribution validation
- Z-scores for individual pattern deviation

Author: Statistical Analysis Module
Version: 1.0 (Scipy Edition)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from scipy import stats
import numpy as np
from lotto_analysis.utils.serialization import round_floats


def calculate_pattern_significance(
    pattern_distributions: List[Dict[str, Any]],
    total_draws: int,
    c_max: int
) -> Dict[str, Any]:
    """
    Validate freshness pattern distributions using chi-square goodness-of-fit test.

    Tests whether observed pattern distributions deviate significantly from
    a uniform distribution (null hypothesis: all patterns equally likely).

    Args:
        pattern_distributions: List of pattern distribution dictionaries
        total_draws: Total number of draws analyzed
        c_max: Maximum recency threshold

    Returns:
        Dictionary with statistical validation results
    """
    if not pattern_distributions:
        return {
            'significant': False,
            'chi2_stat': 0.0,
            'p_value': 1.0,
            'num_patterns': 0
        }

    # Extract observed counts
    observed_counts = []
    pattern_names = []

    for pattern in pattern_distributions:
        # Use 'draws_matched' (actual field) instead of 'count'
        count = pattern.get('draws_matched', pattern.get('count', 0))
        if count > 0:  # Only include patterns that actually occurred
            observed_counts.append(count)
            pattern_names.append(pattern.get('pattern', 'unknown'))

    if len(observed_counts) < 2:
        return {
            'significant': False,
            'chi2_stat': 0.0,
            'p_value': 1.0,
            'num_patterns': len(observed_counts)
        }

    # Chi-square goodness-of-fit test (null: uniform distribution)
    observed = np.array(observed_counts)
    total_observed = sum(observed_counts)
    expected_freq = total_observed / len(observed_counts)
    expected = np.full(len(observed_counts), expected_freq)

    chi2_stat, p_value = stats.chisquare(observed, expected)

    # Calculate effect size (Cramér's V)
    cramers_v = np.sqrt(chi2_stat / (total_observed * (len(observed_counts) - 1)))

    # Calculate standardized residuals for each pattern
    residuals = {}
    for i, pattern_name in enumerate(pattern_names):
        residual = (observed[i] - expected[i]) / np.sqrt(expected[i])
        residuals[pattern_name] = {
            'observed': int(observed[i]),
            'expected': float(expected[i]),
            'residual': float(residual),
            'significant': bool(abs(residual) > 1.96)  # 95% confidence
        }

    return {
        'significant': bool(p_value < 0.05),
        'chi2_stat': float(chi2_stat),
        'p_value': float(p_value),
        'cramers_v': float(cramers_v),
        'num_patterns': len(observed_counts),
        'degrees_of_freedom': len(observed_counts) - 1,
        'pattern_residuals': residuals,
        'interpretation': _interpret_pattern_test(p_value, cramers_v)
    }


def calculate_bin_distribution_test(
    pattern_distributions: List[Dict[str, Any]],
    c_max: int
) -> Dict[str, Any]:
    """
    Test whether recency bins (C0, C1, ..., C_max) follow expected distribution.

    Uses chi-square test to validate that the distribution of numbers across
    recency bins is not random.

    Args:
        pattern_distributions: List of pattern distribution dictionaries
        c_max: Maximum recency threshold

    Returns:
        Dictionary with bin distribution test results
    """
    # Aggregate counts per bin across all patterns
    bin_counts = defaultdict(int)

    for pattern in pattern_distributions:
        # Use 'draws_matched' (actual field) instead of 'count'
        count = pattern.get('draws_matched', pattern.get('count', 0))
        for i in range(c_max + 1):
            if i < c_max:
                bin_key = f'C{i}'
            else:
                bin_key = f'C_GE_{c_max}'

            bin_value = pattern.get(bin_key, 0)
            bin_counts[bin_key] += bin_value * count  # Weight by pattern frequency

    if len(bin_counts) < 2:
        return {
            'significant': False,
            'chi2_stat': 0.0,
            'p_value': 1.0
        }

    # Test against uniform distribution
    observed = np.array(list(bin_counts.values()))
    total_observed = sum(observed)
    expected_freq = total_observed / len(bin_counts)
    expected = np.full(len(bin_counts), expected_freq)

    chi2_stat, p_value = stats.chisquare(observed, expected)

    # Calculate which bins are over/under-represented
    bin_analysis = {}
    bin_keys = list(bin_counts.keys())

    for i, bin_key in enumerate(bin_keys):
        z_score = (observed[i] - expected[i]) / np.sqrt(expected[i])
        bin_analysis[bin_key] = {
            'observed': int(observed[i]),
            'expected': float(expected[i]),
            'percentage': float(observed[i] / total_observed * 100),
            'z_score': float(z_score),
            'over_represented': bool(z_score > 1.96),
            'under_represented': bool(z_score < -1.96)
        }

    return {
        'significant': bool(p_value < 0.05),
        'chi2_stat': float(chi2_stat),
        'p_value': float(p_value),
        'degrees_of_freedom': len(bin_counts) - 1,
        'bin_analysis': bin_analysis,
        'interpretation': _interpret_bin_test(p_value)
    }


def calculate_top_pattern_validation(
    top_pattern: Dict[str, Any],
    all_patterns: List[Dict[str, Any]],
    c_max: int
) -> Dict[str, Any]:
    """
    Validate that the top pattern is significantly more common than others.

    Uses proportion test to determine if the top pattern frequency is
    statistically different from the average.

    Args:
        top_pattern: The most frequent pattern
        all_patterns: All patterns
        c_max: Maximum recency threshold

    Returns:
        Dictionary with top pattern validation results
    """
    # Use 'draws_matched' (actual field) instead of 'count'
    top_count = top_pattern.get('draws_matched', top_pattern.get('count', 0))
    top_percentage = top_pattern.get('percentage', 0)

    # Calculate average pattern frequency
    total_patterns = len(all_patterns)
    if total_patterns == 0:
        return {'significant': False, 'z_score': 0.0, 'p_value': 1.0}

    # Under null hypothesis, each pattern should have equal probability
    expected_percentage = 100.0 / total_patterns

    # Binomial test for top pattern
    # H0: top pattern frequency = expected frequency
    total_draws = sum(p.get('draws_matched', p.get('count', 0)) for p in all_patterns)

    if total_draws == 0:
        return {'significant': False, 'z_score': 0.0, 'p_value': 1.0}

    p0 = expected_percentage / 100.0  # Expected proportion
    p_hat = top_count / total_draws   # Observed proportion

    # Use binomial test
    if p0 > 0 and top_count > 0:
        result = stats.binomtest(top_count, total_draws, p0, alternative='greater')
        p_value = result.pvalue

        # Calculate z-score for effect size
        se = np.sqrt(p0 * (1 - p0) / total_draws)
        z_score = (p_hat - p0) / se if se > 0 else 0.0
    else:
        p_value = 1.0
        z_score = 0.0

    return {
        'significant': bool(p_value < 0.05 and z_score > 0),
        'z_score': float(z_score),
        'p_value': float(p_value),
        'observed_percentage': float(top_percentage),
        'expected_percentage': float(expected_percentage),
        'fold_enrichment': float(top_percentage / expected_percentage) if expected_percentage > 0 else 1.0,
        'interpretation': _interpret_top_pattern(p_value, z_score)
    }


def _interpret_pattern_test(p_value: float, cramers_v: float) -> str:
    """Interpret the pattern distribution test results."""
    if p_value >= 0.05:
        return "Patterns show no significant deviation from uniform distribution (random)"
    elif cramers_v < 0.1:
        return "Statistically significant but small effect size (weak pattern)"
    elif cramers_v < 0.3:
        return "Statistically significant with medium effect size (moderate pattern)"
    else:
        return "Statistically significant with large effect size (strong pattern)"


def _interpret_bin_test(p_value: float) -> str:
    """Interpret the bin distribution test results."""
    if p_value >= 0.05:
        return "Bin distribution is uniform (no freshness bias)"
    else:
        return "Bin distribution is non-uniform (freshness bias detected)"


def _interpret_top_pattern(p_value: float, z_score: float) -> str:
    """Interpret the top pattern validation results."""
    if p_value >= 0.05:
        return "Top pattern is not significantly more common than expected"
    elif z_score > 5:
        return "Top pattern is highly significantly over-represented (very strong signal)"
    elif z_score > 3:
        return "Top pattern is significantly over-represented (strong signal)"
    else:
        return "Top pattern is moderately over-represented (moderate signal)"


def analyze_freshness_patterns(freshness_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main analysis function - validates freshness patterns with scipy.

    Args:
        freshness_data: Raw freshness analysis data

    Returns:
        Dictionary with scipy-validated analysis results
    """
    pattern_distributions = freshness_data.get('distribution_analysis_7_numbers', [])
    c_max = freshness_data.get('c_max_threshold', 4)
    total_draws = freshness_data.get('total_draws_analyzed', 0)

    if not pattern_distributions:
        return {
            'metadata': {
                'analysis_type': 'freshness_pattern_validation',
                'statistical_methods': ['chi_square_goodness_of_fit', 'z_test'],
                'total_draws': 0,
                'significance_level': 0.05
            },
            'error': 'No pattern distributions found'
        }

    top_pattern = pattern_distributions[0] if pattern_distributions else {}

    # Run statistical tests
    print("  Running chi-square goodness-of-fit test on pattern distributions...")
    pattern_test = calculate_pattern_significance(pattern_distributions, total_draws, c_max)

    print("  Running chi-square test on bin distributions...")
    bin_test = calculate_bin_distribution_test(pattern_distributions, c_max)

    print("  Validating top pattern significance...")
    top_pattern_test = calculate_top_pattern_validation(top_pattern, pattern_distributions, c_max)

    # Extract validated weights from top pattern
    validated_weights = {}
    if pattern_test['significant'] and top_pattern_test['significant']:
        # Pattern is statistically valid - use its weights
        total_numbers = 0
        for i in range(c_max + 1):
            if i < c_max:
                count_key = f'C{i}'
            else:
                count_key = f'C_GE_{c_max}'

            count = top_pattern.get(count_key, 0)
            total_numbers += count

        if total_numbers == 0:
            total_numbers = 7.0

        for i in range(c_max + 1):
            if i < c_max:
                count_key = f'C{i}'
            else:
                count_key = f'C_GE_{c_max}'

            count = top_pattern.get(count_key, 0)
            validated_weights[count_key] = {
                'normalized_weight': float(count / total_numbers),
                'statistically_validated': True
            }
    else:
        # Pattern not significant - use uniform weights
        uniform_weight = 1.0 / (c_max + 1)
        for i in range(c_max + 1):
            if i < c_max:
                count_key = f'C{i}'
            else:
                count_key = f'C_GE_{c_max}'

            validated_weights[count_key] = {
                'normalized_weight': float(uniform_weight),
                'statistically_validated': False
            }

    return {
        'metadata': {
            'analysis_type': 'freshness_pattern_validation',
            'statistical_methods': [
                'chi_square_goodness_of_fit',
                'chi_square_uniformity_test',
                'z_test_proportion'
            ],
            'total_draws': total_draws,
            'total_patterns': len(pattern_distributions),
            'c_max': c_max,
            'significance_level': 0.05
        },
        'pattern_distribution_test': pattern_test,
        'bin_distribution_test': bin_test,
        'top_pattern_validation': top_pattern_test,
        'validated_weights': validated_weights,
        'top_pattern_details': {
            'pattern': top_pattern.get('pattern', 'unknown'),
            'draws_matched': top_pattern.get('draws_matched', top_pattern.get('count', 0)),
            'percentage': top_pattern.get('percentage', 0.0)
        }
    }


def main():
    """Main execution - load data and generate scipy-validated analysis."""
    print("=" * 70)
    print("FRESHNESS PATTERN ANALYZER (Statistical Edition)")
    print("=" * 70)
    print()

    # Load freshness data
    freshness_file = 'data/lotto_7_number_freshness_results.json'

    if not Path(freshness_file).exists():
        print(f"❌ ERROR: {freshness_file} not found")
        print(f"   REQUIRED ACTION: Run 'python drawpick.py' first")
        sys.exit(1)

    try:
        with open(freshness_file, 'r') as f:
            freshness_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in {freshness_file}: {e}")
        sys.exit(1)

    print("Analyzing freshness patterns with statistical rigor...")
    results = analyze_freshness_patterns(freshness_data)

    # Display results
    print()
    print("  ✓ Freshness pattern validation complete:")

    pattern_test = results.get('pattern_distribution_test', {})
    print(f"    - Patterns analyzed: {pattern_test.get('num_patterns', 0)}")
    print(f"    - Chi-square statistic: {pattern_test.get('chi2_stat', 0):.4f}")
    print(f"    - P-value: {pattern_test.get('p_value', 1.0):.6f}")
    print(f"    - Statistically significant: {pattern_test.get('significant', False)}")
    print(f"    - Effect size (Cramér's V): {pattern_test.get('cramers_v', 0):.4f}")

    top_pattern = results.get('top_pattern_validation', {})
    print(f"\n    - Top pattern validation:")
    print(f"      Pattern: {results.get('top_pattern_details', {}).get('pattern', 'unknown')}")
    print(f"      Z-score: {top_pattern.get('z_score', 0):.4f}")
    print(f"      P-value: {top_pattern.get('p_value', 1.0):.6f}")
    print(f"      Fold enrichment: {top_pattern.get('fold_enrichment', 1.0):.2f}x")

    bin_test = results.get('bin_distribution_test', {})
    print(f"\n    - Bin distribution test:")
    print(f"      Chi-square p-value: {bin_test.get('p_value', 1.0):.6f}")
    print(f"      Significant: {bin_test.get('significant', False)}")

    # Save results
    output_file = 'data/lotto_freshness_patterns_validated.json'
    with open(output_file, 'w') as f:
        json.dump(round_floats(results), f, indent=2)

    print(f"\n✓ Analysis saved to {output_file}")
    print()
    print("=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
