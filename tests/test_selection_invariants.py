"""
Invariants for ILP line selection.

A generated line must always be a playable ticket: exactly 6 distinct numbers, never
colliding with numbers pre-assigned to the same line, meeting the HMC quotas, the
freshness target and every ticket filter - and it must be the best such line.
"""

from itertools import combinations

import numpy as np
import pytest

from ml_lotto.config import MAX_NUMBER
from ml_lotto.prediction.filters import validate_line
from ml_lotto.prediction.ilp_selection import solve_line

TARGET_PATTERN = {0: 3, 1: 2, 2: 1}


NUMS = np.arange(1, MAX_NUMBER + 1)

# Score shapes whose unconstrained best line breaks one ticket filter each.
SKEWED = {
    'low': 1.0 / NUMS,                       # sum too low
    'high': NUMS / MAX_NUMBER,                # sum too high
    'odd': 0.1 + 0.8 * (NUMS % 2),            # too many odd numbers
    'middle': 1.0 / (1 + np.abs(NUMS - 24)),  # span too narrow
}


def make_world(scores):
    categories = {n: ('hot', 'medium', 'cold')[n % 3] for n in range(1, MAX_NUMBER + 1)}
    freshness_bins = {n: (n // 3) % 3 for n in range(1, MAX_NUMBER + 1)}
    return scores, categories, freshness_bins


@pytest.fixture
def world():
    return make_world(np.random.default_rng(7).random(MAX_NUMBER) * 0.1 + 0.1)


def quotas(h, m, c):
    return {'hot': h, 'medium': m, 'cold': c}


def solve(world, q, target=TARGET_PATTERN, penalties=(), pre=(), min_high=0):
    scores, categories, bins = world
    return solve_line(scores, categories, bins, q, target, set(penalties), list(pre), min_high)


def count(numbers, lookup, key):
    return sum(1 for n in numbers if lookup[n] == key)


@pytest.mark.parametrize('q', [quotas(4, 1, 1), quotas(3, 1, 2), quotas(2, 2, 2), quotas(6, 0, 0)])
def test_line_is_six_distinct_numbers_meeting_every_constraint(world, q):
    _, categories, bins = world
    line = solve(world, q)

    assert len(line) == 6 and len(set(line)) == 6
    assert validate_line(line) == (True, [])
    for cat, quota in q.items():
        assert count(line, categories, cat) == quota
    for b, target in TARGET_PATTERN.items():
        assert count(line, bins, b) == target


def brute_force_best(world, penalties=frozenset()):
    """
    Best (fewest penalised, then highest score) over every 4H+1M+1C line meeting the
    filters and freshness target. Returns (penalised count, score, line).
    """
    scores, categories, bins = world
    by_cat = {cat: [n for n in range(1, MAX_NUMBER + 1) if categories[n] == cat]
              for cat in ('hot', 'medium', 'cold')}
    best = (MAX_NUMBER, -1.0, None)
    for hot in combinations(by_cat['hot'], 4):
        for med in by_cat['medium']:
            for cold in by_cat['cold']:
                line = sorted(hot + (med, cold))
                if not validate_line(line)[0]:
                    continue
                if any(count(line, bins, b) != t for b, t in TARGET_PATTERN.items()):
                    continue
                key = (len(penalties & set(line)), -sum(scores[n - 1] for n in line))
                if key < (best[0], -best[1]):
                    best = (key[0], -key[1], line)
    return best


@pytest.mark.parametrize('shape', ['random', *SKEWED])
def test_line_is_the_optimum_over_every_feasible_line(world, shape):
    world = world if shape == 'random' else make_world(SKEWED[shape])
    line = solve(world, quotas(4, 1, 1))
    assert sum(world[0][n - 1] for n in line) == pytest.approx(brute_force_best(world)[1])


@pytest.mark.parametrize('shape', ['random', *SKEWED])
def test_penalised_numbers_are_avoided_before_any_score_is_weighed(world, shape):
    """
    The diversity penalty is lexicographic: fewest penalised numbers first, then the best
    score (F-16). Penalising the unpenalised optimum forces a trade-off in every world.
    """
    world = world if shape == 'random' else make_world(SKEWED[shape])
    penalties = frozenset(brute_force_best(world)[2])
    count_best, score_best, _ = brute_force_best(world, penalties)

    line = solve(world, quotas(4, 1, 1), penalties=penalties)
    assert len(penalties & set(line)) == count_best
    assert sum(world[0][n - 1] for n in line) == pytest.approx(score_best)


@pytest.mark.parametrize('shape', SKEWED)
def test_filters_bind_when_the_best_numbers_break_them(shape):
    """The unconstrained top 6 fails the filters, so only a binding constraint can pass."""
    world = make_world(SKEWED[shape])
    top_six = sorted(int(n) for n in np.argsort(-world[0], kind='stable')[:6] + 1)
    assert not validate_line(top_six)[0], f"{shape} world does not stress a filter: {top_six}"

    assert validate_line(solve(world, quotas(2, 2, 2))) == (True, [])


def test_pre_assigned_numbers_are_fixed_and_never_reselected(world):
    _, categories, bins = world
    pre = [3, 11]
    q = quotas(2, 1, 1)
    target = {0: 2, 1: 1, 2: 1}

    selected = solve(world, q, target=target, pre=pre)
    ticket = sorted(pre + selected)

    assert len(selected) == 4 and not set(selected) & set(pre)
    assert len(set(ticket)) == 6
    assert validate_line(ticket) == (True, []), "filters apply to the whole ticket"
    for cat, quota in q.items():
        assert count(selected, categories, cat) == quota


def test_penalised_numbers_are_avoided_when_an_alternative_exists(world):
    scores, _, _ = world
    top = [int(n) for n in np.argsort(-scores)[:10] + 1]
    line = solve(world, quotas(2, 2, 2), penalties=top)
    free_line = solve(world, quotas(2, 2, 2))

    assert not set(line) & set(top)
    assert set(free_line) & set(top), "the penalty must actually change the line"


def test_penalised_numbers_are_deprioritised_but_not_banned(world):
    """Penalising nearly everything must still return a full line."""
    penalties = set(range(1, MAX_NUMBER + 1)) - {5}
    line = solve(world, quotas(4, 1, 1), penalties=penalties)
    assert len(set(line)) == 6


def test_infeasible_constraints_raise_instead_of_returning_a_short_line(world):
    with pytest.raises(ValueError, match="No line satisfies"):
        solve(world, quotas(4, 1, 1), target={0: 0, 1: 0, 2: 7})


def test_selection_is_deterministic_for_identical_input(world):
    runs = [solve(world, quotas(4, 1, 1)) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


def test_different_probabilities_produce_different_lines(world):
    """When a new draw shifts the model's probabilities, the picked line must move."""
    scores, categories, bins = world
    line_a = solve(world, quotas(4, 1, 1))
    line_b = solve((scores[::-1].copy(), categories, bins), quotas(4, 1, 1))
    assert line_a != line_b


def high_count(numbers):
    return sum(1 for n in numbers if n >= 32)


BIRTHDAY = np.where(NUMS <= 31, 0.9, 0.1) + NUMS * 1e-4    # 1-31 strongly preferred


@pytest.mark.parametrize('min_high', [2, 3])
def test_minimum_high_numbers_is_enforced_when_scores_favour_low_numbers(min_high):
    """F-19: scores favouring 1-31 make the best line all-birthday, so only the constraint can lift it."""
    world = make_world(BIRTHDAY)
    assert high_count(solve(world, quotas(2, 2, 2))) < min_high, "world does not stress the rule"

    line = solve(world, quotas(2, 2, 2), min_high=min_high)
    assert high_count(line) >= min_high
    assert validate_line(line) == (True, [])


def test_minimum_is_a_floor_not_a_target():
    """Other features may add more high numbers: the 'high' world must keep all it wants."""
    world = make_world(SKEWED['high'])
    assert high_count(solve(world, quotas(2, 2, 2), min_high=2)) > 2


def test_minimum_counts_the_whole_ticket_including_pre_assigned():
    world = make_world(BIRTHDAY)
    pre = [40]
    selected = solve(world, quotas(2, 1, 1), target={0: 2, 1: 1, 2: 1}, pre=pre, min_high=2)
    assert high_count(pre + selected) >= 2
    assert high_count(selected) == 1, "the pre-assigned 40 already counts toward the minimum"
