# view/pages/

**The website for players.** Its purpose is to make picking a lotto line fun, informed by a few
facts about past draws - HMC, odd/even, recent bonus balls, high numbers. It never claims a line is
likelier to win. It is Streamlit today and will be rebuilt in **React** (with spinning-style
pickers), so keep pages thin: everything they show comes from `data/*.json`, produced upstream by
`drawpick.py`, and that JSON is what the React site will read too.

**The replacement is designed in [`../../nextStep/web.md`](../../nextStep/web.md).** Its section 6 is the
completeness matrix - every section of these eight pages and where it lands in the new site. Nothing
here is deleted until that matrix is walked; this folder is the reference for what the new site must
reproduce.

The Streamlit dashboard's eight pages. `app.py` at the repo root holds the `PAGES` dict and the
navigation; each module here exposes the entry point that dict calls.

```bash
streamlit run app.py
```

| Module | Page |
|:--|:--|
| `trigger_analysis.py` | Trigger Periods Analysis |
| `draw_history.py` | Draw History |
| `statistics.py` | Statistics - includes the draw breakdown by count of numbers >= 32 (F-19); each number's odd/even affinity next to its fair-draw chance (F-38) |
| `freshness_analysis.py` | Freshness Analysis |
| `prediction_validator.py` | Prediction Validator - **where a user builds and checks their own line** |
| `number_insights.py` | Number Insights - a neutral profile of one number, no score or verdict (F-30) |
| `pattern_comparison.py` | Pattern Comparison |
| `post_draw_analysis.py` | Post Draw Analysis |

## Building your own line: the Prediction Validator

`prediction_validator.py` is the page for a user who picks their own numbers rather than playing
`lottery_picks.txt`. They type 6 numbers and get six checks, each shown against what past draws did:
odd/even ratio, sum, HMC pattern, bonus transition, range spread, and how many numbers are >= 32.

The first five are scored into an overall score. **That score measures how typical the line looks
next to past draws, not its chance of winning** - its grades and verdicts say "typical" / "unusual"
and never advise playing or regenerating (F-26, `tests/test_site_wording.py`). **The high-numbers check (F-19) is information
only**: it shows the line's count of numbers >= 32 next to the share of past draws with each count,
and a fair draw's share, so the user can decide for themselves. It is not scored because every line
is equally likely to win - the only effect of high numbers is less prize sharing with birthday-number
players. The generated picks use it per model: Models 1 and 2 hold at least 2 numbers >= 32, Model 3
has no floor (F-19 in `issue.md`).

The same breakdown is shown on its own, without entering a line, on the Statistics page.

When adding a check here, compute its statistic in `lotto_analysis/` and load it through
`../utils/data_loader.py`; the page only displays it.

Shared helpers are in `../utils/`: `data_loader.py` (cached artifact reads), `formatting.py`,
`hmc_calculator.py`, `freshness_calculator.py`, `anomaly_detector.py`.

## Rules

- **Describe, never advise.** A page may say a line or number is common, typical or unusual in past
  draws. It must not call it strong, weak, safe, risky, due or overdue, or tell the player to pick,
  avoid, include or regenerate anything - every line is equally likely to win. Do not quote a
  frequency from memory; take it from `data/*.json` (the anomaly alerts quoted "<0.5%" for a share that
  is 2%). `tests/test_site_wording.py` holds the list of banned phrases (F-26, F-28).
- **A check that cannot fire is not a safeguard.** The anomaly detector's volatility alert needed a
  value no number has ever reached, and ran for months without firing (F-29). When adding a check to
  `../utils/anomaly_detector.py`, give `tests/test_anomaly_detector.py` a line that fires it.
- **This layer is read-only.** Pages consume `data/*.json`, `lottery_picks.txt` and `model_metrics/`.
  Never `data/irish500.csv` - that is `drawpick.py`'s input, and the React site will not have it. The
  latest draw is the last of `data_loader.get_sorted_draw_dates(load_draw_history())`; Post Draw
  Analysis parsed the CSV itself until F-35. `tests/test_draw_history_numbers.py` scans `view/` for it.
  Nothing here writes an artifact, trains a model, or recomputes a feature. If a page needs a number
  that does not exist, it is produced upstream in `lotto_analysis/` or `ml_lotto/`, not here.
- A page that recomputes a statistic locally will drift from the analyzer that produces it. Load it
  through `../utils/data_loader.py` instead.
- **Read artifact fields with `data['key']`, not `.get('key', [])`.** Pattern Comparison read
  `main_numbers`, which `lotto_draw_history.json` did not have, and the empty default made it answer
  every line with "no similar draws" for ten months (F-25). A missing field must raise. After
  changing a page, render it with real input (Streamlit `AppTest`), not just a page load.
- **A past draw's hot/medium/cold is the one in force before it**, stored per ball in
  `lotto_draw_history.json` `winning_numbers_details[i]['category']`. `lotto_trigger_periods.json`
  is dated at the latest draw - use it only for the player's own line. Applying it to history made
  recent draws look all-hot (F-27).
- Adding a page means a module here **and** an entry in `app.py`'s `PAGES` dict.
- The dashboard shows stale numbers until `drawpick.py` and `quickpick.py` have re-run. If a page
  looks wrong, check the artifact timestamps before reading the page code.
- Existing code in this folder uses emoji in page titles and `st.markdown`. Do not add more - match
  the no-emoji rule for anything new.
