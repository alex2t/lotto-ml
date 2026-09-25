@AGENTS.md

# frontend/

**The Next.js site that replaces the Streamlit dashboard.** Phases 3 and 4 are built. The build
document is [`../nextStep/web.md`](../nextStep/web.md); its section 6 is the completeness matrix and
its section 8 is the cutover order that ends with deleting `view/`. **`view/` is still the live site
until that cutover - do not delete it.**

Next.js 16 (App Router) + TypeScript + Tailwind 4, `output: 'standalone'`. Icons `lucide-react`.

```bash
npm run dev                # http://localhost:3000, reads ../data
npm run build              # standalone build, what Dockerfile.web ships
npm test                   # vitest: the data layer, the scoring, the wording lint
npm run test:e2e           # playwright: the site as someone meets it, desktop and mobile
npm run test:integration   # the real chain: append a row, run drawpick.py, serve the new draw
```

## The five destinations

| Route | What someone came to do |
|:--|:--|
| `/` | see the latest draw, and whether the data has caught up |
| `/pick` | build a line - wheels, hand, shake, shape, surprise - and see how it compares |
| `/explore` | Draws, Statistics, Freshness, Patterns |
| `/numbers`, `/numbers/[n]` | the 47-number table with its filter rail, and one number's fact sheet |
| `/review` | the last draw; its admin half compares the generated lines |

## The layers

| Path | Role |
|:--|:--|
| `lib/data/artifacts.ts` | reads `DATA_DIR`'s JSON, cached per file mtime; `requireKey()` throws on a missing key |
| `lib/data/draws.ts`, `explore.ts` | the draw history: pages, filters, one number's appearances, similar draws |
| `lib/data/numbers.ts`, `pool.ts`, `table.ts`, `dossier.ts` | the 47 numbers, joined across artifacts |
| `lib/data/distributions.ts`, `hmc.ts` | the distributions a line is described against |
| `lib/data/ranged.ts` | the countable distributions over a date range, counted from the draw history |
| `lib/pick/line-image.ts` | draws a finished line as a PNG, in the browser |
| `lib/data/schedule.ts`, `staleness.ts` | the next draw, and the three freshness states |
| `lib/data/picks.ts` | `lottery_picks.txt`, which is absent on the VPS by design |
| `lib/scoring/` | `line.ts` describes a line, `notes.ts` states facts about it, `bands.ts` mirrors the analyzer's bins |
| `lib/pick/filters.ts` | what the wheels contain |
| `lib/pick/current-line.ts` | the tray's line and the way of picking on screen, published by `Picker` for the chat panel |
| `components/pick/` | `Picker`; `ShakeBag` the bag and its three steps; `BagFilters` the filter cards, each saying what it does, what to look for and how many numbers it takes out |
| `lib/chat/` | the chat panel (`../nextStep/chat.md`): `prepared.ts` layer 0 and the suggestions per page and per picking method, `figures.ts` today's figures for a prepared answer about a picker filter, `intents.ts` layer 1, `cache.ts` layer 2, `openrouter.ts` + `prompt.ts` layer 3; `context.ts` the page fact sheet, `guard.ts` the runtime `ADVICE` scan, `budget.ts` the limits, `answer.ts` the four layers in order |
| `lib/advice.json` | the banned-word list - the one copy the source scan, the rendered scan, the chat prompt and the chat guard all read |
| `components/chat/` | `ChatLauncher` in the nav, `ChatPanel` the native `<dialog>` sheet |
| `app/api/` | `draws`, `numbers`, `distributions`, `schedule`, `validate`, `chat` (public); `login`, `logout`, `download/data` (admin) |
| `proxy.ts` | guards `/api/download/*`; everything a player does is public |
| `test/fixtures/` | trimmed artifacts, rebuilt by `test/make-fixtures.py` |

## Rules

- **The site computes nothing.** Every figure comes from `data/*.json`, written by `drawpick.py`.
  A figure that does not exist there is added in `lotto_analysis/` and written by `drawpick.py`,
  never calculated in a component - which is what happened to the six-ball HMC distribution: it is
  now `lotto_odds_results.json` `hmc_6`, and `lib/data/hmc.ts` reads it (F-59, F-60).
- **Read artifact fields with `requireKey()`, never a default.** An empty default made a Streamlit
  page answer "no similar draws" for ten months (F-25). A missing key is a bug; let it throw.
- **The draw history is 4.4 MB and never goes to the browser whole.** It is read on the server and
  exposed through API routes that return a page, one number's appearances or an aggregate.
- **Never read `data/irish500.csv`.** The one exception is `app/api/download/data/route.ts`, where
  the owner retrieves their own input file. `../tests/test_draw_history_numbers.py` scans for it.
