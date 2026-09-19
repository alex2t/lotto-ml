# lotto_analysis/analyzers/

Stage 1. Twenty-one analyzer modules (~9.4k lines) called by `drawpick.py` in 16 numbered phases.
Each writes one or more JSON artifacts into `data/`. Nothing here reads a model; this layer is
pure statistics over `data/irish500.csv`.

## The two artifacts that matter

`data/lotto_trigger_periods.json` and `data/lotto_draw_history.json`. Every main-model serving
feature comes from the first via `ml_lotto/features/extractor.py`. If you change what an analyzer
writes into either, you have changed the serving distribution and must change
`ml_lotto/features/walk_forward.py` to match — see `../../ml_lotto/features/CLAUDE.md`.

## Phase order (drawpick.py)

| Phase | Analyzer | Writes |
|:--|:--|:--|
| 1-2 | `hmc_analyzer.py` | feeds `lotto_trigger_periods.json`, `lotto_draw_history.json` (each entry carries `main_numbers` and `bonus_number` for the website - F-25) |
| 3 | `pattern_analyzer.py` | feeds `lotto_odds_results.json` |
| 4 | `consecutive_analyzer.py` | feeds pattern output |
| 5 | `freshness_analyzer_7_numbers.py` | `lotto_7_number_freshness_results.json` |
| 6-7 | `distribution_analyzer.py` | `lotto_distribution_stats.json` (odd/even, sums, and `high_number_distribution` - draws by count of main numbers >= 32, for the dashboard) |
| 8 | `bonus_analyzer.py` | `lotto_bonus_analysis.json` |
| 9 | `bonus_to_main_analyzer.py` | `lotto_bonus_to_main_patterns.json` |
| 10 | `consecutive_pair_analyzer.py`, `odd_even_analyzer.py`, `range_spread_analyzer.py`, `sum_contribution_analyzer.py`, `freshness_pattern_analyzer.py`, `hmc_categorization_analyzer.py`, `long_term_pattern_analyzer.py` | the seven `*_validated.json` / `lotto_long_term_patterns.json` |
| 11 | `analysis/bonus_analysis.py` (not in this folder) | `lotto_statistics_analysis.json` |
| 12 | `window_saturation_analyzer.py` | `lotto_window_saturation_calculated.json` |
| 13 | `advanced_pattern_analyzer.py` | `lotto_advanced_patterns.json` |
| 14 | `recency_zone_analyzer.py` | `lotto_recency_zones_calculated.json` |
| 15 | `feature_interaction_analyzer.py` | `data/analysis/lotto_feature_interactions.json`, `lotto_composite_features.json` |
| 16 | `hmc_recommendation_analyzer.py`, `hmc_success_analyzer.py` | `lotto_hmc_recommendations.json`, `lotto_hmc_success_patterns_validated.json` |

Phase 11 lives in `analysis/`, not here. That is the only cross-folder step in the pipeline.

## Conventions in force

- `hmc_analyzer.py` counts `recent_*` and `freshness_bin` over the **main 6 balls**. `walk_forward.py`
  (`cum_main`) must match. Do not change one side.
- SCENARIOS window naming is off by one **by design**: window 5 produces key `last_4` -> feature
  `recent_4`. `recent_4` counts over 5 draws, `recent_9` over 10, `recent_24` over 25. The windows
  are defined in `../config/config.py`.
- `feature_interaction_analyzer.py` must import its split rule and recency bands from
  `../core/interaction_thresholds.py`. When it hard-coded its own, whole feature families went
  silently always-1. Never inline a threshold here.
- HMC categorization is recency-based (`HMC_METHOD = "recency"`), thresholds 13 / 27 days. The
  frequency-based `HOT_COUNT` / `COLD_COUNT` constants are deprecated leftovers.
- **This layer has no train/validation split, deliberately.** It computes over every draw, which is
  correct for what it writes: the artifacts are read at serving time to build the row for the **next**
  draw, and the next draw has no future to leak from. The `category` feature is not read from here -
  `walk_forward.py` derives it point-in-time, and the serving extractor re-derives it at the next
  draw's date (C-6b). The JSON's categories are dated at the last draw and are for the website;
  since F-24 no ML feature reads them. The only split that exists is
  `ml_lotto/config.py:VALIDATION_SPLIT_RATIO` (0.85), and it governs model fitting only. Do not add a
  split here to "match" it; that would change `lotto_trigger_periods.json` and break parity while
  training stayed put. See F-10 in `issue.md`.

- **Artifacts must be reproducible from the data alone.** Running `drawpick.py` twice on unchanged
  input must produce identical JSON, apart from `generated_date`. Two ways this has been broken, both
  now fixed and both silent:
  - **The clock.** No `datetime.now()` in a computed value. Days-since is measured against the most
    recent draw (`frequency_analyzer.calculate_days_since_last_hit`,
    `hmc_categorization_analyzer.latest_last_seen`), never against today. A clock-derived value makes
    the artifact change daily and drifts it out of scale with the draw-relative thresholds in
    `../config/config.py`. See F-11 in `issue.md`.
  - **Unordered iteration.** No `max()`, `min()` or `next()` over a `set` or `dict` where a tie is
    possible — set iteration order varies between processes under hash randomisation. Sort first.
    The `sorted()` calls in `bonus_to_main_analyzer.py` are load-bearing, not cosmetic. See F-12.

  A spurious diff is worse than untidy: it masks the real one. This class has recurred three times
  (C-2, N-4, F-12).

- **A "random" baseline is the chance in a fair draw, counted the same way as the rate it is
  compared with.** `bonus_to_main_analyzer.py` compared "comes up as a main number within 10 draws"
  with 10/47 - one ball per draw instead of six - and reported a 3.44x boost for what is chance
  (1 - (41/47)^10 = 74.5%). Test a baseline on simulated fair draws: the boost must come out ~1.0
  (`tests/test_bonus_transition_baseline.py`, F-30). The rate's denominator counts only the cases
  that could succeed: a bonus ball in the last 10 draws has no 10-draw window yet (F-32).
- **A draw's `recent_bonus_numbers` ends with its own bonus.** `hmc_analyzer.py` updates the list after
  each draw, so it is the window for the NEXT draw - what serving needs. The window before draw `i` is
  draw `i-1`'s list: use `bonus_analyzer.pre_draw_bonus_window()`. Reading a draw's own list as its
  pre-draw window made every bonus "repeat" (F-33). A 10-draw window averages ~9.2 distinct balls, so
  its chance baseline is distinct / 47, not 10/47.
- **A significance test runs on independent data.** `advanced_pattern_analyzer.py` ran Kendall's tau
  on a rolling, smoothed series - neighbouring points share most of their data - and flagged 61% of
  numbers on fair draws. `trend_is_significant` is now Fisher's exact test on the raw counts of the
  two windows. Check a new test on simulated fair draws: about 5% flagged
  (`tests/test_trend_significance.py`, F-31).

## After changing anything here

Re-run `python drawpick.py` then `python quickpick.py`. The ML layer never reads the CSV, only these
JSON files, so a stale `data/` means train/serve parity breaks with no error. Then run
`/lotto-verify`.
