#!/usr/bin/env python3
"""
Lottery Analysis - Main Entry Point
Orchestrates all analysis phases and generates output files
"""

from collections import defaultdict
from lotto_analysis.config import (
    CSV_FILE, TOTAL_DRAWS, TRAINING_DATA, NUM_DRAWS, 
    OUTPUT_FILE_MAIN, OUTPUT_FILE_PERIODS, OUTPUT_FILE_HISTORY,
    SCENARIOS, MAX_NUMBER
)
from lotto_analysis.core.data_loader import load_lotto_data
from lotto_analysis.analyzers.pattern_analyzer import process_pattern_analysis
from lotto_analysis.analyzers.consecutive_analyzer import analyze_consecutive_patterns
from lotto_analysis.analyzers.hmc_analyzer import process_hmc_analysis
from lotto_analysis.utils.output_generator import (
    generate_hmc_analysis, generate_draw_range_analysis, 
    write_json_file, format_date_iso
)


def main():
    """Main execution function"""
    print("=" * 70)
    print("Lottery Analysis Program (Pattern + HMC Range + Consecutive)")
    print("=" * 70)
    
    # ===== LOAD DATA =====
    try:
        # NOTE: load_lotto_data still expects CSV_FILE for generating the JSON files.
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
    print(f"Phase 1: HMC Training ({{TRAINING_DATA}} draws)".format(TRAINING_DATA=TRAINING_DATA))
    print("Phase 2: HMC Analysis and History Logging")
    print("=" * 70)
    
    # process_hmc_analysis uses SCENARIOS indirectly via imported helper functions
    (categorization_history, final_frequency, hmc_counts, 
     final_categories, draw_history_log) = process_hmc_analysis(all_draws)
    total_hmc_draws = len(categorization_history)
    
    # ===== PATTERN ANALYSIS =====
    print("\n" + "=" * 70)
    print(f"Phase 3: Pattern Analysis ({{NUM_DRAWS}} draws)".format(NUM_DRAWS=NUM_DRAWS))
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
        key = f"{{run_length}}_consecutive".format(run_length=run_length)
        data = consecutive_patterns[key]
        hit_count = data["hit_count"]
        odds = data["odds"]
        percentage = odds * 100
        print(f"  {{run_length}}-consecutive: {{hit_count}} draws "
              f"({{percentage:.2f}}%), odds: {{odds:.4f}}".format(run_length=run_length, hit_count=hit_count, percentage=percentage, odds=odds))
    
    # ===== BUILD SUPPORTING DATA (for lotto_trigger_periods.json) =====
    total_counts_by_number = defaultdict(int)
    last_seen_by_number = {}
    
    # Loop to fill last_seen_date and total_counts_by_number
    for num in range(1, MAX_NUMBER + 1):
        for draw in all_draws:
            if num in draw["numbers"]:
                total_counts_by_number[num] += 1
                last_seen_by_number[num] = draw["date"]
    
    # Create number-to-category mapping
    num_to_category = {}
    for cat_name, num_list in final_categories.items():
        for num in num_list:
            category_key = cat_name.replace('_numbers', '')
            num_to_category[num] = category_key
    
    # ===== BUILD OUTPUT FILES =====
    print("\n" + "=" * 70)
    print("Building Output Files")
    print("=" * 70)
    
    # Generate analysis data
    hmc_analysis = generate_hmc_analysis(hmc_counts, total_hmc_draws)
    draw_range_analysis = generate_draw_range_analysis(categorization_history, 
                                                       total_hmc_draws)
    
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
            cat = f"{{w}}_consecutives_{{t}}_times".format(w=w, t=t)
            unique_windows_for_cat = assigned_windows_by_category.get(cat, set())
            hit_count = len(unique_windows_for_cat)
            odds = (hit_count / total_wins) if total_wins > 0 else 0.0
            results[f"{{t}}_times".format(t=t)] = {
                "hit_count": hit_count,
                "total_windows": total_wins,
                "odds": round(odds, 4)
            }
        final_main["scenarios"].append({"window_size": w, "results": results})

    final_main["hmc"] = hmc_analysis
    final_main["draw_range"] = draw_range_analysis
    final_main["patterns"] = consecutive_patterns
    
    # Build lotto_trigger_periods (FIXED LOGIC)
    final_periods = {}
    for num in range(1, MAX_NUMBER + 1):
        assigned = assigned_matches_by_number.get(num, [])
        
        # Calculate recent counts
        recent_data = {}
        for scenario in SCENARIOS:
            window_size = scenario["window"] # e.g., 5
            
            # FIX: Use the window size minus 1 for the key name (e.g., last_4)
            param_suffix = window_size - 1
            param_name = f"last_{param_suffix}"
            
            recent_draws = (pattern_draws[-window_size:] if len(pattern_draws) >= window_size 
                          else pattern_draws)
                          
            count = sum(1 for draw in recent_draws if num in draw["numbers"])
            recent_data[param_name] = count # Key is now 'last_4', 'last_6', etc.
            
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

        # Build output for this number
        output = {}
        if total_counts_by_number[num] > 0:
            output["total_count"] = total_counts_by_number[num]
            output["last_seen"] = format_date_iso(last_seen_by_number[num])
            output["category"] = num_to_category.get(num, "unknown")
        
        output["recent"] = recent_data
        
        if series_data:
            output["series"] = {"series": series_data}
        
        final_periods[str(num)] = output
    
    # ===== WRITE OUTPUT FILES =====
    write_json_file(OUTPUT_FILE_MAIN, final_main, 
                   "Includes scenarios, HMC, draw_range, and consecutive patterns")
    write_json_file(OUTPUT_FILE_PERIODS, final_periods,
                   "Per-number data with category, recent, and series")
    write_json_file(OUTPUT_FILE_HISTORY, draw_history_log,
                   "Per-draw history for HMC state and winning numbers details")

    print("\n" + "=" * 70)
    print("Analysis Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()