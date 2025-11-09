"""
realism.py
==========
Priority 3 realism features using JSON data sources.

All features have been migrated to JSON-loaded versions.

NOTE: Removed duplicate calculated features (use JSON versions instead):
- odd_even_affinity → use odd_even_json
- sum_contribution_score → use sum_contribution_json
- range_spread_affinity → use range_spread_json

This file is now empty but kept for backwards compatibility.
"""

from typing import Dict, Any
from ml_lotto.config import MAX_NUMBER