# Open Issues — Irish Lotto ML System

**Maintained by:** Claude Opus 5
**Last updated:** 2026-09-16
**Scope:** the single record of outstanding defects. The code-review history it grew out of has
been retired; Appendix A lists what was fixed and Appendix B keeps the one write-up worth holding on to.

This is the open-issues register. Everything in §1–§12 is **unfixed**. Items carried from the code
review keep their original IDs (C-nn / N-n); items found in the final review pass are numbered F-n.
Appendix A indexes what is resolved; Appendix B keeps the full C-5 write-up for reference.

---

## Priority summary

| ID | Issue | Severity | Effort |
|:--|:--|:--|:--|
| **F-2** | Bonus and bonus-to-main models have no validation split | High | S |
| **F-3** | Decision threshold is tuned and scored on the same validation set | Medium | S |
| **C-15b** | Jackpot Optimizer Random Forest badly overfits (gap 0.383) | Medium | S |
| **F-4** | `probabilities[num-1]` assumes all 47 numbers are present | Medium (latent) | S |
| **C-14** | Scraper has no fallback source and no main-draw verification | Medium | M |
| **F-5** | `assign_bonus_to_models` divides by zero on an empty list | Low (latent) | XS |
| **C-15a** | Feature engine rebuilt 3–4× per run; O(N²) gap memory | Low | S |
| **F-6** | Ensemble machinery is unreachable from the pipeline | Low | M |
| **C-6b** | Serving reference date differs between the two feature paths | Low | S |
| **C-17b** | Legacy `tests/*.py` are print scripts, not tests | Low | M |
| **F-7** | `analysis/` scripts read a window that has never existed | Low | S |
| **F-8** | Freshness target barely constrains selection; bin 0 absorbs every slot | Medium | M |

---

## 1. F-1 — The freshness target sums to 7 but a line has 6 slots  — **RESOLVED**

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

<details><summary>Original report</summary>

**Severity: High.** Silently biases every line the system generates.

`ml_lotto/prediction/constraints.py:34-46` returns the target distribution straight from
`lotto_7_number_freshness_results.json`, which describes the freshness split of the **7 drawn
balls**. Every model picks **6** numbers.

```
c_max_threshold : 2
target_pattern  : {0: 4, 1: 2, 2: 1}   SUM = 7
numbers picked per model                    6
```

`predictor.py:137` prints:

```
NOTE: Each model picks 6 main numbers (adjusted proportionally from 7-number pattern)
```

No such adjustment exists — `grep -rn "proportion" ml_lotto/` matches only that print statement.
The raw 7-number counts are passed to `pick_line_hybrid` as `freshness_needed`, and
`pick_from_hmc_pool` orders freshness bins by `freshness_needed[f] - freshness_counts[f]`. With one
extra number's worth of demand spread across the bins, that gap is overstated throughout selection
and bin priority is systematically skewed.

**Fix.** Decide what the 6-number target should be and compute it rather than asserting it in a log
line: either scale the 7-number distribution to 6 (rounding under the constraint that counts sum to
6), or derive the distribution from the main 6 balls — note the source JSON is explicitly a
7-number analysis, so a 6-ball equivalent may need generating. Then assert
`sum(target.values()) == 6` so it cannot drift again.

</details>

---

## 2. F-2 — The bonus and bonus-to-main models train on 100% of the data

**Severity: High.** Two of the six models have no validation at all.

Both trainers accept validation parameters:

```python
# ml_lotto/models/bonus_trainer.py:68-69
training_end_draw: int = None,
validation_start_draw: int = None

# ml_lotto/models/bonus_to_main_trainer.py:23-24
training_end_draw: int = None,
validation_start_draw: int = None
```

`quickpick.py` never passes either — `train_bonus_model(...)` and `train_bonus_to_main_model(...)`
are both called with four positional arguments, so both default to `None` and both fit every draw.

C-10 restored `VALIDATION_SPLIT_RATIO = 0.85` for the four main models only. Consequences:

- No held-out metrics, so there is no evidence either model works.
- The probabilities written to `lottery_picks.txt` (bonus 2.8–3.1%, bonus-to-main up to 12.2%) are
  **in-sample** and are not comparable with the main models' out-of-sample numbers.
- They are exempt from the check that caught every other problem in this codebase.

**Fix.** Pass `calculate_train_val_split(len(all_draws))` through to both and route their validation
frames into `calculate_comprehensive_metrics`, so they appear in `model_comparison.csv` with
everything else. Expect the same verdict as the main models; the point is to be able to see it.

---

## 3. F-3 — The decision threshold is chosen on the validation set and then scored on it

**Severity: Medium.** Makes the reported operating-point metrics optimistic.

`ml_lotto/models/model_metrics.py:196-199`:

```python
precisions_temp, recalls_temp, pr_thresholds_temp = precision_recall_curve(y_val, val_proba)
f1_scores_temp = 2 * (precisions_temp * recalls_temp) / (precisions_temp + recalls_temp + 1e-10)
optimal_idx = np.argmax(f1_scores_temp)
optimal_threshold = pr_thresholds_temp[optimal_idx] ...
```

`optimal_threshold` is the F1-maximising threshold **on `y_val`**, and lines 215-216 compute the
reported Precision / Recall / F1 / Accuracy on that same `y_val` at that threshold. The threshold is
fitted to the data it is evaluated on.

Compounding it: maximising F1 at a ~15% positive rate drives the threshold down to roughly the base
rate, which is why every model reports Recall ≈ 1.0 with Precision ≈ the base rate. Those columns
describe a classifier that answers "yes" to nearly everything.

