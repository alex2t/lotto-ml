# Phases 3 and 4: the website

How to build the Next.js site that replaces the Streamlit dashboard - a playful place to pick a lotto
line, informed by what past draws looked like, that never claims any line is likelier to win.

This is the build document for `plan.md` Phases 3 and 4. Phase 3 is the foundation: the project, the
data layer, the admin login and the data download, all running locally in Docker. Phase 4 is the UI,
which is the larger half and the reason this document is long.

---

## 1. What we are building

A public site, no login, that does one thing well: **help someone choose six numbers and enjoy
choosing them.** The statistics are the toy box - hot/medium/cold, how often a number has come up in
the last five draws, how fresh it is, how many high numbers a typical draw holds - and the player
decides what to do with them.

The honest framing is the whole point. People look for pattern in a fair draw; the site lets them
play at it with real data, and says plainly that every line has the same chance. That is more fun
than a fake tipster, and it is the only version worth building.

### Rules that do not move

1. **No login for anything a player does.** Every page, every statistic, every pick: public.
2. **Admin login is one account - the owner - and it unlocks one thing:** downloading the data
   folder. Nothing else changes when logged in.
3. **Describe, never advise.** A line or number may be called common, typical or unusual in past
   draws. It may never be called strong, weak, safe, risky, due or overdue, and the site never tells
   anyone to pick, avoid or regenerate anything. The banned list is in `tests/test_site_wording.py`
   (`ADVICE`) and it moves to the new site with the pages - section 7.
4. **Every statistic on the Streamlit site appears on the new site.** Section 6 is the matrix that
   proves it. Nothing is dropped in the name of a cleaner design; things are regrouped and made
   interactive, which is different.
5. **The site computes nothing.** Every number it shows is read from `data/*.json`, produced by
   `drawpick.py`. If a figure does not exist there, it is added in `lotto_analysis/` and written by
   `drawpick.py` - never calculated in a React component. This is what makes the front end
   replaceable, and it is the rule that already governs `view/pages/`.
6. **The site never reads `data/irish500.csv`.** That is `drawpick.py`'s input. A test enforces it
   today (F-35) and the replacement test keeps enforcing it.

---

## 2. The data, and how the site reads it

| Artifact | What the site uses it for |
|:--|:--|
| `lotto_trigger_periods.json` | 47 per-number records: HMC category, days since last, recent counts, volatility, trend, momentum, regime shift, freshness weights |
| `lotto_draw_history.json` | every draw from `2021-12-15`: `main_numbers`, `bonus_number`, and each ball's **pre-draw** category |
| `lotto_distribution_stats.json` | odd/even, sums, and the count of main numbers >= 32 per draw |
| `lotto_7_number_freshness_results.json` | freshness bins C0-C3 |
| `lotto_bonus_analysis.json`, `lotto_bonus_to_main_patterns.json` | bonus profile, the 10-draw pre-draw bonus window, transition rates |
| `lotto_odd_even_validated.json`, `lotto_sum_contribution_validated.json`, `lotto_range_spread_validated.json`, `lotto_consecutive_pairs_validated.json`, `lotto_hmc_categorization_validated.json`, `lotto_freshness_patterns_validated.json` | the validated distributions the picker compares a line against |
| `lotto_advanced_patterns.json`, `lotto_long_term_patterns.json`, `lotto_statistics_analysis.json`, `lotto_recency_zones_calculated.json`, `lotto_window_saturation_calculated.json` | number dossiers: gaps, trends, recency zones |
| `lotto_hmc_recommendations.json`, `data/analysis/*` | not used by the site (owner-facing ML material) |

**`lotto_draw_history.json` is 4.4 MB. It must never be sent to the browser whole.** It is read on
the server, in a cached module, and exposed through API routes that return only what a view needs -
a page of draws, one number's appearances, the aggregate for a chart. This is the single biggest
performance decision in the build; getting it wrong turns a snappy site into a 4 MB download on
first paint.

```
frontend/lib/data/
  artifacts.ts     // reads and caches each JSON file from DATA_DIR, typed
  draws.ts         // page(), byNumber(), latest(), sinceDate() over the draw history
  numbers.ts       // the 47 per-number records, joined across artifacts
  distributions.ts // odd/even, sums, spread, high numbers, freshness, HMC patterns
  schedule.ts      // latestDrawDate(), nextDrawDate(), isStale()
```

