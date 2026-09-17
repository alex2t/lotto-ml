# view/pages/

The Streamlit dashboard's eight pages. `app.py` at the repo root holds the `PAGES` dict and the
navigation; each module here exposes the entry point that dict calls.

```bash
streamlit run app.py
```

| Module | Page |
|:--|:--|
| `trigger_analysis.py` | Trigger Periods Analysis |
| `draw_history.py` | Draw History |
| `statistics.py` | Statistics |
| `freshness_analysis.py` | Freshness Analysis |
| `prediction_validator.py` | Prediction Validator |
| `number_insights.py` | Number Insights |
| `pattern_comparison.py` | Pattern Comparison |
| `post_draw_analysis.py` | Post Draw Analysis |

Shared helpers are in `../utils/`: `data_loader.py` (cached artifact reads), `formatting.py`,
`hmc_calculator.py`, `freshness_calculator.py`, `anomaly_detector.py`.

## Rules

- **This layer is read-only.** Pages consume `data/*.json`, `lottery_picks.txt` and `model_metrics/`.
  Nothing here writes an artifact, trains a model, or recomputes a feature. If a page needs a number
  that does not exist, it is produced upstream in `lotto_analysis/` or `ml_lotto/`, not here.
- A page that recomputes a statistic locally will drift from the analyzer that produces it. Load it
  through `../utils/data_loader.py` instead.
- Adding a page means a module here **and** an entry in `app.py`'s `PAGES` dict.
- The dashboard shows stale numbers until `drawpick.py` and `quickpick.py` have re-run. If a page
  looks wrong, check the artifact timestamps before reading the page code.
- Existing code in this folder uses emoji in page titles and `st.markdown`. Do not add more - match
  the no-emoji rule for anything new.
