# demos/

Feature-discovery scripts, written while features were being built (from November 2025). They
exercise a module and print what it produces. **They are not tests** - they lived in `tests/` with a
`test_` prefix until C-17b moved them here, so pytest no longer collects them.

Kept on purpose: they show what each part of the ML layer can compute, which makes them a source of
ideas for new facts to show on the website.

## Running one

From the project root, as a module, so `ml_lotto` is importable:

```bash
python -m demos.demo_interactions
```

All 11 ran clean on 2026-09-19 (1-28 s each). None is run by `drawpick.py`, `quickpick.py`,
`/lotto-verify` or pytest, so one can break silently when an API changes - fix it when you next run
it, as `demo_interactions.py` was fixed in C-17b (`feature_medians` -> `feature_thresholds`).

| File | Shows |
|:--|:--|
| `demo_better_metrics.py` | the metrics module on a demo model: Top-K, PR-AUC, calibration |
| `demo_hyperparameter_tuning.py` | the tuning grids and TimeSeriesSplit search, on mock data |
| `demo_integrated_training.py` | `train_model()` with feature selection and tuning switched on |
| `demo_interactions.py` | the mined pairwise and triple interaction features |
| `demo_model_specific_features.py` | which feature groups each model config uses |
| `demo_rolling_integration.py`, `demo_rolling_stats_integration.py` | the rolling-rate and trend features |
| `demo_smote_threshold.py` | SMOTE and threshold selection - SMOTE is off in production |
| `demo_train_with_all_features.py` | the `scripts/train_with_all_features.py` pipeline, on mock data |
| `demo_unified_bonus_features.py` | the Bonus Ball model's merged feature set |
| `demo_unified_bonus_to_main_features.py` | the Bonus-to-Main feature set; asserts `window_saturation_penalty` stays out (F-21) |

## Rules

- **Never write into `model_metrics/` or `data/`.** Those are the real scoreboard and the website's
  data. Use a temporary directory, as `demo_hyperparameter_tuning.py` and
  `demo_train_with_all_features.py` do. The latter used to overwrite `model_metrics/model_comparison.csv`
  with mock models (C-17b).
- **Do not give a file here a `test_` prefix, or move it back into `tests/`.** A real test asserts
  what the code is supposed to do; these print what it happens to do, mostly on mock data.
- **A demo is not where a website statistic comes from.** If one shows something worth displaying,
  compute it in `lotto_analysis/`, write it from `drawpick.py` into `data/*.json`, and have the page
  read that - see the root `CLAUDE.md`.
- Settings a demo turns on (SMOTE, wide tuning, all features) are not production settings. Do not
  copy them into `ml_lotto/config.py` without measuring; several hand capacity back to the models.
