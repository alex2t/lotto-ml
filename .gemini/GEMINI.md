# GEMINI.md

This document serves as the comprehensive architectural reference and operational guide for Google Gemini / Antigravity agents working in the `lotto-ml-system` repository.

---

## 1. Project Purpose & High-Level Philosophy

The **Irish Lotto ML System** is an end-to-end lottery analysis, machine learning prediction, and visual inspection suite tailored for the Irish National Lottery (6/47 main numbers + 1 bonus ball).

The project is structured around **two distinct audiences fed by a single data pipeline**:

1. **The Web Dashboard (`view/`, `app.py`) — For Players & Fun**:
   - An 8-page Streamlit application, and its **built** Next.js replacement in `frontend/`: five destinations (Home, Pick, Explore, Numbers, Review), a picker with wheels and a 1-47 grid, and a shape card that describes a line against past draws. Both run side by side - Streamlit on 8501, Next.js on 3000 - until the cutover in `nextStep/web.md` section 8 deletes `view/`.
   - Allows users to explore factual historical statistics (hot/medium/cold recency bands, odd/even splits, sum distributions, freshness patterns, bonus-to-main transitions, and high number frequencies >= 32).
   - Features an interactive **Prediction Validator** where users can build and validate their own ticket lines against historical distributions.
   - **Crucial Invariant**: It is an informed toy, **never a tipster**. In a fair lottery, every combination has an identical probability of being drawn. The site explicitly states this and never claims a line is "more likely to win."

2. **The ML Engineering Layer (`ml_lotto/`, `quickpick.py`) — For the System Author**:
   - A rigorous machine learning and software engineering sandbox applying the principles from Ed Donner's *AI Coder: Complete Claude Code & Coding Agents Course*.
   - Evaluates six models (logistic regression, random forest, XGBoost, CatBoost, and two auxiliary regressors).
   - **The Honest Baseline**: All models sit at chance (validation AUC close to 0.50 over 60 held-out draws; example figures only in `docs/metrics.md`). A 20-run label-permutation test (`python quickpick.py --permutation-check 20`) confirms that no model outperforms shuffled noise ($p = 0.095\text{--}0.476$).
   - The value of this layer is **engineering discipline, train/serve parity, strict validation, and declarative constraint satisfaction**, not gambling advantage.

3. **The Data Core (`drawpick.py`)**:
   - Ingests historical draws from `data/irish500.csv` and executes 16 sequential statistical analysis phases.
   - Generates ~24 validated JSON artifacts in `data/` and `data/analysis/`.
   - **`data/*.json` is the sole API boundary**: Pages in `view/`, the Next.js site in `frontend/` and models in `ml_lotto/` read only these JSON artifacts, never `data/irish500.csv` directly. The one exception is the admin download route, where the owner retrieves their own input file.

---

## 2. System Architecture & Data Flow

```
┌─────────────────────────┐
│    data/irish500.csv    │ ◄── [scripts/scrape_lotto.py]
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│       drawpick.py       │ (16 Statistical Analysis Phases via lotto_analysis/)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     data/*.json         │ (~24 JSON artifacts; lotto_trigger_periods.json
└──────┬───────────┬──────┘  and lotto_draw_history.json are the two primary files)
       │           │
       │           ▼
       │  ┌─────────────────────────┐
       │  │      quickpick.py       │ (Point-in-time walk-forward features, model fitting,
       │  └────────┬────────────────┘  hyperparameter tuning, MILP line selection)
       │           │
       │           ▼
       │  ┌─────────────────────────┐
       │  │    lottery_picks.txt    │
       │  │     model_metrics/      │
       │  └─────────────────────────┘
       ▼
┌─────────────────────────┐
│        app.py           │ (8-Page Streamlit UI in view/pages/)
│   (view/pages/*.py)     │ (Read-only consumer of JSON and metrics)
└─────────────────────────┘
```

---

## 3. Critical Codebase Invariants (Must Never Break)

### 3.1. Train/Serve Parity Contract (`ml_lotto/features/`)
This is the single highest-risk invariant in the entire repository. Training features and serving features are produced by two separate code paths:

| Context | Engine / Path | Source |
|:---|:---|:---|
| **Training** | `PointInTimeFeatureEngine` (`ml_lotto/features/walk_forward.py`) | Recomputed point-in-time from `data/lotto_draw_history.json` |
| **Serving (Main Models)** | `engine.extract_serving_rows()` | The engine's next-draw row; `ml_lotto/features/extractor.py`'s row (from `data/lotto_trigger_periods.json`) only for features the engine does not compute (F-34) |

* **Counted-Over Conventions**:
  - `recent_4`, `recent_5`, `recent_9`, `recent_24`, and `freshness_bin` are counted over the **main 6 balls** only.
  - `rolling_rate_*`, `rolling_trend_*`, `total_count`, and gap statistics are counted over **all 7 balls** (including bonus).
