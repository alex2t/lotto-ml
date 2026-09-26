#!/usr/bin/env python3
"""
Freshness Pattern Analyzer - Statistical Validation Edition
============================================================

Uses scipy to validate freshness pattern distributions with statistical rigor.

Every test measures against what a fair draw gives (F-69), computed exactly by
`fair_pattern_probabilities()` - never a uniform spread over bins or patterns:
- Chi-square goodness-of-fit test of the pattern counts
- Chi-square test of the bin counts
- One-sided binomial test of the most common pattern

Author: Statistical Analysis Module
Version: 1.0 (Scipy Edition)
"""

import json
import sys
from itertools import product
from math import comb
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from scipy import stats
import numpy as np
from lotto_analysis.config.config import MAX_NUMBER
from lotto_analysis.utils.serialization import round_floats


BALLS_PER_DRAW = 7
MAIN_PER_DRAW = 6
MIN_EXPECTED = 5


def bin_keys(c_max: int) -> List[str]:
    """The bin names in order: C0 .. C{c_max-1}, then C_GE_{c_max}."""
    return [f'C{i}' for i in range(c_max)] + [f'C_GE_{c_max}']


def fair_pattern_probabilities(
    window: int,
    c_max: int,
    balls: int = BALLS_PER_DRAW,
    pool: int = MAX_NUMBER
) -> Dict[Tuple[int, ...], float]:
    """
    Chance of each freshness pattern among a draw's balls when every draw is fair.

    A ball's bin is how many of the `window` preceding draws had it among their main six,
    capped at `c_max`. Each preceding draw hits a given set of k of the balls with chance
    C(pool - balls, 6 - k) / C(pool, 6), and a hit moves a ball up one bin. The pattern is
    the count of balls in each bin, so this is exact rather than simulated.
    """
    all_draws = comb(pool, MAIN_PER_DRAW)
    states = {(balls,) + (0,) * c_max: 1.0}
    for _ in range(window):
        following = defaultdict(float)
        for state, p in states.items():
            for hits in product(*(range(n + 1) for n in state)):
                k = sum(hits)
                if k > MAIN_PER_DRAW:
                    continue
                ways = np.prod([comb(n, h) for n, h in zip(state, hits)])
                chance = ways * comb(pool - balls, MAIN_PER_DRAW - k) / all_draws
                moved = [n - h for n, h in zip(state, hits)]
                for i, h in enumerate(hits):
                    moved[min(i + 1, c_max)] += h
                following[tuple(moved)] += p * chance
        states = following
    return dict(states)


def _pattern_counts(pattern_distributions: List[Dict[str, Any]], c_max: int) -> Dict[Tuple[int, ...], int]:
    """Draws matched per pattern, keyed by the pattern's bin counts."""
    return {
        tuple(p[key] for key in bin_keys(c_max)): p['draws_matched']
        for p in pattern_distributions
    }


def calculate_pattern_significance(
    pattern_distributions: List[Dict[str, Any]],
    fair_probs: Dict[Tuple[int, ...], float],
    c_max: int
) -> Dict[str, Any]:
    """
    Chi-square test of the pattern counts against a fair draw.

    Patterns a fair draw expects fewer than 5 times are pooled into one cell, so the
    chi-square approximation holds.
    """
    observed_by_pattern = _pattern_counts(pattern_distributions, c_max)
    total = sum(observed_by_pattern.values())

    residuals = {}
    observed, expected = [], []
    pooled_observed, pooled_expected = 0, 0.0
    for pattern, prob in sorted(fair_probs.items(), key=lambda item: -item[1]):
        obs = observed_by_pattern.get(pattern, 0)
        exp = prob * total
        if exp < MIN_EXPECTED:
            pooled_observed += obs
            pooled_expected += exp
            continue
        observed.append(obs)
        expected.append(exp)
        name = ', '.join(f'{key}={n}' for key, n in zip(bin_keys(c_max), pattern))
        residual = (obs - exp) / np.sqrt(exp)
        residuals[name] = {
            'observed': int(obs),
            'expected': float(exp),
            'residual': float(residual),
            'significant': bool(abs(residual) > 1.96)
        }
    observed.append(pooled_observed)
    expected.append(pooled_expected)

    chi2_stat, p_value = stats.chisquare(observed, expected)
    cramers_v = np.sqrt(chi2_stat / (total * (len(observed) - 1)))

    return {
        'significant': bool(p_value < 0.05),
        'chi2_stat': float(chi2_stat),
        'p_value': float(p_value),
        'cramers_v': float(cramers_v),
        'num_patterns': len(observed_by_pattern),
        'degrees_of_freedom': len(observed) - 1,
        'pooled_rare_patterns': {'observed': int(pooled_observed), 'expected': float(pooled_expected)},
        'pattern_residuals': residuals,
        'interpretation': _interpret_pattern_test(p_value)
    }


