# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An Irish Lotto (6/47 + 1 bonus) project with two audiences and one data layer:

- **The website, for players.** `view/` (Streamlit, being replaced by `frontend/`) is for people who want to have fun picking their own line
  from a few facts about past draws - hot/medium/cold numbers, odd vs even, whether a ball was
  recently a bonus, how many numbers are 32 or above. It is a toy, not a tipster: every line is
  equally likely to win, and the site says so. It is Streamlit in `view/` and **Next.js in
  `frontend/`**, where Phases 3 and 4 are both built: five destinations, wheels and a 1-47 grid to
  pick with, and a shape card that describes a line against past draws. Both run side by side -
  Streamlit on 8501, Next.js on 3000 - until the cutover deletes `view/`. The build
  document is [`nextStep/web.md`](nextStep/web.md) - the five destinations, the picker, the
  completeness matrix that says every current statistic must survive the move, and the cutover
  order for deleting `view/`.
- **The ML layer, for the owner only.** `ml_lotto/` and `quickpick.py` are a personal learning
  project - vibe coding put on a proper footing, applying the techniques from Ed Donner's Udemy
  course *AI Coder: Complete Claude Code & Coding Agents Course*. All six models sit at chance,
  which is the correct result for a fair draw (F-17). Its value is the engineering, not the
  predictions.
- **`drawpick.py` feeds both.** It turns `data/irish500.csv` into ~24 JSON artifacts in `data/` that
  the site displays and the ML layer trains on.

**What that means for the work:**

- **`data/*.json` is the website's API.** A statistic the site shows is computed in
  `lotto_analysis/` and written by `drawpick.py`, never in a page. A page only reads and displays.
  That is what lets a Next.js front end replace Streamlit without redoing any analysis.
- **The VPS runs `drawpick.py`; the owner's PC runs `quickpick.py`.** Per `plan.md`, the VPS
  (Docker, no bare-metal Python or Node) hosts the public site and rebuilds `data/*.json` when n8n
  ingests a new draw. Model training never runs there. Keep `drawpick.py` and `lotto_analysis/`
  light and free of any dependency on `ml_lotto/`.
- **Site features are about informed fun, not prediction.** Show what past draws looked like and let
  the player decide. Do not score a line as "more likely to win" - nothing is.
- **The ML layer is where engineering discipline is practised** - parity, tests, `issue.md`. It does
  not need to beat chance; it needs to be correct.

**Read [`issue.md`](issue.md) before starting work.** It is the register of known open defects with
file:line evidence, and it will save you rediscovering them. [`plan.md`](plan.md) is the roadmap:
the Next.js front end, the Docker stack on the VPS, n8n scraping of each draw (Phase A test emails,
then Phase B commits to `data/irish500.csv` and a rebuild webhook), and the single-admin data
download. `nextStep/` holds the build documents: [`n8n.md`](nextStep/n8n.md) for Phase 2
ingestion, [`web.md`](nextStep/web.md) for the Phase 3-4 website, [`chat.md`](nextStep/chat.md)
for the chat panel beside the numbers (built 2026-09-24, F-68). [`recap.md`](nextStep/recap.md) is the running
list of what is still outstanding across those documents.
[`README.md`](README.md) holds the architecture overview.

## Folder guides

Every substantial folder has its own `CLAUDE.md` holding the invariants that apply inside it. All
twelve are imported below, so they are in context from the start of every session:

@frontend/CLAUDE.md
@ml_lotto/features/CLAUDE.md
@tests/CLAUDE.md
@lotto_analysis/analyzers/CLAUDE.md
@ml_lotto/models/CLAUDE.md
@ml_lotto/prediction/CLAUDE.md
@ml_lotto/data/CLAUDE.md
@view/pages/CLAUDE.md
@scripts/CLAUDE.md
@analysis/CLAUDE.md
@demos/CLAUDE.md
@docs/CLAUDE.md

What each one covers:

