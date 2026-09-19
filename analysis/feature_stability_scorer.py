#!/usr/bin/env python3
"""
Feature Stability Scorer
========================
Measures which features are most stable and reliable over time by analyzing
feature performance across rolling time windows.

This script analyzes:
1. Feature importance over rolling windows
2. Which features are consistently predictive
3. Which features are noisy/unstable
4. Feature correlation stability over time
5. Win rate consistency per feature
6. Recommended "core feature set" for robust models

Usage:
    From project root:
        python analysis/feature_stability_scorer.py

    From analysis folder:
        python feature_stability_scorer.py

Output:
    - data/analysis/lotto_feature_stability.json (full stability analysis)
    - data/analysis/lotto_feature_stability_rankings.csv (ranked features)
    - data/analysis/lotto_core_feature_set.json (recommended stable features)
    - Console output with key findings
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import math

def load_draw_history() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Load draw history JSON and convert to sorted list."""
    try:
        # Try relative path from analysis folder first
        for path in ['../data/lotto_draw_history.json', 'data/lotto_draw_history.json']:
            if Path(path).exists():
                with open(path, 'r') as f:
                    data = json.load(f)

                # Convert to sorted list
                sorted_draws = []
                for date, draw_data in data.items():
                    winning_details = draw_data.get('winning_numbers_details', [])
                    if len(winning_details) >= 7:
                        sorted_draws.append({
                            'date': date,
                            'draw_index': draw_data.get('draw_index', 0),
                            'winning_details': winning_details
                        })

                sorted_draws.sort(key=lambda x: x['draw_index'])
                return data, sorted_draws

        print("ERROR: data/lotto_draw_history.json not found")
        print("Run this script from either the project root or the analysis folder")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        sys.exit(1)


def extract_features_from_draw(winning_details: List[Dict]) -> Dict[int, Dict[str, Any]]:
    """Extract features for all numbers from a draw's winning_numbers_details."""
    features = {}

    for detail in winning_details:
        num = detail['number']

        features[num] = {
            'total_count': detail.get('total_count', 0),
            'days_since_last': detail.get('days_since_last_hit', 0),
            'category': detail.get('category', 'unknown'),
            'freshness_bin': detail.get('current_freshness_bin', 0),
            # Windows are last_4/5/9/24; there is no last_14 (F-7). A missing one must fail.
            'recent_4': detail['recent_counts']['last_4'],
            'recent_9': detail['recent_counts']['last_9'],
            'recent_24': detail['recent_counts']['last_24'],
            'bonus_hit_contribution': detail.get('bonus_hit_contribution', 0.0),
            'is_recent_bonus_hit': detail.get('is_recent_bonus_hit', False)
        }

    return features


