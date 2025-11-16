#!/usr/bin/env python
"""
ensemble.py
===========
Simple ensemble voting system - runs quickpick multiple times and aggregates results.

Usage:
    From project root:
        python analysis/ensemble.py --runs 15

    From analysis folder:
        python ensemble.py --runs 15

Note: This script must be run from the project root directory where quickpick.py is located.
"""

import re
import argparse
import os
import sys
from collections import Counter
from pathlib import Path

# Ensure we're running from project root
if not Path('quickpick.py').exists():
    print("ERROR: This script must be run from the project root directory.")
    print("Current directory:", os.getcwd())
    print("\nUsage from project root:")
    print("  python analysis/ensemble.py --runs 15")
    sys.exit(1)


def extract_numbers_from_file(filepath: str = 'lottery_picks.txt') -> dict:
    """
    Extract lottery numbers from lottery_picks.txt file.

    Returns:
        dict: {model_1: {main: [...], bonus: X}, model_2: {...}, model_3: {...}}
    """
    results = {}

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract for each model using line markers
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Look for "Line 1:", "Line 2:", "Line 3:"
            if line.startswith('Line 1:'):
                model_key = 'model_1'
            elif line.startswith('Line 2:'):
                model_key = 'model_2'
            elif line.startswith('Line 3:'):
                model_key = 'model_3'
            else:
                continue

            # Initialize model entry
            if model_key not in results:
                results[model_key] = {'main': [], 'bonus': None}

            # Look ahead for main numbers
            main_found = False
            bonus_found = False
            for j in range(i, min(i+10, len(lines))):
                if not main_found and 'Main Numbers (6):' in lines[j]:
                    # Extract numbers like: "Main Numbers (6): [6, 10, 20, 21, 35, 42]"
                    match = re.search(r'\[([0-9, ]+)\]', lines[j])
                    if match:
                        numbers_str = match.group(1)
                        numbers = [int(n.strip()) for n in numbers_str.split(',')]
                        results[model_key]['main'] = numbers
                        main_found = True

                # Look for bonus
                if not bonus_found and 'Bonus Ball:' in lines[j] and 'None' not in lines[j]:
                    match = re.search(r'Bonus Ball:\s*(\d+)', lines[j])
                    if match:
                        results[model_key]['bonus'] = int(match.group(1))
                        bonus_found = True

                # Break early if we found both
                if main_found and (bonus_found or 'Bonus Ball: None' in lines[j]):
                    break

    except FileNotFoundError:
        print(f"Error: {filepath} not found")
        return {}

    return results


