"""
Data loading and parsing utilities for lottery data
"""

import re
import pandas as pd
from typing import List, Dict, Tuple


def load_lotto_data(filename: str, requested_draws: int) -> Tuple[List[Dict], int, int]:
    """
    Read CSV, detect date/number columns, parse rows (skip invalid),
    and return chronological draws oldest->newest (so index increases in time).
    
    Args:
        filename: Path to the CSV file
        requested_draws: Number of draws to load
        
    Returns:
        Tuple of (parsed_draws, available_draws, skipped_rows)
    """
    df = pd.read_csv(filename, dtype=str)
    available_draws = len(df)
    df_head = df.head(requested_draws)

    # Detect date column
    date_cols = [c for c in df_head.columns if re.search(r'(?i)\bdate\b', c)]
    if not date_cols:
        raise ValueError("No Date column found in CSV.")
    date_col = date_cols[0]

    # Detect number columns (Num*, Bonus)
    num_cols = [c for c in df_head.columns if re.search(r'(?i)\bnum|bonus\b', c)]
    if not num_cols:
        raise ValueError("No number columns found (expected Num1–Num6 and Bonus).")

    parsed = []
    skipped_rows = 0
    
    for _, row in df_head.iterrows():
        # Parse date
        raw_date = row.get(date_col, "")
        dt = pd.to_datetime(raw_date, dayfirst=True, errors='coerce')
        if pd.isna(dt):
            skipped_rows += 1
            continue
            
        # Parse numbers (allow '06' etc.)
        nums = []
        ok = True
        for c in num_cols:
            val = row.get(c, "")
            if pd.isna(val) or str(val).strip() == "":
                ok = False
                break
            digits = "".join(ch for ch in str(val) if ch.isdigit())
            if digits == "":
                ok = False
                break
            nums.append(int(digits))
            
        if not ok:
            skipped_rows += 1
            continue
            
        parsed.append({"date": dt.strftime("%Y-%m-%d"), "numbers": nums})

    # CSV gives latest first; we want chronological oldest -> newest
    parsed = list(reversed(parsed))
    return parsed, available_draws, skipped_rows


def extract_all_winning_numbers(draw: Dict) -> List[int]:
    """
    Extracts all 7 winning numbers (Num1-6 + Bonus) from a draw record.
    
    Args:
        draw: Dictionary containing draw data
        
    Returns:
        List of winning numbers
    """
    return draw["numbers"]
