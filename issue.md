# Open Issues — Irish Lotto ML System

**Maintained by:** Claude Opus 5
**Last updated:** 2026-09-19
**Scope:** the single record of outstanding defects.

Sections 1-5 are **open**: defects by severity, then improvements not yet started. Section 6 lists
improvements already done. Items carried from the retired code review keep
their original IDs (C-nn / N-n); items found later are numbered F-n, and an ID is never reused.
Appendix A is the resolved list. Appendix B keeps the full C-5 write-up for reference.

**Keeping this file true.** The Priority summary lists **open items only** — a resolved ID never
appears in it. When a defect is found: give it the next free F-n, add a row to the Priority summary,
and write a section with file:line evidence. When one is fixed: delete its summary row, renumber the
remaining sections, add it to the Appendix A table, and write up the root cause and the measured
effect. A fix is not finished until this file says so.

**Improvements are tracked the same way.** Planned work that is not a defect also gets the next
free F-n, a Priority summary row with severity `Improvement`, and its own section. When done, it
moves to section 6 (Improvements done). Nothing open lives only in a list or in `plan.md`.

---

## Priority summary

| # | ID | Issue | Severity | Effort |
|--:|:--|:--|:--|:--|
| 1 | **C-6b** | Serving reference date differs between the two feature paths | Low | S |
| 2 | **C-17b** | Legacy `tests/*.py` are print scripts, not tests | Low | M |
| 3 | **F-7** | `analysis/` scripts read a window that has never existed | Low | S |

**3 open defects, nothing High; no improvement open.** Everything resolved is in Appendix A and appears nowhere above.

---

## 1. C-6b — The two feature paths use different serving reference dates

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
## 2. C-17b — The legacy test files are not tests

**Severity: Low.** Carried from the code review.

Six of the eleven legacy files in `tests/` contain zero `assert` statements — they are
print scripts that pass by not raising (counted 2026-09-19, after F-6 deleted two ensemble scripts). Their work also happens at module import, so collecting them
under pytest executes data loading and model training:

```
test_better_metrics.py  test_interactions.py
test_model_specific_features.py  test_rolling_integration.py
test_rolling_stats_integration.py  test_smote_threshold.py
```

The four files added during this review (`test_walk_forward_parity.py`,
`test_selection_invariants.py`, `test_metrics.py`, `test_no_constant_features.py` — 37 tests) are
real and run in about 5 seconds. A plain `pytest tests/` still cannot be used because of the others.

**Fix.** Convert the useful ones to assertions inside functions, delete the rest, and add a
`pytest.ini` so `pytest` runs clean from the repo root.

---
## 3. F-7 — Standalone analysis scripts read a window that has never existed

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
## 6. Improvements done

Kept for the record; each is complete and covered by tests.

