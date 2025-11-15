from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple
from ..config import (
    TRAINING_DATA, MAX_NUMBER, SCENARIOS, HMC_METHOD,
    HMC_HOT_THRESHOLD, HMC_COLD_THRESHOLD, VALIDATION_SPLIT_RATIO
)
from .frequency_analyzer import (
    calculate_frequency,
    get_hot_cold,
    get_hot_cold_by_recency,
    calculate_days_since_last_hit,
    get_draw_metrics
)

HISTORY_WINDOWS_DATA = [s["window"] for s in SCENARIOS]

def get_days_difference(date_str_latest: str, date_str_oldest: str) -> int:
    """Calculate the number of days between two 'YYYY-MM-DD' date strings."""
    try:
        d1 = datetime.strptime(date_str_latest, "%Y-%m-%d")
        d2 = datetime.strptime(date_str_oldest, "%Y-%m-%d")
        return (d1 - d2).days
    except ValueError:
        return None

def calculate_win_bias_ratio_for_draw(
    preceding_draws: List[Dict],
    current_categories: Dict[str, List[int]],
    max_number: int
) -> Dict[int, float]:
    """Calculate win bias ratio for each number based on recent history."""
    if not preceding_draws:
        return {num: 1.0 for num in range(1, max_number + 1)}
    
    # 1. Count wins per number (only main numbers, exclude bonus)
    individual_wins = defaultdict(int)
    for draw in preceding_draws:
        for number in draw['numbers'][:6]:
            individual_wins[number] += 1
    
    # 2. Map numbers to their current categories
    num_to_category = {}
    for cat_name, num_list in current_categories.items():
        category = cat_name.replace('_numbers', '')
        for num in num_list:
            num_to_category[num] = category
    
    # 3. Calculate category average win rates
    category_win_totals = defaultdict(int)
    category_counts = defaultdict(int)
    
    for num in range(1, max_number + 1):
        category = num_to_category.get(num, 'cold')
        category_win_totals[category] += individual_wins[num]
        category_counts[category] += 1
    
    category_avg_win_rates = {}
    for category in category_win_totals:
        if category_counts[category] > 0:
            category_avg_win_rates[category] = (
                category_win_totals[category] / category_counts[category]
            )
        else:
            category_avg_win_rates[category] = 0.0
    
    # 4. Calculate bias ratio for each number
    num_training_draws = len(preceding_draws)
    overall_avg = sum(individual_wins.values()) / (max_number * num_training_draws)
    
    win_bias_ratios = {}
    for num in range(1, max_number + 1):
        category = num_to_category.get(num, 'cold')
        num_wins = individual_wins[num]
        num_win_rate = num_wins / num_training_draws
        
        avg_group_rate = category_avg_win_rates.get(category, overall_avg)
        
        if avg_group_rate > 0:
            win_bias_ratios[num] = round(num_win_rate / avg_group_rate, 4)
        else:
            win_bias_ratios[num] = 1.0
    
    return win_bias_ratios

