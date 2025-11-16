#!/usr/bin/env python3
"""
Gap Pattern Analyzer
====================
Analyzes time gaps between consecutive appearances of lottery numbers to identify
patterns and determine "due" numbers based on historical gap distributions.

This script analyzes:
1. Distribution of gap lengths for each number (draws between appearances)
2. Predictive power of gap length (does a long gap predict imminent appearance?)
3. Gap consistency vs volatility (coefficient of variation)
4. Optimal "due" threshold (how many draws before a number becomes "due")
5. Category-specific gap patterns (hot vs medium vs cold)
6. Survival analysis (probability of appearance given current gap)

Usage:
    From project root:
        python analysis/gap_pattern_analyzer.py

    From analysis folder:
        python gap_pattern_analyzer.py

Output:
    - data/lotto_gap_analysis.json (full gap analysis data)
    - data/lotto_gap_summary.csv (per-number statistics)
    - data/lotto_due_numbers.csv (current "due" rankings)
    - Console output with key findings
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import math
from datetime import datetime

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
                        numbers = [detail['number'] for detail in winning_details]
                        sorted_draws.append({
                            'date': date,
                            'draw_index': draw_data.get('draw_index', 0),
                            'numbers': numbers,
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


def calculate_gaps_per_number(sorted_draws: List[Dict[str, Any]], max_number: int = 47) -> Dict[int, List[int]]:
    """
    Calculate all gap lengths for each number.

    Gap = number of draws between consecutive appearances.
    Example: If number appears in draw 10 and next in draw 15, gap = 4

    Returns:
        Dict mapping number -> list of gap lengths
    """
    # Track last appearance of each number
    last_appearance = {}
    gaps = defaultdict(list)

    for draw_idx, draw in enumerate(sorted_draws):
        for num in draw['numbers']:
            if num in last_appearance:
                gap = draw_idx - last_appearance[num] - 1  # -1 because gap is draws between
                gaps[num].append(gap)

            last_appearance[num] = draw_idx

    return dict(gaps)


def calculate_gap_statistics(gaps: Dict[int, List[int]]) -> Dict[int, Dict[str, float]]:
    """
    Calculate comprehensive gap statistics for each number.

    Statistics include:
    - Mean, median, std deviation
    - Min, max, range
    - Coefficient of variation (CV = std/mean) - measures consistency
    - Percentiles (25th, 75th, 90th)
    """
    stats = {}

    for num, gap_list in gaps.items():
        if not gap_list:
            continue

        sorted_gaps = sorted(gap_list)
        n = len(sorted_gaps)

        # Basic statistics
        mean = sum(gap_list) / n
        median = sorted_gaps[n // 2] if n % 2 == 1 else (sorted_gaps[n // 2 - 1] + sorted_gaps[n // 2]) / 2

        # Standard deviation
        variance = sum((x - mean) ** 2 for x in gap_list) / n
        std = math.sqrt(variance)

        # Coefficient of variation (CV) - measures consistency
        cv = std / mean if mean > 0 else 0

        # Min, max, range
        min_gap = min(gap_list)
        max_gap = max(gap_list)
        gap_range = max_gap - min_gap

        # Percentiles
        p25 = sorted_gaps[int(n * 0.25)]
        p75 = sorted_gaps[int(n * 0.75)]
        p90 = sorted_gaps[int(n * 0.90)] if n > 10 else max_gap

        stats[num] = {
            'mean': round(mean, 2),
            'median': round(median, 2),
            'std': round(std, 2),
            'cv': round(cv, 3),  # Lower CV = more consistent
            'min': min_gap,
            'max': max_gap,
            'range': gap_range,
            'p25': p25,
            'p75': p75,
            'p90': p90,
            'total_gaps': n,
            'consistency_score': round(1 / (1 + cv), 3)  # Higher = more consistent
        }

    return stats


def calculate_current_gaps(sorted_draws: List[Dict[str, Any]], max_number: int = 47) -> Dict[int, int]:
    """
    Calculate current gap for each number (draws since last appearance).

    Returns:
        Dict mapping number -> current gap (draws since last seen)
    """
    current_gaps = {}
    latest_draw_idx = len(sorted_draws) - 1

    # Find last appearance of each number
    last_appearance = {}
    for draw_idx, draw in enumerate(sorted_draws):
        for num in draw['numbers']:
            last_appearance[num] = draw_idx

    # Calculate current gap
    for num in range(1, max_number + 1):
        if num in last_appearance:
            current_gaps[num] = latest_draw_idx - last_appearance[num]
        else:
            current_gaps[num] = latest_draw_idx  # Never appeared

    return current_gaps


def calculate_due_scores(gap_stats: Dict[int, Dict[str, float]],
                        current_gaps: Dict[int, int]) -> Dict[int, Dict[str, Any]]:
    """
    Calculate "due" scores for each number based on current gap vs historical patterns.

    Due score logic:
    - Compare current gap to mean/median
    - Higher score = more overdue
    - Score = (current_gap - mean) / std  (z-score)
    """
    due_scores = {}

    for num in current_gaps:
        if num not in gap_stats:
            continue

        stats = gap_stats[num]
        current = current_gaps[num]

        # Z-score (how many std deviations above mean)
        z_score = (current - stats['mean']) / stats['std'] if stats['std'] > 0 else 0

        # Percentile position (where current gap falls in historical distribution)
        percentile_position = 0
        if current >= stats['p90']:
            percentile_position = 90
        elif current >= stats['p75']:
            percentile_position = 75
        elif current >= stats['median']:
            percentile_position = 50
        elif current >= stats['p25']:
            percentile_position = 25
        else:
            percentile_position = 0

        # Due probability (simple heuristic)
        # Based on: if gap > mean, probability increases
        due_prob = min(0.99, max(0.01, 0.5 + (z_score * 0.1)))

        due_scores[num] = {
            'current_gap': current,
            'mean_gap': stats['mean'],
            'median_gap': stats['median'],
            'z_score': round(z_score, 3),
            'percentile_position': percentile_position,
            'due_probability': round(due_prob, 4),
            'is_overdue': current > stats['mean'],
            'overdue_by': round(current - stats['mean'], 2) if current > stats['mean'] else 0
        }

    return due_scores


def analyze_gap_predictive_power(gaps: Dict[int, List[int]],
                                 sorted_draws: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Test if long gaps predict imminent appearance.

    Method: For each appearance, check if it came after a long gap (>mean).
    Calculate: P(appear in next N draws | gap > threshold)
    """
    # Build appearance tracking
    appearances = defaultdict(list)
    last_appearance = {}

    for draw_idx, draw in enumerate(sorted_draws):
        for num in draw['numbers']:
            if num in last_appearance:
                gap = draw_idx - last_appearance[num] - 1
                appearances[num].append({
                    'draw_idx': draw_idx,
                    'gap_before': gap
                })
            else:
                appearances[num].append({
                    'draw_idx': draw_idx,
                    'gap_before': 0  # First appearance
                })

            last_appearance[num] = draw_idx

    # Calculate mean gap for each number
    mean_gaps = {}
    for num, gap_list in gaps.items():
        if gap_list:
            mean_gaps[num] = sum(gap_list) / len(gap_list)

    # Test prediction: After long gap, is appearance more likely?
    long_gap_appeared_next = 0
    long_gap_total = 0
    normal_gap_appeared_next = 0
    normal_gap_total = 0

    for num in range(1, 48):
        if num not in appearances or num not in mean_gaps:
            continue

        mean = mean_gaps[num]
        app_list = appearances[num]

        for i in range(len(app_list) - 1):
            gap = app_list[i]['gap_before']

            # Check if appeared in next 5 draws
            appeared_soon = False
            next_draw = app_list[i]['draw_idx']
            for j in range(i + 1, len(app_list)):
                if app_list[j]['draw_idx'] <= next_draw + 5:
                    appeared_soon = True
                    break

            if gap > mean:
                long_gap_total += 1
                if appeared_soon:
                    long_gap_appeared_next += 1
            else:
                normal_gap_total += 1
                if appeared_soon:
                    normal_gap_appeared_next += 1

    # Calculate probabilities
    p_after_long = (long_gap_appeared_next / long_gap_total) if long_gap_total > 0 else 0
    p_after_normal = (normal_gap_appeared_next / normal_gap_total) if normal_gap_total > 0 else 0

    lift = (p_after_long / p_after_normal) if p_after_normal > 0 else 0

    return {
        'long_gap_appearances': long_gap_total,
        'long_gap_appeared_next_5': long_gap_appeared_next,
        'p_appear_after_long_gap': round(p_after_long, 4),
        'normal_gap_appearances': normal_gap_total,
        'normal_gap_appeared_next_5': normal_gap_appeared_next,
        'p_appear_after_normal_gap': round(p_after_normal, 4),
        'predictive_lift': round(lift, 3),
        'interpretation': 'Predictive' if lift > 1.1 else 'Not predictive'
    }


