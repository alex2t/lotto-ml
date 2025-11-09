#!/usr/bin/env python3
"""
bonus_analysis.py
=================
Analyze bonus ball patterns and statistics from historical draw data.

This script reads lotto_draw_history.json and generates comprehensive
statistics about bonus ball behavior, HMC patterns, timing patterns,
and correlations.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
from datetime import datetime


def load_draw_history(filename: str = 'data/lotto_draw_history.json') -> Dict[str, Any]:
    """Load draw history JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {filename} not found. Run 'python drawpick.py' first.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {filename}: {e}")
        sys.exit(1)


def get_dynamic_recent_count_keys(draw_history: Dict) -> List[str]:
    """Dynamically detect all recent_count keys from data."""
    recent_keys = set()
    
    for draw_data in draw_history.values():
        winning_details = draw_data.get('winning_numbers_details', [])
        if winning_details:
            recent_counts = winning_details[0].get('recent_counts', {})
            recent_keys.update(recent_counts.keys())
            break
    
    # Sort by window size (extract number from 'last_N')
    sorted_keys = sorted(recent_keys, key=lambda x: int(x.split('_')[1]))
    return sorted_keys


def analyze_hmc_distribution(draw_history: Dict) -> Dict:
    """Analyze HMC (Hot/Medium/Cold) distribution patterns."""
    
    hmc_patterns = Counter()
    category_counts = defaultdict(lambda: defaultdict(int))
    total_numbers = defaultdict(int)
    
    for draw_data in draw_history.values():
        hmc_summary = draw_data.get('hmc_summary', {})
        hmc_dist = hmc_summary.get('hmc_distribution', '')
        
        if hmc_dist:
            hmc_patterns[hmc_dist] += 1
        
        # Count by category
        winning_details = draw_data.get('winning_numbers_details', [])
        for detail in winning_details:
            category = detail.get('category', 'unknown')
            is_bonus = detail.get('is_bonus', False)
            
            position = 'bonus' if is_bonus else 'main'
            category_counts[position][category] += 1
            total_numbers[position] += 1
    
    total_draws = len(draw_history)
    
    # Calculate percentages
    hmc_percentages = {
        pattern: (count / total_draws * 100)
        for pattern, count in hmc_patterns.most_common()
    }
    
    main_percentages = {
        category: (count / total_numbers['main'] * 100)
        for category, count in category_counts['main'].items()
    }
    
    bonus_percentages = {
        category: (count / total_numbers['bonus'] * 100)
        for category, count in category_counts['bonus'].items()
    }
    
    return {
        'hmc_pattern_distribution': hmc_percentages,
        'main_category_distribution': main_percentages,
        'bonus_category_distribution': bonus_percentages,
        'total_draws': total_draws,
        'total_main_numbers': total_numbers['main'],
        'total_bonus_numbers': total_numbers['bonus']
    }


def analyze_days_since_last_hit(draw_history: Dict) -> Dict:
    """Analyze days_since_last_hit distribution by category and position."""
    
    bins = [
        (0, 7, '0-7 days'),
        (8, 14, '8-14 days'),
        (15, 21, '15-21 days'),
        (22, 30, '22-30 days'),
        (31, 45, '31-45 days'),
        (46, 60, '46-60 days'),
        (61, 90, '61-90 days'),
        (91, 120, '91-120 days'),
        (121, 999, '121+ days')
    ]
    
    main_by_category = defaultdict(lambda: defaultdict(int))
    bonus_by_category = defaultdict(lambda: defaultdict(int))
    main_total_by_category = defaultdict(int)
    bonus_total_by_category = defaultdict(int)
    
    for draw_data in draw_history.values():
        winning_details = draw_data.get('winning_numbers_details', [])
        
        for detail in winning_details:
            days = detail.get('days_since_last_hit', 0)
            category = detail.get('category', 'unknown')
            is_bonus = detail.get('is_bonus', False)
            
            # Find appropriate bin
            bin_name = '121+ days'
            for min_days, max_days, name in bins:
                if min_days <= days <= max_days:
                    bin_name = name
                    break
            
            if is_bonus:
                bonus_by_category[category][bin_name] += 1
                bonus_total_by_category[category] += 1
            else:
                main_by_category[category][bin_name] += 1
                main_total_by_category[category] += 1
    
    # Calculate percentages
    main_percentages = {}
    for category in main_by_category:
        main_percentages[category] = {
            bin_name: (count / main_total_by_category[category] * 100)
            for bin_name, count in main_by_category[category].items()
        }
    
    bonus_percentages = {}
    for category in bonus_by_category:
        bonus_percentages[category] = {
            bin_name: (count / bonus_total_by_category[category] * 100)
            for bin_name, count in bonus_by_category[category].items()
        }
    
    return {
        'main_numbers': {
            'by_category': main_percentages,
            'totals': dict(main_total_by_category)
        },
        'bonus_numbers': {
            'by_category': bonus_percentages,
            'totals': dict(bonus_total_by_category)
        },
        'bins_used': [name for _, _, name in bins]
    }


