"""
wheel.py
========
Turn the top of Model 4's ranked pool into a covering-design wheel.

The wheel takes the pool's top 8 numbers and plays 4 lines, each omitting one of
four disjoint pairs. A 3-number combination touches at most 3 of the pairs, so
it is contained in the line that omits the fourth: every 3-subset of the top 8
appears in some line. This is the minimum, C(8,6,3) = 4.

Guarantee: if 3 or more winning numbers are among the top 8, some line matches
at least 3. It holds in about 5.3% of draws. It does not raise expected value,
and it lowers the chance of any match-3 compared with 4 unrelated lines (about
7.2%), because every line sits inside the same 8 numbers.

Lines are not passed through filters.py: repairing a line would break the cover.
"""

from typing import List

WHEEL_SIZE = 8
OMITTED_PAIRS = [(0, 1), (2, 3), (4, 5), (6, 7)]


def wheel_lines(ranked_pool: List[int]) -> List[List[int]]:
    """Return 4 sorted 6-number lines covering every 3-subset of the pool's top 8."""
    top = ranked_pool[:WHEEL_SIZE]
    if len(top) < WHEEL_SIZE:
        raise ValueError(f"wheel needs {WHEEL_SIZE} pool numbers, got {len(top)}")
    return [sorted(n for i, n in enumerate(top) if i not in pair) for pair in OMITTED_PAIRS]
