"""
Lottery Trend Discovery Analyzer
=================================

Purpose: Detect long-term trends and regime shifts in lottery data
         to identify potential new ML features.

Input: lotto_draw_history.json
Output: Statistical analysis + feature recommendations

Usage:
    python trend_analyzer.py
"""

import json
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
from datetime import datetime
import matplotlib.pyplot as plt

# Configuration
DRAW_HISTORY_JSON = '../data/lotto_draw_history.json'
ANALYSIS_WINDOWS = [50, 100, 150, 200]  # Different lookback windows
TOTAL_COUNT_BINS = [(60, 70), (70, 80), (80, 90), (90, 100)]
DAYS_SINCE_BINS = [(0, 14), (14, 30), (30, 60), (60, 120), (120, 999)]


def load_draw_history(filename: str) -> List[Dict]:
    """Load and convert draw history to chronological list."""
    with open(filename, 'r') as f:
        data = json.load(f)
    
    draws = []
    for date, draw_data in data.items():
        # Extract winning numbers
        winning_numbers = []
        bonus_number = None
        
        for detail in draw_data.get('winning_numbers_details', []):
            number = detail['number']
            winning_numbers.append(number)
            if detail.get('is_bonus', False):
                bonus_number = number
        
        draws.append({
            'draw_index': draw_data['draw_index'],
            'date': date,
            'numbers': winning_numbers,
            'bonus_number': bonus_number,
            'hmc_summary': draw_data.get('hmc_summary', {}),
            'categories_pre_draw': draw_data.get('categories_pre_draw', {}),
            'winning_numbers_details': draw_data.get('winning_numbers_details', [])
        })
    
    # Sort chronologically
    draws.sort(key=lambda x: x['draw_index'])
    return draws


def calculate_historical_hmc_baseline(draws: List[Dict]) -> Dict[str, float]:
    """
    Calculate the ACTUAL historical baseline from all draw data.
    This is more accurate than assuming 2-3-2.
    
    Returns:
        Dict with average hot/medium/cold counts
    """
    all_hot = []
    all_medium = []
    all_cold = []
    
    for draw in draws:
        hmc = draw['hmc_summary']
        all_hot.append(hmc.get('hot_count', 0))
        all_medium.append(hmc.get('medium_count', 0))
        all_cold.append(hmc.get('cold_count', 0))
    
    baseline = {
        'hot': np.mean(all_hot),
        'medium': np.mean(all_medium),
        'cold': np.mean(all_cold)
    }
    
    print(f"\n✓ Historical HMC Baseline (from {len(draws)} draws):")
    print(f"  Hot:    {baseline['hot']:.2f} avg")
    print(f"  Medium: {baseline['medium']:.2f} avg")
    print(f"  Cold:   {baseline['cold']:.2f} avg")
    
    return baseline


def analyze_hmc_distribution_patterns(draws: List[Dict]) -> pd.DataFrame:
    """
    Analyze the actual HMC distribution patterns (e.g., "2-3-2", "1-4-2") over time.
    
    Returns DataFrame with pattern frequency analysis.
    """
    pattern_counts = Counter()
    
    for draw in draws:
        pattern = draw['hmc_summary'].get('hmc_distribution', 'unknown')
        pattern_counts[pattern] += 1
    
    # Convert to DataFrame
    pattern_df = pd.DataFrame([
        {'pattern': pattern, 'count': count, 'percentage': round(count/len(draws)*100, 2)}
        for pattern, count in pattern_counts.most_common()
    ])
    
    return pattern_df


