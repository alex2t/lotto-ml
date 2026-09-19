# Features

What the models are trained on, where each family is computed, and which model uses what.

The train/serve parity contract - the thing that breaks most often - is **not** repeated here. It
lives in `ml_lotto/features/CLAUDE.md`, which is loaded automatically. Read that before changing any
feature.

## Verified state

Checked against the code on 2026-09-19:

- `PointInTimeFeatureEngine.extract_features_for_next_draw()` produces **65 keys** per number (73
  before F-24 deleted the 8 unused full-history features).
- Every named feature requested by the six model configs **is** produced. Zero missing.

That second point matters. The historical failure mode here was a config naming a feature that no
extractor produced, which `.get(key, 0)` then silently filled with a constant. Re-run this check
after changing a feature list:

```bash
venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'.')
from ml_lotto.data.loader import load_draw_history_with_bias_ratios
from ml_lotto.features.walk_forward import PointInTimeFeatureEngine
from ml_lotto.config import DRAW_HISTORY_JSON, ACTIVE_MODELS
draws,_ = load_draw_history_with_bias_ratios(DRAW_HISTORY_JSON)
produced = set(PointInTimeFeatureEngine(draws).extract_features_for_next_draw()[1])
req = {f for m in ACTIVE_MODELS for f in m['features'] if not f.isupper()}
print('missing:', sorted(req - produced))
"
```

## Per-model feature counts

| Model | Algorithm | Named features |
|:--|:--|--:|
| Momentum Specialist | logistic_regression | 15 |
| Jackpot Optimizer | random_forest | 11 |
| Complexity Explorer | xgboost | 23 |
| Conservative Pool Generator | catboost | 5 |
| Bonus Ball Predictor | logistic_regression | 22 |
| Bonus-to-Main Transition | logistic_regression | 24 |

Counts include the uppercase group markers, each of which expands to a family.

## Group markers

An entry in a config's `features` list written in UPPERCASE is a placeholder, not a feature.
`ml_lotto/features/extractor.py` (~line 458) maps each to a list, and the trainers expand it:

| Marker | Expands to |
|:--|:--|
| `PAIRWISE_INTERACTIONS` | the top pairwise interaction features |
| `TRIPLE_INTERACTIONS` | the top triple interaction features |
| `ADVANCED_PATTERN_FEATURES` | volatility and trend features |
| `FRESHNESS_PATTERN_WEIGHTS` | freshness interaction features |

So a config listing 5 entries may train on considerably more columns. Check the logged final feature
count, not the config length.

## Families

**Core** - `total_count` (all 7 balls), `days_since_last`, `category` (hot/medium/cold by recency).
Computed in `features/base.py`.

**Recent activity windows** - `recent_4`, `recent_5`, `recent_9`, `recent_24`, counted over the
**main 6 balls**. The names are off by one by design: `recent_4` counts over 5 draws, `recent_9` over
10, `recent_24` over 25. `recent_14` (15 draws) exists only in the walk-forward engine, so only the
bonus model - trained and served from that engine - can use it; the main models' serving path has no
such window (verified 2026-09-18, F-15).

**Rolling statistics** - `rolling_rate_10/20/50`, `rolling_trend_10/20/50`, counted over **all 7
balls**. `features/rolling_stats.py`.

**Gap statistics** - `gap_consistency_score`, `gap_cv`, `gap_variance`, `max_gap_ratio`. All 7 balls.

**Timing** - `days_since_bonus`, `draws_since_bonus`, `recency_zone_score`, `timing_decay_weight`,
`timing_zone_weight`. `features/timing.py`. Recency zones come from
`data/lotto_recency_zones_calculated.json`, not hard-coded.

**Freshness** - `freshness_bin`, `freshness_weight`, `freshness_multiplier`,
`freshness_weight_score`. Counted over the **main 6**. `features/freshness.py`.

**Patterns** - `has_consecutive_partner`, `appearance_volatility`, `appearance_acceleration`.

**Deleted (F-24, 2026-09-19)** - `odd_even_json`, `range_spread_json`, `sum_contribution_json`,
`series_total`, `series_recent`, `window_saturation_penalty`, `lt_category_alignment`,
`lt_recency_weight` (and the unexported `lt_*` weights). Per-number statistics over the whole
timeline, copied unchanged into every training row; no model used any of them after F-21. Their
source JSON files still exist - the website reads them - only the ML feature code is gone.
`tests/test_no_constant_features.py` keeps them out of every config.

**Bonus** - `was_recent_bonus`, `was_bonus_last_10`, `total_bonus_count`, `avg_days_between_bonus`,
`days_since_last_bonus`, `bonus_frequency_ratio`, `is_in_bonus_window`. `features/bonus*.py`.

**Bonus-to-main transition** - `historical_transition_rate`, `avg_draws_to_transition`,
`composite_transition_score`. Used only by the auxiliary transition model.

**Category weighting** - `category_weight`, `category_multiplier`.

## Interaction features

Binary features capturing combinations, e.g. `recent_4_x_recent_9_interaction`,
`freshness_bin_x_bonus_hit_contribution_interaction`, and triples like `triple_hot_0_very_recent`.

Three-part pipeline, and all three must agree:

1. `lotto_analysis/analyzers/feature_interaction_analyzer.py` mines them from history.
2. `lotto_analysis/core/interaction_thresholds.py` holds the split rule and recency bands.
3. `ml_lotto/features/interactions.py` applies them at train and predict time.

**The threshold module is shared deliberately.** When the analyzer and the calculator carried their
own copies and drifted, whole families went silently always-1 (a threshold at the floor of a
distribution makes `value >= threshold` vacuously true) or always-0. Never inline a threshold in
either end.

`split_threshold()` returns `None` for constant input rather than inventing a split, and
`recency_level()` bands days-since-last at 7 / 21 / 60. Both ends import these.

## Rules

- **No hard-coded feature values.** Weights, thresholds and zones come from the JSON artifacts. If
  you find a literal where a JSON lookup should be, that is a defect - log it in `issue.md`.
- **No silent defaults.** `.get(key, 0)` on a feature dict fabricates a constant when the key is
  missing. Let it fail instead.
- **A feature that never varies is a bug.** `tests/test_no_constant_features.py` enforces it.
  Per-number constants computed over full history leak outcome information from the validation
  window; globally constant features carry nothing.
- **Adding a name to a config does nothing** unless both `walk_forward.py` (training) and
  `extractor.py` (serving) produce it. Check both, then run the parity test.
- Adding a feature will not improve the metrics - see `metrics.md`. It will, if you are not careful,
  widen the overfit gap.