def process_hmc_analysis(all_draws: List[Dict]) -> Tuple[Dict, Dict, Dict, Dict, Dict, Dict]:
    """
    Performs HMC and draw range analysis on all draws, 
    and collects per-draw history data.
    """
    # Pre-analysis Setup
    last_seen_date = {}
    first_draw_date = all_draws[0]["date"]
    
    for num in range(1, MAX_NUMBER + 1):
        last_seen_date[num] = first_draw_date

    # Phase 1: Training
    training_draws = all_draws[:TRAINING_DATA]
    frequency_count = calculate_frequency(training_draws)
    
    # Update last_seen_date based on training draws
    for draw in training_draws:
        for number in draw["numbers"]:
            last_seen_date[number] = draw["date"]

    # Phase 2: Rolling analysis and History Logging
    categorization_history = {}
    hmc_distribution_counts = defaultdict(int)
    draw_history_log = {}
    
    # Tracking counts for 1, 2, or 3 hits in the Last 10 Bonus
    recent_bonus_hit_counts = defaultdict(int)
    
    max_history_window = max(HISTORY_WINDOWS_DATA)
    
    # Import freshness analyzer and distribution analyzer
    from ..analyzers.freshness_analyzer_7_numbers import get_top_pattern_from_draws
    from ..analyzers.distribution_analyzer import calculate_draw_distribution_features
    from ..config import FRESHNESS_WINDOW_INDEX
    
    target_scenario = SCENARIOS[FRESHNESS_WINDOW_INDEX]
    TARGET_FRESHNESS_WINDOW = target_scenario["window"]
    C_MAX_THRESHOLD = max(target_scenario["targets"])
    
    # Keep a rolling list of the last 10 bonus numbers
    recent_bonus_numbers = [] 
    
    # Update recent_bonus_numbers with bonus numbers from training data (if any)
    for draw in training_draws:
        bonus_number = draw["numbers"][-1] if draw["numbers"] else None
        if bonus_number is not None:
            recent_bonus_numbers.append(bonus_number)
            if len(recent_bonus_numbers) > 10:
                recent_bonus_numbers.pop(0)

    # Print HMC method being used (one-time debug)
    print(f"  Using HMC categorization method: {HMC_METHOD}")
    if HMC_METHOD == "recency":
        print(f"  Recency thresholds: Hot <= {HMC_HOT_THRESHOLD} days, Cold >= {HMC_COLD_THRESHOLD} days")

    for i in range(TRAINING_DATA, len(all_draws)):
        current_draw = all_draws[i]
        draw_date = current_draw["date"]
        winning_numbers = current_draw["numbers"]

        # Categorize based on HMC_METHOD (PRIOR to this draw)
        if HMC_METHOD == "recency":
            # Use RECENCY-BASED categorization (validated with scipy ANOVA)
            days_since = calculate_days_since_last_hit(all_draws[:i])
            categories = get_hot_cold_by_recency(days_since, HMC_HOT_THRESHOLD, HMC_COLD_THRESHOLD)
        else:
            # Use FREQUENCY-BASED categorization (deprecated)
            categories = get_hot_cold(frequency_count)
        
        # ============ Calculate per-draw freshness pattern ============
        temp_history = {}
        for j in range(TRAINING_DATA, i):
            temp_date = all_draws[j]["date"]
            if temp_date in draw_history_log:
                temp_history[temp_date] = draw_history_log[temp_date]
        
        top_pattern_dist_current = get_top_pattern_from_draws(
            temp_history,
            end_draw_index=i,
            target_window=TARGET_FRESHNESS_WINDOW,
            c_max_threshold=C_MAX_THRESHOLD
        )
        
        # Calculate Draw Metrics
        draw_range, rating_counts, hmc_dist = get_draw_metrics(winning_numbers, categories)
        hmc_distribution_counts[hmc_dist] += 1
        
        categorization_history[draw_date] = {
            "draw_range": draw_range,
            "frequency_rating": rating_counts,
            "hmc_distribution": hmc_dist,
            **categories
        }

        # ============ Calculate win_bias_ratio per-draw ============
        bias_analysis_window = 100
        preceding_for_bias = all_draws[max(0, i - bias_analysis_window): i]
        win_bias_ratios = calculate_win_bias_ratio_for_draw(
            preceding_for_bias,
            categories,
            MAX_NUMBER
        )
        
        # Determine the set of last 10 bonus numbers for checking
        recent_bonus_set = set(recent_bonus_numbers)
        
        # Determine the bonus number
        bonus_number = winning_numbers[-1] if winning_numbers else None
        
        # Count how many *main* winning numbers hit the recent bonus set
        current_draw_bonus_hits = 0
        main_winning_numbers = winning_numbers[:6]
        
        for number in main_winning_numbers:
            if number in recent_bonus_set:
                current_draw_bonus_hits += 1
        
        # Record the draw hit count (1, 2, or 3+)
        if current_draw_bonus_hits >= 1:
            if current_draw_bonus_hits >= 3:
                recent_bonus_hit_counts['3_or_more'] += 1
            elif current_draw_bonus_hits == 2:
                recent_bonus_hit_counts['2_hits'] += 1
            elif current_draw_bonus_hits == 1:
                recent_bonus_hit_counts['1_hit'] += 1

        # ============ Calculate Bonus Hit Analysis ============
        bonus_hit_analysis = {
            "total_bonus_hits": current_draw_bonus_hits,
            "alignment_score": 0.0,
            "target_range": "1-2 hits",
            "is_optimal": False
        }
        
        # Alignment scoring: optimal is 1-2 hits
        if current_draw_bonus_hits == 1 or current_draw_bonus_hits == 2:
            bonus_hit_analysis["alignment_score"] = 1.0
            bonus_hit_analysis["is_optimal"] = True
        elif current_draw_bonus_hits == 0:
            bonus_hit_analysis["alignment_score"] = 0.5
        else:  # 3+ hits
            bonus_hit_analysis["alignment_score"] = 0.3

        # Build winning_numbers_details for draw history
        winning_numbers_details = []
        hot_set = set(categories['hot_numbers'])
        medium_set = set(categories['medium_numbers'])
        
        # Draws preceding the current one (for recent counts)
        preceding_draws = all_draws[max(0, i - max_history_window): i]
        
        
        # ============ Build winning_numbers_details ONCE ============
        for number in winning_numbers:
            # 1. Determine Category
            category = 'cold'
            if number in hot_set:
                category = 'hot'
            elif number in medium_set:
                category = 'medium'
            
            # 2. Days Since Last Hit
            last_hit_date = last_seen_date.get(number, first_draw_date)
            days_since_last_hit = get_days_difference(draw_date, last_hit_date)
            
            # 3. Recent Counts
            recent_counts = {}
            for w in HISTORY_WINDOWS_DATA:
                window_draws = preceding_draws[-w:]
                count = sum(1 for draw in window_draws if number in draw["numbers"])
                recent_counts[f"last_{w - 1}"] = count 
            
            # 4. Determine if Bonus
            is_bonus = (number == bonus_number)
            
            # 5. Calculate freshness for THIS number
            recent_count_key = f"last_{TARGET_FRESHNESS_WINDOW - 1}"
            recent_count = recent_counts.get(recent_count_key, 0)
            
            if recent_count >= C_MAX_THRESHOLD:
                current_freshness_bin = C_MAX_THRESHOLD
            else:
                current_freshness_bin = recent_count
            
            # Create per-number freshness weights
            freshness_weights = {}
            for bin_idx in range(C_MAX_THRESHOLD + 1):
                feature_name = f'freshness_c{bin_idx}_weight'
                if bin_idx == current_freshness_bin:
                    freshness_weights[feature_name] = top_pattern_dist_current.get(bin_idx, 0.0)
                else:
                    freshness_weights[feature_name] = 0.0
            
            # 6. Check if the number was one of the last 10 bonus numbers
            is_recent_bonus_hit = number in recent_bonus_set
            
            # 7. Calculate bonus hit contribution for this number
            bonus_hit_contribution = 1.0 if is_recent_bonus_hit else 0.0
            
            # ============ APPEND ONCE with ALL data ============
            winning_numbers_details.append({
                "number": number,
                "is_bonus": is_bonus,
                "category": category,
                "days_since_last_hit": days_since_last_hit,
                "recent_counts": recent_counts,
                "win_bias_ratio": win_bias_ratios.get(number, 1.0),
                "freshness_weights": freshness_weights,
                "current_freshness_bin": current_freshness_bin,
                "is_recent_bonus_hit": is_recent_bonus_hit,
                "bonus_hit_contribution": bonus_hit_contribution
            })
        
        # ============ Calculate distribution features for the draw ============
        distribution_features = calculate_draw_distribution_features(winning_numbers_details)
        
        # ============ Store Draw History Log ONCE (with all features) ============
        draw_history_log[draw_date] = {
            "draw_index": i,
            "draw_date": draw_date,
            "hmc_summary": {
                "hot_count": rating_counts['hot'],
                "medium_count": rating_counts['medium'],
                "cold_count": rating_counts['cold'],
                "hmc_distribution": hmc_dist,
                "draw_range": draw_range
            },
            "categories_pre_draw": {
                'hot_numbers': list(categories['hot_numbers']),
                'medium_numbers': list(categories['medium_numbers']),
                'cold_numbers': list(categories['cold_numbers'])
            },
            "winning_numbers_details": winning_numbers_details,
            "all_numbers_bias_ratios": win_bias_ratios,
            "freshness_pattern_weights": top_pattern_dist_current,
            "recent_bonus_numbers": recent_bonus_numbers[:],
            "distribution_features": distribution_features,
            "bonus_hit_analysis": bonus_hit_analysis
        }

        # Update Frequency and Last Seen Date (POST-DRAW)
        for number in winning_numbers:
            frequency_count[number] += 1
            last_seen_date[number] = draw_date

        # Update the recent bonus number list (POST-DRAW) - FIX v3.10: Update BEFORE logging next draw
        if bonus_number is not None:
            recent_bonus_numbers.append(bonus_number)
            if len(recent_bonus_numbers) > 10:
                recent_bonus_numbers.pop(0)

        # Update draw_history_log to include current bonus in recent list
        draw_history_log[draw_date]["recent_bonus_numbers"] = recent_bonus_numbers[:]

    # Final categories (using current HMC method)
    # IMPORTANT: Calculate using only TRAINING data (80%) to prevent look-ahead bias
    # Validation data (last 20%) should NOT influence category assignments used in ML training
    available_draws = len(all_draws) - TRAINING_DATA
    train_size = int(available_draws * VALIDATION_SPLIT_RATIO)
    train_end_index = TRAINING_DATA + train_size

    print(f"\n  Calculating final categories WITHOUT look-ahead bias:")
    print(f"    Total draws: {len(all_draws)}")
    print(f"    Training cutoff: draw {train_end_index} ({VALIDATION_SPLIT_RATIO*100:.0f}% of available data)")
    print(f"    Validation draws excluded: {len(all_draws) - train_end_index}")

    if HMC_METHOD == "recency":
        # Use RECENCY-BASED categorization for final output
        # Use ONLY draws up to training cutoff (excludes validation data)
        days_since_final = calculate_days_since_last_hit(all_draws[:train_end_index])
        final_categories = get_hot_cold_by_recency(days_since_final, HMC_HOT_THRESHOLD, HMC_COLD_THRESHOLD)
        print(f"  Final categories (recency, train-only): Hot={len(final_categories['hot_numbers'])}, "
              f"Medium={len(final_categories['medium_numbers'])}, "
              f"Cold={len(final_categories['cold_numbers'])}")
    else:
        # Use FREQUENCY-BASED categorization (deprecated)
        final_categories = get_hot_cold(frequency_count)

    return (categorization_history, frequency_count, dict(hmc_distribution_counts),
            final_categories, draw_history_log, dict(recent_bonus_hit_counts))