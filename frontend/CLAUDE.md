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
| `lib/data/schedule.ts`, `staleness.ts` | the next draw, and the three freshness states |
| `lib/data/picks.ts` | `lottery_picks.txt`, which is absent on the VPS by design |
| `lib/scoring/` | `line.ts` describes a line, `notes.ts` states facts about it, `bands.ts` mirrors the analyzer's bins |
| `lib/pick/filters.ts` | what the wheels contain |
| `app/api/` | `draws`, `numbers`, `distributions`, `schedule`, `validate` (public); `login`, `logout`, `download/data` (admin) |
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
  `../tests/test_site_wording.py` `ADVICE`, verbatim. It bans ordinary words too - "strongest
  trend" failed both guards and became "biggest change".
- **A band boundary belongs to the analyzer, not here.** `lib/scoring/bands.ts` mirrors
  `lotto_analysis/config/config.py` and `utils/output_generator.py`, including that the spread bins
  are half-open while their labels read as inclusive: "20-25" is 20 to 24, and 25 is in "25-30".
- **A six-number line needs a six-ball distribution.** `lotto_odds_results.json` holds both: every
  key in `hmc` sums to 7, every key in `hmc_6` sums to 6. Reading `hmc` for a line matched nothing,
  every time (F-59).
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
- **Fixtures are generated, not hand-edited.** `python frontend/test/make-fixtures.py` from the
  project root after an artifact's shape changes.
- No emoji, matching the root `CLAUDE.md`.

## After changing anything here

`npm test`, `npm run build`, `npm run test:e2e`. After a change to `lib/data/` or the artifacts it
reads, also `npm run test:integration` - it is what proves an ingested draw reaches the page without
a restart.