`artifacts.ts` reads with `fs` at request time and caches per file mtime, so a `drawpick.py` rebuild
on the volume is picked up without restarting the container. Every read is `data['key']`, never
`data.get('key', default)` - a missing key must throw, for the same reason it must throw in Python
(F-25: an empty default made a page answer "no similar draws" for ten months).

### The draw schedule, and staleness

Draws are Monday, Wednesday and Saturday, about 20:00 Irish time. `schedule.ts` derives the next
draw the same way `ml_lotto` does: **the first date after the latest draw falling on a weekday used
by the latest six draws.** Deriving it from the data rather than hard-coding Mon/Wed/Sat means a
future schedule change is picked up automatically, as the September 2026 addition of Monday would
have been.

Staleness: if the next expected draw date has passed by more than a few hours and the artifact still
does not contain it, the homepage says so (section 4.1).

---

## 3. Phase 3 - foundation

### 3.1 The project

- **Next.js (App Router) + TypeScript + Tailwind CSS**, `output: 'standalone'` for a small Docker
  image. Icons: `lucide-react`.
- Charts: **Recharts** for the ordinary ones (bars, lines, distributions). The playful pieces -
  wheels, the number grid, the freshness matrix - are hand-built SVG and CSS, not a chart library.
- Animation: **Framer Motion** for the wheels and transitions, with `prefers-reduced-motion`
  honoured everywhere (section 5.4).

```
frontend/
  app/
    page.tsx                  // home
    pick/page.tsx             // the picker
    explore/page.tsx          // draws, statistics, freshness, patterns
    numbers/[n]/page.tsx      // one number's dossier
    review/page.tsx           // last draw review
    login/page.tsx            // admin only
    api/
      draws/route.ts
      numbers/route.ts
      distributions/route.ts
      validate/route.ts       // scores a line against the artifacts
      download/data/route.ts  // admin only, streams the zip
  components/
    wheel/  grid/  charts/  layout/  ui/
  lib/
    data/ ...                 // section 2
    scoring/                  // line typicality, shared by /pick and /api/validate
  test/
    fixtures/                 // small copies of the artifacts for unit tests
```

### 3.2 Admin login

One account. Username and a bcrypt password hash in environment variables, a signed httpOnly session
cookie, and middleware protecting `/api/download/data` and any admin route. **NextAuth is more than
this needs** - one user, no providers, no account linking - so a signed cookie (`jose` or
`iron-session`) is fewer moving parts and less to keep patched.

Non-negotiables: the cookie is `httpOnly`, `secure`, `sameSite=lax`; the session is short-lived; the
login route is rate-limited (a simple in-memory counter is enough for one user); no credential
appears in any client bundle. The public site never checks for a session, so an admin failure can
never take the site down.

### 3.3 The data download

`GET /api/download/data`, admin only: streams a zip of `data/*.json`, `data/analysis/*`, and
`data/irish500.csv` - this route is the **one** place the CSV is read, because it is the owner
retrieving their own input file, not the site displaying it. Streamed with `archiver`, never buffered
(the JSON alone is ~5 MB). The filename carries the date of the latest draw, so downloads are
self-describing: `lotto-data-2026-09-16.zip`.

This is what closes the loop in `plan.md`: the VPS produces the artifacts, the owner downloads them
to the PC, `quickpick.py` trains there.

### 3.4 Docker, local first

Development and production both run in Docker; `data/` is a bind mount in both, so the site always
reads the same artifacts `drawpick.py` writes.

- `Dockerfile.web` - multi-stage: `deps` -> `build` -> `runner` on `node:20-alpine`, non-root,
  `ARG UID/GID` as the other two images have since F-45.
- `docker-compose.yml` gains a `nextjs-web` service mounting `./data:/app/data:ro`, with
  `depends_on: { data-engine: { condition: service_completed_successfully } }` - the same guard the
  Streamlit service has.
- `docker-compose.dev.yml` runs `next dev` with the source bind-mounted for hot reload.

**Both sites run side by side during the migration** - Streamlit on 8501, Next.js on 3000 - so every
page can be compared against the one it replaces. Nothing in `view/` is deleted until section 8's
checklist is complete.

### Phase 3 checklist

