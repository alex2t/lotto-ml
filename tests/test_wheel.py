"""The Model 4 wheel keeps its covering guarantee."""

from itertools import combinations

import pytest

from ml_lotto.prediction.wheel import WHEEL_SIZE, wheel_lines

POOL = [41, 7, 23, 12, 38, 3, 29, 17, 45, 9, 33, 1, 20, 26, 14, 47, 5, 36, 30, 11]


def test_four_lines_of_six_distinct_numbers():
    lines = wheel_lines(POOL)
    assert len(lines) == 4
    for line in lines:
        assert len(set(line)) == 6
        assert line == sorted(line)


def test_lines_use_only_the_top_of_the_ranked_pool():
    used = {n for line in wheel_lines(POOL) for n in line}
    assert used == set(POOL[:WHEEL_SIZE])


def test_every_triple_of_the_top_eight_is_in_some_line():
    lines = [set(line) for line in wheel_lines(POOL)]
    for triple in combinations(POOL[:WHEEL_SIZE], 3):
        assert any(set(triple) <= line for line in lines), triple


@pytest.mark.parametrize("winners_in_top", [3, 4, 5, 6])
def test_any_draw_with_enough_winners_in_top_eight_matches_three(winners_in_top):
    """Every draw with this many winners in the top 8 hits 3+ on some line."""
    lines = [set(line) for line in wheel_lines(POOL)]
    outside = [n for n in range(1, 48) if n not in POOL[:WHEEL_SIZE]][:6 - winners_in_top]
    for inside in combinations(POOL[:WHEEL_SIZE], winners_in_top):
        draw = set(inside) | set(outside)
        assert max(len(draw & line) for line in lines) >= 3, sorted(draw)


def test_short_pool_is_rejected():
    with pytest.raises(ValueError):
        wheel_lines(POOL[:7])