def analyze_recent_counts(draw_history: Dict, recent_keys: List[str]) -> Dict:
    """Analyze recent_counts distribution by category and position."""
    
    results = {}
    
    for key in recent_keys:
        main_by_category = defaultdict(lambda: defaultdict(int))
        bonus_by_category = defaultdict(lambda: defaultdict(int))
        main_total_by_category = defaultdict(int)
        bonus_total_by_category = defaultdict(int)
        
        for draw_data in draw_history.values():
            winning_details = draw_data.get('winning_numbers_details', [])
            
            for detail in winning_details:
                recent_counts = detail.get('recent_counts', {})
                count = recent_counts.get(key, 0)
                category = detail.get('category', 'unknown')
                is_bonus = detail.get('is_bonus', False)
                
                count_label = f"{count}x"
                
                if is_bonus:
                    bonus_by_category[category][count_label] += 1
                    bonus_total_by_category[category] += 1
                else:
                    main_by_category[category][count_label] += 1
                    main_total_by_category[category] += 1
        
        # Calculate percentages
        main_percentages = {}
        for category in main_by_category:
            main_percentages[category] = {
                count: (num / main_total_by_category[category] * 100)
                for count, num in main_by_category[category].items()
            }
        
        bonus_percentages = {}
        for category in bonus_by_category:
            bonus_percentages[category] = {
                count: (num / bonus_total_by_category[category] * 100)
                for count, num in bonus_by_category[category].items()
            }
        
        results[key] = {
            'main_numbers': {
                'by_category': main_percentages,
                'totals': dict(main_total_by_category)
            },
            'bonus_numbers': {
                'by_category': bonus_percentages,
                'totals': dict(bonus_total_by_category)
            }
        }
    
    return results


def analyze_bonus_patterns(draw_history: Dict) -> Dict:
    """Analyze specific bonus ball patterns and behaviors."""
    
    bonus_categories = Counter()
    bonus_recent_bonus_hits = Counter()
    bonus_hit_contributions = []
    
    main_that_were_recent_bonus = 0
    total_main_numbers = 0
    
    for draw_data in draw_history.values():
        winning_details = draw_data.get('winning_numbers_details', [])
        
        for detail in winning_details:
            is_bonus = detail.get('is_bonus', False)
            is_recent_bonus_hit = detail.get('is_recent_bonus_hit', False)
            bonus_hit_contribution = detail.get('bonus_hit_contribution', 0.0)
            category = detail.get('category', 'unknown')
            
            if is_bonus:
                bonus_categories[category] += 1
                if is_recent_bonus_hit:
                    bonus_recent_bonus_hits['was_recent_bonus'] += 1
                else:
                    bonus_recent_bonus_hits['was_not_recent_bonus'] += 1
                
                bonus_hit_contributions.append(bonus_hit_contribution)
            else:
                total_main_numbers += 1
                if is_recent_bonus_hit:
                    main_that_were_recent_bonus += 1
    
    total_bonus = sum(bonus_categories.values())
    
    return {
        'bonus_category_distribution': {
            category: (count / total_bonus * 100)
            for category, count in bonus_categories.items()
        },
        'bonus_was_recent_bonus': {
            status: (count / total_bonus * 100)
            for status, count in bonus_recent_bonus_hits.items()
        },
        'main_numbers_that_were_recent_bonus': {
            'count': main_that_were_recent_bonus,
            'total': total_main_numbers,
            'percentage': (main_that_were_recent_bonus / total_main_numbers * 100) if total_main_numbers > 0 else 0
        },
        'bonus_hit_contribution_stats': {
            'avg': sum(bonus_hit_contributions) / len(bonus_hit_contributions) if bonus_hit_contributions else 0,
            'min': min(bonus_hit_contributions) if bonus_hit_contributions else 0,
            'max': max(bonus_hit_contributions) if bonus_hit_contributions else 0
        }
    }


