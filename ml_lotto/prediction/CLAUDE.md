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

- The `hot/medium/cold/generic_count` keys mean different things per model. Models 1-3 sum to 6 -
  they are the composition of the line (4/1/1, 3/1/2, 2/2/2). **Model 4 is a pool generator**: its
  10/5/5 defines a 20-number ranked pool that `pool_generator.py` consumes, not a line. Do not
  "fix" it to sum to 6.
- `ENSEMBLE_MODE` in `../config.py` is `False`; `ensemble.py` is reachable from
  `scripts/ensemble_predict.py` but is not part of the default `quickpick.py` run.
- Invariants are covered by `../../tests/test_selection_invariants.py` and
  `../../tests/test_prediction_alignment.py`. A filter you cannot express as a test on a generated
  line probably belongs somewhere else.
- Verify claims against `lottery_picks.txt`. Filters have been advertised in logs and docs here
  without being implemented.

## After changing anything here

`python quickpick.py`, then `/lotto-verify`, which validates every generated ticket.