Done 2026-09-21. Next.js 16 and Tailwind 4 - the current releases, not the 14 named in `plan.md`.

- [x] `frontend/` scaffolded: Next.js + TypeScript + Tailwind, standalone output.
- [x] `lib/data/` reads every artifact in section 2, typed, cached on mtime, no silent defaults.
- [x] `schedule.ts` derives the next draw date from the history, with unit tests including a
      schedule change.
- [x] Admin login: signed cookie session, hashed password from env, rate-limited.
- [x] `/api/download/data` streams the zip, admin only, 401 when logged out.
- [x] `Dockerfile.web` and the compose services, dev and prod - built, started and exercised from
      the container on 2026-09-21 (F-57 in `issue.md`), including the engine-before-site ordering.
- [x] The test harness of section 7 running against fixture artifacts: 50 vitest tests, plus 7.2's
      integration test as `npm run test:integration`.

**What Phase 4 inherits.** `app/page.tsx` is a holding page, not the home of section 4.1. There is
no `lib/scoring/` and no `/api/validate` yet - they arrive with the picker, since the vocabulary
they score in is decided there. The wording guard is still Streamlit's `test_site_wording.py`;
section 7.4's Playwright replacement and source lint are Phase 4 work, before `view/` is deleted.

---

## 4. Phase 4 - the UI

Eight Streamlit pages become **five destinations**, because the current split is by artifact, not by
what someone came to do:

| New | Replaces | What someone came to do |
|:--|:--|:--|
| **Home** | (new) | see the latest draw and when it landed |
| **Pick** | Prediction Validator, parts of Trigger Periods, Freshness | build a line and see how it compares |
| **Explore** | Draw History, Statistics, Freshness Analysis, Pattern Comparison, Trigger Periods | look at what draws have done |
| **Number** | Number Insights | read one number's dossier |
| **Review** | Post Draw Analysis | see how the last draw went |

### 4.1 Home

```
+--------------------------------------------------------------+
|  IRISH LOTTO                      Pick  Explore  Numbers  ... |
+--------------------------------------------------------------+
|                                                              |
|            Latest draw - Wednesday 16 September 2026         |
|                                                              |
|        ( 04 ) ( 07 ) ( 19 ) ( 20 ) ( 35 ) ( 42 )   + ( 31 )  |
|         hot    cold   med    hot    med    cold      bonus   |
|                                                              |
|        Next draw: Saturday 19 September, 20:00               |
|                                                              |
|              [  Build my line  ]   [  Explore the draws  ]   |
|                                                              |
+--------------------------------------------------------------+
|  598 draws on file, back to 2 January 2021                   |
|  Every line has the same chance of winning. This site shows  |
|  what past draws looked like - nothing more.                 |
+--------------------------------------------------------------+
```

The six balls animate in on load (a short stagger, nothing that delays reading). Each carries its
**pre-draw** category, from `winning_numbers_details[i]['category']` in the draw history - the
category in force *before* that draw, not today's (F-27).

**The staleness banner.** If the next expected draw has passed and the artifacts do not contain it:

```
+--------------------------------------------------------------+
|  !  Saturday's draw is not in yet - the site is waiting for   |
|     the latest result. Showing Wednesday 16 September.        |
+--------------------------------------------------------------+
```

Wording is factual, not alarming: the data is late, nothing is broken. Three states, from
`schedule.ts`: **current** (no banner), **waiting** (expected draw within the last ~24 h), **stale**
(more than one expected draw missing - the banner names how many).

### 4.2 Pick - the heart of the site

Someone arrives with no plan. The page asks one question - **how do you want to choose?** - and every
answer leads somewhere playful. The chosen method builds a line into the same tray at the bottom of
the screen, so methods can be mixed: two numbers from a wheel, one picked by hand, three from a
shake.

