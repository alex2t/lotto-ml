# ml_lotto/features/

The highest-risk folder in the repo. Training features and serving features are built by two
different code paths here, and they must produce identical values.

## The parity contract

| | Path | Source |
|:--|:--|:--|
| Training | `walk_forward.py` (`PointInTimeFeatureEngine`) | recomputed from draw history |
| Serving (main models) | `extractor.py` | reads `data/lotto_trigger_periods.json` |

A mismatch means a model is fitted on one distribution and applied to another. It does not raise.
`../../tests/test_walk_forward_parity.py` is what holds this together: it asserts 0/47 mismatches on
`recent_*`, `total_count` and `draws_since_bonus`.

**Counted-over conventions - do not change one side only:**

| Feature family | Counted over | Enforced in |
|:--|:--|:--|
| `recent_4/5/9/14/24`, `freshness_bin` | main 6 balls | `walk_forward.py` `cum_main`, `hmc_analyzer.py`, `drawpick.py` |
| `rolling_rate_*`, `rolling_trend_*`, `total_count`, gap stats | all 7 balls | `walk_forward.py` `cum_all`, `rolling_stats.py` |

**Window naming is off by one by design.** `recent_4` counts over 5 draws, `recent_9` over 10,
`recent_24` over 25 - see `cum_main[t] - cum_main[t-5]` at `walk_forward.py:209`.

**Only `extract_features_for_next_draw()` builds a correct serving row** (`t = N`).
`extract_features_at_draw(N-1)` conditions on draws `0..N-2` and silently drops the most recent draw.

## Modules

| File | Role |
|:--|:--|
| `walk_forward.py` | point-in-time engine; no lookahead. `build_walk_forward_dataset()` is the training entry point |
| `extractor.py` | serving orchestrator for the four main models, reads the JSON artifacts |
| `base.py` | `total_count`, `days_since_last`, category; dynamic key detection from HMC data |
| `rolling_stats.py` | `rolling_rate_*` / `rolling_trend_*`, counted over all 7 |
| `freshness.py` | `freshness_c0..c3_weight`, `current_freshness_bin` |
| `timing.py` | `days_since_bonus`, `recency_zone_score` |
| `patterns.py` | consecutive-partner and pair-affinity features |
| `interactions.py` | applies mined pairwise/triple interactions |
| `long_term_patterns.py` | reads `lotto_long_term_patterns.json` |
| `window_saturation.py` | saturation penalties from `lotto_odds_results.json` |
| `history.py` | `win_bias_ratio` |
| `bonus.py`, `bonus_features.py`, `bonus_to_main_features.py` | the two auxiliary models' features |
| `feature_selection.py` | correlation and importance filtering |
| `realism.py` | thin; features migrated to JSON-loaded versions |

## Rules

- **Interaction thresholds are shared.** `interactions.py` must import `recency_level` and
  `split_threshold` from `lotto_analysis/core/interaction_thresholds.py`, the same module the
  analyzer uses. Dependency direction is `ml_lotto -> lotto_analysis`; do not invert it.
- **No silent defaults.** `.get(key, 0)` on a feature dict fabricates a constant when the key is
  missing, which is how phantom `total_count` and `recent_14` columns got in. A missing key is a bug;
  let it fail.
- **A feature that never varies is a bug.** `../../tests/test_no_constant_features.py` enforces it.
  Per-number constants over full history leak outcome information from the validation window.
- Adding a feature name to a model's `features` list in `../config.py` does nothing unless both
  `walk_forward.py` and `extractor.py` produce it.

## After changing anything here

`python quickpick.py`, then `/lotto-verify`. If you also touched `lotto_analysis/`, run
`python drawpick.py` first.
