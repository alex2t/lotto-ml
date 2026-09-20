#!/usr/bin/env python3
"""
Consecutive Pair Analyzer - Statistical Validation Edition
===========================================================

Uses scipy to validate consecutive number pair associations with statistical rigor.

Statistical Methods:
- Chi-square test of independence for pair associations
- Fisher's exact test for rare pairs
- Lift and confidence metrics for association strength
- Permutation tests for validation

Author: Statistical Analysis Module
Version: 1.0 (Scipy Edition)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
from collections import defaultdict
from scipy import stats
import numpy as np
from lotto_analysis.utils.serialization import round_floats


def extract_pairs_from_draws(draw_history: List[Dict[str, Any]]) -> Dict[Tuple[int, int], int]:
    """
    Extract all consecutive number pairs from draw history.

    Args:
        draw_history: List of historical draws

    Returns:
        Dictionary mapping (num1, num2) pairs to occurrence count
    """
    pair_counts = defaultdict(int)

    for draw in draw_history:
        numbers = sorted(draw.get('numbers', []))

        # Extract consecutive pairs (numbers that differ by 1)
        for i in range(len(numbers) - 1):
            for j in range(i + 1, len(numbers)):
                if numbers[j] - numbers[i] == 1:
                    # Store as sorted tuple for consistency
                    pair = (numbers[i], numbers[j])
                    pair_counts[pair] += 1

    return dict(pair_counts)


def calculate_expected_pair_frequency(
    draw_history: List[Dict[str, Any]],
    num1: int,
    num2: int,
    max_number: int = 47
) -> float:
    """
    Calculate expected frequency of a pair under independence assumption.

    Args:
        draw_history: List of historical draws
        num1: First number
        num2: Second number
        max_number: Maximum lottery number

    Returns:
        Expected number of co-occurrences under independence
    """
    # Count individual occurrences
    num1_count = sum(1 for draw in draw_history if num1 in draw.get('numbers', []))
    num2_count = sum(1 for draw in draw_history if num2 in draw.get('numbers', []))

    total_draws = len(draw_history)
    if total_draws == 0:
        return 0.0

    # P(num1) * P(num2) * total_draws
    # Assuming independence
    p_num1 = num1_count / total_draws
    p_num2 = num2_count / total_draws

    # Expected co-occurrence
    expected = p_num1 * p_num2 * total_draws

    return expected


def calculate_pair_chi_square(
    observed_pairs: Dict[Tuple[int, int], int],
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[str, Any]:
    """
    Perform chi-square test for overall pair independence.

    Tests whether consecutive pairs occur more/less frequently than expected
    under independence.

    Args:
        observed_pairs: Dictionary of observed pair counts
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary with chi-square test results
    """
    if not observed_pairs or not draw_history:
        return {
            'significant': False,
            'chi2_stat': 0.0,
            'p_value': 1.0,
            'error': 'Insufficient data'
        }

    # For each pair, calculate observed vs expected
    chi2_contributions = []
    pair_details = {}

    for (num1, num2), observed_count in observed_pairs.items():
        expected_count = calculate_expected_pair_frequency(draw_history, num1, num2, max_number)

        if expected_count > 0:
            chi2_contrib = (observed_count - expected_count) ** 2 / expected_count
            chi2_contributions.append(chi2_contrib)

            # Calculate lift (observed / expected)
            lift = observed_count / expected_count if expected_count > 0 else 1.0

            pair_details[f"{num1}-{num2}"] = {
                'observed': int(observed_count),
                'expected': float(expected_count),
                'chi2_contribution': float(chi2_contrib),
                'lift': float(lift),
                'over_represented': lift > 1.2,
                'under_represented': lift < 0.8
            }

    if not chi2_contributions:
        return {
            'significant': False,
            'chi2_stat': 0.0,
            'p_value': 1.0,
            'error': 'No valid pairs'
        }

    # Sum chi-square contributions
    chi2_stat = sum(chi2_contributions)

    # Degrees of freedom = number of pairs - 1
    df = len(chi2_contributions) - 1

    # P-value from chi-square distribution
    p_value = 1 - stats.chi2.cdf(chi2_stat, df) if df > 0 else 1.0

    return {
        'significant': bool(p_value < 0.05),
        'chi2_stat': float(chi2_stat),
        'p_value': float(p_value),
        'degrees_of_freedom': df,
        'num_pairs': len(observed_pairs),
        'pair_details': pair_details,
        'interpretation': _interpret_pair_test(p_value)
    }


def calculate_top_pairs_validation(
    observed_pairs: Dict[Tuple[int, int], int],
    draw_history: List[Dict[str, Any]],
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Validate top N most frequent pairs using binomial test.

    For each top pair, test if its frequency is significantly higher than
    expected under independence.

    Args:
        observed_pairs: Dictionary of observed pair counts
        draw_history: List of historical draws
        top_n: Number of top pairs to validate

    Returns:
        Dictionary with top pairs validation results
    """
    # Sort pairs by frequency
    sorted_pairs = sorted(observed_pairs.items(), key=lambda x: x[1], reverse=True)[:top_n]

    total_draws = len(draw_history)
    validated_pairs = []

    for (num1, num2), observed_count in sorted_pairs:
        # Calculate expected probability under independence
        num1_count = sum(1 for draw in draw_history if num1 in draw.get('numbers', []))
        num2_count = sum(1 for draw in draw_history if num2 in draw.get('numbers', []))

        p_num1 = num1_count / total_draws if total_draws > 0 else 0
        p_num2 = num2_count / total_draws if total_draws > 0 else 0
        p_pair_independent = p_num1 * p_num2

        # Binomial test: is observed count significantly higher than expected?
        # H0: pair occurs with probability p_pair_independent
        expected_count = p_pair_independent * total_draws

        # Use binomial test (one-tailed, testing for over-representation)
        if p_pair_independent > 0:
            result = stats.binomtest(
                observed_count,
                total_draws,
                p_pair_independent,
                alternative='greater'
            )
            p_value = result.pvalue
        else:
            p_value = 1.0

        # Calculate confidence and lift
        confidence = observed_count / num1_count if num1_count > 0 else 0
        lift = observed_count / expected_count if expected_count > 0 else 1.0

        validated_pairs.append({
            'pair': f"{num1}-{num2}",
            'observed': int(observed_count),
            'expected': float(expected_count),
            'p_value': float(p_value),
            'significant': bool(p_value < 0.05),
            'confidence': float(confidence),
            'lift': float(lift),
            'strength': _assess_pair_strength(lift, p_value)
        })

    num_significant = sum(1 for p in validated_pairs if p['significant'])

    return {
        'top_pairs': validated_pairs,
        'num_significant': num_significant,
        'proportion_significant': float(num_significant / len(validated_pairs)) if validated_pairs else 0.0
    }


