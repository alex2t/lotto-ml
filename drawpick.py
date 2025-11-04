#!/usr/bin/env python3
"""
Lottery Analysis - Main Entry Point
Orchestrates all analysis phases and generates output files
"""

from collections import defaultdict
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
from lotto_analysis.analyzers.distribution_analyzer import analyze_distribution_patterns
from lotto_analysis.utils.output_generator import (
    generate_hmc_analysis, generate_draw_range_analysis, 
    write_json_file, format_date_iso
)

def main():
    """Main execution function"""
    print("=" * 70)
    print("Lottery Analysis Program (Pattern + HMC Range + Consecutive + Distributions)")
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
        }
    }
    
    # ===== WRITE OUTPUT FILES =====
    write_json_file(OUTPUT_FILE_MAIN, final_main, 
                   "Includes scenarios, HMC, draw_range, and consecutive patterns")
    write_json_file(OUTPUT_FILE_PERIODS, final_periods,
                   "Per-number data with category, recent, and series")
    write_json_file(OUTPUT_FILE_HISTORY, draw_history_log,
                   "Per-draw history for HMC state and winning numbers details")
    
    final_freshness_data = format_freshness_output(
        freshness_counts, total_draws_freshness, TARGET_FRESHNESS_WINDOW, C_MAX_THRESHOLD
    )
    write_json_file(OUTPUT_FILE_7_NUMBERS, final_freshness_data,
                   "Comprehensive freshness distribution for all 7 winning numbers")
    
    write_json_file(OUTPUT_FILE_DISTRIBUTIONS, final_distribution_stats,
                   "Odd/Even patterns and Sum distributions (both 6 and 7 numbers) for ML")

    print("\n" + "=" * 70)
    print("Analysis Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()