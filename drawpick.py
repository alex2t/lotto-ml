#!/usr/bin/env python3
"""
Lottery Analysis - Main Entry Point
Orchestrates all analysis phases and generates output files
"""

from collections import defaultdict
from datetime import datetime
from lotto_analysis.config import (
    CSV_FILE, TOTAL_DRAWS, TRAINING_DATA, NUM_DRAWS, 
    OUTPUT_FILE_MAIN, OUTPUT_FILE_PERIODS, OUTPUT_FILE_HISTORY,
    OUTPUT_FILE_7_NUMBERS, OUTPUT_FILE_DISTRIBUTIONS,
    SCENARIOS, MAX_NUMBER,
    FRESHNESS_WINDOW_INDEX
)
from lotto_analysis.core.data_loader import load_lotto_data
from lotto_analysis.analyzers.pattern_analyzer import process_pattern_analysis
from lotto_analysis.analyzers.consecutive_analyzer import analyze_consecutive_patterns
from lotto_analysis.analyzers.hmc_analyzer import process_hmc_analysis
from lotto_analysis.analyzers.freshness_analyzer_7_numbers import (
    analyze_7_number_freshness, format_freshness_output
)
from lotto_analysis.analyzers.distribution_analyzer import (
    analyze_distribution_patterns,
    calculate_per_number_distribution_stats
)
from lotto_analysis.analyzers.bonus_analyzer import generate_bonus_analysis
from lotto_analysis.analyzers.bonus_to_main_analyzer import generate_bonus_to_main_analysis

# Import scipy validation analyzers (Phase 10)
from lotto_analysis.analyzers.consecutive_pair_analyzer import analyze_consecutive_pairs
from lotto_analysis.analyzers.odd_even_analyzer import analyze_odd_even_patterns
from lotto_analysis.analyzers.range_spread_analyzer import analyze_range_spread
from lotto_analysis.analyzers.sum_contribution_analyzer import analyze_sum_contribution
from lotto_analysis.analyzers.freshness_pattern_analyzer import analyze_freshness_patterns
from lotto_analysis.analyzers.hmc_categorization_analyzer import analyze_hmc_categorization
from lotto_analysis.analyzers.long_term_pattern_analyzer import generate_long_term_pattern_analysis
from lotto_analysis.analyzers.advanced_pattern_analyzer import generate_advanced_pattern_analysis

# Import statistics and window saturation analyzers (Phase 11)
from analysis.bonus_analysis import (
    get_dynamic_recent_count_keys,
    analyze_hmc_distribution,
    analyze_days_since_last_hit,
    analyze_recent_counts,
    analyze_freshness_patterns as analyze_stats_freshness_patterns,
    analyze_bonus_patterns
)
from lotto_analysis.analyzers.window_saturation_analyzer import generate_window_saturation_data
from lotto_analysis.analyzers.recency_zone_analyzer import generate_recency_zones_data

from lotto_analysis.utils.output_generator import (
    generate_hmc_analysis, generate_draw_range_analysis,
    write_json_file, format_date_iso,
    generate_range_spread_analysis
)

