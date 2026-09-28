# tests/

**Every file in this folder is a real test.** `pytest` from the project root runs all of them -
`pytest.ini` sets `testpaths = tests`. The feature-discovery scripts that used to sit here with a
`test_` prefix are in `../demos/` since C-17b; do not move one back.

## The twenty-four real tests (281 tests, ~2 min)

```bash
python -m pytest -q          # all of them, via pytest.ini
python -m pytest tests/test_walk_forward_parity.py tests/test_selection_invariants.py \
                 tests/test_metrics.py tests/test_no_constant_features.py \
                 tests/test_freshness_target.py tests/test_threshold_holdout.py \
                 tests/test_model_capacity.py tests/test_prediction_alignment.py \
                 tests/test_scraper_sources.py tests/test_wheel.py \
                 tests/test_permutation_check.py tests/test_high_number_distribution.py \
                 tests/test_bonus_predictor.py tests/test_draw_history_numbers.py \
                 tests/test_bonus_transition_baseline.py tests/test_trend_significance.py \
                 tests/test_bonus_window.py tests/test_odd_even_affinity.py \
                 tests/test_pipeline_completeness.py tests/test_docker_stack.py \
                 tests/test_artifact_rounding.py tests/test_number_pairs.py \
                 tests/test_rebuild_webhook.py tests/test_freshness_fair_draw.py -q
```

This is the same list `.claude/skills/lotto-verify/verify.py` runs. Keep the two in sync.

