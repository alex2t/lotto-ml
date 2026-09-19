# tests/

**Every file in this folder is a real test.** `pytest` from the project root runs all of them -
`pytest.ini` sets `testpaths = tests`. The feature-discovery scripts that used to sit here with a
`test_` prefix are in `../demos/` since C-17b; do not move one back.

## The fourteen real tests (139 tests, ~30s)

```bash
python -m pytest -q          # all of them, via pytest.ini
python -m pytest tests/test_walk_forward_parity.py tests/test_selection_invariants.py \
                 tests/test_metrics.py tests/test_no_constant_features.py \
                 tests/test_freshness_target.py tests/test_threshold_holdout.py \
                 tests/test_model_capacity.py tests/test_prediction_alignment.py \
                 tests/test_scraper_sources.py tests/test_wheel.py \
                 tests/test_permutation_check.py tests/test_high_number_distribution.py \
                 tests/test_bonus_predictor.py tests/test_draw_history_numbers.py -q
```

This is the same list `.claude/skills/lotto-verify/verify.py` runs. Keep the two in sync.

| File | Guards |
|:--|:--|
| `test_walk_forward_parity.py` | train/serve parity - 0/47 mismatches on `recent_*`, `total_count`, `draws_since_bonus`, and extractor vs engine on `days_since_last`, `category`, `days_since_bonus`; the next-draw date follows the schedule. The most important file here |
| `test_no_constant_features.py` | no model trains on a value that never varies; the C-5 full-history features stay out of all six models (F-21) |
| `test_model_capacity.py` | the constrained model params and tuning grids stay constrained |
| `test_selection_invariants.py` | the ILP line meets every constraint and is the brute-force optimum |
| `test_prediction_alignment.py` | predictions line up with the numbers they claim to be for |
| `test_freshness_target.py` | freshness target is sized for a 6-number line |
| `test_metrics.py` | metric computation |
| `test_threshold_holdout.py` | decision threshold is chosen on held-out data |
| `test_scraper_sources.py` | `scripts/scrape_lotto.py` parsing, against `fixtures/*.html` |
| `test_wheel.py` | the Model 4 wheel covers every 3-subset of the pool's top 8 |
| `test_permutation_check.py` | the F-17 shuffle keeps each draw's hit count and moves only the labels |
| `test_high_number_distribution.py` | the F-19 count of main numbers >= 32 per draw that the dashboard shows |
| `test_draw_history_numbers.py` | the draw history carries each draw's `main_numbers` and `bonus_number`, and Pattern Comparison finds a past draw among its best matches (F-25). Reads `data/*.json` |
| `test_bonus_predictor.py` | bonus picks avoid recent bonus balls and span hot/medium/cold (F-20); a pool too small for the request raises (F-5) |

## Not tests

`../demos/` holds the old feature-discovery scripts. They print what a module produces, mostly on
mock data, and pytest does not collect them. Turning one into a real test means rewriting it to
assert intended behaviour, putting it here, and adding it to `verify.py`'s list.

## Rules

- `test_walk_forward_parity.py` reads `data/*.json`, so it fails after a `lotto_analysis/` change
  until `drawpick.py` is re-run. **That is the test doing its job, not a broken test.**
- A test validates what the code is *supposed* to do, not what it currently happens to do. Never
  write a test around observed output.
- Never weaken, skip or delete a test to make the suite pass. If a test fails the default assumption
  is that the code is wrong. If you genuinely believe the test is wrong, say so explicitly and
  explain why before touching it.
- `fixtures/` holds saved HTML for the scraper tests. No network access in tests.
