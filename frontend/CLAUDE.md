@AGENTS.md

# frontend/

**The Next.js site that replaces the Streamlit dashboard.** Phase 3 (the foundation) is built;
Phase 4 (the UI) is designed in [`../nextStep/web.md`](../nextStep/web.md), whose section 6 is the
completeness matrix every current `view/` statistic must survive into.

Next.js 16 (App Router) + TypeScript + Tailwind 4, `output: 'standalone'`. Icons `lucide-react`.

```bash
npm run dev             # http://localhost:3000, reads ../data
npm run build           # standalone build, what Dockerfile.web ships
npm test                # vitest, against test/fixtures/
npm run test:integration  # the real chain: append a row, run drawpick.py, serve the new draw
```

## What is here after Phase 3

| Path | Role |
|:--|:--|
| `lib/data/artifacts.ts` | reads `DATA_DIR`'s JSON, cached per file mtime; `requireKey()` throws on a missing key |
| `lib/data/draws.ts` | `allDraws`, `latest`, `page`, `byNumber`, `sinceDate` over the draw history |
| `lib/data/numbers.ts` | the 47 per-number records, joined across artifacts |
| `lib/data/distributions.ts` | odd/even, sums, spread, high numbers, freshness, HMC |
| `lib/data/schedule.ts` | `latestDrawDate`, `nextDrawDate`, `freshness` |
| `lib/auth/` | the one admin account: bcrypt hash from env, signed cookie, rate limit |
| `app/api/` | `draws`, `numbers`, `distributions`, `schedule` (public); `login`, `logout`, `download/data` (admin) |
| `proxy.ts` | guards `/api/download/*`; everything a player does is public |
| `test/fixtures/` | trimmed artifacts, rebuilt by `test/make-fixtures.py` |

`app/page.tsx` is a holding page that proves the data layer reads the mount. The real home page
is Phase 4.

## Rules

- **The site computes nothing.** Every figure comes from `data/*.json`, written by `drawpick.py`.
  A figure that does not exist there is added in `lotto_analysis/` and written by `drawpick.py`,
  never calculated in a component. That is what keeps the front end replaceable.
- **Read artifact fields with `requireKey()`, never a default.** An empty default made a Streamlit
  page answer "no similar draws" for ten months (F-25). A missing key is a bug; let it throw.
- **The draw history is 4.4 MB and never goes to the browser whole.** It is read on the server and
  exposed through API routes that return a page, one number's appearances or an aggregate.
- **Never read `data/irish500.csv`.** The one exception is `app/api/download/data/route.ts`, where
  the owner retrieves their own input file. `../tests/test_draw_history_numbers.py` scans for it.
- **Describe, never advise.** Common, typical, unusual - never strong, weak, safe, risky, due or
  overdue, and never tell anyone to pick, avoid or regenerate. The banned list is
  `../tests/test_site_wording.py` `ADVICE`; its Playwright replacement arrives with Phase 4
  (`../nextStep/web.md` 7.4).
- **No login for anything a player does.** `proxy.ts` lists the admin surface explicitly rather
  than protecting by default, so an admin failure can never take the site down.
- **The admin account lives in the repo-root `.env`, not here.** Compose passes it with
  `env_file: format: raw`, because a bcrypt hash contains `$` and compose expands `$name` inside an
  interpolated value - the hash arrived mangled and every login returned 401 (F-58). `.env.example`
  at the root has the two generator commands. `frontend/.env.example` is for `npm run dev` outside
  Docker.
- **Fixtures are generated, not hand-edited.** `python frontend/test/make-fixtures.py` from the
  project root after an artifact's shape changes.
- No emoji, matching the root `CLAUDE.md`.

## After changing anything here

`npm test`, `npm run build`. After a change to `lib/data/` or the artifacts it reads, also
`npm run test:integration` - it is what proves an ingested draw reaches the page without a restart.
