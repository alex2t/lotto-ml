# docs/

Reference material. **This folder is not specification.** Start from [`README.md`](README.md) for the
index.

## Precedence

On any conflict between this folder and reality, reality wins, in this order:

1. The code and the generated artifacts (`model_metrics/model_comparison.csv`, `data/*.json`,
   `lottery_picks.txt`) - these cannot be stale.
2. The `CLAUDE.md` files, root and per-folder - these carry the invariants and are checked on every
   change.
3. This folder.

A doc here that contradicts the code is a defect in the doc. Say so and fix it; do not change working
code to match a document.

## Do not take a number from here as a target

The single most damaging thing a stale doc did in this repo was state that AUC 0.65-0.75 was a
"strong result showing genuine pattern detection". Real validation AUC is **close to 0.50** for all
six models (example figures in `metrics.md`), and that is the **correct** answer - Irish Lotto is a fair draw. An agent that treats a
documented number as a goal will close the gap the only way it can: by handing models capacity to
memorise with, widening the overfit gap and breaking exactly what `tests/test_model_capacity.py`
protects.

Performance figures live in `metrics.md`, sourced from `model_comparison.csv`. If a figure appears
anywhere else in this folder, verify it against that CSV before acting on it.

`ml-concepts.md` is general ML background written for the owner. Its scales and examples are generic
teaching material and describe ML in general, **not** this system.

## Which file answers what

| Question | File |
|:--|:--|
| How are models evaluated? What are the real numbers? | `metrics.md` |
| What features exist? How do interactions work? | `features.md` |
| What are the six models? What is switched on? | `models.md` |
| What JSON files exist and what is in them? | `json-artifacts.md` |
| How does a person use the dashboard? | `dashboard-manual.md` |
| What is logistic regression / XGBoost? | `ml-concepts.md` (general background) |

Not here: open defects (`issue.md`), architecture (`README.md`), roadmap (`plan.md`), per-folder
invariants (each folder's `CLAUDE.md`).

## Writing or updating a doc here

- **Write down the invariant, not the diff.** Every file removed in the 2026-09 rebuild failed the
  same way: it recorded what was changed at the time ("add this code after line 321") and became
  wrong the moment the code moved. Describe what must always be true instead.
- **Verify before you write.** Every claim in `metrics.md`, `features.md`, `models.md` and
  `json-artifacts.md` was checked against the code or the artifacts at the time of writing. Match
  that standard - do not carry a number across from another document.
- **Date any claim that could age**, and say what it was verified against.
- Keep it short. A long document that is 80% right is worse than a short one that is entirely right,
  because nobody can tell which 20% to distrust.
- Docs are updated **last**, after the code change is made and verified.