| Folder guide | Covers |
|:--|:--|
| `frontend/CLAUDE.md` | the Next.js site: the five destinations, the server-side data layer, the scoring, what a page may say |
| `ml_lotto/features/CLAUDE.md` | the train/serve parity contract - the highest-risk file in the repo |
| `tests/CLAUDE.md` | the twenty-three test files and what each one guards |
| `lotto_analysis/analyzers/CLAUDE.md` | the 16 analysis phases and which JSON each writes |
| `ml_lotto/models/CLAUDE.md` | the six model configs, the noise floor, the overfit gap |
| `ml_lotto/prediction/CLAUDE.md` | selection vs filters, the playable-ticket boundary |
| `ml_lotto/data/CLAUDE.md` | artifact loading and strict validation |
| `view/pages/CLAUDE.md` | the 8 dashboard pages; read-only layer |
| `scripts/CLAUDE.md` | scraper and standalone utilities |
| `analysis/CLAUDE.md` | exploratory scripts, and the one that is in the pipeline |
| `demos/CLAUDE.md` | the feature-discovery scripts moved out of `tests/` - not tests, a source of ideas for the site |
| `docs/CLAUDE.md` | reference material - and why a number in there is never a target |

**They are imported rather than left to on-demand loading on purpose.** Claude Code will often load a
subdirectory `CLAUDE.md` by itself when a file in that subtree is opened, but that is not guaranteed -
it is unreliable when files are read through the shell (`cat`, `sed`) rather than the file tools, when
the work happens in a subagent, and when a question is answered without opening a file at all. A miss
is **silent**: the guide is simply absent and the invariant gets broken with no error. The whole cost
is ~5k tokens at session start. Do not convert these back to on-demand loading to save context.

Folders with no `CLAUDE.md`: `lotto_analysis/{core,config,utils}` and `ml_lotto/utils` are small -
covered by their parent. `data/`, `model_metrics/`, `catboost_info/` hold generated artifacts, not
code.

Reference material lives in [`docs/`](docs/README.md) - metrics, features, models, JSON artifacts,
the dashboard manual. It is reference, **not** specification: where it conflicts with the code or an
artifact, the code wins.

## Commands

```bash
python drawpick.py      # Stage 1: analysis -> writes ~25 JSON files into data/
python quickpick.py     # Stage 2: trains models, writes lottery_picks.txt + model_metrics/
streamlit run app.py    # The website (8 pages, view/pages/); Prediction Validator = build your own line
npm --prefix frontend run dev   # The Next.js site that replaces it (Phases 3-4 built)
```

`drawpick.py` must run before `quickpick.py` - the ML layer reads only the JSON artifacts, never the
CSV directly. Re-run `drawpick.py` after changing anything in `lotto_analysis/`, or the ML layer
will read stale data and train/serve parity will silently break.

### Tests

`tests/` holds only real tests: twenty-six files, 295 tests, ~60s. The Next.js site has its own
suites in `frontend/` - `npm --prefix frontend test` (374 vitest) and `npm --prefix frontend run
test:e2e` (102 Playwright, desktop and mobile); `pytest` does not run them. `pytest.ini` points pytest there, so
a bare `pytest` runs exactly those. What each file guards is in `tests/CLAUDE.md`. `/lotto-verify`
runs the same list. The old feature-discovery scripts are in `demos/` and are not tests.

```bash
python -m pytest -q                                                              # all 295
python -m pytest tests/test_no_constant_features.py -q -k "per_number_constant"   # by pattern
python -m demos.demo_interactions                                                # a demo, from the root
```

### Environment

- Package installs go through `uv`, and this machine needs the system cert store:
  `VIRTUAL_ENV=venv uv pip install --system-certs <pkg>`
- Git cannot reach GitHub with its bundled CA bundle. Prefix remote operations with
  `git -c http.sslBackend=schannel` (push, fetch, ls-remote), or set it globally once.
- `gh` is not installed, so PRs cannot be created from the CLI.
- **Do not touch or alter the `secrets.env` file.** Do not read, edit, move a value into or out
  of it, or regenerate anything in it. The owner maintains it by hand. If something seems to
  belong in it, say so and let the owner decide. **The file cannot be committed or pushed to
  GitHub** - it is in `.gitignore`; never `git add -f` it, and never remove that line.
