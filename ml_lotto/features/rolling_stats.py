"""
rolling_stats.py
================
Compute rolling statistics features for lottery numbers.

These features capture temporal patterns and trends over different time windows.
"""

import numpy as np
from typing import Dict, Any, List
from collections import defaultdict


def calculate_rolling_statistics(
    all_draws: List[Dict[str, Any]],
    number: int,
    current_draw_idx: int,
    windows: List[int] = [10, 20, 50]
) -> Dict[str, float]:
    """
    Calculate rolling statistics for a specific number up to current draw.

    Args:
        all_draws: List of all historical draws
        number: The lottery number (1-47)
        current_draw_idx: Index of current draw (features calculated before this draw)
        windows: List of window sizes for rolling calculations

    Returns:
        Dictionary of rolling statistics features
    """
    features = {}

    # Get appearance history for this number up to (not including) current draw
    appearances = []
    gaps = []
    last_appearance_idx = None

    for idx in range(current_draw_idx):
        draw = all_draws[idx]
        if number in draw['numbers']:
            appearances.append(idx)
            if last_appearance_idx is not None:
                gaps.append(idx - last_appearance_idx)
            last_appearance_idx = idx

    # If number never appeared, return zero features
    if len(appearances) == 0:
        for window in windows:
            features[f'rolling_rate_{window}'] = 0.0
            features[f'rolling_trend_{window}'] = 0.0
        features['gap_variance'] = 0.0
        features['gap_cv'] = 0.0
        features['appearance_acceleration'] = 0.0
        return features

    # Calculate rolling appearance rates for each window
    for window in windows:
        if current_draw_idx >= window:
            # Count appearances in last N draws
            recent_draws = list(range(current_draw_idx - window, current_draw_idx))
            recent_appearances = [idx for idx in appearances if idx in recent_draws]
            appearance_rate = len(recent_appearances) / window
            features[f'rolling_rate_{window}'] = appearance_rate

            # Calculate trend (recent half vs older half)
            half_window = window // 2
            if current_draw_idx >= window:
                recent_half_start = current_draw_idx - half_window
                older_half_start = current_draw_idx - window
                older_half_end = current_draw_idx - half_window

                recent_half_count = len([idx for idx in appearances
                                        if recent_half_start <= idx < current_draw_idx])
                older_half_count = len([idx for idx in appearances
                                       if older_half_start <= idx < older_half_end])

                recent_half_rate = recent_half_count / half_window
                older_half_rate = older_half_count / half_window

                # Trend: positive means increasing frequency
                trend = recent_half_rate - older_half_rate
                features[f'rolling_trend_{window}'] = trend
            else:
                features[f'rolling_trend_{window}'] = 0.0
        else:
            features[f'rolling_rate_{window}'] = 0.0
            features[f'rolling_trend_{window}'] = 0.0

    # Calculate gap statistics (variance and coefficient of variation)
    if len(gaps) > 1:
        gap_mean = np.mean(gaps)
        gap_variance = np.var(gaps)
        gap_std = np.std(gaps)
        gap_cv = gap_std / gap_mean if gap_mean > 0 else 0.0

        features['gap_variance'] = gap_variance
        features['gap_cv'] = gap_cv  # Coefficient of variation (normalized volatility)
    else:
        features['gap_variance'] = 0.0
        features['gap_cv'] = 0.0

    # Calculate appearance acceleration (change in trend)
    # Compare last 10 draws vs previous 10 draws
    if current_draw_idx >= 20:
        last_10_start = current_draw_idx - 10
        prev_10_start = current_draw_idx - 20
        prev_10_end = current_draw_idx - 10

        last_10_count = len([idx for idx in appearances if last_10_start <= idx < current_draw_idx])
        prev_10_count = len([idx for idx in appearances if prev_10_start <= idx < prev_10_end])

        acceleration = (last_10_count - prev_10_count) / 10.0
        features['appearance_acceleration'] = acceleration
    else:
        features['appearance_acceleration'] = 0.0

    return features


def extract_rolling_features_for_all_numbers(
    all_draws: List[Dict[str, Any]],
    training_start_draw: int = 100,
    max_number: int = 47
) -> Dict[int, Dict[str, float]]:
    """
    Extract rolling statistics features for all numbers.

    Args:
        all_draws: List of all historical draws
        training_start_draw: Index where training starts
        max_number: Maximum lottery number (default: 47)

    Returns:
        Dictionary mapping number -> rolling features dict
    """
    print(f"  Calculating rolling statistics features...")

    rolling_features = {}

    # Calculate features for each number at the training start point
    for num in range(1, max_number + 1):
        rolling_features[num] = calculate_rolling_statistics(
            all_draws,
            num,
            current_draw_idx=training_start_draw,
            windows=[10, 20, 50]
        )

    print(f"  ✓ Rolling statistics calculated for {len(rolling_features)} numbers")

    return rolling_features
