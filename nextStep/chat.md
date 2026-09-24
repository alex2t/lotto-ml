# A chat panel beside the numbers

How someone asks "what does this table mean?" on the page they are looking at, and gets an
answer - without the site paying an AI provider for a question it could have answered for
nothing.

This is the build document for the chat panel in [`../frontend/`](../frontend/CLAUDE.md). It
is a Phase 4 addition to the five destinations in [`web.md`](web.md); it changes no analyzer
and adds no artifact.

## Status - built 2026-09-24 (F-68 in `issue.md`)

Steps 1-4 of section 10 are built and tested. What is left is owner work and step 5, which
never finishes.

- [x] Step 1 - layers 0 and 1 and the panel: `lib/chat/prepared.ts` (57 answers),
  `intents.ts` (12 intents), `match.ts`, `components/chat/`, `app/api/chat/route.ts`
- [x] Step 2 - the fact sheets: `lib/chat/context.ts`, one per destination
- [x] Step 3 - layer 3 behind the four limits and the guard: `openrouter.ts`, `prompt.ts`,
  `budget.ts`, `guard.ts`, `answer.ts`
- [x] Step 4 - the response cache: `lib/chat/cache.ts`
- [x] Section 8 - `OPENROUTER_API_KEY` in both example env files; `tests/test_docker_stack.py`
  asserts it arrives raw from `secrets.env` and is never `NEXT_PUBLIC_`
- [x] Section 9 - `test/chat-layers.test.ts`, `test/chat-model.test.ts`,
  `test/e2e/chat.spec.ts`, and the scanned-set assertion in `test/wording.test.ts`
- [ ] Owner: issue a key for this site alone, **set its credit limit at OpenRouter first**
  (section 5, limit 1), then put it in `secrets.env` and rebuild `nextjs-web`
- [ ] Step 5 - read the `[chat] model question` lines in the container log and move the
  repeated questions into `prepared.ts`

Where the build differs from the design below, on purpose:

- **The `ADVICE` list is `frontend/lib/advice.json`**, not the array in `test/wording.test.ts`.
  The source scan, the rendered scan, the system prompt and the guard all read that file. It is
  JSON so the list is not itself a scanned source.
- **`source` has two more values**: `guarded` (the model answered in banned words and was not
  shown) and `unavailable` (no key, budget spent, rate limited, or the call failed).
- **The budget starts lower** than section 5's example, as step 3 says: 500k input and 100k
  output tokens a day in `budget.ts`, about $0.25 at the Cerebras endpoint's price.
- **A question in the banned vocabulary** ("is 7 a strong number?") is answered by a fixed
  prepared entry, `out-of-scope-rating`, rather than reaching the model. The words cannot be
  written into a pattern - the source scan would flag them - so `match.ts` checks the list.
- **Data answers are route-aware**: on `/numbers/12`, "how often has it come up?" is about 12,
  and on `/pick`, "is my line typical?" reads the tray through `lib/pick/current-line.ts`.
- **The nav is tighter on a phone.** The launcher pushed a 412px screen's page to 443px; the
  links and gaps shrink below the `sm` breakpoint, and desktop is unchanged.

---

## 1. What it is, and what it must never be

A panel that opens from the right on every page. It answers questions about **the statistics
and tables the site is already showing** - what hot/medium/cold means, why a spread band
reads 20-25, what the freshness bins are, how many times 23 has come up in the last 25 draws,
why the site says a line is uncommon.

It is a reading aid for the page. It is not a tipster, not a chatbot about lotteries in
general, and not somewhere the site starts computing things.

### The rules that do not move

- **Describe, never advise.** The `ADVICE` list in `frontend/test/wording.test.ts` applies to
  every word the panel puts in front of someone, whether a person wrote it or the model did.
  A model will reach for "strong", "consider" and "confidence" unprompted, so this is
  enforced three times over - in the system prompt, over the prepared answers at test time,
  and over every model response at runtime before it is shown. Section 6.
- **The site computes nothing** (`frontend/CLAUDE.md`). The panel is no exception. Every
  figure it states comes from `data/*.json` through the existing `lib/data/` readers. **The
  model is never asked to do arithmetic and never sees a raw artifact** - it is handed
  figures that are already correct and asked to put them in a sentence.
- **No login.** Asking a question is something a player does, so it stays public, like
  everything else outside `/api/download/*` (`proxy.ts`). Public and metered are not in
  conflict - section 5.