- **2026-09-19 - F-19, steer lines away from popular combinations.**
  Expected *payout* is not uniform even when probability is: birthday numbers (<=31), calendar
  patterns and arithmetic sequences are heavily played and share prizes more often. Steering toward
  numbers >=32 does not change the chance of winning; it lowers the chance of sharing a prize. This
  repo has no ticket-sales data, so that benefit cannot be measured here. (An earlier note said the
  sum and odd rules push toward popular combinations; checked 2026-09-19, they barely steer - they
  pass 95% and 81% of all lines.)

  **Done 2026-09-19 - the data, on the dashboard.** `drawpick.py` Phase 6
  (`distribution_analyzer.analyze_high_number_distribution`) writes, into
  `lotto_distribution_stats.json`, how many draws had 0-6 main numbers >= 32, with a fair draw's share
  alongside. The Statistics page shows the breakdown on its own; the Prediction Validator also shows it
  for any line the user types in, information only.
  Over the 497 analysed draws:

  | Numbers >= 32 | Draws | Share | Fair draw |
  |--:|--:|--:|--:|
  | 0 | 32 | 6.44% | 6.86% |
  | 1 | 112 | 22.54% | 25.32% |
  | 2 | 182 | 36.62% | 35.16% |
  | 3 | 130 | 26.16% | 23.44% |
  | 4 | 35 | 7.04% | 7.88% |
  | 5 | 5 | 1.01% | 1.26% |
  | 6 | 1 | 0.20% | 0.07% |

  Draws follow the fair-draw shares; 2 is the most common count and 3+ happens in 34%.

  **Tried and reverted: "at least 3 numbers >= 32" in selection.** It worked (all three lines met it)
  but skewed the lines: it rules out 67% of all lines and squeezes half of each into a 16-number range,
  which raises the share of lines with a consecutive pair from 53% to 55% and the share whose pair sits
  in 32-47 from 20% to 44% - all three generated lines had one (42-43, 39-40, 32-33). "At least 2"
  leaves consecutive pairs at their natural rate (51%) and still excludes the most birthday-heavy lines
  (0-1 high numbers).

  **Decided 2026-09-19, from the dashboard data: a per-model floor.** `min_high_numbers` in each model
  config - Models 1 and 2: at least 2 numbers >= 32 (71% of past draws had 2+); Model 3: no floor, its
  probabilities decide. A floor, not a target: a model may pick more. One constraint in
  `ilp_selection.solve_line` over the whole ticket; not in `validate_line`, since it differs per model.

  Picks: Model 1 unchanged `[5, 13, 15, 24, 42, 43]` (already 2); Model 2 `[6, 8, 9, 23, 31, 39]` ->
  `[6, 9, 23, 31, 38, 39]` (8 -> 38); Model 3 `[7, 22, 32, 38, 40, 47]` -> `[10, 19, 22, 32, 40, 47]`,
  moved only because Model 2 now holds 38 (it still has 3 high numbers unforced). Lines disjoint.
  Tests (`test_selection_invariants.py`): the floor is enforced in a world whose scores favour 1-31,
  is a floor not a target, and counts pre-assigned numbers; removing the constraint fails two.

- **2026-09-19 - F-18, is the freshness pattern worth enforcing? Kept; change freeze lifted.**
  Enforcing a bin pattern can only help if a number's freshness bin changes its chance of being
  drawn, so that was tested directly instead of the two-line backtest first proposed (60 draws, noise
  ~ +/- 0.27 matches - it could only have seen a huge effect). `analysis/freshness_hit_rate.py`: for
  draws 5..496, each number's bin as it stood before the draw - the engine's `min(recent_4, 2)`,
  identical to the serving `current_freshness_bin` selection enforces (`last_4`, C_max 2) - against
  whether it was a main ball. Rule fixed before running: chi-square p < 0.05 keeps the mechanism,
  otherwise its enforcement is deleted.

  | Bin | Exposures | Hits | Hit rate | Expected hits |
  |--:|--:|--:|--:|--:|
  | 0 | 11,714 | 1,499 | 0.1280 | 1,495.4 |
  | 1 | 8,526 | 1,045 | 0.1226 | 1,088.4 |
  | 2 | 2,884 | 408 | 0.1415 | 368.2 |

  chi2 = 6.94, dof 2, **p = 0.031 - keep**. The excess is in bin 2 (drawn 2+ times in the last 5
  draws): +11% over its share. Checked not to be a data artifact: 497 draws on 497 distinct dates, no
  duplicated draw, consecutive-draw overlaps match a fair draw (3 shared numbers 13 times vs 9.8
  expected, 4+ never).

  **Read it with care.** p = 0.031 is weak - one test in twenty passes at that level by chance - and
  the effect is small: one bin-2 number per line is worth about +0.015 expected matches. The rule said
  keep, so the mechanism stays and the freeze is lifted by its own condition. Re-run the script as
  draws accumulate; it takes seconds. If p rises above 0.05, delete the enforcement - the decision was
  made on this evidence, and it should follow the evidence.
