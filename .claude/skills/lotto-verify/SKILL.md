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

This runs the 120 real tests across the twelve real test files, re-derives train/serve parity from the
data, validates every generated ticket, and prints the validation metrics with the 2 SE noise floor.
It exits non-zero if anything fails. The twelve files, and what each one guards, are listed in
[`tests/CLAUDE.md`](../../../tests/CLAUDE.md) - if you add a real test, add it to both that list and
`verify.py`.

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
AvgCaught over the 60-draw validation window. All six models sit at chance (AUC 0.50-0.55, Top-7
lift 1.01-1.12), which is the correct answer for a fair draw. Do not report a sub-2-SE move as an
improvement, and do not tune until something exceeds it.

**Watch the overfit gap as well as the AUC.** All six models sit at a train/validation AUC gap of
0.005-0.053. A gap back above ~0.1 means capacity was handed back to a model, not that it learned
something.

**A constant feature is a defect.** `test_no_constant_features.py` fails if a model trains on a
value that never changes: per-number constants leak outcome information from the validation window,
globally constant ones carry no information at all.

## After verifying

Two registers must be current before you report back. A change is not finished until both are.

### 1. The folder `CLAUDE.md` files

Each substantial folder has a `CLAUDE.md` holding the invariants that apply inside it. They are what
stops the next agent rediscovering a convention the hard way, so a stale one is worse than no file —
it gets trusted over the source.

For **every folder you changed a file in**, open its `CLAUDE.md` and check the change did not make
anything in it untrue. Then check the root [`CLAUDE.md`](../../../CLAUDE.md) the same way, and
[`GEMINI.md`](../../../GEMINI.md) with its copy `.gemini/GEMINI.md` - they restate the same
invariants and roadmap for Gemini, so a fact changed in a `CLAUDE.md` must change there too.

| If you changed | Check |
|:--|:--|
| `lotto_analysis/analyzers/` — which JSON an analyzer writes, or a phase | `lotto_analysis/analyzers/CLAUDE.md` |
| `ml_lotto/features/` — a counted-over convention, a window, either feature path | `ml_lotto/features/CLAUDE.md` |
| `ml_lotto/config.py` or `ml_lotto/models/` — a model config, params, grids | `ml_lotto/models/CLAUDE.md` |
| `ml_lotto/prediction/` — a filter, or the selection/filters boundary | `ml_lotto/prediction/CLAUDE.md` |
| `ml_lotto/data/` — an artifact added or a validation rule | `ml_lotto/data/CLAUDE.md` |
| `tests/` — a test added, or a print-script promoted | `tests/CLAUDE.md` **and** `verify.py`'s list |
| `view/` — a dashboard page | `view/pages/CLAUDE.md` **and** `app.py` |
| `scripts/` or `analysis/` | that folder's `CLAUDE.md` |
| a metric, feature, model or artifact a doc describes | the matching file in `docs/` |

A new folder worth documenting needs its own `CLAUDE.md`, an `@` import line in the root
`CLAUDE.md`, and a row in its folder-guide table. The imports are deliberate — do not convert the
folder guides back to on-demand loading.

Report which ones you updated, or state plainly that none needed it. Do not claim a file is current
without opening it.

### 2. `issue.md`

Update [`issue.md`](../../../issue.md) — it is the defect register, and a change is not finished
until it is current:

- **Anything found**, including what this run could not fix and anything noticed in passing: next
  free `F-n`, a row in the **Priority summary** in severity order, and a section with file:line
  evidence.
- **Anything fixed**: remove its Priority summary row, renumber the remaining sections, add it to
  the Appendix A table and write up root cause, measured before/after, and the covering tests.
- The Priority summary lists **open items only**. A resolved ID appearing there is itself a defect
  in the register.

Architecture is in [`README.md`](../../../README.md); the roadmap is in [`plan.md`](../../../plan.md).