* **Off-By-One Window Naming by Design**:
  - `recent_4` counts over 5 draws (`last_4` in JSON).
  - `recent_9` counts over 10 draws (`last_9` in JSON).
  - `recent_24` counts over 25 draws (`last_24` in JSON).
* **Serving Row Construction**: Only `engine.extract_features_for_next_draw()` ($t = N$) builds a valid serving row. `extract_features_at_draw(N-1)` drops the latest draw. The main models are served `engine.with_base_features(features_dict).extract_serving_rows()`, built exactly like a training row - never the extractor's row alone (F-34). The Bonus-to-Main model builds training and serving rows with the same two functions, `bonus_to_main_row()` and `bonus_window_positions()`, over the engine (F-40).
* **One Serving Date**: Every serving path counts days to `engine.next_draw_date` (the next draw on the current Mon/Wed/Sat schedule), matching training rows dated at their own draw. `category` is derived with `hmc_category()` in both paths, never read from the JSON. Never use `datetime.now()` (C-6b).
* **No Silent Defaults**: Never use `feat.get(key, 0)` for feature values. A missing key indicates a distribution mismatch or missing column; let it fail loudly with `feat[col]`.
* **Single Engine Instance**: `quickpick.py` instantiates one `PointInTimeFeatureEngine`, and models consume views via `engine.with_base_features()`.

### 3.2. Statistical Analysis Invariants (`lotto_analysis/`)
* **Shared Thresholds**: `ml_lotto/features/interactions.py` must import split thresholds and recency bands from `lotto_analysis/core/interaction_thresholds.py`. The dependency direction is strictly `ml_lotto -> lotto_analysis`.
* **Pure Determinism (No Clock, No Set Randomness)**:
  - No `datetime.now()` in computed feature values. Recency must always be measured relative to the latest draw date in the dataset.
  - Never call `max()`, `min()`, or `next()` on unordered `set` or `dict` items where ties can occur; sort explicitly first.
* **No Analysis Split**: `drawpick.py` intentionally computes statistics across all available draws because its artifacts represent serving-time state for the upcoming draw. The 0.85 train/val split exists exclusively within `quickpick.py` for model fitting.

### 3.3. Model Capacity & Evaluation Constraints (`ml_lotto/models/`)
* **Noise Floor (2 Standard Errors over 60 draws)**:
  - **AUC**: $\pm 0.031$
  - **Top-7 AvgCaught**: $\pm 0.227$ (expected chance baseline: ~1.043 numbers)
  - Any metric change smaller than this floor is noise.
* **Overfit Gap Guard**:
  - Train AUC minus Validation AUC must stay below ~0.10. Current values are in `model_metrics/model_comparison.csv`; do not copy them into this file.
  - Widening model capacity or tuning grids will simply memorise noise. `tests/test_model_capacity.py` actively guards against this.

### 3.4. Declarative Line Selection & Mathematical Filter Bounds (`ml_lotto/prediction/`)
* **Integer Linear Programming (MILP)**: `ml_lotto/prediction/ilp_selection.py` uses `scipy.optimize.milp` to solve for tickets holistically. Procedural greedy picking and post-hoc repair passes have been completely eliminated (F-14).
* **Ticket Filter Bounds (`filters.py`)**:
  Empirical and mathematical bounds derived from Irish Lotto 6/47 history:
  - **Sum Constraint ($84 \le \text{Sum} \le 206$)**: The sum of the 6 drawn numbers follows an approximately normal distribution ($\mu \approx 144\text{--}146$, $\sigma \approx 30.5$). The range $84\text{--}206$ represents $\mu \pm 2\sigma$, capturing $\sim 95.5\%$ of all historical draws. Extreme tickets with sums $< 84$ (e.g. $[1, 2, 3, 4, 5, 6] = 21$) or $> 206$ (e.g. $[42, 43, 44, 45, 46, 47] = 267$) fall in the extreme $< 2.5\%$ tails and are rejected as unrealistic.
  - **Span Constraint ($\text{Max} - \text{Min} \ge 20$)**: The difference between the highest and lowest ball must be at least 20. This prevents extreme clustering (e.g. $[10, 11, 12, 13, 14, 15]$ with a span of 5), ensuring natural dispersion across the 1–47 range.
  - **Odd/Even Balance ($2 \le \text{Odd} \le 4$)**: The line must contain 2, 3, or 4 odd numbers (splits 2:4, 3:3, or 4:2), representing $78.7\%$ of historical draws. Unbalanced lines (6:0, 5:1, 1:5, 0:6) are filtered out.
