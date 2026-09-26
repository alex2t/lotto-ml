"""
The freshness tests measure against what a fair draw gives, not a uniform spread (F-69).

A drawn ball's freshness bin is how many of the 5 preceding draws had it among the main six. In a
fair draw most balls are in C0 - 5 draws hold at most 30 of the 47 numbers - so testing the bins
against a third each reported "freshness bias detected" (p 1.9e-160) for what chance produces. The
pattern test and the top-pattern test made the same mistake against 1/26 per pattern.
"""

import random
from math import comb

from lotto_analysis.analyzers.freshness_analyzer_7_numbers import (
    analyze_7_number_freshness,
    build_distribution_list,
)
from lotto_analysis.analyzers.freshness_pattern_analyzer import (
    analyze_freshness_patterns,
    fair_pattern_probabilities,
)

WINDOW = 5
C_MAX = 2
N_DRAWS = 500
SEEDS = range(40)


def draw_history(draws):
    """The draw history log as `hmc_analyzer.py` writes it: main-6 counts over the 5 draws before."""
    log = {}
    for i in range(WINDOW, len(draws)):
        preceding = draws[i - WINDOW:i]
        log[i] = {'winning_numbers_details': [
            {'recent_counts': {f'last_{WINDOW - 1}': sum(n in d[:6] for d in preceding)},
             'is_bonus': pos == 6}
            for pos, n in enumerate(draws[i])
        ]}
    return log


def freshness_data(draws):
    counts, total = analyze_7_number_freshness(draw_history(draws), WINDOW, C_MAX)
    return {
        'window_size_W': WINDOW,
        'c_max_threshold': C_MAX,
        'total_draws_analyzed': total,
        'distribution_analysis_7_numbers': build_distribution_list(counts, total, C_MAX),
    }


def fair_draws(seed, n_draws=N_DRAWS):
    rng = random.Random(seed)
    return [rng.sample(range(1, 48), 7) for _ in range(n_draws + WINDOW)]


def repeating_draws(seed):
    """Each draw takes two balls from the draw before: recent numbers really do come up more."""
    rng = random.Random(seed)
    draws = [rng.sample(range(1, 48), 7)]
    for _ in range(N_DRAWS + WINDOW - 1):
        kept = rng.sample(draws[-1][:6], 2)
        rest = rng.sample([n for n in range(1, 48) if n not in kept], 5)
        draws.append(kept + rest)
    return draws


def fair_results():
    return [analyze_freshness_patterns(freshness_data(fair_draws(seed))) for seed in SEEDS]


def flagged_share(results, test_key):
    return sum(r[test_key]['significant'] for r in results) / len(results)


def test_fair_draws_rarely_flag_any_freshness_test():
    """40 fair histories: each test may flag about 5% of them (all three flagged every one)."""
    results = fair_results()
    for key in ('bin_distribution_test', 'pattern_distribution_test', 'top_pattern_validation'):
        assert flagged_share(results, key) <= 0.15, key


def test_fair_draws_leave_the_weights_unvalidated():
    """The top pattern's weights are marked validated only when both tests flag it."""
    validated = [
        all(w['statistically_validated'] for w in r['validated_weights'].values())
        for r in fair_results()
    ]
    assert sum(validated) <= 2


def test_bin_chance_is_binomial():
    """A drawn ball is in the main six of each preceding draw with chance 6/47, independently."""
    probs = fair_pattern_probabilities(WINDOW, C_MAX)
    q = 6 / 47
    c0 = sum(p * pattern[0] for pattern, p in probs.items()) / 7
    c1 = sum(p * pattern[1] for pattern, p in probs.items()) / 7
    assert abs(sum(probs.values()) - 1) < 1e-12
    assert abs(c0 - (1 - q) ** 5) < 1e-12
    assert abs(c1 - comb(5, 1) * q * (1 - q) ** 4) < 1e-12


def test_pattern_chance_matches_simulated_fair_draws():
    """Every pattern's stated chance is what 20,000 fair draws produce, within 1 point."""
    data = freshness_data(fair_draws(0, 20_000))
    probs = fair_pattern_probabilities(WINDOW, C_MAX)
    for entry in data['distribution_analysis_7_numbers']:
        observed = entry['draws_matched'] / data['total_draws_analyzed']
        assert abs(observed - probs[(entry['C0'], entry['C1'], entry['C_GE_2'])]) < 0.01


def test_a_real_freshness_bias_is_flagged():
    """When every draw repeats two balls of the one before, the bin and pattern tests say so."""
    result = analyze_freshness_patterns(freshness_data(repeating_draws(1)))
    assert result['bin_distribution_test']['significant']
    assert result['pattern_distribution_test']['significant']
    assert result['bin_distribution_test']['bin_analysis']['C0']['under_represented']