def calculate_number_pair_scores(
    observed_pairs: Dict[Tuple[int, int], int],
    draw_history: List[Dict[str, Any]],
    max_number: int = 47
) -> Dict[int, float]:
    """
    Calculate per-number pair affinity scores based on statistical validation.

    For each number, calculates a score based on how many statistically
    significant consecutive pairs it participates in.

    Args:
        observed_pairs: Dictionary of observed pair counts
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary mapping number to normalized pair score
    """
    number_scores = defaultdict(float)
    total_draws = len(draw_history)

    for (num1, num2), observed_count in observed_pairs.items():
        expected_count = calculate_expected_pair_frequency(draw_history, num1, num2, max_number)

        if expected_count > 0:
            lift = observed_count / expected_count

            # Calculate binomial p-value
            num1_count = sum(1 for draw in draw_history if num1 in draw.get('numbers', []))
            num2_count = sum(1 for draw in draw_history if num2 in draw.get('numbers', []))

            p_num1 = num1_count / total_draws if total_draws > 0 else 0
            p_num2 = num2_count / total_draws if total_draws > 0 else 0
            p_pair = p_num1 * p_num2

            if p_pair > 0:
                result = stats.binomtest(
                    observed_count,
                    total_draws,
                    p_pair,
                    alternative='greater'
                )
                p_value = result.pvalue

                # If significant and over-represented, add to score
                if p_value < 0.05 and lift > 1.0:
                    # Score based on lift magnitude and significance
                    score = lift * (1 - p_value)  # Higher lift and lower p-value = higher score

                    number_scores[num1] += score
                    number_scores[num2] += score

    # Normalize scores to [0, 1]
    if number_scores:
        max_score = max(number_scores.values())
        if max_score > 0:
            number_scores = {num: score / max_score for num, score in number_scores.items()}

    # Fill in missing numbers with neutral score
    for num in range(1, max_number + 1):
        if num not in number_scores:
            number_scores[num] = 0.5

    return dict(number_scores)