- **2026-09-18 - F-17, label-permutation check: no model has an edge.**
  `ml_lotto/models/permutation_check.py`, run as `python quickpick.py --permutation-check 20`. Each
  main model is trained once on real labels and 20 times with the training labels shuffled within
  each draw (hit counts kept, number-outcome link destroyed), through the exact production pipeline
  - features, selection, tuning, calibration - and every run is scored on the real validation
  labels. The rule was fixed before running: an edge needs p < 0.05, i.e. beating all 20 shuffled
  runs.

  | Model | Real val AUC | Shuffled: mean +/- sd (range) | Shuffled >= real | p |
  |:--|--:|:--|--:|--:|
  | Momentum Specialist | 0.5011 | 0.4967 +/- 0.0151 (0.454-0.522) | 9 / 20 | 0.476 |
  | Jackpot Optimizer | 0.5257 | 0.5066 +/- 0.0163 (0.483-0.551) | 2 / 20 | 0.143 |
  | Complexity Explorer | 0.5074 | 0.4891 +/- 0.0132 (0.471-0.532) | 2 / 20 | 0.143 |
  | Conservative Pool Generator | 0.5118 | 0.4928 +/- 0.0119 (0.470-0.516) | 1 / 20 | 0.095 |

  No model passes. Model 1 sits mid-null; the best, Model 4, is beaten by 1 of 20 shuffled runs. The
  shuffled sd of 0.012-0.016 independently confirms the +/- 0.031 noise floor. Four real AUCs above
  their null means is not evidence either: the models share one validation window, so the four are
  not independent draws. The answer to "is there any edge?" is no, as expected for a fair draw -
  further model tuning has nothing to find. To support this, `trainer.build_main_datasets()` was
  extracted and `train_model(output_dir=None)` writes no artifacts. Tests:
  `tests/test_permutation_check.py`.
- **2026-09-18 - Wheel the Model 4 pool.** `ml_lotto/prediction/wheel.py` covers every 3-subset of the
  pool's top 8 with 4 lines (C(8,6,3) = 4): 3+ winners in the top 8 guarantees a match-3, which
  happens in ~5.3% of draws. Written to `lottery_picks.txt` as `Wheel Line 1-4`, guarded by
  `tests/test_wheel.py`. A guarantee over the whole 20 does not fit a 4-8 line budget - even "all 6
  winners in the pool" needs more than 8 lines and fires in 0.36% of draws. It is not an edge and
  does not reduce blanks: 4 unrelated lines catch a match-3 in ~7.2% of draws.
