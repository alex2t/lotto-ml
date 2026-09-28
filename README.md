# Irish Lotto - draw analytics, a line picker and an ML sandbox

A system that collects every Irish Lotto draw (6 from 47, plus a bonus ball), turns the history
into statistics, and shows them on a website where a player builds their own line and sees how
it compares with past draws. Behind it sits a set of machine-learning models trained on the same
data.

**The website is live at [quickpick.ie](https://quickpick.ie)** - without the ML, which runs on
the owner's PC only. A later stage may bring it to the site as a sandbox where a visitor sets the
features and penalties and sees what the models make of them - for fun, and perhaps as a way for
students to learn how a model behaves on a fair draw.

## Built as an AI coder

Started over a year ago, this project began as an experiment to learn machine learning and to
enjoy the vibe-coding side of it. The result was plenty of bugs, an ML model, a basic Streamlit
interface, and a pause. When I picked it back up recently, my approach changed fundamentally. It
became the proving ground where I became an AI coder, learning to steer AI rather than just prompt
it: architecting the system, setting boundary constraints for the agents, and demanding proof
through test-driven verification.

Developed primarily with Claude Code and Gemini, the project doubles as an end-to-end machine
learning study and a worked example of AI-led software delivery, detailed in
[How it was built with AI agents](#how-it-was-built-with-ai-agents). Gemini also generated the
home page's background picture.

## The lottery is random. Looking for logic is human.

That line from the home page is the whole idea of the site. No line is more likely to win than
another, and the site never pretends otherwise. What it offers is the fun of looking: how past
draws were shaped, which numbers have been about lately, and how your own line compares. It
**describes, never advises** - a line is "typical", "uncommon" or "unusual" next to past draws -
and words such as "safe", "due" or "overdue" are banned by tests, not by good intentions.

*Taming pure chance is impossible. Mapping it is fascinating.*

## Architecture

```
  irish.national-lottery.com   lottery.ie
              \                 /
               n8n  (Mon/Wed/Sat 21:05, Dublin time)
               |  scrape both, cross-check, email, commit to GitHub
               |  then a signed POST (HMAC-SHA256)
               v
        rebuild-receiver ---- appends data/irish500.csv, runs drawpick.py
               |
               v
        data/*.json  (~24 artifacts: the website's API and the models' only input)
          |                                   |
          v                                   v
   nextjs-web (read-only mount)        quickpick.py on the owner's PC
   behind Caddy, behind nginx          (6 models, never on the server)
```

| Layer | Where | Stack |
|:--|:--|:--|
| Ingestion | n8n workflow | n8n Code nodes, GitHub API, Gmail |
| Rebuild receiver | `rebuild_webhook.py` | Python standard library `http.server`, HMAC-SHA256 |
| Statistics engine | `drawpick.py`, `lotto_analysis/` | Python 3.11, pandas, NumPy, SciPy, statsmodels |
| Website | `frontend/` | Next.js 16 (App Router), React 19, TypeScript, Tailwind 4 |
| Chat panel | `frontend/lib/chat/` | `openai/gpt-oss-120b` on Cerebras, via OpenRouter |
| ML layer | `quickpick.py`, `ml_lotto/` | scikit-learn, XGBoost, CatBoost, SciPy MILP |
| Hosting | Docker Compose | Caddy 2 behind the VPS's existing nginx |

### Decisions, and why

- **The JSON artifacts are the only interface.** `drawpick.py` writes every statistic into
  `data/*.json`; the website only reads and displays them. A figure the site needs is added to
  the engine, never calculated in a component. That is what let a Next.js site replace the first
  (Streamlit) front end without redoing any analysis - the Streamlit version is kept on the
  `streamlit-app` branch.
- **Training stays off the server.** The VPS runs the light statistics engine and the site; the
  models train on my PC from a data bundle the site's admin page streams as a zip. The engine has
  no dependency on the ML package, so the server image stays small.
- **A rebuild happens because the data changed, not because it was asked.** A draw already in the
  CSV appends nothing and runs nothing, so a retried webhook is free. The same date with other
  numbers is a 409 conflict that writes nothing.
- **The receiver never gets the Docker socket.** It runs the engine in its own process. The socket
  would be root on the host, on the one network-facing service that writes files. It is also not
  proxied: n8n reaches it over the Docker network only.
- **No restart after a rebuild.** The site caches each artifact by file modification time, so a
  rewritten file is picked up on the next request. An integration test appends a draw, runs the
  real engine and asserts the running site serves it.
- **Artifacts are reproducible.** Every float is rounded to 12 significant digits and the files
  are stored with LF endings, so a run on Windows and a run in the Linux container produce
  identical output apart from the timestamp.

## Ingestion: the n8n workflow

![The n8n workflow: fetch, parse and validate, duplicate check, commit, signed rebuild](image/irish-lotto-n8n.png)

1. **Fetch** the results from two independent sites.
2. **Parse and validate** in one Code node: exactly 6 main numbers and a bonus, all 1-47 and
   distinct, and three separate defences against picking up a Lotto Plus draw by mistake.
3. **Cross-check.** Both sources must agree. If they disagree, nothing is committed and an email
   says so. If only one has published, the row is marked in the email subject for a manual check.
4. **Retry** up to three times at 15-minute intervals if the draw is not out yet, then send a
   failure email. A failure is always an email, never a guess.
5. **Duplicate check** against the current CSV on GitHub, then a result email.
6. **Commit** the row to `data/irish500.csv` through the GitHub API, then **sign and POST** the
   draw to the receiver. The signature covers the exact bytes, so the body is sent raw.

## The chat panel, and why it is built this way

The panel answers questions about whatever page is on screen. Most answers never touch a model:

| Layer | Answers with | Cost |
|:--|:--|:--|
| 0. Prepared | one of 65 hand-written answers, matched by page | free |
| 1. Data | typed readers over the artifacts, for questions such as "how often has 7 come up?" | free |
| 2. Cache | a previous model answer, keyed on the page and the artifacts' modification time | free |
| 3. Model | `gpt-oss-120b`, given a short fact sheet for the page | fractions of a cent |

The rules around layer 3:

- **The model never does arithmetic.** Every number in an answer comes from a data reader, either
  stated directly or handed to the model in the fact sheet. A model that adds up a column will
  eventually add it up wrong, silently.
- **No streaming.** A banned word cannot be unsaid once it is on screen, so the whole answer is
  scanned against the same banned list the tests use before any of it is shown. A blocked answer
  is replaced with the page's own figures.
- **Why Cerebras.** Because the answer is not streamed, the time to generate the whole answer is
  the entire wait. Cerebras serves `gpt-oss-120b` fast enough for that to feel immediate. The
  provider is pinned with fallbacks off, and the response is checked to have come from Cerebras,
  so speed and price stay predictable. The call is a plain `fetch` from the Next.js server:
  low reasoning effort, 300-token cap, temperature 0.2, 15-second timeout.
- **The cost to guard against is abuse, not tokens.** One answer costs about $0.0003; the risk is
  a script hitting a public endpoint all night. So there is a credit cap on the key at OpenRouter,
  a daily token budget (500k in, 100k out), a per-client limit (5 a minute, 20 an hour), a
  500-character question limit and an 8 KB body limit. Conversation history is capped at two turns,
  because re-sending the transcript grows cost with the square of the conversation.
- **It degrades, it does not fail.** No key, a spent budget, a rate limit or a failed call each
  answer with a sentence; layers 0-2 keep working. The panel can never take the site down.
- **The key stays on the server.** It is never a `NEXT_PUBLIC_` variable, and a test checks that.

## The website

Five destinations: **Home** (the latest draw, and whether the data has caught up), **Pick**
(build a line with wheels, a 1-47 grid, a shaken bag, a target shape or at random), **Explore**
(draws, statistics, freshness, patterns), **Numbers** (a table of all 47 and a fact sheet for
each) and **Review** (the last draw, with an admin half).

A line is described by a shape card with six checks against past draws - odd/even, sum, spread,
hot/medium/cold mix, count of numbers 32 and above, recent bonus balls - with the verdict and the
equal-chance sentence rendered by one component, so the wording lives in one place.

- **The draw history (4.4 MB) never goes to the browser.** It is read on the server and exposed
  through API routes that return a page, one number's appearances or an aggregate.
- **A missing field throws.** Artifacts are read with `requireKey()`, never a default. An empty
  default once made the old site answer "no similar draws" to every line for ten months.
- **Date ranges are counted, and the counting is held to the engine.** A test recounts the whole
  history and asserts every figure matches the artifact's own. That test found a real bug: a
  six-number line was being compared with a seven-ball distribution.
- **Contrast is measured, not chosen.** A test computes the WCAG ratio for every colour pair the
  site paints, in both themes, and fails below AA. Reduced motion turns animation into a short
  fade rather than removing it.
- **Admin is one account and one purpose.** A bcrypt hash, a short-lived signed httpOnly cookie
  (HS256 JWT), a rate-limited login, and it unlocks only the data download. Everything a player
  does is public, and the admin routes are listed explicitly, so an admin failure cannot take
  the site down.

## The ML layer

Six models for my own use: logistic regression, random forest, XGBoost and CatBoost for the main
numbers, plus two auxiliary logistic regressions (the bonus ball, and main numbers following a
recent bonus ball). Their value is the engineering:

- **Walk-forward features with no look-ahead.** Each training row is computed from the draws
  before it only.
- **Train/serve parity, tested.** Training rows and the serving row are built by two code paths;
  a test asserts they produce the same value for every model column. This broke more than once
  before the test existed.
- **A feature that never varies is a bug.** A test fails any model column that is constant -
  that is how phantom features created by `.get(key, 0)` were found.
- **Capacity is constrained on purpose.** On data with no signal, a model with room to memorise
  shows a train/validation gap, not skill. Parameters and tuning grids are kept narrow, and a
  test guards both.
- **Lines are chosen by integer programming** (`scipy.optimize.milp`): maximise the model's
  probabilities subject to the hot/medium/cold quota and the ticket rules. An infeasible
  combination raises instead of returning a line that quietly breaks a rule.
- **Results are measured against a noise floor.** Over 60 validation draws, a change smaller than
  about 0.03 AUC is noise, and it is reported as noise.

## How it was built with AI agents

How the agents are directed, and how their work is checked:

- **A `CLAUDE.md` in every substantial folder**, holding the invariants that must stay true in it
  (the parity contract, the six-ball rule, the wording rules). All of them are imported by the
  root file, because an agent that loads them only on demand misses them silently. `GEMINI.md`
  restates the same rules for Gemini.
- **`issue.md`, one register of defects**, each with an ID, file:line evidence and the failing
  case, and when fixed, the root cause, the measured before/after and the test that now covers
  it. It runs from F-1 to F-77 so far, after the items of an earlier code review. A defect found in passing is
  recorded, not left in a conversation.
- **Evidence before a fix.** Reproduce it, prove the cause, then change the code. Many of the
  worst bugs here were confident-sounding code that did something else - a statistic reported
  "freshness bias" at p = 1.9e-160 because it was tested against the wrong baseline.
- **Statistical tests are tested on simulated fair draws.** On a fair lottery a 5% test must flag
  about 5% of numbers. Several did not - one flagged 61% of numbers, another flagged every
simulated fair history - until this was checked.
- **Tests assert what the code should do**, not what it happens to output, and are never
  weakened to pass.
- **Project skills for agents:** `/lotto-verify` runs the tests, checks parity, validates every
  generated ticket and compares metrics with the noise floor; `/cerebras` holds the exact request
  shape for the model call.

| Suite | Tests | Covers |
|:--|:--|:--|
| pytest | 281 | the engine, parity, the models, the scraper, the receiver, the Docker wiring |
| vitest | 374 | the data layer, the scoring, the chat layers and limits, the source wording scan |
| Playwright | 102 | every page on desktop and mobile, including the rendered wording scan |
| integration | 1 | a new draw appended, the real engine run, the new draw served without a restart |

## Running it

```bash
python drawpick.py                  # build data/*.json from data/irish500.csv
python quickpick.py                 # train the models, write lottery_picks.txt (local only)
npm --prefix frontend run dev       # the website on http://localhost:3000

python -m pytest -q                 # the Python suite
npm --prefix frontend test          # vitest
npm --prefix frontend run test:e2e  # Playwright
```

With Docker, `scripts/docker_start.ps1` (or `.sh`, `.bat`) runs the engine, checks it exited
cleanly, then starts the site. The production stack is `docker-compose.yml` plus
`docker-compose.prod.yml`, and `docker-compose.nginx.yml` on a server where nginx already
holds ports 80 and 443. Secrets go in `secrets.env` (see `secrets.env.example`), passed to the
containers raw, because Compose would expand the `$` signs in a bcrypt hash.

## Layout

| Path | What |
|:--|:--|
| `drawpick.py`, `lotto_analysis/` | the statistics engine: 16 phases -> `data/*.json` |
| `rebuild_webhook.py` | the signed rebuild receiver |
| `frontend/` | the website - see `frontend/CLAUDE.md` |
| `quickpick.py`, `ml_lotto/` | features, models, line selection |
| `tests/` | the Python tests - see `tests/CLAUDE.md` |
| `docs/` | reference: metrics, features, models, JSON artifacts |
| `issue.md` | the defect register |
| `reverse_proxy/`, `docker-compose*.yml`, `Dockerfile.*` | the deployment |

## Licence

[PolyForm Strict 1.0.0](LICENSE). You are free to read the code and run it for personal,
non-commercial use. Publishing it, sharing a changed version, or any commercial use needs my
written permission - ask through my GitHub profile, [alex2t](https://github.com/alex2t).

The licence covers this project's own code. Its dependencies keep their own licences, and the
draw results themselves are public facts.
