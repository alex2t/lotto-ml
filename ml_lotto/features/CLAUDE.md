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
`recent_*`, `total_count` and `draws_since_bonus` against the JSON, and on `days_since_last`,
`category` and `days_since_bonus` between the extractor's serving row and the engine's.

**Counted-over conventions - do not change one side only:**

| Feature family | Counted over | Enforced in |
|:--|:--|:--|
| `recent_4/5/9/14/24`, `freshness_bin` | main 6 balls | `walk_forward.py` `cum_main`, `hmc_analyzer.py`, `drawpick.py` |
| `rolling_rate_*`, `rolling_trend_*`, `total_count`, gap stats | all 7 balls | `walk_forward.py` `cum_all`, `rolling_stats.py` |

**Window naming is off by one by design.** `recent_4` counts over 5 draws, `recent_9` over 10,
`recent_24` over 25 - see `cum_main[t] - cum_main[t-5]` at `walk_forward.py:225`.

**Only `extract_features_for_next_draw()` builds a correct serving row** (`t = N`).
`extract_features_at_draw(N-1)` conditions on draws `0..N-2` and silently drops the most recent draw.

**One serving date: `engine.next_draw_date`** (C-6b). Training row `t` counts days to draw `t`'s own
date, so the serving row counts to the next draw's date - the first day after the last draw on a
weekday used by the latest 6 draws (`next_draw_date()`), which picks up schedule changes such as the
2026 move to Mon/Wed/Sat. `extract_features_from_hmc_json(..., reference_date=)` and
`calculate_days_since_bonus(draws, reference_date)` both take it from the engine. `category` is
derived with `hmc_category(days_since_last)` in both paths - never read from the JSON, whose
category is dated at the last draw. Never count days to `datetime.now()`.

**One engine per run.** `quickpick.py` builds a single `PointInTimeFeatureEngine` and each model
uses `engine.with_base_features(its_dict)` - a view sharing the precomputed draw state. Do not
construct another engine inside a trainer; pass `base_engine` down. Gap statistics are running
moments (count, sum, sum of squares, max), not stored gap lists - keep them O(N). See C-15a.

## Modules

| File | Role |
|:--|:--|
| `walk_forward.py` | point-in-time engine; no lookahead. `with_base_features()` gives each model a view of the one engine per run |
| `extractor.py` | serving orchestrator for the four main models, reads the JSON artifacts |
| `base.py` | `total_count`, `days_since_last`, category; dynamic key detection from HMC data |
| `rolling_stats.py` | `rolling_rate_*` / `rolling_trend_*`, counted over all 7 |
| `freshness.py` | `freshness_c0..c3_weight`, `current_freshness_bin` |
| `timing.py` | `days_since_bonus`, `recency_zone_score` |
| `patterns.py` | consecutive-partner and pair-affinity features |
| `interactions.py` | applies mined pairwise/triple interactions |
| `long_term_patterns.py` | reads `lotto_long_term_patterns.json`; its `lt_*` features are used by no model (C-5) - deletion is F-24 |
| `window_saturation.py` | `window_saturation_penalty` from `lotto_odds_results.json`; used by no model since F-21 - deletion is F-24 |
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
- A feature name in a model's `features` list in `../config.py` must be produced by both
  `walk_forward.py` and `extractor.py`. `expand_feature_selection` raises on a name the serving
  features lack (F-15); a name only serving produces still falls back to the base features in training.

## After changing anything here

`python quickpick.py`, then `/lotto-verify`. If you also touched `lotto_analysis/`, run
`python drawpick.py` first.
