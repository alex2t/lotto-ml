# Open Issues — Irish Lotto ML System

**Maintained by:** Claude Opus 5
**Last updated:** 2026-09-17
**Scope:** the single record of outstanding defects.

Sections 1-8 are **open**, ordered by severity. Items carried from the retired code review keep
their original IDs (C-nn / N-n); items found later are numbered F-n, and an ID is never reused.
Appendix A is the resolved list. Appendix B keeps the full C-5 write-up for reference.

**Keeping this file true.** The Priority summary lists **open items only** — a resolved ID never
appears in it. When a defect is found: give it the next free F-n, add a row to the Priority summary,
and write a section with file:line evidence. When one is fixed: delete its summary row, renumber the
remaining sections, add it to the Appendix A table, and write up the root cause and the measured
effect. A fix is not finished until this file says so.

---

## Priority summary

| # | ID | Issue | Severity | Effort |
|--:|:--|:--|:--|:--|
| 1 | **F-8** | Freshness target barely constrains selection; bin 0 absorbs every slot | Medium | M |
| 2 | **F-5** | `assign_bonus_to_models` divides by zero on an empty list | Low (latent) | XS |
| 3 | **C-15a** | Feature engine rebuilt 3-4x per run; O(N^2) gap memory | Low | S |
| 4 | **F-6** | Ensemble machinery is unreachable from the pipeline | Low | M |
| 5 | **C-6b** | Serving reference date differs between the two feature paths | Low | S |
| 6 | **C-17b** | Legacy `tests/*.py` are print scripts, not tests | Low | M |
| 7 | **F-7** | `analysis/` scripts read a window that has never existed | Low | S |

**7 open, nothing High.** Everything resolved is in Appendix A and appears nowhere above.

---

## 1. F-8 — The freshness target barely constrains selection

**Severity: Medium.** Found while verifying the F-1 fix.

The target is now correct, but selection largely ignores it. `pick_from_hmc_pool`
(`ml_lotto/prediction/selection.py`) computes the bin priority **once per HMC category**:

```python
freshness_priority = sorted(
    freshness_needed.keys(),
    key=lambda f: freshness_needed[f] - freshness_counts[f],
    reverse=True,
)
```

then drains the highest-priority bin until `count_needed` is met. Bin 0 holds 24 of the 47
candidates right now (`{0: 24, 1: 16, 2: 7}`), so it never runs out and the loop never reaches
bin 1. The target is consulted for ordering and then effectively discarded.

The gap between target and outcome in the current run:

```
target            C0=3, C1=2, C_GE_2=1
Line 1 achieved   C0=6, C1=0, C_GE_2=0
Line 2 achieved   C0=6, C1=0, C_GE_2=0
Line 3 achieved   C0=4, C1=2, C_GE_2=0
```

Two of three lines are entirely bin 0. Whatever the freshness pattern is worth, the system is not
currently getting it.

**Fix.** Recompute the priority after each pick, or cap per-bin intake at the target count and only
overflow once a bin's quota is met. Either turns `freshness_needed` into a real constraint rather
than a one-time sort key. Worth measuring before and after with the noise floor — if enforcing the
target does not move Top-K lift, the honest conclusion is that the freshness pattern carries no
signal and the whole mechanism should be dropped rather than fixed.

---
## 2. F-5 — `assign_bonus_to_models` divides by zero on an empty list

**Severity: Low, latent.**

`ml_lotto/prediction/bonus_predictor.py:150`:

```python
bonus_idx = (model_idx - 1) % len(bonus_predictions)
```

`ZeroDivisionError` when `bonus_predictions` is empty. `generate_bonus_predictions` builds
`available_pool` by excluding every number with `was_bonus_last_10 == 1`; it returns fewer than
`num_predictions` entries when the pool is thin, and could in principle return none.

**Fix.** Return an empty assignment dict when there are no predictions and let Step 10's existing
`None` handling take over.

---
## 3. C-15a — The feature engine is rebuilt several times per run

**Severity: Low** (performance and memory only). Carried from the code review.

`PointInTimeFeatureEngine` is constructed in `train_all_models`, again inside
`build_walk_forward_dataset` when the legacy `build_training_dataset` wrapper is used, again in
`build_walk_forward_bonus_dataset`, and again in `quickpick.py` for the bonus serving row. Each
construction re-runs `_precompute_matrices` and `_precompute_timeline_state`.

`_precompute_timeline_state` also stores a full copy of every number's gap list at every draw:

```python
'gaps': {num: list(appearance_gaps[num]) for num in range(1, MAX_NUMBER + 1)}
```

That is O(N² × 47) memory for quantities that could be maintained as running moments (count, sum,
sum of squares, max) in O(N × 47).

**Fix.** Build the engine once in `quickpick.py` and pass it down; replace the gap-list snapshots
with running moments.

---
## 4. F-6 — The ensemble machinery cannot be reached from the pipeline

**Severity: Low.**

`ml_lotto/prediction/ensemble.py` (341 lines) is imported only by `scripts/ensemble_predict.py`,
`scripts/train_with_all_features.py` and three test scripts. `quickpick.py` never imports it, so no
ensembling happens in the path that produces `lottery_picks.txt`.

`review.md` §3.2 proposes soft voting as an improvement, apparently unaware that hard voting already
exists but is unreachable. `ENSEMBLE_MODE = False` in `ml_lotto/config.py` is commented "not used
currently", confirming it.

**Fix.** Decide whether ensembling is wanted: wire it into `quickpick.py`, or delete the module and
the config flag rather than leaving 341 lines that look load-bearing. With all four models at
chance, ensembling them will not help — resolve the modelling question first.

---
## 5. C-6b — The two feature paths use different serving reference dates

**Severity: Low.** Carried from the code review.

- `walk_forward.py` anchors the serving row (`t = N`) to an **estimated next-draw date** (last draw
  + median inter-draw gap, currently 3 days), matching how every training row uses its own draw's
  date.
- `extractor.py:90-97` anchors the main path to the **latest draw's date**.

Both are internally consistent and reproducible (C-6 fixed the wall-clock dependency), but they sit
about 3 days apart. `days_since_last` is Model 1's top feature and the HMC bands are 13 / 27 days,
so a 3-day offset can move numbers across a category boundary.

**Fix.** Use one anchor. The engine's convention is more defensible — features for the draw being
predicted should be measured as of that draw — so move `extractor.py` onto the estimated next-draw
date, or retire the JSON serving path in favour of `engine.extract_features_for_next_draw()`.

---
## 6. C-17b — The legacy test files are not tests

**Severity: Low.** Carried from the code review.

Seven of the thirteen pre-existing files in `tests/` contain zero `assert` statements — they are
print scripts that pass by not raising. Their work also happens at module import, so collecting them
under pytest executes data loading and model training:

```
test_better_metrics.py  test_ensemble.py  test_interactions.py
test_model_specific_features.py  test_rolling_integration.py
test_rolling_stats_integration.py  test_smote_threshold.py
```

The four files added during this review (`test_walk_forward_parity.py`,
`test_selection_invariants.py`, `test_metrics.py`, `test_no_constant_features.py` — 37 tests) are
real and run in about 5 seconds. A plain `pytest tests/` still cannot be used because of the others.

**Fix.** Convert the useful ones to assertions inside functions, delete the rest, and add a
`pytest.ini` so `pytest` runs clean from the repo root.

---
## 7. F-7 — Standalone analysis scripts read a window that has never existed

**Severity: Low.** Carried from the code review, confirmed in the final pass.

`analysis/bonus_to_main_analysis.py:109,121` and `analysis/feature_stability_scorer.py:82` read:

```python
'recent_14': recent_counts.get('last_14', 0)
```

`SCENARIOS` produces windows 5/6/10/25, i.e. `last_4`, `last_5`, `last_9`, `last_24`. There is no
`last_14`, so these silently read 0 for every number — the same defect that produced the dead
interaction features that were fixed earlier (see Appendix A).

None of these scripts feed `drawpick.py` or `quickpick.py`, so the prediction path is unaffected.

**Fix.** Point them at `last_24` or remove the field. Better, have them fail on a missing key rather
than defaulting to 0, which is what let this hide.

---
## 8. Improvements (not defects)

Carried from the code review's improvement list, kept here so the register is complete.

1. **Label-permutation check.** Shuffle `hit` within each draw, retrain, compare the AUC
   distribution to the real 0.49–0.53. Settles whether any edge exists for this feature family, in
   ~30 lines. Do this before further modelling work.
2. **Wheel the Model 4 pool.** A covering design over the 20-number pool *guarantees* a match-3 if
   enough winners land in the pool. The guarantee is combinatorial and does not depend on beating
   randomness — the only item here with a provable payoff.
3. **Bias toward unpopular combinations.** Expected *payout* is not uniform even when probability
   is: birthday numbers (≤31), calendar patterns and arithmetic sequences are heavily played and
   share jackpots more often. Steering toward numbers ≥32 raises expected value without predicting
   anything. Note the current sum ∈ [84,206] and 3-odd/3-even filters push the *opposite* way,
   toward the most commonly played combinations — keep them for the match-3/4 tiers, not for
   jackpot EV.
4. **MILP selection** (`review.md` §3.5) to replace greedy picking. Worth doing only once the
   probabilities mean something.

---

## Reality check

All six models are now measured out-of-sample on the same 60-draw hold-out, and all six sit at
**validation AUC 0.498-0.545 with Top-7 lift 1.01-1.12**. The 2 SE noise floor is 0.031 AUC and
0.227 Top-7 AvgCaught, so every one of them is at chance. That is the correct answer for a fair
draw, and it is the real result of the review and fix work.

Train/validation AUC gaps are now 0.005-0.053 across all six, down from a 0.383 worst case, so the
training numbers can be trusted as a diagnostic rather than reflecting memorised noise.

Read the scoreboard in this order: AUC, PR-AUC lift and per-draw Top-K lift first, since they are
threshold-free; the precision / recall / F1 columns last, because maximising F1 at a ~15% positive
rate parks the threshold near the base rate by construction.

None of the open items above will move those numbers, and none should be expected to. What is left
is hygiene, latent crashes and one honest question (F-8) about whether the freshness mechanism earns
its place at all.

---

## Appendix A — Resolved

Every item below was fixed and verified against the live pipeline.

| ID | Issue | Fixed in |
|:--|:--|:--|
| C-1 | SMOTE destroyed calibration (2 distinct probabilities across 47 numbers) | `config.py`, `trainer.py` |
| C-2 | Tie-breaks decided picks, in opposite directions in two modules | `constraints.py`, `pool_generator.py`, `selection.py`, `bonus_predictor.py` |
| C-3 | Walk-forward windows disagreed with the serving JSON | `walk_forward.py`, `drawpick.py` |
| C-4 | Eight serving features frozen at draw #100 | `rolling_stats.py`, `quickpick.py` |
| C-5 | Full-history constant features in the training matrix | `config.py`, `trainer.py` (Appendix B) |
| C-6 | `days_since_last` moved with wall-clock time | `extractor.py` |
| C-7 | Sum and range filters advertised but not implemented | `filters.py` |
| C-8 | Bonus ball could duplicate a main number | `quickpick.py` |
| C-9 | Soft diversity penalty disabled while the hard lockout stayed | `config.py`, `selection.py` |
| C-10 | No validation set for the main models | `config.py` |
| C-11 | `pick_from_hmc_pool` returned 1 number for a request of 0 | `selection.py` |
| C-12 | Safety top-up could duplicate a pre-assigned number | `selection.py` |
| C-13 | Streamlit autofill inert; CSV assumed newest-first | `post_draw_analysis.py` |
| C-14 | Scraper had no fallback source and accepted any game sharing the draw date | `scrape_lotto.py` |
| C-15b | Tree models memorised the training set (train/val AUC gap 0.383) | `config.py`, `hyperparameter_tuning.py` |
| C-16 | Non-deterministic feature column order | `extractor.py` |
| F-1 | Freshness target sized for 7 balls while a line has 6 slots | `freshness_analyzer_7_numbers.py`, `constraints.py`, `drawpick.py` |
| F-2 | Bonus and bonus-to-main models had no validation split | `quickpick.py`, `bonus_trainer.py`, `bonus_to_main_trainer.py`, `trainer.py` |
| F-3 | Decision threshold tuned and scored on the same validation rows | `model_metrics.py` |
| F-4 | Probability array built conditionally while every consumer indexed it positionally | `predictor.py` |
| F-10 | Dead look-ahead guard printed a false reassurance; contradictory split constant | `hmc_analyzer.py`, `lotto_analysis/config/config.py` |
| F-9 | Serving features fell back to 0 for a column the model was trained on | `predictor.py`, `bonus_predictor.py` |
| F-11 | HMC categorization measured days against wall-clock today | `hmc_categorization_analyzer.py` |
| F-12 | `max(set(...), key=list.count)` tie-break was non-deterministic | `bonus_to_main_analyzer.py`, `generate_bonus_to_main_json.py` |
| N-1 | Serving row was stale by one draw | `walk_forward.py`, `quickpick.py` |
| N-1b | `draws_since_bonus` was exactly inverted | `walk_forward.py` |

### F-9 — Serving features fell back to 0 for a column the model was trained on