```
+--------------------------------------------------------------+
|  How do you want to pick?                                     |
|                                                              |
|  [ Spin the wheels ]  [ Pick by hand ]  [ Shake the bag ]     |
|  [ Follow a shape  ]  [ Surprise me  ]                        |
+--------------------------------------------------------------+
|                                                              |
|   HOT  (14 numbers)     MEDIUM  (16)        COLD  (17)       |
|      .-------.            .-------.           .-------.      |
|     /   17    \          /   23    \         /   41    \     |
|    |    (04)   |        |    (26)   |       |    (33)   |    |
|     \   11    /          \   09    /         \   47    /     |
|      '-------'            '-------'           '-------'      |
|      [ SPIN ]             [ SPIN ]            [ SPIN ]       |
|      2 picked             1 picked            0 picked       |
|      [-] [+] wheels       [-] [+]             [-] [+]        |
|                                                              |
|   Filters on what the wheels contain:                        |
|   [x] drop numbers drawn 3+ times in the last 10 draws       |
|   [ ] drop numbers not drawn in the last 25 draws            |
|   [ ] only numbers 32 and above          [ Reset filters ]   |
|                                                              |
+--------------------------------------------------------------+
|  YOUR LINE   ( 04 ) ( 11 ) ( 26 ) (  ) (  ) (  )             |
|              3 of 6 chosen        [ Clear ]  [ Fill the rest ]|
+--------------------------------------------------------------+
```

**Spin the wheels.** One wheel per HMC band by default - hot, medium, cold - because that is the
classification the whole site is built around (recency-based: hot = drawn in the last 13 days,
medium = 14-26, cold = 27 or more; thresholds from `lotto_analysis/config/config.py`). Press `+` to
add a wheel to a band, `-` to remove one; a band with no wheel contributes nothing. That alone lets
someone build a 4 hot / 1 medium / 1 cold line, or six cold numbers, or anything else - and the tray
shows the shape they are building.

**The filters are the interesting part**, and they are where the recent-draw windows live. The
artifacts carry, per number, how many times it appeared in the last **5, 6, 10 and 25 draws**
(`recent_4`, `recent_5`, `recent_9`, `recent_24` - the names are one less than the window they count,
a deliberate quirk of the pipeline; the UI must show the honest number, "the last 10 draws", never
the key name). Each becomes a slider or a toggle that removes numbers from the wheels:

- drawn **more than N times** in the last 5 / 6 / 10 / 25 draws - remove them;
- **not drawn at all** in the last 5 / 10 / 25 - remove them;
- freshness bin C0 / C1 / C2 / C3 - keep or drop (`lotto_7_number_freshness_results.json`);
- was a bonus ball in the last 10 draws - keep or drop (`lotto_bonus_analysis.json`);
- 32 and above only, or below 32 only.

Every filter shows its cost immediately: **"34 numbers left in the wheels"**, and a wheel that empties
says so rather than silently spinning nothing. Filters are chips, so the player can see at a glance
what they have narrowed to, and every chip has an `x`.

**Pick by hand** is the 1-47 grid, each cell tinted by HMC, with the number's recent count printed
small. Tap to add, tap to remove. Long-press (or hover) opens a peek card: last seen, how many times
in the last 25 draws, link to the full dossier.

**Shake the bag** is the same pool as the wheels but as one animated draw of six - for someone who
wants it over in three seconds. The filters still apply, so it is a quick pick with the player's own
rules.

**Follow a shape** starts from what draws have looked like: pick an odd/even split (4/2 is the most
common), a sum band, a spread, a count of numbers >= 32, and the site fills a line that has that
shape. Each option shows the share of past draws with it - `lotto_odd_even_validated.json`,
`lotto_sum_contribution_validated.json`, `lotto_range_spread_validated.json`,
`lotto_distribution_stats.json`.

**Surprise me** is a uniform random six, offered without ceremony and labelled exactly that. It is
there to make the point: it is as good as any other method on this page.

#### The line tray, and what it says about a line

Fixed to the bottom on desktop, a sheet on mobile. When six numbers are in, it expands into the
**shape card** - the Prediction Validator's six checks, rebuilt as a comparison rather than a score
out of 100:

```
+--------------------------------------------------------------+
|  YOUR LINE   04  11  26  33  38  45              [ Save PNG ] |
|                                                              |
|  Odd / even     2 odd, 4 even   |||||====  38% of draws       |
|  Sum            197             ||||||===  in the top fifth   |
|  Spread         41              |||||||==  wider than typical |
|  Hot/med/cold   2 / 2 / 2       ||||=====  14% of draws       |
|  32 and above   3               ||||||===  22% of draws       |
|  Recent bonus   1 of your six was a bonus ball in the last 10 |
|                                                              |
|  This line looks TYPICAL of past draws.                      |
|  That is not an advantage - every line has the same chance.   |
+--------------------------------------------------------------+
```