- **2026-09-18 - MILP selection**. `ml_lotto/prediction/ilp_selection.py` replaces
  greedy picking and the filter repair pass with `scipy.optimize.milp`: HMC quotas, the reachable
  freshness target and the ticket rules are constraints, so a line meets all of them or the solver
  raises. Not a prediction change - it removed a defect surface (F-14).

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
| C-15a | Feature engine rebuilt 5x per run; O(N^2) gap-list memory | `walk_forward.py`, `trainer.py`, `bonus_trainer.py`, `bonus_to_main_trainer.py`, `quickpick.py` |
| F-6 | Ensemble code was unreachable, and each entry point was broken | deletes `ensemble.py`, `ensemble_predict.py`, `analysis/ensemble.py`; `config.py`, `quickpick.py` |
| F-20 | Bonus prediction 2 claimed category diversity it never applied | `bonus_predictor.py` |
| F-5 | A too-small bonus pool crashed with a bare IndexError; the registered divide-by-zero was unreachable | `bonus_predictor.py` |
| F-16 | Diversity penalty applied twice; the configured percentage barely mattered | `ilp_selection.py`, `predictor.py` (deletes `penalties.py`) |
| F-15 | Config feature names the serving path never produces were dropped silently | `config.py`, `extractor.py` |
| C-15b | Tree models memorised the training set (train/val AUC gap 0.383) | `config.py`, `hyperparameter_tuning.py` |
| C-16 | Non-deterministic feature column order | `extractor.py` |
| F-1 | Freshness target sized for 7 balls while a line has 6 slots | `freshness_analyzer_7_numbers.py`, `constraints.py`, `drawpick.py` |
| F-2 | Bonus and bonus-to-main models had no validation split | `quickpick.py`, `bonus_trainer.py`, `bonus_to_main_trainer.py`, `trainer.py` |
| F-3 | Decision threshold tuned and scored on the same validation rows | `model_metrics.py` |
| F-4 | Probability array built conditionally while every consumer indexed it positionally | `predictor.py` |
| F-10 | Dead look-ahead guard printed a false reassurance; contradictory split constant | `hmc_analyzer.py`, `lotto_analysis/config/config.py` |
| F-13 | Freshness target could be unreachable for a model's HMC ratio, and missed it silently | `constraints.py`, `predictor.py` |
| F-14 | Filter repair overrode the diversity penalty and reported the pre-repair pattern | `ilp_selection.py` (replaces `selection.py`, `rebalance_line`) |
| F-8 | Freshness target was consulted for ordering then discarded; bin 0 absorbed every slot | `selection.py` |
| F-9 | Serving features fell back to 0 for a column the model was trained on | `predictor.py`, `bonus_predictor.py` |
| F-11 | HMC categorization measured days against wall-clock today | `hmc_categorization_analyzer.py` |
| F-12 | `max(set(...), key=list.count)` tie-break was non-deterministic | `bonus_to_main_analyzer.py`, `generate_bonus_to_main_json.py` |
| N-1 | Serving row was stale by one draw | `walk_forward.py`, `quickpick.py` |
| N-1b | `draws_since_bonus` was exactly inverted | `walk_forward.py` |

### F-6 — Ensemble code was unreachable, and each entry point was broken

**Root cause.** Ensembling was added (commit `85d3c41`, 2025-11-21) to combine the four main models
by vote, but never wired into `quickpick.py`. Checked 2026-09-19, every way in was broken as well
as unreachable:

- `ml_lotto/prediction/ensemble.py` (341 lines, majority/threshold/weighted/unanimous voting) was
  imported only by a demo script and legacy print-scripts.
- `scripts/ensemble_predict.py`: `main()` printed two warnings and returned 0 - it never called
  the voting code.
- `ENSEMBLE_MODE = True` in `config.py` only printed a banner claiming "Each model runs 15x with
  different seeds"; nothing reran anything.
- `scripts/train_with_all_features.py` voted on `val_proba.argsort()` - row positions in the
  validation table, not lotto numbers 1-47.
- `analysis/ensemble.py` reran `quickpick.py` with seeds 42..56 by rewriting `ml_lotto/config.py`
  in place (a crash mid-run left the source modified), left `lottery_picks.txt` and
  `model_metrics/` from the last seed rather than 42, had a 120 s timeout against a ~108 s run, and
  read only Models 1-3.

Beyond the defects, the method cannot help here: averaging cancels independent errors of models
that carry signal, and every model sits at chance (F-17).

**Fix.** Deleted `ml_lotto/prediction/ensemble.py`, `scripts/ensemble_predict.py`,
`analysis/ensemble.py`, and the print-scripts `tests/test_ensemble.py` and
`tests/test_ensemble_predict.py`. Removed `ENSEMBLE_MODE`, `ENSEMBLE_RUNS` and the unused
`_CURRENT_RANDOM_SEED` from `config.py` and the banner branch from `quickpick.py` (the deterministic
seed path is now the only one). Stripped the voting step from `scripts/train_with_all_features.py`
and `tests/test_train_with_all_features.py`. About 1,300 lines removed; recoverable from git.

**Measured before/after.** `lottery_picks.txt` identical apart from its timestamp; metrics
unchanged against the baseline. Nothing removed was on the path that produces either.