- **Two env files, two jobs.** Compose reads `.env` for its own `${VAR}` substitution into
  `docker-compose.yml` (`UID`, `GID`). It does **not** put those values into a container. Secrets
  that a container reads - `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, `SESSION_SECRET`,
  `REBUILD_SECRET`, `OPENROUTER_API_KEY` - live in `secrets.env`, passed with `env_file` and
  `format: raw`, because Compose would expand the `$` signs in a bcrypt hash from `.env` (F-58).
  `npm run dev` outside Docker reads neither; it reads `frontend/.env.local`.
- **The owner views the site in Docker, at http://localhost:3000 - and that container serves a
  built image, not the source.** `Dockerfile.web` copies `frontend/` and runs `npm run build`
  inside the image; only `data/` is mounted. A change under `frontend/` is not on the owner's site
  until the image is rebuilt: `docker compose up -d --build --no-deps nextjs-web`. Passing
  `npm run dev`, `npm run build` or the e2e suite does not put it there. Before reporting a
  frontend change done, rebuild that container and check the change on localhost:3000.

### The chat model

The chat panel (`nextStep/chat.md`, built in `frontend/lib/chat/`) answers most questions from
prepared answers and the artifacts; only what those miss goes to one model:
**`openai/gpt-oss-120b` on OpenRouter, pinned to the Cerebras provider** for speed - the panel
does not stream, so generation time is the wait. The call is made server-side from the Next.js
route with plain `fetch`, never from Python and never from the browser; the key is
`OPENROUTER_API_KEY` in `secrets.env`. The `/cerebras` skill (`.claude/skills/cerebras/SKILL.md`)
holds the request shape and the provider settings; use it for any change to that call. Without
the key the model layer is off and the panel still answers its prepared and data questions.

## Context efficiency

- Avoid `cat` on files that could be large. Use the Read tool with offset/limit for large files, or `head`/`tail`/`grep` in bash to scope output.
- When checking logs, use `tail -n 100` or `grep` for the relevant pattern instead of dumping the whole file.
- For directory listings, avoid recursive `ls`/`find` with no filters on large trees — narrow the path or pattern first.
- If you genuinely need the full contents of something, that's fine — just don't default to it.

## Architecture

```
data/irish500.csv
  -> drawpick.py        (lotto_analysis/analyzers/*, 16 phases)
  -> data/*.json        (~24 artifacts; lotto_trigger_periods.json and
                         lotto_draw_history.json are the two that matter)
  -> quickpick.py       (ml_lotto/*)
  -> lottery_picks.txt, model_metrics/
```

Four main models in `ml_lotto/config.py` (`MODEL_1..4_CONFIG`), each with its own feature list and
HMC ratio, plus two auxiliary models (`BONUS_MODEL_CONFIG`, `BONUS_TO_MAIN_MODEL_CONFIG`). Models
1/3/4 label all 7 drawn positions; Model 2 labels the main 6 only (`exclude_bonus=True`). Details in
`ml_lotto/models/CLAUDE.md`.

### The part that matters most: train/serve parity

Training features come from `ml_lotto/features/walk_forward.py`. `ml_lotto/features/extractor.py`
builds a second row from `data/lotto_trigger_periods.json`; the main models are served
`engine.extract_serving_rows()`, which takes the engine's value wherever it has one and the
extractor's only for the rest, exactly as a training row does (F-34). Serving the extractor's row
directly fitted models on one distribution and applied them to another. This has broken repeatedly.

The full contract - which feature families are counted over the main 6 versus all 7, the deliberate
off-by-one window naming, and the only correct way to build a serving row - is in
`ml_lotto/features/CLAUDE.md`, imported above.

The package dependency direction is `ml_lotto -> lotto_analysis`; do not invert it.
`lotto_analysis/core/interaction_thresholds.py` holds the interaction split rule and recency bands
that the mining analyzer and the applying calculator **must share**. When they diverged, entire
feature families were silently always-1 or always-0.

## Working on this codebase

**Measure before refactoring.** All six models sit at chance - validation AUC close to 0.50 - which
is the correct answer for a fair draw. A change that does not move the numbers by more than the noise
floor has not helped. `model_metrics/model_comparison.csv` is the scoreboard; the 2 SE noise floor
is ~0.031 AUC and ~0.227 Top-7 AvgCaught over the 60 validation draws. A model whose train/validation
AUC gap climbs above ~0.1 has been given capacity to memorise with, and the constrained parameters
in `config.py` plus the tuning grids in `hyperparameter_tuning.py` must both be kept that way. Example figures are in `docs/metrics.md`,
the only file that quotes them - do not copy numbers from it into another file.

**Distrust silent defaults.** Most bugs found here were `.get(key, 0)` fabricating a constant for a
field that did not exist - phantom `total_count` and `recent_14` columns, vacuous interaction
thresholds, dead freshness weights. A default that hides a missing key hides a bug.

**A feature that never varies is a bug, not a feature.** `tests/test_no_constant_features.py`
enforces this. Full-history per-number constants leak outcome information from the validation
window; globally constant features carry no information at all.

**Verify claims against the artifacts.** Log lines and docs in this repo have asserted things the
code does not do (a "proportionally adjusted" freshness target that is never adjusted, filters
advertised but unimplemented, resolution matrices for fixes not made). Check `lottery_picks.txt` and
`model_metrics/model_comparison.csv` rather than trusting a summary.

**Do not use emoji in new code**, matching the user's global instruction. The engine and the ML
layer are now clear of them - `drawpick.py`, `quickpick.py`, `lotto_analysis/`, `ml_lotto/`,
`analysis/`, `scripts/` and `demos/` were stripped on 2026-09-21. `app.py` and `view/` still use
them in page titles and `st.markdown`, and are left alone because the cutover in
`nextStep/web.md` section 8 deletes that folder.

**`issue.md` is part of the work, not a report about it.** Every defect found and every defect fixed
updates it in the same change:

- **Found a bug** - give it the next free `F-n`, add a row to the **Priority summary** table in
  severity order, and write a section with file:line evidence and the failing case. This applies to
  anything noticed in passing, not only to what was asked for.
- **Fixed a bug** - delete its Priority summary row (the summary lists open items only), renumber
  the remaining sections, add it to the Appendix A table, and write up the root cause, the measured
  before/after and the tests that now cover it.
- **Planned an improvement** - it is tracked exactly like a defect: next free `F-n`, a Priority
  summary row with severity `Improvement`, its own section. When done, it moves to section 6.
- Never leave a resolved ID in the Priority summary, and never leave a found defect only in the
  conversation.

**The `CLAUDE.md` files are part of the work too.** Before reporting a task complete, check the
`CLAUDE.md` of every folder you changed a file in, plus this one, and update anything the change made
untrue. They exist to stop the next agent rediscovering an invariant, so a stale one is worse than no
file at all - it gets trusted over the source. Specifically:

| If you changed | Update |
|:--|:--|
| which JSON an analyzer writes, or added a phase | `lotto_analysis/analyzers/CLAUDE.md` |
| a counted-over convention, a window, or either feature path | `ml_lotto/features/CLAUDE.md` |
| a model config, or the constrained params and grids | `ml_lotto/models/CLAUDE.md` |
| a filter or the selection/filters boundary | `ml_lotto/prediction/CLAUDE.md` |
| added a test file, or turned a demo into one | `tests/CLAUDE.md` **and** `.claude/skills/lotto-verify/verify.py` |
| a dashboard page | `view/pages/CLAUDE.md` and `app.py` |
| anything under `frontend/` | `frontend/CLAUDE.md` |
| a documented fact - metrics, features, models, artifacts | the matching file in `docs/`, verified against the code |
| added a folder worth documenting | its own `CLAUDE.md`, an `@` import line **and** a row in the table above |

`nextStep/lottodraw.md` is how a scraped draw reaches the site: n8n posts it to the rebuild
receiver, which appends it to the CSV and regenerates the artifacts **only when the data
changed**, so a retried webhook costs nothing. Designed, not yet built.

`nextStep/vps.md` is the deployment runbook: the production overlay, the Caddy config, the two
env files and the rebuild receiver. `rebuild_webhook.py` at the root is the only network-facing
code here that writes anything - it runs `drawpick.py` for a signed request, never gets the Docker
socket, and is not proxied to the internet.

`GEMINI.md` and its copy `.gemini/GEMINI.md` restate these invariants and the roadmap for Gemini;
update them in the same change as any `CLAUDE.md` fact they repeat. `/lotto-verify` ends with this
check. State in your report which `CLAUDE.md` files you updated, or
that none needed it.