def analyze_hmc_imbalance(draws: List[Dict], window: int, baseline: Dict[str, float]) -> pd.DataFrame:
    """
    Analyze HMC category representation over time using ACTUAL historical baseline.
    
    Args:
        draws: List of draw dictionaries
        window: Lookback window size
        baseline: Historical baseline from calculate_historical_hmc_baseline()
    
    Returns DataFrame with deviation analysis.
    """
    results = []
    
    for i in range(window, len(draws)):
        recent_draws = draws[i-window:i]
        
        # Count HMC occurrences in this window
        hmc_counts = {'hot': [], 'medium': [], 'cold': []}
        pattern_distribution = Counter()
        
        for draw in recent_draws:
            hmc = draw['hmc_summary']
            hmc_counts['hot'].append(hmc.get('hot_count', 0))
            hmc_counts['medium'].append(hmc.get('medium_count', 0))
            hmc_counts['cold'].append(hmc.get('cold_count', 0))
            
            # Track actual patterns
            pattern = hmc.get('hmc_distribution', 'unknown')
            pattern_distribution[pattern] += 1
        
        # Calculate averages and deviations from historical baseline
        hot_avg = np.mean(hmc_counts['hot'])
        med_avg = np.mean(hmc_counts['medium'])
        cold_avg = np.mean(hmc_counts['cold'])
        
        # Get most common pattern in this window
        most_common_pattern = pattern_distribution.most_common(1)[0][0] if pattern_distribution else 'unknown'
        
        results.append({
            'draw_index': draws[i]['draw_index'],
            'date': draws[i]['date'],
            'window': window,
            'hot_avg': round(hot_avg, 2),
            'medium_avg': round(med_avg, 2),
            'cold_avg': round(cold_avg, 2),
            'hot_deviation_pct': round((hot_avg - baseline['hot']) / baseline['hot'] * 100, 1),
            'medium_deviation_pct': round((med_avg - baseline['medium']) / baseline['medium'] * 100, 1),
            'cold_deviation_pct': round((cold_avg - baseline['cold']) / baseline['cold'] * 100, 1),
            'most_common_pattern': most_common_pattern,
            'pattern_count': pattern_distribution[most_common_pattern]
        })
    
    return pd.DataFrame(results)


def analyze_total_count_performance(draws: List[Dict], window: int) -> pd.DataFrame:
    """
    Analyze which total_count ranges are performing best recently.
    
    Returns DataFrame showing win rate by frequency bin.
    """
    results = []
    
    for i in range(window, len(draws)):
        recent_draws = draws[i-window:i]
        
        # Count wins per total_count bin
        bin_wins = {str(b): 0 for b in TOTAL_COUNT_BINS}
        total_opportunities = {str(b): 0 for b in TOTAL_COUNT_BINS}
        
        for draw in recent_draws:
            for winner_detail in draw['winning_numbers_details']:
                # Get total_count (need to extract from pre-draw categories)
                # Approximation: use category as proxy
                category = winner_detail.get('category', 'cold')
                
                # Map category to approximate total_count range
                if category == 'hot':
                    bin_key = str((80, 90))  # Hot ≈ 80-90
                elif category == 'medium':
                    bin_key = str((70, 80))  # Medium ≈ 70-80
                else:
                    bin_key = str((60, 70))  # Cold ≈ 60-70
                
                bin_wins[bin_key] += 1
        
        # Calculate win rates
        total_wins = sum(bin_wins.values())
        
        result = {
            'draw_index': draws[i]['draw_index'],
            'date': draws[i]['date'],
            'window': window
        }
        
        for bin_range in TOTAL_COUNT_BINS:
            bin_key = str(bin_range)
            win_rate = (bin_wins[bin_key] / total_wins * 100) if total_wins > 0 else 0
            result[f'bin_{bin_range[0]}-{bin_range[1]}_pct'] = round(win_rate, 1)
        
        results.append(result)
    
    return pd.DataFrame(results)


def analyze_days_since_last_sweet_spot(draws: List[Dict], window: int) -> pd.DataFrame:
    """
    Find optimal 'days_since_last' windows that are hot recently.
    
    Returns DataFrame showing win rates by recency bin.
    """
    results = []
    
    for i in range(window, len(draws)):
        recent_draws = draws[i-window:i]
        
        # Count wins per days_since_last bin
        bin_wins = {str(b): 0 for b in DAYS_SINCE_BINS}
        
        for draw in recent_draws:
            for winner_detail in draw['winning_numbers_details']:
                days_since = winner_detail.get('days_since_last_hit', 999)
                
                # Assign to bin
                for bin_range in DAYS_SINCE_BINS:
                    if bin_range[0] <= days_since < bin_range[1]:
                        bin_wins[str(bin_range)] += 1
                        break
        
        # Calculate percentages
        total_wins = sum(bin_wins.values())
        
        result = {
            'draw_index': draws[i]['draw_index'],
            'date': draws[i]['date'],
            'window': window
        }
        
        for bin_range in DAYS_SINCE_BINS:
            bin_key = str(bin_range)
            win_rate = (bin_wins[bin_key] / total_wins * 100) if total_wins > 0 else 0
            result[f'days_{bin_range[0]}-{bin_range[1]}_pct'] = round(win_rate, 1)
        
        results.append(result)
    
    return pd.DataFrame(results)


