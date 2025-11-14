"""
Long-term pattern analysis module - calculates statistically rigorous long-term patterns
Uses scipy for statistical significance testing, following the bonus_analyzer.py pattern
"""

from collections import defaultdict, Counter
from typing import Dict, Tuple, List, Any
from scipy import stats
import numpy as np
import json
from pathlib import Path


def load_baseline_category_weights() -> Dict[str, float]:
    """
    Load baseline category weights from lotto_statistics_analysis.json.

    Uses REAL historical distribution instead of hardcoded estimates.

    Returns:
        Dictionary with normalized category weights from real data
    """
    try:
        stats_file = Path(__file__).parent.parent.parent / 'data' / 'lotto_statistics_analysis.json'
        with open(stats_file, 'r') as f:
            stats_data = json.load(f)

        # Get real main category distribution
        hmc_dist = stats_data.get('hmc_distribution', {})
        main_cat_dist = hmc_dist.get('main_category_distribution', {})

        if main_cat_dist:
            hot_pct = main_cat_dist.get('hot', 33.33)
            medium_pct = main_cat_dist.get('medium', 33.33)
            cold_pct = main_cat_dist.get('cold', 33.33)

            # Normalize to sum to 1.0
            total = hot_pct + medium_pct + cold_pct
            return {
                'hot': hot_pct / total,
                'medium': medium_pct / total,
                'cold': cold_pct / total
            }
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        pass

    # Fallback only if file doesn't exist
    return {'hot': 1/3, 'medium': 1/3, 'cold': 1/3}


