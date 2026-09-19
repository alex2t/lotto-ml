# ml_lotto/models/

Training and evaluation. Called by `quickpick.py` after `drawpick.py` has written `data/`.

| File | Role |
|:--|:--|
| `trainer.py` | `train_model()` - the single training entry point for the four main models |
| `pipelines.py` | scaling + calibration pipeline construction |
| `hyperparameter_tuning.py` | TimeSeriesSplit CV grids; `quick` (6-24 combos) or `extensive` |
| `model_metrics.py` | AUC, PR-AUC, Top-K, calibration; writes `model_metrics/` |
| `bonus_trainer.py` | auxiliary bonus-ball model |
| `bonus_to_main_trainer.py` | auxiliary bonus-to-main transition model |
| `permutation_check.py` | F-17 label-permutation check: `python quickpick.py --permutation-check N` |

## The six models

Four main configs live in `../config.py` (`MODEL_1..4_CONFIG`), each with its own algorithm, feature
list and hot/medium/cold counts summing to 6:

| Config | Name | Algorithm | Labels |
|:--|:--|:--|:--|
| `MODEL_1_CONFIG` | Momentum Specialist | logistic_regression | all 7 positions |
| `MODEL_2_CONFIG` | Jackpot Optimizer | random_forest | main 6 only (`exclude_bonus=True`) |
| `MODEL_3_CONFIG` | Complexity Explorer | xgboost | all 7 positions |
| `MODEL_4_CONFIG` | Conservative Pool Generator | catboost | all 7 positions |

Plus `BONUS_MODEL_CONFIG` and `BONUS_TO_MAIN_MODEL_CONFIG`, both logistic regression.
`ACTIVE_MODELS` is what `quickpick.py` iterates.

## Measure before changing anything

All six models sit at chance - validation AUC close to 0.50 over the same 60 draws - and chance is
the correct answer for a fair draw. The scoreboard is `model_metrics/model_comparison.csv`; a dated
example is in `docs/metrics.md`, the only file that quotes figures.

**Noise floor (2 SE): ~0.031 AUC, ~0.227 Top-7 AvgCaught.** A move smaller than that is not a
result. Do not report it as an improvement and do not tune against it.

**The permutation check says there is no edge** (F-17, 2026-09-18). Retrained 20 times on shuffled
labels, every model's real validation AUC fell inside the noise range (p 0.095-0.476). A claimed gain
is not real until `python quickpick.py --permutation-check 20` says so - see `docs/metrics.md`.

**Watch the overfit gap.** A train/validation AUC gap above
~0.1 means a model was handed capacity to memorise with, not that it learned something. The
constrained `algorithm_params` in `../config.py` and the grids in `hyperparameter_tuning.py` are
deliberately narrow and must both stay that way - widening one alone reintroduces the gap through
the back door. `../../tests/test_model_capacity.py` covers this.

## Rules

- **The C-5 full-history features stay out of all six models**, auxiliaries included:
  `*_json` statistics, `series_*`, `lt_*`, `window_saturation_penalty`. Each was a per-number value
  over the whole timeline, copied unchanged into every training row. Bonus-to-Main kept
  `window_saturation_penalty` until F-21; F-24 then deleted all of them from `ml_lotto/`. Their
  source JSON stays - the website reads it. `../../tests/test_no_constant_features.py` guards all six
  configs, so none comes back.
- Playable-ticket constraints (sum, span, odd count) belong in `../prediction/filters.py`, never in a
  feature list or a model.
- A feature named in a config must be produced by both `../features/walk_forward.py` and
  `../features/extractor.py`. A name the serving features lack raises in `expand_feature_selection`
  (F-15) - fix the config, do not catch the error.
- `model_metrics/` is regenerated output. Read it, do not hand-edit it.

## After changing anything here

`python quickpick.py`, then `/lotto-verify`. Save `model_metrics/model_comparison.csv` as a baseline
first if you intend to claim a metric moved.