def analyze_freshness_pattern_evolution(draws: List[Dict], window: int) -> pd.DataFrame:
    """
    Track how freshness patterns (C0/C1/C2/C3+) evolve over time.
    
    Returns DataFrame showing pattern distribution changes.
    """
    results = []
    
    for i in range(window, len(draws)):
        recent_draws = draws[i-window:i]
        
        # Count freshness bins
        freshness_counts = defaultdict(int)
        
        for draw in recent_draws:
            for winner_detail in draw['winning_numbers_details']:
                # Get freshness bin (C0, C1, C2, C3+)
                bin_idx = winner_detail.get('current_freshness_bin', 0)
                # Approximation: Assume C3+ is stored as 3 or more
                # For this analysis, we group counts >= 3 into C3
                if bin_idx >= 3:
                    c_bin = 'C3'
                else:
                    c_bin = f'C{bin_idx}'
                
                freshness_counts[c_bin] += 1
        
        # Calculate percentages
        total_numbers = sum(freshness_counts.values())
        
        result = {
            'draw_index': draws[i]['draw_index'],
            'date': draws[i]['date'],
            'window': window
        }
        
        # Add percentages for each C bin
        for c_bin in ['C0', 'C1', 'C2', 'C3']:
            count = freshness_counts.get(c_bin, 0)
            result[f'{c_bin}_pct'] = round((count / total_numbers * 100), 1) if total_numbers > 0 else 0
        
        results.append(result)
    
    return pd.DataFrame(results)


def analyze_bonus_prediction_power(draws: List[Dict], lookback: int = 10, forecast: int = 5) -> Dict:
    """
    Test if recent bonus numbers predict future main winners.
    
    Args:
        lookback: How many draws back to collect bonus numbers
        forecast: How many draws forward to check if they win
    
    Returns:
        Dict with analysis results
    """
    bonus_prediction_results = []
    
    for i in range(lookback, len(draws) - forecast):
        # Get bonus numbers from last N draws
        recent_bonuses = set()
        for j in range(i - lookback, i):
            bonus = draws[j]['bonus_number']
            if bonus is not None:
                recent_bonuses.add(bonus)
        
        # Check if any appear as main winners in next M draws
        future_winners = set()
        for j in range(i, min(i + forecast, len(draws))):
            # Only count first 6 numbers (main numbers)
            future_winners.update(draws[j]['numbers'][:6])
        
        # Calculate overlap
        overlap = recent_bonuses & future_winners
        
        bonus_prediction_results.append({
            'draw_index': draws[i]['draw_index'],
            'recent_bonuses_count': len(recent_bonuses),
            'overlap_count': len(overlap),
            'overlap_rate': len(overlap) / len(recent_bonuses) if recent_bonuses else 0
        })
    
    df = pd.DataFrame(bonus_prediction_results)
    
    # Calculate baseline (random chance)
    # If 7 numbers win per draw and 47 total numbers, baseline = 7/47 = 14.9% per number
    baseline_rate = 7 / 47
    
    avg_overlap_rate = df['overlap_rate'].mean()
    
    return {
        'avg_overlap_rate': round(avg_overlap_rate, 3),
        'baseline_rate': round(baseline_rate, 3),
        'lift': round(avg_overlap_rate / baseline_rate, 2),
        'interpretation': 'Predictive' if avg_overlap_rate > baseline_rate * 1.1 else 'Not predictive'
    }


def detect_regime_shifts(df: pd.DataFrame, metric_col: str, threshold: float = 10.0) -> List[Dict]:
    """
    Detect significant regime shifts in a metric.
    
    Args:
        df: DataFrame with time series data
        metric_col: Column to analyze
        threshold: % change to consider a shift
    
    Returns:
        List of detected shifts
    """
    if len(df) < 50:
        return []
    
    shifts = []
    window_size = 50
    
    for i in range(window_size, len(df), window_size):
        prev_window = df.iloc[i-window_size:i][metric_col].mean()
        curr_window = df.iloc[i:min(i+window_size, len(df))][metric_col].mean()
        
        pct_change = ((curr_window - prev_window) / prev_window * 100) if prev_window != 0 else 0
        
        if abs(pct_change) > threshold:
            shifts.append({
                'draw_index': df.iloc[i]['draw_index'],
                'date': df.iloc[i]['date'],
                'metric': metric_col,
                'prev_avg': round(prev_window, 2),
                'curr_avg': round(curr_window, 2),
                'pct_change': round(pct_change, 1)
            })
    
    return shifts


