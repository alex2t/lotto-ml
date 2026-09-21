"""
How often each pair of numbers has come up in the same draw.

The dossier shows a number's most frequent partners. That is a fact about past draws, so it
is counted here and written to an artifact rather than derived in a page - the website
computes nothing. `consecutive_pair_analyzer.py` counts only neighbours (12-13, 41-42);
this counts every pair.

A pair count is a raw count, not a signal. In a fair draw every pair is equally likely, and
over 499 draws the expected count for any pair is small enough that the most frequent pairs
are ordinary sampling noise - which is why the artifact carries the fair-draw expectation
beside every count, so a page can show the two together the way F-38 requires for odd/even.
"""

from collections import defaultdict
from itertools import combinations
from typing import Any, Dict, List

from ..config import MAX_NUMBER

# A pair is two of the six main numbers; the bonus is not part of the main draw.
MAIN_BALLS = 6


def _expected_pair_count(total_draws: int) -> float:
    """
    How often a given pair appears in `total_draws` fair draws.

    Each draw shows C(6,2) = 15 of the C(47,2) = 1081 possible pairs.
    """
    pairs_per_draw = len(list(combinations(range(MAIN_BALLS), 2)))
    possible_pairs = len(list(combinations(range(MAX_NUMBER), 2)))
    return total_draws * pairs_per_draw / possible_pairs


def analyze_number_pairs(draws: List[Dict[str, Any]], top_n: int = 8) -> Dict[str, Any]:
    """
    Count every pair of main numbers drawn together.

    Args:
        draws: the draw list, each with a 'numbers' sequence of 6 main balls plus a bonus.
        top_n: how many partners to record per number.

    Returns:
        The artifact payload: metadata, per-number partners, and the raw pair counts.
    """
    counts: Dict[str, int] = defaultdict(int)
    partner_counts: Dict[int, Dict[int, int]] = {
        n: defaultdict(int) for n in range(1, MAX_NUMBER + 1)
    }

    for draw in draws:
        main = sorted(draw["numbers"][:MAIN_BALLS])
        for low, high in combinations(main, 2):
            counts[f"{low}-{high}"] += 1
            partner_counts[low][high] += 1
            partner_counts[high][low] += 1

    total_draws = len(draws)
    expected = _expected_pair_count(total_draws)

    per_number = {}
    for number in range(1, MAX_NUMBER + 1):
        # Sort by count, then by number, so the output does not depend on dict order (F-12).
        partners = sorted(
            partner_counts[number].items(), key=lambda item: (-item[1], item[0])
        )
        per_number[str(number)] = {
            "appearances": sum(
                1 for draw in draws if number in draw["numbers"][:MAIN_BALLS]
            ),
            "top_partners": [
                {"number": partner, "count": count}
                for partner, count in partners[:top_n]
            ],
        }

    return {
        "metadata": {
            "analysis_type": "number_pair_cooccurrence",
            "total_draws": total_draws,
            "counted_over": "the 6 main numbers, the bonus excluded",
            "expected_count_per_pair_in_a_fair_draw": round(expected, 4),
            "note": (
                "Raw counts. Every pair is equally likely in a fair draw, so a high count "
                "is sampling noise, not an affinity."
            ),
        },
        "expected_count_per_pair": round(expected, 4),
        "per_number": per_number,
        "pair_counts": dict(sorted(counts.items())),
    }