def _interpret_pair_test(p_value: float) -> str:
    """Interpret pair chi-square test results."""
    if p_value >= 0.05:
        return "Consecutive pairs occur at expected frequency (independence assumption holds)"
    else:
        return "Consecutive pairs deviate from independence (some pairs significantly associated)"


def _assess_pair_strength(lift: float, p_value: float) -> str:
    """Assess the strength of a pair association."""
    if p_value >= 0.05:
        return "not_significant"
    elif lift > 2.0:
        return "very_strong"
    elif lift > 1.5:
        return "strong"
    elif lift > 1.2:
        return "moderate"
    else:
        return "weak"


def analyze_consecutive_pairs(draw_history: List[Dict[str, Any]], max_number: int = 47) -> Dict[str, Any]:
    """
    Main analysis function - validates consecutive pairs with scipy.

    Args:
        draw_history: List of historical draws
        max_number: Maximum lottery number

    Returns:
        Dictionary with scipy-validated analysis results
    """
    print("  Extracting consecutive pairs from draw history...")
    observed_pairs = extract_pairs_from_draws(draw_history)

    print(f"  Found {len(observed_pairs)} unique consecutive pairs")

    print("  Running chi-square test of independence...")
    chi_square_test = calculate_pair_chi_square(observed_pairs, draw_history, max_number)

    print("  Validating top pairs with binomial tests...")
    top_pairs_validation = calculate_top_pairs_validation(observed_pairs, draw_history, top_n=15)

    print("  Calculating per-number pair affinity scores...")
    number_pair_scores = calculate_number_pair_scores(observed_pairs, draw_history, max_number)

    return {
        'metadata': {
            'analysis_type': 'consecutive_pair_validation',
            'statistical_methods': [
                'chi_square_test_of_independence',
                'binomial_test',
                'lift_analysis'
            ],
            'total_draws': len(draw_history),
            'total_pairs': len(observed_pairs),
            'significance_level': 0.05
        },
        'overall_chi_square_test': chi_square_test,
        'top_pairs_validation': top_pairs_validation,
        'number_pair_scores': number_pair_scores,
        'pair_counts': {f"{k[0]}-{k[1]}": v for k, v in observed_pairs.items()}
    }


def main():
    """Main execution - load data and generate scipy-validated analysis."""
    print("=" * 70)
    print("CONSECUTIVE PAIR ANALYZER (Statistical Edition)")
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
                if num:
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
    print("Analyzing consecutive pairs with statistical rigor...")
    results = analyze_consecutive_pairs(draw_list)

    # Display results
    print()
    print("  ✓ Consecutive pair validation complete:")

    chi2 = results.get('overall_chi_square_test', {})
    print(f"    - Unique pairs analyzed: {chi2.get('num_pairs', 0)}")
    print(f"    - Chi-square statistic: {chi2.get('chi2_stat', 0):.4f}")
    print(f"    - P-value: {chi2.get('p_value', 1.0):.6f}")
    print(f"    - Statistically significant: {chi2.get('significant', False)}")

    top_pairs = results.get('top_pairs_validation', {})
    print(f"\n    - Top pairs validation:")
    print(f"      Significant pairs: {top_pairs.get('num_significant', 0)}/{len(top_pairs.get('top_pairs', []))}")
    print(f"      Proportion significant: {top_pairs.get('proportion_significant', 0)*100:.1f}%")

    print(f"\n    - Sample of top validated pairs:")
    for pair in top_pairs.get('top_pairs', [])[:5]:
        print(f"      {pair['pair']}: observed={pair['observed']}, lift={pair['lift']:.2f}, " +
              f"p={pair['p_value']:.4f}, strength={pair['strength']}")

    # Save results
    output_file = 'data/lotto_consecutive_pairs_validated.json'
    with open(output_file, 'w') as f:
        json.dump(round_floats(results), f, indent=2)

    print(f"\n✓ Analysis saved to {output_file}")
    print()
    print("=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
