"""
ilp_selection.py
================
Pick a line by integer linear programming instead of greedy picking plus repair.

    maximise   sum(score_n * x_n) - PENALTY_COST * sum(x_n for penalised n)
    subject to 6 numbers in total, pre-assigned numbers fixed in
               each HMC category  >= its quota          (selected numbers only)
               each freshness bin >= its target count   (selected numbers only)
               MIN_SUM <= sum of the line <= MAX_SUM
               MIN_ODD <= odd numbers     <= MAX_ODD
               max - min >= MIN_SPAN
               numbers >= HIGH_NUMBER_FROM >= min_high   (per model, F-19)

This is the only diversity mechanism (F-16). Scores are probabilities below 1, so two
lines' score sums differ by less than LINE_SIZE; a PENALTY_COST of LINE_SIZE therefore
makes the penalty lexicographic - a penalised number is taken only when no feasible
line avoids it, whatever the probabilities. The span is linearised with two marker vectors:
z picks one selected number as the top, w one as the bottom, and their values must
differ by MIN_SPAN - which holds exactly when the line's span does.

The solver either returns a line meeting every constraint or raises. There is no
repair pass: a constraint cannot look satisfied while not binding.
"""

from typing import Dict, List, Set

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from ml_lotto.config import MAX_NUMBER
from ml_lotto.prediction.constraints import LINE_SIZE
from ml_lotto.prediction.filters import MAX_ODD, MAX_SUM, MIN_ODD, MIN_SPAN, MIN_SUM
from lotto_analysis.config.config import HIGH_NUMBER_FROM

NUMBERS = np.arange(1, MAX_NUMBER + 1)
PENALTY_COST = float(LINE_SIZE)


def solve_line(
    scores: np.ndarray,
    categories: Dict[int, str],
    freshness_bins: Dict[int, int],
    quotas: Dict[str, int],
    target_pattern: Dict[int, int],
    penalty_numbers: Set[int],
    pre_assigned: List[int],
    min_high: int,
) -> List[int]:
    """
    Return the sorted selected numbers (pre-assigned excluded) of the optimal line.

    min_high is the model's floor on numbers >= HIGH_NUMBER_FROM across the whole ticket;
    0 leaves them to the model's probabilities.
    """
    n = MAX_NUMBER
    fixed = np.isin(NUMBERS, pre_assigned)
    free = ~fixed
    odd = NUMBERS % 2 == 1
    zeros = np.zeros(n)

    def row(x, z=zeros, w=zeros):
        return np.concatenate([x, z, w])

    rows, lower, upper = [], [], []

    def add(coeffs, lo, hi):
        rows.append(coeffs)
        lower.append(lo)
        upper.append(hi)

    add(row(np.ones(n)), LINE_SIZE, LINE_SIZE)
    for cat, quota in quotas.items():
        in_cat = np.array([categories[num] == cat for num in NUMBERS])
        add(row((in_cat & free).astype(float)), quota, np.inf)
    for b, count in target_pattern.items():
        in_bin = np.array([freshness_bins[num] == b for num in NUMBERS])
        add(row((in_bin & free).astype(float)), count, np.inf)
    add(row(NUMBERS.astype(float)), MIN_SUM, MAX_SUM)
    add(row(odd.astype(float)), MIN_ODD, MAX_ODD)
    add(row((NUMBERS >= HIGH_NUMBER_FROM).astype(float)), min_high, np.inf)

    eye = np.eye(n)
    for i in range(n):
        add(row(-eye[i], z=eye[i]), -np.inf, 0)
        add(row(-eye[i], w=eye[i]), -np.inf, 0)
    add(row(zeros, z=np.ones(n)), 1, 1)
    add(row(zeros, w=np.ones(n)), 1, 1)
    add(row(zeros, z=NUMBERS.astype(float), w=-NUMBERS.astype(float)), MIN_SPAN, np.inf)

    penalised = np.isin(NUMBERS, list(penalty_numbers))
    gain = np.where(free, scores - PENALTY_COST * penalised, 0.0)
    cost = row(-gain)

    lb = row(fixed.astype(float))
    result = milp(
        cost,
        constraints=LinearConstraint(np.array(rows), lower, upper),
        integrality=np.ones(3 * n),
        bounds=Bounds(lb, np.ones(3 * n)),
    )
    if not result.success:
        raise ValueError(
            f"No line satisfies quotas {quotas}, freshness {target_pattern}, {min_high}+ numbers >= "
            f"{HIGH_NUMBER_FROM} and the "
            f"ticket filters with pre-assigned {sorted(pre_assigned)}: {result.message}"
        )

    chosen = NUMBERS[np.round(result.x[:n]).astype(bool) & free]
    return sorted(int(num) for num in chosen)


def pattern_string(numbers: List[int], freshness_bins: Dict[int, int], target_pattern: Dict[int, int]) -> str:
    """Freshness counts of `numbers` in the C0=.., C1=.., C_GE_k=.. display format."""
    top = max(target_pattern)
    counts = {b: sum(1 for num in numbers if freshness_bins[num] == b) for b in sorted(target_pattern)}
    return ", ".join(f"C{b}={c}" if b < top else f"C_GE_{top}={c}" for b, c in counts.items())
