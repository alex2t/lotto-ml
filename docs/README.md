# docs/

Reference material for the Irish Lotto system. Rebuilt 2026-09-17 from the code and the artifacts,
replacing 15 files (~11,900 lines) written in late 2025 that had drifted out of date.

## What is here

| File | Audience | Status |
|:--|:--|:--|
| [`metrics.md`](metrics.md) | agent + human | current - how models are evaluated, the real numbers, the noise floor |
| [`features.md`](features.md) | agent + human | current - the feature set, group markers, interaction pipeline |
| [`models.md`](models.md) | agent + human | current - the six models, training setup, what is not enabled |
| [`json-artifacts.md`](json-artifacts.md) | agent + human | current - the ~26 JSON files, verified inventory |
| [`dashboard-manual.md`](dashboard-manual.md) | human | current - operating the Streamlit dashboard, page by page |
| [`ml-concepts.md`](ml-concepts.md) | human | background - general ML explanation, **not** project spec |
| [`implementation.md`](implementation.md) | proposal | **plan, not spec** - Dynamic Walk-Forward Feature Generation, unimplemented |
| [`feature_review.md`](feature_review.md) | agent + human | assessment of that proposal, claims checked against the code |

## Where the authority actually lies

This folder is reference, not specification. On any conflict the order is:

1. **The code and the artifacts** - `model_metrics/model_comparison.csv`, `data/*.json`,
   `lottery_picks.txt`. These are generated and cannot be out of date.
2. **The `CLAUDE.md` files** - root and per-folder. These carry the invariants and are checked on
   every change via `/lotto-verify`.
3. **This folder.**

If something here contradicts the code, the code is right and the doc is a defect. Fix it rather
than working around it.

## What is deliberately not here

- **Open defects** - `issue.md` at the repo root.
- **Architecture, scraping plan, VPS/automation plan** - `review.md` at the repo root.
- **Per-folder rules and invariants** - the `CLAUDE.md` in each folder.
- **Analysis and utility script inventories** - `analysis/CLAUDE.md` and `scripts/CLAUDE.md`.

## Removed in the 2026-09 rebuild

Recoverable from git history if needed. Superseded content is listed against each.

| Removed | Superseded by |
|:--|:--|
| `AUC_ROC_GUIDE.md` | `metrics.md` - its stated targets (AUC 0.65-0.75 "strong") were wrong and actively harmful |
| `METRICS_IMPLEMENTATION_SUMMARY.md` | `metrics.md` |
| `ML_FEATURES_REFERENCE.md` | `features.md` |
| `FEATURE_INTERACTION_IMPLEMENTATION_GUIDE.md` | `features.md` |
| `INTERACTION_FEATURES_IMPLEMENTATION.md` | `features.md` |
| `FEATURE_IMPROVEMENTS_V3.14.md` | `features.md`, `models.md` - version-specific changelog |
| `HARDCODED_VALUES_ANALYSIS.md` | `features.md` - the audit's conclusion is now a rule in the root `CLAUDE.md` |
| `JSON_DATA_REFERENCE.md` | `json-artifacts.md` |
| `ML_APPROACHES_FOR_LOTTO_PREDICTION.md` | `models.md` |
| `ENSEMBLE_VOTING.md` | `models.md` - ensemble is off in the main pipeline (`ENSEMBLE_MODE = False`) |
| `BONUS_TO_MAIN_ANALYSIS_SUMMARY.md` | `models.md` |
| `HMC_RECOMMENDATION_IMPLEMENTATION.md` | `models.md` |
| `ANALYSIS_SCRIPTS_REFERENCE.md` | `analysis/CLAUDE.md`, `scripts/CLAUDE.md` |
| `USER_MANUAL.md` | renamed to `dashboard-manual.md`, content kept |
| `ML_CONCEPTS_GUIDE.md` | renamed to `ml-concepts.md`, content kept, AUC scale annotated |

The common failure was implementation notes written at the time of a change ("add this code at line
321") that became wrong once the code moved on. **Write down the invariant, not the diff.**