def run_ensemble(num_runs: int = 15):
    """
    Run quickpick multiple times and aggregate results.

    Args:
        num_runs: Number of times to run quickpick
    """
    import subprocess
    import sys

    print("=" * 70)
    print(f"ENSEMBLE LOTTERY PREDICTION ({num_runs} runs)")
    print("=" * 70)
    print(f"Running quickpick.py {num_runs} times with different random seeds...")
    print("This will take a few minutes...\n")

    # Store all results
    all_results = {
        'model_1': {'numbers': [], 'bonuses': []},
        'model_2': {'numbers': [], 'bonuses': []},
        'model_3': {'numbers': [], 'bonuses': []}
    }

    # Temporarily modify config to change random seed each run
    config_file = Path('ml_lotto/config.py')
    original_content = config_file.read_text()

    for run_idx in range(num_runs):
        seed = 42 + run_idx

        print(f"Run {run_idx + 1}/{num_runs} (seed={seed})...", end='', flush=True)

        # Modify config with new seed
        modified_content = re.sub(
            r'RANDOM_SEED_BASE = \d+',
            f'RANDOM_SEED_BASE = {seed}',
            original_content
        )

        # Also update the model configs
        modified_content = re.sub(
            r"'random_state':\s*\d+",
            f"'random_state': {seed}",
            modified_content
        )

        config_file.write_text(modified_content)

        # Run quickpick
        try:
            result = subprocess.run(
                [sys.executable, 'quickpick.py'],
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parse results from lottery_picks.txt
            picks = extract_numbers_from_file('lottery_picks.txt')

            if picks:
                for model_key in ['model_1', 'model_2', 'model_3']:
                    if model_key in picks:
                        all_results[model_key]['numbers'].extend(picks[model_key]['main'])
                        if picks[model_key]['bonus']:
                            all_results[model_key]['bonuses'].append(picks[model_key]['bonus'])

                print(" ✓")
            else:
                print(" ✗ (no results)")

        except subprocess.TimeoutExpired:
            print(" ✗ (timeout)")
        except Exception as e:
            print(f" ✗ ({e})")

    # Restore original config
    config_file.write_text(original_content)

    print(f"\n✓ Completed {num_runs} runs\n")

    # Aggregate and display results
    display_ensemble_results(all_results, num_runs)


def display_ensemble_results(all_results: dict, num_runs: int):
    """
    Display ensemble results with frequency analysis.

    Args:
        all_results: Dictionary with all collected results
        num_runs: Total number of runs
    """
    model_names = {
        'model_1': 'Model 1: Short-Term Momentum',
        'model_2': 'Model 2: Jackpot Optimizer',
        'model_3': 'Model 3: Complex Pattern Discovery'
    }

    print("=" * 70)
    print("ENSEMBLE VOTING RESULTS")
    print("=" * 70)

    for model_key in ['model_1', 'model_2', 'model_3']:
        print(f"\n{model_names[model_key]} ({num_runs} runs)")
        print("-" * 70)

        # Count number frequencies
        number_counter = Counter(all_results[model_key]['numbers'])
        bonus_counter = Counter(all_results[model_key]['bonuses'])

        # Calculate frequencies (each run picks 6 numbers)
        number_freq = {
            num: count / num_runs
            for num, count in number_counter.items()
        }

        # Sort by frequency
        sorted_numbers = sorted(
            number_freq.items(),
            key=lambda x: (-x[1], x[0])
        )

        print(f"\n{'Rank':<6} {'Number':<8} {'Frequency':<12} {'Confidence'}")
        print("-" * 70)

        for rank, (num, freq) in enumerate(sorted_numbers[:20], 1):
            confidence = (
                "★★★ Very High" if freq >= 0.80 else
                "★★☆ High" if freq >= 0.60 else
                "★☆☆ Medium" if freq >= 0.40 else
                "☆☆☆ Low"
            )
            print(f"{rank:<6} #{num:<7} {freq:>6.1%}       {confidence}")

        # Recommend top 6
        top_6 = sorted([num for num, freq in sorted_numbers[:6]])
        print(f"\nRECOMMENDED LINE: {top_6}")

        print("  Confidence breakdown:")
        for num in top_6:
            freq = number_freq.get(num, 0)
            print(f"    #{num:2d}: {freq:>6.1%}")

        # Bonus recommendation
        if bonus_counter:
            top_bonus = max(bonus_counter.items(), key=lambda x: x[1])
            bonus_num, bonus_count = top_bonus
            bonus_freq = bonus_count / num_runs
            print(f"\nBONUS BALL: #{bonus_num} ({bonus_freq:.1%} frequency)")

    print("\n" + "=" * 70)
    print("INTERPRETATION GUIDE")
    print("=" * 70)
    print("★★★ Very High (80%+):  Appeared in 80%+ of runs - top priority")
    print("★★☆ High (60-80%):     Very consistent picks")
    print("★☆☆ Medium (40-60%):   Moderately reliable")
    print("☆☆☆ Low (<40%):        Less consistent - consider alternatives")
    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Ensemble voting for lottery predictions'
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=15,
        help='Number of ensemble runs (default: 15)'
    )
    args = parser.parse_args()

    run_ensemble(args.runs)


if __name__ == '__main__':
    main()
