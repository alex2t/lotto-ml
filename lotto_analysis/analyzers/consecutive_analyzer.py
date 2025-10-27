"""
Consecutive number pattern analysis
"""

from collections import defaultdict
from typing import List, Dict


def extract_consecutive_runs(sorted_numbers: List[int]) -> List[List[int]]:
    """
    Extract all maximal consecutive runs from a sorted list of numbers.
    A run is a sequence where each number is exactly +1 from the previous.
    
    Args:
        sorted_numbers: Sorted list of numbers
        
    Returns:
        List of runs, where each run is a list of consecutive numbers
    """
    if not sorted_numbers:
        return []
    
    runs = []
    current_run = [sorted_numbers[0]]
    
    for i in range(1, len(sorted_numbers)):
        if sorted_numbers[i] == current_run[-1] + 1:
            # Continue the current run
            current_run.append(sorted_numbers[i])
        else:
            # End current run if it has 2+ numbers
            if len(current_run) >= 2:
                runs.append(current_run[:])
            # Start new run
            current_run = [sorted_numbers[i]]
    
    # Don't forget the last run
    if len(current_run) >= 2:
        runs.append(current_run)
    
    return runs


def analyze_consecutive_patterns(all_draws: List[Dict]) -> Dict:
    """
    Analyze consecutive number patterns across all draws.
    Returns pattern data with odds (probability per draw) and last 20 occurrences.
    
    Args:
        all_draws: List of all draw dictionaries
        
    Returns:
        Dictionary of consecutive patterns with statistics
    """
    total_draws = len(all_draws)
    
    # Track occurrences by run length
    occurrences_by_length = defaultdict(list)
    
    # Track which draws have which run lengths (for counting unique draws)
    draws_with_run_length = defaultdict(set)
    
    for draw_idx, draw in enumerate(all_draws):
        draw_date = draw["date"]
        all_seven = sorted(draw["numbers"])  # All 7 numbers sorted
        
        # Extract all maximal consecutive runs
        runs = extract_consecutive_runs(all_seven)
        
        # Track which run lengths appear in this draw
        run_lengths_in_draw = set()
        
        # Record each run
        for run in runs:
            run_length = len(run)
            occurrences_by_length[run_length].append({
                "draw_index": draw_idx,
                "date": draw_date,
                "numbers": run
            })
            run_lengths_in_draw.add(run_length)
        
        # Mark this draw as having these run lengths
        for rl in run_lengths_in_draw:
            draws_with_run_length[rl].add(draw_idx)
    
    # Build pattern results
    patterns = {}
    
    for run_length in range(2, 8):  # 2 through 7 consecutive
        key = f"{run_length}_consecutive"
        occurrences = occurrences_by_length.get(run_length, [])
        draws_with_pattern = len(draws_with_run_length.get(run_length, set()))
        
        # Calculate odds: how many draws had this pattern / total draws
        odds = (draws_with_pattern / total_draws) if total_draws > 0 else 0.0
        
        # Get last 20 occurrences (most recent first)
        last_20 = occurrences[-20:] if len(occurrences) > 0 else []
        last_20.reverse()  # Most recent first
        
        patterns[key] = {
            "hit_count": draws_with_pattern,
            "total_draws": total_draws,
            "odds": round(odds, 4),
            "last20": [
                {
                    "date": occ["date"],
                    "numbers": occ["numbers"]
                }
                for occ in last_20
            ]
        }
    
    return patterns
