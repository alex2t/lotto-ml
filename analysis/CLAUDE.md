# analysis/

Exploratory and one-off analysis scripts. **One of them is load-bearing; the rest are not.**

## The one in the pipeline

`bonus_analysis.py` is imported by `drawpick.py` (Phase 11) and writes
`data/lotto_statistics_analysis.json`, which Phase 12 then reads. It is production code that
happens to live outside `lotto_analysis/`. Treat a change to it exactly as a change to an analyzer:
re-run `drawpick.py` and `quickpick.py`.

This is the only cross-folder step in the pipeline. If you are tidying the package layout, this is
the import to be careful with.

## Standalone scripts

Run by hand, not imported by the pipeline:

| File | Produces |
|:--|:--|
| `feature_interaction_explorer.py` | interaction candidates; the analyzer in `lotto_analysis/analyzers/` is what actually mines them for production |
| `correlation_matrix_analyzer.py` | `data/analysis/lotto_correlation_matrix.json`, `lotto_correlation_summary.csv` |
| `feature_stability_scorer.py` | `data/analysis/lotto_feature_stability.json`, rankings CSV |
| `gap_pattern_analyzer.py` | gap statistics |
| `trend_analyzer.py` | `trend_analysis/*.csv` |
| `bonus_to_main_analysis.py`, `generate_bonus_to_main_json.py` | `data/analysis/bonus_to_main_analysis.json` |
| `validate_bonus.py` | checks the `was_recent_bonus` feature is live |
| `freshness_hit_rate.py` | F-18: hit rate by freshness bin, chi-square; decides whether the freshness constraint stays |

`trend_analysis/` holds their CSV output, which is regenerated, not source.

**Running them.** Invoke from the project root - `python analysis/<script>.py`. Most resolve their
input paths relative to either the root or this folder, but the root is the reliable choice. They
read `data/*.json`, so `drawpick.py` must have run first.

## Rules

- Output here is exploratory evidence, not an artifact the ML layer reads. Only `data/*.json` written
  by `drawpick.py` feeds `quickpick.py`.
- Findings from these scripts belong in `issue.md` with file:line evidence, not in a new markdown
  file at the repo root.
