---
name: lotto-verify
description: Verify the Irish Lotto pipeline after a change - runs the real tests, checks train/serve feature parity, validates generated tickets, and reports validation metrics against the noise floor. Use after editing anything in ml_lotto/, lotto_analysis/, drawpick.py or quickpick.py, or after adding a draw to data/irish500.csv.
---

# Verify the lotto pipeline

Checks that a change did not break train/serve parity, ticket validity, or the evaluation metrics.
Most defects in this repo were silent — nothing crashed, the numbers were just wrong — so run this
rather than eyeballing output.

## Decide what to re-run first

| What you changed | Re-run |
|:--|:--|
| `lotto_analysis/`, `drawpick.py`, `data/irish500.csv` | `drawpick.py` **then** `quickpick.py` |
| `ml_lotto/`, `quickpick.py` | `quickpick.py` only |
| Docs, tests only | neither |

`drawpick.py` writes the JSON artifacts that `quickpick.py` reads. Skipping it after an analysis
change means the ML layer trains on stale data and parity breaks silently.

```bash
python drawpick.py      # ~1-2 min
python quickpick.py     # ~2-4 min
```

Both must exit 0. `quickpick.py` exiting 3 with `Tcl_AsyncDelete` means a matplotlib backend
regression — `matplotlib.use('Agg')` must come before `import matplotlib.pyplot`.

## Run the checks

```bash
python .claude/skills/lotto-verify/verify.py
```

This runs the 37 real tests, re-derives train/serve parity from the data, validates every generated
ticket, and prints the validation metrics with the 2 SE noise floor. It exits non-zero if anything
fails.

To compare metrics against a baseline you saved before the change:

```bash
cp model_metrics/model_comparison.csv /tmp/baseline.csv     # before
python .claude/skills/lotto-verify/verify.py --baseline /tmp/baseline.csv
```

## Interpreting the result

**Parity failures are the serious ones.** Training features come from
`ml_lotto/features/walk_forward.py`; serving features for the main models come from
`ml_lotto/features/extractor.py` via `data/lotto_trigger_periods.json`. A mismatch means a model was
fitted on one distribution and applied to another. If parity fails, you changed one side only —
`recent_*` and `freshness_bin` are counted over the **main 6** balls, `rolling_*` and `total_count`
over **all 7**, and both sides must agree.

**Metric moves under the noise floor mean nothing.** The floor is ~0.031 AUC and ~0.227 Top-7
AvgCaught over the 60-draw validation window. All four models sit at chance (AUC 0.49-0.53, Top-7
lift ≈ 1.0), which is the correct answer for a fair draw. Do not report a sub-2-SE move as an
improvement, and do not tune until something exceeds it.

**A constant feature is a defect.** `test_no_constant_features.py` fails if a model trains on a
value that never changes: per-number constants leak outcome information from the validation window,
globally constant ones carry no information at all.

## After verifying

Record anything you could not fix in [`issue.md`](../../../issue.md) with file:line evidence, rather
than leaving it in conversation. Architecture and the automation plans are in
[`review.md`](../../../review.md).
