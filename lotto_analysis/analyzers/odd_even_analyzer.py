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
from lotto_analysis.utils.serialization import round_floats

# Try to import statsmodels for FDR correction
try:
    from statsmodels.stats.multitest import multipletests
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False


def odd_in_pool(max_number: int) -> int:
    """How many of the numbers 1..max_number are odd."""
    return (max_number + 1) // 2


def chance_of_odd_draw(number: int, max_number: int, draw_size: int) -> float:
    """
    Chance that a fair draw containing `number` has at least as many odd numbers as even.

    The draw's other draw_size - 1 numbers come from the remaining max_number - 1, so this is
    hypergeometric. An odd number already supplies one odd ball, which is why testing its share
    of odd draws against 0.5 flagged every odd number (F-38).
    """
    others_odd = odd_in_pool(max_number) - number % 2
    odd_needed = -(-draw_size // 2) - number % 2
    return float(stats.hypergeom.sf(odd_needed - 1, max_number - 1, others_odd, draw_size - 1))


def analyze_odd_even_distribution(draw_history: List[Dict[str, Any]], max_number: int = 47) -> Dict[str, Any]:
    """
    Analyze odd/even distribution across draws using chi-square test.

    Tests whether the observed odd/even split deviates from a fair draw's, which is the
    pool's share of odd numbers - 24/47 for 1-47, not 50/50 (F-38).

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
    # H0: balls are odd in the pool's proportion, 24/47 - not 50/50 (F-38)
    observed = np.array([total_odd, total_even])
    odd_share = odd_in_pool(max_number) / max_number
    expected = total_numbers * np.array([odd_share, 1 - odd_share])

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
        'expected_odd_percentage': float(odd_share * 100),
        'interpretation': _interpret_odd_even_test(p_value, total_odd, total_even)
    }


def calculate_per_number_odd_even_affinity(
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[int, Dict[str, Any]]:
    """
    Calculate per-number odd/even affinity with statistical validation.

    A draw is "odd" when it has at least as many odd numbers as even. Each number's share of
    odd draws is tested (binomial) against the chance of an odd draw given that number came
    up (chance_of_odd_draw), not 0.5 (F-38).

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary mapping number to affinity analysis
    """
    number_stats = defaultdict(lambda: {'odd_draw_count': 0, 'even_draw_count': 0, 'total_appearances': 0,
                                        'chance_sum': 0.0})

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
                number_stats[num]['chance_sum'] += chance_of_odd_draw(num, max_number, len(numbers))
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
                'chance_affinity_score': 0.5,
                'statistically_validated': False,
                'p_value': 1.0,
                'preferred_type': 'neutral'
            }
            continue

        odd_draw_count = stats_data['odd_draw_count']
        chance = stats_data['chance_sum'] / total

        # H0: the number's draws are odd as often as fair draws containing it would be
        p_value = stats.binomtest(odd_draw_count, total, chance, alternative='two-sided').pvalue

        affinity_score = odd_draw_count / total
        if p_value < 0.05:
            preferred_type = 'odd' if affinity_score > chance else 'even'
        else:
            preferred_type = 'neutral'

        num_parity = 'odd' if num % 2 == 1 else 'even'

        affinity_results[num] = {
            'affinity_score': float(affinity_score),
            'chance_affinity_score': float(chance),
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
    overall_test = analyze_odd_even_distribution(draw_history, max_number)

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
            if not rejected[i]:
                per_number_affinity[num]['preferred_type'] = 'neutral'
                per_number_affinity[num]['alignment'] = 'misaligned'

        num_significant_after = sum(
            1 for data in per_number_affinity.values()
            if data['statistically_validated']
        )

        print(f"    Before FDR: {num_significant_before} significant results")
        print(f"    After FDR:  {num_significant_after} significant results")

        fdr_applied = True
    else:
        if not STATSMODELS_AVAILABLE:
            print("  Skipping FDR correction (statsmodels not installed)")
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
        return "Odd/even split is what a fair draw gives (24 of the 47 numbers are odd)"
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
    print("Analyzing odd/even distribution with statistical rigor...")
    results = analyze_odd_even_patterns(draw_list)

    # Display results
    print()
    print("  Odd/even distribution validation complete:")

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
        json.dump(round_floats(results), f, indent=2)

    print(f"\nAnalysis saved to {output_file}")
    print()
    print("=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