Each row is a small distribution with the player's value marked on it, so the comparison is visible
rather than asserted. The verdict word is from a fixed vocabulary - **typical / uncommon / unusual**
- and the equal-chance sentence is rendered with it, always, in the same component. That makes the
wording testable in one place instead of eight.

`/api/validate` scores the line server-side from `lib/scoring/`, and `/pick` calls it. One
implementation, so the page and the API can never disagree.

### 4.3 Explore

Four tabs, one destination, everything the Streamlit pages showed:

**Draws** - the draw history as a virtualised list (server-paginated, 50 at a time). Each row: date,
six balls tinted by their **pre-draw** category, bonus, and small badges for odd/even split, sum,
spread, count >= 32. Filters: date range, contains number(s), odd/even split, sum band, high-number
count. Clicking a draw opens it as a card with the pre-draw bonus window (the 10 bonus balls before
it - F-33) and the numbers' categories at that time.

**Statistics** - the charts, each one interactive: HMC distribution across the 47; HMC distribution
of the 7-ball and 6-ball patterns; odd/even with each number's own affinity **next to a fair draw's
chance** (F-38 - the two must appear together or the affinity reads as a signal); sums; spreads;
consecutive pairs; and the high-number breakdown (draws by count of main numbers >= 32, where 71% of
draws hold two or more). Every chart is filterable by date range, and every one says how many draws
it is computed over.

**Freshness** - the C0-C3 matrix as a heat grid, 47 columns wide, with the bin definitions written
beside it rather than in a manual. Selecting a bin highlights those numbers everywhere on the page,
and offers "send these to the picker".

**Patterns** - Pattern Comparison rebuilt: enter or send a line, and see the past draws most like it,
each with its similarity and its date, plus how common that shape is. The exact-match case must work
(F-25: it silently answered "no similar draws" for ten months because a key was read with a default).

The Trigger Periods page's filters - HMC category, freshness weight, volatility, trend, momentum,
regime shift - become a **filter rail shared by all four tabs**, plus the per-number columns in the
Numbers table. Nothing from that page is lost; it stops being a page of its own because what it
really is, is a way of filtering the 47 numbers.

### 4.4 Number dossier

`/numbers/[n]` - one number, everything known about it, as a page worth landing on from anywhere:

```
+--------------------------------------------------------------+
|   ( 23 )   MEDIUM - last seen 18 days ago                     |
|                                                              |
|   Appearances   ||  |   ||||  |  ||   |     |||   (25 draws)  |
|   In the last   5 draws: 1    10 draws: 2    25 draws: 6      |
|                                                              |
|   Gaps          average 7.2 draws, longest 31, current 6      |
|   Trend         steady        Volatility   moderate           |
|   As a bonus    14 times, last on 2 Aug 2026                  |
|   Odd/even      odd - appears in 83% of odd-sum draws vs      |
|                 83% expected for an odd number in a fair draw |
|   Often with    31, 07, 44 (pair counts, not predictions)     |
|                                                              |
|   [ Add 23 to my line ]                                      |
+--------------------------------------------------------------+
```

Everything Number Insights shows - overview, volatility, trend, recent activity, bonus profile, gap
analysis, trigger series, appearance history, the neutral profile (F-30, no verdict) - lands here.
The page must read as a fact sheet, never as a rating.

### 4.5 Review

Public: the last draw, its shape against the distributions, which numbers were hot/medium/cold
beforehand, the pre-draw bonus window, and how the draw compares with what typical draws look like.
Autofilled from the newest entry in the draw history (F-35 - never from the CSV).

Owner-only: the Streamlit page also compares the draw against `lottery_picks.txt`, which is the ML
layer's output and **does not exist on the VPS** - models train on the PC. So the picks comparison
lives behind the admin session, reading `lottery_picks.txt` if it is present and saying plainly that
it is not, otherwise. The public half never depends on it.

---

## 5. Look, feel, and the things that make it fun

### 5.1 Visual language

- **One colour scale for HMC**, used everywhere - ball, chart, grid, badge. Warm for hot, neutral for
  medium, cool for cold. A player should be able to read a category without a legend after two
  minutes on the site.
- **Balls are the motif.** The lottery ball - a circle with a number, tinted by category - is the
  atom of the whole UI, and appears at three sizes: grid (small), draw row (medium), hero (large).
