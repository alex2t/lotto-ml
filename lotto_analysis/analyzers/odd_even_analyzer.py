#!/usr/bin/env python3
"""
Odd/Even Distribution Analyzer - Statistical Validation Edition
================================================================

Uses scipy to validate odd/even distribution patterns with statistical rigor.

Statistical Methods:
- Chi-square goodness-of-fit test for odd/even ratio validation
- Binomial test for individual number analysis
- Effect size calculation (Cramér's V)
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

# Try to import statsmodels for FDR correction
try:
    from statsmodels.stats.multitest import multipletests
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False


def analyze_odd_even_distribution(draw_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze odd/even distribution across draws using chi-square test.

    Tests whether the observed odd/even distribution deviates significantly
    from expected (uniform) distribution.

    Args:
        draw_history: List of historical draws

    Returns:
        Dictionary with chi-square test results
    """
    # Count odd/even appearances in each draw
    odd_counts = []
    even_counts = []

    for draw in draw_history:
        numbers = draw.get('numbers', [])
        # Exclude bonus number if present
        numbers = [n for n in numbers if isinstance(n, int)]

        odd = sum(1 for n in numbers if n % 2 == 1)
        even = sum(1 for n in numbers if n % 2 == 0)

        odd_counts.append(odd)
        even_counts.append(even)

    # Expected: 3.5 odd, 3.5 even per 7-number draw (50/50 split)
    # But we'll test against observed distribution
    total_odd = sum(odd_counts)
    total_even = sum(even_counts)
    total_numbers = total_odd + total_even

    if total_numbers == 0:
        return {
            'significant': False,
            'chi2_stat': 0.0,
            'p_value': 1.0,
            'error': 'No data'
        }

    # Chi-square goodness-of-fit test
    # H0: Odd and even numbers appear with equal frequency (50/50)
    observed = np.array([total_odd, total_even])
    expected = np.full(2, total_numbers / 2.0)

    chi2_stat, p_value = stats.chisquare(observed, expected)

    # Calculate effect size (Cramér's V)
    cramers_v = np.sqrt(chi2_stat / total_numbers)

    return {
        'significant': bool(p_value < 0.05),
        'chi2_stat': float(chi2_stat),
        'p_value': float(p_value),
        'cramers_v': float(cramers_v),
        'total_odd': int(total_odd),
        'total_even': int(total_even),
        'odd_percentage': float(total_odd / total_numbers * 100),
        'even_percentage': float(total_even / total_numbers * 100),
        'interpretation': _interpret_odd_even_test(p_value, total_odd, total_even)
    }


