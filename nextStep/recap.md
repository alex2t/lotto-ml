# What is left across the build documents

A single list of everything still outstanding in [`lottodraw.md`](lottodraw.md),
[`n8n.md`](n8n.md), [`web.md`](web.md) and [`chat.md`](chat.md), separated into **code in
this repository** and **work that happens somewhere else** - in the n8n editor, on the VPS,
at OpenRouter, or by reading two sites side by side.

Written 2026-09-24, verified against the code and the tests, not against the documents'
own checkboxes. Updated the same day when `chat.md` was built (section 5).

---

## 1. The short answer

**There is one piece of repository code left in all four documents**, and it is the last
step of the cutover: deleting Streamlit and rewriting the six tests that import from
`view/` (web.md section 8, step 6). It is gated behind a VPS deployment and a week of
running both sites, so it cannot be started now. `chat.md` is built.

Everything else outstanding is n8n nodes, a deployment, an OpenRouter key, or a comparison
someone has to look at.

| Document | Code left | Not code | Blocked by |
|:--|:--|:--|:--|
| `lottodraw.md` | none | 2 n8n nodes | nothing - can be built today |
| `n8n.md` | none | monitoring week, Phase 2B nodes, verification | 3 clean draws |
| `web.md` | the Streamlit deletion commit | VPS deploy, domain, matrix comparison | VPS, then 1 week + 3 draws |
| `chat.md` | none - built 2026-09-24 | a capped OpenRouter key in `secrets.env`; reading the question log | nothing - the panel works without the key |

One test is red on `main`, and not because of any of these: F-67 in `issue.md`, a parity test
whose assertion cannot hold when a ball comes up as the bonus two days after its last
appearance. The engine is right; the fix is a one-line change to the test, waiting for a
decision.

---

## 2. `lottodraw.md` - complete on the code side

Verified 2026-09-24: `tests/test_rebuild_webhook.py` is **32 tests, passing in 18.5s**, and
every row of the document's section 6 table is in `rebuild_webhook.py`:

| Requirement | Where |
|:--|:--|
| the draw validated at the receiver | `parse_draw()`, `rebuild_webhook.py:86` |
| ISO date to `19 Sep 2026`, in one place | `CSV_DATE_FORMAT:51`, read by `format_row():152` and `row_date():135` |
| dedupe by date, row after the header, zero-padded, LF | `handle_draw():196`, `append_draw():158` |
| atomic write - temp file, fsync, rename | `append_draw():158` |
| rebuild only when the CSV changed or the artifacts are stale | `artifact_state():180` |
| the response with `csv_rows` and the five `state` values | `handle_draw():216-230` |
| the engine's log decoded UTF-8 (F-65) | `run_drawpick():234` |

F-64 and F-65 are both closed in `issue.md`'s Appendix A. Nothing is open against the
receiver.

### What is left

Two nodes, built in n8n, described in `n8n.md` section 7 steps 4 and 5:

- **Code node** - sign the draw. `crypto.createHmac('sha256', $env.REBUILD_SECRET)` over
  `JSON.stringify({date, main, bonus})`, returning `{body, signature}`.
- **HTTP Request node** - `POST http://lotto-rebuild:8080/rebuild`, header
  `X-Lotto-Signature: {{$json.signature}}`, body `{{$json.body}}` sent **raw**. Letting n8n
  re-serialise the object changes the bytes and produces a 401 that reads as a wrong secret.

`REBUILD_SECRET` must hold the same value in n8n's environment and in the receiver's.

---

## 3. `n8n.md` - all n8n, no repository code

The Python side of ingestion is finished: `scripts/scrape_lotto.py` and
`tests/test_scraper_sources.py` against `tests/fixtures/*.html` are what the n8n Code node
reproduces, and the two most recent commits on `main` fixed real parser defects found there
(`5f46fac`, `d52f32e`).

### Section 6 - the monitoring week (in progress)

Three draws - Monday, Wednesday, Saturday - each email checked on five points:

1. the six numbers and the bonus match lottery.ie;
2. they are the **main Lotto** draw, not Plus 1 or Plus 2;
3. `csvRow` is the exact CSV format - day zero-padded, `Jan`..`Dec`, two digits a number,
   seven commas;
4. the email arrived within about ten minutes of 21:05;
5. `notes` is empty, or holds a note you can explain. A note saying a Plus row was rejected
   means the markup changed - read it, do not tick it off.

**Go/no-go:** three consecutive draws, all five points correct, no failure email between
them. Anything less restarts the week.

### Section 7 - Phase 2B, after the week passes

Five nodes, in order, all after the result email so a commit can never happen without the
email describing it:

1. GitHub **Get** `data/irish500.csv` on `main`.
2. Code node - insert the row at position 2 (newest-first), skipping if the date is already
   the newest.
3. GitHub **Edit** - same path, commit message naming the draw and whether one source or
   two; pass the `sha` from step 1 if the node exposes it.
