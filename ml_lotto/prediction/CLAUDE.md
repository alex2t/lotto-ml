# ml_lotto/prediction/

Turns trained model probabilities into playable lines. Writes `lottery_picks.txt`.

| File | Role |
|:--|:--|
| `predictor.py` | orchestrator - generates predictions and picks from the trained models |
| `ilp_selection.py` | `solve_line()` - picks the best line by integer linear programming |
| `constraints.py` | HMC and freshness pattern constraints feeding selection |
| `filters.py` | the ticket-rule bounds and `validate_line()`; no repair |
| `pool_generator.py` | ranked candidate pool for Model 4 |
| `wheel.py` | 4-line covering-design wheel over the pool's top 8 |
| `ensemble.py` | majority / threshold / weighted / unanimous voting |
| `bonus_predictor.py` | 3 diverse bonus-ball predictions |
| `bonus_to_main_predictor.py` | bonus-to-main transition picks |

## The boundary that matters

**Constraints on a ticket live in `filters.py`, not in model features.** Sum 84-206, span >= 20,
2-4 odd. A model must not be taught to satisfy a rule that a filter already enforces - that spends
model capacity on a deterministic check and makes the feature set harder to reason about.

`ilp_selection.py` solves for the whole line at once with `scipy.optimize.milp`: maximise the
penalised probability sum subject to the HMC quotas, the freshness target and the ticket rules,
with pre-assigned numbers fixed in. The rule bounds (`MIN_SUM`, `MAX_SUM`, `MIN_SPAN`, `MIN_ODD`,
`MAX_ODD`) are constants in `filters.py`, shared by the solver and `validate_line()`. The solver
returns a line meeting every constraint or raises - there is no repair pass, which is what used to
let a constraint look satisfied while not binding (F-8, F-14).

## Rules

- **Constraints are declarative.** Add or change a rule as a constraint in `solve_line()`, never as a
  post-hoc fix-up of its output. An infeasible combination must raise, not return a short or
  rule-breaking line.
- **The ticket rules apply to the whole ticket**, pre-assigned numbers included. HMC quotas and
  the freshness target count the selected numbers only, as `predictor.py` adjusts the quotas for
  what is pre-assigned.
- **Diversity is one lexicographic rule.** `solve_line` charges `PENALTY_COST` (= `LINE_SIZE`) per
  number already on an earlier line, which exceeds any difference in probability sums, so a reused
  number is taken only when no feasible line avoids it. There is no percentage penalty and no
  per-model setting - two stacked mechanisms made the configured one meaningless (F-16).
- **A model's HMC ratio can make the freshness target unreachable.** With 2 hot slots a line can hold
  at most 2 non-bin-0 numbers, whatever the target asks for. `constraints.reachable_pattern()`
  computes what a model can actually achieve and `predictor.py` passes that to the solver, printing
  the shortfall. A missed bin there is a structural limit - see F-13. The freshness mechanism was
  kept on evidence (F-18): bin 2 numbers are drawn ~11% more often, p = 0.031 - weak, and small in
  effect. Re-run `analysis/freshness_hit_rate.py` as draws accumulate; if p rises above 0.05, delete
  the enforcement rather than tuning it.
- The `hot/medium/cold/generic_count` keys mean different things per model. Models 1-3 sum to 6 -
  they are the composition of the line (4/1/1, 3/1/2, 2/2/2). **Model 4 is a pool generator**: its
  10/5/5 defines a 20-number ranked pool that `pool_generator.py` consumes, not a line. Do not
  "fix" it to sum to 6.
- **Wheel lines bypass `filters.py` on purpose.** `wheel.py` turns the top 8 of Model 4's pool into
  4 lines covering every 3-subset: 3+ winners in the top 8 guarantees a match-3 (~5.3% of draws).
  Repairing one line would break the cover, so they are written as `Wheel Line n:` - a format
  `/lotto-verify` does not parse as a model ticket. It is variance management, not an edge: 4
  unrelated lines catch a match-3 more often (~7.2%) at the same expected value.
- `ENSEMBLE_MODE` in `../config.py` is `False`; `ensemble.py` is reachable from
  `scripts/ensemble_predict.py` but is not part of the default `quickpick.py` run.
- Invariants are covered by `../../tests/test_selection_invariants.py` and
  `../../tests/test_prediction_alignment.py`. A filter you cannot express as a test on a generated
  line probably belongs somewhere else.
- **Build serving rows with `feat[col]`, never `feat.get(col, 0)`.** The column list is the exact one
  the pipeline was fitted on, so a silent 0 applies a coefficient fitted on real values to a constant
  and breaks parity with no error. Both sites - `predictor.py` and `bonus_predictor.py` - carry a
  comment saying so; do not "harden" them back into defaults. See F-9 in `issue.md`.
- Verify claims against `lottery_picks.txt`. Filters have been advertised in logs and docs here
  without being implemented.

## After changing anything here

`python quickpick.py`, then `/lotto-verify`, which validates every generated ticket.
