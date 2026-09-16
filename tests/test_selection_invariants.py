"""
Invariants for hybrid line selection.

A generated line must always be a playable ticket: exactly the requested number of
distinct numbers, never colliding with numbers pre-assigned to the same line.
"""

import numpy as np
import pytest

from ml_lotto.config import MAX_NUMBER
from ml_lotto.prediction.selection import pick_line_hybrid

TARGET_PATTERN = {0: 4, 1: 2, 2: 1}


def make_pools(probabilities, categories, freshness_bins, exclude=()):
    """Build the {hmc: {freshness_bin: [(prob, num)]}} structure selection expects."""
    pools = {cat: {b: [] for b in TARGET_PATTERN} for cat in ('hot', 'medium', 'cold')}
    for num in range(1, MAX_NUMBER + 1):
        if num in exclude:
            continue
        pools[categories[num]][freshness_bins[num]].append((probabilities[num - 1], num))
    for cat in pools:
        for b in pools[cat]:
            pools[cat][b].sort(key=lambda x: (-x[0], x[1]))
    return pools


@pytest.fixture
def world():
    rng = np.random.default_rng(7)
    probabilities = rng.random(MAX_NUMBER) * 0.1 + 0.1
    categories = {n: ('hot', 'medium', 'cold')[n % 3] for n in range(1, MAX_NUMBER + 1)}
    freshness_bins = {n: n % 3 for n in range(1, MAX_NUMBER + 1)}
    features = {n: {'category': categories[n]} for n in range(1, MAX_NUMBER + 1)}
    return probabilities, categories, freshness_bins, features


@pytest.mark.parametrize('config', [
    {'hot_count': 4, 'medium_count': 1, 'cold_count': 1, 'generic_count': 0},
    {'hot_count': 3, 'medium_count': 1, 'cold_count': 2, 'generic_count': 0},
    {'hot_count': 2, 'medium_count': 2, 'cold_count': 2, 'generic_count': 0},
    {'hot_count': 2, 'medium_count': 2, 'cold_count': 1, 'generic_count': 1},
])
def test_line_has_exactly_target_count_distinct_numbers(world, config):
    probabilities, categories, freshness_bins, features = world
    pools = make_pools(probabilities, categories, freshness_bins)
    target = sum(config.values())

    line, _, _ = pick_line_hybrid(
        config, probabilities, features, freshness_bins, TARGET_PATTERN, pools
    )

    assert len(line) == target, f"expected {target} numbers, got {len(line)}: {line}"
    assert len(set(line)) == target, f"duplicate numbers in line: {line}"
    assert all(1 <= n <= MAX_NUMBER for n in line)


def test_zero_count_category_contributes_nothing(world):
    """
    Regression: the bound check ran after the append, so a category asked for 0
    numbers still returned 1, overfilling the line.
    """
    probabilities, categories, freshness_bins, features = world
    pools = make_pools(probabilities, categories, freshness_bins)
    config = {'hot_count': 6, 'medium_count': 0, 'cold_count': 0, 'generic_count': 0}

    line, _, _ = pick_line_hybrid(
        config, probabilities, features, freshness_bins, TARGET_PATTERN, pools
    )

    assert len(line) == 6
    assert len(set(line)) == 6


def test_pre_assigned_numbers_are_never_reselected(world):
    """
    Regression: the safety top-up scanned all 47 numbers and excluded only the
    working line, so it could re-pick a number already pre-assigned to this ticket.
    Combining the two lists then produced a ticket with a repeat.
    """
    probabilities, categories, freshness_bins, features = world
    pre_assigned = [3, 11, 29]
    # Starve the pools so the top-up path is the one under test
    pools = make_pools(probabilities, categories, freshness_bins,
                       exclude=set(range(6, MAX_NUMBER + 1)))
    config = {'hot_count': 2, 'medium_count': 2, 'cold_count': 2, 'generic_count': 0}

    line, _, _ = pick_line_hybrid(
        config, probabilities, features, freshness_bins, TARGET_PATTERN, pools,
        penalty_numbers=set(), pre_assigned_numbers=pre_assigned
    )

    assert not set(line) & set(pre_assigned), (
        f"line {line} collides with pre-assigned {pre_assigned}"
    )
    combined = sorted(pre_assigned + line)
    assert len(set(combined)) == len(combined), f"final ticket has duplicates: {combined}"


def test_penalised_numbers_are_deprioritised_but_not_banned(world):
    """
    A penalised number may still be selected when the unpenalised pool runs out -
    the line must never come back short just because numbers were penalised.
    """
    probabilities, categories, freshness_bins, features = world
    pools = make_pools(probabilities, categories, freshness_bins)
    config = {'hot_count': 4, 'medium_count': 1, 'cold_count': 1, 'generic_count': 0}

    # Penalise nearly everything; selection must still return a full line
    penalties = set(range(1, MAX_NUMBER + 1)) - {5}
    line, _, _ = pick_line_hybrid(
        config, probabilities, features, freshness_bins, TARGET_PATTERN, pools,
        penalty_numbers=penalties
    )

    assert len(line) == 6
    assert len(set(line)) == 6


def test_selection_is_deterministic_for_identical_input(world):
    probabilities, categories, freshness_bins, features = world
    config = {'hot_count': 4, 'medium_count': 1, 'cold_count': 1, 'generic_count': 0}

    runs = [
        pick_line_hybrid(config, probabilities, features, freshness_bins, TARGET_PATTERN,
                         make_pools(probabilities, categories, freshness_bins))[0]
        for _ in range(3)
    ]
    assert runs[0] == runs[1] == runs[2]


def test_different_probabilities_produce_different_lines(world):
    """
    Guards the property the user cares about: when a new draw shifts the model's
    probabilities, the picked line must actually move.
    """
    probabilities, categories, freshness_bins, features = world
    config = {'hot_count': 4, 'medium_count': 1, 'cold_count': 1, 'generic_count': 0}

    line_a, _, _ = pick_line_hybrid(
        config, probabilities, features, freshness_bins, TARGET_PATTERN,
        make_pools(probabilities, categories, freshness_bins)
    )
    reversed_probs = probabilities[::-1].copy()
    line_b, _, _ = pick_line_hybrid(
        config, reversed_probs, features, freshness_bins, TARGET_PATTERN,
        make_pools(reversed_probs, categories, freshness_bins)
    )

    assert line_a != line_b