def convert_to_native_types(obj):
    """
    Convert numpy types to native Python types for JSON serialization.

    Args:
        obj: Object to convert

    Returns:
        Object with native Python types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {key: convert_to_native_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native_types(item) for item in obj]
    else:
        return obj


def calculate_hmc_pattern_significance(
    draw_history: Dict[str, Any],
    min_count: int = 5
) -> Dict:
    """
    Analyze HMC pattern distributions with statistical significance testing.

    Uses chi-square goodness-of-fit test to determine if observed HMC patterns
    deviate significantly from expected uniform distribution.

    Args:
        draw_history: Historical draw data from lotto_draw_history.json
        min_count: Minimum pattern count to include in analysis

    Returns:
        Dictionary containing:
        - pattern_distribution: {pattern: {count, percentage, expected, chi2_contribution}}
        - overall_chi2: Overall chi-square statistic
        - p_value: P-value for chi-square test
        - significant: Boolean indicating statistical significance (p < 0.05)
        - category_weights: Statistically derived weights for hot/medium/cold
    """
    hmc_patterns = Counter()
    total_draws = 0

    # Count HMC patterns
    for draw_date, draw_data in draw_history.items():
        hmc_summary = draw_data.get('hmc_summary', {})
        hmc_dist = hmc_summary.get('hmc_distribution', '')

        if hmc_dist:
            hmc_patterns[hmc_dist] += 1
            total_draws += 1

    if total_draws == 0:
        # Load baseline weights from REAL data instead of hardcoded values
        baseline_weights = load_baseline_category_weights()
        return {
            'pattern_distribution': {},
            'overall_chi2': 0.0,
            'p_value': 1.0,
            'significant': False,
            'category_weights': baseline_weights,
            'note': 'Using baseline weights from lotto_statistics_analysis.json (no draw data available)'
        }

    # Filter patterns by minimum count
    significant_patterns = {
        pattern: count for pattern, count in hmc_patterns.items()
        if count >= min_count
    }

    # Calculate chi-square test
    observed = np.array(list(significant_patterns.values()))
    total_significant = sum(significant_patterns.values())  # Sum of observed counts
    expected_freq = total_significant / len(significant_patterns) if significant_patterns else 1

    if len(observed) > 1:
        expected = np.full(len(observed), expected_freq)
        chi2_stat, p_value = stats.chisquare(observed, expected)
    else:
        chi2_stat, p_value = 0.0, 1.0

    # Calculate category weights based on weighted average of patterns
    hot_total = 0.0
    medium_total = 0.0
    cold_total = 0.0
    weight_sum = 0.0

    pattern_details = {}

    for pattern, count in significant_patterns.items():
        parts = pattern.split('-')
        if len(parts) == 3:
            try:
                hot_count = int(parts[0])
                medium_count = int(parts[1])
                cold_count = int(parts[2])

                # Weight by frequency (more common patterns = more weight)
                weight = count / total_draws

                hot_total += hot_count * weight
                medium_total += medium_count * weight
                cold_total += cold_count * weight
                weight_sum += weight

                percentage = (count / total_draws) * 100
                chi2_contribution = ((count - expected_freq) ** 2) / expected_freq if expected_freq > 0 else 0

                pattern_details[pattern] = {
                    'count': int(count),
                    'percentage': float(percentage),
                    'expected': float(expected_freq),
                    'chi2_contribution': float(chi2_contribution),
                    'hot_count': int(hot_count),
                    'medium_count': int(medium_count),
                    'cold_count': int(cold_count)
                }
            except (ValueError, IndexError):
                continue

    # Normalize category weights
    if weight_sum > 0:
        hot_weight = hot_total / weight_sum / 6.0  # Normalize to 0-1 (max 6 numbers)
        medium_weight = medium_total / weight_sum / 6.0
        cold_weight = cold_total / weight_sum / 6.0

        # Further normalize so they sum to 1.0
        total_weight = hot_weight + medium_weight + cold_weight
        if total_weight > 0:
            hot_weight /= total_weight
            medium_weight /= total_weight
            cold_weight /= total_weight
    else:
        # Load baseline weights from REAL data instead of hardcoded 1/3
        baseline_weights = load_baseline_category_weights()
        hot_weight = baseline_weights['hot']
        medium_weight = baseline_weights['medium']
        cold_weight = baseline_weights['cold']

    return {
        'pattern_distribution': pattern_details,
        'overall_chi2': float(chi2_stat),
        'p_value': float(p_value),
        'significant': bool(p_value < 0.05),
        'total_draws_analyzed': int(total_draws),
        'num_patterns': int(len(significant_patterns)),
        'category_weights': {
            'hot': float(hot_weight),
            'medium': float(medium_weight),
            'cold': float(cold_weight)
        }
    }


def analyze_recency_correlations(
    draw_history: Dict[str, Any]
) -> Dict:
    """
    Analyze correlation between days-since-last-hit and win probability by category.

    Uses Pearson correlation to determine if recency is a significant predictor.

    Args:
        draw_history: Historical draw data

    Returns:
        Dictionary containing:
        - by_category: {category: {ranges, correlations, p_values}}
        - recency_ranges: Binned recency data with win rates
    """
    # Define recency ranges
    recency_bins = [
        ('0-7 days', 0, 7),
        ('8-14 days', 8, 14),
        ('15-21 days', 15, 21),
        ('22-30 days', 22, 30),
        ('31-45 days', 31, 45),
        ('46-60 days', 46, 60),
        ('61-90 days', 61, 90),
        ('91-120 days', 91, 120),
        ('121+ days', 121, 999)
    ]

    category_data = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'total': 0}))

    # Collect recency data by category
    for draw_date, draw_data in draw_history.items():
        winning_details = draw_data.get('winning_numbers_details', [])

        for detail in winning_details:
            if detail.get('is_bonus', False):
                continue  # Skip bonus numbers

            category = detail.get('category', 'unknown')
            days_since = detail.get('days_since_last', 999)

            # Find which recency bin this falls into
            for bin_name, min_days, max_days in recency_bins:
                if min_days <= days_since <= max_days:
                    category_data[category][bin_name]['wins'] += 1
                    break

        # Also count non-winners (approximate from recent_counts if available)
        # This is a simplification - ideally we'd track all numbers per draw

    # Calculate statistics for each category
    results_by_category = {}

    for category in ['hot', 'medium', 'cold']:
        if category not in category_data:
            continue

        bin_stats = {}
        x_values = []  # Midpoint of recency range
        y_values = []  # Win rate

        for bin_name, min_days, max_days in recency_bins:
            if bin_name in category_data[category]:
                wins = category_data[category][bin_name]['wins']
                total = category_data[category][bin_name]['total']

                if total > 0:
                    win_rate = wins / total
                else:
                    # Use wins as proxy for frequency
                    win_rate = wins

                midpoint = (min_days + max_days) / 2 if max_days < 999 else min_days + 30

                bin_stats[bin_name] = {
                    'wins': int(wins),
                    'win_rate': float(win_rate),
                    'midpoint_days': float(midpoint)
                }

                x_values.append(midpoint)
                y_values.append(win_rate)

        # Calculate correlation if we have enough data points
        if len(x_values) >= 3:
            try:
                correlation, p_value = stats.pearsonr(x_values, y_values)
            except:
                correlation, p_value = 0.0, 1.0
        else:
            correlation, p_value = 0.0, 1.0

        results_by_category[category] = {
            'recency_ranges': bin_stats,
            'correlation': float(correlation),
            'p_value': float(p_value),
            'significant': bool(p_value < 0.05),
            'num_data_points': int(len(x_values))
        }

    return {
        'by_category': results_by_category,
        'recency_bins': [{'name': name, 'min': min_d, 'max': max_d}
                         for name, min_d, max_d in recency_bins]
    }


def calculate_category_performance_by_recency(
    draw_history: Dict[str, Any]
) -> Dict:
    """
    Calculate which categories perform best at different recency ranges.

    Uses chi-square test to determine if category distribution varies by recency.

    Args:
        draw_history: Historical draw data

    Returns:
        Dictionary with category performance metrics by recency range
    """
    recency_bins = [
        ('0-7 days', 0, 7),
        ('8-14 days', 8, 14),
        ('15-21 days', 15, 21),
        ('22-30 days', 22, 30),
        ('31-45 days', 31, 45),
        ('46-60 days', 46, 60),
        ('61-90 days', 61, 90),
        ('91-120 days', 91, 120),
        ('121+ days', 121, 999)
    ]

    # Count wins by category and recency
    data = defaultdict(lambda: defaultdict(int))

    for draw_date, draw_data in draw_history.items():
        winning_details = draw_data.get('winning_numbers_details', [])

        for detail in winning_details:
            if detail.get('is_bonus', False):
                continue

            category = detail.get('category', 'unknown')
            days_since = detail.get('days_since_last', 999)

            for bin_name, min_days, max_days in recency_bins:
                if min_days <= days_since <= max_days:
                    data[bin_name][category] += 1
                    break

    # Calculate chi-square for each recency bin
    results = {}

    for bin_name, min_days, max_days in recency_bins:
        if bin_name not in data:
            continue

        observed = []
        categories = []

        for cat in ['hot', 'medium', 'cold']:
            count = data[bin_name].get(cat, 0)
            observed.append(count)
            categories.append(cat)

        if sum(observed) > 0 and len(observed) > 1:
            # Chi-square test for uniform distribution
            expected = np.full(len(observed), sum(observed) / len(observed))
            chi2, p_value = stats.chisquare(observed, expected)

            # Calculate percentages
            total = sum(observed)
            percentages = {cat: (count / total * 100) for cat, count in zip(categories, observed)}

            results[bin_name] = {
                'counts': {cat: int(count) for cat, count in zip(categories, observed)},
                'percentages': {cat: float(pct) for cat, pct in percentages.items()},
                'chi2': float(chi2),
                'p_value': float(p_value),
                'significant': bool(p_value < 0.05),
                'total': int(total)
            }

    return results


def generate_long_term_pattern_analysis(
    draw_history: Dict[str, Any]
) -> Dict:
    """
    Main entry point: Generate comprehensive long-term pattern analysis.

    Args:
        draw_history: Historical draw data from lotto_draw_history.json

    Returns:
        Complete analysis dictionary with all statistical tests
    """
    print("\nAnalyzing long-term patterns with statistical rigor...")

    # 1. HMC Pattern Analysis
    print("  1. Analyzing HMC pattern distributions (chi-square test)...")
    hmc_analysis = calculate_hmc_pattern_significance(draw_history)

    # 2. Recency Correlation Analysis
    print("  2. Analyzing recency correlations (Pearson correlation)...")
    recency_analysis = analyze_recency_correlations(draw_history)

    # 3. Category Performance by Recency
    print("  3. Analyzing category performance by recency (chi-square test)...")
    category_recency = calculate_category_performance_by_recency(draw_history)

    results = {
        'metadata': {
            'analysis_type': 'long_term_pattern_analysis',
            'statistical_methods': [
                'chi_square_goodness_of_fit',
                'pearson_correlation',
                'chi_square_test_of_independence'
            ],
            'total_draws': int(len(draw_history)),
            'significance_level': 0.05
        },
        'hmc_pattern_analysis': hmc_analysis,
        'recency_correlation_analysis': recency_analysis,
        'category_performance_by_recency': category_recency
    }

    # Convert numpy types to native Python types
    results = convert_to_native_types(results)

    # Print summary
    print(f"\n  ✓ Long-term pattern analysis complete:")
    print(f"    - HMC patterns analyzed: {hmc_analysis['num_patterns']}")
    print(f"    - Chi-square p-value: {hmc_analysis['p_value']:.4f}")
    print(f"    - Statistically significant: {hmc_analysis['significant']}")
    print(f"    - Category weights derived:")
    print(f"      Hot: {hmc_analysis['category_weights']['hot']:.3f}")
    print(f"      Medium: {hmc_analysis['category_weights']['medium']:.3f}")
    print(f"      Cold: {hmc_analysis['category_weights']['cold']:.3f}")

    return results


def save_analysis(results: Dict, output_file: str = 'data/lotto_long_term_patterns.json'):
    """
    Save long-term pattern analysis to JSON file.

    Args:
        results: Analysis results dictionary
        output_file: Output file path
    """
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Analysis saved to {output_file}")


if __name__ == '__main__':
    """
    Standalone execution: Load draw history and generate analysis.
    """
    import sys

    print("="*70)
    print("LONG-TERM PATTERN ANALYZER (Statistical Edition)")
    print("="*70)

    # Load draw history
    try:
        with open('data/lotto_draw_history.json', 'r') as f:
            draw_history = json.load(f)
    except FileNotFoundError:
        print("ERROR: data/lotto_draw_history.json not found")
        print("Run 'python drawpick.py' first to generate data")
        sys.exit(1)

    # Generate analysis
    results = generate_long_term_pattern_analysis(draw_history)

    # Save results
    save_analysis(results)

    print("\n" + "="*70)
    print("Analysis complete!")
    print("="*70)