- **Never `data/irish500.csv`.** `../tests/test_draw_history_numbers.py` scans `frontend/`
  for it (F-35).
- **The key never reaches the browser.** Every call to OpenRouter is made server-side from a
  route handler. No `NEXT_PUBLIC_` anything.
- No emoji, matching the root `CLAUDE.md`.

---

## 2. The model, and what it actually costs

`openai/gpt-oss-120b` on OpenRouter. Verified against `https://openrouter.ai/api/v1/models`
on 2026-09-24:

| | |
|:--|:--|
| Slug | `openai/gpt-oss-120b` |
| Context | 131,072 tokens |
| Input | **$0.15** per million tokens |
| Cached input | **$0.075** per million tokens |
| Output | **$0.60** per million tokens |

There is no `:free` variant. There is an `openai/gpt-oss-120b:batch` at roughly a fifth of
the price, which is no use here - a person is waiting for the answer.

**What one answered question costs**, on the budget of section 4 - about 1,200 input tokens
and a 250-token answer:

```
  1,200 input  x $0.15/M  = $0.00018
    250 output x $0.60/M  = $0.00015
                            ---------
                            $0.00033   about a third of a tenth of a cent
```

With the static part of the prompt cached, input drops to about $0.00011 and the question
costs **$0.00026**. A thousand questions is **26 cents**. Ten thousand is $2.60.

That is the number that matters: the model is not the expense. **The expense is an unmetered
endpoint on a public site**, where one script can ask a hundred thousand questions overnight.
Everything in sections 3 to 5 is aimed at that, not at shaving tokens off a prompt.

---

## 3. Three layers, and only the third one costs anything

Every question falls through these in order. Most never reach layer 3.

```
  question
     |
  [0] prepared answer      -- matched, no model call        cost: 0
     |  miss
  [1] data answer          -- a template filled from lib/data   cost: 0
     |  miss
  [2] response cache       -- someone already asked this     cost: 0
     |  miss
  [3] the model            -- page facts + question -> gpt-oss-120b
```

### Layer 0 - the prepared answers

A catalogue of about sixty questions written by hand, in `lib/chat/prepared.ts`, covering
what the site already explains somewhere and what people will ask first. Grouped by the
destination they belong to:

| Group | Questions of the kind |
|:--|:--|
| The vocabulary | what hot / medium / cold mean and the 13 and 27 day thresholds; what a freshness bin is; what C0-C2+ mean; what "pre-draw category" means on a draw row |
| The tables | what each column of the trigger periods table is; what volatility, trend and momentum mean there; what "often drawn with" counts and what it does not mean |
| The bands | why the spread bins are half-open - "20-25" is 20 to 24 (`lib/scoring/bands.ts`); how the sum bands are cut; what the six-ball and seven-ball distributions are and why a line is compared with the six-ball one (F-59, F-63) |
| The verdict | what typical / uncommon / unusual mean; why the site will not say a line is good; why every line is equally likely |
| The data | how many draws are on file and from when; where the numbers come from; how often it updates; what the staleness banner is saying |
| Out of scope | can you tell me what to play; what will win; can you predict the next draw - each gets a fixed, polite, one-sentence answer with no model call |

Each entry is `{ id, patterns, answer, routes }`. Matching is deterministic and local:
lower-case, strip punctuation, and score against each entry's phrase patterns, weighted
towards the entries for the current route. A confident match answers immediately.

**This is also the quality floor.** A hand-written answer about the site's own vocabulary is
better than a generated one every time, because it can say "20-25 means 20 to 24" and be
right, which a model reading a chart label will not be.

### Layer 1 - the data answers

Questions with a number for an answer are answered from `lib/data/`, not by the model. A
small set of parameterised intents, in `lib/chat/intents.ts`:

| Intent | Reads |
|:--|:--|
| how often has N come up / in the last K draws | `lib/data/numbers.ts`, `dossier.ts` |
| when was N last drawn / what category is it | `lib/data/numbers.ts` |
| which numbers are hot / medium / cold right now | `lib/data/table.ts` |
| what was the last draw / the draw on a date | `lib/data/draws.ts` |
| what share of draws had K numbers at 32 or above / this odd-even split / this sum band | `lib/data/distributions.ts` |
| what is N most often drawn with | `lib/data/dossier.ts` |
| when is the next draw | `lib/data/schedule.ts` |

