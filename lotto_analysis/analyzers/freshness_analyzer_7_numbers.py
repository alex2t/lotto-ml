"""
Comprehensive freshness distribution analysis for 7 winning numbers.
"""

from collections import defaultdict
from typing import Dict, Tuple

def get_top_pattern_from_draws(
    draw_history_log: dict,
    end_draw_index: int,
    target_window: int,
    c_max_threshold: int,
    min_draws_required: int = 50
) -> Dict[int, float]:
    """
    Calculate the top freshness pattern using only draws up to end_draw_index.
    
    Args:
        draw_history_log: Complete draw history
        end_draw_index: Only use draws up to this index (exclusive)
        target_window: Window size (e.g., 5)
        c_max_threshold: Max category threshold (e.g., 2)
        min_draws_required: Minimum draws needed for reliable pattern
        
    Returns:
        Dictionary mapping bin_index -> normalized_weight
    """
    recent_key = f"last_{target_window - 1}"
    
    # Filter draws up to end_draw_index
    analysis_draws = [
        draw for date, draw in draw_history_log.items()
        if draw.get('draw_index', 999999) < end_draw_index
    ]
    
    if len(analysis_draws) < min_draws_required:
        # Not enough data - return balanced default
        num_bins = c_max_threshold + 1
        return {i: 1.0 / num_bins for i in range(num_bins)}
    
    # Run the analysis (reuse existing logic)
    distribution_counts, total_draws = analyze_7_number_freshness(
        {date: draw for date, draw in draw_history_log.items() 
         if draw.get('draw_index', 999999) < end_draw_index},
        target_window,
        c_max_threshold
    )
    
    if not distribution_counts:
        # No patterns found - return balanced default
        num_bins = c_max_threshold + 1
        return {i: 1.0 / num_bins for i in range(num_bins)}
    
    # Get top pattern
    top_pattern_key = max(distribution_counts.items(), key=lambda x: x[1])[0]
    
    # Parse the pattern string to extract counts
    # Example: "C0=3, C1=3, C2=1" or "C0=3, C1=2, C_GE_2=2"
    pattern_dist = {}
    parts = top_pattern_key.split(', ')
    
    for part in parts:
        label, _, value = part.partition('=')
        
        # Determine bin index from label
        if label.startswith('C_GE_'):
            bin_idx = c_max_threshold
        else:
            bin_idx = int(label[1:])  # Extract number from "C0", "C1", etc.
        
        pattern_dist[bin_idx] = int(value)
    
    # Normalize to weights (divide by 7)
    total_numbers = sum(pattern_dist.values())
    if total_numbers == 0:
        total_numbers = 7
        
    normalized_weights = {
        i: pattern_dist.get(i, 0) / total_numbers
        for i in range(c_max_threshold + 1)
    }
    
    return normalized_weights


def analyze_7_number_freshness(draw_history_log: dict, target_window: int, c_max_threshold: int) -> Tuple[Dict[str, int], int]:
    """
    Analyzes the full distribution of recent hit counts (0, 1, ..., C_max) 
    among the 7 winning numbers for a specific window.
    """
    
    recent_key = f"last_{target_window - 1}"
    
    analysis_draws = draw_history_log.values()
    total_draws_analyzed = len(analysis_draws)
    
    distribution_counts = defaultdict(int)
    
    # Dynamically determine the number of bins: C=0 to C=C_max (inclusive)
    num_bins = c_max_threshold + 1
    
    for draw in analysis_draws:
        winning_numbers_details = draw.get('winning_numbers_details', [])
        
        if len(winning_numbers_details) != 7:
            continue
            
        # Initialize counts array dynamically
        counts = [0] * num_bins
        
        # Iterate over all 7 winning numbers details
        for winner in winning_numbers_details:
            recent_count = winner['recent_counts'].get(recent_key, -1)
            
            if recent_count < 0:
                continue

            if recent_count < c_max_threshold:
                # Assign to exact bin (C=0, C=1, C=2, etc.)
                counts[recent_count] += 1
            else:
                # Assign to the final C>=X bin (Index C_max)
                counts[c_max_threshold] += 1
        
        if sum(counts) == 7:
            # Dynamically build the distribution key string
            key_parts = []
            for i in range(c_max_threshold):
                key_parts.append(f"C{i}={counts[i]}")
            
            # **FIXED LOGIC HERE:** Use a label without the '='
            final_bin_label = f"C_GE_{c_max_threshold}"
            key_parts.append(f"{final_bin_label}={counts[c_max_threshold]}")
            
            distribution_key = ", ".join(key_parts)
            distribution_counts[distribution_key] += 1
                 
    return dict(distribution_counts), total_draws_analyzed


def format_freshness_output(counts: Dict[str, int], total_draws: int, target_window: int, c_max_threshold: int) -> Dict:
    """Formats the final output structure and calculates percentages."""
    distribution_list = []
    recent_key = f"last_{target_window - 1}"
    
    # Sort the patterns by count (descending)
    sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    
    # Dynamically create the list of expected C-values for output
    c_keys = [f"C{i}" for i in range(c_max_threshold)] + [f"C_GE_{c_max_threshold}"]
    
    for key, count in sorted_counts:
        percentage = round((count / total_draws) * 100, 2) if total_draws > 0 else 0.0
        
        # Extract C values using the corrected key names
        c_values = {}
        parts = key.split(', ')
        for part in parts:
            # **FIXED LOGIC HERE:** Use partition to handle split safely
            label, _, value = part.partition('=')
            
            # The label should now be clean (e.g., "C0", "C_GE_3")
            c_values[label] = int(value)
        
        output_entry = {
            "pattern": key,
            "draws_matched": count,
            "percentage": percentage
        }
        
        # Insert dynamic C-values into the output_entry
        for i in range(c_max_threshold):
            k = f"C{i}"
            output_entry[k] = c_values.get(k, 0)
        
        final_k = f"C_GE_{c_max_threshold}"
        output_entry[final_k] = c_values.get(final_k, 0)
        
        distribution_list.append(output_entry)

    return {
        "window_size_W": target_window,
        "c_max_threshold": c_max_threshold,
        "recent_count_key": recent_key,
        "total_draws_analyzed": total_draws,
        "distribution_analysis_7_numbers": distribution_list
    }