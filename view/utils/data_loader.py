# utils/data_loader.py
import streamlit as st
import json
import pandas as pd
from typing import Dict, Any, List, Tuple
from pathlib import Path


@st.cache_data
def load_trigger_data() -> Tuple[pd.DataFrame, Dict[str, Any], List[str], List[str]]:
    """Load and restructure data from trigger periods and odds JSON files."""
    try:
        with open('data/lotto_trigger_periods.json', 'r') as f:
            raw_trigger_data = json.load(f)
        with open('data/lotto_odds_results.json', 'r') as f:
            odds_data = json.load(f)
        with open('data/lotto_draw_history.json', 'r') as f:
            draw_history = json.load(f)
    except FileNotFoundError as e:
        st.error(f"Required JSON file not found: {e.filename}")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON data: {str(e)}")
        st.stop()

    # Extract dynamic recent keys from first number
    first_number_data = next(iter(raw_trigger_data.values()), None)

    if first_number_data and 'recent' in first_number_data:
        dynamic_recent_keys = sorted(
            first_number_data['recent'].keys(),
            key=lambda x: int(x.split('_')[-1])
        )
        dynamic_recent_columns = [
            key.replace('last_', 'Last ') for key in dynamic_recent_keys
        ]
    else:
        dynamic_recent_keys = []
        dynamic_recent_columns = []

    # Get the latest draw to extract current freshness bins
    latest_draw_date = max(draw_history.keys(), key=lambda x: draw_history[x].get('draw_index', 0))
    latest_draw = draw_history[latest_draw_date]

    # Build a mapping of number -> freshness_bin from the latest draw
    number_to_freshness_bin = {}
    for number_detail in latest_draw.get('winning_numbers_details', []):
        number = number_detail.get('number')
        freshness_bin = number_detail.get('current_freshness_bin')
        if number is not None and freshness_bin is not None:
            number_to_freshness_bin[number] = freshness_bin

    # Also check categories_pre_draw for all numbers (winning and non-winning)
    # We need to determine freshness for all 47 numbers
    # The draw history only has freshness for winning numbers, so we need to calculate for others
    # For now, we'll use the data from the most recent draw's winning numbers
    # and set others to None (to be safe)

    # Process trigger data
    processed_trigger_data = []
    all_series_options = set()

    for number, data in raw_trigger_data.items():
        number_int = int(number)

        # Determine freshness bin based on recent counts
        # Use the first recent count key (e.g., last_4) to determine freshness
        recent_data = data.get("recent", {})
        freshness_bin = None

        if dynamic_recent_keys:
            # Use the primary recent count key (usually the smallest window)
            primary_key = dynamic_recent_keys[0]
            recent_count = recent_data.get(primary_key, 0)

            # Determine freshness bin based on count
            # C0: 0 appearances, C1: 1 appearance, C≥2: 2+ appearances
            if recent_count == 0:
                freshness_bin = 0  # C0
            elif recent_count == 1:
                freshness_bin = 1  # C1
            else:
                freshness_bin = 2  # C≥2

        record = {
            "Number": number_int,
            "Category": data.get("category", "N/A"),
            "Total Count": data.get("total_count", 0),
            "Last Seen": data.get("last_seen", "N/A"),
            "Freshness Bin": freshness_bin,
            "Series Data": data.get("series", {}).get("series", {})
        }

        # Add dynamic recent columns
        for key, column_name in zip(dynamic_recent_keys, dynamic_recent_columns):
            record[column_name] = recent_data.get(key, 0)

        processed_trigger_data.append(record)

        # Collect all series names
        for series_name in data.get("series", {}).get("series", {}).keys():
            all_series_options.add(series_name)

    trigger_df = pd.DataFrame(processed_trigger_data)

    return trigger_df, odds_data, sorted(list(all_series_options)), dynamic_recent_columns


@st.cache_data
def load_draw_history() -> Dict[str, Any]:
    """Load draw history data from JSON file."""
    file_path = Path('data/lotto_draw_history.json')
    
    try:
        with open(file_path, 'r') as f:
            draw_data = json.load(f)
        return draw_data
    except FileNotFoundError:
        st.error(f"Draw history file not found at: {file_path}")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"Error decoding draw history JSON: {str(e)}")
        st.stop()


def get_sorted_draw_dates(draw_data: Dict[str, Any]) -> List[str]:
    """Get list of draw dates sorted from oldest to newest."""
    dates = list(draw_data.keys())
    # Sort by draw_index to ensure correct order
    return sorted(dates, key=lambda x: draw_data[x].get('draw_index', 0))