def calculate_per_number_odd_even_affinity(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[int, Dict[str, Any]]:
    """
    Calculate per-number odd/even affinity with statistical validation.

    For each number, calculates how well it fits with odd/even draws using
    binomial test.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary mapping number to affinity analysis
    """
    number_stats = defaultdict(lambda: {'odd_draw_count': 0, 'even_draw_count': 0, 'total_appearances': 0})

    # Categorize each draw as odd-heavy or even-heavy
    for draw in draw_history:
        numbers = draw.get('numbers', [])
        numbers = [n for n in numbers if isinstance(n, int)]

        odd_in_draw = sum(1 for n in numbers if n % 2 == 1)
        even_in_draw = sum(1 for n in numbers if n % 2 == 0)

        draw_type = 'odd' if odd_in_draw >= even_in_draw else 'even'

        for num in numbers:
            if 1 <= num <= max_number:
                number_stats[num]['total_appearances'] += 1
                if draw_type == 'odd':
                    number_stats[num]['odd_draw_count'] += 1
                else:
                    number_stats[num]['even_draw_count'] += 1

    # Calculate affinity scores with binomial test
    affinity_results = {}

    for num in range(1, max_number + 1):
        stats_data = number_stats[num]
        total = stats_data['total_appearances']

        if total < 5:  # Need minimum sample size
            affinity_results[num] = {
                'affinity_score': 0.5,
                'statistically_validated': False,
                'p_value': 1.0,
                'preferred_type': 'neutral'
            }
            continue

        odd_draw_count = stats_data['odd_draw_count']
        even_draw_count = stats_data['even_draw_count']

        # Binomial test: does this number appear more in odd or even draws?
        # H0: number appears equally in odd/even draws (p=0.5)
        result = stats.binomtest(odd_draw_count, total, 0.5, alternative='two-sided')
        p_value = result.pvalue

        # Calculate affinity score
        if odd_draw_count > even_draw_count:
            affinity_score = 0.5 + (odd_draw_count / total - 0.5)
            preferred_type = 'odd' if p_value < 0.05 else 'neutral'
        else:
            affinity_score = 0.5 - (even_draw_count / total - 0.5)
            preferred_type = 'even' if p_value < 0.05 else 'neutral'

        # If number itself is odd, higher score = prefers odd draws
        # If number itself is even, lower score = prefers even draws
        num_parity = 'odd' if num % 2 == 1 else 'even'

        affinity_results[num] = {
            'affinity_score': float(affinity_score),
            'statistically_validated': bool(p_value < 0.05),
            'p_value': float(p_value),
            'preferred_type': preferred_type,
            'number_parity': num_parity,
            'alignment': 'aligned' if preferred_type == num_parity else 'misaligned'
        }

    return affinity_results


def analyze_odd_even_patterns(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[str, Any]:
    """
    Main analysis function - validates odd/even patterns with scipy.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary with scipy-validated analysis results
    """
    print("  Running chi-square test on overall odd/even distribution...")
    overall_test = analyze_odd_even_distribution(draw_history)

    print("  Calculating per-number odd/even affinity with binomial tests...")
    per_number_affinity = calculate_per_number_odd_even_affinity(draw_history, max_number)

    # CRITICAL FIX v3.11: Apply multiple hypothesis testing correction (FDR)
    if STATSMODELS_AVAILABLE and len(per_number_affinity) > 0:
        print("  Applying FDR correction for multiple hypothesis testing...")

        # Collect p-values in order
        numbers = sorted(per_number_affinity.keys())
        p_values = [per_number_affinity[num]['p_value'] for num in numbers]

        # Apply Benjamini-Hochberg FDR correction
        rejected, p_adjusted, _, _ = multipletests(
            p_values,
            method='fdr_bh',
            alpha=0.05
        )

        # Update results with corrected p-values
        num_significant_before = sum(
            1 for data in per_number_affinity.values()
            if data['statistically_validated']
        )

        for i, num in enumerate(numbers):
            per_number_affinity[num]['p_value_adjusted'] = float(p_adjusted[i])
            per_number_affinity[num]['statistically_validated'] = bool(rejected[i])

        num_significant_after = sum(
            1 for data in per_number_affinity.values()
            if data['statistically_validated']
        )

        print(f"    Before FDR: {num_significant_before} significant results")
        print(f"    After FDR:  {num_significant_after} significant results")

        fdr_applied = True
    else:
        if not STATSMODELS_AVAILABLE:
            print("  ⚠️  Skipping FDR correction (statsmodels not installed)")
        fdr_applied = False

    # Calculate validated scores (normalized 0-1)
    validated_scores = {}
    for num, affinity_data in per_number_affinity.items():
        validated_scores[num] = affinity_data['affinity_score']

    # Count statistically significant deviations (after FDR correction)
    num_significant = sum(1 for data in per_number_affinity.values() if data['statistically_validated'])

    return {
        'metadata': {
            'analysis_type': 'odd_even_validation',
            'statistical_methods': [
                'chi_square_goodness_of_fit',
                'binomial_test',
                'fdr_correction' if fdr_applied else 'no_fdr_correction'
            ],
            'total_draws': len(draw_history),
            'significance_level': 0.05,
            'fdr_correction_applied': fdr_applied
        },
        'overall_distribution_test': overall_test,
        'per_number_affinity': per_number_affinity,
        'validated_scores': validated_scores,
        'num_significant_deviations': num_significant
    }


def _interpret_odd_even_test(p_value: float, total_odd: int, total_even: int) -> str:
    """Interpret odd/even distribution test."""
    if p_value >= 0.05:
        return "Odd/even distribution is balanced (no significant deviation from 50/50)"
    elif total_odd > total_even:
        return "Odd numbers are significantly over-represented"
    else:
        return "Even numbers are significantly over-represented"


def main():
    """Main execution - load data and generate scipy-validated analysis."""
    print("=" * 70)
    print("ODD/EVEN DISTRIBUTION ANALYZER (Statistical Edition)")
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
    print("Analyzing odd/even distribution with statistical rigor...")
    results = analyze_odd_even_patterns(draw_list)

    # Display results
    print()
    print("  ✓ Odd/even distribution validation complete:")

    overall = results.get('overall_distribution_test', {})
    print(f"    - Chi-square statistic: {overall.get('chi2_stat', 0):.4f}")
    print(f"    - P-value: {overall.get('p_value', 1.0):.6f}")
    print(f"    - Statistically significant: {overall.get('significant', False)}")
    print(f"    - Odd: {overall.get('odd_percentage', 0):.1f}%")
    print(f"    - Even: {overall.get('even_percentage', 0):.1f}%")

    print(f"\n    - Per-number affinity:")
    print(f"      Numbers with significant deviation: {results.get('num_significant_deviations', 0)}/47")

    # Save results
    output_file = 'data/lotto_odd_even_validated.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Analysis saved to {output_file}")
    print()
    print("=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