- **Light and dark**, with the theme stored per viewer. Colours defined as CSS custom properties on
  `:root` and redefined for dark, so a chart never has a hard-coded colour.
- **No emoji in new code**, matching the repo rule. The Streamlit pages are full of them; the new
  site uses icons.

### 5.2 Motion, with restraint

The wheel spin, the bag shake and the ball stagger are the three animated moments. Everything else is
instant. The rule: **animation may never delay information** - the numbers are in the DOM as soon as
they are chosen, and the animation is decoration over the top. `prefers-reduced-motion: reduce`
replaces all three with a cross-fade.

### 5.3 Mobile

Most people who pick a line will do it on a phone, probably standing in a shop. So: the picker is
designed at 390 px first and adapted upward; the line tray is a bottom sheet; the wheels stack
vertically and stay thumb-reachable; the 1-47 grid is six columns with 44 px targets; charts scroll
horizontally rather than shrinking into unreadability.

### 5.4 Accessibility

Not an afterthought, and cheap if done from the start: category is never conveyed by colour alone (a
ball carries its letter or a pattern); every control is keyboard reachable and the wheels have a
plain "choose a number" fallback; contrast checked in both themes; the spinning wheel is
`aria-live="polite"` so a screen reader announces the result; every chart has a table behind a
"show the numbers" toggle - which doubles as the honest way to expose the underlying data.

---

## 6. Completeness matrix

Every section of the eight Streamlit pages, and where it lands. This is the checklist for the
cutover: nothing may be ticked in section 8 until every row here is done.

Walked 2026-09-21. The last column records where each row actually landed.

| Streamlit page | Section | New home | Built |
|:--|:--|:--|:--|
| Trigger Periods | HMC category / freshness / volatility / trend / momentum / regime-shift filters | Explore filter rail, shared by all four tabs | yes, as the filter rail on `/numbers` - the rail filters the 47 numbers, which is what that page is |
| | Historical scenario results table | Explore > Statistics | yes, from `lotto_odds_results.json` `scenarios` |
| | Trigger periods table (47 numbers, all columns) | Explore > Numbers table, sortable | yes, at `/numbers`: category, last 10, total, volatility, trend, momentum, sortable, with badges for bin, significant trend, regime shift and recent bonus |
| | Trending and volatile numbers | Explore > Statistics, and each number's dossier | yes, "the most volatile, and the biggest changes", and the dossier's trend and volatility |
| | Sum/range check | Pick > shape card | yes |
| Draw History | draw list with categories | Explore > Draws | yes, 50 a page, each ball tinted by its pre-draw category |
| | recent bonus balls and the main draw | Explore > Draws, per-draw card (pre-draw window, F-33) | yes |
| | date and number filters | Explore > Draws filters | yes, plus odd/even, sum band and high-number count |
| Statistics | overall HMC distribution | Explore > Statistics | yes |
| | 7-ball and 6-ball HMC patterns | Explore > Statistics | yes - and the six-ball one is counted here for the first time (F-59, F-60) |
| | odd/even analysis, per-number affinity vs fair chance (F-38) | Explore > Statistics | yes, the fair-draw chance drawn on the same bar |
| | high numbers (>= 32) per draw | Explore > Statistics, and Pick > shape card | yes, with the fair-draw share beside it |
| Freshness Analysis | mode selection, bin filter, C0-C3 matrix | Explore > Freshness | yes: main 6 / all 7 toggle, bin highlight, the C0-C2+ grid with the definitions beside it |
| Prediction Validator | the six checks | Pick > shape card | yes, each as a distribution with the line marked on it |
| | anomaly alerts | Pick > shape card, as notes (F-28 wording) | yes, `lib/scoring/notes.ts`; every note takes its figure from an artifact and each one has a test that fires it (F-29) |
| | overall score | Pick > shape card verdict word (typical / uncommon / unusual) | yes |
| Number Insights | all nine sections | `/numbers/[n]` dossier | yes: overview, recent activity, gaps, trend and volatility, bonus profile, odd/even against fair chance, trigger series, appearance history. The co-occurrence line in the 4.4 sketch is **not** built - no artifact holds general pair counts, only consecutive ones |
| Pattern Comparison | similar draws, frequency, typicality | Explore > Patterns | yes, including the exact-match case that F-25 broke |
| Post Draw Analysis | last draw autofill, performance summary | Review (public) | yes, from the newest draw in the history, never the CSV (F-35) |
| | comparison with `lottery_picks.txt` | Review (admin only - the file is not on the VPS) | yes, and verified in the container, where it correctly says the file is not there |