| File | Guards |
|:--|:--|
| `test_walk_forward_parity.py` | train/serve parity - 0/47 mismatches on `recent_*`, `total_count`, `draws_since_bonus`, and extractor vs engine on `days_since_last`, `category`, `days_since_bonus`; the served row equals the training row on every main-model column (F-34), and the Bonus-to-Main predictor scores the rows its trainer builds (F-40); the next-draw date follows the schedule. The most important file here |
| `test_no_constant_features.py` | no model trains on a value that never varies, including a string column that every row turns into 0.0 (F-41); the C-5 full-history features stay out of all six models (F-21) |
| `test_model_capacity.py` | the constrained model params and tuning grids stay constrained |
| `test_selection_invariants.py` | the ILP line meets every constraint and is the brute-force optimum; `validate_line` takes exactly the 6 main numbers and raises otherwise (F-39) |
| `test_prediction_alignment.py` | predictions line up with the numbers they claim to be for |
| `test_freshness_target.py` | freshness target is sized for a 6-number line |
| `test_metrics.py` | metric computation |
| `test_threshold_holdout.py` | decision threshold is chosen on held-out data |
| `test_scraper_sources.py` | `scripts/scrape_lotto.py` parsing, against `fixtures/*.html` |
| `test_wheel.py` | the Model 4 wheel covers every 3-subset of the pool's top 8 |
| `test_permutation_check.py` | the F-17 shuffle keeps each draw's hit count and moves only the labels |
| `test_high_number_distribution.py` | the F-19 count of main numbers >= 32 per draw that the site shows |
| `test_draw_history_numbers.py` | the draw history carries each draw's `main_numbers` and `bonus_number` (F-25); every drawn number sits in exactly one pre-draw category list, and each ball's `category` is that pre-draw one, not today's (F-27); no module in `frontend/` reads `irish500.csv` (F-35), the admin download route excepted. The site's exact-match check for a past draw (F-25) is in `frontend/test/e2e/site.spec.ts`. Reads `data/*.json` |
| `test_bonus_transition_baseline.py` | on simulated fair draws the bonus-to-main analyzer reports its random baseline as 1 - (41/47)^10 and a boost of ~1.0, not 3.5x (F-30); a transition rate divides only by bonus balls with 10 draws after them (F-32) |
| `test_trend_significance.py` | the "significant trend" flag flags about 5% of numbers on simulated fair draws (was 61%), still flags a real change in frequency, and flags nothing without an older window (F-31) |
| `test_bonus_window.py` | bonus statistics use the 10 bonus balls before each draw, not a list ending with the draw's own bonus: on fair draws the repeat rate matches chance (was 1.0), the main-from-recent-bonus boost and recency penalty are ~1.0 (were 0.92 and 4.7) (F-33); `bonus_window_positions()` counts a repeated bonus ball from its most recent appearance, over the last 10 draws only (F-36). Reads `data/*.json` |
| `test_odd_even_affinity.py` | odd/even tests measure against a fair draw: on simulated fair draws about 5% of numbers have p < 0.05 (was 56%) and FDR validates almost none (was 254 of 470); the stated chance of an odd draw matches simulation; a real affinity is still flagged; the overall test expects 24/47 odd (F-38) |
| `test_pipeline_completeness.py` | a phase failure in the data engine stops the run (F-43): the engine requirements list `scikit-learn`, the lazy import raises instead of returning an error stub, the Phase 16 handler re-raises, and `verify_artifacts` rejects an artifact left from an earlier run as well as a missing one; the artifacts are stored with LF endings and the engine dependencies are pinned with `==`, so a host/VPS alternation is not a whole-file diff (F-44); a missing draw CSV exits non-zero rather than printing an error and returning 0 (F-47); and a file written in the same clock tick as the run's start is not called stale over a float rounding (F-61) |
| `test_artifact_rounding.py` | every float in the 22 JSON artifacts carries at most 12 significant digits, so a host run and a container run are byte-identical (F-46); a tiny p-value survives the rounding and ints, bools and strings are untouched. Reads `data/*.json` |
| `test_docker_stack.py` | the Docker stack orders its services and stays out of the repo (F-45): no `echo` redirect in either `.bat`, `nextjs-web` waits for `service_completed_successfully` and mounts the artifacts read-only, both images take the uid as a build arg and the web image runs as it, and `.dockerignore` excludes `data/` and the frontend's `node_modules`/`.next`; the admin hash and session secret reach `nextjs-web` through `env_file` with `format: raw` from `secrets.env`, never `.env` and never `environment:` interpolation (F-58); the root layout reads no artifact, so the image builds without the data mount (F-62); and the chat panel's `OPENROUTER_API_KEY` arrives the same raw way, sits in both example env files, and is never a `NEXT_PUBLIC_` variable (F-68); the rebuild receiver's `REBUILD_SECRET` arrives raw from `secrets.env` and `secrets.env.example` lists it (F-73); on the VPS nothing but the proxy publishes a port (F-75); and behind the VPS's host nginx (`docker-compose.nginx.yml`, F-78) Caddy publishes only `127.0.0.1:8088` and serves `:80`, only that overlay trusts `X-Forwarded-For` so each visitor keeps their own rate-limit bucket, and only the receiver joins n8n's network |
| `test_freshness_fair_draw.py` | the freshness tests in `lotto_freshness_patterns_validated.json` measure against a fair draw, not a third per bin or 1/26 per pattern (F-69): on 40 simulated fair histories the bin, pattern and top-pattern tests each flag about 5% (all three flagged every one), the fair chance per bin is Binomial(5, 6/47) and per pattern matches 20,000 simulated draws, and a history that really repeats recent balls is flagged |
| `test_bonus_predictor.py` | bonus picks avoid recent bonus balls and span hot/medium/cold (F-20); a pool too small for the request raises (F-5), as does an empty bonus window (F-42) |
| `test_rebuild_webhook.py` | the receiver that appends n8n's draw and runs `drawpick.py`: a signed request runs it, an unsigned or wrongly-signed one does not, a signature over different content does not, two at once get 409 rather than interleaving writes, a failing engine answers 500 with the tail of its log, an oversized body is refused before it is read, and it refuses to start without a secret. And the draw itself (F-64): a new draw lands after the header zero-padded and LF, the same draw twice rebuilds once (in any order), a known date with other numbers is a 409 conflict that writes and rebuilds nothing (F-72), a retry with artifacts older than the CSV rebuilds without appending, a malformed draw is rejected and writes nothing, an interrupted write leaves the file intact, and the engine's log is decoded as UTF-8 so its emoji do not turn a successful rebuild into a crash. The engine is stubbed - that the real one works is `test_pipeline_completeness.py` |
| `test_number_pairs.py` | the pair counts the dossier shows are written by the engine, not counted in a page: every number has partners, a pair counts the same from both sides, the totals add up to 15 a draw, the bonus is not part of a pair, ties break on the number (F-12), and the fair-draw expectation is published beside the counts so they are never read as a pairing. Also that `draw_range_6` is written beside `draw_range` and sits lower, because a seventh ball can only widen a span (F-63) |

## The site's own tests are not here

The Next.js site has its own suites in `../frontend/`, which `pytest` does not run:

- `npm --prefix frontend test` - 374 vitest tests over the data layer, the scoring, the chat panel and the wording
  source lint, against the trimmed fixtures in `frontend/test/fixtures/`;
- `npm --prefix frontend run test:e2e` - 102 Playwright tests, desktop and mobile, over the rendered
  pages, including the wording guard on a typical and an unusual line;
- `npm --prefix frontend run test:integration` - the one that appends a row to a copy of the CSV,
  runs `drawpick.py` and asserts the new draw is served without a restart.

What stays here is what guards the site from the Python side: the CSV scan in
`test_draw_history_numbers.py` and the Docker wiring in `test_docker_stack.py`. The Streamlit
dashboard's own tests (`test_site_wording.py`, `test_anomaly_detector.py` and the page checks in
four other files) were removed with it on 2026-09-27; they are on the `streamlit-app` branch.

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
