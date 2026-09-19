"""
Advanced Pattern Analyzer
==========================
Generates volatility, trend, and temporal features for improved ML prediction.

Features Generated:
1. Volatility: appearance_volatility, gap_consistency_score, max_gap_ratio
2. Trend: appearance_trend, appearance_acceleration
3. Temporal: draws_since_last (not days, but actual draw count)
4. SCIPY ENHANCED: Detrending, smoothing, regime shift detection, trend significance

Version: 2.0 (Scipy Time Series Edition)
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Tuple
import numpy as np
import json

# Try to import scipy for advanced time series analysis
try:
    from scipy.signal import savgol_filter, detrend, find_peaks
    from scipy.stats import fisher_exact
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("⚠️  scipy not available - using basic time series analysis")


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

        # SCIPY ENHANCEMENT: Detrend gaps before calculating volatility
        # This removes long-term trends to get true volatility measure
        if HAS_SCIPY and len(gaps) >= 5:
            # Remove linear trend from gaps
            detrended_gaps = detrend(gaps)

            # Calculate volatility on detrended data (more accurate)
            std_detrended = np.std(detrended_gaps)
            avg_gap = np.mean(gaps)
            std_gap = np.std(gaps)

            # Detrended volatility (better for numbers with changing patterns)
            appearance_volatility_detrended = std_detrended / avg_gap if avg_gap > 0 else 1.0

            # Original volatility (for comparison)
            appearance_volatility = std_gap / avg_gap if avg_gap > 0 else 1.0
        else:
            # Fallback to basic calculation
            avg_gap = np.mean(gaps)
            std_gap = np.std(gaps)
            appearance_volatility = std_gap / avg_gap if avg_gap > 0 else 1.0
            appearance_volatility_detrended = appearance_volatility

        # Consistency score (inverse of volatility, bounded 0-1)
        # Use detrended volatility for more accurate consistency measure
        gap_consistency_score = 1.0 / (1.0 + appearance_volatility_detrended)

        # Max gap ratio (how much larger is the longest gap vs average?)
        max_gap = max(gaps)
        max_gap_ratio = max_gap / avg_gap if avg_gap > 0 else 1.0

        volatility_features[num] = {
            'appearance_volatility': float(appearance_volatility_detrended),  # SCIPY: use detrended
            'appearance_volatility_raw': float(appearance_volatility),  # Keep original for comparison
            'gap_consistency_score': float(gap_consistency_score),
            'max_gap_ratio': float(max_gap_ratio),
            'appearance_count': len(dates),
            'avg_gap_days': float(avg_gap),
            'std_gap_days': float(std_gap)
        }

    return volatility_features


def build_appearance_time_series(
    draw_history: Dict[str, Any],
    number: int,
    window_size: int = 10
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build a time series of appearance frequency for a specific number.

    Args:
        draw_history: Historical draw data
        number: Number to track
        window_size: Rolling window size for frequency calculation

    Returns:
        Tuple of (draw_indices, appearance_frequencies)
    """
    sorted_draws = sorted(draw_history.items())

    # Create binary series (1 if number appeared, 0 if not)
    appearances = []
    for _, draw_data in sorted_draws:
        appeared = any(
            detail['number'] == number and not detail.get('is_bonus', False)
            for detail in draw_data.get('winning_numbers_details', [])
        )
        appearances.append(1 if appeared else 0)

    # Calculate rolling frequency
    frequencies = []
    for i in range(len(appearances)):
        start_idx = max(0, i - window_size + 1)
        window_data = appearances[start_idx:i+1]
        freq = sum(window_data) / len(window_data) if window_data else 0
        frequencies.append(freq)

    return np.arange(len(appearances)), np.array(frequencies)


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
    - SCIPY: Smoothed trend detection and significance testing

    Args:
        draw_history: Historical draw data
        max_number: Maximum lottery number
        recent_window: Window for "recent" period (default 50 draws)
        very_recent_window: Window for "very recent" period (default 25 draws)

    Returns:
        Dict mapping number -> trend features
    """
    print("  Calculating trend features...")
    if HAS_SCIPY:
        print("    (using scipy smoothing for noise reduction)")

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

        # SCIPY ENHANCEMENT: Smoothed trend detection using time series
        if HAS_SCIPY and total_draws >= 30:
            # Build time series for this number
            _, frequencies = build_appearance_time_series(draw_history, num, window_size=10)

            if len(frequencies) >= 30:
                # Apply Savitzky-Golay filter to smooth noisy time series
                # This reduces noise while preserving trend shape
                window_length = min(21, len(frequencies) if len(frequencies) % 2 == 1 else len(frequencies) - 1)
                if window_length >= 5:
                    smoothed_freq = savgol_filter(frequencies, window_length=window_length, polyorder=3)

                    # Calculate smoothed trend (slope of recent vs older)
                    recent_smooth_avg = np.mean(smoothed_freq[-recent_window:]) if len(smoothed_freq) >= recent_window else np.mean(smoothed_freq)
                    older_smooth_avg = np.mean(smoothed_freq[-2*recent_window:-recent_window]) if len(smoothed_freq) >= 2*recent_window else recent_smooth_avg

                    if older_smooth_avg > 0:
                        smoothed_trend = (recent_smooth_avg - older_smooth_avg) / older_smooth_avg
                    else:
                        smoothed_trend = appearance_trend

                    # Significance of recent vs older on the raw per-draw counts (F-31). The smoothed
                    # rolling series shares most of its data between neighbouring points, so a test on
                    # it flagged most numbers even on fair draws.
                    trend_significant = bool(older_draws) and fisher_exact(
                        [[recent, len(recent_draws) - recent], [older, len(older_draws) - older]]
                    ).pvalue < 0.05
                else:
                    smoothed_trend = appearance_trend
                    trend_significant = False
            else:
                smoothed_trend = appearance_trend
                trend_significant = False
        else:
            smoothed_trend = appearance_trend
            trend_significant = False

        trend_features[num] = {
            'appearance_trend': float(smoothed_trend if HAS_SCIPY and total_draws >= 30 else appearance_trend),  # SCIPY: use smoothed
            'appearance_trend_raw': float(appearance_trend),  # Keep original
            'appearance_acceleration': float(appearance_acceleration),
            'recent_vs_baseline': float(recent_vs_baseline),
            'trend_is_significant': bool(trend_significant),  # SCIPY: statistical significance
            'recent_count': int(recent),
            'older_count': int(older),
            'very_recent_count': int(very_recent)
        }

    return trend_features


def detect_regime_shifts(
    draw_history: Dict[str, Any],
    max_number: int
) -> Dict[int, Dict[str, Any]]:
    """
    Detect regime shifts (changes in behavior patterns) using peak detection.

    A regime shift occurs when a number transitions from one behavior pattern
    to another (e.g., from cold to hot, or vice versa).

    SCIPY ENHANCEMENT: Uses find_peaks() to detect significant changes in frequency.

    Args:
        draw_history: Historical draw data
        max_number: Maximum lottery number

    Returns:
        Dict mapping number -> regime shift features
    """
    print("  Detecting regime shifts...")
    if not HAS_SCIPY:
        print("    (scipy not available - skipping regime shift detection)")
        return {num: {'regime_shifts_detected': 0, 'in_regime_shift': False} for num in range(1, max_number + 1)}

    sorted_draws = sorted(draw_history.items())
    total_draws = len(sorted_draws)

    if total_draws < 50:
        return {num: {'regime_shifts_detected': 0, 'in_regime_shift': False} for num in range(1, max_number + 1)}

    regime_features = {}

    for num in range(1, max_number + 1):
        # Build smoothed frequency time series
        _, frequencies = build_appearance_time_series(draw_history, num, window_size=10)

        if len(frequencies) < 30:
            regime_features[num] = {
                'regime_shifts_detected': 0,
                'in_regime_shift': False,
                'last_peak_distance': 0,
                'last_trough_distance': 0
            }
            continue

        # Smooth the time series
        window_length = min(21, len(frequencies) if len(frequencies) % 2 == 1 else len(frequencies) - 1)
        if window_length < 5:
            regime_features[num] = {
                'regime_shifts_detected': 0,
                'in_regime_shift': False,
                'last_peak_distance': 0,
                'last_trough_distance': 0
            }
            continue

        smoothed = savgol_filter(frequencies, window_length=window_length, polyorder=3)

        # Detect peaks (regime highs) and troughs (regime lows)
        peaks, peak_properties = find_peaks(smoothed, distance=15, prominence=0.05)
        troughs, trough_properties = find_peaks(-smoothed, distance=15, prominence=0.05)

        # Count total regime shifts (peaks + troughs)
        total_shifts = len(peaks) + len(troughs)

        # Check if currently in a regime shift
        # (defined as being within 10 draws of a recent peak or trough)
        recent_shift_window = 10
        last_peak_distance = (len(smoothed) - peaks[-1]) if len(peaks) > 0 else 999
        last_trough_distance = (len(smoothed) - troughs[-1]) if len(troughs) > 0 else 999

        in_regime_shift = (last_peak_distance <= recent_shift_window or
                          last_trough_distance <= recent_shift_window)

        regime_features[num] = {
            'regime_shifts_detected': int(total_shifts),
            'in_regime_shift': bool(in_regime_shift),
            'last_peak_distance': int(last_peak_distance),
            'last_trough_distance': int(last_trough_distance),
            'peak_count': int(len(peaks)),
            'trough_count': int(len(troughs))
        }

    shifts_detected = sum(1 for f in regime_features.values() if f['regime_shifts_detected'] > 0)
    currently_shifting = sum(1 for f in regime_features.values() if f['in_regime_shift'])

    print(f"    ✓ {shifts_detected}/{max_number} numbers show regime shifts")
    print(f"    ✓ {currently_shifting}/{max_number} numbers currently in regime shift")

    return regime_features


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
    if HAS_SCIPY:
        print("  (SCIPY TIME SERIES ANALYSIS ENABLED)")

    # Calculate volatility features
    volatility_features = calculate_volatility_features(draw_history, max_number)

    # Calculate trend features
    trend_features = calculate_trend_features(draw_history, max_number)

    # SCIPY: Detect regime shifts
    regime_features = detect_regime_shifts(draw_history, max_number)

    # Combine per-number features
    per_number_features = {}
    for num in range(1, max_number + 1):
        per_number_features[num] = {
            **volatility_features[num],
            **trend_features[num],
            **regime_features[num]
        }

    # Calculate summary statistics
    all_volatilities = [f['appearance_volatility'] for f in volatility_features.values()]
    all_trends = [f['appearance_trend'] for f in trend_features.values()]

    # Count scipy enhancements
    significant_trends = sum(1 for f in trend_features.values() if f.get('trend_is_significant', False))
    numbers_in_regime_shift = sum(1 for f in regime_features.values() if f.get('in_regime_shift', False))

    results = {
        'metadata': {
            'analysis_type': 'advanced_pattern_features',
            'feature_types': ['volatility', 'trend', 'temporal', 'regime_shifts'],
            'scipy_enhanced': HAS_SCIPY,
            'total_numbers': max_number,
            'total_draws': len(draw_history),
            'enhancements': {
                'detrended_volatility': HAS_SCIPY,
                'smoothed_trends': HAS_SCIPY,
                'trend_significance_testing': HAS_SCIPY,
                'regime_shift_detection': HAS_SCIPY
            }
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
                'trending_down_count': int(sum(1 for t in all_trends if t < -0.2)),
                'statistically_significant_trends': int(significant_trends)
            },
            'regime_shifts': {
                'numbers_in_shift': int(numbers_in_regime_shift),
                'total_shifts_detected': int(sum(f.get('regime_shifts_detected', 0) for f in regime_features.values()))
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
    if HAS_SCIPY:
        print(f"     Statistically significant trends: {significant_trends} numbers")
        print(f"  ✓ Regime shift analysis: {numbers_in_regime_shift} numbers currently shifting")

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