**Fix.** Either select the threshold on a slice of the training data and report it on untouched
validation, or drop the operating-point columns. AUC, PR-AUC and the per-draw Top-K lift are
threshold-free and already carry the signal.

---

## 4. C-15b — The Jackpot Optimizer memorises the training set

**Severity: Medium.** Carried from the code review.

```
Train AUC 0.911  vs  Val AUC 0.528   ->  gap 0.383
```

`MODEL_2_CONFIG['algorithm_params']` is `n_estimators=100, max_depth=10, min_samples_split=5`, with
no `min_samples_leaf` and no `max_features` constraint, over ~15,800 rows. A depth-10 forest has
ample capacity to memorise per-number patterns.

Rev 4 briefly showed 0.148, but that came from *removing* features, not from fixing the model; Rev 6
restored informative main-6 features and the gap returned. Validation AUC is unaffected (0.5078
baseline → 0.5284), so this is wasted capacity rather than a correctness bug — but it makes the
model's training behaviour useless as a diagnostic.

**Fix.** Constrain the forest (`max_depth` 4–6, `min_samples_leaf` in the hundreds, `max_features`
below 1.0) and confirm the gap falls without validation AUC dropping. Worth reviewing for all four
models — Complexity Explorer sits at 0.165.

---

## 5. F-4 — Probability arrays are indexed by number without guaranteeing all 47 exist

**Severity: Medium, currently latent.**

`ml_lotto/prediction/predictor.py:53-62` builds the prediction matrix conditionally:

```python
for num in range(1, MAX_NUMBER + 1):
    if num in features_dict:
        X_pred_list.append(record)
X_pred = np.array(X_pred_list)
probabilities = pipeline.predict_proba(X_pred)[:, 1]
```

Every consumer then indexes positionally by number — `probabilities[num - 1]` in `penalties.py:41`
and `:56`, `pool_generator.py:55`, `filters.py`, `selection.py:140`. If `features_dict` were ever
missing a number the array would be 46 long and **every number above the gap would silently receive
another number's probability**. There is no length check.

It does not fire today because `extract_features_from_hmc_json` always emits all 47. But the guard
`if num in features_dict` exists precisely because absence was considered possible, and the two
halves disagree about what happens then.

**Fix.** Drop the conditional and let a missing number raise, or return a dict keyed by number
instead of a positional array. The one-line version is
`assert len(probabilities) == MAX_NUMBER` after `predict_proba`.

---

## 6. C-14 — Scraper resilience

**Severity: Medium.** Carried from the code review; partially addressed.

`scripts/scrape_lotto.py`:

- **No fallback source.** The module docstring advertises `lottery.ie` as a backup parser; only
  `irish.national-lottery.com` is implemented. `review.md` §4 specifies a two-source design.
- **No main-draw verification.** Rows are matched on a `results-DD-MM-YYYY` link and a `balls`
  list. If the archive page also carries Lotto Plus 1 / Plus 2 rows they share the draw date, and
  deduplication is by date, so whichever parses first wins. Nothing checks that a row belongs to the
  main Lotto draw.

Already fixed: 7-ball uniqueness, date-object deduplication, non-zero exit on failure.

**Fix.** Assert the row's draw-type label before accepting it, and implement the documented
fallback — or remove the claim from the docstring.

---

## 7. F-5 — `assign_bonus_to_models` divides by zero on an empty list

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

## 8. C-15a — The feature engine is rebuilt several times per run

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

## 9. F-6 — The ensemble machinery cannot be reached from the pipeline

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

## 10. C-6b — The two feature paths use different serving reference dates

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

## 11. C-17b — The legacy test files are not tests

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

## 12. F-7 — Standalone analysis scripts read a window that has never existed

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

## 12b. F-8 — The freshness target barely constrains selection

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

## 13. Improvements (not defects)

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

All four main models sit at **validation AUC 0.49–0.53 with Top-7 lift ≈ 1.0 over 60 draws**. None
of the fixes above will change that, and none should be expected to. A fair lottery is not
predictable, and the measurement now says so honestly — which is the real result of the review and
fix work.

F-1, F-2 and F-3 are worth fixing because they are the remaining places where the system reports
something that is not true. The rest is hygiene.

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
| C-16 | Non-deterministic feature column order | `extractor.py` |
| F-1 | Freshness target sized for 7 balls while a line has 6 slots | `freshness_analyzer_7_numbers.py`, `constraints.py`, `drawpick.py` |
| N-1 | Serving row was stale by one draw | `walk_forward.py`, `quickpick.py` |
| N-1b | `draws_since_bonus` was exactly inverted | `walk_forward.py` |
| N-3 | Top-K computed globally instead of per draw; overfit gap zero by construction | `model_metrics.py` |
| N-4 | Bonus-pool tie-break non-deterministic | `bonus_predictor.py` |
| N-5 | Two models could be assigned the same bonus ball | `quickpick.py` |
| — | `total_count` train/serve window mismatch | `drawpick.py` |
| — | Pipeline crashed at shutdown on the Tk matplotlib backend | `model_metrics.py`, `trend_analyzer.py` |
| — | Interaction thresholds: phantom features, vacuous splits, empty cells, mismatched recency | `feature_interaction_analyzer.py`, `interaction_thresholds.py` |
| — | Duplicate interaction script overwriting pipeline output | `feature_interaction_explorer.py` |
| — | main-6 / all-7 split corrupting the freshness selection target | `drawpick.py`, `walk_forward.py` |

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
harness described in §13 for answering whether any edge exists at all.

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
