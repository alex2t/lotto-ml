#!/usr/bin/env python3
"""
Lottery Analysis - Main Entry Point
Orchestrates all analysis phases and generates output files
"""

import sys
import time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from lotto_analysis.config import (
    CSV_FILE, TOTAL_DRAWS, TRAINING_DATA, NUM_DRAWS,
    OUTPUT_FILE_MAIN, OUTPUT_FILE_PERIODS, OUTPUT_FILE_HISTORY,
    OUTPUT_FILE_7_NUMBERS, OUTPUT_FILE_DISTRIBUTIONS,
    SCENARIOS, MAX_NUMBER,
    FRESHNESS_WINDOW_INDEX, HIGH_NUMBER_FROM
)
from lotto_analysis.core.data_loader import load_lotto_data
from lotto_analysis.analyzers.pattern_analyzer import process_pattern_analysis
from lotto_analysis.analyzers.consecutive_analyzer import analyze_consecutive_patterns
from lotto_analysis.analyzers.hmc_analyzer import process_hmc_analysis
from lotto_analysis.analyzers.freshness_analyzer_7_numbers import (
    analyze_7_number_freshness, analyze_6_main_freshness, format_freshness_output
)
from lotto_analysis.analyzers.distribution_analyzer import (
    analyze_distribution_patterns,
    analyze_high_number_distribution,
    calculate_per_number_distribution_stats
)
from lotto_analysis.analyzers.bonus_analyzer import generate_bonus_analysis
from lotto_analysis.analyzers.bonus_to_main_analyzer import generate_bonus_to_main_analysis

# Import scipy validation analyzers (Phase 10)
from lotto_analysis.analyzers.consecutive_pair_analyzer import analyze_consecutive_pairs
from lotto_analysis.analyzers.number_pair_analyzer import analyze_number_pairs
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

# Import feature interaction analyzer (Phase 15)
from lotto_analysis.analyzers.feature_interaction_analyzer import (
    generate_feature_interaction_analysis,
    save_feature_interaction_outputs
)

# Import HMC recommendation analyzers (Phase 16)
from lotto_analysis.analyzers.hmc_success_analyzer import HMCSuccessAnalyzer
from lotto_analysis.analyzers.hmc_recommendation_analyzer import HMCRecommendationAnalyzer

from lotto_analysis.utils.output_generator import (
    generate_hmc_analysis, generate_draw_range_analysis,
    write_json_file, format_date_iso,
    generate_range_spread_analysis
)

EXPECTED_ARTIFACTS = [
    "data/lotto_odds_results.json",
    "data/lotto_trigger_periods.json",
    "data/lotto_draw_history.json",
    "data/lotto_7_number_freshness_results.json",
    "data/lotto_distribution_stats.json",
    "data/lotto_bonus_analysis.json",
    "data/lotto_bonus_to_main_patterns.json",
    "data/lotto_consecutive_pairs_validated.json",
    "data/lotto_number_pairs.json",
    "data/lotto_odd_even_validated.json",
    "data/lotto_range_spread_validated.json",
    "data/lotto_sum_contribution_validated.json",
    "data/lotto_freshness_patterns_validated.json",
    "data/lotto_hmc_categorization_validated.json",
    "data/lotto_long_term_patterns.json",
    "data/lotto_statistics_analysis.json",
    "data/lotto_window_saturation_calculated.json",
    "data/lotto_advanced_patterns.json",
    "data/lotto_recency_zones_calculated.json",
    "data/analysis/lotto_feature_interactions.json",
    "data/analysis/lotto_interaction_summary.csv",
    "data/analysis/lotto_composite_features.json",
    "data/lotto_hmc_success_patterns_validated.json",
    "data/lotto_hmc_recommendations.json",
    "data/lotto_hmc_recommendations.txt"
]


# st_mtime and time.time() are doubles built from the same clock but rounded differently: a
# file written immediately after run_started can come back about 2.4e-7 seconds before it
# (measured: 534 of 6000 writes on Windows). A run's own artifacts are written seconds or
# minutes later and one left from an earlier run is hours old, so a second of slack tells
# those two apart without ever calling a fresh file stale. See F-61.
MTIME_TOLERANCE_SECONDS = 1.0