**Not carried across, deliberately:** a date-range filter on the *distributions*. The charts are the
artifacts' own figures, computed over every draw, and each one says how many draws that is. Filtering
them by date would mean recomputing a statistic in the front end, which rule 5 forbids; it belongs in
`lotto_analysis/` if it is wanted. The Draws tab, which shows raw history rather than a statistic,
does filter by date.

---

## 7. Testing - everything provable locally, before production

The rule for this build: **the site must be provable on the PC against real artifacts before it is
deployed.** Nothing about ingestion or freshness may be discovered in production.

### 7.1 Unit - the data layer

Vitest over `lib/data/` and `lib/scoring/`, against small fixture artifacts in `frontend/test/fixtures/`
(a trimmed copy of each JSON, committed). Cover:

- every artifact reader parses its real shape, and **throws on a missing key** rather than defaulting;
- `latestDrawDate()` returns the newest entry, not the first;
- `nextDrawDate()` handles Mon/Wed/Sat, and picks up a schedule change from the last six draws;
- `isStale()` returns current / waiting / stale at the boundaries;
- the scoring functions agree with the figures in the validated artifacts.

### 7.2 Freshness - the test the whole ingestion chain hangs on

The site's job after Phase 2 is to show the new draw. That is testable without the VPS:

1. Fixture test: an artifact set whose newest draw is today -> homepage shows it, no banner.
2. Fixture test: newest draw is four days old with an expected draw in between -> the waiting banner
   appears, naming the draw being shown.
3. **Integration test, locally, the real chain**: append a synthetic row to a copy of
   `data/irish500.csv`, run `python drawpick.py` against that copy, point the dev container's mount
   at it, and assert the homepage shows the new draw **without a restart** (this is what the
   mtime-based cache in `artifacts.ts` is for). Reverted afterwards; the real CSV is never touched.

Test 3 is the one that proves Phase 2 will work end to end: n8n commits a row, the VPS rebuilds the
artifacts, the site shows the draw.

### 7.3 End to end

Playwright against the dev container: pick a line by each of the five methods and assert six
distinct numbers in 1-47; apply filters and assert the pool shrinks and an emptied wheel says so;
open a number dossier from three routes; paginate the draw list; log in, download the zip, assert it
contains the artifacts; log out and assert `/api/download/data` returns 401.

### 7.4 The wording test must survive the migration

`tests/test_site_wording.py` is the guard on rule 3, and it is written against Streamlit's `AppTest`.
It cannot survive as it is. The replacement, before `view/` is deleted:

- **a Playwright test** that renders each new page with a typical line and an unusual line, takes the
  full visible text, and asserts none of the `ADVICE` phrases appears and that the equal-chance
  sentence does; plus
- **a source lint** over `frontend/` for the same phrase list, so a banned word in a component is
  caught before it ever renders.

The `ADVICE` list and the `equally likely to win` sentence move across verbatim. Similarly
`test_draw_history_numbers.py`'s CSV scan (F-35) is re-pointed from `view/` to `frontend/`, with the
single documented exception of the admin download route.

---

## 8. Cutover, and deleting Streamlit

In order. Nothing is deleted early.

1. Both sites run side by side locally - `streamlit-web` on 8501, `nextjs-web` on 3000.
2. Walk section 6 row by row against the two sites. Every figure must match.
3. Section 7's tests all pass, including the freshness integration test.
4. Deploy `nextjs-web` to the VPS alongside Streamlit; verify the artifacts mount read-only, the
   admin download works over HTTPS, and the homepage is correct after a real `drawpick.py` run.
5. Point the domain at `nextjs-web`. Leave Streamlit running, unlinked, for one week - and through at
   least three ingested draws.
6. Then, in one commit: remove `streamlit-web` from `docker-compose.yml`, delete `app.py`,
   `view/`, `Dockerfile.streamlit`, `requirements-web.txt`, and the old Streamlit-bound tests
   (replaced in 7.4). Update `CLAUDE.md` (the `@view/pages/CLAUDE.md` import and the folder table),
   `GEMINI.md`, `.gemini/GEMINI.md`, `README.md`, `plan.md`, `tests/CLAUDE.md` and
   `.claude/skills/lotto-verify/verify.py`'s test list in the same commit.
