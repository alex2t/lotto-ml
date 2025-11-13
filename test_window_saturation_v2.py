#!/usr/bin/env python3
"""
test_window_saturation_v2.py
=============================
Test and demonstration script for the improved window saturation feature (V2.0)

This script demonstrates:
1. Loading the new JSON configuration
2. Comparing V1.0 (hardcoded) vs V2.0 (JSON-driven) calculations
3. Category-aware penalty adjustments
4. Window weighting
5. Statistical analysis

Run: python test_window_saturation_v2.py
"""

import json
import sys
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, '.')

from ml_lotto.features.window_saturation import (
    calculate_window_saturation_score,
    get_saturation_explanation,
    get_saturation_statistics,
    load_saturation_config
)


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def load_test_data() -> tuple:
    """Load HMC and odds data for testing"""
    print_section("Loading Test Data")

    try:
        with open('data/lotto_trigger_periods.json', 'r') as f:
            hmc_data = json.load(f)
        print("✓ Loaded lotto_trigger_periods.json")

        with open('data/lotto_odds_results.json', 'r') as f:
            odds_data = json.load(f)
        print("✓ Loaded lotto_odds_results.json")

        return hmc_data, odds_data

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Make sure you're running this from the project root directory")
        sys.exit(1)


def show_configuration():
    """Display the current configuration"""
    print_section("Configuration Overview")

    config = load_saturation_config()

    print("\n📋 Penalty Thresholds:")
    for threshold_name, threshold_data in config['penalty_thresholds'].items():
        print(f"\n  {threshold_name.replace('_', ' ').title()}:")
        print(f"    Base Multiplier: {threshold_data['base_multiplier']}")
        print(f"    Category Adjustments:")
        for cat, adj in threshold_data['category_adjustments'].items():
            print(f"      - {cat}: {adj}x (effective: {threshold_data['base_multiplier'] * adj:.2f})")

    print("\n🎯 Window Weights:")
    for window, weight in config['window_weights'].items():
        print(f"    Window size {window}: {weight}x")

    print("\n⚙️  Advanced Settings:")
    for setting, value in config['advanced_settings'].items():
        print(f"    {setting}: {value}")


def demonstrate_calculation(hmc_data: Dict, odds_data: Dict):
    """Demonstrate detailed calculation for specific numbers"""
    print_section("Detailed Calculation Examples")

    # Calculate scores
    scores = calculate_window_saturation_score(hmc_data, odds_data)

    # Find interesting examples: high, medium, and low saturation
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    examples = {
        'High Saturation': sorted_scores[0],
        'Medium Saturation': sorted_scores[len(sorted_scores)//2],
        'Low/No Saturation': sorted_scores[-1]
    }

    for label, (num, score) in examples.items():
        print(f"\n{label} Example:")
        print("-" * 60)
        explanation = get_saturation_explanation(num, score, hmc_data, odds_data)
        print(explanation)


def compare_categories(hmc_data: Dict, odds_data: Dict):
    """Compare saturation scores by category"""
    print_section("Category-Aware Penalty Comparison")

    scores = calculate_window_saturation_score(hmc_data, odds_data)
    stats = get_saturation_statistics(scores, hmc_data)

    print("\n📊 Overall Statistics:")
    print(f"  Total Numbers: {stats['total_numbers']}")
    print(f"  Average Saturation: {stats['avg_saturation']:.3f}")
    print(f"  Max Saturation: {stats['max_saturation']:.3f}")
    print(f"  Min Saturation: {stats['min_saturation']:.3f}")
    print(f"\n  Distribution:")
    print(f"    High Saturation (>0.5): {stats['saturated_count']} numbers")
    print(f"    Moderate (0.2-0.5): {stats['moderate_saturation_count']} numbers")
    print(f"    Low (0.0-0.2): {stats['low_saturation_count']} numbers")
    print(f"    None (0.0): {stats['no_saturation_count']} numbers")

    print("\n📈 By Category:")
    for category, cat_stats in stats['by_category'].items():
        print(f"\n  {category.upper()}:")
        print(f"    Count: {cat_stats['count']} numbers")
        print(f"    Avg Saturation: {cat_stats['avg_saturation']:.3f}")
        print(f"    Max Saturation: {cat_stats['max_saturation']:.3f}")
        print(f"    Saturated (>0.5): {cat_stats['saturated_count']} numbers")


def show_top_saturated(hmc_data: Dict, odds_data: Dict, top_n: int = 10):
    """Show the most saturated numbers"""
    print_section(f"Top {top_n} Most Saturated Numbers")

    scores = calculate_window_saturation_score(hmc_data, odds_data)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    print("\n{:<8} {:<12} {:<10} {:<15}".format(
        "Number", "Category", "Penalty", "Recent Counts"
    ))
    print("-" * 60)

    for num, score in sorted_scores[:top_n]:
        num_str = str(num)
        category = hmc_data.get(num_str, {}).get('category', 'unknown')
        recent = hmc_data.get(num_str, {}).get('recent', {})
        recent_str = f"4:{recent.get('last_4', 0)} 9:{recent.get('last_9', 0)}"

        print("{:<8} {:<12} {:<10.3f} {:<15}".format(
            num, category, score, recent_str
        ))


def simulate_config_changes():
    """Demonstrate the effect of configuration changes"""
    print_section("Configuration Impact Simulation")

    print("\n💡 What-If Scenarios:")
    print("\n1. Increasing hot number penalties by 50%:")
    print("   Edit config: penalty_thresholds.at_or_exceeding.category_adjustments.hot = 1.8")
    print("   Result: Hot numbers approaching saturation get ~50% higher penalties")

    print("\n2. Emphasizing short-term windows:")
    print("   Edit config: window_weights.5 = 1.2, window_weights.10 = 0.8")
    print("   Result: Recent patterns (5 draws) weighted more heavily")

    print("\n3. Using average instead of max penalty:")
    print("   Edit config: advanced_settings.combine_multiple_scenarios = 'avg'")
    print("   Result: Smooths penalties across multiple window scenarios")

    print("\n4. Lowering penalty cap:")
    print("   Edit config: advanced_settings.penalty_cap = 0.75")
    print("   Result: Maximum penalty limited to 0.75 instead of 1.0")


def main():
    """Main test execution"""
    print("\n" + "=" * 80)
    print("  WINDOW SATURATION V2.0 - TEST & DEMONSTRATION")
    print("  JSON-Driven Configuration System")
    print("=" * 80)

    # Load data
    hmc_data, odds_data = load_test_data()

    # Show configuration
    show_configuration()

    # Demonstrate calculations
    demonstrate_calculation(hmc_data, odds_data)

    # Compare categories
    compare_categories(hmc_data, odds_data)

    # Show top saturated
    show_top_saturated(hmc_data, odds_data, top_n=10)

    # Simulate config changes
    simulate_config_changes()

    print_section("Test Complete")
    print("\n✅ All demonstrations completed successfully!")
    print("\n📖 For more information, see: docs/WINDOW_SATURATION_IMPROVEMENTS.md")
    print("⚙️  To customize behavior, edit: data/lotto_window_saturation_config.json")
    print()


if __name__ == '__main__':
    main()
