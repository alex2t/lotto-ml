# Review: Dynamic Walk-Forward Feature Generation

Assessment of the `implementation.md` proposal, 2026-09-18. Claims were checked against the code,
not against the document.

**The proposal was declined and the document deleted** (it lived at `docs/implementation.md` and a
byte-identical `doc/implementation.md`; recoverable from git at commit `28ac724`). This review is
kept as the record of why, so the plan is not re-proposed without new information.

**Verdict: the engineering is sound, the premise is largely spent.** Most of the value the plan
promises has either already been delivered by earlier fixes, or applies to features no model reads.
Split it into three independent pieces and take one of them.

---

## The finding that changes the case

The plan's central justification is eliminating lookahead leakage from features that "fell back to
static per-number values derived from the entire historical timeline". Six are named. Checked against
`ACTIVE_MODELS`, `BONUS_MODEL_CONFIG` and `BONUS_TO_MAIN_MODEL_CONFIG`:

| Feature | Used by a model? |
|:--|:--|
| `sum_contribution_json` | **no** |
| `range_spread_json` | **no** |
| `odd_even_json` | **no** |
| `series_recent` | **no** |
| `series_total` | **no** |
| `window_saturation_penalty` | yes - Bonus-to-Main auxiliary only (removed from it 2026-09-19, F-21; now **no**) |

**Update 2026-09-19:** all six were deleted from the ML layer in F-24, as recommended below. Their
source JSON stays for the website.

Five of the six are computed for all 47 numbers on every row and then discarded. They appear in
`extractor.py`'s `new_json_features` list, but that list is not bound to any of the four group
markers the configs actually use (`ADVANCED_PATTERN_FEATURES`, `FRESHNESS_PATTERN_WEIGHTS`,
`PAIRWISE_INTERACTIONS`, `TRIPLE_INTERACTIONS`).

The static fallback itself is real - `walk_forward.py:322-323` reads `series_total` and
`series_recent` through `static_feat.get(..., 0)`. But **a leak in a feature nothing consumes is not
a leak.** It cannot bias a model that never sees the column. Making these six point-in-time is
engineering effort spent on inert code.

The cheaper fix is deletion: stop computing five unused features per number per row, and the leak
goes with them. That is strictly less work than the plan's Phase 2 and strictly more effective.

## Benefits that have already been banked

Two of the plan's headline results are presented as future gains but are already in `issue.md`
Appendix A:

- *"Model 2's overfit gap blew out to 0.380 ... dynamic features collapse it to a healthy 0.053."*
  That is **C-15b**, resolved. Model 2's gap is 0.0534 today, in `model_comparison.csv`, before any
  of this work.
- *"Model 3's #1 feature was `series_recent` at 5.48% importance."* Past tense, and already
  remediated. Model 3's current top six are `total_count` (0.165), `max_gap_ratio` (0.162),
  `gap_variance` (0.146), `gap_consistency_score` (0.121), `appearance_volatility` (0.121),
  `recent_vs_baseline` (0.121). `series_recent` does not appear.

The Summary of Benefits table should not count these. Doing so makes the proposal look far more
valuable than it is.

## What the plan gets right

Credit where due - this is a competent document and several parts are correct and useful.

- **The UI analysis is right.** `view/` is strictly read-only over `data/*.json`,
  `lottery_picks.txt` and `model_metrics/`, with no imports from `ml_lotto`. Verified independently;
  it is recorded in `view/pages/CLAUDE.md`. The "no breakage" verdict holds.
- **C-15a is real, and understated.** The plan says the engine is built four times; production code
  builds it **five** times (`walk_forward.py:508,528`, `trainer.py:567`,
  `bonus_to_main_trainer.py:132`, `quickpick.py:616`). The singleton refactor is worth doing.
- **The prefix-sum formulation is correct** and already partly in place - `cum_all` and `cum_main`
  exist and are how `recent_*` is computed in O(1).
- **R-05, the noise fallacy, is the right risk to lead with**, and it correctly cites the 2 SE bands
  from `metrics.md` (+/-0.031 AUC, +/-0.227 Top-7).
- **The label-permutation test is the best idea in the document.** Shuffling labels within each draw
  and confirming AUC collapses to chance is a genuine leakage detector, and it is cheap. Done as
  F-17 on 2026-09-18: no model beat its shuffled-label runs - see `metrics.md`.
- The phase ordering - baseline, cleanup, implement, verify parity, retrain, smoke-test - is sensible
  and matches how the fixes in Appendix A were actually done.

## Where I disagree

**The framing treats integrity as though it implies performance.** The document states the AUC
ceiling is 0.50 for a uniform draw, then presents a benefits table reading "maximizes non-linear
pattern rejection capabilities" and "robust, un-memorized jackpot optimization". Both are integrity
statements dressed as capability. After this work every model still sits at chance, because a fair
draw has nothing to find. That is the correct outcome and the document should say so plainly rather
than implying lift.

**18,659 rows is not obviously an improvement.** The plan frames the expansion from a 47-row snapshot
to a dynamic panel as unlocking capability. It equally unlocks memorisation - the plan's own R-03
says so. More rows of a signal-free process buys more opportunity to fit noise, held back only by the
capacity constraints in `config.py` and `hyperparameter_tuning.py`. Net expected gain on validation
AUC: zero.

**The Learning-to-Rank proposal does not do what is claimed.** LTR is the most interesting idea here
and deserves a straight answer: **changing the loss function does not create signal.** NDCG@6 over a
uniform random process has the same ceiling as AUC 0.5. Optimising a ranking objective on noise
yields a well-ranked list of noise.

There is a real argument for LTR, but it is not accuracy - it is **interpretability**. The loss would
match the actual use case (choose 6 of 47), so the reported metric would mean something directly,
rather than needing Top-K lift to be derived from a binary classifier. That is a reporting
improvement, and it is worth considerably less than a seventh model's complexity in a system with six
models at chance and six open defects.

If LTR is pursued, it needs the same gate as the freshness mechanism: does it beat chance on a
walk-forward backtest? Build the gate first.

## Recommendation

Do not take this as one project. It is three, with very different value.

| Piece | Verdict | Why |
|:--|:--|:--|
| **1. C-15a singleton + drop dead columns** | **Do it** | Real logged defect, 5 instantiations, bounded work, no behavioural risk. Includes deleting the 5 unused features, which removes the leak outright. |
| **2. Point-in-time rewrite of the 6 static features** | **Descope** | 5 of 6 feed nothing. Delete them instead. Revisit only if one is wired into a model, and only after measuring. |
| **3. Learning-to-Rank model** | **Gate it** | Independent of walk-forward. Needs the backtest harness first, and the same delete-if-inside-noise rule as the freshness mechanism. |

Sequence: piece 1 now; build the backtest harness next (it is the shared prerequisite for the
freshness decision, LTR, and any future selection question); then decide 3 with evidence.

## One process note

At 493 lines with LaTeX and mermaid, this document is a plan, not a reference - it describes a diff,
and it will be wrong the moment the work starts or is descoped. `docs/CLAUDE.md` asks for the
invariant, not the diff. The durable form is an `issue.md` entry per piece plus a short decision
record of what was chosen and why.

The plan also existed as two byte-identical copies, in `doc/` and `docs/`. Both are deleted, along
with the stray `doc/` folder.