**Tests.** None added - this deletes code rather than changing behaviour. The 127 real tests pass;
`grep` finds no remaining import of the deleted modules or flags.

### F-20 — Bonus prediction 2 claimed category diversity it never applied

**Root cause.** `ml_lotto/prediction/bonus_predictor.py` chose prediction 2 with
`cat != used_categories` - a string compared to a set, always true - so it took the second-highest
probability whatever its category, while the log printed "Category diversity". Prediction 3 used
`not in` and was correct. Found 2026-09-19 while fixing F-5.

**Fix.** `cat not in used_categories`. The rule the docstring describes now holds: prediction 2 is
the best number from a different hot/medium/cold category than prediction 1, and prediction 3 from
a category not used yet, so the three span all three categories when the pool allows.

**Measured before/after.** In a case where the top two share a category (47 and 46 both cold), the
old code returned `[47, 46, 45]` - two colds - and the fix returns `[47, 45, 44]`, one of each. The
real run is unchanged, `[45, 10, 19]` (cold, medium, hot): its top two already differed. Picks and
metrics identical; bonus probabilities are at chance, so this is about what the output claims, not
about odds.

**Tests.** `tests/test_bonus_predictor.py::test_three_picks_span_three_categories_when_the_top_two_share_one`
fails on the old comparison and passes on the fix.

### F-5 — A too-small bonus pool crashed with a bare IndexError

**Root cause.** The register said `assign_bonus_to_models` divides by zero on an empty list and that
`generate_bonus_predictions` could return fewer picks than requested. Reproduced 2026-09-19 with a
stub model: the second claim is false. With a pool of 0, 1 or 2 numbers after recent-bonus
exclusions, `generate_bonus_predictions` raised `IndexError: list index out of range` itself
(`available_pool[0]`, `available_pool[i]`, `candidates[0]`), so an empty list never reached
`assign_bonus_to_models` - the division by zero was unreachable from `quickpick.py`. The real defect
was an unchecked precondition failing with an unexplained error. In practice the pool is never thin:
the bonus window is a `deque(maxlen=10)` (`walk_forward.py:145`), so at most 10 numbers are excluded
and at least 37 remain.

**Fix.** `generate_bonus_predictions` raises `ValueError` naming the pool size and the request when
the pool is smaller than `num_predictions`. The fix the register proposed - return `{}` and let the
`None` handling take over - was not applied: it is a silent default, and would have produced a run
with no bonus ball and no error.

**Measured before/after.** Pools of 0/1/2: `IndexError` before, `ValueError` with a message after.
Pool of 3 and the real pipeline: unchanged. No metric or pick can move - the guard is never reached
with a 10-draw window.

**Tests.** `tests/test_bonus_predictor.py` (new, 6 tests): pools of 0, 1 and 2 raise `ValueError`
(the three fail on the old code with `IndexError`); a pool of exactly 3 uses all of it; with the
widest real exclusion (10 numbers) the three picks are distinct and none excluded; every model gets
one of the predictions.

### F-16 — The diversity penalty was applied twice

**Root cause.** `predictor.py` scaled each number used by an earlier line down by the model's
`diversity_penalty` (25-40%, rank-aware, `penalties.py`), then `solve_line` also charged a flat 1 per
such number. The flat cost dominated, so the configured percentages only ordered reused numbers
among themselves when one was unavoidable - a config advertising "30% soft penalty" was in effect a
near-hard rule. Model 4's key was never read at all. The greedy picker had the same stack; the ILP
carried it over.

**Fix.** One mechanism: the flat cost, now `PENALTY_COST = LINE_SIZE`. Scores are probabilities
below 1, so two lines' sums differ by less than 6 and the cost is exactly lexicographic - fewest
reused numbers first, then best probability - whatever the probability spread. The cost of 1 relied
on spreads being small. The solver gets raw probabilities. Deleted: `penalties.py`, the four
`diversity_penalty` keys, `SHOW_DETAILED_PENALTIES` and the rank-aware explanation display. The run
now prints how many numbers each line avoids and any it had to reuse.

