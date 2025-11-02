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

    # Process trigger data
    processed_trigger_data = []
    all_series_options = set()
    
    for number, data in raw_trigger_data.items():
        record = {
            "Number": int(number),
            "Category": data.get("category", "N/A"),
            "Total Count": data.get("total_count", 0),
            "Last Seen": data.get("last_seen", "N/A"),
            "Series Data": data.get("series", {}).get("series", {})
        }
        
        # Add dynamic recent columns
        recent_data = data.get("recent", {})
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