* **High Numbers ($\ge 32$) Policy (F-19)**:
  - Model 1 & Model 2: Floor of at least 2 numbers $\ge 32$ (based on empirical fact that 71% of draws hold 2+ high numbers, reducing prize sharing with birthday-number players).
  - Model 3: No floor (unconstrained probabilities decide).
* **Diversity Rule**: Flat penalty of 6 (`LINE_SIZE`) charged per number already selected in an earlier model's line.
* **Model 4 Wheeling**: Model 4 outputs a 20-number candidate pool (`10H / 5M / 5C`). `ml_lotto/prediction/wheel.py` wheels the top 8 numbers into 4 covering lines ($C(8, 6, 3) = 4$), guaranteeing at least one Match-3 if 3+ winning numbers appear in the top 8.

### 3.5. Web Dashboard Read-Only Contract (`view/pages/`)
* Streamlit pages consume `data/*.json`, `lottery_picks.txt`, and `model_metrics/`.
* Pages **never** compute features, train models, or write artifacts.
* Avoid emojis in new code.

---

## 4. Summary of the Six Models

| Config | Model Name | Algorithm | Ball Targets | H / M / C Ratio | Min $\ge 32$ | Purpose |
|:---|:---|:---|:---|:---:|:---:|:---|
| `MODEL_1_CONFIG` | Momentum Specialist | Logistic Regression | All 7 balls | 4 / 1 / 1 | 2 | Momentum, recency, rolling rates, interactions |
| `MODEL_2_CONFIG` | Jackpot Optimizer | Random Forest | Main 6 only | 3 / 1 / 2 | 2 | Long-term distribution stability (`exclude_bonus=True`) |
| `MODEL_3_CONFIG` | Complexity Explorer | XGBoost | All 7 balls | 2 / 2 / 2 | 0 | Non-linear interaction exploration |
| `MODEL_4_CONFIG` | Conservative Pool Generator | CatBoost | All 7 balls | 10 / 5 / 5 | - | Emits 20-number pool, wheeled into 4 ticket lines |
| `BONUS_MODEL_CONFIG` | Bonus Ball Predictor | Logistic Regression | Bonus only | - | - | Selects 3 diverse bonus ball predictions |
| `BONUS_TO_MAIN_MODEL_CONFIG` | Bonus-to-Main Transition | Logistic Regression | Main from Bonus | - | - | Predicts bonus balls transitioning to main |

---

## 5. Defect Tracking & Single Source of Truth (`issue.md`)

All defects, active issues, and planned improvements are tracked **exclusively in [`issue.md`](issue.md)** to prevent multi-document duplication and synchronization drift. Always consult `issue.md` before beginning work.

### Register Discipline
- **Found a defect**: Allocate next sequential `F-n`, add a row to Priority Summary in `issue.md`, and document file:line evidence.
- **Fixed a defect**: Remove from Priority Summary, add to Appendix A of `issue.md` with root cause, before/after evidence, and tests.
- **Evidence before change**: Measure baselines before touching code. Never state a claim without artifact backing.

---

## 6. System Automation & Deployment Roadmap (`plan.md`)

The roadmap is maintained **exclusively in [`plan.md`](plan.md)** to prevent documentation divergence. The architecture overview is in [`README.md`](README.md). `plan.md` covers:
- Phase 1: Docker for the Python data engine; `drawpick.py` writes the JSON artifacts into a shared volume.
- Phase 2: n8n scraping on Mon/Wed/Sat at 21:05, built in the existing n8n instance - Phase 2A sends test emails, Phase 2B commits new draws to `data/irish500.csv` (inserted after the header; the file is newest-first) and calls a VPS rebuild webhook. The node-by-node design is `nextStep/n8n.md`.
- Phase 3 (done 2026-09-21): the Next.js foundation in `frontend/` - Next.js 16, TypeScript, Tailwind 4; `lib/data/` reading the mounted artifacts with an mtime cache; a signed-cookie admin login; and `/api/download/data` streaming the bundle. The `nextjs-web` image is built and runs beside Streamlit, non-root, with the artifacts mounted read-only.
- Phase 4 (done 2026-09-21): the UI - the five destinations, `lib/scoring/` describing a line in the fixed vocabulary typical / uncommon / unusual with the equal-chance sentence rendered beside it, and the wording guard that replaces `tests/test_site_wording.py` (a source lint plus a Playwright pass). The section 6 completeness matrix is walked and signed off.
- Phase 4: migrating the 8 Streamlit pages to Next.js, including the interactive Prediction Validator.
- Phases 3-4 are designed node by node in `nextStep/web.md`: five destinations (Home, Pick, Explore, Numbers, Review), the completeness matrix that keeps every current statistic, the wording test that must replace `tests/test_site_wording.py`, and the cutover order for deleting `view/`.
- Phase 5: VPS deployment with Docker Compose and Caddy/Nginx SSL.

