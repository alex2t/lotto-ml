"""
The odd/even tests measure against what a fair draw gives, not 50/50 (F-38).

A draw counts as "odd" when it has at least as many odd numbers as even. A draw that contains an odd
number is more likely to be one of those, so testing each number's share of odd draws against 0.5
flagged all 24 odd numbers as "statistically validated" on real draws. The overall test also expected
50/50 odd balls, where the pool 1-47 holds 24 odd and 23 even.
"""

import random

import numpy as np
from streamlit.testing.v1 import AppTest

from lotto_analysis.analyzers.odd_even_analyzer import analyze_odd_even_patterns

N_DRAWS = 498
ODD = [n for n in range(1, 48) if n % 2]


def fair_draws(seed, n_draws=N_DRAWS):
    rng = random.Random(seed)
    return [{'numbers': rng.sample(range(1, 48), 6)} for _ in range(n_draws)]


def affinities(seed):
    return analyze_odd_even_patterns(fair_draws(seed), 47)['per_number_affinity']


def test_fair_draws_flag_about_five_percent_of_numbers():
    """10 x 47 = 470 numbers with no affinity: about 5% may have p < 0.05 (was over half)."""
    flagged = sum(a['p_value'] < 0.05 for seed in range(10) for a in affinities(seed).values())
    assert 0.005 <= flagged / 470 <= 0.10


def test_fair_draws_validate_almost_no_number():
    """After FDR correction a fair draw should validate nothing; allow a stray one over 10 runs."""
    validated = sum(a['statistically_validated'] for seed in range(10) for a in affinities(seed).values())
    assert validated <= 2


def test_chance_share_matches_fair_draws():
    """The stated chance of an odd draw, given the number came up, is what fair draws produce."""
    history = fair_draws(0, 20_000)
    result = analyze_odd_even_patterns(history, 47)['per_number_affinity']
    for parity in (ODD, [n for n in range(1, 48) if n % 2 == 0]):
        observed = np.mean([result[n]['affinity_score'] for n in parity])
        assert abs(observed - result[parity[0]]['chance_affinity_score']) < 0.01


def test_a_real_odd_affinity_is_flagged():
    """Whenever 2 is drawn the other five are odd: 2 prefers odd draws, and it is flagged."""
    rng = random.Random(1)
    history = []
    for draw in fair_draws(1):
        if 2 in draw['numbers']:
            draw = {'numbers': [2] + rng.sample(ODD, 5)}
        history.append(draw)
    two = analyze_odd_even_patterns(history, 47)['per_number_affinity'][2]
    assert two['statistically_validated']
    assert two['preferred_type'] == 'odd'


def test_overall_test_expects_24_odd_in_47():
    """Every number drawn exactly 6 times gives 24/47 odd balls - exactly what a fair draw expects."""
    balls = list(range(1, 48)) * 6
    history = [{'numbers': balls[i:i + 6]} for i in range(0, len(balls), 6)]
    overall = analyze_odd_even_patterns(history, 47)['overall_distribution_test']
    assert overall['chi2_stat'] == 0
    assert not overall['significant']


def test_statistics_page_shows_each_number_against_its_chance():
    """The page shows the fair-draw chance beside each share, and no 'strong preference' (F-38)."""
    at = AppTest.from_string("from view.pages import statistics; statistics.show()", default_timeout=60)
    at.run()
    assert not at.exception
    table = next(df.value for df in at.dataframe if 'Affinity Score' in df.value.columns)
    assert 'Chance' in table.columns
    text = ' '.join(str(m.value) for m in at.markdown).lower()
    assert 'strong preference' not in text and '50/50' not in text