**Root cause.** `[feat.get(col, 0) for col in features_for_model]`, where `features_for_model` is the
exact column list the pipeline was fitted on. A column absent from the serving dict - a renamed
feature, an analyzer that stopped emitting a key, a `drawpick.py` run that did not happen - would be
served as a constant 0 to every number, and the model would apply a coefficient fitted on real values
to a column that no longer exists. Nothing prints; train/serve parity breaks silently. Same
`.get(key, 0)` pattern that produced the phantom `total_count` and `recent_14` columns.

**A second site was found during the fix.** F-9 recorded only
`ml_lotto/prediction/predictor.py:60`, because it was written from the F-4 investigation, which
touched that line. `ml_lotto/prediction/bonus_predictor.py:51` carried the identical pattern and had
never been examined. Both are fixed; fixing only the recorded one would have been the "changed one
side only" failure the parity contract exists to prevent.

**Fix.** `feat[col]` at both sites, so a missing column raises where it happens. Each carries a
comment saying why `.get(col, 0)` is wrong there, since the bare indexing otherwise looks like an
oversight waiting to be "hardened".

**Measured before/after.** Verified no column is missing before making it raise: 0 missing across all
five models with named feature lists (13, 9, 21, 5 and 20 columns) x 47 numbers. After the change
`quickpick.py` exits 0 with no `KeyError`, picks are unchanged
(`[2, 4, 5, 27, 42, 43]`+45, `[6, 23, 37, 39, 41, 46]`, `[9, 10, 32, 38, 40, 47]`+19) and all six
model AUCs are unchanged (0.5074 / 0.5011 / 0.5118 / 0.5257 / 0.4979 / 0.5454).

**Tests.** No new test. The change converts a silent wrong answer into a loud failure; asserting it
would mean constructing a serving dict with a column removed, which tests Python's `KeyError` rather
than this system. The existing 79 pass, and `test_walk_forward_parity.py` remains the real guard -
it checks the columns actually agree.

### F-11 — HMC categorization measured days against wall-clock today

**Root cause.** `hmc_categorization_analyzer.calculate_days_since_date()` used `datetime.now()` as
the reference, while the rest of the layer references the most recent draw
(`frequency_analyzer.calculate_days_since_last_hit`). Three call sites were affected
(`calculate_category_anova`, `calculate_pairwise_comparisons`, `calculate_threshold_validation`).

`data/lotto_hmc_categorization_validated.json` therefore changed **every calendar day** with no new
draw and no code change. Observed: the copy committed 2026-09-17 (generated on the 16th) had
`hot.min = 2.0`; a re-run on the 17th gave `3.0`, every statistic +1, `std_dev` byte-identical — the
signature of a moving reference rather than changed data.

There was a second effect, not noticed when the defect was logged. `suggested_thresholds` is read
against `HMC_HOT_THRESHOLD = 13` / `HMC_COLD_THRESHOLD = 27`, which are **draw-relative**. The
validated thresholds were on a clock-relative scale, so the two drifted further apart the longer the
gap since the last draw. They are now on the same basis.

**Fix.** Added `latest_last_seen(hmc_data)`, which derives the reference from the most recent
`last_seen` in the data, and made `calculate_days_since_date(date_str, reference)` take it
explicitly. Computed once per function and passed at all three call sites. No `datetime.now()`
remains in the path.

**Measured before/after** (run 2026-09-17, last draw 2026-09-14, so a -3 day shift):

| Category | Before (clock) | After (last draw) |
|:--|:--|:--|
| hot | mean 8.133, min 3, max 15 | mean 5.133, min 0, max 12 |
| medium | mean 21.857, min 19, max 26 | mean 18.857, min 16, max 23 |
| cold | mean 59.400, min 33, max 124 | mean 56.400, min 30, max 121 |

`std_dev` byte-identical (`4.150058855696763`) and `p_value` identical (`1.2947678031855394e-13`),
confirming a pure constant shift with the ANOVA verdict unchanged. `hot.min` is now 0, the correct
answer for a number drawn in the most recent draw. `suggested_thresholds` 8.0/19.0 -> 5.0/16.0.
Picks and all six model metrics unchanged.

**Tests.** No new test. The defect only reproduces across a calendar day boundary, so a meaningful
regression test would have to inject a reference date; the fix removes the clock from the path
entirely, which `grep -n "datetime.now()"` over the module now confirms. Covered by the existing 79.

---

### F-12 — A tie-break over a set made an artifact non-deterministic

**Root cause.** `max(set(values), key=values.count)` at four sites -
`bonus_to_main_analyzer.py:128,136` and `generate_bonus_to_main_json.py:122,128`. `max()` returns the
first maximal element in iteration order, and set iteration order varies between processes under
hash randomisation (`sys.flags.hash_randomization` is 1). On a tie the winner changed run to run, so
`data/lotto_bonus_to_main_patterns.json` differed between identical runs, dirtying the working tree
and masking real diffs. It already cost time during the F-10 verification, where a genuine
comparison had to be separated from this noise.

**Fix.** `sorted()` around the set at all four sites, so ties resolve to the first candidate in
sorted order. Each site carries a comment stating the call is load-bearing - this class has now
recurred three times (C-2, N-4, F-12) and an uncommented `sorted()` reads as removable noise.

**Measured before/after.** Three `drawpick.py` runs under `PYTHONHASHSEED` 1, 2 and 12345 now produce
a byte-identical artifact (`bbc69db8bd522d90b9da4b689c5a0ffc`); before the fix the same file varied
between runs at a fixed seed.

Three values changed and are now pinned. All five numbers that had ever varied were verified to be
genuine ties, so no majority is overruled:

| Number | Counts | Tied | Now |
|--:|:--|:--|:--|
| 2 | hot 4, cold 4, medium 4 | three-way | cold |
| 6 | cold 3, medium 3, hot 2 | cold/medium | cold |
| 21 | cold 2, medium 2, hot 1 | cold/medium | cold |
| 1 | hot 7, medium 7, cold 2 | hot/medium | hot |
| 40 | medium 4, hot 4, cold 3 | hot/medium | hot |

Picks and all six model metrics unchanged.

**Tests.** No new test. Reproducing it requires a subprocess with a forced `PYTHONHASHSEED`, since
hash randomisation is fixed within a process - a same-process test cannot fail. Verified empirically
across three seeds. A permanent guard would be worth adding if this class recurs a fourth time.

### F-10 — The HMC look-ahead guard was dead code printing a false reassurance

**Root cause.** `hmc_analyzer.py` sliced `all_draws[:train_end_index]` to exclude the validation
window from the final HMC category assignment. With `VALIDATION_SPLIT_RATIO = 1.0` in
`lotto_analysis/config/config.py`, `train_end_index` equalled `len(all_draws)`, so the slice excluded
nothing. The guard ran and did nothing while printing `Calculating final categories WITHOUT
look-ahead bias` and `Validation draws excluded: 0`.