def analyze_category_gaps(sorted_draws: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Analyze gap patterns by HMC category.

    Questions:
    - Do hot numbers have shorter gaps?
    - Do cold numbers have longer gaps?
    """
    category_gaps = defaultdict(list)
    last_appearance = defaultdict(lambda: {})

    for draw_idx, draw in enumerate(sorted_draws):
        for detail in draw['winning_details']:
            num = detail['number']
            category = detail.get('category', 'unknown')

            if num in last_appearance:
                gap = draw_idx - last_appearance[num]['draw_idx'] - 1
                # Use category from when it appeared (not current category)
                prev_category = last_appearance[num]['category']
                category_gaps[prev_category].append(gap)

            last_appearance[num] = {
                'draw_idx': draw_idx,
                'category': category
            }

    # Calculate statistics by category
    category_stats = {}
    for category, gap_list in category_gaps.items():
        if not gap_list:
            continue

        mean = sum(gap_list) / len(gap_list)
        sorted_gaps = sorted(gap_list)
        median = sorted_gaps[len(gap_list) // 2]

        variance = sum((x - mean) ** 2 for x in gap_list) / len(gap_list)
        std = math.sqrt(variance)

        category_stats[category] = {
            'mean_gap': round(mean, 2),
            'median_gap': round(median, 2),
            'std_gap': round(std, 2),
            'min_gap': min(gap_list),
            'max_gap': max(gap_list),
            'total_observations': len(gap_list)
        }

    return category_stats


def generate_due_rankings(due_scores: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate ranked list of most "due" numbers."""
    rankings = []

    for num, scores in due_scores.items():
        rankings.append({
            'number': num,
            'current_gap': scores['current_gap'],
            'mean_gap': scores['mean_gap'],
            'z_score': scores['z_score'],
            'due_probability': scores['due_probability'],
            'overdue_by': scores['overdue_by']
        })

    # Sort by due probability (descending)
    rankings.sort(key=lambda x: x['due_probability'], reverse=True)

    return rankings


def save_outputs(gap_stats: Dict, due_scores: Dict, predictive_power: Dict,
                category_stats: Dict, due_rankings: List, total_draws: int):
    """Save all analysis outputs to files."""

    # Full JSON output
    output_data = {
        'metadata': {
            'total_draws': total_draws,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analysis_type': 'gap_pattern_analysis'
        },
        'per_number_gap_statistics': gap_stats,
        'due_scores': due_scores,
        'predictive_power_analysis': predictive_power,
        'category_gap_patterns': category_stats,
        'due_rankings_top_20': due_rankings[:20]
    }

    # Save JSON
    for path in ['../data/lotto_gap_analysis.json', 'data/lotto_gap_analysis.json']:
        try:
            with open(path, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"✓ Full analysis saved to {path}")
            break
        except:
            continue

    # Save gap statistics CSV
    for path in ['../data/lotto_gap_summary.csv', 'data/lotto_gap_summary.csv']:
        try:
            with open(path, 'w') as f:
                f.write("Number,Mean_Gap,Median_Gap,Std_Gap,CV,Min,Max,P90,Consistency_Score,Total_Gaps\n")
                for num in sorted(gap_stats.keys()):
                    stats = gap_stats[num]
                    f.write(f"{num},{stats['mean']},{stats['median']},{stats['std']},"
                           f"{stats['cv']},{stats['min']},{stats['max']},{stats['p90']},"
                           f"{stats['consistency_score']},{stats['total_gaps']}\n")
            print(f"✓ Gap summary saved to {path}")
            break
        except:
            continue

    # Save due numbers CSV
    for path in ['../data/lotto_due_numbers.csv', 'data/lotto_due_numbers.csv']:
        try:
            with open(path, 'w') as f:
                f.write("Rank,Number,Current_Gap,Mean_Gap,Z_Score,Due_Probability,Overdue_By\n")
                for rank, item in enumerate(due_rankings[:47], 1):
                    f.write(f"{rank},{item['number']},{item['current_gap']},{item['mean_gap']},"
                           f"{item['z_score']},{item['due_probability']},{item['overdue_by']}\n")
            print(f"✓ Due numbers saved to {path}")
            break
        except:
            continue


def print_results(gap_stats: Dict, due_scores: Dict, predictive_power: Dict,
                 category_stats: Dict, due_rankings: List):
    """Print comprehensive analysis results."""

    print("\n" + "=" * 80)
    print("GAP PATTERN ANALYSIS")
    print("=" * 80)

    # Overall gap statistics
    all_means = [stats['mean'] for stats in gap_stats.values()]
    all_cvs = [stats['cv'] for stats in gap_stats.values()]

    print(f"\nOVERALL GAP STATISTICS:")
    print(f"  Average mean gap across all numbers: {sum(all_means) / len(all_means):.2f} draws")
    print(f"  Most consistent number (lowest CV): #{min(gap_stats.items(), key=lambda x: x[1]['cv'])[0]} "
          f"(CV = {min(all_cvs):.3f})")
    print(f"  Most volatile number (highest CV): #{max(gap_stats.items(), key=lambda x: x[1]['cv'])[0]} "
          f"(CV = {max(all_cvs):.3f})")

    print("\n" + "-" * 80)
    print("TOP 10 MOST CONSISTENT NUMBERS (Lowest Coefficient of Variation)")
    print("-" * 80)
    print(f"{'Number':<8} {'Mean Gap':<12} {'Std Dev':<12} {'CV':<8} {'Consistency':<12}")
    print("-" * 80)

    sorted_by_consistency = sorted(gap_stats.items(), key=lambda x: x[1]['cv'])
    for num, stats in sorted_by_consistency[:10]:
        print(f"{num:<8} {stats['mean']:<12.2f} {stats['std']:<12.2f} "
              f"{stats['cv']:<8.3f} {stats['consistency_score']:<12.3f}")

    print("\n" + "-" * 80)
    print("TOP 10 MOST VOLATILE NUMBERS (Highest Coefficient of Variation)")
    print("-" * 80)
    print(f"{'Number':<8} {'Mean Gap':<12} {'Std Dev':<12} {'CV':<8} {'Min':<8} {'Max':<8}")
    print("-" * 80)

    sorted_by_volatility = sorted(gap_stats.items(), key=lambda x: x[1]['cv'], reverse=True)
    for num, stats in sorted_by_volatility[:10]:
        print(f"{num:<8} {stats['mean']:<12.2f} {stats['std']:<12.2f} "
              f"{stats['cv']:<8.3f} {stats['min']:<8} {stats['max']:<8}")

    print("\n" + "-" * 80)
    print("TOP 20 'DUE' NUMBERS (Most Overdue Based on Historical Patterns)")
    print("-" * 80)
    print(f"{'Rank':<6} {'Number':<8} {'Current':<10} {'Mean':<10} {'Z-Score':<10} {'Due Prob':<10} {'Status':<15}")
    print("-" * 80)

    for rank, item in enumerate(due_rankings[:20], 1):
        status = "⚠️ VERY OVERDUE" if item['z_score'] > 2 else "⚡ OVERDUE" if item['z_score'] > 1 else "Due"
        print(f"{rank:<6} #{item['number']:<7} {item['current_gap']:<10} {item['mean_gap']:<10.2f} "
              f"{item['z_score']:<10.2f} {item['due_probability']:<10.4f} {status:<15}")

    print("\n" + "-" * 80)
    print("PREDICTIVE POWER OF GAP LENGTH")
    print("-" * 80)

    pp = predictive_power
    print(f"\nDoes a long gap predict imminent appearance?")
    print(f"  P(appear in next 5 draws | gap > mean):  {pp['p_appear_after_long_gap']:.4f}")
    print(f"  P(appear in next 5 draws | gap ≤ mean):  {pp['p_appear_after_normal_gap']:.4f}")
    print(f"  Predictive lift: {pp['predictive_lift']:.3f}x")
    print(f"  Interpretation: {pp['interpretation']}")

    if pp['predictive_lift'] > 1.1:
        print(f"  ✓ Long gaps DO predict higher probability of appearance")
    else:
        print(f"  ✗ Long gaps do NOT significantly predict appearance")

    print("\n" + "-" * 80)
    print("GAP PATTERNS BY HMC CATEGORY")
    print("-" * 80)
    print(f"{'Category':<12} {'Mean Gap':<12} {'Median':<10} {'Std Dev':<12} {'Observations':<15}")
    print("-" * 80)

    for category in ['hot', 'medium', 'cold']:
        if category in category_stats:
            stats = category_stats[category]
            print(f"{category.capitalize():<12} {stats['mean_gap']:<12.2f} {stats['median_gap']:<10.2f} "
                  f"{stats['std_gap']:<12.2f} {stats['total_observations']:<15}")

    print("\n" + "=" * 80)
    print("INTERPRETATION GUIDE")
    print("=" * 80)
    print("Coefficient of Variation (CV): Std Dev / Mean")
    print("  - Low CV (<0.5):  Very consistent gaps - predictable reappearance")
    print("  - Medium CV (0.5-1.0):  Moderate consistency")
    print("  - High CV (>1.0):  Highly variable gaps - unpredictable")
    print("\nZ-Score: (Current Gap - Mean) / Std Dev")
    print("  - Z > 2:  Very overdue (97.5th percentile)")
    print("  - Z > 1:  Overdue (84th percentile)")
    print("  - Z ≈ 0:  On schedule")
    print("  - Z < 0:  Appeared recently")
    print("\nDue Probability: Estimated likelihood of appearing soon")
    print("  - Based on z-score and historical gap distribution")
    print("=" * 80)


def main():
    """Main execution function."""
    print("Loading draw history...")
    full_history, sorted_draws = load_draw_history()
    print(f"✓ Loaded {len(sorted_draws)} draws")

    print("\n1. Calculating gaps for each number...")
    gaps = calculate_gaps_per_number(sorted_draws)
    print(f"✓ Calculated gaps for {len(gaps)} numbers")

    print("\n2. Computing gap statistics...")
    gap_stats = calculate_gap_statistics(gaps)
    print(f"✓ Computed statistics for {len(gap_stats)} numbers")

    print("\n3. Analyzing current gaps...")
    current_gaps = calculate_current_gaps(sorted_draws)
    print(f"✓ Calculated current gaps for 47 numbers")

    print("\n4. Computing due scores...")
    due_scores = calculate_due_scores(gap_stats, current_gaps)
    print(f"✓ Computed due scores for {len(due_scores)} numbers")

    print("\n5. Testing predictive power of gap length...")
    predictive_power = analyze_gap_predictive_power(gaps, sorted_draws)
    print(f"✓ Analyzed {predictive_power['long_gap_appearances'] + predictive_power['normal_gap_appearances']} gap instances")

    print("\n6. Analyzing category-specific gap patterns...")
    category_stats = analyze_category_gaps(sorted_draws)
    print(f"✓ Analyzed gaps for {len(category_stats)} categories")

    print("\n7. Generating due rankings...")
    due_rankings = generate_due_rankings(due_scores)
    print(f"✓ Generated rankings for 47 numbers")

    print("\n8. Saving outputs...")
    save_outputs(gap_stats, due_scores, predictive_power, category_stats,
                due_rankings, len(sorted_draws))

    # Print results
    print_results(gap_stats, due_scores, predictive_power, category_stats, due_rankings)


if __name__ == "__main__":
    main()
