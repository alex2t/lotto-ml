# pages/__init__.py
"""
Lotto Analysis Dashboard Pages Module
"""

from . import trigger_analysis
from . import draw_history
from . import statistics
from . import freshness_analysis

__all__ = [
    'trigger_analysis',
    'draw_history',
    'statistics',
    'freshness_analysis'
]