The intent is recognised by pattern, the number is extracted, the reader supplies the figure,
and a fixed sentence states it. **No model, no rounding drift, no invented number.**

### Layer 2 - the response cache

An in-process `Map`, keyed on `(route, normalised question, artifacts mtime)`, holding the
last few hundred model answers. The mtime is already how `lib/data/artifacts.ts` invalidates
its own cache, so a `drawpick.py` rebuild drops every answer that was based on the old
numbers - which is the correct behaviour, not an optimisation.

On a site with one owner and a handful of visitors this is what makes the second person to
ask the same thing free.

### Layer 3 - the model

Only what the first three missed. Section 4 is what it is given.

---

## 4. The prompt, and why it is small

The model gets three things and nothing else.

**1. A static system prompt** (~600 tokens), byte-identical on every request so it is the
cacheable prefix. It says what the site is, the vocabulary it may use, the words it may not
use, that it must not do arithmetic or state a figure that is not in the facts it was given,
that it must answer in at most three sentences, and that it must say it does not know rather
than guess.

**2. A page fact sheet** (~400-800 tokens), built server-side for the current route by
`lib/chat/context.ts`. This is the part that makes the panel useful and the part most easily
got wrong: it is a **small, typed summary**, never a dump of the artifacts.

| Route | What the fact sheet carries |
|:--|:--|
| `/` | the latest draw, its date, the staleness state, the next draw date, the draw count |
| `/pick` | the line currently in the tray, if any, and its shape card figures as already computed by `lib/scoring/line.ts` |
| `/explore` | the active tab, and the headline figures of the chart in view |
| `/numbers`, `/numbers/[n]` | the active filters, or that one number's dossier figures |
| `/review` | the last draw and its shape |

The figures in the sheet are the ones the page is displaying, taken from the same readers the
page used. If the panel and the page ever disagree, that is a bug in the sheet, not a model
problem.

**3. The question, and at most the previous two turns.** Not the whole conversation. A chat
about a table does not need turn nine to answer turn ten, and carrying the transcript is how
a cheap endpoint becomes an expensive one - cost grows with the square of the conversation
length when every turn re-sends every earlier turn.

### The settings

| Setting | Value | Why |
|:--|:--|:--|
| `max_tokens` | 300 | a three-sentence answer; also the hard ceiling on the output half of the bill |
| `temperature` | 0.2 | the same question should not get a different answer each time, and the response cache is worth more when it does not |
| `reasoning.effort` | `low` | gpt-oss emits reasoning tokens, which are billed as output. This is an explaining task, not a thinking one |
| `stream` | **false** | see section 6 - a filtered answer cannot be streamed |
| `usage.include` | true | OpenRouter returns the real token counts, which is what section 5's budget counts |

---

## 5. Spending limits, because the endpoint is public

Four limits, each one able to stop the bill on its own.

1. **A cap at OpenRouter.** Set a credit limit on the key, and use a key issued for this site
   alone. This is the only limit that holds if the code is wrong, so it is the one that is
   set first.
2. **Per-IP rate limit.** Reuse `lib/auth/rate-limit.ts`, which already exists for the login
   route. Something like 20 questions an hour and 5 a minute. Layers 0-2 are answered even
   when the model limit is spent, so a rate-limited visitor still gets the prepared answers -
   they lose the model, not the panel.
3. **A daily token budget**, counted from the `usage` OpenRouter returns, held in the same
   process. When it is spent, layer 3 is switched off for the rest of the day and the panel
   says so plainly. Set it to something like 2 million input and 400k output tokens a day -
   about $0.54, and far more than the site will ever legitimately use.
4. **Input limits.** A question longer than 500 characters is rejected before anything else
   happens; a body over 8 KB is refused unread. `rebuild_webhook.py` already refuses an
   oversized body before reading it, for the same reason.

**A limit that has never fired is not a safeguard** (F-29). Each of these four gets a test
that fires it - section 8.

---

## 6. The wording guard, and the one decision it forces

The site's whole voice rests on never telling anyone a line is good. A language model asked
about lottery statistics will say "strong pattern" and "you might consider" without being
provoked. So the panel is guarded at three points:

1. **In the system prompt.** The banned list is stated, with the replacement vocabulary -
   typical, uncommon, unusual, common - and the equal-chance sentence.