The guard was the leftover, not the ratio. `final_categories` is consumed by **serving** only - it
reaches `lotto_trigger_periods.json` via `num_to_category` (`drawpick.py:231`) and
`ml_lotto/features/extractor.py` reads it to build the row for the next draw, where conditioning on
all history is correct. Training never reads it: `walk_forward.py:225-227` derives `category` itself,
point-in-time. The mechanism survived from a design that assumed these categories fed model fitting.

Three numbers also described one concept: the comment said 80/20, the constant was 100/0, and
`ml_lotto/config.py:57` is 85/15. The comment claimed `(matches ml_lotto/config.py)`, which was
false, and acting on it - setting this side to 0.85 - would have changed HMC categorisation for the
last 15% of draws, changed `lotto_trigger_periods.json`, and broken train/serve parity while training
stayed put.

**Fix.** Removed the dead slice and the misleading log lines; `calculate_days_since_last_hit` is now
called on `all_draws` with a comment stating why that is correct and that training does not consume
the value. Removed the now-unused `VALIDATION_SPLIT_RATIO` import from `hmc_analyzer.py` and the
dead constant from `lotto_analysis/config/config.py`, replacing it with a note pointing at
`ml_lotto/config.py` as the only split that exists. **Neither ratio was changed.**

**Measured before/after.** Behaviour-preserving by construction, and verified:

- Category distribution unchanged: Hot=30, Medium=7, Cold=10.
- `data/lotto_trigger_periods.json` byte-identical.
- Isolation test: `drawpick.py` run with the fix applied and with it reverted produced the identical
  hash for every artifact (`c4e8a85...` for `lotto_hmc_categorization_validated.json`). The drift
  against the committed copy predates this change - the committed `data/` was already stale.
- `lottery_picks.txt` Line 1 unchanged: `[2, 4, 5, 27, 42, 43]` + bonus 45.
- All six models unchanged to 4 dp: AUC 0.5074 / 0.5011 / 0.5118 / 0.5257 / 0.4979 / 0.5454, overfit
  gaps 0.0190 / 0.0197 / 0.0511 / 0.0534 / 0.0331 / 0.0051.

**Tests.** No new test - there is no behaviour to assert, the change removes code. Covered by the
existing 79: `test_walk_forward_parity.py` (parity across the artifacts this touches),
`test_no_constant_features.py`, `test_model_capacity.py`. All 79 pass after the change.

**Note for the future.** The system is deliberately **not** 85/15 end to end. ML training holds out
15% (`ml_lotto/config.py`). The analysis layer computes over all draws, which is correct for
serving-time artifacts. Do not "harmonise" them.
| N-3 | Top-K computed globally instead of per draw; overfit gap zero by construction | `model_metrics.py` |
| N-4 | Bonus-pool tie-break non-deterministic | `bonus_predictor.py` |
| N-5 | Two models could be assigned the same bonus ball | `quickpick.py` |
| — | `total_count` train/serve window mismatch | `drawpick.py` |
| — | Pipeline crashed at shutdown on the Tk matplotlib backend | `model_metrics.py`, `trend_analyzer.py` |
| — | Interaction thresholds: phantom features, vacuous splits, empty cells, mismatched recency | `feature_interaction_analyzer.py`, `interaction_thresholds.py` |
| — | Duplicate interaction script overwriting pipeline output | `feature_interaction_explorer.py` |
| — | main-6 / all-7 split corrupting the freshness selection target | `drawpick.py`, `walk_forward.py` |

The six fixed on 2026-09-16/17 — **F-1**, **F-2**, **F-3**, **F-4**, **C-14**, **C-15b** — are written up
below in full, because each one's root cause is the kind that comes back. The original reports are
in git history.

### F-1 — The freshness target was sized for 7 balls while a line has 6 slots

**Resolved 2026-09-16.** `lotto_7_number_freshness_results.json` now carries a second
distribution, `distribution_analysis_6_main`, built from the 6 main balls only, and
`get_optimal_pattern_distribution` reads that instead of the 7-ball one. The target went from
`{0:4, 1:2, 2:1}` (sums to 7) to `{0:3, 1:2, 2:1}` (sums to 6) — the genuine mode of the main-ball
distribution, 69 of 497 draws. The function now raises if the key is missing or the target is the
wrong width, rather than silently using a 7-wide one, and `predictor.py` no longer claims a
proportional adjustment it never made. Nine tests in `tests/test_freshness_target.py` cover it.

Generated lines did **not** change on current data: both the old and new targets yield the same
initial bin priority `[0, 1, 2]`, so selection picked identically. The fix removes a real defect and
pins the contract; it did not improve the picks. Investigating that turned up **F-8**.

### F-2 — The bonus and bonus-to-main models trained on 100% of the data

**Resolved 2026-09-17.** `quickpick.py` now calls `calculate_train_val_split(len(all_draws))` once
and passes `training_end_draw` / `validation_start_draw` into both `train_bonus_model` and
`train_bonus_to_main_model`. Both build a chronological validation set, score it with
`calculate_comprehensive_metrics`, and return those metrics; `train_all_models` takes them as
`extra_metrics` and merges them into `compare_models`, so all six models now sit in
`model_metrics/model_comparison.csv` on the same 60-draw hold-out.

`calculate_topk_accuracy` gained a `groups` argument for this. The bonus-to-main model scores only
the numbers in the current bonus window, so its rows per draw vary (9-10, not 47) and the old fixed
reshape would have collapsed the whole validation set into one "draw". Passing the per-row draw
index makes Top-K a real within-draw metric for it.

First out-of-sample numbers for the two models, on 60 validation draws:

| Model | Val AUC | PR-AUC Lift | Top-7 Lift |
|:--|--:|--:|--:|
| Bonus Ball Predictor | 0.461 | 0.90 | 0.67 |
| Bonus-to-Main Transition Predictor | 0.434 | 0.93 | 0.94 |

Same verdict as the four main models — chance, slightly below it here — which is the expected
answer for a fair draw. The point was to be able to see it.

