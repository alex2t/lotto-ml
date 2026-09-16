"""
interaction_thresholds.py
=========================
Shared rules for binary interaction features.

Two places must agree on these: the analyzer that mines interactions from history
(lotto_analysis/analyzers/feature_interaction_analyzer.py) and the calculator that
applies them at training and prediction time (ml_lotto/features/interactions.py).

When they disagreed, two whole classes of interaction feature were silently dead:
a threshold at the floor of a distribution made `value >= threshold` always true, and
mismatched recency bands meant a third of candidates could never match any triple.
"""

from typing import Optional, Sequence

# Recency bands for triple interactions, in ascending order of days since last hit.
RECENCY_BANDS = (
    (7, 'very_recent'),
    (21, 'recent'),
    (60, 'moderate'),
)
RECENCY_OLDEST = 'old'


def recency_level(days_since_last: int) -> str:
    """Band a days-since-last-hit value."""
    for limit, label in RECENCY_BANDS:
        if days_since_last <= limit:
            return label
    return RECENCY_OLDEST


def split_threshold(values: Sequence[float], percentile: float = 0.75) -> Optional[float]:
    """
    Smallest threshold at or above `percentile` that actually splits the values.

    A binary interaction tests `value >= threshold`. If the threshold sits at the minimum
    of the distribution the test is vacuously true for every record, producing a feature
    that is always 1 and carries no information. That happens for any zero-inflated
    feature, and for any feature whose source field is missing entirely.

    Returns None when the values are constant, i.e. no split exists.
    """
    ordered = sorted(values)
    if not ordered or ordered[0] == ordered[-1]:
        return None

    candidate = ordered[min(int(len(ordered) * percentile), len(ordered) - 1)]
    if candidate > ordered[0]:
        return candidate
    return next(value for value in ordered if value > candidate)
