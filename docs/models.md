# Models

The six models, how they are trained, and which options are actually switched on.

Configs live in `ml_lotto/config.py`. Training runs from `quickpick.py` via
`ml_lotto/models/trainer.py`. Results go to `model_metrics/` - see `metrics.md`.

## The six

Four main models in `ACTIVE_MODELS`, each producing a 6-number line:

| Config | Name | Algorithm | Hot/Med/Cold | Min numbers >= 32 | Labels |
|:--|:--|:--|:--|--:|:--|
| `MODEL_1_CONFIG` | Momentum Specialist | logistic_regression | 4 / 1 / 1 | 2 | all 7 positions |
| `MODEL_2_CONFIG` | Jackpot Optimizer | random_forest | 3 / 1 / 2 | 2 | main 6 only |
| `MODEL_3_CONFIG` | Complexity Explorer | xgboost | 2 / 2 / 2 | 0 | all 7 positions |
| `MODEL_4_CONFIG` | Conservative Pool Generator | catboost | 10 / 5 / 5 | - | all 7 positions |

Model 2 sets `exclude_bonus=True`, so it labels only the main 6 balls. Its PR-AUC baseline is
therefore ~0.128 rather than ~0.149, and its Top-7 expected value is lower. Do not compare its
absolute numbers against the others without accounting for that.

**Model 4 is the exception to the counts rule.** Models 1-3 sum to 6 because they compose a line
directly. Model 4's 10/5/5 defines a **20-number ranked pool** consumed by
`ml_lotto/prediction/pool_generator.py`. It is not a broken config - do not "fix" it to sum to 6.
`ml_lotto/prediction/wheel.py` turns the pool's top 8 into 4 wheel lines covering every 3-subset
(verified 2026-09-18 against `lottery_picks.txt` and `tests/test_wheel.py`).

Lines are kept apart by one rule: a number used by an earlier line is avoided unless no feasible
line avoids it (a flat cost in `ilp_selection.py`). There is no per-model diversity setting
(verified 2026-09-18, F-16).

Two auxiliary models, both logistic regression:

- `BONUS_MODEL_CONFIG` - Bonus Ball Predictor. Produces 3 diverse bonus candidates.
- `BONUS_TO_MAIN_MODEL_CONFIG` - Bonus-to-Main Transition Predictor. Ranks numbers from the recent
  bonus window by likelihood of appearing as a main number.

## Training setup

| Setting | Value | Where |
|:--|:--|:--|
| Training start draw | 100 | `TRAINING_START_DRAW` |
| Train/validation split | 0.85 - last 15% held out | `ml_lotto/config.py` |
| Validation window | 60 draws | observed in `model_comparison.csv` |
| Random seed | 42, fixed | `RANDOM_SEED_BASE` |
| Hyperparameter tuning | **on**, `quick` mode | `quickpick.py` |
| Tuning CV | TimeSeriesSplit, 3 folds | `TUNING_CV_SPLITS` |
| Tuning metric | `roc_auc` | `TUNING_SCORING` |

Training features come from the walk-forward engine, which conditions each row only on draws before
it. That is what keeps lookahead bias out; see `ml_lotto/features/CLAUDE.md`.

**The 0.85 split applies to model fitting only.** The analysis layer (`lotto_analysis/`) deliberately
has no split - it computes over every draw, which is correct because its artifacts are read at
serving time to build the row for the next draw. The system is therefore not 85/15 end to end, and
should not be "harmonised" to make it so.

## What is NOT enabled

Documented because several older notes describe these as active. They are not.

**SMOTE is off.** `trainer.py` accepts `use_smote` (default `False`) and no model config overrides
it. The class imbalance is handled by threshold selection instead, not by synthetic oversampling.

**There is no ensemble.** Nothing combines the models' outputs; each model writes its own line.
The voting module, its CLI, the seed-rerun script and the `ENSEMBLE_MODE` / `ENSEMBLE_RUNS` flags
were deleted on 2026-09-19 (F-6 in `issue.md`) - none was reachable from `quickpick.py`, and
combining models that each sit at chance yields a model at chance. Verified against the code
2026-09-19.

**Feature selection is per-model**, not global - each config carries its own
`feature_selection` block with correlation and importance thresholds.

## Capacity is deliberately constrained

This is the single most important thing to understand before changing a model.

Validation AUC cannot meaningfully improve on a fair draw. The only way to move it is to let a model
memorise the training set, which shows up as the train/validation gap widening rather than as a
better score. Current gaps are 0.002-0.078; above ~0.1 means capacity was handed back.

Two things hold the line and **both** must stay constrained:

1. The narrow `algorithm_params` in each config (e.g. Model 1's `C: 1.0`, `max_iter: 1000`).
2. The tuning grids in `ml_lotto/models/hyperparameter_tuning.py`.

Widening one alone reintroduces the problem through the back door.
`tests/test_model_capacity.py` enforces this.

## Calibration

Each main model wraps its estimator in a calibration step (`sigmoid`, cv=5) so the output is usable
as a probability. Calibration error is reported per model; all main models are currently under 0.025.
The Bonus-to-Main model is the weakest at 0.073.

## HMC recommendations

`drawpick.py` Phase 16 writes `data/lotto_hmc_recommendations.json` with a recommended hot/medium/cold
composition derived from the current draw environment, plus `learned_parameters`. The principle is
that no HMC ratio is hard-coded - the recommendation comes from the analysis, and the per-model
counts in `config.py` are the values currently in force.

## Changing a model

1. Save a baseline: `cp model_metrics/model_comparison.csv /tmp/baseline.csv`
2. Edit the config. If you add a feature name, confirm both feature paths produce it (`features.md`).
3. `python quickpick.py`
4. `python .claude/skills/lotto-verify/verify.py --baseline /tmp/baseline.csv`
5. Compare against the noise floor in `metrics.md`. Inside it means no effect - report that honestly.