4. Code node - sign the draw (section 2 above).
5. HTTP Request - post it to the receiver. `rebuilt`, `already had it` and
   `rebuilt stale artifacts` are all success. Anything else, or a `csv_rows` that disagrees
   with the row count just committed, routes into the section 5 failure email.

### Section 8 - verification, before trusting any of it

- **The backtest is the one that matters**: point the archive node at `results-archive-2025`,
  return every parsed draw, and compare all 105 lines against `data/irish500.csv`. Exact
  match, zero padding and ordering included. Wrong Plus filtering shows up here and nowhere
  else.
- Manual run with `TARGET_OVERRIDE` set, then put it back to `null`.
- `python scripts/scrape_lotto.py --dry-run` on the PC must print the same row the email
  carried.
- Drive the downstream path with **pinned** Code-node output, not a test override. Unpin
  before the monitoring week.
- Force the failure path on each source in turn. A failure path that has never fired is not
  a safeguard.
- After the first real commit, `git diff` must show exactly one added line in position 2 and
  no line-ending change anywhere else. A whole-file diff means CRLF.

---

## 4. `web.md` - one commit of code, at the end

Phases 3 and 4 are built and signed off. What remains is section 8, in order.

### Step 2 - the matrix comparison (not code, and it can gate Phase 4)

The section 6 matrix records **where** each statistic landed, not that both sites print the
same number for it. Part of the comparison is already automatic and stronger than a visual
check - `frontend/test/ranged.test.ts` recounts every countable distribution from the draw
history and asserts it equals the artifact. The rest has to be read off both sites with the
same input.

This is the one outstanding item that could send work back into Phase 4, so it is worth
doing before the deployment rather than after.

### Steps 4 and 5 - VPS (not code)

Deploy `nextjs-web` alongside Streamlit per [`vps.md`](vps.md) section 3 - read 3.1 first,
the uid on the bind mount is what stops the stack starting (F-45). Verify the artifacts
mount read-only, the admin download works over HTTPS, and the homepage is right after a real
`drawpick.py` run on the server. Then point the domain, and leave Streamlit running unlinked
for **one week and at least three ingested draws**.

### Step 6 - the only code left, in one commit

- Remove `streamlit-web` from `docker-compose.yml` and from `scripts/docker_start.*`.
- Delete `app.py`, `view/`, `Dockerfile.streamlit`, `requirements-web.txt`.
- **Six test files import from `view/`** (confirmed 2026-09-24). Each needs its Streamlit
  half removed or rewritten against `frontend/`, not simply deleted - five of them also
  guard analyzer behaviour that has nothing to do with the dashboard:

  | File | What survives the deletion |
  |:--|:--|
  | `test_site_wording.py` | nothing - replaced wholesale by `frontend/test/wording.test.ts` and the Playwright pass |
  | `test_anomaly_detector.py` | the detector's own checks; only the `AppTest` on Pattern Comparison goes |
  | `test_draw_history_numbers.py` | the F-25/F-27 history assertions and the CSV scan; the Post Draw Analysis `AppTest` goes |
  | `test_bonus_transition_baseline.py` | the fair-draw baseline; the import of `validate_bonus_transition` needs a new home |
  | `test_bonus_window.py` | the F-33/F-36 window rules; `create_draw_table_html` goes |
  | `test_odd_even_affinity.py` | the F-38 simulation; the Statistics `AppTest` goes |

- Update in the same commit: root `CLAUDE.md` (the `@view/pages/CLAUDE.md` import and the
  folder table), `GEMINI.md`, `.gemini/GEMINI.md`, `README.md`, `plan.md`, `tests/CLAUDE.md`
  and `.claude/skills/lotto-verify/verify.py`'s test list.

**Do not delete `view/` before this step.** It is the reference for every statistic the new
site reproduces, and the fallback if the matrix comparison finds something missing.

### Step 7 - the manual

`docs/dashboard-manual.md` rewritten for the new site, or deleted. A manual describing pages
that no longer exist is worse than none, because it gets trusted.

---

## 5. `chat.md` - built 2026-09-24

The chat panel is in `frontend/`: a button in the nav opens a sheet on every page, and a
question falls through four layers - prepared answers, data answers, a response cache, and
only then the model. `issue.md` records it as F-68 under Improvements done; `chat.md` now opens
with a status checklist and the list of places the build differs from the design.

### What was done

- [x] **The one `ADVICE` list.** Moved out of `test/wording.test.ts` and `test/e2e/site.spec.ts`
  into `frontend/lib/advice.json`; both scans, the system prompt and the runtime guard import it.
- [x] **Layer 0** - `lib/chat/prepared.ts`: 57 hand-written answers over the vocabulary, the
  tables, the bands, the verdict, the data and the out-of-scope questions. Every fact in them
  was checked against the code or the artifacts first (the 13/27-day thresholds, the freshness
  cap of 2, momentum as a ratio around 1, a regime shift as a recent peak or trough, the six
  checks and which two are informational, 1 in 10,737,573 for the jackpot).