def analyze_feature_win_rates_over_time(sorted_draws: List[Dict[str, Any]],
                                        window_size: int = 50) -> Dict[str, List[float]]:
    """
    Calculate win rates for each feature value over rolling windows.

    For each numeric feature, bin into quartiles and track win rate over time.

    Returns:
        Dict mapping feature -> list of win rates over windows
    """
    numeric_features = ['total_count', 'days_since_last', 'recent_4', 'recent_9',
                       'recent_24', 'freshness_bin', 'bonus_hit_contribution']

    feature_win_rates = defaultdict(list)

    # Slide window through draws
    for start_idx in range(0, len(sorted_draws) - window_size, window_size // 2):
        window = sorted_draws[start_idx:start_idx + window_size]

        # For each feature, calculate win rate for high values
        for feat in numeric_features:
            # Collect all values in this window
            values = []
            labels = []

            for draw in window:
                features_dict = extract_features_from_draw(draw['winning_details'])
                main_winners = set([draw['winning_details'][i]['number']
                                   for i in range(min(6, len(draw['winning_details'])))])

                for num, features in features_dict.items():
                    values.append(features[feat])
                    labels.append(1 if num in main_winners else 0)

            # Calculate median
            sorted_vals = sorted(values)
            median = sorted_vals[len(sorted_vals) // 2]

            # Calculate win rate for high values (>= median)
            high_wins = 0
            high_total = 0

            for val, label in zip(values, labels):
                if val >= median:
                    high_total += 1
                    if label == 1:
                        high_wins += 1

            win_rate = high_wins / high_total if high_total > 0 else 0
            feature_win_rates[feat].append(win_rate)

    return dict(feature_win_rates)


def calculate_feature_stability(feature_win_rates: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    """
    Calculate stability metrics for each feature.

    Stability metrics:
    - Mean win rate: Average across windows
    - Std dev: Standard deviation of win rates
    - Coefficient of variation: std / mean (lower = more stable)
    - Stability score: 1 / (1 + CV)
    - Trend: Linear trend over time (positive/negative/flat)
    """
    stability_scores = {}

    for feat, win_rates in feature_win_rates.items():
        if not win_rates:
            continue

        mean = sum(win_rates) / len(win_rates)
        variance = sum((x - mean) ** 2 for x in win_rates) / len(win_rates)
        std = math.sqrt(variance)
        cv = std / mean if mean > 0 else 0
        stability = 1 / (1 + cv)

        # Calculate trend (simple linear regression slope)
        n = len(win_rates)
        x_mean = (n - 1) / 2
        y_mean = mean

        numerator = sum((i - x_mean) * (win_rates[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator > 0 else 0

        # Determine trend direction
        if slope > 0.001:
            trend = 'improving'
        elif slope < -0.001:
            trend = 'declining'
        else:
            trend = 'stable'

        stability_scores[feat] = {
            'mean_win_rate': round(mean, 4),
            'std_dev': round(std, 4),
            'coefficient_variation': round(cv, 3),
            'stability_score': round(stability, 3),
            'trend_slope': round(slope, 6),
            'trend_direction': trend,
            'num_windows': len(win_rates),
            'min_win_rate': round(min(win_rates), 4),
            'max_win_rate': round(max(win_rates), 4),
            'range': round(max(win_rates) - min(win_rates), 4)
        }

    return stability_scores


def analyze_feature_correlations_over_time(sorted_draws: List[Dict[str, Any]],
                                          window_size: int = 100) -> Dict[str, float]:
    """
    Analyze how stable feature correlations are over time.

    For each feature pair, calculate correlation in different windows
    and measure stability of those correlations.

    Returns:
        Dict mapping feature -> correlation_stability_score
    """
    numeric_features = ['total_count', 'days_since_last', 'recent_4', 'recent_9',
                       'recent_24', 'freshness_bin']

    # Calculate correlations in multiple windows
    feature_correlations = defaultdict(lambda: defaultdict(list))

    for start_idx in range(0, len(sorted_draws) - window_size, window_size):
        window = sorted_draws[start_idx:start_idx + window_size]

        # Extract feature values
        feature_values = defaultdict(list)

        for draw in window:
            features_dict = extract_features_from_draw(draw['winning_details'])

            for num, features in features_dict.items():
                for feat in numeric_features:
                    feature_values[feat].append(features[feat])

        # Calculate pairwise correlations
        for i, feat1 in enumerate(numeric_features):
            for feat2 in numeric_features[i+1:]:
                vals1 = feature_values[feat1]
                vals2 = feature_values[feat2]

                # Calculate Pearson correlation
                n = len(vals1)
                mean1 = sum(vals1) / n
                mean2 = sum(vals2) / n

                num = sum((vals1[i] - mean1) * (vals2[i] - mean2) for i in range(n))
                den1 = math.sqrt(sum((x - mean1) ** 2 for x in vals1))
                den2 = math.sqrt(sum((x - mean2) ** 2 for x in vals2))

                corr = num / (den1 * den2) if den1 > 0 and den2 > 0 else 0

                feature_correlations[feat1][feat2].append(corr)

    # Calculate stability of correlations
    correlation_stability = {}

    for feat1 in feature_correlations:
        corr_stabilities = []

        for feat2, corr_list in feature_correlations[feat1].items():
            # Stability = 1 / (1 + std_dev of correlations)
            if len(corr_list) > 1:
                mean_corr = sum(corr_list) / len(corr_list)
                std_corr = math.sqrt(sum((x - mean_corr) ** 2 for x in corr_list) / len(corr_list))
                stability = 1 / (1 + std_corr)
                corr_stabilities.append(stability)

        # Average correlation stability for this feature
        if corr_stabilities:
            correlation_stability[feat1] = round(sum(corr_stabilities) / len(corr_stabilities), 3)
        else:
            correlation_stability[feat1] = 0.5

    return correlation_stability


def identify_noisy_features(stability_scores: Dict[str, Dict[str, float]],
                           threshold: float = 0.5) -> Tuple[List[str], List[str]]:
    """
    Identify stable vs noisy features based on stability scores.

    Args:
        stability_scores: Feature stability metrics
        threshold: Stability score threshold (default 0.5)

    Returns:
        Tuple of (stable_features, noisy_features)
    """
    stable = []
    noisy = []

    for feat, scores in stability_scores.items():
        if scores['stability_score'] >= threshold:
            stable.append(feat)
        else:
            noisy.append(feat)

    # Sort by stability score
    stable.sort(key=lambda x: stability_scores[x]['stability_score'], reverse=True)
    noisy.sort(key=lambda x: stability_scores[x]['stability_score'])

    return stable, noisy


def recommend_core_feature_set(stability_scores: Dict[str, Dict[str, float]],
                              correlation_stability: Dict[str, float],
                              min_features: int = 3,
                              max_features: int = 8) -> List[Dict[str, Any]]:
    """
    Recommend a core set of stable features for robust models.

    Selection criteria:
    1. High stability score (>0.6)
    2. High correlation stability (>0.7)
    3. Improving or stable trend
    4. Good mean win rate (>0.14, which is baseline 6/47)

    Returns:
        List of recommended features with justification
    """
    candidates = []

    baseline_win_rate = 6 / 47  # Random chance for main numbers

    for feat, scores in stability_scores.items():
        # Calculate composite score
        stability_component = scores['stability_score']
        correlation_component = correlation_stability.get(feat, 0.5)
        win_rate_component = max(0, (scores['mean_win_rate'] - baseline_win_rate) / baseline_win_rate)

        # Trend bonus
        trend_bonus = 0
        if scores['trend_direction'] == 'improving':
            trend_bonus = 0.1
        elif scores['trend_direction'] == 'stable':
            trend_bonus = 0.05

        composite_score = (stability_component * 0.4 +
                          correlation_component * 0.3 +
                          win_rate_component * 0.2 +
                          trend_bonus)

        candidates.append({
            'feature': feat,
            'stability_score': scores['stability_score'],
            'correlation_stability': correlation_component,
            'mean_win_rate': scores['mean_win_rate'],
            'trend': scores['trend_direction'],
            'composite_score': round(composite_score, 3),
            'recommendation': 'core' if composite_score > 0.5 else 'optional'
        })

    # Sort by composite score
    candidates.sort(key=lambda x: x['composite_score'], reverse=True)

    # Select top features
    core_features = [c for c in candidates if c['composite_score'] > 0.5][:max_features]

    # Ensure minimum features
    if len(core_features) < min_features:
        core_features = candidates[:min_features]

    return core_features


def save_outputs(stability_scores: Dict, correlation_stability: Dict,
                stable_features: List[str], noisy_features: List[str],
                core_feature_set: List[Dict], feature_win_rates: Dict):
    """Save all outputs to files."""

    # Full JSON
    output_data = {
        'metadata': {
            'analysis_type': 'feature_stability_analysis',
            'total_features_analyzed': len(stability_scores),
            'stable_features_count': len(stable_features),
            'noisy_features_count': len(noisy_features),
            'core_feature_set_size': len(core_feature_set)
        },
        'feature_stability_scores': stability_scores,
        'correlation_stability_scores': correlation_stability,
        'stable_features': stable_features,
        'noisy_features': noisy_features,
        'core_feature_set': core_feature_set,
        'feature_win_rates_over_time': feature_win_rates
    }

    for path in ['../data/analysis/lotto_feature_stability.json', 'data/analysis/lotto_feature_stability.json']:
        try:
            with open(path, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"✓ Full analysis saved to {path}")
            break
        except:
            continue

    # CSV rankings
    for path in ['../data/analysis/lotto_feature_stability_rankings.csv', 'data/analysis/lotto_feature_stability_rankings.csv']:
        try:
            with open(path, 'w') as f:
                f.write("Rank,Feature,Stability_Score,Mean_Win_Rate,CV,Trend,Corr_Stability,Category\n")

                # Combine and rank all features
                all_features = []
                for feat, scores in stability_scores.items():
                    all_features.append({
                        'feature': feat,
                        'stability': scores['stability_score'],
                        'mean_win_rate': scores['mean_win_rate'],
                        'cv': scores['coefficient_variation'],
                        'trend': scores['trend_direction'],
                        'corr_stability': correlation_stability.get(feat, 0.5),
                        'category': 'stable' if feat in stable_features else 'noisy'
                    })

                all_features.sort(key=lambda x: x['stability'], reverse=True)

                for rank, item in enumerate(all_features, 1):
                    f.write(f"{rank},{item['feature']},{item['stability']:.3f},"
                           f"{item['mean_win_rate']:.4f},{item['cv']:.3f},"
                           f"{item['trend']},{item['corr_stability']:.3f},{item['category']}\n")

            print(f"✓ Feature rankings saved to {path}")
            break
        except:
            continue

    # Core feature set JSON
    for path in ['../data/analysis/lotto_core_feature_set.json', 'data/analysis/lotto_core_feature_set.json']:
        try:
            with open(path, 'w') as f:
                json.dump({
                    'core_features': [feat['feature'] for feat in core_feature_set],
                    'detailed_recommendations': core_feature_set,
                    'usage_notes': 'Use these stable features for robust ML models that generalize well over time'
                }, f, indent=2)
            print(f"✓ Core feature set saved to {path}")
            break
        except:
            continue


def print_results(stability_scores: Dict, correlation_stability: Dict,
                 stable_features: List[str], noisy_features: List[str],
                 core_feature_set: List[Dict]):
    """Print comprehensive results."""

    print("\n" + "=" * 80)
    print("FEATURE STABILITY ANALYSIS")
    print("=" * 80)

    print(f"\nOVERALL STATISTICS:")
    print(f"  Total features analyzed: {len(stability_scores)}")
    print(f"  Stable features (stability > 0.5): {len(stable_features)}")
    print(f"  Noisy features (stability < 0.5): {len(noisy_features)}")
    print(f"  Core feature set size: {len(core_feature_set)}")

    print("\n" + "-" * 80)
    print("TOP 10 MOST STABLE FEATURES")
    print("-" * 80)
    print(f"{'Rank':<6} {'Feature':<20} {'Stability':<12} {'Mean Win Rate':<15} "
          f"{'CV':<8} {'Trend':<12}")
    print("-" * 80)

    sorted_features = sorted(stability_scores.items(),
                           key=lambda x: x[1]['stability_score'], reverse=True)

    for rank, (feat, scores) in enumerate(sorted_features[:10], 1):
        print(f"{rank:<6} {feat:<20} {scores['stability_score']:<12.3f} "
              f"{scores['mean_win_rate']:<15.4f} {scores['coefficient_variation']:<8.3f} "
              f"{scores['trend_direction']:<12}")

    print("\n" + "-" * 80)
    print("MOST NOISY/UNSTABLE FEATURES")
    print("-" * 80)
    print(f"{'Rank':<6} {'Feature':<20} {'Stability':<12} {'CV':<8} {'Range':<10}")
    print("-" * 80)

    for rank, (feat, scores) in enumerate(sorted_features[-5:], 1):
        print(f"{rank:<6} {feat:<20} {scores['stability_score']:<12.3f} "
              f"{scores['coefficient_variation']:<8.3f} {scores['range']:<10.4f}")

    print("\n" + "-" * 80)
    print("CORRELATION STABILITY SCORES")
    print("-" * 80)
    print(f"{'Feature':<20} {'Correlation Stability':<25} {'Interpretation':<20}")
    print("-" * 80)

    sorted_corr = sorted(correlation_stability.items(), key=lambda x: x[1], reverse=True)

    for feat, stability in sorted_corr:
        interpretation = (
            "Very stable" if stability > 0.8 else
            "Stable" if stability > 0.6 else
            "Moderate" if stability > 0.4 else
            "Unstable"
        )
        print(f"{feat:<20} {stability:<25.3f} {interpretation:<20}")

    print("\n" + "-" * 80)
    print("RECOMMENDED CORE FEATURE SET")
    print("-" * 80)
    print(f"{'Rank':<6} {'Feature':<20} {'Composite':<12} {'Stability':<12} "
          f"{'Win Rate':<12} {'Trend':<12}")
    print("-" * 80)

    for rank, feat_info in enumerate(core_feature_set, 1):
        print(f"{rank:<6} {feat_info['feature']:<20} {feat_info['composite_score']:<12.3f} "
              f"{feat_info['stability_score']:<12.3f} {feat_info['mean_win_rate']:<12.4f} "
              f"{feat_info['trend']:<12}")

    print("\n" + "=" * 80)
    print("INTERPRETATION GUIDE")
    print("=" * 80)
    print("Stability Score: 1 / (1 + CV) where CV = std_dev / mean")
    print("  - >0.7:  Very stable - highly recommended")
    print("  - 0.5-0.7:  Stable - good for robust models")
    print("  - 0.3-0.5:  Moderately stable - use with caution")
    print("  - <0.3:  Unstable - avoid in production models")
    print("\nCoefficient of Variation (CV): std_dev / mean")
    print("  - <0.2:  Very consistent")
    print("  - 0.2-0.5:  Moderately consistent")
    print("  - >0.5:  Highly variable")
    print("\nTrend Direction:")
    print("  - Improving: Feature becoming more predictive over time")
    print("  - Stable: Feature maintains consistent predictiveness")
    print("  - Declining: Feature losing predictive power")
    print("\nCorrelation Stability: How consistent feature correlations are over time")
    print("  - >0.8:  Very stable relationships with other features")
    print("  - 0.6-0.8:  Stable relationships")
    print("  - <0.6:  Unstable relationships")
    print("=" * 80)


def main():
    """Main execution function."""
    print("Loading draw history...")
    full_history, sorted_draws = load_draw_history()
    print(f"✓ Loaded {len(sorted_draws)} draws")

    print("\n1. Analyzing feature win rates over rolling windows...")
    feature_win_rates = analyze_feature_win_rates_over_time(sorted_draws, window_size=50)
    total_windows = len(next(iter(feature_win_rates.values())))
    print(f"✓ Analyzed {len(feature_win_rates)} features across {total_windows} time windows")

    print("\n2. Calculating feature stability scores...")
    stability_scores = calculate_feature_stability(feature_win_rates)
    print(f"✓ Calculated stability metrics for {len(stability_scores)} features")

    print("\n3. Analyzing feature correlation stability...")
    correlation_stability = analyze_feature_correlations_over_time(sorted_draws, window_size=100)
    print(f"✓ Analyzed correlation stability for {len(correlation_stability)} features")

    print("\n4. Identifying stable vs noisy features...")
    stable_features, noisy_features = identify_noisy_features(stability_scores, threshold=0.5)
    print(f"✓ Identified {len(stable_features)} stable and {len(noisy_features)} noisy features")

    print("\n5. Recommending core feature set...")
    core_feature_set = recommend_core_feature_set(
        stability_scores, correlation_stability, min_features=3, max_features=8
    )
    print(f"✓ Recommended {len(core_feature_set)} core features for robust models")

    print("\n6. Saving outputs...")
    save_outputs(stability_scores, correlation_stability, stable_features,
                noisy_features, core_feature_set, feature_win_rates)

    # Print results
    print_results(stability_scores, correlation_stability, stable_features,
                 noisy_features, core_feature_set)


if __name__ == "__main__":
    main()
