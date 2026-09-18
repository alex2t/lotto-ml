"""The permutation check destroys the number-outcome link and nothing else."""

import numpy as np
import pandas as pd
import pytest

from ml_lotto.config import MAX_NUMBER
from ml_lotto.models.permutation_check import empirical_p, shuffle_within_draws

N_DRAWS = 30


@pytest.fixture
def df():
    rng = np.random.default_rng(3)
    hits = np.zeros((N_DRAWS, MAX_NUMBER), dtype=int)
    for row in hits:
        row[rng.choice(MAX_NUMBER, size=7, replace=False)] = 1
    return pd.DataFrame({
        'feature': np.arange(N_DRAWS * MAX_NUMBER, dtype=float),
        'hit': hits.ravel(),
    })


def test_every_draw_keeps_its_hit_count(df):
    shuffled = shuffle_within_draws(df, np.random.default_rng(0))
    before = df['hit'].to_numpy().reshape(-1, MAX_NUMBER).sum(axis=1)
    after = shuffled['hit'].to_numpy().reshape(-1, MAX_NUMBER).sum(axis=1)
    assert (before == after).all()


def test_labels_move_and_features_do_not(df):
    original = df.copy()
    shuffled = shuffle_within_draws(df, np.random.default_rng(0))

    assert (shuffled['hit'] != df['hit']).mean() > 0.1, "labels were not shuffled"
    assert shuffled['feature'].equals(df['feature'])
    assert df.equals(original), "the input frame must not be modified"


def test_shuffle_is_reproducible_per_seed(df):
    a = shuffle_within_draws(df, np.random.default_rng(5))['hit']
    b = shuffle_within_draws(df, np.random.default_rng(5))['hit']
    c = shuffle_within_draws(df, np.random.default_rng(6))['hit']
    assert a.equals(b)
    assert not a.equals(c)


def test_a_frame_that_is_not_whole_draws_is_rejected(df):
    with pytest.raises(ValueError):
        shuffle_within_draws(df.iloc[:-1], np.random.default_rng(0))


@pytest.mark.parametrize('real,null,expected', [
    (0.60, [0.50, 0.52, 0.55], 1 / 4),      # beats every null run: the smallest p possible
    (0.40, [0.50, 0.52, 0.55], 4 / 4),      # below every null run
    (0.52, [0.50, 0.52, 0.55], 3 / 4),      # a tie counts against the real run
])
def test_empirical_p(real, null, expected):
    assert empirical_p(real, null) == pytest.approx(expected)
