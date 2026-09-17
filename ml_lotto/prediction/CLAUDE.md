# ml_lotto/prediction/

Turns trained model probabilities into playable lines. Writes `lottery_picks.txt`.

| File | Role |
|:--|:--|
| `predictor.py` | orchestrator - generates predictions and picks from the trained models |
| `selection.py` | `pick_line_hybrid()` - picks by HMC category and freshness bin |
| `constraints.py` | HMC and freshness pattern constraints feeding selection |
| `filters.py` | playable-ticket validation with repair |
| `penalties.py` | rank-aware diversity penalty (`diversity_penalty` in each model config) |
| `pool_generator.py` | ranked candidate pool for Model 4 |
| `ensemble.py` | majority / threshold / weighted / unanimous voting |
| `bonus_predictor.py` | 3 diverse bonus-ball predictions |
| `bonus_to_main_predictor.py` | bonus-to-main transition picks |

## The boundary that matters

**Constraints on a ticket live in `filters.py`, not in model features.** Sum 84-206, span >= 20,
2-4 odd. A model must not be taught to satisfy a rule that a filter already enforces - that spends
model capacity on a deterministic check and makes the feature set harder to reason about.

`selection.py` chooses *which* numbers by category; `filters.py` decides whether the resulting line
is playable and repairs it if not. Keep those two jobs separate.

## Rules

- **The freshness bins are not spread evenly across HMC categories**, so selection order matters.
  Currently every bin 1 and bin 2 candidate is hot; medium and cold can supply only bin 0. So
  `selection.py` takes the most-constrained category first **and** re-ranks the bins before every
  pick. Both halves are needed - ranking alone still lets hot spend the bin 0 quota that medium and
  cold have no alternative to. See F-8 in `issue.md`.
- **A model's HMC ratio can make the freshness target unreachable.** With 2 hot slots a line can hold
  at most 2 non-bin-0 numbers, whatever the target asks for. `constraints.reachable_pattern()`
  computes what a model can actually achieve and `predictor.py` passes that to selection, printing
  the shortfall. A missed bin there is a structural limit, not a selection bug - do not rewrite
  selection chasing it. See F-13.
- **`reachable_pattern()` must stay consistent with `pick_line_hybrid()`.** It predicts what
  selection will do by mirroring its ordering - scarce bins first, most-constrained category first.
  Change one and the other is wrong, and the shortfall message starts lying. It is validated against
  the achieved patterns, not against the target.
- The `hot/medium/cold/generic_count` keys mean different things per model. Models 1-3 sum to 6 -
  they are the composition of the line (4/1/1, 3/1/2, 2/2/2). **Model 4 is a pool generator**: its
  10/5/5 defines a 20-number ranked pool that `pool_generator.py` consumes, not a line. Do not
  "fix" it to sum to 6.
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
