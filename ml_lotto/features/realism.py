"""
realism.py
==========
Priority 3 realism features using JSON data sources.

All features have been migrated to JSON-loaded versions.

NOTE: odd_even_affinity, sum_contribution_score and range_spread_affinity were replaced by
JSON-loaded *_json features, which were themselves deleted in F-24 (no model used them).

This file is now empty but kept for backwards compatibility.
"""

from typing import Dict, Any
from ml_lotto.config import MAX_NUMBER