"""
prediction package
==================
Handles all prediction and number selection logic.
"""

from ml_lotto.prediction.predictor import (
    generate_predictions,
    generate_all_picks
)

__all__ = [
    'generate_predictions',
    'generate_all_picks'
]