def main():
    """Main execution function"""
    print("=" * 70)
    print("Lottery Analysis Program")
    print("Pattern + HMC + Distributions + Bonus + Scipy Validation")
    print("=" * 70)
    
    # **DYNAMIC CONFIGURATION SETUP**
    try:
        target_scenario = SCENARIOS[FRESHNESS_WINDOW_INDEX]
    except IndexError:
        print(f"\nERROR: FRESHNESS_WINDOW_INDEX {FRESHNESS_WINDOW_INDEX} is out of bounds for SCENARIOS list.")
        return
        
    TARGET_FRESHNESS_WINDOW = target_scenario["window"]
    C_MAX_THRESHOLD = max(target_scenario["targets"])

    print(f"\nFreshness Analysis Settings: W={TARGET_FRESHNESS_WINDOW}, C_max={C_MAX_THRESHOLD}")
    
    # ===== LOAD DATA =====
    try:
        all_draws, available_draws, skipped_rows = load_lotto_data(CSV_FILE, TOTAL_DRAWS)
    except FileNotFoundError:
        print(f"\nERROR: CSV file '{CSV_FILE}' not found. Please place it in the 'data/' folder.")
        return
    except ValueError as e:
        print(f"\nERROR: Data loading failed: {e}")
        return
        
    if not all_draws:
        print("No valid draws were loaded.")
        return
    
    print(f"\nLoaded {len(all_draws)} draws "
          f"(requested: {TOTAL_DRAWS}, skipped: {skipped_rows})")
    
    # ===== HMC ANALYSIS (Phase 1 & 2) =====
    print("\n" + "=" * 70)
    print(f"Phase 1: HMC Training ({TRAINING_DATA} draws)")
    print("Phase 2: HMC Analysis and History Logging")
    print("=" * 70)
    
    (categorization_history, final_frequency, hmc_counts, 
     final_categories, draw_history_log, recent_bonus_hits) = process_hmc_analysis(all_draws)
    total_hmc_draws = len(categorization_history)
    
    # ===== PATTERN ANALYSIS =====
    print("\n" + "=" * 70)
    print(f"Phase 3: Pattern Analysis ({NUM_DRAWS} draws)")
    print("=" * 70)
    
    pattern_draws = all_draws[TRAINING_DATA:]
    (assigned_matches_by_number, assigned_windows_by_category, 
     total_windows_by_size) = process_pattern_analysis(pattern_draws)
    
    # ===== CONSECUTIVE RUNS ANALYSIS =====
    print("\n" + "=" * 70)
    print("Phase 4: Consecutive Runs Analysis")
    print("=" * 70)
    
    consecutive_patterns = analyze_consecutive_patterns(all_draws)
    
    for run_length in range(2, 8):
        key = f"{run_length}_consecutive"
        data = consecutive_patterns[key]
        hit_count = data["hit_count"]
        odds = data["odds"]
        percentage = odds * 100
        print(f"  {run_length}-consecutive: {hit_count} draws "
              f"({percentage:.2f}%), odds: {odds:.4f}")
    

    # ===== 7-NUMBER FRESHNESS ANALYSIS =====
    print("\n" + "=" * 70)
    print(f"Phase 5: 7-Number Freshness Distribution Analysis (W={TARGET_FRESHNESS_WINDOW}, C>= {C_MAX_THRESHOLD})")
    print("=" * 70)
    
    freshness_counts, total_draws_freshness = analyze_7_number_freshness(
        draw_history_log, TARGET_FRESHNESS_WINDOW, C_MAX_THRESHOLD
    )

    # ===== ODD/EVEN AND SUM DISTRIBUTION ANALYSIS (BOTH 6 & 7 NUMBERS) =====
    print("\n" + "=" * 70)
    print("Phase 6: Odd/Even and Sum Distribution Analysis")
    print("=" * 70)
    
    odd_even_6_stats, odd_even_7_stats, sum_6_stats, sum_7_stats = analyze_distribution_patterns(draw_history_log)
    
    print(f"\n--- 6 MAIN NUMBERS (excluding bonus) ---")
    print(f"\nOdd/Even Pattern Distribution (6 numbers):")
    for pattern, stats in odd_even_6_stats.items():
        if stats['count'] > 0:
            print(f"  {pattern}: {stats['count']} draws ({stats['percentage']:.2f}%)")
    
    print(f"\nSum Distribution (6 numbers):")
    for bin_name, stats in sum_6_stats.items():
        if stats['count'] > 0:
            print(f"  {bin_name}: {stats['count']} draws ({stats['percentage']:.2f}%)")
    
    print(f"\n--- ALL 7 NUMBERS (6 main + bonus) ---")
    print(f"\nOdd/Even Pattern Distribution (7 numbers):")
    for pattern, stats in odd_even_7_stats.items():
        if stats['count'] > 0:
            print(f"  {pattern}: {stats['count']} draws ({stats['percentage']:.2f}%)")
    
    print(f"\nSum Distribution (7 numbers):")
    for bin_name, stats in sum_7_stats.items():
        if stats['count'] > 0:
            print(f"  {bin_name}: {stats['count']} draws ({stats['percentage']:.2f}%)")

    # ===== CALCULATE PER-NUMBER DISTRIBUTION STATS =====
    print("\n" + "=" * 70)
    print("Phase 7: Per-Number Distribution Statistics")
    print("=" * 70)
    
    odd_even_analysis, sum_contribution_analysis = calculate_per_number_distribution_stats(
        draw_history_log, MAX_NUMBER
    )
    
    print(f"✓ Calculated odd/even analysis for {len(odd_even_analysis)} numbers")
    print(f"✓ Calculated sum contribution analysis for {len(sum_contribution_analysis)} numbers")

    # ===== BONUS BALL ANALYSIS =====
    print("\n" + "=" * 70)
    print("Phase 8: Comprehensive Bonus Ball Analysis")
    print("=" * 70)
    
    bonus_analysis = generate_bonus_analysis(
        draw_history_log,
        total_hmc_draws,
        C_MAX_THRESHOLD,
        MAX_NUMBER
    )
    
    print(f"✓ Completed bonus validation statistics")
    print(f"✓ Completed bonus category preference analysis")
    print(f"✓ Completed recent bonus exclusion patterns")
    print(f"✓ Completed bonus timing analysis")
    print(f"✓ Completed per-number bonus profiles for {MAX_NUMBER} numbers")

    # ===== BUILD SUPPORTING DATA (for lotto_trigger_periods.json) =====
    total_counts_by_number = defaultdict(int)
    last_seen_by_number = {}
    
    for num in range(1, MAX_NUMBER + 1):
        for draw in all_draws:
            if num in draw["numbers"]:
                total_counts_by_number[num] += 1
                last_seen_by_number[num] = draw["date"]
    
    num_to_category = {}
    for cat_name, num_list in final_categories.items():
        for num in num_list:
            category_key = cat_name.replace('_numbers', '')
            num_to_category[num] = category_key
    
    # ===== BUILD OUTPUT FILES =====
    print("\n" + "=" * 70)
    print("Building Output Files")
    print("=" * 70)
    
    hmc_analysis = generate_hmc_analysis(hmc_counts, total_hmc_draws)
    draw_range_analysis = generate_draw_range_analysis(categorization_history, 
                                                       total_hmc_draws)
    
    recent_bonus_analysis = {}
    for key in ['1_hit', '2_hits', '3_or_more']:
        count = recent_bonus_hits.get(key, 0)
        odds = (count / total_hmc_draws) if total_hmc_draws > 0 else 0.0
        recent_bonus_analysis[key] = {
            "count": count,
            "odds": round(odds, 4)
        }
    
    # ===== BUILD RANGE SPREAD ANALYSIS =====
    range_spread_analysis = generate_range_spread_analysis(draw_history_log, MAX_NUMBER)
        
    # Build lotto_odds_results
    final_main = {
        "requested_draws": NUM_DRAWS,
        "pattern_analysis_draws": len(pattern_draws),
        "hmc_analysis_draws": total_hmc_draws,
        "hmc_training_draws": TRAINING_DATA,
        "available_draws": available_draws,
        "used_draws": len(all_draws),
        "skipped_rows": skipped_rows,
        "scenarios": []
    }

    for s in SCENARIOS:
        w = s["window"]
        results = {}
        total_wins = total_windows_by_size.get(w, 0)
        for t in s["targets"]:
            cat = f"{w}_consecutives_{t}_times"
            unique_windows_for_cat = assigned_windows_by_category.get(cat, set())
            hit_count = len(unique_windows_for_cat)
            odds = (hit_count / total_wins) if total_wins > 0 else 0.0
            results[f"{t}_times"] = {
                "hit_count": hit_count,
                "total_windows": total_wins,
                "odds": round(odds, 4)
            }
        final_main["scenarios"].append({"window_size": w, "results": results})

    final_main["hmc"] = hmc_analysis
    final_main["draw_range"] = draw_range_analysis
    final_main["patterns"] = consecutive_patterns
    final_main["recent_bonus_analysis"] = recent_bonus_analysis
    final_main["range_spread_analysis"] = range_spread_analysis
    
    # Build lotto_trigger_periods
    final_periods = {}
    for num in range(1, MAX_NUMBER + 1):
        assigned = assigned_matches_by_number.get(num, [])
        
        recent_data = {}
        for scenario in SCENARIOS:
            window_size = scenario["window"]
            param_suffix = window_size - 1
            param_name = f"last_{param_suffix}"
            
            recent_draws = (pattern_draws[-window_size:] if len(pattern_draws) >= window_size 
                          else pattern_draws)
                          
            count = sum(1 for draw in recent_draws if num in draw["numbers"])
            recent_data[param_name] = count
            
        series_data = {}

        if assigned:
            grouped = defaultdict(list)
            for m in assigned:
                grouped[m["category"]].append(m)
                
            for cat, lst in grouped.items():
                count = len(lst)
                latest = max(lst, key=lambda x: x["end_idx"]) 
                
                series_data[cat] = [{
                    "start_date": format_date_iso(latest["start_date"]),
                    "end_date": format_date_iso(latest["end_date"]),
                    "count": count
                }]

        output = {}
        if total_counts_by_number[num] > 0:
            output["total_count"] = total_counts_by_number[num]
            output["last_seen"] = format_date_iso(last_seen_by_number[num])
            output["category"] = num_to_category.get(num, "unknown")
        
        output["recent"] = recent_data
        
        if series_data:
            output["series"] = {"series": series_data}
        
        final_periods[str(num)] = output
    
    # ===== BUILD DISTRIBUTION STATISTICS OUTPUT (BOTH 6 & 7) =====
    final_distribution_stats = {
        "total_draws_analyzed": total_hmc_draws,
        "analysis_6_main_numbers": {
            "description": "Analysis of 6 main numbers (excluding bonus)",
            "odd_even_patterns": odd_even_6_stats,
            "sum_distributions": sum_6_stats
        },
        "analysis_all_7_numbers": {
            "description": "Analysis of all 7 numbers (6 main + bonus)",
            "odd_even_patterns": odd_even_7_stats,
            "sum_distributions": sum_7_stats
        },
        "odd_even_analysis": odd_even_analysis,
        "sum_contribution_analysis": sum_contribution_analysis
    }
    
    # ===== WRITE OUTPUT FILES =====
    write_json_file(OUTPUT_FILE_MAIN, final_main, 
                   "Includes scenarios, HMC, draw_range, consecutive patterns, and range_spread_analysis")
    write_json_file(OUTPUT_FILE_PERIODS, final_periods,
                   "Per-number data with category, recent, and series")
    write_json_file(OUTPUT_FILE_HISTORY, draw_history_log,
                   "Per-draw history for HMC state and winning numbers details with bonus_hit_analysis")
    
    final_freshness_data = format_freshness_output(
        freshness_counts, total_draws_freshness, TARGET_FRESHNESS_WINDOW, C_MAX_THRESHOLD
    )
    write_json_file(OUTPUT_FILE_7_NUMBERS, final_freshness_data,
                   "Comprehensive freshness distribution for all 7 winning numbers with weight calculation")
    
    write_json_file(OUTPUT_FILE_DISTRIBUTIONS, final_distribution_stats,
                   "Odd/Even patterns and Sum distributions (both 6 and 7 numbers) with per-number analysis")
    
    # ===== WRITE BONUS ANALYSIS FILE =====
    OUTPUT_FILE_BONUS = "data/lotto_bonus_analysis.json"
    write_json_file(OUTPUT_FILE_BONUS, bonus_analysis,
                   "Comprehensive bonus ball analysis with data-driven weights and statistical validation")

    # ===== BONUS-TO-MAIN TRANSITION ANALYSIS =====
    print("\n" + "=" * 70)
    print("Phase 9: Bonus-to-Main Transition Analysis")
    print("=" * 70)

    bonus_to_main_analysis = generate_bonus_to_main_analysis(
        draw_history_log,
        MAX_NUMBER
    )

    print(f"✓ Analyzed {bonus_to_main_analysis['metadata']['total_bonus_appearances']} bonus appearances")
    print(f"✓ Overall transition rate: {bonus_to_main_analysis['metadata']['overall_transition_rate']*100:.2f}%")
    print(f"✓ Boost over random: {bonus_to_main_analysis['transition_prediction_factors']['boost_factor']}x")

    # ===== WRITE BONUS-TO-MAIN ANALYSIS FILE =====
    OUTPUT_FILE_BONUS_TO_MAIN = "data/lotto_bonus_to_main_patterns.json"
    write_json_file(OUTPUT_FILE_BONUS_TO_MAIN, bonus_to_main_analysis,
                   "Bonus-to-Main transition patterns with data-driven weights for ML prediction")

    # ===== SCIPY STATISTICAL VALIDATION ANALYSIS (PHASE 10) =====
    print("\n" + "=" * 70)
    print("Phase 10: Scipy Statistical Validation")
    print("=" * 70)
    print("Generating statistically validated feature data for ML prediction...")
    print("This ensures all features are based on rigorous statistical testing")
    print("(chi-square, t-tests, ANOVA, correlation analysis, p-value < 0.05)")

    # Convert draw_history_log to format needed by analyzers
    # Analyzers expect: List[Dict[str, Any]] with 'date' and 'numbers' keys
    print("\n  Preparing draw history data for validation analyzers...")
    draw_list = []
    for draw_date, draw_data in draw_history_log.items():
        winning_numbers = []
        for detail in draw_data.get('winning_numbers_details', []):
            num = detail.get('number')
            is_bonus = detail.get('is_bonus', False)
            if num and not is_bonus:  # Exclude bonus for most analyses
                winning_numbers.append(num)

        if winning_numbers:
            draw_list.append({
                'date': draw_date,
                'numbers': winning_numbers
            })

    draw_list.sort(key=lambda x: x['date'])
    print(f"  ✓ Prepared {len(draw_list)} draws for scipy validation")

    # 1. Consecutive Pairs Validation
    print("\n  [1/7] Consecutive Pair Analysis (chi-square + binomial tests)...")
    consecutive_pairs_results = analyze_consecutive_pairs(draw_list, MAX_NUMBER)
    OUTPUT_FILE_CONSECUTIVE_PAIRS = "data/lotto_consecutive_pairs_validated.json"
    write_json_file(OUTPUT_FILE_CONSECUTIVE_PAIRS, consecutive_pairs_results,
                   "Scipy-validated consecutive pair analysis with binomial significance tests")
    print(f"        ✓ Saved to {OUTPUT_FILE_CONSECUTIVE_PAIRS}")

    # Show validation summary
    chi2_test = consecutive_pairs_results.get('overall_chi_square_test', {})
    print(f"        Chi-square p-value: {chi2_test.get('p_value', 1.0):.6f}")
    print(f"        Statistically significant: {chi2_test.get('significant', False)}")

    # 2. Odd/Even Distribution Validation
    print("\n  [2/7] Odd/Even Distribution Analysis (chi-square + binomial tests)...")
    odd_even_results = analyze_odd_even_patterns(draw_list, MAX_NUMBER)
    OUTPUT_FILE_ODD_EVEN = "data/lotto_odd_even_validated.json"
    write_json_file(OUTPUT_FILE_ODD_EVEN, odd_even_results,
                   "Scipy-validated odd/even distribution analysis with per-number affinity scores")
    print(f"        ✓ Saved to {OUTPUT_FILE_ODD_EVEN}")

    overall_test = odd_even_results.get('overall_distribution_test', {})
    print(f"        Chi-square p-value: {overall_test.get('p_value', 1.0):.6f}")
    print(f"        Significant deviations: {odd_even_results.get('num_significant_deviations', 0)}/47 numbers")

    # 3. Range Spread Validation
    print("\n  [3/7] Range Spread Analysis (Levene test + t-tests + correlation)...")
    range_spread_results = analyze_range_spread(draw_list, MAX_NUMBER)
    OUTPUT_FILE_RANGE_SPREAD = "data/lotto_range_spread_validated.json"
    write_json_file(OUTPUT_FILE_RANGE_SPREAD, range_spread_results,
                   "Scipy-validated range spread analysis with Levene variance tests")
    print(f"        ✓ Saved to {OUTPUT_FILE_RANGE_SPREAD}")

    levene = range_spread_results.get('levene_analysis', {})
    print(f"        Levene p-value: {levene.get('p_value', 1.0):.6f}")
    print(f"        Significant contributions: {range_spread_results.get('num_significant_contributions', 0)}/47 numbers")

    # 4. Sum Contribution Validation
    print("\n  [4/7] Sum Contribution Analysis (t-tests + ANOVA + effect sizes)...")
    sum_contribution_results = analyze_sum_contribution(draw_list, MAX_NUMBER)
    OUTPUT_FILE_SUM_CONTRIBUTION = "data/lotto_sum_contribution_validated.json"
    write_json_file(OUTPUT_FILE_SUM_CONTRIBUTION, sum_contribution_results,
                   "Scipy-validated sum contribution analysis with independent t-tests")
    print(f"        ✓ Saved to {OUTPUT_FILE_SUM_CONTRIBUTION}")

    anova = sum_contribution_results.get('anova_analysis', {})
    print(f"        ANOVA p-value: {anova.get('p_value', 1.0):.6f}")
    print(f"        Significant contributions: {sum_contribution_results.get('num_significant_contributions', 0)}/47 numbers")

    # 5. Freshness Pattern Validation
    print("\n  [5/7] Freshness Pattern Analysis (chi-square goodness-of-fit)...")
    freshness_pattern_results = analyze_freshness_patterns(final_freshness_data)
    OUTPUT_FILE_FRESHNESS_PATTERNS = "data/lotto_freshness_patterns_validated.json"
    write_json_file(OUTPUT_FILE_FRESHNESS_PATTERNS, freshness_pattern_results,
                   "Scipy-validated freshness pattern distribution with chi-square tests")
    print(f"        ✓ Saved to {OUTPUT_FILE_FRESHNESS_PATTERNS}")

    pattern_test = freshness_pattern_results.get('pattern_distribution_test', {})
    print(f"        Chi-square p-value: {pattern_test.get('p_value', 1.0):.6f}")
    print(f"        Cramér's V: {pattern_test.get('cramers_v', 0.0):.4f}")

    # 6. HMC Categorization Validation
    print("\n  [6/7] HMC Categorization Analysis (ANOVA + pairwise t-tests)...")
    hmc_categorization_results = analyze_hmc_categorization(final_periods)
    OUTPUT_FILE_HMC_CATEGORIZATION = "data/lotto_hmc_categorization_validated.json"
    write_json_file(OUTPUT_FILE_HMC_CATEGORIZATION, hmc_categorization_results,
                   "Scipy-validated HMC categorization with ANOVA and Bonferroni-corrected tests")
    print(f"        ✓ Saved to {OUTPUT_FILE_HMC_CATEGORIZATION}")

    anova_test = hmc_categorization_results.get('anova_test', {})
    print(f"        ANOVA p-value: {anova_test.get('p_value', 1.0):.6f}")
    print(f"        Effect size (η²): {anova_test.get('eta_squared', 0.0):.4f}")
    print(f"        Categories valid: {hmc_categorization_results.get('categorization_valid', False)}")

    # 7. Long-term Pattern Validation
    print("\n  [7/7] Long-term Pattern Analysis (chi-square + Pearson correlation)...")
    long_term_pattern_results = generate_long_term_pattern_analysis(draw_history_log)
    OUTPUT_FILE_LONG_TERM = "data/lotto_long_term_patterns.json"
    write_json_file(OUTPUT_FILE_LONG_TERM, long_term_pattern_results,
                   "Scipy-validated long-term pattern analysis with chi-square and correlation tests")
    print(f"        ✓ Saved to {OUTPUT_FILE_LONG_TERM}")

    hmc_pattern = long_term_pattern_results.get('hmc_pattern_analysis', {})
    print(f"        HMC pattern chi-square p-value: {hmc_pattern.get('p_value', 1.0):.6f}")
    print(f"        Statistically significant: {hmc_pattern.get('significant', False)}")

    print("\n" + "=" * 70)
    print("✓ Phase 10 Complete: All scipy validation files generated")
    print("=" * 70)
    print("\nValidation Summary:")
    print("  These files provide statistically rigorous feature data for ML models:")
    print("  - All features tested with p-value < 0.05 significance threshold")
    print("  - Only statistically significant patterns are weighted")
    print("  - Random noise filtered out through proper hypothesis testing")
    print("  - Effect sizes calculated (Cohen's d, Cramér's V, eta-squared)")

    # ===== STATISTICS ANALYSIS (PHASE 11) =====
    print("\n" + "=" * 70)
    print("Phase 11: Statistical Analysis Generation")
    print("=" * 70)
    print("Generating lotto_statistics_analysis.json from draw history...")

    # Get recent count keys dynamically
    recent_keys = get_dynamic_recent_count_keys(draw_history_log)
    print(f"  ✓ Found {len(recent_keys)} recent count windows: {recent_keys}")

    # Run all statistics analyses
    hmc_stats = analyze_hmc_distribution(draw_history_log)
    days_stats = analyze_days_since_last_hit(draw_history_log)
    recent_stats = analyze_recent_counts(draw_history_log, recent_keys)
    freshness_stats = analyze_stats_freshness_patterns(draw_history_log)
    bonus_stats = analyze_bonus_patterns(draw_history_log)

    # Combine results
    statistics_results = {
        'hmc_distribution': hmc_stats,
        'days_since_last_hit': days_stats,
        'recent_counts': recent_stats,
        'freshness_patterns': freshness_stats,
        'bonus_patterns': bonus_stats,
        'metadata': {
            'total_draws': len(draw_history_log),
            'recent_count_windows': recent_keys,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }

    # Save statistics file
    OUTPUT_FILE_STATISTICS = "data/lotto_statistics_analysis.json"
    write_json_file(OUTPUT_FILE_STATISTICS, statistics_results,
                   "Comprehensive statistical analysis of draw history patterns")
    print(f"  ✓ Saved to {OUTPUT_FILE_STATISTICS}")

    # ===== WINDOW SATURATION ANALYSIS (PHASE 12) =====
    print("\n" + "=" * 70)
    print("Phase 12: Window Saturation Analysis")
    print("=" * 70)
    print("Generating data-driven window saturation penalties...")

    stats_file = "data/lotto_statistics_analysis.json"
    odds_file = OUTPUT_FILE_MAIN
    output_file = "data/lotto_window_saturation_calculated.json"

    generate_window_saturation_data(stats_file, odds_file, output_file)
    print(f"  ✓ Window saturation analysis complete")

    # ===== ADVANCED PATTERN ANALYSIS (PHASE 13) =====
    print("\n" + "=" * 70)
    print("Phase 13: Advanced Pattern Features (Volatility + Trend)")
    print("=" * 70)
    print("Generating volatility and trend features for improved prediction...")

    advanced_pattern_results = generate_advanced_pattern_analysis(draw_history_log, MAX_NUMBER)
    OUTPUT_FILE_ADVANCED = "data/lotto_advanced_patterns.json"
    write_json_file(OUTPUT_FILE_ADVANCED, advanced_pattern_results,
                   "Advanced pattern features: volatility, trend, and temporal analysis")
    print(f"  ✓ Saved to {OUTPUT_FILE_ADVANCED}")

    # ===== RECENCY ZONE ANALYSIS (PHASE 14) =====
    print("\n" + "=" * 70)
    print("Phase 14: Recency Zone Analysis (Data-Driven)")
    print("=" * 70)
    print("Generating data-driven recency zone scoring to replace hard-coded thresholds...")

    draw_history_file = OUTPUT_FILE_HISTORY
    output_file_recency = "data/lotto_recency_zones_calculated.json"

    generate_recency_zones_data(draw_history_file, output_file_recency)
    print(f"  ✓ Recency zone analysis complete")

    print("\n" + "=" * 70)
    print("✓ All Analysis Phases Complete!")
    print("=" * 70)

    # ===== VERIFICATION: CHECK ALL JSON FILES WERE GENERATED =====
    print("\n" + "=" * 70)
    print("VERIFICATION: Checking all JSON files were generated")
    print("=" * 70)

    import os
    from pathlib import Path

    expected_files = [
        "data/lotto_odds_results.json",
        "data/lotto_trigger_periods.json",
        "data/lotto_draw_history.json",
        "data/lotto_7_number_freshness_results.json",
        "data/lotto_distribution_stats.json",
        "data/lotto_bonus_analysis.json",
        "data/lotto_bonus_to_main_patterns.json",
        "data/lotto_consecutive_pairs_validated.json",
        "data/lotto_odd_even_validated.json",
        "data/lotto_range_spread_validated.json",
        "data/lotto_sum_contribution_validated.json",
        "data/lotto_freshness_patterns_validated.json",
        "data/lotto_hmc_categorization_validated.json",
        "data/lotto_long_term_patterns.json",
        "data/lotto_statistics_analysis.json",
        "data/lotto_window_saturation_calculated.json",
        "data/lotto_advanced_patterns.json",
        "data/lotto_recency_zones_calculated.json"
    ]

    missing_files = []
    generated_files = []

    for file_path in expected_files:
        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            generated_files.append(f"  ✓ {file_path} ({size:,} bytes)")
        else:
            missing_files.append(f"  ✗ {file_path} - MISSING!")

    print(f"\nGenerated {len(generated_files)}/{len(expected_files)} JSON files:")
    for f in generated_files:
        print(f)

    if missing_files:
        print(f"\n⚠️  WARNING: {len(missing_files)} files are MISSING:")
        for f in missing_files:
            print(f)
        print("\n❌ INCOMPLETE: Not all JSON files were generated!")
        print("   Please check the error messages above for details.")
    else:
        print(f"\n✅ SUCCESS: All {len(expected_files)} JSON files generated successfully!")

    print("=" * 70)


if __name__ == "__main__":
    main()