def generate_feature_recommendations(analyses: Dict) -> List[Dict]:
    """
    Generate ML feature recommendations based on trend analysis.
    
    Returns:
        List of recommended features with implementation details
    """
    recommendations = []
    
    # Analyze HMC deviations
    for window in ANALYSIS_WINDOWS:
        hmc_df = analyses['hmc_imbalance'][window]
        
        # Check if there's persistent imbalance
        recent = hmc_df.tail(50)
        hot_dev_avg = recent['hot_deviation_pct'].mean()
        med_dev_avg = recent['medium_deviation_pct'].mean()
        cold_dev_avg = recent['cold_deviation_pct'].mean()
        
        if abs(hot_dev_avg) > 10 or abs(med_dev_avg) > 10 or abs(cold_dev_avg) > 10:
            recommendations.append({
                'feature_name': f'hmc_imbalance_last_{window}',
                'type': 'category_deviation',
                'window': window,
                'description': f'Track HMC category deviation in last {window} draws',
                'current_signal': f'Hot: {hot_dev_avg:.1f}%, Med: {med_dev_avg:.1f}%, Cold: {cold_dev_avg:.1f}%',
                'implementation': f'For each number: deviation_score = (category_avg_last_{window} - expected) / expected',
                'potential_impact': 'High' if abs(hot_dev_avg) > 20 else 'Medium'
            })
    
    # Analyze bonus prediction power
    bonus_analysis = analyses['bonus_prediction']
    if bonus_analysis['interpretation'] == 'Predictive':
        recommendations.append({
            'feature_name': 'was_recent_bonus',
            'type': 'bonus_indicator',
            'window': 10,
            'description': 'Binary indicator if number was bonus in last 10 draws',
            'current_signal': f"Lift: {bonus_analysis['lift']}x over baseline",
            'implementation': 'For each number: 1 if appeared as bonus in last 10 draws, 0 otherwise',
            'potential_impact': 'High' if bonus_analysis['lift'] > 1.2 else 'Medium'
        })
    
    return recommendations