2. **Over the prepared answers, at test time.** `test/wording.test.ts` already scans every
   file under `lib/`, so `lib/chat/prepared.ts` is covered the moment it exists. No new test
   is needed for layers 0 and 1; they are source.
3. **Over every model response, at runtime.** `lib/chat/guard.ts` scans the finished answer
   against the same `ADVICE` list, imported from one place so it cannot drift. A hit means
   the answer is **not shown at all**: the panel replies with a fixed sentence saying it
   cannot phrase that one, and offers the figures from the fact sheet instead.

**The decision this forces: the panel does not stream.** A streamed token is already on the
screen when the banned word arrives, and there is no unsaying it. The whole answer is
buffered, scanned, then shown. It costs nothing extra and adds a second or two of latency,
which a typing indicator covers. gpt-oss-120b is fast enough that this is not worth trading
the guarantee for.

Do not "fix" the latency by streaming and filtering client-side. The filter would then be in
the browser, where it is advice rather than enforcement.

---

## 7. The shape of it

### Files

| Path | Role |
|:--|:--|
| `lib/chat/prepared.ts` | the ~60 prepared questions and their answers, with route weighting |
| `lib/chat/intents.ts` | layer 1 - the parameterised data answers, reading `lib/data/` |
| `lib/chat/match.ts` | normalising and scoring a question against layers 0 and 1 |
| `lib/chat/context.ts` | the per-route fact sheet of section 4 |
| `lib/chat/guard.ts` | the `ADVICE` scan over a model answer, sharing the list with `test/wording.test.ts` |
| `lib/chat/openrouter.ts` | the one place that calls OpenRouter; reads the key, counts usage, applies the budget |
| `lib/chat/budget.ts` | the daily token budget and the rate limit |
| `app/api/chat/route.ts` | `POST`, `runtime = 'nodejs'`, `dynamic = 'force-dynamic'` |
| `components/chat/ChatPanel.tsx` | the panel itself |
| `components/chat/ChatLauncher.tsx` | the button that opens it |

### The route

`POST /api/chat`, taking `{ question, route, history? }` and returning
`{ answer, source, cached }` where `source` is `prepared`, `data`, `cache` or `model`.
Surfacing `source` is not decoration - it is how the panel can say "from the data" on a
figure, and how the tests assert that a question which should never reach the model did not.

The route is public, so it is **not** added to `proxy.ts`'s matcher. That file lists the
admin surface explicitly and stays that way.

### The panel

A right-hand sheet, opened by a button in `Nav`, full-width on a phone as a bottom sheet -
the pattern `components/pick/Picker.tsx`'s line tray already uses (web.md 5.3). It opens with
four or five suggested questions for the current route, taken straight from the prepared
catalogue, because a suggested question that is answered for free is the cheapest question
there is and the best first impression.

Accessibility, per web.md 5.4: a real `<dialog>` or a focus-trapped panel, `aria-live="polite"`
on the answer, keyboard reachable, and the reduced-motion cross-fade rather than a slide.

---

## 8. Environment

The key lives in the repo-root `secrets.env`, with the admin credentials, **not** in `.env` -
Compose reads `.env` for its own variable substitution and would expand a `$` in the value
(F-58). `secrets.env.example` gains the line; `frontend/.env.example` gains it too, for
`npm run dev` outside Docker.

```
# OpenRouter, for the chat panel. Issue a key for this site alone and set a credit
# limit on it: https://openrouter.ai/keys
OPENROUTER_API_KEY=
```

`docker-compose.prod.yml` passes it to `nextjs-web` through `env_file` with `format: raw`,
exactly as the admin hash and session secret are passed. `../tests/test_docker_stack.py`
already asserts that shape and gains a line for this variable.

**Without the key the site still works.** Layers 0, 1 and 2 need no key at all, so a missing
`OPENROUTER_API_KEY` disables layer 3 and nothing else. That is deliberate: the chat panel
must never be able to take the site down, for the same reason `proxy.ts` protects by
exception rather than by default.

---

## 9. Testing

No network in tests - the repo rule (`tests/CLAUDE.md`), and here it is also what keeps the
suite free. `lib/chat/openrouter.ts` takes its `fetch` as a parameter so the tests pass a
fake, in the same way `test/fixtures/` stands in for the artifacts.

**Vitest**

