"""
Utils package for Lotto Analysis Dashboard.
Contains data loading and formatting utilities.
"""

from .data_loader import (
    load_trigger_data,
    load_draw_history,
    get_sorted_draw_dates
)

from .formatting import (
    get_weeks_ago,
    get_color_for_date,
    abbreviate_series_name,
    expand_series_data,
    extract_window_size,
    sort_series_names,
    get_category_color,
    THRESHOLD_RED,
    THRESHOLD_PURPLE,
    THRESHOLD_YELLOW
)

__all__ = [
    'load_trigger_data',
    'load_draw_history',
    'get_sorted_draw_dates',
    'get_weeks_ago',
    'get_color_for_date',
    'abbreviate_series_name',
    'expand_series_data',
    'extract_window_size',
    'sort_series_names',
    'get_category_color',
    'THRESHOLD_RED',
    'THRESHOLD_PURPLE',
    'THRESHOLD_YELLOW'
]