def verify_artifacts(expected_files, run_started):
    """Exit non-zero unless every expected artifact was written by this run."""
    bad_files = []
    generated_files = []

    for file_path in expected_files:
        path = Path(file_path)
        if not path.exists():
            bad_files.append(f"  {file_path} - MISSING!")
        elif path.stat().st_mtime < run_started - MTIME_TOLERANCE_SECONDS:
            bad_files.append(f"  {file_path} - STALE, left from an earlier run!")
        else:
            generated_files.append(f"  ✓ {file_path} ({path.stat().st_size:,} bytes)")

    print(f"\nGenerated {len(generated_files)}/{len(expected_files)} JSON files:")
    for f in generated_files:
        print(f)

    if bad_files:
        print(f"\n⚠️  WARNING: {len(bad_files)} files were not written by this run:")
        for f in bad_files:
            print(f)
        print("\n❌ INCOMPLETE: Not all JSON files were generated!")
        print("   Please check the error messages above for details.")
        sys.exit(1)

    print(f"\n✅ SUCCESS: All {len(expected_files)} JSON files generated successfully!")


def main():
    """Main execution function"""
    run_started = time.time()
    print("=" * 70)
    print("Lottery Analysis Program")
    print("Pattern + HMC + Distributions + Bonus + Scipy Validation")
    print("=" * 70)
    
    # **DYNAMIC CONFIGURATION SETUP**
    try:
        target_scenario = SCENARIOS[FRESHNESS_WINDOW_INDEX]
    except IndexError:
        print(f"\nERROR: FRESHNESS_WINDOW_INDEX {FRESHNESS_WINDOW_INDEX} is out of bounds for SCENARIOS list.")
        sys.exit(1)
        
    TARGET_FRESHNESS_WINDOW = target_scenario["window"]
    C_MAX_THRESHOLD = max(target_scenario["targets"])

    print(f"\nFreshness Analysis Settings: W={TARGET_FRESHNESS_WINDOW}, C_max={C_MAX_THRESHOLD}")
    
    # ===== LOAD DATA =====
    try:
        all_draws, available_draws, skipped_rows = load_lotto_data(CSV_FILE, TOTAL_DRAWS)
    except FileNotFoundError:
        print(f"\nERROR: CSV file '{CSV_FILE}' not found. Please place it in the 'data/' folder.")
        sys.exit(1)
    except ValueError as e:
        print(f"\nERROR: Data loading failed: {e}")
        sys.exit(1)
        
    if not all_draws:
        print("No valid draws were loaded.")
        sys.exit(1)
    
    print(f"\nLoaded {len(all_draws)} draws "
          f"(available: {available_draws}, requested: {TOTAL_DRAWS if TOTAL_DRAWS else 'ALL'}, skipped: {skipped_rows})")
    
    # ===== HMC ANALYSIS (Phase 1 & 2) =====
    print("\n" + "=" * 70)
    print(f"Phase 1: HMC Training ({TRAINING_DATA} draws)")
    print("Phase 2: HMC Analysis and History Logging")
    print("=" * 70)
    
    (categorization_history, final_frequency, hmc_counts, 
     hmc_counts_6, final_categories, draw_history_log,
     recent_bonus_hits) = process_hmc_analysis(all_draws)
    total_hmc_draws = len(categorization_history)
    
    # ===== PATTERN ANALYSIS =====
    pattern_draws = all_draws[TRAINING_DATA:]
    num_pattern_draws = len(pattern_draws)
    print("\n" + "=" * 70)
    print(f"Phase 3: Pattern Analysis ({num_pattern_draws} draws)")
    print("=" * 70)
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
    # A generated line is 6 main numbers, so the selection layer targets this one
    main_freshness_counts, _ = analyze_6_main_freshness(
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

    high_number_stats = analyze_high_number_distribution(draw_history_log)
    print(f"\nMain numbers >= {HIGH_NUMBER_FROM} per draw (observed vs fair draw):")
    for k, stats in high_number_stats.items():
        print(f"  {k}: {stats['count']} draws ({stats['percentage']:.2f}%, fair {stats['fair_percentage']:.2f}%)")

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
    # Counted over pattern_draws, NOT all_draws. The ML training matrix is built from
    # lotto_draw_history.json, which starts at TRAINING_DATA, so counting total_count
    # over the full CSV made the served value systematically larger than anything the
    # model saw in training. Matches how the recent_* windows are already counted.
    total_counts_by_number = defaultdict(int)
    last_seen_by_number = {}
    
    for num in range(1, MAX_NUMBER + 1):
        for draw in pattern_draws:
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
    hmc_analysis_6 = generate_hmc_analysis(hmc_counts_6, total_hmc_draws)
    draw_range_analysis = generate_draw_range_analysis(categorization_history, 
                                                       total_hmc_draws)
    draw_range_analysis_6 = generate_draw_range_analysis(categorization_history,
                                                         total_hmc_draws,
                                                         range_key='draw_range_6')
    
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
        "requested_draws": NUM_DRAWS if NUM_DRAWS else num_pattern_draws,
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
    # Over the main 6, for anything comparing a six-number line (F-59).
    final_main["hmc_6"] = hmc_analysis_6
    final_main["draw_range"] = draw_range_analysis
    # Over the main 6, for anything comparing a six-number line (F-63).
    final_main["draw_range_6"] = draw_range_analysis_6
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
                          
            # Main 6 only, matching hmc_analyzer's recent_counts. A number's bonus
            # appearances are carried separately by was_recent_bonus / draws_since_bonus;
            # counting them here too would double-count the bonus signal and would put
            # this file in a different space from lotto_draw_history.json.
            count = sum(1 for draw in recent_draws if num in draw["numbers"][:6])
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
            "sum_distributions": sum_6_stats,
            "high_number_distribution": {
                "high_from": HIGH_NUMBER_FROM,
                "by_count": high_number_stats
            }
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
        freshness_counts, total_draws_freshness, TARGET_FRESHNESS_WINDOW, C_MAX_THRESHOLD,
        main_counts=main_freshness_counts
    )
    write_json_file(OUTPUT_FILE_7_NUMBERS, final_freshness_data,
                   "Freshness distribution for the 7 drawn balls and for the 6 main balls, with weight calculation")
    
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

    # 1b. Every pair, not only the neighbours: the dossier's "often with".
    print("\n  [1b/7] Number Pair Co-occurrence (raw counts over the main 6)...")
    number_pairs_results = analyze_number_pairs(draw_list)
    OUTPUT_FILE_NUMBER_PAIRS = "data/lotto_number_pairs.json"
    write_json_file(OUTPUT_FILE_NUMBER_PAIRS, number_pairs_results,
                   "How often each pair of main numbers has been drawn together")
    print(f"        ✓ Saved to {OUTPUT_FILE_NUMBER_PAIRS}")
    print(f"        Expected per pair in a fair draw: "
          f"{number_pairs_results['expected_count_per_pair']:.2f}")

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
    print("Phase 12: Window Saturation Analysis (Scipy Optimization)")
    print("=" * 70)
    print("Generating data-driven window saturation penalties...")

    stats_file = "data/lotto_statistics_analysis.json"
    odds_file = OUTPUT_FILE_MAIN
    output_file = "data/lotto_window_saturation_calculated.json"
    draw_history_file = OUTPUT_FILE_HISTORY  # Enable scipy optimization

    generate_window_saturation_data(stats_file, odds_file, output_file, draw_history_file)
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

    # ===== FEATURE INTERACTION ANALYSIS (PHASE 15) =====
    print("\n" + "=" * 70)
    print("Phase 15: Feature Interaction Analysis (Pairwise + Triple)")
    print("=" * 70)
    print("Discovering non-linear feature interactions for ML prediction...")
    print("This generates interaction features for Model 1 enhancement")

    try:
        print("\n  Generating feature interaction analysis...")
        interaction_analysis = generate_feature_interaction_analysis(draw_history_log)

        print(f"  ✓ Analyzed {interaction_analysis['metadata']['total_draws']} draws")
        print(f"  ✓ Found {interaction_analysis['metadata']['total_pairwise_interactions']} pairwise interactions")
        print(f"  ✓ Found {interaction_analysis['metadata']['total_triple_interactions']} triple interactions")
        print(f"  ✓ Generated {interaction_analysis['metadata']['total_composite_features']} composite features")

        print("  Saving interaction analysis outputs...")
        save_feature_interaction_outputs(interaction_analysis, output_dir="data/analysis")
        print("  ✓ Interaction analysis complete")

    except Exception as e:
        print(f"  ⚠️  Warning: Feature interaction analysis failed: {e}")
        print("  System will continue without interaction features")
        import traceback
        traceback.print_exc()

    # ===== HMC RECOMMENDATION ANALYSIS (PHASE 16) =====
    print("\n" + "=" * 70)
    print("Phase 16: HMC Configuration Recommendation (Data-Driven)")
    print("=" * 70)
    print("Generating optimal HMC configurations for 3 models...")
    print("All parameters learned from historical backtest data (scipy validated)")

    try:
        # Step 1: Analyze what predicts HMC success
        print("\n[HMC] Analyzing historical success patterns...")
        hmc_success_analyzer = HMCSuccessAnalyzer(
            draws_data=draw_history_log,
            hmc_data=final_main['hmc']
        )
        hmc_success_results = hmc_success_analyzer.analyze()

        # Save success patterns
        hmc_success_file = 'data/lotto_hmc_success_patterns_validated.json'
        write_json_file(hmc_success_file, hmc_success_results)
        print(f"  ✓ HMC success patterns saved to {hmc_success_file}")

        # Step 2: Generate HMC recommendations
        print("\n[HMC] Generating HMC configuration recommendations...")
        hmc_recommender = HMCRecommendationAnalyzer(
            draws_data=draw_history_log,
            hmc_data=final_main['hmc'],
            success_patterns=hmc_success_results
        )
        hmc_recommendations = hmc_recommender.analyze()

        # Save JSON recommendations
        hmc_json_file = 'data/lotto_hmc_recommendations.json'
        write_json_file(hmc_json_file, hmc_recommendations)
        print(f"  ✓ HMC recommendations (JSON) saved to {hmc_json_file}")

        # Generate and save text file
        hmc_text_file = 'data/lotto_hmc_recommendations.txt'
        hmc_recommender.generate_text_report(hmc_recommendations, hmc_text_file)
        print(f"  ✓ HMC recommendations (TEXT) saved to {hmc_text_file}")

        # Print top recommendation summary
        if hmc_recommendations['recommendations']:
            top_rec = hmc_recommendations['recommendations'][0]
            print("\n" + "-" * 70)
            print("TOP HMC RECOMMENDATION (Rank #1)")
            print("-" * 70)
            print(f"Score: {top_rec['total_score']:.2f}")
            print(f"\nModel 1: {top_rec['model_1_config']['pattern']} "
                  f"(h={top_rec['model_1_config']['hot_count']}, "
                  f"m={top_rec['model_1_config']['medium_count']}, "
                  f"c={top_rec['model_1_config']['cold_count']}) "
                  f"- {top_rec['model_1_config']['probability']:.2f}%")
            print(f"Model 2: {top_rec['model_2_config']['pattern']} "
                  f"(h={top_rec['model_2_config']['hot_count']}, "
                  f"m={top_rec['model_2_config']['medium_count']}, "
                  f"c={top_rec['model_2_config']['cold_count']}) "
                  f"- {top_rec['model_2_config']['probability']:.2f}%")
            print(f"Model 3: {top_rec['model_3_config']['pattern']} "
                  f"(h={top_rec['model_3_config']['hot_count']}, "
                  f"m={top_rec['model_3_config']['medium_count']}, "
                  f"c={top_rec['model_3_config']['cold_count']}) "
                  f"- {top_rec['model_3_config']['probability']:.2f}%")
            print(f"\nEnsemble Coverage: {top_rec['ensemble_metrics']['total_coverage']:.2f}%")
            print(f"Diversity Score:   {top_rec['ensemble_metrics']['diversity_score']:.2f}")
            print(f"\n📄 Review full report: {hmc_text_file}")
            print("-" * 70)

        print("  ✓ HMC recommendation analysis complete")

    except Exception as e:
        print(f"  ERROR: HMC recommendation analysis failed: {e}")
        raise

    print("\n" + "=" * 70)
    print("✓ All Analysis Phases Complete!")
    print("=" * 70)

    # ===== VERIFICATION: CHECK ALL JSON FILES WERE GENERATED =====
    print("\n" + "=" * 70)
    print("VERIFICATION: Checking all JSON files were generated")
    print("=" * 70)

    verify_artifacts(EXPECTED_ARTIFACTS, run_started)

    print("=" * 70)


if __name__ == "__main__":
    main()