def main():
    """Main execution function."""
    print("=" * 80)
    print("LOTTERY TREND DISCOVERY ANALYZER")
    print("=" * 80)
    
    # Load data
    print("\nLoading draw history...")
    draws = load_draw_history(DRAW_HISTORY_JSON)
    print(f"✓ Loaded {len(draws)} draws")
    
    # Calculate HMC baseline
    baseline = calculate_historical_hmc_baseline(draws)

    # Run analyses
    print("\n" + "=" * 80)
    print("RUNNING TREND ANALYSES")
    print("=" * 80)
    
    analyses = {
        'hmc_imbalance': {},
        'total_count_performance': {},
        'days_since_sweet_spot': {},
        'freshness_evolution': {}
    }
    
    # HMC Imbalance Analysis
    print("\n1. HMC Category Imbalance Over Time")
    print("-" * 80)
    for window in ANALYSIS_WINDOWS:
        # FIXED CALL: Pass the required 'baseline' argument
        df = analyze_hmc_imbalance(draws, window, baseline)
        analyses['hmc_imbalance'][window] = df
        
        # Show recent snapshot
        recent = df.tail(1).iloc[0]
        # Approximation of expected values (2.0, 3.0, 2.0 sums to 7.0)
        expected_hot = baseline.get('hot', 2.0)
        expected_medium = baseline.get('medium', 3.0)
        expected_cold = baseline.get('cold', 2.0)
        
        print(f"\nWindow: Last {window} draws (as of {recent['date']})")
        print(f"  Hot:    {recent['hot_avg']:.2f} avg ({recent['hot_deviation_pct']:+.1f}% vs expected {expected_hot:.2f})")
        print(f"  Medium: {recent['medium_avg']:.2f} avg ({recent['medium_deviation_pct']:+.1f}% vs expected {expected_medium:.2f})")
        print(f"  Cold:   {recent['cold_avg']:.2f} avg ({recent['cold_deviation_pct']:+.1f}% vs expected {expected_cold:.2f})")
    
    # Total Count Performance
    print("\n2. Total Count Range Performance")
    print("-" * 80)
    for window in [100]:  # Focus on 100-draw window
        df = analyze_total_count_performance(draws, window)
        analyses['total_count_performance'][window] = df
        
        recent = df.tail(1).iloc[0]
        print(f"\nLast {window} draws - Win Distribution by Frequency Range:")
        for bin_range in TOTAL_COUNT_BINS:
            col = f'bin_{bin_range[0]}-{bin_range[1]}_pct'
            print(f"  {bin_range[0]}-{bin_range[1]}: {recent[col]:.1f}%")
    
    # Days Since Last Sweet Spot
    print("\n3. Optimal Days-Since-Last Window")
    print("-" * 80)
    for window in [100]:
        df = analyze_days_since_last_sweet_spot(draws, window)
        analyses['days_since_sweet_spot'][window] = df
        
        recent = df.tail(1).iloc[0]
        print(f"\nLast {window} draws - Win Distribution by Recency:")
        for bin_range in DAYS_SINCE_BINS:
            col = f'days_{bin_range[0]}-{bin_range[1]}_pct'
            print(f"  {bin_range[0]}-{bin_range[1]} days: {recent[col]:.1f}%")
    
    # Freshness Pattern Evolution
    print("\n4. Freshness Pattern Evolution")
    print("-" * 80)
    for window in [100, 200]:
        df = analyze_freshness_pattern_evolution(draws, window)
        analyses['freshness_evolution'][window] = df
        
        recent = df.tail(1).iloc[0]
        print(f"\nLast {window} draws - Freshness Distribution:")
        for c in ['C0', 'C1', 'C2', 'C3']:
            col = f'{c}_pct'
            if col in recent:
                print(f"  {c}: {recent[col]:.1f}%")
    
    # Bonus Prediction Power
    print("\n5. Bonus Ball Predictive Power")
    print("-" * 80)
    bonus_analysis = analyze_bonus_prediction_power(draws)
    analyses['bonus_prediction'] = bonus_analysis
    
    print(f"\nRecent bonus numbers (last 10 draws) → Future winners (next 5 draws)")
    print(f"  Average overlap rate: {bonus_analysis['avg_overlap_rate']*100:.1f}%")
    print(f"  Random baseline: {bonus_analysis['baseline_rate']*100:.1f}%")
    print(f"  Lift: {bonus_analysis['lift']}x")
    print(f"  Verdict: {bonus_analysis['interpretation']}")
    
    # Regime Shift Detection
    print("\n6. Regime Shift Detection")
    print("-" * 80)
    hmc_100 = analyses['hmc_imbalance'][100]
    shifts = detect_regime_shifts(hmc_100, 'hot_deviation_pct', threshold=15.0)
    
    if shifts:
        print(f"\nDetected {len(shifts)} significant shifts in Hot deviation:")
        for shift in shifts[-3:]:  # Show last 3
            print(f"  {shift['date']}: {shift['prev_avg']:.1f}% → {shift['curr_avg']:.1f}% "
                  f"({shift['pct_change']:+.1f}% change)")
    else:
        print("\nNo significant regime shifts detected (stable pattern)")
    
    # Feature Recommendations
    print("\n" + "=" * 80)
    print("FEATURE RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = generate_feature_recommendations(analyses)
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['feature_name']} [{rec['potential_impact']} Impact]")
            print(f"   Type: {rec['type']}")
            print(f"   Description: {rec['description']}")
            print(f"   Current Signal: {rec['current_signal']}")
            print(f"   Implementation: {rec['implementation']}")
    else:
        print("\nNo strong feature candidates detected in current analysis.")
        print("All patterns appear stable or random.")
    
    # Export results
    print("\n" + "=" * 80)
    print("EXPORTING RESULTS")
    print("=" * 80)
    
    # Save HMC imbalance time series
    for window in ANALYSIS_WINDOWS:
        filename = f'trend_analysis_hmc_imbalance_{window}draws.csv'
        analyses['hmc_imbalance'][window].to_csv(filename, index=False)
        print(f"✓ Saved: {filename}")
    
    # Save recommendations
    if recommendations:
        rec_df = pd.DataFrame(recommendations)
        rec_df.to_csv('feature_recommendations.csv', index=False)
        print("✓ Saved: feature_recommendations.csv")
    
    print("\n" + "=" * 80)
    print("✓ Analysis Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()