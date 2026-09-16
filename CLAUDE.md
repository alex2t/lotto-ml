# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An Irish Lotto (6/47 + 1 bonus) analysis and prediction system. Statistical analysis writes ~24 JSON
artifacts to `data/`, an ML layer trains six models on those artifacts, and a Streamlit dashboard
displays the results.

**Read [`issue.md`](issue.md) before starting work.** It is the register of known open defects with
file:line evidence, and it will save you rediscovering them. [`review.md`](review.md) holds the
architecture overview, the scraping plan and the VPS/automation plan.

## Commands

```bash
python drawpick.py      # Stage 1: analysis -> writes ~24 JSON files into data/
python quickpick.py     # Stage 2: trains models, writes lottery_picks.txt + model_metrics/
streamlit run app.py    # Dashboard (8 pages, view/pages/)
```

`drawpick.py` must run before `quickpick.py` — the ML layer reads only the JSON artifacts, never the
CSV directly. Re-run `drawpick.py` after changing anything in `lotto_analysis/`, or the ML layer
will read stale data and train/serve parity will silently break.

### Tests

Only these four files are real tests (37 of them, ~6s). Everything else in `tests/` is a legacy
print-script that runs model training at import — **do not run `pytest tests/` bare.**

```bash
python -m pytest tests/test_walk_forward_parity.py tests/test_selection_invariants.py \
                 tests/test_metrics.py tests/test_no_constant_features.py -q

python -m pytest tests/test_walk_forward_parity.py::test_total_count_matches_serving_json -q   # single test
python -m pytest tests/test_no_constant_features.py -q -k "per_number_constant"                # by pattern
```

`test_walk_forward_parity.py` reads `data/*.json`, so it fails after a source change until
`drawpick.py` is re-run. That is the test doing its job, not a broken test.

### Environment

- Package installs go through `uv`, and this machine needs the system cert store:
  `VIRTUAL_ENV=venv uv pip install --system-certs <pkg>`
- Git cannot reach GitHub with its bundled CA bundle. Prefix remote operations with
  `git -c http.sslBackend=schannel` (push, fetch, ls-remote), or set it globally once.
- `gh` is not installed, so PRs cannot be created from the CLI.

## Architecture

### Two-stage pipeline

```
data/irish500.csv
  -> drawpick.py        (lotto_analysis/analyzers/*, 16 phases)
  -> data/*.json        (~24 artifacts; lotto_trigger_periods.json and
                         lotto_draw_history.json are the two that matter)
  -> quickpick.py       (ml_lotto/*)
  -> lottery_picks.txt, model_metrics/
```

### The six models

Four main models in `ml_lotto/config.py` (`MODEL_1..4_CONFIG`), each picking 6 numbers with its own
feature list and HMC ratio, plus two auxiliary models (`BONUS_MODEL_CONFIG`,
`BONUS_TO_MAIN_MODEL_CONFIG`). Models 1/3/4 label all 7 drawn positions; Model 2 labels the main 6
only (`exclude_bonus=True`).

### The part that matters most: train/serve parity

Training features come from `ml_lotto/features/walk_forward.py`
(`PointInTimeFeatureEngine`). Serving features for the main models come from a **different** path,
`ml_lotto/features/extractor.py` reading `data/lotto_trigger_periods.json`. The two must produce
identical values or a model is fitted on one distribution and applied to another.

This has broken repeatedly. `tests/test_walk_forward_parity.py` is what holds it together — it
asserts 0/47 mismatches on `recent_*`, `total_count` and `draws_since_bonus`.

Conventions currently in force, **do not change one side only**:

| Feature family | Counted over | Both sides |
|:--|:--|:--|
| `recent_4/5/9/24`, `freshness_bin` | **main 6 balls** | `drawpick.py`, `hmc_analyzer.py`, `walk_forward.py` (`cum_main`) |
| `rolling_rate_*`, `rolling_trend_*`, `total_count`, gap stats | **all 7 balls** | `rolling_stats.py`, `walk_forward.py` (`cum_all`) |

Window naming is off by one by design: SCENARIOS window 5 produces the key `last_4` -> feature
`recent_4`. So `recent_4` counts over **5** draws, `recent_9` over 10, `recent_24` over 25.

`extract_features_for_next_draw()` (i.e. `t = N`) is the only correct way to build a serving row.
`extract_features_at_draw(N-1)` conditions on draws `0..N-2` and drops the most recent draw.

### Selection

`predictor.py` orchestrates; `selection.py:pick_line_hybrid` picks by HMC category and freshness
bin; `filters.py` enforces the playable-ticket constraints (sum 84-206, span >= 20, 2-4 odd) with
repair. Constraints belong in `filters.py`, not in model features.

### Interaction features

`lotto_analysis/analyzers/feature_interaction_analyzer.py` mines them, `ml_lotto/features/interactions.py`
applies them, and `lotto_analysis/core/interaction_thresholds.py` holds the split rule and recency
bands **both must share**. When they diverged, entire feature families were silently always-1 or
always-0. Note the package dependency direction is ml_lotto -> lotto_analysis; do not invert it.

## Working on this codebase

**Measure before refactoring.** All four main models sit at validation AUC 0.49-0.53 with Top-7 lift
near 1.0 over 60 draws — chance, which is the correct answer for a fair draw. A change that does not
move those numbers has not helped. `model_metrics/model_comparison.csv` is the scoreboard; the
2 SE noise floor is ~0.031 AUC and ~0.227 Top-7 AvgCaught.

**Distrust silent defaults.** Most bugs found here were `.get(key, 0)` fabricating a constant for a
field that did not exist — phantom `total_count` and `recent_14` columns, vacuous interaction
thresholds, dead freshness weights. A default that hides a missing key hides a bug.

**A feature that never varies is a bug, not a feature.** `tests/test_no_constant_features.py`
enforces this. Full-history per-number constants leak outcome information from the validation
window; globally constant features carry no information at all.

**Verify claims against the artifacts.** Log lines and docs in this repo have asserted things the
code does not do (a "proportionally adjusted" freshness target that is never adjusted, filters
advertised but unimplemented, resolution matrices for fixes not made). Check `lottery_picks.txt` and
`model_metrics/model_comparison.csv` rather than trusting a summary.

**Do not use emoji in new code**, matching the user's global instruction — though note much of the
existing code already prints them.