Separation of concerns: the VPS runs only `drawpick.py` and the public site; `quickpick.py` (model training) runs on the owner's PC. Keep `lotto_analysis/` light and free of any dependency on `ml_lotto/`.

---

## 7. Execution Commands & Runbook

Always execute commands inside the project's virtual environment:

### Windows PowerShell
```powershell
# Run statistical analysis and write ~24 JSON artifacts
.\venv\Scripts\python.exe drawpick.py

# Train models, evaluate metrics, and generate lottery_picks.txt
.\venv\Scripts\python.exe quickpick.py

# Run 20-fold label permutation verification
.\venv\Scripts\python.exe quickpick.py --permutation-check 20

# Launch the Streamlit dashboard
.\venv\Scripts\streamlit.exe run app.py

# Launch the Next.js site (reads the same data/*.json)
npm --prefix frontend run dev

# The Next.js site's own tests: vitest over the data layer and the scoring, then Playwright
npm --prefix frontend test
npm --prefix frontend run test:e2e

# Execute all 23 test files (241 tests, ~50s) - pytest.ini limits pytest to tests/
.\venv\Scripts\python.exe -m pytest -q

# Run the comprehensive lotto verification suite
.\venv\Scripts\python.exe .claude/skills/lotto-verify/verify.py
```

### Linux / VPS
```bash
source venv/bin/activate
python drawpick.py
python quickpick.py
streamlit run app.py
python .claude/skills/lotto-verify/verify.py
```

---

## 8. Directory Guide & Repository Map

| Directory | Key Files | Responsibility |
|:---|:---|:---|
| **`lotto_analysis/`** | `drawpick.py`, `analyzers/` | 16 analytical phases computing statistics over `data/irish500.csv` to emit JSON artifacts. |
| **`ml_lotto/data/`** | `loader.py` | Strictly loads and validates `data/*.json`. Raises immediately on missing keys. |
| **`ml_lotto/features/`** | `walk_forward.py`, `extractor.py` | Point-in-time training engine & serving feature extractors. Governs the train/serve parity contract. |
| **`ml_lotto/models/`** | `trainer.py`, `pipelines.py`, `hyperparameter_tuning.py` | Model architectures, training loops, calibration, and constrained parameter spaces. |
| **`ml_lotto/prediction/`** | `ilp_selection.py`, `filters.py`, `wheel.py`, `predictor.py` | MILP ticket selection, constraint verification, candidate pooling, and wheeling designs. |
| **`view/pages/`** | `app.py`, `view/pages/*.py` | 8-page Streamlit web dashboard. Strictly read-only; displays facts for user enjoyment. |
| **`frontend/`** | `lib/data/`, `lib/scoring/`, `app/`, `proxy.ts` | The Next.js site, Phases 3-4 built. Reads `data/*.json` server-side, computes nothing, never sends the 4.4 MB draw history to the browser, and describes a line rather than advising on it. |
| **`scripts/`** | `scrape_lotto.py`, `train_with_all_features.py` | Independent utilities; web scraper for new draw ingestion. |
| **`analysis/`** | `bonus_analysis.py`, exploratory scripts | Phase 11 statistical analysis; exploratory data science scripts. |
| **`tests/`** | 23 test files, nothing else (see Section 7) | Guards parity, model capacity, invariants, filter rules, scraper integrity, and wheel coverage. |
| **`demos/`** | `demo_*.py` | Feature-discovery scripts moved out of `tests/` (C-17b). Not tests; run with `python -m demos.<name>`. Never write to `model_metrics/` or `data/`. |
| **`docs/`** | `metrics.md`, `features.md`, `models.md`, `json-artifacts.md` | Reference documentation. Code and artifacts always supersede docs in conflicts. |
| **`data/`** | `irish500.csv`, `*.json` | Ground-truth historical draws and generated analytical artifacts. |
| **`model_metrics/`** | `model_comparison.csv`, `*.png` | Evaluation scoreboards, ROC/PR curves, and calibration plots. |

---

## 9. Guidelines for Working with this Codebase

1. **Verify Before and After**: Always run `.\venv\Scripts\python.exe .claude/skills/lotto-verify/verify.py` before and after modifying logic.
2. **Order of Operations**: If modifying `lotto_analysis/`, you must re-run `drawpick.py` before `quickpick.py`. Failing to do so causes silent parity drift.
3. **Respect the Noise Floor**: Never optimize against differences smaller than 0.031 AUC or 0.227 Top-7 AvgCaught. The lottery is a uniform physical random process.
4. **Single Source of Truth**: Keep defects exclusively in `issue.md` and roadmap exclusively in `plan.md`. Update corresponding folder `CLAUDE.md` and `GEMINI.md` invariants when logic changes.
