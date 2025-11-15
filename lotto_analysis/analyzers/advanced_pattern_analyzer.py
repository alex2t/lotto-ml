"""
Advanced Pattern Analyzer
==========================
Generates volatility, trend, and temporal features for improved ML prediction.

Features Generated:
1. Volatility: appearance_volatility, gap_consistency_score, max_gap_ratio
2. Trend: appearance_trend, appearance_acceleration
3. Temporal: draws_since_last (not days, but actual draw count)
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List
import numpy as np
import json


def calculate_volatility_features(
    draw_history: Dict[str, Any],
    max_number: int
) -> Dict[int, Dict[str, float]]:
    """
    Calculate appearance volatility features for each number.

    Volatility measures how predictable a number's appearance timing is:
    - Low volatility (CV < 0.5): Consistent, predictable timing
    - Medium volatility (CV 0.5-1.0): Moderate variation
    - High volatility (CV > 1.0): Unpredictable, erratic timing

    Args:
        draw_history: Historical draw data
        max_number: Maximum lottery number

    Returns:
        Dict mapping number -> volatility features
    """
    print("  Calculating volatility features...")

    # Track appearances with dates for each number
    number_appearances = defaultdict(list)
    sorted_draws = sorted(draw_history.items())

    for draw_date, draw_data in sorted_draws:
        for detail in draw_data.get('winning_numbers_details', []):
            if not detail.get('is_bonus', False):
                number_appearances[detail['number']].append(draw_date)

    volatility_features = {}

    for num in range(1, max_number + 1):
        dates = number_appearances.get(num, [])

        if len(dates) < 3:
            # Not enough data for meaningful volatility calculation
            volatility_features[num] = {
                'appearance_volatility': 1.0,  # Default: medium volatility
                'gap_consistency_score': 0.5,
                'max_gap_ratio': 2.0,
                'appearance_count': len(dates)
            }
            continue

        # Calculate gaps between consecutive appearances
        date_objs = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
        gaps = [(date_objs[i+1] - date_objs[i]).days for i in range(len(date_objs)-1)]

        # Volatility metrics
        avg_gap = np.mean(gaps)
        std_gap = np.std(gaps)

        # Coefficient of variation (CV) - key volatility metric
        appearance_volatility = std_gap / avg_gap if avg_gap > 0 else 1.0

        # Consistency score (inverse of volatility, bounded 0-1)
        gap_consistency_score = 1.0 / (1.0 + appearance_volatility)

        # Max gap ratio (how much larger is the longest gap vs average?)
        max_gap = max(gaps)
        max_gap_ratio = max_gap / avg_gap if avg_gap > 0 else 1.0

        volatility_features[num] = {
            'appearance_volatility': float(appearance_volatility),
            'gap_consistency_score': float(gap_consistency_score),
            'max_gap_ratio': float(max_gap_ratio),
            'appearance_count': len(dates),
            'avg_gap_days': float(avg_gap),
            'std_gap_days': float(std_gap)
        }

    return volatility_features


def calculate_trend_features(
    draw_history: Dict[str, Any],
    max_number: int,
    recent_window: int = 50,
    very_recent_window: int = 25
) -> Dict[int, Dict[str, float]]:
    """
    Calculate trend/momentum features for each number.

    Trend features capture if a number is "heating up" or "cooling down":
    - appearance_trend: Recent vs previous frequency change
    - appearance_acceleration: Very recent vs recent change

    Args:
        draw_history: Historical draw data
        max_number: Maximum lottery number
        recent_window: Window for "recent" period (default 50 draws)
        very_recent_window: Window for "very recent" period (default 25 draws)

    Returns:
        Dict mapping number -> trend features
    """
    print("  Calculating trend features...")

    sorted_draws = sorted(draw_history.items())
    total_draws = len(sorted_draws)

    # Define time windows
    very_recent_draws = sorted_draws[-very_recent_window:] if total_draws >= very_recent_window else sorted_draws
    recent_draws = sorted_draws[-recent_window:] if total_draws >= recent_window else sorted_draws
    older_draws = sorted_draws[-2*recent_window:-recent_window] if total_draws >= 2*recent_window else []

    # Count appearances in each window
    very_recent_counts = defaultdict(int)
    recent_counts = defaultdict(int)
    older_counts = defaultdict(int)

    for draw_date, draw_data in very_recent_draws:
        for detail in draw_data.get('winning_numbers_details', []):
            if not detail.get('is_bonus', False):
                very_recent_counts[detail['number']] += 1

    for draw_date, draw_data in recent_draws:
        for detail in draw_data.get('winning_numbers_details', []):
            if not detail.get('is_bonus', False):
                recent_counts[detail['number']] += 1

    for draw_date, draw_data in older_draws:
        for detail in draw_data.get('winning_numbers_details', []):
            if not detail.get('is_bonus', False):
                older_counts[detail['number']] += 1

    trend_features = {}

    for num in range(1, max_number + 1):
        recent = recent_counts.get(num, 0)
        older = older_counts.get(num, 0)
        very_recent = very_recent_counts.get(num, 0)

        # Calculate baseline (expected frequency based on total history)
        total_appearances = sum(1 for _, draw_data in sorted_draws
                               for detail in draw_data.get('winning_numbers_details', [])
                               if detail['number'] == num and not detail.get('is_bonus', False))
        baseline_rate = total_appearances / total_draws if total_draws > 0 else 0

        # Trend: recent vs older (positive = trending up, negative = trending down)
        if older > 0:
            appearance_trend = (recent - older) / older
        elif recent > 0:
            appearance_trend = 1.0  # Appeared recently but not before
        else:
            appearance_trend = 0.0  # Never appeared

        # Acceleration: very recent vs recent (captures if trend is accelerating)
        recent_rate = recent / recent_window if recent_window > 0 else 0
        very_recent_rate = very_recent / very_recent_window if very_recent_window > 0 else 0

        if recent_rate > 0:
            appearance_acceleration = (very_recent_rate - recent_rate) / recent_rate
        elif very_recent_rate > 0:
            appearance_acceleration = 1.0
        else:
            appearance_acceleration = 0.0

        # Normalized recent frequency vs baseline
        recent_vs_baseline = (recent / recent_window) / baseline_rate if baseline_rate > 0 else 1.0

        trend_features[num] = {
            'appearance_trend': float(appearance_trend),
            'appearance_acceleration': float(appearance_acceleration),
            'recent_vs_baseline': float(recent_vs_baseline),
            'recent_count': int(recent),
            'older_count': int(older),
            'very_recent_count': int(very_recent)
        }

    return trend_features


def generate_advanced_pattern_analysis(
    draw_history: Dict[str, Any],
    max_number: int = 47
) -> Dict[str, Any]:
    """
    Main entry point: Generate advanced pattern features.

    Args:
        draw_history: Historical draw data from lotto_draw_history.json
        max_number: Maximum lottery number

    Returns:
        Complete analysis dictionary with volatility and trend features
    """
    print("\nGenerating advanced pattern features...")

    # Calculate volatility features
    volatility_features = calculate_volatility_features(draw_history, max_number)

    # Calculate trend features
    trend_features = calculate_trend_features(draw_history, max_number)

    # Combine per-number features
    per_number_features = {}
    for num in range(1, max_number + 1):
        per_number_features[num] = {
            **volatility_features[num],
            **trend_features[num]
        }

    # Calculate summary statistics
    all_volatilities = [f['appearance_volatility'] for f in volatility_features.values()]
    all_trends = [f['appearance_trend'] for f in trend_features.values()]

    results = {
        'metadata': {
            'analysis_type': 'advanced_pattern_features',
            'feature_types': ['volatility', 'trend', 'temporal'],
            'total_numbers': max_number,
            'total_draws': len(draw_history)
        },
        'summary_statistics': {
            'volatility': {
                'mean': float(np.mean(all_volatilities)),
                'std': float(np.std(all_volatilities)),
                'min': float(np.min(all_volatilities)),
                'max': float(np.max(all_volatilities))
            },
            'trend': {
                'mean': float(np.mean(all_trends)),
                'std': float(np.std(all_trends)),
                'min': float(np.min(all_trends)),
                'max': float(np.max(all_trends)),
                'trending_up_count': int(sum(1 for t in all_trends if t > 0.2)),
                'trending_down_count': int(sum(1 for t in all_trends if t < -0.2))
            }
        },
        'per_number_features': per_number_features
    }

    print(f"  ✓ Volatility features calculated for {max_number} numbers")
    print(f"     Mean volatility (CV): {results['summary_statistics']['volatility']['mean']:.2f}")
    print(f"     Range: {results['summary_statistics']['volatility']['min']:.2f} - {results['summary_statistics']['volatility']['max']:.2f}")

    print(f"  ✓ Trend features calculated for {max_number} numbers")
    print(f"     Trending up: {results['summary_statistics']['trend']['trending_up_count']} numbers")
    print(f"     Trending down: {results['summary_statistics']['trend']['trending_down_count']} numbers")

    return results


def save_analysis(results: Dict, output_file: str = 'data/lotto_advanced_patterns.json'):
    """
    Save advanced pattern analysis to JSON file.

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
    print("ADVANCED PATTERN ANALYZER")
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
    results = generate_advanced_pattern_analysis(draw_history)

    # Save results
    save_analysis(results)

    print("\n" + "="*70)
    print("Analysis complete!")
    print("="*70)