- **Describe, never advise.** Common, typical, unusual - never strong, weak, safe, risky, due or
  overdue, and never tell anyone to pick, avoid or regenerate. The verdict vocabulary is fixed to
  **typical / uncommon / unusual** and the equal-chance sentence is rendered with it by
  `ShapeCard`, so the wording lives in one component. `test/wording.test.ts` scans every source
  file for the banned list and `test/e2e/site.spec.ts` scans every rendered page. The list is
  `lib/advice.json` - `../tests/test_site_wording.py` `ADVICE`, verbatim - and it is JSON so
  that it is not itself a scanned source; anything that needs the words reads that file. It bans ordinary words too - "strongest
  trend" failed both guards and became "biggest change".
- **A band boundary belongs to the analyzer, not here.** `lib/scoring/bands.ts` mirrors
  `lotto_analysis/config/config.py` and `utils/output_generator.py`, including that the spread bins
  are half-open while their labels read as inclusive: "20-25" is 20 to 24, and 25 is in "25-30".
- **A six-number line needs a six-ball distribution.** `lotto_odds_results.json` holds both of
  each: `hmc` and `draw_range` span all seven balls, `hmc_6` and `draw_range_6` the main six.
  Reading `hmc` for a line matched nothing at all (F-59); reading `draw_range` matched the wrong
  band quietly, because the keys are shared (F-63). Always the `_6` one.
- **A date range is counted, and the counting is held to the artifact.** No artifact can hold every
  possible range, so `lib/data/ranged.ts` counts draws - and only counts draws, never a statistic
  with a test or a correction in it. `test/ranged.test.ts` recounts the whole history and asserts
  every figure matches the artifact's own. That test is what found F-63; if it ever fails, the
  counting and the analyzer have drifted and the analyzer is right.
- **The root layout reads no artifact.** `data/` is a runtime mount and is absent while the image
  builds, so anything the layout read would break Next's prerender of the error pages.
- **The admin account lives in the repo-root `secrets.env`, not `.env`.** Compose reads `.env` for
  its own variable substitution and would expand the `$` signs in a bcrypt hash (F-58).
  `secrets.env.example` has the generator commands. `frontend/.env.example` is for `npm run dev`
  outside Docker.
- **No login for anything a player does.** `proxy.ts` lists the admin surface explicitly rather
  than protecting by default, so an admin failure can never take the site down.
- **A check that cannot fire is not a safeguard** (F-29). Every note in `lib/scoring/notes.ts` has
  a line in `test/scoring.test.ts` that fires it.
- **Contrast is measured, not chosen.** `test/contrast.test.ts` computes the WCAG ratio for every
  pair the site paints, in both themes, and fails below AA. A new colour token goes in the pair
  list, or it is not checked.
- **The chat panel never states a figure it computed, and never streams.** Every number in an
  answer comes from a `lib/data/` reader, either stated by `intents.ts` or handed to the model in
  the fact sheet; the model is told not to do arithmetic. A model answer is scanned whole by
  `guard.ts` before it is shown - streaming would put a banned word on screen before the scan.
  Only what the prepared answers, the data answers and the cache miss reaches the model, behind
  the daily token budget and the per-client rate limit in `budget.ts`, and without
  `OPENROUTER_API_KEY` that layer is simply off. `/api/chat` is public and stays out of
  `proxy.ts`. A new prepared answer needs a question that matches it on its own page -
  `test/chat-layers.test.ts` asks every one. **The suggested questions follow what is on
  screen**: on `/pick` they are `METHOD_SUGGESTED[method]`, in plain words a player would use,
  and none may need the model. A prepared answer about a picker filter carries `figures` from
  `figures.ts`, so its explanation is hand-written and its numbers come from the readers.
- **Motion is reduced to a cross-fade, not to nothing.** `prefers-reduced-motion` turns the four
  animated moments (the three of web.md 5.2 and the chat sheet's slide) into a 160ms opacity fade with the stagger delay cleared - a number still
  arrives rather than blinking into place (web.md 5.2).
- **Fixtures are generated, not hand-edited.** `python frontend/test/make-fixtures.py` from the
  project root after an artifact's shape changes.
- No emoji, matching the root `CLAUDE.md`.

## After changing anything here

`npm test`, `npm run build`, `npm run test:e2e`. Then **rebuild the Docker image the owner
actually looks at** - `docker compose up -d --build --no-deps nextjs-web` from the repo root - and
check the change on http://localhost:3000. That container runs code built into its image, so
without the rebuild it keeps serving the old site however many local checks passed. After a change to `lib/data/` or the artifacts it
reads, also `npm run test:integration` - it is what proves an ingested draw reaches the page without
a restart.