def analyze_freshness_patterns(draw_history: Dict) -> Dict:
    """Analyze freshness bin distribution by category and position."""
    
    main_by_category = defaultdict(lambda: defaultdict(int))
    bonus_by_category = defaultdict(lambda: defaultdict(int))
    main_total_by_category = defaultdict(int)
    bonus_total_by_category = defaultdict(int)
    
    for draw_data in draw_history.values():
        winning_details = draw_data.get('winning_numbers_details', [])
        
        for detail in winning_details:
            freshness_bin = detail.get('current_freshness_bin', 0)
            category = detail.get('category', 'unknown')
            is_bonus = detail.get('is_bonus', False)
            
            bin_label = f"C{freshness_bin}"
            
            if is_bonus:
                bonus_by_category[category][bin_label] += 1
                bonus_total_by_category[category] += 1
            else:
                main_by_category[category][bin_label] += 1
                main_total_by_category[category] += 1
    
    # Calculate percentages
    main_percentages = {}
    for category in main_by_category:
        main_percentages[category] = {
            bin_label: (count / main_total_by_category[category] * 100)
            for bin_label, count in main_by_category[category].items()
        }
    
    bonus_percentages = {}
    for category in bonus_by_category:
        bonus_percentages[category] = {
            bin_label: (count / bonus_total_by_category[category] * 100)
            for bin_label, count in bonus_by_category[category].items()
        }
    
    return {
        'main_numbers': {
            'by_category': main_percentages,
            'totals': dict(main_total_by_category)
        },
        'bonus_numbers': {
            'by_category': bonus_percentages,
            'totals': dict(bonus_total_by_category)
        }
    }


def print_results(results: Dict):
    """Print analysis results in readable format."""
    
    print("\n" + "=" * 80)
    print("LOTTERY DRAW HISTORY ANALYSIS")
    print("=" * 80)
    
    # HMC Distribution
    print("\n" + "-" * 80)
    print("1. HMC PATTERN DISTRIBUTION")
    print("-" * 80)
    
    hmc = results['hmc_distribution']
    print(f"\nTotal Draws Analyzed: {hmc['total_draws']}")
    
    print("\nTop HMC Patterns:")
    for pattern, pct in list(hmc['hmc_pattern_distribution'].items())[:10]:
        print(f"  {pattern:>10} : {pct:>6.2f}%")
    
    print("\nMain Numbers by Category:")
    for category in ['hot', 'medium', 'cold']:
        pct = hmc['main_category_distribution'].get(category, 0)
        print(f"  {category.capitalize():>8} : {pct:>6.2f}%")
    
    print("\nBonus Numbers by Category:")
    for category in ['hot', 'medium', 'cold']:
        pct = hmc['bonus_category_distribution'].get(category, 0)
        print(f"  {category.capitalize():>8} : {pct:>6.2f}%")
    
    # Days Since Last Hit
    print("\n" + "-" * 80)
    print("2. DAYS SINCE LAST HIT DISTRIBUTION")
    print("-" * 80)
    
    days = results['days_since_last_hit']
    
    print("\nMAIN NUMBERS:")
    for category in ['hot', 'medium', 'cold']:
        if category in days['main_numbers']['by_category']:
            print(f"\n  {category.upper()} ({days['main_numbers']['totals'][category]} numbers):")
            bins = days['main_numbers']['by_category'][category]
            for bin_name in days['bins_used']:
                if bin_name in bins:
                    print(f"    {bin_name:>15} : {bins[bin_name]:>6.2f}%")
    
    print("\nBONUS NUMBERS:")
    for category in ['hot', 'medium', 'cold']:
        if category in days['bonus_numbers']['by_category']:
            print(f"\n  {category.upper()} ({days['bonus_numbers']['totals'][category]} numbers):")
            bins = days['bonus_numbers']['by_category'][category]
            for bin_name in days['bins_used']:
                if bin_name in bins:
                    print(f"    {bin_name:>15} : {bins[bin_name]:>6.2f}%")
    
    # Recent Counts
    print("\n" + "-" * 80)
    print("3. RECENT COUNTS DISTRIBUTION")
    print("-" * 80)
    
    recent = results['recent_counts']
    
    for key in recent.keys():
        window = key.replace('last_', '')
        print(f"\n{key.upper()} (Window: {window} draws):")
        
        print("  MAIN NUMBERS:")
        for category in ['hot', 'medium', 'cold']:
            if category in recent[key]['main_numbers']['by_category']:
                print(f"    {category.capitalize():>8}:", end='')
                counts = recent[key]['main_numbers']['by_category'][category]
                # Show top 5 most common counts
                sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
                for count, pct in sorted_counts:
                    print(f" {count}={pct:.1f}%", end='')
                print()
        
        print("  BONUS NUMBERS:")
        for category in ['hot', 'medium', 'cold']:
            if category in recent[key]['bonus_numbers']['by_category']:
                print(f"    {category.capitalize():>8}:", end='')
                counts = recent[key]['bonus_numbers']['by_category'][category]
                sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
                for count, pct in sorted_counts:
                    print(f" {count}={pct:.1f}%", end='')
                print()
    
    # Freshness Bins
    print("\n" + "-" * 80)
    print("4. FRESHNESS BIN DISTRIBUTION")
    print("-" * 80)
    
    fresh = results['freshness_patterns']
    
    print("\nMAIN NUMBERS:")
    for category in ['hot', 'medium', 'cold']:
        if category in fresh['main_numbers']['by_category']:
            print(f"  {category.capitalize():>8}:", end='')
            bins = fresh['main_numbers']['by_category'][category]
            sorted_bins = sorted(bins.items())
            for bin_name, pct in sorted_bins:
                print(f" {bin_name}={pct:.1f}%", end='')
            print()
    
    print("\nBONUS NUMBERS:")
    for category in ['hot', 'medium', 'cold']:
        if category in fresh['bonus_numbers']['by_category']:
            print(f"  {category.capitalize():>8}:", end='')
            bins = fresh['bonus_numbers']['by_category'][category]
            sorted_bins = sorted(bins.items())
            for bin_name, pct in sorted_bins:
                print(f" {bin_name}={pct:.1f}%", end='')
            print()
    
    # Bonus-Specific Patterns
    print("\n" + "-" * 80)
    print("5. BONUS-SPECIFIC PATTERNS")
    print("-" * 80)
    
    bonus = results['bonus_patterns']
    
    print("\nBonus Ball Category Preference:")
    for category, pct in bonus['bonus_category_distribution'].items():
        print(f"  {category.capitalize():>8} : {pct:>6.2f}%")
    
    print("\nBonus Ball Was Recent Bonus:")
    for status, pct in bonus['bonus_was_recent_bonus'].items():
        print(f"  {status:>22} : {pct:>6.2f}%")
    
    print("\nMain Numbers That Were Recent Bonus:")
    main_bonus = bonus['main_numbers_that_were_recent_bonus']
    print(f"  Count     : {main_bonus['count']}")
    print(f"  Total     : {main_bonus['total']}")
    print(f"  Percentage: {main_bonus['percentage']:>6.2f}%")
    
    print("\nBonus Hit Contribution Stats:")
    contrib = bonus['bonus_hit_contribution_stats']
    print(f"  Average: {contrib['avg']:.4f}")
    print(f"  Min    : {contrib['min']:.4f}")
    print(f"  Max    : {contrib['max']:.4f}")
    
    print("\n" + "=" * 80)


