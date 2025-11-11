"""
window_saturation.py
====================
Calculate window saturation penalties based on lotto_odds_results.json scenarios.

Penalizes numbers that are approaching or exceeding rare high-frequency thresholds,
making them less likely to be selected if they've been appearing too frequently.
"""

from typing import Dict, Any, List


def calculate_window_saturation_score(
    hmc_data: Dict[str, Any],
    odds_data: Dict[str, Any],
    max_number: int = 47
) -> Dict[int, float]:
    """
    Calculate saturation penalty scores for all numbers based on window odds.

    Args:
        hmc_data: HMC trigger periods data (contains recent counts)
        odds_data: Odds results data (contains scenario thresholds and odds)
        max_number: Maximum lottery number

    Returns:
        Dictionary mapping number -> saturation_penalty_score (0.0 = no penalty, 1.0 = max penalty)

    Logic:
        For each scenario (window_size, target_times):
        - If number appeared >= target_times in window: STRONG penalty (odds are low)
        - If number appeared (target_times - 1) in smaller window: MODERATE penalty (approaching threshold)
        - If number appeared (target_times - 2) in smaller window: LIGHT penalty

    Example:
        Scenario: window=10, target=4_times, odds=24.4%
        Number 12: last_9=3
        - 3 appearances in 9 draws means it's likely to hit 4 in 10 (approaching rare threshold)
        - Apply moderate penalty (0.5)
    """
    saturation_scores = {}

    # Get scenarios from odds data
    scenarios = odds_data.get('scenarios', [])

    for num in range(1, max_number + 1):
        num_str = str(num)

        if num_str not in hmc_data:
            saturation_scores[num] = 0.0
            continue

        recent_data = hmc_data[num_str].get('recent', {})

        # Calculate maximum saturation across all scenarios
        max_saturation = 0.0

        for scenario in scenarios:
            window_size = scenario.get('window_size')
            results = scenario.get('results', {})

            # Get the target threshold from results (e.g., "4_times" -> 4)
            for target_key, target_stats in results.items():
                target_count = int(target_key.split('_')[0])
                odds = target_stats.get('odds', 1.0)

                # Find the closest recent window we have data for
                # Try exact match first, then closest smaller window
                recent_key = f'last_{window_size}'
                recent_count = recent_data.get(recent_key)

                # If exact window not available, try closest smaller window
                if recent_count is None:
                    # Try smaller windows
                    for try_window in [window_size - 1, window_size - 2, window_size - 3]:
                        if try_window > 0:
                            recent_key = f'last_{try_window}'
                            recent_count = recent_data.get(recent_key)
                            if recent_count is not None:
                                break

                if recent_count is None:
                    continue

                # Calculate saturation penalty based on how close to threshold
                # The LOWER the odds, the HIGHER the penalty for approaching threshold
                rarity_factor = 1.0 - odds  # Low odds = high rarity = high penalty

                if recent_count >= target_count:
                    # Already at or exceeding threshold - STRONG penalty
                    saturation = 1.0 * rarity_factor
                elif recent_count == target_count - 1:
                    # One away from threshold - MODERATE penalty
                    saturation = 0.6 * rarity_factor
                elif recent_count == target_count - 2:
                    # Two away from threshold - LIGHT penalty
                    saturation = 0.3 * rarity_factor
                else:
                    saturation = 0.0

                max_saturation = max(max_saturation, saturation)

        saturation_scores[num] = max_saturation

    return saturation_scores


def get_saturation_explanation(
    number: int,
    saturation_score: float,
    hmc_data: Dict[str, Any],
    odds_data: Dict[str, Any]
) -> str:
    """
    Generate human-readable explanation for a number's saturation score.

    Args:
        number: The lottery number
        saturation_score: The calculated saturation score
        hmc_data: HMC trigger periods data
        odds_data: Odds results data

    Returns:
        Explanation string
    """
    if saturation_score < 0.1:
        return f"Number {number}: No saturation (score={saturation_score:.2f})"

    num_str = str(number)
    recent_data = hmc_data.get(num_str, {}).get('recent', {})

    explanation_parts = [f"Number {number}: Saturation penalty {saturation_score:.2f}"]

    scenarios = odds_data.get('scenarios', [])
    for scenario in scenarios:
        window_size = scenario.get('window_size')
        results = scenario.get('results', {})

        for target_key, target_stats in results.items():
            target_count = int(target_key.split('_')[0])
            odds = target_stats.get('odds', 1.0)

            recent_key = f'last_{window_size}'
            recent_count = recent_data.get(recent_key)

            if recent_count is not None and recent_count >= target_count - 2:
                explanation_parts.append(
                    f"  - Window {window_size}: {recent_count} times "
                    f"(threshold {target_count} has {odds*100:.1f}% odds)"
                )

    return "\n".join(explanation_parts)