**Measured before/after.** Picks unchanged - `[5, 13, 15, 24, 42, 43]`, `[6, 8, 9, 23, 31, 39]`,
`[7, 22, 32, 38, 40, 47]`, still disjoint - which confirms the percentage was not affecting the
result. Metrics untouched: selection does not feed training.

**Tests.** `tests/test_selection_invariants.py`: in a random and four skewed score worlds, the
unpenalised optimum is penalised and the solver must match a brute-force lexicographic optimum.
Dropping the cost to 0.1 fails two of the five.

### F-15 — Config feature names were dropped silently

**Root cause.** `expand_feature_selection` (`ml_lotto/features/extractor.py`) kept a config name only
`if item in all_features` and skipped anything else without a word. A run with every call
instrumented found two such names: `recent_14` in Models 1, 2 and 3 (the walk-forward engine
produces it, the main serving path has no 15-draw window) and `category` in `BONUS_MODEL_CONFIG`
(the bonus dataset excludes the raw category string; the model uses `category_weight`). Model 1's
comments also misdescribed its config: "~17 features" for 25, `recent_4` as "last 4 draws" for 5, and
an empty `# CONSTRAINTS` block.

**Fix.** The four dead names are removed from the configs, Model 1's comments corrected, and
`expand_feature_selection` now raises `ValueError` on a name that is neither a keyword nor an
available feature. The bonus model's `recent_14` stays - it is produced on both of its paths.

**Measured before/after.** No model's features changed - Model 1 25, Model 2 16, Model 3 26, Model 4 5,
bonus 32 columns, identical to before - because the names were never reaching a model. Picks
unchanged; the largest metric move is 1.9e-5 in Model 2's overfit gap, run-to-run noise.

**Tests.** `tests/test_no_constant_features.py` expands every main config against the engine's
features, so an unknown name now fails it; a new test asserts the raise directly. A full
`quickpick.py` run exercises all six configs against the serving features.

### C-15a — The feature engine was rebuilt five times per run

**Root cause.** Each trainer built its own `PointInTimeFeatureEngine` because the engine carried its
static `base_features_dict` (main, bonus, bonus-to-main) alongside the draw state, so a different
dict meant a new engine. Measured 2026-09-18 on a full `quickpick.py` run: 5 constructions - main
trainer, bonus trainer twice (train and validation datasets), bonus serving row, bonus-to-main
trainer - at ~0.5 s each. Separately, `_precompute_timeline_state` snapshotted every number's full
gap list at every draw: 843,204 stored gaps, 12.8 MB retained per engine.

**Fix.** Two parts.
- `with_base_features()` returns a shallow view sharing the precomputed state and swapping only the
  base features. `quickpick.py` builds one engine and passes it to all three trainers and the bonus
  serving row as `base_engine`.
- Gap lists are replaced by running moments `(count, sum, sum of squares, max)`; variance is
  `(n*ss - s^2) / n^2` over exact integers.

**Measured before/after.** Constructions 5 -> 1; engine time 2.43 s -> 0.49 s of a ~120 s run.
Memory per engine 12.8 MB -> 5.1 MB. Feature output for every draw 0..N compared value by value:
1,683,420 identical, 25,218 differing by at most 5.7e-14 (float rounding in the four gap-derived
features only), 0 real differences. Picks unchanged; the largest metric move is 1.1e-5 in Model 2's
overfit gap, run-to-run noise.

**Tests.** `tests/test_walk_forward_parity.py`: gap variance, CV and max ratio checked against numpy
over the gaps recomputed from the draw history; a view shares state and equals a freshly built
engine. Both fail when the variance formula or the view is broken.