def save_results(results: Dict, output_file: str = 'data/lotto_statistics_analysis.json'):
    """Save analysis results to JSON file."""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"\n✓ Results saved to {output_file}")
    except Exception as e:
        print(f"\n✗ Error saving results: {e}")


def main():
    """Main execution function."""
    
    print("Loading draw history...")
    draw_history = load_draw_history()
    
    print(f"Loaded {len(draw_history)} draws")
    
    print("\nDetecting recent count parameters...")
    recent_keys = get_dynamic_recent_count_keys(draw_history)
    print(f"Found {len(recent_keys)} recent count windows: {recent_keys}")
    
    print("\nAnalyzing HMC distribution...")
    hmc_results = analyze_hmc_distribution(draw_history)
    
    print("Analyzing days since last hit...")
    days_results = analyze_days_since_last_hit(draw_history)
    
    print("Analyzing recent counts...")
    recent_results = analyze_recent_counts(draw_history, recent_keys)
    
    print("Analyzing freshness patterns...")
    freshness_results = analyze_freshness_patterns(draw_history)
    
    print("Analyzing bonus-specific patterns...")
    bonus_results = analyze_bonus_patterns(draw_history)
    
    # Combine all results
    results = {
        'hmc_distribution': hmc_results,
        'days_since_last_hit': days_results,
        'recent_counts': recent_results,
        'freshness_patterns': freshness_results,
        'bonus_patterns': bonus_results,
        'metadata': {
            'total_draws': len(draw_history),
            'recent_count_windows': recent_keys,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    
    # Print results
    print_results(results)
    
    # Save to file
    save_results(results)


if __name__ == "__main__":
    main()