Both models now fit 85% of the draws rather than 100%, so the probabilities in `lottery_picks.txt`
changed (bonus top pick 21 -> 10, bonus-to-main #1 27 at 23.0% rather than 33.9%). Main-number
picks are unchanged. The bonus-to-main trainer's duplicated training/validation loop was folded
into one `_build_bonus_to_main_dataset` helper.

### F-3 — The decision threshold was chosen and scored on the same rows

**Resolved 2026-09-17.** `calculate_comprehensive_metrics` now splits the validation window
chronologically on draw boundaries (`split_threshold_tuning_rows`): the earlier 30 draws pick the
F1-maximising threshold, the later 30 carry every threshold-dependent number — accuracy, precision,
recall, F1, both confusion matrices and the classification report. The default-threshold columns
moved to the same held-out half, so the "Default vs Optimal" table compares like with like.
AUC, PR-AUC, Top-K and calibration are threshold-free and still use the whole 60-draw window.

For the bonus-to-main model the split reuses the per-row draw index added for F-2, since its
candidate pool varies by draw; it lands at 281 tuning / 286 reporting rows rather than a clean half.

Effect on the scoreboard — the threshold-free columns are unchanged to the last digit, which is
what confirms only the operating point moved:

| Model | F1 before | F1 after | Recall before | Recall after |
|:--|--:|--:|--:|--:|
| Momentum Specialist | 0.261 | 0.247 | 1.00 | 0.84 |
| Complexity Explorer | 0.261 | 0.254 | 0.90 | 0.86 |
| Conservative Pool Generator | 0.260 | 0.247 | 1.00 | 0.91 |
| Jackpot Optimizer | 0.229 | 0.217 | 0.83 | 0.71 |
| Bonus Ball Predictor | 0.046 | 0.038 | 0.98 | 0.67 |
| Bonus-to-Main Transition Predictor | 0.256 | 0.247 | 1.00 | 0.61 |

Every model's reported F1 fell once the threshold stopped being scored on its own tuning data.
Selection never used these thresholds, so `lottery_picks.txt` is unchanged.

The compounding half of the original report is **not** fixed and was not a defect: maximising F1
at a ~15% positive rate still drives the threshold to roughly the base rate, so recall stays high
and precision stays near the base rate. That is what F1-maximisation does on imbalanced data, and
the columns should still be read after AUC, PR-AUC and Top-K lift, not before them.

`tests/test_threshold_holdout.py` covers it (6 tests): the split is chronological, disjoint and on
draw boundaries, it handles the variable-width bonus-to-main draws, and a model that separates
winners in the tuning half but ranks them last in the reporting half now reports recall 0.0 where
the old code reported 0.50.

### F-4 — The probability array was built conditionally but read positionally

**Resolved 2026-09-17.** `generate_predictions` in `ml_lotto/prediction/predictor.py` now builds one
row per number unconditionally, indexing `features_dict[num]` directly, so the array is
`MAX_NUMBER` long by construction and row *i* is always number *i+1*. A missing number raises a
`KeyError` naming it, at the point where it is missing.

The defect was a disagreement between two halves of the same file: the builder skipped absent
numbers (`if num in features_dict`) while `penalties.py`, `pool_generator.py` and `selection.py` all
read the result as `probabilities[num - 1]`. Demonstrated on a dict missing number 23: the array
comes back 46 long and `probabilities[24 - 1]` returns **number 25's** probability — every number
above the gap shifts down one, silently, with no length check anywhere.

Latent, and confirmed latent before the change: at the point `train_all_models` is called, all 47
numbers are present and no model is missing a single feature column. Re-running the pipeline
produced a `lottery_picks.txt` identical to the previous one apart from its timestamp, which is the
expected result — the fix removes a hazard, it does not change behaviour.

`tests/test_prediction_alignment.py` covers it (3 tests): every number keeps its own probability, a
missing number raises rather than shifting the array, and a `features_dict` built in reverse order
still yields a number-ordered array.

The same four lines still carry `feat.get(col, 0)`, a silent default for a missing *column* rather
than a missing number. That is logged separately as **F-9** rather than folded in here.

### C-14 — The scraper had one source and no main-draw check

**Resolved 2026-09-17.** Both halves of the report are now implemented in
`scripts/scrape_lotto.py`, and the docstring describes what the code does.

**Main-draw verification.** Both result pages carry Lotto Plus 1 and Plus 2 next to the main draw,
sharing its date, and deduplication is by date — so whichever game parsed first won, and nothing
checked which game it was. The two pages need different checks, because they identify the game
differently:

- *Archive table.* The game is in the row's link path (`/irish-lotto/results-...`), and every ball
  carries a class token per game, so a Plus row's balls read `irish-lotto-plus-1`. The parser now
  requires the exact `irish-lotto` token on every ball, and requires the row to hold **exactly one**
  `<ul class="balls">` — with two lists, the link and the balls could refer to different games.
- *lottery.ie.* Verified against the live page: the three games appear in order under repeated
  `Winning numbers` / `Bonus` labels with **no game heading to key on**. The main draw is the first
  pair, and the parser refuses the section if a `Plus` marker appears before it rather than guessing.

**Fallback source.** `parse_lottery_ie` implements the second parser the docstring had advertised
since the beginning. It is used as the data source when the primary yields nothing, and otherwise as
a check on it: dates present in both must carry identical numbers or **nothing is written** and the
run exits non-zero. A date only one source has is not a mismatch — the fallback page holds only the
most recent draws.

Verified against both live sites on 2026-09-17: 76 main draws parsed from the archive, 4 from
lottery.ie, and all 4 shared dates agreed ball for ball.

```
Verified 4 shared date(s) against lottery.ie
Using irish.national-lottery.com. Latest draw: 16 Sep 2026 (Numbers: [4, 7, 19, 20, 35, 42] + Bonus: 31)
Found 1 new draw(s) to add:
  + 16 Sep 2026,04,07,19,20,35,42,31
```

`tests/test_scraper_sources.py` covers it (11 tests) against markup captured verbatim from both
live pages into `tests/fixtures/`. The Plus cases are produced by editing that real markup rather
than inventing a shape the sites do not use: a row retagged `irish-lotto-plus-1` yields no draws, a
row holding two ball lists is dropped while its neighbours survive, the lottery.ie section returns
the Lotto numbers and not Plus 1's, and a reordered section is skipped.

Already fixed earlier: 7-ball uniqueness, date-object deduplication, non-zero exit on failure.

### C-15b — The tree models memorised their training sets

**Resolved 2026-09-17.** Gap 0.383 -> 0.053, validation AUC unchanged within noise.

| | Train AUC | Val AUC | Gap | Top-7 Lift |
|:--|--:|--:|--:|--:|
| before | 0.911 | 0.528 | 0.383 | 1.175 |
| after | 0.579 | 0.526 | **0.053** | 1.119 |

Validation moved -0.003 AUC against a 2 SE noise floor of 0.031, and Top-7 AvgCaught moved well
inside its 0.227 floor. Nothing was gained or lost in predictive terms; the wasted capacity is gone.

**Root cause, and why the obvious fix would have been inert.** `ENABLE_HYPERPARAMETER_TUNING` is
`True` in `quickpick.py:28`, so `MODEL_2_CONFIG['algorithm_params']` is only a starting point —
`get_random_forest_grid(quick=True)` overrode it every run. That grid offered
`max_depth: [5, 10, None]` with no `min_samples_leaf` and no `max_features`, and its CV roc_auc came
out at 0.5103, i.e. chance. A search that cannot tell its candidates apart picks arbitrarily among
them, and it kept landing on `max_depth=10` with `min_samples_leaf=1`. Editing only the config would
have changed nothing that runs.

**Fix.** Both places are constrained: `MODEL_2_CONFIG['algorithm_params']` is now
`max_depth=4, min_samples_leaf=300, max_features=0.5, class_weight='balanced_subsample'`, and both
random-forest grids search only within that envelope (depths 3-6, leaves 100-500, `max_features`
0.3-sqrt). The grid now picks `max_depth=4, min_samples_leaf=500`; 12 fits instead of 24, 38s
instead of 71s.

Measured on the exact Model 2 frames a real run builds (15,839 train / 2,820 val rows). The
selection rule was lowest train/val gap among candidates whose validation AUC did not fall — all
validation differences below are noise:

| Forest | Train AUC | Val AUC | Gap |
|:--|--:|--:|--:|
| depth 10, leaf 1 (the grid winner) | 0.912 | 0.528 | 0.383 |
| depth 6, leaf 50, mf 0.5 | 0.689 | 0.530 | 0.160 |
| depth 6, leaf 100, mf 0.5 | 0.652 | 0.529 | 0.123 |
| depth 5, leaf 200, mf 0.5 | 0.619 | 0.521 | 0.098 |
| depth 4, leaf 300, mf 0.5 | 0.595 | 0.535 | 0.060 |
| depth 4, leaf 500, sqrt | 0.577 | 0.521 | 0.056 |

`lottery_picks.txt` changed: Model 2's line is `[6, 23, 37, 39, 41, 46]` rather than
`[6, 17, 37, 39, 41, 46]` — a different model picks differently. Model 3's line moved 23 -> 17 as a
consequence, which is the cross-model diversity penalty releasing 17 once Model 2 took 23, not a
second change.

`tests/test_model_capacity.py` covers it (4 tests). The behavioural one fits the configured
pipeline on features that carry no information about the label: the constrained forest scores 0.61
on its own training rows, the old one 0.878. The others pin the config and assert no tuning
candidate — quick or extensive — escapes the envelope, since one unconstrained candidate is enough
to bring the memorising model back.

#### The other models — done 2026-09-17, same pass

The report's closing line, "worth reviewing for all four models", is now done. Every model's gap is
at or below 0.054; no validation AUC fell.

| Model | Gap before | Gap after | Val AUC before | Val AUC after |
|:--|--:|--:|--:|--:|
| Jackpot Optimizer (random forest) | 0.383 | 0.053 | 0.528 | 0.526 |
| Complexity Explorer (XGBoost) | 0.165 | **0.019** | 0.507 | 0.507 |
| Bonus-to-Main (logistic) | 0.150 | **0.033** | 0.434 | 0.498 |
| Bonus Ball (logistic) | 0.135 | **0.005** | 0.461 | 0.545 |
| Conservative Pool Generator (CatBoost) | 0.051 | 0.051 | 0.512 | 0.512 |
| Momentum Specialist (logistic) | 0.020 | 0.020 | 0.501 | 0.501 |

**Complexity Explorer.** Same shape of fix as Model 2, in the same two places. Config is now
`max_depth=2, n_estimators=50, learning_rate=0.03, min_child_weight=500, reg_lambda=20`, and both
XGBoost grids search inside that envelope. `scale_pos_weight` is pinned to 1 in the quick grid
because that is the operating point the gap was measured at. The dead `use_label_encoder` parameter
was dropped — XGBoost has ignored it for several releases and warned on every fit.

| Forest of stumps | Train AUC | Val AUC | Gap |
|:--|--:|--:|--:|
| depth 3, min_child_weight 3 (the grid winner) | 0.672 | 0.507 | 0.165 |
| depth 3, mcw 200, lr 0.05, L2 10 | 0.568 | 0.520 | 0.049 |
| depth 2, mcw 300, lr 0.03, L2 20 | 0.545 | 0.515 | 0.030 |
| depth 2, mcw 500, lr 0.03, L2 20, 50 trees | 0.526 | 0.507 | 0.019 |

**The two logistic models needed a different lever, and finding out why mattered.** Sweeping `C`
downward barely moved either gap — 0.135 -> 0.110 for the bonus model across two orders of
magnitude. L2 shrinks coefficients but preserves their ranking, and AUC sees only the ranking, so
L2 cannot reduce a rank-metric gap however hard it is applied. The capacity is in the feature
count: 32 features against 337 positive training rows, and 35 against 462.

The gap is real optimism rather than an unlucky validation window. Refitting the bonus model on the
first 80% of its training window scores 0.614 in-sample, 0.511 on the held-out tail of the *training*
window and 0.503 on the validation window — the drop reproduces on a slice that is not the
validation set.

So both moved to L1, which zeroes features outright: bonus `C=0.05` (5 of 32 features survive),
bonus-to-main `C=0.005` (2 of 35).

**A cost worth knowing about.** The bonus model's probabilities now span 1.9%-2.5%, so all six
entries in `lottery_picks.txt` print as `2.4%`. The ranking behind them is still well defined (241
distinct values across the validation rows) but the displayed figures no longer discriminate. That
is what a model with no signal honestly looks like; if the printed spread matters more than the
gap, `C=0.1` keeps 17 features and a 1.1%-3.5% spread at a gap of 0.096.

**These choices were informed by the same 60 validation draws they are reported on**, so the
validation AUC rises above (bonus +0.084, bonus-to-main +0.064) are not evidence of a better model.
The criterion was the train/val gap, with a guard that validation must not fall; the AUCs remain at
chance, which is the correct answer for a fair draw.

All four main lines and both auxiliary predictions changed in `lottery_picks.txt`, since four of the
six models are different models now.

---

## Appendix B — C-5 full write-up (resolved)

Kept for reference. The analysis below led to the decision to **delete** the seven leaking features
rather than rebuild them point-in-time: removing them moved every validation metric by less than
2 SE while cutting the Jackpot Optimizer's train/val AUC gap from 0.380 to 0.148, so they carried no
signal. Section numbers inside this appendix are the original ones.

### 1. Summary

`PointInTimeFeatureEngine` computes a genuine point-in-time feature row for every historical draw —
that was the whole purpose of `walk_forward.py`. But a subset of features are not computed from the
draw history at all. They are copied out of `base_features_dict`, which holds one value per number
derived from the **entire timeline**, and that same value is written into every training row for
that number.

Two separate mechanisms produce this:

**(A) Explicit static passthrough.** The feature is listed in the `rec` dictionary but its value is
read straight from the static dict. Fourteen features do this, e.g. `walk_forward.py:333`:

```python
'odd_even_json': static_feat.get('odd_even_json', 0.5),
```

**(B) Silent fallback.** The engine never produces the name at all, and the row builder substitutes
the static value without comment — `walk_forward.py:449` (and `:488` for the bonus dataset):

```python
row = {fn: rec.get(fn, static_feat.get(fn, 0)) for fn in all_feature_names}
```

Rev 3 added a warning that prints the (B) names on every run, so the list is at least visible. The
values themselves are unchanged.

---

### 2. Why it matters

These are not innocuous constants. They are **statistics estimated from draw outcomes over the full
dataset, including the validation period**, and then fed back in as inputs.

Take `sum_contribution_json`. Its source, `data/lotto_sum_contribution_validated.json`, stores per
number:

```json
"1": {
  "contribution_score": 0.142923238062531,
  "mean_with": 124.04918032786885,
  "mean_without": 149.0619266055046,
  "appearances": 61,
  "p_value": 1.38896544408424e-09
}
```

`mean_with` is "the average draw sum on draws where number 1 appeared". That is computed from the
outcomes — including the 60 validation draws the model is later scored on. The same is true of
`range_spread_json` (`mean_with` / `mean_without` / `appearances`) and `odd_even_json`
(`affinity_score` conditioned on appearances).

Two distinct consequences:

1. **Target leakage.** A statistic computed from outcomes in the validation window is used as an
   input when predicting that window. Any validation score is therefore optimistic by an unknown
   amount, and cannot be used to compare model variants honestly.
2. **Zero temporal variance.** Because the value never changes across the ~15,800 training rows for
   a given number, the model can only learn a per-number fixed effect from it. It contributes
   nothing to "is this number due *now*", which is the entire question.

A third, separate problem applies to `series_recent` specifically — see §4.

**An honest caveat:** current validation AUC is ≈ 0.50, so this leakage is evidently *not* inflating
results much today. Fixing it is unlikely to change the headline numbers. The reason to fix it is
that until it is fixed, you cannot tell whether a future improvement is real or is the leak talking.

---

### 3. Exact scope — what actually reaches a model

This is narrower than the Rev 2 write-up implied, and worth pinning down before any work starts.

The warning currently prints **23** names, but none of them are selected by
`expand_feature_selection`, so they never enter any model's `X`. They are materialised as DataFrame
columns and then dropped:

```
appearance_count, appearance_trend_raw, appearance_volatility_raw, avg_gap_days,
freshness_c0_weight, freshness_c1_weight, freshness_c2_weight, in_regime_shift,
last_peak_distance, last_trough_distance, lt_category, lt_cold_weight, lt_hot_weight,
lt_medium_weight, lt_statistical_confidence, older_count, peak_count, recent_count,
regime_shifts_detected, std_gap_days, trend_is_significant, trough_count, very_recent_count
```

These are **wasted work, not leakage.**

The features that genuinely reach a trained model — taken from the `Final features (...)` lines of
the last run — are these seven:

| Feature | Source | M1 (15) | M2 (22) | M3 (33) | M4 (8) |
|:--|:--|:-:|:-:|:-:|:-:|
| `odd_even_json` | `lotto_odd_even_validated.json` | ✓ | ✓ | ✓ | ✓ |
| `range_spread_json` | `lotto_range_spread_validated.json` | ✓ | ✓ | ✓ | ✓ |
| `sum_contribution_json` | `lotto_sum_contribution_validated.json` | ✓ | ✓ | ✓ | ✓ |
| `window_saturation_penalty` | `window_saturation.py` over hmc + odds | | ✓ | ✓ | |
| `lt_category_alignment` | `lotto_long_term_patterns.json` | | ✓ | ✓ | |
| `lt_recency_weight` | `lotto_long_term_patterns.json` | | ✓ | ✓ | |
| `series_recent` | `hmc_data['series']` via `extractor.py:305-320` | | | ✓ | |

Proportion of each model's trained feature set that is a full-history constant:

```
Model 1 Momentum Specialist        3 / 15   (20%)
Model 2 Jackpot Optimizer          6 / 22   (27%)
Model 3 Complexity Explorer        7 / 33   (21%)
Model 4 Pool Generator             3 /  8   (38%)
```

And they are not fringe features. From the current `lottery_picks.txt`:

```
Line 3 Complexity Explorer   #1  series_recent           0.0548   <- top feature in the model
Line 2 Jackpot Optimizer    #10  range_spread_json       0.0438
Line 1 Momentum Specialist   #8  sum_contribution_json   0.0163
```

---

### 4. `series_recent` is a different and worse bug

The other six are static statistics that *could* defensibly be per-number constants if they were
estimated in-sample. `series_recent` is not: it is explicitly a **recency window**, and it has been
frozen at one date. `ml_lotto/features/extractor.py:305-320`:

```python
series_total = 0
series_recent = 0
for pattern_name, occurrences in series_patterns.items():
    for occurrence in occurrences:
        series_total += occurrence.get('count', 0)
        end_date = pd.to_datetime(occurrence.get('end_date', ''))
        days_ago = (current_timestamp - end_date).days
        if days_ago <= 60:                      # <-- 60 days before the LATEST draw
            series_recent += occurrence.get('count', 0)
```

`current_timestamp` is the most recent draw date. So for a training row at draw 200 (early 2023),
`series_recent` answers "did this number have a series ending in the 60 days before **September
2026**" — a question about the future, injected into a 2023 row. It is Model 3's single
highest-importance feature.

This one should be fixed first regardless of what is decided about the rest.

---

### 5. Evidence

Reproduced read-only against the live 497-draw history:

```
engine features produced:                                       72
time-invariant across draw 200 vs draw 450:                     18
  (was 20 before Rev 3 fixed avg_days_between_bonus,
   timing_decay_weight and composite_transition_score)

of those 18, actually selected into a model:                     7
of those 18, derived interaction terms built on the others:      4
  recent_14_x_bonus_hit_contribution_interaction
  total_count_x_bonus_hit_contribution_interaction
  total_count_x_recent_14_interaction
  triple_hot_0_recent
silently substituted but never selected (dead columns):         23
```

---

### 6. Fix plan

Four phases. Phases 0 and 1 are small and independently useful; Phase 2 is the real fix; Phase 3
is what makes it stick.

#### Phase 0 — Measure before building anything  *(~1 hour)*

Do not refactor six features on the assumption that they matter. Find out first.

1. Record the current validation block as a baseline (`model_comparison.csv` is already there).
2. Remove the seven names from the four model `features` lists in `ml_lotto/config.py`.
3. Re-run `quickpick.py` and compare Val AUC, PR-AUC lift and Top-7 lift.

Interpretation:

- **Metrics unchanged** (most likely, given AUC ≈ 0.50) → the features carry no signal. Delete them
  and close this issue. No point-in-time implementation needed at all. This is the cheapest good
  outcome and it is genuinely plausible.
- **Metrics drop materially** → the signal is real *or* the leak was doing the work. You cannot tell
  which yet, so proceed to Phase 2 and compare against this measurement.
- **Metrics improve** → they were pure noise plus leak. Delete them.

Phase 0 is reversible, touches one file, and could make Phases 1–2 unnecessary.

#### Phase 1 — Stop the two cheap problems  *(~2 hours)*

Independent of Phase 0's outcome.

1. **Stop materialising the 23 dead columns.** `get_all_feature_names(features_dict)` returns every
   key in the features dict, so the `**adv_feat` / `**lt_feat` splats in `extractor.py:360-375` drag
   23 unused names into every training DataFrame. Build `all_feature_names` from the union of the
   model configs' expanded feature lists instead. Saves 23 × 15,800 cells per dataset build, ×4
   datasets, and removes the misleading warning.
2. **Narrow the Rev 3 warning** to only the names that a model actually selected, so it reports
   leakage rather than unused columns.

#### Phase 2 — Point-in-time implementations  *(the real work, ~1–2 days)*

Only if Phase 0 says the features matter. Every one of these is derivable from the draw sequence the
engine already holds, so they belong in `walk_forward.py` next to the existing prefix-sum machinery
— not in a separate analyzer.

Add to `_precompute_matrices()` the running quantities each feature needs, then read the slice at
`t` in `extract_features_at_draw`.

**`sum_contribution_json`** — "mean draw-sum when this number appears, vs when it does not",
restricted to draws `0..t-1`. Both terms come from two prefix sums:

```
draw_sum[i]                = sum of the 6 main balls in draw i
cum_sum_with[t, num]       = cumsum over i<t of draw_sum[i] * matrix_main[i, num]
cum_count_with[t, num]     = cum_main[t, num]                       (already exists)
cum_sum_all[t]             = cumsum over i<t of draw_sum[i]

mean_with    = cum_sum_with[t,num] / cum_count_with[t,num]
mean_without = (cum_sum_all[t] - cum_sum_with[t,num]) / (t - cum_count_with[t,num])
score        = normalise(mean_with - mean_without)
```

O(1) per number per draw. Guard `t` small / zero appearances with the existing 0.5 default.

**`range_spread_json`** — identical shape, substituting `draw_span[i] = max(main) - min(main)` for
`draw_sum[i]`.

**`odd_even_json`** — affinity is the number's parity weighted by how often that parity wins. Keep a
running count of odd-balls-per-draw over `0..t-1`; the per-number score is a function of the number's
own (fixed) parity and that running rate.

**`window_saturation_penalty`** — `window_saturation.py` computes saturation rates from HMC category
counts. Port it to take a draw-index bound and call it with `t`. Cache per `t` since it is
category-level, not per-number — 3 values per draw, not 47.

**`lt_category_alignment` / `lt_recency_weight`** — from `long_term_pattern_analyzer`. These are
category-level statistics too (alignment of HMC category with realised win rate), so the same
"compute once per `t`, fan out to 47 numbers" trick applies. This is the most involved of the six;
if effort has to be cut, cut here — they appear in two models at modest importance.

**`series_recent` / `series_total`** (§4) — the engine has `self.draw_dates`, so the fix is to
evaluate the 60-day window against `draw_dates[t]` instead of a fixed `current_timestamp`. The series
occurrence list is already in `hmc_data`; filter it by `end_date <= draw_dates[t]` and
`(draw_dates[t] - end_date).days <= 60`. Sort the occurrences once in `__init__` and use
`bisect` to get an O(log n) slice per draw.

> **Convention to preserve:** the serving row uses `t = N` with the estimated next-draw date. Every
> new feature must be reachable at `t = N` or the serving row will KeyError. Rev 3's
> `extract_features_for_next_draw()` is the single entry point — use it.

#### Phase 3 — Lock it in  *(~2 hours)*

1. **Extend `tests/test_walk_forward_parity.py`** with the parity assertion for each newly
   implemented feature: the engine's value at `t = N` must equal the serving JSON's value, 0/47
   mismatches — the same contract `recent_*` and `total_count` are already held to.
2. **Add `tests/test_no_constant_features.py`**: no feature selected by any model config may be
   identical for a given number across draw 200 and draw 450. This test **fails today** with the
   seven names listed in §3, which is the point — it encodes the bug, then passes when it is fixed.
3. **Re-run the Phase 0 comparison** and record the before/after.

---

### 7. Verification that the fix is real

The leak is only genuinely gone when both of these hold:

1. `test_no_constant_features.py` passes.
2. **A label-permutation check**: shuffle `hit` within each draw, retrain, and confirm validation
   AUC collapses to 0.50 ± noise. If a permuted-label model still scores above chance, a feature is
   still carrying outcome information from the validation window and the leak was not closed.

The second check is the one that actually proves it, and it is worth building once — it is the same
harness described in the Improvements section (§9) for answering whether any edge exists at all.

---

### 8. Risks and things not to do

- **Do not "fix" this by deleting the static fallback and letting it raise.** Roughly 23 names would
  immediately KeyError on a legitimate path. Phase 1.1 removes those names first; only then is a
  hard failure safe.
- **Do not change feature semantics silently.** Changing `odd_even_json` from a full-sample score to
  an expanding-window score changes what the model learns. Re-run Phase 0's comparison after each
  feature, not once at the end, or a regression cannot be attributed.
- **Watch the early draws.** An expanding window at `t = 100` has few observations, so
  `mean_without` and friends will be noisy or undefined. Keep the existing neutral defaults (0.5,
  0.0) and prefer them over a wild estimate; `TRAINING_START_DRAW = 100` already gives some burn-in.
- **Do not regenerate the source JSONs per draw.** These are analyzer outputs over the whole file;
  calling `drawpick.py` 400 times is not the fix. The point-in-time versions belong inside the
  engine, computed from the matrices already in memory.
- **Expect no headline improvement.** Validation AUC is at chance. This work makes the measurement
  trustworthy; it is not a performance change, and it should not be reported as one.

---

### 9. Recommendation

Run **Phase 0 first**. Three of the seven features are in every model and the other four are in two
models each, but validation says the models have no skill, so there is a real chance that deleting
all seven changes nothing measurable — in which case the correct fix is deletion and this issue
closes in an afternoon.

Regardless of Phase 0, do **Phase 1** (cheap, removes 23 wasted columns and makes the warning
honest) and fix **`series_recent`** (§4), which is a genuine future-data leak into a 2023 training
row and is Model 3's top feature.

Reserve the full Phase 2 for the case where Phase 0 shows the features carry weight.