**Not changed.** `build_walk_forward_dataset` / `trainer.build_training_dataset` still build their
own engine; only `scripts/train_with_all_features.py` and a legacy print-script call them.

### F-14 — The filter repair overrode the diversity penalty and reported a stale pattern

**Root cause.** `pick_line_hybrid()` chose numbers first and checked the ticket rules afterwards;
a failing line went to `filters.rebalance_line()`, which swapped numbers by raw probability. Two
consequences, both visible in the 2026-09-18 run:

- **The penalty was bypassed.** Model 3's line `[10, 22, 32, 38, 40, 47]` failed odd/even (1 odd).
  The repair swapped 22 for 9 - the rank-1 penalised number for Model 3 (35%) and already on Model 2's
  line `[6, 8, 9, 23, 31, 39]` - because it ranked replacements on unpenalised `probabilities`.
- **The printed pattern could be stale.** `pattern_str` was built before the repair phase ran
  (old `selection.py`, pattern built above `# PHASE 3: Filter validation`), so `Achieved Pattern`
  described the pre-repair line whenever a repair happened.

**Fix.** Replaced by `ilp_selection.solve_line()`: one `scipy.optimize.milp` solve with the HMC
quotas, the reachable freshness target, the sum/odd/span rules (on the whole ticket, pre-assigned
included) and a 1-per-number penalty cost. `selection.py` and `rebalance_line` are deleted. The
pattern is computed from the returned line.

**Measured before/after.** Models 1 and 2 are unchanged (`[5, 13, 15, 24, 42, 43]`,
`[6, 8, 9, 23, 31, 39]`) - the greedy line was already the optimum. Model 3 goes from
`[9, 10, 32, 38, 40, 47]` to `[7, 22, 32, 38, 40, 47]`: still 2H/2M/2C and `C0=4, C1=2`, and the
three lines now share no number. Validation metrics are untouched - selection does not feed training.

**Tests.** `tests/test_selection_invariants.py`, rewritten for the solver (19 tests): every
constraint met, the line equals a brute-force optimum in a random and four filter-stressing score
shapes, pre-assigned numbers fixed and filters applied to the whole ticket, penalties avoided when
possible but never shortening the line, infeasibility raises. Disabling any one constraint in the
solver fails at least two tests.

### F-13 — The freshness target could be unreachable for a model's HMC ratio

**Root cause.** `target_pattern` came from `get_optimal_pattern_distribution()` and the hot/medium/
cold counts from `ml_lotto/config.py`, with nothing reconciling them. The freshness bins are not
spread evenly across HMC categories - measured 2026-09-17, every bin 1 and bin 2 candidate was hot
(hot 7/16/7, medium 7/0/0, cold 10/0/0) - so a line can hold at most as many non-bin-0 numbers as it
has hot slots. Model 3 has 2 hot slots against a target wanting 3 non-bin-0, and was therefore
unsatisfiable by construction. It missed silently, and the miss looked like a selection failure.

**Fix.** `constraints.reachable_pattern()` computes what a model can actually achieve from its HMC
quotas and the live pool composition, allocating scarce bins first and drawing on the most
constrained category first - the same ordering `selection.pick_line_hybrid` uses, so the result is
attainable rather than optimistic. `predictor.py` passes that to selection and prints the shortfall:

```
Target unreachable for this HMC ratio, using {0: 4, 1: 2, 2: 0} (C0: 3 -> 4, C2: 1 -> 0)
```

**Measured before/after.** Picks are unchanged - `[5, 13, 15, 24, 42, 43]`, `[6, 8, 9, 23, 31, 39]`,
`[9, 10, 32, 38, 40, 47]` - because the reachable pattern is what selection already achieved after
F-8. The change makes the constraint visible and attributable, not different.

