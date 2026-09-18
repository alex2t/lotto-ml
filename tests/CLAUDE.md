# tests/

**Only ten files in this folder are real tests. Do not run `pytest tests/` bare** - the other
thirteen are legacy print-scripts that run model training at import and will take minutes, hang, or
fail on missing artifacts.

## The ten real tests (100 tests, ~30s)

```bash
python -m pytest tests/test_walk_forward_parity.py tests/test_selection_invariants.py \
                 tests/test_metrics.py tests/test_no_constant_features.py \
                 tests/test_freshness_target.py tests/test_threshold_holdout.py \
                 tests/test_model_capacity.py tests/test_prediction_alignment.py \
                 tests/test_scraper_sources.py tests/test_wheel.py -q
```

This is the same list `.claude/skills/lotto-verify/verify.py` runs. Keep the two in sync.

| File | Guards |
|:--|:--|
| `test_walk_forward_parity.py` | train/serve parity - 0/47 mismatches on `recent_*`, `total_count`, `draws_since_bonus`. The most important file here |
| `test_no_constant_features.py` | no model trains on a value that never varies |
| `test_model_capacity.py` | the constrained model params and tuning grids stay constrained |
| `test_selection_invariants.py` | the ILP line meets every constraint and is the brute-force optimum |
| `test_prediction_alignment.py` | predictions line up with the numbers they claim to be for |
| `test_freshness_target.py` | freshness target is sized for a 6-number line |
| `test_metrics.py` | metric computation |
| `test_threshold_holdout.py` | decision threshold is chosen on held-out data |
| `test_scraper_sources.py` | `scripts/scrape_lotto.py` parsing, against `fixtures/*.html` |
| `test_wheel.py` | the Model 4 wheel covers every 3-subset of the pool's top 8 |

## The legacy print-scripts

`test_better_metrics.py`, `test_ensemble.py`, `test_ensemble_predict.py`, `test_hyperparameter_tuning.py`,
`test_integrated_training.py`, `test_interactions.py`, `test_model_specific_features.py`,
`test_rolling_integration.py`, `test_rolling_stats_integration.py`, `test_smote_threshold.py`,
`test_train_with_all_features.py`, `test_unified_bonus_features.py`, `test_unified_bonus_to_main_features.py`.

They are demonstration scripts with a `test_` prefix, mostly `print` and no assertions. Leave them
alone unless you are converting one into a real test - in which case add it to the ten-file list
above **and** to `verify.py`.

## Rules

- `test_walk_forward_parity.py` reads `data/*.json`, so it fails after a `lotto_analysis/` change
  until `drawpick.py` is re-run. **That is the test doing its job, not a broken test.**
- A test validates what the code is *supposed* to do, not what it currently happens to do. Never
  write a test around observed output.
- Never weaken, skip or delete a test to make the suite pass. If a test fails the default assumption
  is that the code is wrong. If you genuinely believe the test is wrong, say so explicitly and
  explain why before touching it.
- `fixtures/` holds saved HTML for the scraper tests. No network access in tests.
