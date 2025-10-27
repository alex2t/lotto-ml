from datetime import datetime
from typing import Dict, List, Tuple

# Configuration constants
THRESHOLD_RED = 10
THRESHOLD_PURPLE = 30
THRESHOLD_YELLOW = 52


def get_weeks_ago(date_str: str) -> float:
    """Calculate the number of weeks between today and the given date."""
    try:
        date = datetime.strptime(date_str, "%Y/%m/%d")
        diff = datetime.now() - date
        return diff.days / 7.0
    except:
        return None


def get_color_for_date(date_str: str) -> str:
    """Return color code based on recency."""
    weeks = get_weeks_ago(date_str)
    
    if weeks is None:
        return "#000000"
    
    if weeks < THRESHOLD_RED:
        return "#FF0000"
    elif weeks < THRESHOLD_PURPLE:
        return "#800080"
    elif weeks < THRESHOLD_YELLOW:
        return "#FFD700"
    else:
        return "#000000"


def abbreviate_series_name(series_name: str) -> str:
    """Convert '15_consecutives_5_times' to '15c5t' format."""
    try:
        parts = series_name.split('_')
        return f"{parts[0]}c{parts[2]}t"
    except:
        return series_name


def expand_series_data(series_dict: Dict) -> Dict[str, Tuple]:
    """Expand series data dictionary into individual columns."""
    result = {}
    
    for series_name, series_list in series_dict.items():
        if series_list and len(series_list) > 0:
            latest = series_list[-1]
            end_date = latest.get("end_date", "N/A")
            color = get_color_for_date(end_date)
            result[series_name] = (end_date, color)
        else:
            result[series_name] = None
    
    return result


def extract_window_size(series_name: str) -> int:
    """Extract the window size from a series name."""
    try:
        return int(series_name.split('_')[0])
    except:
        return float('inf')


def sort_series_names(series_names: List[str]) -> List[str]:
    """Sort series names by window size (smallest to largest)."""
    return sorted(series_names, key=extract_window_size)


def get_category_color(category: str) -> str:
    """Return color code for category badge."""
    colors = {
        'hot': '#FF4444',
        'medium': '#FFA500',
        'cold': '#4169E1'
    }
    return colors.get(category.lower(), '#666666')