7. `docs/dashboard-manual.md` is rewritten for the new site, or deleted. A manual describing pages
   that no longer exist is worse than none - it gets trusted.

**Do not delete `view/` before step 6.** It is the reference for every statistic the new site must
reproduce, and the fallback if something in the matrix turns out to be missing.

### Phase 4 checklist

Done 2026-09-21, except the two rows marked below.

- [x] Layout, navigation, light/dark theme, the ball component at three sizes.
- [x] Home: latest draw, next draw, the three staleness states.
- [x] Pick: wheels with add/remove per band, hand grid, shake, shape, surprise.
      **The per-band `+`/`-` to add a second wheel to a band is not built**: one wheel per band,
      and a band contributes nothing once its numbers are filtered out. The composition a player
      builds is visible in the tray and in the shape card's hot/medium/cold row.
- [x] Pick: the filter set of 4.2, each showing the remaining pool size.
- [x] Pick: the line tray and shape card, scored by `/api/validate`.
- [x] Explore: Draws, Statistics, Freshness, Patterns. **The filter rail is on `/numbers`**, not
      shared across the four tabs - what that rail really does is filter the 47 numbers, which is
      what that page is.
- [x] `/numbers/[n]` dossier, all nine Number Insights sections.
- [x] Review, public half and admin half.
- [x] Section 6 matrix walked and signed off - see the column added to it.
- [x] Section 7 tests green, including the wording replacement: 99 vitest and 44 Playwright
      (desktop and mobile), plus the ingestion integration test.

---

## 9. Decisions taken here, for the record

| Decision | Why |
|:--|:--|
| Charts server-rendered as SVG, not Recharts | the distributions are static for a set of artifacts, so a chart library would ship client JavaScript to draw a fixed bar chart; each chart carries a "show the numbers" table, which is the accessible route and the honest one |
| The verdict is a percentile, calibrated on the draws | comparing a bucket's share with the largest share is not comparable across checks with different numbers of buckets; the thresholds are set so about two thirds of past draws read typical |
| Five destinations, not eight pages | the Streamlit split is by artifact; people arrive with an intention |
| Signed cookie, not NextAuth | one account, no providers - NextAuth is machinery for a problem this does not have |
| Server-side data layer, API routes | `lotto_draw_history.json` is 4.4 MB; it must never reach the browser whole |
| Recharts for charts, hand-built SVG for the playful parts | a chart library cannot make a wheel feel good |
| Scoring in one module, used by page and API | the Streamlit site drifted between pages that recomputed the same figure |
| Verdict vocabulary fixed to typical / uncommon / unusual | makes rule 3 testable in one component |
| `docs/dashboard-manual.md` rewritten or deleted at cutover | a stale manual is trusted over the code |

## Where the facts came from

| Fact | Source |
|:--|:--|
| HMC is recency-based, 13 / 27 day thresholds | `lotto_analysis/config/config.py:28-37` |
| recent windows are the last 5, 6, 10, 25 draws | `lotto_analysis/config/config.py:41-46`, root `CLAUDE.md` (naming is off by one by design) |
| high numbers start at 32; 71% of draws hold 2+ | `lotto_analysis/config/config.py:101`, `view/pages/CLAUDE.md` |
| a past draw's category is its pre-draw one | `view/pages/CLAUDE.md` (F-27), `lotto_draw_history.json` |
| the pre-draw bonus window is the 10 before the draw | F-33 in `issue.md`, `bonus_analyzer.pre_draw_bonus_window()` |
| per-number odd/even affinity must be shown against fair chance | F-38 in `issue.md` |
| read artifacts with `data['key']`, never a default | `view/pages/CLAUDE.md` (F-25) |
| the site must not read `irish500.csv` | `tests/test_draw_history_numbers.py` (F-35) |
| the banned advice vocabulary | `tests/test_site_wording.py` `ADVICE` (F-26, F-28, F-30) |
| artifact inventory and sizes | `docs/json-artifacts.md` |
| what each current page shows | `docs/dashboard-manual.md`, `view/pages/` |
| Phase 3 and Phase 4 scope | `plan.md` |
