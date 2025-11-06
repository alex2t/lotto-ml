"""
base.py
=======
Basic utility functions for feature extraction.

This module contains utility functions that don't fit into specific
feature categories, such as dynamic key detection from HMC data.
"""

import re
from typing import Dict, Any, List, Tuple


def get_dynamic_recent_keys(hmc_data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Dynamically identify all unique 'last_N' keys used for recent counts.
    
    Scans the HMC data structure to find all recent count keys (e.g., 'last_4',
    'last_6', 'last_9', 'last_14') and maps them to ML feature names
    (e.g., 'recent_4', 'recent_6', etc.).
    
    Args:
        hmc_data: HMC statistics dictionary from lotto_trigger_periods.json
        
    Returns:
        List of tuples (data_key, ml_feature_key)
        Example: [('last_4', 'recent_4'), ('last_6', 'recent_6'), ...]
    """
    all_recent_keys = set()
    for num_key, num_data in hmc_data.items():
        if num_key.isdigit() and 'recent' in num_data:
            all_recent_keys.update(num_data['recent'].keys())
            if len(all_recent_keys) >= 4:
                break
    
    dynamic_keys = []
    for data_key in all_recent_keys:
        match = re.match(r'last_(\d+)$', data_key)
        if match:
            window_size = match.group(1)
            ml_feature_key = f'recent_{window_size}'
            dynamic_keys.append((data_key, ml_feature_key))
    
    dynamic_keys.sort(key=lambda x: int(x[1].split('_')[1]))
    return dynamic_keys