def calculate_bin_distribution_test(
    pattern_distributions: List[Dict[str, Any]],
    fair_probs: Dict[Tuple[int, ...], float],
    c_max: int
) -> Dict[str, Any]:
    """
    Chi-square test of how many drawn balls fall in each freshness bin, against a fair draw.

    In a fair draw most balls are in C0 - five draws hold at most 30 of the 47 numbers - so
    the expected share per bin comes from `fair_probs`, never a third each.
    """
    keys = bin_keys(c_max)
    observed = np.zeros(len(keys))
    for pattern, count in _pattern_counts(pattern_distributions, c_max).items():
        observed += np.array(pattern) * count
    fair_share = sum(np.array(pattern) * p for pattern, p in fair_probs.items()) / BALLS_PER_DRAW
    total_observed = observed.sum()
    expected = fair_share * total_observed

    chi2_stat, p_value = stats.chisquare(observed, expected)

    bin_analysis = {}
    for i, bin_key in enumerate(keys):
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
        'degrees_of_freedom': len(keys) - 1,
        'bin_analysis': bin_analysis,
        'interpretation': _interpret_bin_test(p_value)
    }


def calculate_top_pattern_validation(
    top_pattern: Dict[str, Any],
    all_patterns: List[Dict[str, Any]],
    fair_probs: Dict[Tuple[int, ...], float],
    c_max: int
) -> Dict[str, Any]:
    """
    Is the most common pattern more common than a fair draw makes it?

    The top pattern is picked after looking, from several a fair draw makes almost equally
    likely, so testing it alone against its own chance flags a quarter of fair histories. The
    p-value is the chance that any pattern reaches the top count: at most the sum, over every
    pattern, of its binomial tail (Bonferroni).
    """
    top_count = top_pattern['draws_matched']
    total_draws = sum(p['draws_matched'] for p in all_patterns)
    p0 = fair_probs[tuple(top_pattern[key] for key in bin_keys(c_max))]
    p_hat = top_count / total_draws

    tails = stats.binom.sf(top_count - 1, total_draws, list(fair_probs.values()))
    p_value = min(1.0, float(tails.sum()))
    z_score = (p_hat - p0) / np.sqrt(p0 * (1 - p0) / total_draws)

    return {
        'significant': bool(p_value < 0.05),
        'z_score': float(z_score),
        'p_value': float(p_value),
        'observed_percentage': float(p_hat * 100),
        'expected_percentage': float(p0 * 100),
        'fold_enrichment': float(p_hat / p0),
        'interpretation': _interpret_top_pattern(p_value)
    }


def _interpret_pattern_test(p_value: float) -> str:
    """Interpret the pattern distribution test results."""
    if p_value >= 0.05:
        return "Pattern counts are in line with a fair draw"
    return "Pattern counts differ from a fair draw"


def _interpret_bin_test(p_value: float) -> str:
    """Interpret the bin distribution test results."""
    if p_value >= 0.05:
        return "Bin counts are in line with a fair draw (no freshness bias)"
    return "Bin counts differ from a fair draw (freshness bias detected)"


def _interpret_top_pattern(p_value: float) -> str:
    """Interpret the top pattern validation results."""
    if p_value >= 0.05:
        return "Top pattern is no more common than a fair draw makes it"
    return "Top pattern is more common than a fair draw makes it"


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

    top_pattern = pattern_distributions[0]
    fair_probs = fair_pattern_probabilities(freshness_data['window_size_W'], c_max)

    print("  Running chi-square test of pattern counts against a fair draw...")
    pattern_test = calculate_pattern_significance(pattern_distributions, fair_probs, c_max)

    print("  Running chi-square test of bin counts against a fair draw...")
    bin_test = calculate_bin_distribution_test(pattern_distributions, fair_probs, c_max)

    print("  Testing the top pattern against a fair draw...")
    top_pattern_test = calculate_top_pattern_validation(top_pattern, pattern_distributions, fair_probs, c_max)

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
                'chi_square_fair_draw_bins',
                'binomial_test_top_pattern'
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
        print(f"ERROR: {freshness_file} not found")
        print(f"   REQUIRED ACTION: Run 'python drawpick.py' first")
        sys.exit(1)

    try:
        with open(freshness_file, 'r') as f:
            freshness_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {freshness_file}: {e}")
        sys.exit(1)

    print("Analyzing freshness patterns with statistical rigor...")
    results = analyze_freshness_patterns(freshness_data)

    # Display results
    print()
    print("  Freshness pattern validation complete:")

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

    print(f"\nAnalysis saved to {output_file}")
    print()
    print("=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
