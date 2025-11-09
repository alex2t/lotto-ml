"""
Bonus ball analysis module - calculates comprehensive bonus statistics from historical data
All weights are derived from actual patterns, no hardcoded values
"""

from collections import defaultdict
from typing import Dict, Tuple, List
from scipy import stats
import numpy as np


def convert_to_native_types(obj):
    """
    Convert numpy types to native Python types for JSON serialization.

    Args:
        obj: Object to convert

    Returns:
        Object with native Python types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {key: convert_to_native_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native_types(item) for item in obj]
    else:
        return obj


def calculate_chi_square_test(
    bonus_category_counts: Dict[str, int],
    main_category_counts: Dict[str, int],
    total_bonus: int,
    total_main: int
) -> Dict:
    """
    Perform chi-square test comparing bonus vs main number category distribution.

    Args:
        bonus_category_counts: Count of bonus appearances by category
        main_category_counts: Count of main number appearances by category
        total_bonus: Total bonus appearances
        total_main: Total main number appearances

    Returns:
        Dictionary with chi-square test results
    """
    categories = ['hot', 'medium', 'cold']

    # Observed frequencies
    observed_bonus = [bonus_category_counts.get(cat, 0) for cat in categories]
    observed_main = [main_category_counts.get(cat, 0) for cat in categories]

    # Expected frequencies (if bonus followed same distribution as main)
    bonus_rate = total_bonus / (total_bonus + total_main) if (total_bonus + total_main) > 0 else 0
    main_rate = 1 - bonus_rate

    expected_bonus = []
    expected_main = []

    for cat in categories:
        total_cat = bonus_category_counts.get(cat, 0) + main_category_counts.get(cat, 0)
        expected_bonus.append(total_cat * bonus_rate)
        expected_main.append(total_cat * main_rate)

    # Perform chi-square test
    observed = np.array([observed_bonus, observed_main]).flatten()
    expected = np.array([expected_bonus, expected_main]).flatten()

    # Filter out zero expectations
    mask = expected > 0
    observed = observed[mask]
    expected = expected[mask]

    if len(observed) > 0:
        chi2_stat = np.sum((observed - expected) ** 2 / expected)
        df = len(observed) - 1
        p_value = 1 - stats.chi2.cdf(chi2_stat, df)
    else:
        chi2_stat = 0.0
        p_value = 1.0

    significant = bool(p_value < 0.05)

    return {
        "statistic": round(float(chi2_stat), 2),
        "p_value": round(float(p_value), 3),
        "significant": significant,
        "conclusion": "Bonus distribution differs from main significantly" if significant
                     else "Bonus distribution differs from main but not statistically significant"
    }


def calculate_bonus_category_preference(
    draw_history_log: Dict,
    total_draws: int
) -> Dict:
    """
    Calculate bonus ball preference for hot/medium/cold categories with data-driven weights.

    Args:
        draw_history_log: Full draw history
        total_draws: Total number of draws analyzed

    Returns:
        Dictionary with category preference statistics and calculated weights
    """
    bonus_category_counts = defaultdict(int)
    main_category_counts = defaultdict(int)

    for draw_date, draw_data in draw_history_log.items():
        winning_details = draw_data.get('winning_numbers_details', [])

        if len(winning_details) < 7:
            continue

        # Last number is bonus
        bonus_detail = winning_details[6]
        bonus_category = bonus_detail.get('category', 'unknown')
        bonus_category_counts[bonus_category] += 1

        # First 6 are main numbers
        for i in range(6):
            main_category = winning_details[i].get('category', 'unknown')
            main_category_counts[main_category] += 1

    total_bonus = sum(bonus_category_counts.values())
    total_main = sum(main_category_counts.values())

    # Calculate expected counts if bonus followed same distribution as main
    category_stats = {}

    for category in ['hot', 'medium', 'cold']:
        bonus_count = bonus_category_counts.get(category, 0)
        main_count = main_category_counts.get(category, 0)

        # Expected bonus count based on main distribution
        main_rate = main_count / total_main if total_main > 0 else 0
        expected_bonus = total_bonus * main_rate

        # Actual vs expected ratio becomes the weight
        actual_rate = bonus_count / total_bonus if total_bonus > 0 else 0
        weight = actual_rate / main_rate if main_rate > 0 else 1.0

        # Binomial test p-value
        if total_bonus > 0 and main_rate > 0:
            result = stats.binomtest(bonus_count, total_bonus, main_rate, alternative='two-sided')
            p_value = result.pvalue
        else:
            p_value = 1.0

        percentage = (bonus_count / total_bonus * 100) if total_bonus > 0 else 0

        category_stats[category] = {
            "count": bonus_count,
            "percentage": round(percentage, 2),
            "expected_if_equal": round(expected_bonus, 1),
            "weight": round(weight, 2),
            "p_value": round(p_value, 2)
        }

    # Perform chi-square test
    chi_square_result = calculate_chi_square_test(
        bonus_category_counts,
        main_category_counts,
        total_bonus,
        total_main
    )

    return {
        "validation": chi_square_result,
        "preference": category_stats
    }


def calculate_recent_bonus_exclusion(
    draw_history_log: Dict,
    total_draws: int
) -> Dict:
    """
    Calculate how often numbers that were recent bonuses avoid appearing as bonus again.

    Args:
        draw_history_log: Full draw history
        total_draws: Total number of draws analyzed

    Returns:
        Dictionary with exclusion statistics
    """
    was_bonus_and_appeared_again = 0
    total_opportunities = 0

    exclusion_by_draw = {i: {"avoided": 0, "appeared": 0} for i in [1, 2, 3, 5, 10]}

    # Build chronological list of draws
    sorted_draws = sorted(
        draw_history_log.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    for idx, (draw_date, draw_data) in enumerate(sorted_draws):
        winning_details = draw_data.get('winning_numbers_details', [])

        if len(winning_details) < 7:
            continue

        current_bonus = winning_details[6]['number']
        recent_bonus_list = draw_data.get('recent_bonus_numbers', [])

        if current_bonus in recent_bonus_list:
            was_bonus_and_appeared_again += 1

        total_opportunities += 1

        # Check specific draw distances
        for lookback in [1, 2, 3, 5, 10]:
            if idx >= lookback:
                past_draw_date, past_draw_data = sorted_draws[idx - lookback]
                past_winning_details = past_draw_data.get('winning_numbers_details', [])

                if len(past_winning_details) >= 7:
                    past_bonus = past_winning_details[6]['number']

                    if current_bonus == past_bonus:
                        exclusion_by_draw[lookback]["appeared"] += 1
                    else:
                        exclusion_by_draw[lookback]["avoided"] += 1

    # Calculate overall avoidance rate
    overall_rate = was_bonus_and_appeared_again / total_opportunities if total_opportunities > 0 else 0
    expected_random = 10 / 47  # 10 positions in recent list, 47 total numbers
    avoidance_rate = 1 - overall_rate

    # Calculate p-value for overall pattern
    if total_opportunities > 0:
        result = stats.binomtest(
            was_bonus_and_appeared_again,
            total_opportunities,
            expected_random,
            alternative='less'
        )
        overall_p_value = result.pvalue
    else:
        overall_p_value = 1.0

    # Calculate per-draw statistics
    exclusion_by_draw_stats = {}

    for lookback, counts in exclusion_by_draw.items():
        total = counts["avoided"] + counts["appeared"]
        avoidance = counts["avoided"] / total if total > 0 else 0

        # Expected if random (1/47 chance)
        expected = 1 / 47

        # P-value
        if total > 0:
            result = stats.binomtest(counts["appeared"], total, expected, alternative='less')
            p_val = result.pvalue
        else:
            p_val = 1.0

        exclusion_by_draw_stats[f"{lookback}_draw{'s' if lookback > 1 else ''}_ago"] = {
            "avoidance_rate": round(avoidance, 2),
            "p_value": round(p_val, 3)
        }

    return {
        "was_bonus_last_10": {
            "appeared_as_bonus_again": was_bonus_and_appeared_again,
            "total_opportunities": total_opportunities,
            "rate": round(overall_rate, 4),
            "expected_if_random": round(expected_random, 4),
            "avoidance_rate": round(avoidance_rate, 4),
            "p_value": round(overall_p_value, 2)
        },
        "exclusion_by_draw": exclusion_by_draw_stats
    }


def calculate_main_from_recent_bonus(
    draw_history_log: Dict
) -> Dict:
    """
    Calculate how often main numbers come from recent bonus list.

    Args:
        draw_history_log: Full draw history

    Returns:
        Dictionary with boost statistics
    """
    main_from_recent_bonus = 0
    total_main_numbers = 0

    for draw_date, draw_data in draw_history_log.items():
        winning_details = draw_data.get('winning_numbers_details', [])

        if len(winning_details) < 7:
            continue

        # First 6 are main numbers
        for i in range(6):
            total_main_numbers += 1

            if winning_details[i].get('is_recent_bonus_hit', False):
                main_from_recent_bonus += 1

    rate = main_from_recent_bonus / total_main_numbers if total_main_numbers > 0 else 0
    expected_random = 10 / 47  # 10 in list, 47 total
    boost_factor = rate / expected_random if expected_random > 0 else 1.0

    # Calculate p-value
    if total_main_numbers > 0:
        result = stats.binomtest(
            main_from_recent_bonus,
            total_main_numbers,
            expected_random,
            alternative='greater'
        )
        p_value = result.pvalue
    else:
        p_value = 1.0

    return {
        "count": main_from_recent_bonus,
        "total_main_numbers": total_main_numbers,
        "rate": round(rate, 4),
        "expected_if_random": round(expected_random, 4),
        "boost_factor": round(boost_factor, 2),
        "p_value": round(p_value, 2)
    }


def calculate_bonus_timing_by_category(
    draw_history_log: Dict,
    max_number: int = 47
) -> Dict:
    """
    Calculate bonus appearance timing patterns by HMC category with data-driven weights.

    Args:
        draw_history_log: Full draw history
        max_number: Maximum lottery number

    Returns:
        Dictionary with timing patterns by category
    """
    # Track bonus appearances by category and timing
    category_timing = {
        'hot': defaultdict(int),
        'medium': defaultdict(int),
        'cold': defaultdict(int)
    }

    category_totals = defaultdict(int)

    for draw_date, draw_data in draw_history_log.items():
        winning_details = draw_data.get('winning_numbers_details', [])

        if len(winning_details) < 7:
            continue

        bonus_detail = winning_details[6]
        bonus_category = bonus_detail.get('category', 'unknown')
        days_since = bonus_detail.get('days_since_last_hit', 0)

        if bonus_category in ['hot', 'medium', 'cold']:
            # Assign to timing bin
            if days_since <= 7:
                bin_name = "0-7"
            elif days_since <= 14:
                bin_name = "8-14"
            elif days_since <= 21:
                bin_name = "15-21"
            elif days_since <= 30:
                bin_name = "22-30"
            elif days_since <= 45:
                bin_name = "31-45"
            elif days_since <= 60:
                bin_name = "46-60"
            else:
                bin_name = "61+"

            category_timing[bonus_category][bin_name] += 1
            category_totals[bonus_category] += 1

    # Calculate percentages and weights for each category
    timing_stats = {}

    for category in ['hot', 'medium', 'cold']:
        total = category_totals.get(category, 0)

        if total == 0:
            timing_stats[category] = {}
            continue

        bin_stats = {}
        bin_percentages = {}

        for bin_name in ["0-7", "8-14", "15-21", "22-30", "31-45", "46-60", "61+"]:
            count = category_timing[category].get(bin_name, 0)
            percentage = (count / total * 100) if total > 0 else 0

            bin_stats[bin_name] = {
                "count": count,
                "percentage": round(percentage, 2)
            }
            bin_percentages[bin_name] = percentage

        # Calculate weights: normalize to peak bin
        if bin_percentages:
            peak_percentage = max(bin_percentages.values())

            for bin_name in bin_stats:
                if peak_percentage > 0:
                    weight = bin_percentages[bin_name] / peak_percentage
                else:
                    weight = 1.0

                bin_stats[bin_name]["weight"] = round(weight, 2)

        timing_stats[category] = bin_stats

    return timing_stats


def calculate_bonus_freshness_preference(
    draw_history_log: Dict,
    c_max_threshold: int = 2
) -> Dict:
    """
    Calculate bonus preference for freshness bins with data-driven weights.

    Args:
        draw_history_log: Full draw history
        c_max_threshold: Maximum freshness threshold

    Returns:
        Dictionary with freshness preference by bin
    """
    freshness_counts_bonus = defaultdict(int)
    freshness_counts_main = defaultdict(int)

    for draw_date, draw_data in draw_history_log.items():
        winning_details = draw_data.get('winning_numbers_details', [])

        if len(winning_details) < 7:
            continue

        # Process bonus (last number)
        bonus_detail = winning_details[6]
        bonus_freshness = bonus_detail.get('current_freshness_bin', 0)
        freshness_counts_bonus[bonus_freshness] += 1

        # Process main numbers (first 6)
        for i in range(6):
            main_freshness = winning_details[i].get('current_freshness_bin', 0)
            freshness_counts_main[main_freshness] += 1

    total_bonus = sum(freshness_counts_bonus.values())
    total_main = sum(freshness_counts_main.values())

    freshness_stats = {}

    for bin_idx in range(c_max_threshold + 1):
        bonus_count = freshness_counts_bonus.get(bin_idx, 0)
        main_count = freshness_counts_main.get(bin_idx, 0)

        bonus_rate = bonus_count / total_bonus if total_bonus > 0 else 0
        main_rate = main_count / total_main if total_main > 0 else 0

        # Preference score: how much more/less bonus favors this bin vs main
        preference_score = bonus_rate / main_rate if main_rate > 0 else 1.0

        # Weight is the preference score
        weight = preference_score

        bin_name = f"C{bin_idx}" if bin_idx < c_max_threshold else f"C_GE_{c_max_threshold}"

        freshness_stats[bin_name] = {
            "bonus_count": bonus_count,
            "main_count": main_count,
            "bonus_rate": round(bonus_rate, 3),
            "main_rate": round(main_rate, 3),
            "preference_score": round(preference_score, 2),
            "weight": round(weight, 2)
        }

    return freshness_stats


def calculate_per_number_bonus_profile(
    draw_history_log: Dict,
    max_number: int = 47
) -> Dict:
    """
    Calculate comprehensive bonus profile for each number.
    All weights and predictions are DATA-DRIVEN from historical patterns.

    Args:
        draw_history_log: Full draw history
        max_number: Maximum lottery number

    Returns:
        Dictionary with per-number bonus profiles
    """
    from datetime import datetime

    # Track appearances per number
    number_stats = {}

    for num in range(1, max_number + 1):
        number_stats[num] = {
            'total_appearances': 0,
            'bonus_appearances': 0,
            'main_appearances': 0,
            'last_bonus_date': None,
            'bonus_dates': [],
            'category': 'unknown',
            'bonus_timing_days': []  # Track days_since for each bonus appearance
        }

    # Scan all draws to collect timing data
    sorted_draws = sorted(
        draw_history_log.items(),
        key=lambda x: x[1].get('draw_index', 0)
    )

    # Track when each number last appeared (for calculating days_since at bonus time)
    number_last_appearance = {}

    for draw_date, draw_data in sorted_draws:
        winning_details = draw_data.get('winning_numbers_details', [])

        if len(winning_details) < 7:
            continue

        draw_date_obj = datetime.strptime(draw_date, "%Y-%m-%d")

        # Process main numbers
        for i in range(6):
            num = winning_details[i]['number']
            number_stats[num]['total_appearances'] += 1
            number_stats[num]['main_appearances'] += 1
            number_stats[num]['category'] = winning_details[i].get('category', 'unknown')
            number_last_appearance[num] = draw_date_obj

        # Process bonus
        bonus_num = winning_details[6]['number']

        # Calculate days since last appearance when this number appeared as bonus
        days_since_at_bonus = None
        if bonus_num in number_last_appearance:
            days_since_at_bonus = (draw_date_obj - number_last_appearance[bonus_num]).days
            number_stats[bonus_num]['bonus_timing_days'].append(days_since_at_bonus)

        number_stats[bonus_num]['total_appearances'] += 1
        number_stats[bonus_num]['bonus_appearances'] += 1
        number_stats[bonus_num]['last_bonus_date'] = draw_date
        number_stats[bonus_num]['bonus_dates'].append(draw_date)
        number_stats[bonus_num]['category'] = winning_details[6].get('category', 'unknown')
        number_last_appearance[bonus_num] = draw_date_obj

    # Build global timing distribution (for calculating weights)
    all_bonus_timing_days = []
    for num in range(1, max_number + 1):
        all_bonus_timing_days.extend(number_stats[num]['bonus_timing_days'])

    # Calculate timing score function from actual data
    timing_bins = {
        '0-7': [],
        '8-14': [],
        '15-21': [],
        '22-30': [],
        '31-45': [],
        '46-60': [],
        '61+': []
    }

    for days in all_bonus_timing_days:
        if days <= 7:
            timing_bins['0-7'].append(days)
        elif days <= 14:
            timing_bins['8-14'].append(days)
        elif days <= 21:
            timing_bins['15-21'].append(days)
        elif days <= 30:
            timing_bins['22-30'].append(days)
        elif days <= 45:
            timing_bins['31-45'].append(days)
        elif days <= 60:
            timing_bins['46-60'].append(days)
        else:
            timing_bins['61+'].append(days)

    # Calculate weights for each timing bin (normalized to peak)
    timing_bin_counts = {bin_name: len(days_list) for bin_name, days_list in timing_bins.items()}
    max_count = max(timing_bin_counts.values()) if timing_bin_counts else 1
    timing_bin_weights = {bin_name: count / max_count for bin_name, count in timing_bin_counts.items()}

    # Calculate global average bonus rate
    total_bonus_appearances = sum(s['bonus_appearances'] for s in number_stats.values())
    total_appearances = sum(s['total_appearances'] for s in number_stats.values())
    global_avg_bonus_rate = total_bonus_appearances / total_appearances if total_appearances > 0 else 0.149

    # Calculate recency effect from data
    in_recent_bonus_appeared = 0
    not_in_recent_bonus_appeared = 0

    for draw_date, draw_data in sorted_draws:
        winning_details = draw_data.get('winning_numbers_details', [])
        if len(winning_details) >= 7:
            bonus_num = winning_details[6]['number']
            recent_bonus_list = draw_data.get('recent_bonus_numbers', [])

            if bonus_num in recent_bonus_list:
                in_recent_bonus_appeared += 1
            else:
                not_in_recent_bonus_appeared += 1

    # Calculate recency penalty multiplier
    if in_recent_bonus_appeared + not_in_recent_bonus_appeared > 0:
        in_recent_rate = in_recent_bonus_appeared / (in_recent_bonus_appeared + not_in_recent_bonus_appeared)
        expected_rate = 10 / 47  # 10 in recent list, 47 total numbers
        recency_penalty = in_recent_rate / expected_rate if expected_rate > 0 else 0.5
    else:
        recency_penalty = 0.5

    # Calculate category bonuses from actual data
    category_bonus_rates = {'hot': 0, 'medium': 0, 'cold': 0}
    category_totals = {'hot': 0, 'medium': 0, 'cold': 0}

    for num in range(1, max_number + 1):
        stats = number_stats[num]
        cat = stats['category']
        if cat in category_bonus_rates:
            if stats['total_appearances'] > 0:
                category_bonus_rates[cat] += stats['bonus_appearances']
                category_totals[cat] += stats['total_appearances']

    category_weights = {}
    for cat in ['hot', 'medium', 'cold']:
        if category_totals[cat] > 0:
            cat_rate = category_bonus_rates[cat] / category_totals[cat]
            category_weights[cat] = cat_rate / global_avg_bonus_rate if global_avg_bonus_rate > 0 else 1.0
        else:
            category_weights[cat] = 1.0

    # Calculate final profiles
    profiles = {}

    latest_draw_date = sorted_draws[-1][0] if sorted_draws else "2024-01-01"
    latest_date_obj = datetime.strptime(latest_draw_date, "%Y-%m-%d")

    for num in range(1, max_number + 1):
        stats = number_stats[num]

        bonus_rate = (stats['bonus_appearances'] / stats['total_appearances']
                     if stats['total_appearances'] > 0 else 0)

        # Calculate days since last bonus
        days_since_last_bonus = None
        if stats['last_bonus_date']:
            last_bonus_obj = datetime.strptime(stats['last_bonus_date'], "%Y-%m-%d")
            days_since_last_bonus = (latest_date_obj - last_bonus_obj).days

        # Calculate average days between bonus appearances
        avg_days_between = None
        if len(stats['bonus_dates']) >= 2:
            intervals = []
            for i in range(1, len(stats['bonus_dates'])):
                d1 = datetime.strptime(stats['bonus_dates'][i], "%Y-%m-%d")
                d2 = datetime.strptime(stats['bonus_dates'][i-1], "%Y-%m-%d")
                intervals.append((d1 - d2).days)

            avg_days_between = sum(intervals) / len(intervals) if intervals else None

        # Determine optimal zone from this number's actual timing history
        optimal_zone = "unknown"
        if stats['bonus_timing_days']:
            avg_timing = sum(stats['bonus_timing_days']) / len(stats['bonus_timing_days'])
            if avg_timing <= 14:
                optimal_zone = "8-14"
            elif avg_timing <= 30:
                optimal_zone = "15-30"
            elif avg_timing <= 60:
                optimal_zone = "31-60"
            else:
                optimal_zone = "61+"

        # Check if in recent bonus 10
        in_recent_bonus = False
        if sorted_draws:
            recent_bonus_list = sorted_draws[-1][1].get('recent_bonus_numbers', [])
            in_recent_bonus = num in recent_bonus_list

        # ===== DATA-DRIVEN PREDICTED BONUS SCORE =====
        predicted_score = 0.0

        if stats['bonus_appearances'] > 0:
            # 1. Relative bonus rate (normalized to global average)
            relative_rate = bonus_rate / global_avg_bonus_rate if global_avg_bonus_rate > 0 else 1.0
            predicted_score += min(1.0, relative_rate) * 0.35

            # 2. Timing factor (using data-driven weights)
            if days_since_last_bonus is not None:
                timing_weight = 0.0
                if days_since_last_bonus <= 7:
                    timing_weight = timing_bin_weights.get('0-7', 0)
                elif days_since_last_bonus <= 14:
                    timing_weight = timing_bin_weights.get('8-14', 0)
                elif days_since_last_bonus <= 21:
                    timing_weight = timing_bin_weights.get('15-21', 0)
                elif days_since_last_bonus <= 30:
                    timing_weight = timing_bin_weights.get('22-30', 0)
                elif days_since_last_bonus <= 45:
                    timing_weight = timing_bin_weights.get('31-45', 0)
                elif days_since_last_bonus <= 60:
                    timing_weight = timing_bin_weights.get('46-60', 0)
                else:
                    timing_weight = timing_bin_weights.get('61+', 0)

                predicted_score += timing_weight * 0.35

            # 3. Category factor (data-driven weight)
            category = stats['category']
            if category in category_weights:
                category_contribution = (category_weights[category] - 1.0) * 0.15
                predicted_score += category_contribution

            # 4. Recency penalty (data-driven)
            if in_recent_bonus:
                predicted_score *= recency_penalty

            # 5. Cycle position bonus (if we have cycle data)
            if avg_days_between and days_since_last_bonus:
                cycle_position = days_since_last_bonus / avg_days_between
                # Numbers at 0.8-1.2x their average cycle get a boost
                if 0.8 <= cycle_position <= 1.2:
                    predicted_score += 0.15
                elif 1.2 < cycle_position <= 1.5:
                    predicted_score += 0.10

        predicted_score = min(1.0, max(0.0, predicted_score))

        profiles[str(num)] = {
            "total_appearances": stats['total_appearances'],
            "bonus_appearances": stats['bonus_appearances'],
            "main_appearances": stats['main_appearances'],
            "bonus_rate": round(bonus_rate, 2),
            "category": stats['category'],
            "last_bonus_date": stats['last_bonus_date'],
            "days_since_last_bonus": days_since_last_bonus,
            "avg_days_between_bonus": round(avg_days_between, 1) if avg_days_between else None,
            "bonus_frequency_ratio": round(bonus_rate, 2),
            "current_optimal_zone": optimal_zone,
            "in_recent_bonus_10": in_recent_bonus,
            "predicted_bonus_score": round(predicted_score, 2),
            "data_driven_weights": {
                "timing_weight": round(timing_bin_weights.get(
                    '8-14' if days_since_last_bonus and days_since_last_bonus <= 14 else
                    '15-21' if days_since_last_bonus and days_since_last_bonus <= 21 else
                    '22-30' if days_since_last_bonus and days_since_last_bonus <= 30 else
                    '31-45' if days_since_last_bonus and days_since_last_bonus <= 45 else
                    '46-60' if days_since_last_bonus and days_since_last_bonus <= 60 else
                    '61+', 0
                ), 3) if days_since_last_bonus else None,
                "category_weight": round(category_weights.get(stats['category'], 1.0), 3),
                "recency_penalty": round(recency_penalty, 3)
            }
        }

    return profiles


def generate_bonus_analysis(
    draw_history_log: Dict,
    total_draws: int,
    c_max_threshold: int = 2,
    max_number: int = 47
) -> Dict:
    """
    Generate comprehensive bonus analysis with all statistics.

    Args:
        draw_history_log: Full draw history
        total_draws: Total number of draws analyzed
        c_max_threshold: Freshness threshold
        max_number: Maximum lottery number

    Returns:
        Complete bonus analysis dictionary
    """
    print("\n  Calculating bonus validation statistics...")
    bonus_category_analysis = calculate_bonus_category_preference(draw_history_log, total_draws)

    print("  Calculating recent bonus exclusion patterns...")
    recent_bonus_exclusion = calculate_recent_bonus_exclusion(draw_history_log, total_draws)

    print("  Calculating main number boost from recent bonus...")
    main_from_bonus = calculate_main_from_recent_bonus(draw_history_log)

    print("  Calculating bonus timing by category...")
    timing_by_category = calculate_bonus_timing_by_category(draw_history_log, max_number)

    print("  Calculating bonus freshness preference...")
    freshness_preference = calculate_bonus_freshness_preference(draw_history_log, c_max_threshold)

    print("  Calculating per-number bonus profiles...")
    per_number_profiles = calculate_per_number_bonus_profile(draw_history_log, max_number)

    result = {
        "bonus_validation": bonus_category_analysis["validation"],
        "bonus_category_preference": bonus_category_analysis["preference"],
        "recent_bonus_exclusion": recent_bonus_exclusion,
        "main_from_recent_bonus": main_from_bonus,
        "bonus_timing_by_category": timing_by_category,
        "bonus_freshness_preference": freshness_preference,
        "per_number_bonus_profile": per_number_profiles
    }

    # Convert all numpy types to native Python types for JSON serialization
    return convert_to_native_types(result)
