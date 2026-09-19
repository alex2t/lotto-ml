# JSON artifacts

The handoff between the two stages. `drawpick.py` writes them; `quickpick.py` and the dashboard read
them. **The ML layer never reads `data/irish500.csv`** - adding a draw to the CSV changes nothing
until `drawpick.py` re-runs.

Inventory verified on 2026-09-17 against the files on disk.

## data/ - written by drawpick.py

| File | Size | Top-level structure |
|:--|--:|:--|
| `lotto_draw_history.json` | 4.4 MB | 497 keys, one per draw date (`2021-12-15` ...) |
| `lotto_trigger_periods.json` | 58 KB | 47 keys, one per number |
| `lotto_odds_results.json` | 32 KB | `requested_draws`, `pattern_analysis_draws`, `hmc_analysis_draws`, `hmc_training_draws`, +9 |
| `lotto_advanced_patterns.json` | 45 KB | `metadata`, `summary_statistics`, `per_number_features` |
| `lotto_bonus_analysis.json` | 37 KB | `bonus_validation`, `bonus_category_preference`, `recent_bonus_exclusion`, +4 |
| `lotto_bonus_to_main_patterns.json` | 28 KB | `metadata`, `per_number_transition_profile`, `category_transition_weights`, +4 |
| `lotto_distribution_stats.json` | 22 KB | `total_draws_analyzed`, `analysis_6_main_numbers` (incl. `high_number_distribution`, 2026-09-19), `analysis_all_7_numbers`, +2 |
| `lotto_7_number_freshness_results.json` | 10 KB | `window_size_W`, `c_max_threshold`, `recent_count_key`, +4 |
| `lotto_long_term_patterns.json` | 14 KB | `metadata`, `hmc_pattern_analysis`, `recency_correlation_analysis`, `category_performance_by_recency` |
| `lotto_statistics_analysis.json` | 15 KB | `hmc_distribution`, `days_since_last_hit`, `recent_counts`, +3 |
| `lotto_recency_zones_calculated.json` | 5 KB | `metadata`, `recency_zones_by_category`, `recency_zones_combined`, +4 |
| `lotto_window_saturation_calculated.json` | 6 KB | `description`, `version`, `scipy_optimized`, +8 |
| `lotto_hmc_recommendations.json` | 14 KB | `metadata`, `current_environment`, `recommendations`, `learned_parameters`, +1 |

### Scipy-validated files

Written in Phase 10. Each carries a `metadata` block plus the statistical test that validated it.

| File | Size | Test |
|:--|--:|:--|
| `lotto_consecutive_pairs_validated.json` | 22 KB | chi-square |
| `lotto_odd_even_validated.json` | 17 KB | distribution test, per-number affinity |
| `lotto_range_spread_validated.json` | 28 KB | Levene |
| `lotto_sum_contribution_validated.json` | 27 KB | ANOVA |
| `lotto_freshness_patterns_validated.json` | 8 KB | pattern and bin distribution |
| `lotto_hmc_categorization_validated.json` | 3 KB | ANOVA, pairwise comparisons |
| `lotto_hmc_success_patterns_validated.json` | 6 KB | success correlations, learned weights |

## data/analysis/ - feature mining output

| File | Size | Contents |
|:--|--:|:--|
| `lotto_correlation_matrix.json` | 372 KB | `metadata`, `all_correlations`, `insights` |
| `lotto_feature_interactions.json` | 15 KB | `pairwise_interactions`, `threshold_effects`, `triple_interactions` |
| `lotto_feature_stability.json` | 7 KB | `feature_stability_scores`, `stable_features` |
| `bonus_to_main_analysis.json` | 25 KB | `analysis_summary`, `timing_distribution`, +4 |
| `lotto_core_feature_set.json` | 1 KB | `core_features`, `detailed_recommendations` |
| `lotto_composite_features.json` | <1 KB | `composite_features` - currently **one** entry |

`lotto_composite_features.json` being small is expected, not a fault. `split_threshold()` returns
`None` rather than inventing a split for constant input, so vacuous interactions are filtered out
instead of being emitted as always-true features.

Also present: `lotto_correlation_summary.csv`, `lotto_interaction_summary.csv`,
`lotto_feature_stability_rankings.csv`.

## The two that matter

**`lotto_trigger_periods.json`** - the serving feature source for the four main models, via
`ml_lotto/features/extractor.py`. Keyed by number, 1 to 47. Change what an analyzer writes here and
you have changed the serving distribution; training must change to match or parity breaks silently.

**`lotto_draw_history.json`** - the draw record the walk-forward training engine reads. Keyed by
date. Starts at `TRAINING_DATA` (draw 100), which is why counts derived from it differ from counts
over the full CSV.

Everything else is supporting detail. If you are short of time, understand these two.

## Regenerating

```bash
python drawpick.py      # rewrites all of the above, ~1-2 min
```

There is no partial regeneration. `drawpick.py` runs all 16 phases or none.

## Rules

- **Treat these as build output.** Never hand-edit one. The next `drawpick.py` run overwrites it,
  and a hand-edited artifact that survives into training is undetectable.
- **A missing key must raise.** `ml_lotto/data/loader.py` validates strictly on purpose. A
  `.get(key, 0)` that papers over a missing field fabricates a constant column and hides the bug.
- **Stale artifacts are the most common silent failure.** After changing anything in
  `lotto_analysis/`, re-run `drawpick.py` before `quickpick.py`.
  `tests/test_walk_forward_parity.py` reads these files and will fail until you do - that is the test
  working, not a broken test.