Validated against the three known outcomes: `reachable_pattern` predicts `{0:3,1:2,2:1}`,
`{0:3,1:2,2:1}` and `{0:4,1:2,2:0}`, matching all three lines exactly, Model 3's shortfall included.
A feasibility calculation that disagreed with what selection produces would be worse than none.
Slot conservation checked across all 28 hot/medium/cold splits summing to 6: no mismatches.

**What this does not do.** Model 3 still cannot place 3 non-bin-0 numbers; that is arithmetic, not a
bug. Two alternatives were rejected: deriving a per-model target from the freshness data would mean
each model chases a different pattern, which is no longer the observed distribution the target
represents; and changing the HMC ratios would be tuning the models to satisfy a mechanism whose value
is unestablished.

**Resolved by F-18 (2026-09-19): kept.** Freshness bins do differ in hit rate (p = 0.031), so the
target and `reachable_pattern` stay. See section 7.

### F-8 — The freshness target was consulted for ordering, then discarded

**Root cause, two parts.** `pick_from_hmc_pool` ranked the freshness bins **once** per HMC category
and then drained the top bin until the slot count was met. Bin 0 holds 24 of 47 candidates, so it
never ran out and the loop never reached bin 1. The target was a sort key, not a constraint.

Fixing the ranking alone was **not sufficient**, and the first attempt made Line 3 worse. The second
part is call order. Every bin 1 and bin 2 candidate is hot (see F-13); medium and cold can supply
only bin 0. Picking hot first spent the bin 0 quota on the one category that could have supplied the
scarce bins, after which medium and cold overshot bin 0 because they had nowhere else to go.

**Fix.** Re-rank the bins before every pick, so each slot goes to the bin with the largest unmet gap,
and take the HMC categories **most-constrained-first**, so a category that can only supply one bin
claims its quota before the flexible category spends it. `freshness_counts` is shared across the
three calls, so the target applies to the line rather than per category. HMC categories are disjoint,
so the reordering changes only which bins get claimed, never which numbers a category may use.

**Measured before/after** (target `C0=3, C1=2, C_GE_2=1`):

| Line | Before | Ranking fix only | Both fixes |
|:--|:--|:--|:--|
| 1 Momentum Specialist | C0=6, C1=0 | C0=5, C1=1 | **C0=3, C1=2, C_GE_2=1** |
| 2 Jackpot Optimizer | C0=6, C1=0 | C0=5, C1=1 | **C0=3, C1=2, C_GE_2=1** |
| 3 Complexity Explorer | C0=4, C1=2 | C0=6, C1=0 | C0=4, C1=2 |

Two lines now hit the target exactly. Line 3 has only 2 hot slots and therefore at most 2 non-bin-0
numbers, so `C0=4, C1=2` is its structural optimum - see F-13, which is the open half of this.

All three lines still pass the ticket filters unrepaired (sums 142/116/176, spans 38/33/38, odd
counts 4/4/2). A side effect worth noting: bin 0 concentration was itself *causing* filter failures -
in a controlled reproduction the old code produced an all-bin-0 line that was 6 odd / 0 even, failed
`odd_even_balance`, and had to be repaired, which scrambled the freshness distribution further. The
two mechanisms were working against each other.

**Tests.** Verified with a controlled reproduction on a pool deliberately skewed like the real one
(bin 0 oversupplied): the old code returns `{0:2, 1:3, 2:0}` plus a repaired number and fails the
filters, the new code returns `{0:3, 1:2, 2:1}` and passes. The existing 79 pass. Model metrics are
unchanged and cannot change - selection is downstream of them.

**Not answered.** Whether enforcing the target is worth anything. `model_comparison.csv` scores the
models, not the selection, so it cannot settle this; it needs a backtest of generated lines against
actual draws. If the freshness pattern carries no signal the mechanism should be deleted rather than
fixed, and F-13 disappears with it.

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
all history is correct. Training never reads it: `walk_forward.py:241-243` derives `category` itself,
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
harness described in F-17 for answering whether any edge exists at all.

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