- Every prepared answer matches its own patterns, and no two entries claim the same question.
- The route-weighting picks the `/explore` entry for an `/explore` question and the `/numbers`
  entry for the same words on `/numbers`.
- Each layer 1 intent returns the figure the corresponding `lib/data/` reader returns - the
  same recount discipline as `test/ranged.test.ts`, so a chat answer can never drift from the
  artifact.
- The wording guard blocks an answer containing each banned word, one case per word.
- The wording source scan already covers `lib/chat/prepared.ts`; assert it is in the scanned
  set rather than assuming it.
- The budget: a request over the daily cap does not call the fake fetch; the rate limit
  refuses the 21st question in an hour; a 501-character question is rejected; an 8 KB body is
  refused. Four tests, one per limit of section 5, each firing it.
- The response cache returns without calling the fake fetch, and a changed artifact mtime
  drops the entry.
- A missing key answers from layers 0-2 and says the rest is unavailable, rather than
  throwing.

**Playwright**

- The panel opens, a suggested question is asked and answered with no network call leaving
  the box.
- The panel is reachable and usable at phone width.
- The existing whole-page wording scan in `test/e2e/site.spec.ts` covers the panel's opening
  state, since it renders the suggested questions.

**Python** - nothing new, beyond the `test_docker_stack.py` line for the env variable.

---

## 10. Build order

Each step is worth having on its own, and the site is never broken between them.

1. **Layers 0 and 1, and the panel, with no model at all.** `prepared.ts`, `intents.ts`,
   `match.ts`, the route returning only `prepared` and `data` sources, and the UI. At this
   point the panel is useful, costs nothing, and cannot say anything a person did not write.
   Ship it and use it for a week.
2. **The fact sheets** (`context.ts`), still with no model - they make the layer 1 answers
   route-aware.
3. **Layer 3**, behind the four limits of section 5 and the guard of section 6, with the
   budget set low at first.
4. **The response cache**, once there is a log of what people actually ask.
5. **Read the log and move the common questions into layer 0.** This is the step that keeps
   the bill flat as the site gets busier, and it is the only one that never finishes.

Step 5 is the whole cost strategy in one sentence: **every question the model answers twice
is a question that should have been prepared once.**

---

## 11. Decisions taken here, for the record

| Decision | Why |
|:--|:--|
| Prepared answers first, model last | A hand-written answer about the site's own vocabulary is both cheaper and better than a generated one |
| The model never does arithmetic | The site computes nothing in a component, and a model that adds up a column will eventually add it up wrong, silently |
| No streaming | A banned word cannot be unsaid once it is on the screen; the guard has to see the whole answer |
| No login on the panel | Everything a player does is public (`proxy.ts`); spending is controlled by metering, not by a wall |
| History capped at two turns | Re-sending the transcript makes cost grow with the square of the conversation |
| Cache keyed on artifact mtime | The same invalidation the data layer already uses, so a rebuild can never serve an answer about the old numbers |
| `:batch` not used | A fifth of the price, but someone is waiting |
| The key in `secrets.env` | Compose expands `$` in `.env` (F-58) |
| A missing key degrades, not fails | The chat panel must never be able to take the site down |

---

## 12. Where the facts came from

| Fact | Source |
|:--|:--|
| the model slug, context, and the three prices | `https://openrouter.ai/api/v1/models`, read 2026-09-24 |
| the `ADVICE` list and both halves of the wording guard | `frontend/test/wording.test.ts`, `frontend/test/e2e/site.spec.ts`, `../tests/test_site_wording.py` |
| the site computes nothing; read with `requireKey()` | `frontend/CLAUDE.md`, `lib/data/artifacts.ts` |
| the mtime cache and how a rebuild is picked up | `lib/data/artifacts.ts:20-32` |
| admin surface listed explicitly, not protected by default | `frontend/proxy.ts` |
| an existing rate limiter to reuse | `lib/auth/rate-limit.ts` |
| secrets in `secrets.env`, `format: raw`, never `.env` | F-58 in `issue.md`, `../tests/test_docker_stack.py` |
| refuse an oversized body before reading it | `rebuild_webhook.py`, `MAX_BODY_BYTES` |
| a check that cannot fire is not a safeguard | F-29 in `issue.md` |
| the bottom-sheet pattern and the reduced-motion rule | [`web.md`](web.md) 5.2, 5.3 |
| the six-ball versus seven-ball distinction the panel must explain | F-59 and F-63 in `issue.md` |
