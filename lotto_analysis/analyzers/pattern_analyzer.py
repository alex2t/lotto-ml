"""
Pattern analysis for lottery draws
"""

from collections import Counter, defaultdict
from typing import List, Dict, Set, Tuple
from ..config import SCENARIOS, MAX_NUMBER


def build_windows(draws: List[Dict], window_size: int) -> List[Dict]:
    """
    Return windows for this window_size; each window contains counts and index/date bounds.
    
    Args:
        draws: List of draw dictionaries
        window_size: Size of the sliding window
        
    Returns:
        List of window dictionaries
    """
    windows = []
    n = len(draws)
    total = max(0, n - window_size + 1)
    
    for i in range(total):
        window = draws[i:i + window_size]
        flat = [num for d in window for num in d["numbers"]]
        counts = Counter(flat)
        windows.append({
            "window_size": window_size,
            "start_idx": i,
            "end_idx": i + window_size - 1,
            "start_date": window[0]["date"],
            "end_date": window[-1]["date"],
            "counts": counts
        })
    return windows


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Check if two intervals overlap."""
    return not (a_end < b_start or b_end < a_start)


def process_pattern_analysis(draws: List[Dict]) -> Tuple[Dict, Dict, Dict]:
    """
    Analyzes draw patterns and returns pattern data.
    
    Args:
        draws: List of draw dictionaries
        
    Returns:
        Tuple of (assigned_matches_by_number, assigned_windows_by_category, total_windows_by_size)
    """
    # Build windows for each scenario window size
    windows_by_size = {}
    total_windows_by_size = {}
    
    for s in SCENARIOS:
        w = s["window"]
        wlist = build_windows(draws, w)
        windows_by_size[w] = wlist
        total_windows_by_size[w] = len(wlist)

    # Build match lists
    matches_by_number = defaultdict(list)
    for s in SCENARIOS:
        w = s["window"]
        targets = set(s["targets"])
        for win in windows_by_size.get(w, []):
            wk = (w, win["start_idx"])
            for num in range(1, MAX_NUMBER + 1):
                cnt = win["counts"].get(num, 0)
                if cnt in targets:
                    matches_by_number[num].append({
                        "num": num,
                        "window_size": w,
                        "target": cnt,
                        "start_idx": win["start_idx"],
                        "end_idx": win["end_idx"],
                        "start_date": win["start_date"],
                        "end_date": win["end_date"],
                        "window_key": wk,
                        "category": f"{w}_consecutives_{cnt}_times"
                    })

    # Assign windows exclusively
    assigned_matches_by_number = defaultdict(list)
    assigned_windows_by_category = defaultdict(set)
    
    for num in range(1, MAX_NUMBER + 1):
        matches = matches_by_number.get(num, [])
        matches.sort(key=lambda m: (-m["target"], -m["window_size"], -m["start_idx"])) 
        assigned_intervals = []
        
        for m in matches:
            if any(overlaps(m["start_idx"], m["end_idx"], a0, a1) 
                   for (a0, a1) in assigned_intervals):
                continue
            assigned_intervals.append((m["start_idx"], m["end_idx"]))
            assigned_matches_by_number[num].append(m)
            assigned_windows_by_category[m["category"]].add(m["window_key"])

    return assigned_matches_by_number, assigned_windows_by_category, total_windows_by_size