- [x] **Matching** - `lib/chat/match.ts`: every pattern word present, longest pattern wins, the
  current destination breaks a tie; a question in the banned vocabulary gets the fixed "the site
  does not rate lines" answer.
- [x] **Layer 1** - `lib/chat/intents.ts`: 12 intents - a number's counts, when it was last
  drawn, the numbers in a category, the latest draw, a draw by date, the next draw, the
  high-number, odd/even and sum shares, a number's partners, the draw count, and the tray's line.
- [x] **The fact sheets** - `lib/chat/context.ts`, one per destination, from the same readers
  the page uses. The Numbers page's filter parsing moved into `lib/data/table.ts`
  (`railFromParams`) so the page and the sheet cannot read the URL differently.
- [x] **Layer 3** - `lib/chat/openrouter.ts` (the `/cerebras` skill's pinned request, no retry,
  no stream), `prompt.ts` (static system prompt, the fact sheet in the last message, at most
  two turns of history).
- [x] **The four limits** - credit cap (owner, at OpenRouter), 5 a minute and 20 an hour per
  client (`lib/auth/rate-limit.ts` generalised into `limiter()` and shared with login), a daily
  budget of 500k input / 100k output tokens counted from OpenRouter's `usage`, and a 500-character
  question / 8 KB body cap enforced while the body is read.
- [x] **The guard** - `lib/chat/guard.ts`: a model answer with a banned word is never shown; the
  panel says so and gives the page's figures instead.
- [x] **Layer 2** - `lib/chat/cache.ts`: 300 answers, keyed on page, question, fact sheet,
  history and the artifacts' newest mtime (`artifactsVersion()` in `lib/data/artifacts.ts`).
- [x] **The panel** - `components/chat/ChatLauncher.tsx` and `ChatPanel.tsx`: a native modal
  `<dialog>` (focus trapped, Escape closes), right-hand sheet on desktop, bottom sheet on a
  phone, suggested questions for the page, `aria-live` answers, each labelled with where it came
  from; the slide becomes the 160ms cross-fade under reduced motion.
- [x] **The route** - `app/api/chat/route.ts`: `POST` answers, `GET` returns the suggestions.
  Public, not in `proxy.ts`.
- [x] **Env** - `OPENROUTER_API_KEY=` in `secrets.env.example` and `frontend/.env.example`.
  `secrets.env` itself was not touched. Compose already passes that file raw to `nextjs-web`.
- [x] **Tests** - vitest 290 (was 159): `test/chat-layers.test.ts` and
  `test/chat-model.test.ts`, each limit fired once, the guard once per banned word, no network.
  Playwright 76 (was 66): `test/e2e/chat.spec.ts` on desktop and mobile. pytest 295: one new
  assertion in `tests/test_docker_stack.py`.
- [x] **A real bug the e2e suite caught** - the new nav button pushed a 412px phone's page to
  443px, putting the panel's Ask button off screen. Measured, then fixed by tightening the nav
  below the `sm` breakpoint only.
- [x] **Docs** - root, `frontend/` and `tests/` `CLAUDE.md`, `GEMINI.md` and its copy, the
  `/cerebras` skill, `chat.md`'s status, `issue.md` (F-67 open, F-68 done), and this file.

### What is left

- [ ] **Owner, at OpenRouter:** issue a key for this site alone and set its credit limit
  **before** putting it anywhere - the only limit that holds if the code is wrong.
- [ ] **Owner:** put `OPENROUTER_API_KEY=` in `secrets.env` (by hand), then
  `docker compose up -d --build --no-deps nextjs-web`. Until then the panel answers its
  prepared and data questions and says the rest is not switched on.
- [ ] **Ongoing (chat.md step 5):** read the `[chat] model question` lines in the container log
  and move anything asked twice into `prepared.ts`.
- [ ] **F-67:** decide on the parity test fix in `issue.md`.

---

## 6. The order it actually has to happen in

```
  now
   |
   +-- lottodraw.md's two n8n nodes            (independent, can be built today)
   |
   +-- web.md step 2: compare the figures      (independent; could send work back to Phase 4)
   |
   +-- chat.md: a capped key into secrets.env  (independent; the panel already runs without it)
   |
  n8n.md section 6: three clean draws
   |
  n8n.md section 7: Phase 2B nodes + section 8 backtest
   |
  web.md steps 4-5: deploy, point the domain, wait a week and three draws
   |
  web.md step 6: delete Streamlit        <-- the only repository code left
   |
  web.md step 7: the manual
```

The three branches at the top do not depend on anything and are the only things that can be
worked on right now. Everything below the monitoring week waits on real draws.

---

## 7. The test counts - corrected 2026-09-24

Collected after the chat panel landed: **295 pytest tests across 26 files** (294 pass; the one
failure is F-67), **290 vitest**, **76 Playwright** on desktop and mobile. The root
`CLAUDE.md`, `tests/CLAUDE.md` and `GEMINI.md` now say so. `web.md`'s own figures (277 pytest,
159 vitest, 66 Playwright) are left as they are: they record what was green when Phase 4 was
signed off.
