# Phase 2: n8n ingestion of the Irish Lotto draw

How to build the n8n workflow that scrapes each Irish Lotto draw, checks it against the format of
`data/irish500.csv`, emails it to the owner, and - once a week of emails has proved the parser -
commits it to the repository.

This is the build document for `plan.md` Phase 2. It settles the decision `plan.md` left open: the
parsing is **re-implemented in an n8n Code node**, not delegated to `scripts/scrape_lotto.py`. The VPS
runs Docker with no bare-metal Python and the engine image does not carry `scripts/`, so calling the
script would mean changing the image, adding a machine-readable output mode to it, and giving n8n
either an SSH key to the host or access to the Docker socket. The Code node needs none of that.
`scripts/scrape_lotto.py` stays as the tested reference and the manual fallback - every rule below is
taken from it, with the file:line it came from.

The schedule is **Monday, Wednesday and Saturday** - Monday draws began in September 2026
(`14 Sep 2026`, `07 Sep 2026` in `data/irish500.csv`). `plan.md` said Wed/Sat until this document
was written; it now agrees.

---

## 1. What this workflow does, and what it must never do

Three evenings a week it fetches the published result, proves it is the **main Lotto draw**, proves it
fits the CSV contract, and tells the owner. Nothing else.

The rules it must not break:

1. **Main Lotto only.** The same evening produces three draws - Lotto, Lotto Plus 1, Lotto Plus 2 -
   on the same pages, often with the same date. Only the main Lotto result may ever be used. Section
   3.4 gives the three independent checks that enforce this.
2. **Both sources must agree.** A row is produced only when the two sites return the same seven
   numbers for the date. One source alone is not enough to write to the CSV.
3. **A failure is an email, never a guess.** If anything cannot be established with certainty, the
   workflow sends the error email of section 5 and stops. It never writes a partial or assumed row.
4. **Phase 2A does not touch the repository.** The commit step of section 7 is switched on only after
   the monitoring week of section 6.

---

## 2. Using the n8n instance you already have

The workflow is built in the existing instance at **https://n8n.catcheroo.com**. Nothing needs to be
installed, and n8n does **not** belong in this repository's `docker-compose.yml` - it is its own
stack, with its own state and its own credentials, and the lotto data engine must never see its
volume.

Three things to settle in that instance before building.

**1. Timezone.** Check **Settings > General** (or the container's `GENERIC_TIMEZONE`). If the instance
is on UTC, do not change it for this workflow - other workflows may depend on it. Set the timezone on
**this workflow only**: open it, **Settings > Timezone > Europe/Dublin**. That is what makes 21:05
mean Irish time, and it keeps meaning Irish time across the March and October clock changes. A
workflow left on UTC fires at 22:05 Irish time for half the year, after the result is published and
an hour late for no reason anyone will remember in six months.

**2. Credentials.** Two, created once in the n8n UI:

| Credential | Used by | Notes |
|:--|:--|:--|
| Gmail OAuth2 | the result email and the failure email | Google Cloud project with the Gmail API enabled; the authorised redirect URI is `https://n8n.catcheroo.com/rest/oauth2-credential/callback` |
| GitHub API (Personal Access Token) | Phase 2B only, section 7 | Fine-grained token, repository `alex2t/lotto-ml` only, permission `Contents: read and write`, nothing else. Not needed during the monitoring week |

**3. Reaching GitHub and Gmail.** Both are public APIs called outbound from n8n, so there is nothing
to open up and no connection needed between n8n and the lotto stack. Phase 2A and Phase 2B work
whether or not the Docker stack of `plan.md` Phase 5 is deployed yet.

The one place that changes later: `plan.md`'s rebuild webhook, the second half of Phase 2B. When the
lotto stack is running on the same VPS, n8n can reach it either over the public URL or, if both
stacks are attached to a shared Docker network, over the internal hostname. That is a decision for
when the receiver exists; it is not designed here.

---

## 3. The workflow, node by node (Phase 2A)

```
[Schedule Trigger  Mon/Wed/Sat 21:05 Europe/Dublin]
              |
              v
     [HTTP: archive] --> [HTTP: lottery.ie] --> [Code: parse, validate, cross-check]
                                                       |
                                                       v
                                    [Switch on status]
                                            |                      |                |
                                           ok                not published  failed / fallback
                                            v                      v                v
                              [HTTP: current irish500.csv]  [Count attempt]  [Gmail: FAILED]
                                                |                        |         ^
                                                v                        v         |
                                    [Code: read current CSV head] [IF attempts < 3]-+ no
                                                |                        | yes
                                                v                        v
                                    [IF date newer than top row]    [Wait 15m]
                                        |               |                |
                                     no |               | yes            +--> back to
                                        v               v                     [HTTP: archive]
                                   [No-op: end]   [Gmail: result]
                                                        |
                                                        v
                                              (Phase 2B: section 7)
```

Every `failed` item converges on **Gmail: FAILED**, including one raised by *Code: read current CSV
head* (3.6). **No-op: end** is the only exit without an email, and it is reached only after
proving the draw is already in `data/irish500.csv`.

The two HTTP nodes are **chained, not parallel**. The Code node reads both by name with
`$('Fetch archive')` and `$('Fetch lottery.ie')`, so it does not need them as inputs - and two
connections into one node input is not a join in n8n, it runs the node once per incoming branch.
Chaining gives one execution without a Merge node. With regular output (3.2) a failed archive
fetch still emits an item, so the rest of the chain still runs and the failure email still sends.

### 3.1 Schedule Trigger

- Mode: **Cron**, expression `5 21 * * 1,3,6` (Monday, Wednesday, Saturday at 21:05).
- Workflow **Settings > Timezone: Europe/Dublin** (section 2). Without it the cron runs on the
  instance default, which may be UTC.

Why 21:05: the draw is at about 20:00 and the result is published somewhere between 20:45 and 21:15.
21:05 catches most evenings, and the retry in 3.5 covers the late ones out to about 21:50.

### 3.2 HTTP Request - archive (primary source)

| Field | Value |
|:--|:--|
| URL | `https://irish.national-lottery.com/irish-lotto/results-archive-{{ $now.setZone('Europe/Dublin').year }}` |
| Method | GET |
| Response format | **Text** (property name `data`) |
| Timeout | 15000 ms |
| On error | **Continue (using regular output)** - the failed item stays on the main output carrying an `error` property, which is what 3.4's `archiveItem.error` check reads. Error output would send it down a second connector, leaving `$('Fetch archive').first()` undefined and the Code node throwing with no email sent |
| Header `User-Agent` | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` |
| Header `Accept-Language` | `en-IE,en-US;q=0.9` |

Both headers are the ones `scripts/scrape_lotto.py:44-51` sends. The site returns a different page to a
request with no browser User-Agent.

### 3.3 HTTP Request - lottery.ie (cross-check source)

Identical settings, URL `https://www.lottery.ie/results/lotto/history`.

### 3.4 Code node - parse, validate, cross-check

One Code node, **Run Once for All Items**, language JavaScript. Everything it rejects is recorded in
`notes`, which goes into the email.

**Two guarantees this node is built around.** Both are about making a wrong row or a silent evening
impossible, and both cost a few lines that look redundant until the day they fire:

1. **It always returns exactly one item, and never throws.** The whole body sits in `try`/`catch`,
   and the `catch` returns `status: 'failed'` with the exception message. A Code node that throws
   ends the execution with no email - the only failure the owner cannot see. Every return goes
   through one `result()` helper, so every field the email templates reference is always present and
   no downstream expression can throw either.
2. **`not_published` means the draw is genuinely absent, nothing else.** Three conditions that used
   to collapse into it are now `failed`, because each is a real fault wearing a quiet evening's
   clothes: a fetch that failed or returned a challenge page; a page the parser read to completion
   but found **zero** draws on, which cannot happen on pages that list the whole year; and a target
   date that **was** on the page and was thrown out by validation. Only "both pages parsed fine and
   neither lists today yet" waits and retries.

3. **One source carries the row, and says so.** When only one page lists the date, `one_source` goes
   down the **same path as `ok`** - duplicate check, row, email, and in Phase 2B the commit. It is
   built and proved by the same block 5, so the CSV contract and the round-trip apply to it
   identically; the only difference is that nothing cross-checked it, which `status`, `verified: false`
   and the subject line all state. **It does not retry.** From inside the node a site that publishes
   late and a parser that has gone blind look the same, so three attempts would only delay the row in
   the second case - and F-66 was the second case.

   What this trades away: the cross-check is the only thing that catches a Plus row leaking through
   one parser, so on this path a wrong date can reach `irish500.csv`, and from there every artifact.
   The subject line is what stands in its place. **A `one_source` email is opened, not filed** - check
   the row against the official result the same evening. Two of them in a row on the same site is a
   broken parser, not a slow site: fix it rather than letting one-sided rows become the normal
   evening.

`status` is therefore `ok`, `not_published`, `one_source` or `failed` on every path, and the Switch
node of 3.5 routes the four cases, with its fallback output covering a fifth that cannot currently
occur.

The three defences against Lotto Plus 1 and Plus 2, all from `scripts/scrape_lotto.py`:

- **The class token** (`:38`, `:107-112`). In the archive table every ball carries its game in the
  `class` attribute. The main draw's balls are tagged `irish-lotto`; the Plus rows are tagged
  `irish-lotto-plus-1` and `irish-lotto-plus-2`. The token is matched against the **split class list**,
  not by substring - `"irish-lotto-plus-1".includes("irish-lotto")` is true, which is exactly the trap.
- **One ball list per row** (`:97-102`). A row holding two ball lists cannot be tied to the date link
  with certainty, so it is dropped rather than guessed.
- **First block only, and only if no Plus precedes it** (`:152-158`). On lottery.ie the three games sit
  under repeated "Winning numbers" / "Bonus" labels with no game heading. The main draw is the first
  pair; if the word `Plus` appears before it, the page order has changed and the section is skipped.

```javascript
// Parse the Irish Lotto main draw from two sources and cross-check them.
// Mirrors scripts/scrape_lotto.py - keep the two in step if either page changes.

const MAX_BALL = 47;
const ARCHIVE_GAME_TOKEN = 'irish-lotto';           // Plus rows carry -plus-1 / -plus-2
const BALL_RE = /<div class="flex font-bold rounded-full[^"]*">(\d{1,2})<\/div>/g;
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const MON_FULL = ['January','February','March','April','May','June','July','August',
                  'September','October','November','December'];

const notes = [];
const pad = (n) => String(n).padStart(2, '0');

// A draw is valid only if it is 6 main + 1 bonus, every ball 1..47, all seven distinct.
// scripts/scrape_lotto.py:54-76
function buildDraw(key, main, bonus) {
  if (main.length !== 6 || bonus.length !== 1) {
    notes.push(`${key}: ${main.length} main + ${bonus.length} bonus, expected 6 + 1`);
    return null;
  }
  const all = [...main, ...bonus];
  if (all.some((n) => !Number.isInteger(n) || n < 1 || n > MAX_BALL)) {
    notes.push(`${key}: a ball is outside 1-${MAX_BALL}: ${all.join(',')}`);
    return null;
  }
  if (new Set(all).size !== 7) {
    notes.push(`${key}: duplicate ball in ${all.join(',')}`);
    return null;
  }
  return { key, main: [...main].sort((a, b) => a - b), bonus: bonus[0] };
}

// irish.national-lottery.com results archive. scripts/scrape_lotto.py:79-126
function parseArchive(html) {
  const draws = {};
  for (const row of html.match(/<tr[^>]*>[\s\S]*?<\/tr>/gi) || []) {
    const d = row.match(/\/irish-lotto\/results-(\d{2})-(\d{2})-(\d{4})/);
    if (!d) continue;                                   // defence 1: the link names the game
    const key = `${d[3]}-${d[2]}-${d[1]}`;

    const lists = row.match(/<ul class="balls">[\s\S]*?<\/ul>/g) || [];
    if (lists.length !== 1) {                           // defence 2: ambiguous row
      if (lists.length) notes.push(`${key}: row holds ${lists.length} ball lists, skipped`);
      continue;
    }

    const main = [], bonus = [];
    let wrongGame = false;
    const li = /<li class="([^"]*)">(\d+)<\/li>/g;
    let m;
    while ((m = li.exec(lists[0])) !== null) {
      const tokens = m[1].split(/\s+/);                  // defence 3: exact token, not substring
      if (!tokens.includes(ARCHIVE_GAME_TOKEN)) { wrongGame = true; break; }
      (tokens.includes('bonus-ball') ? bonus : main).push(Number(m[2]));
    }
    if (wrongGame) { notes.push(`${key}: balls not tagged ${ARCHIVE_GAME_TOKEN}, skipped`); continue; }

    const draw = buildDraw(key, main, bonus);
    if (draw) draws[key] = draw;
  }
  return draws;
}

// lottery.ie history page. scripts/scrape_lotto.py:129-168
function parseLotteryIe(html) {
  const draws = {};
  // The newest draw is headed "Last draw, ..."; every older one "Draw, ...". Matching
  // only "Draw, " skipped the one draw the workflow is for, every run (F-66).
  const heads = [...html.matchAll(/<h2 aria-label="(?:Last draw|Draw), ([^"]+)"/g)];
  for (let i = 0; i < heads.length; i++) {
    const section = html.slice(heads[i].index,
                               i + 1 < heads.length ? heads[i + 1].index : html.length);

    const label = heads[i][1].replace(/(\d+)(st|nd|rd|th)/, '$1');   // "Monday, September 14, 2026"
    const parts = label.match(/([A-Za-z]+) (\d{1,2}), (\d{4})$/);
    if (!parts) { notes.push(`lottery.ie: cannot parse date "${heads[i][1]}"`); continue; }
    const monthIdx = MON_FULL.indexOf(parts[1]);
    if (monthIdx === -1) { notes.push(`lottery.ie: unknown month "${parts[1]}"`); continue; }
    const key = `${parts[3]}-${pad(monthIdx + 1)}-${pad(Number(parts[2]))}`;

    const mainAt = section.indexOf('>Winning numbers<');
    const bonusAt = section.indexOf('>Bonus<');
    if (mainAt === -1 || bonusAt <= mainAt) continue;
    if (section.slice(0, mainAt).includes('Plus')) {     // a Plus game precedes the main block
      notes.push(`${key}: Plus game before the main draw on lottery.ie, section skipped`);
      continue;
    }

    const grab = (s) => [...s.matchAll(BALL_RE)].map((x) => Number(x[1]));
    const draw = buildDraw(key, grab(section.slice(mainAt, bonusAt)),
                                grab(section.slice(bonusAt)).slice(0, 1));
    if (draw) draws[key] = draw;
  }
  return draws;
}

// --- main -------------------------------------------------------------------
// This node must ALWAYS return exactly one item and must NEVER throw. A thrown
// Code node ends the execution with no email at all - the one failure mode that
// is invisible. Every return goes through result(), so every downstream
// expression finds every field present and cannot throw either.

const CSV_ROW_RE =
  /^\d{2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}(,\d{2}){7}$/;

function result(status, extra) {
  return [{ json: Object.assign({
    status, targetKey: null, reason: '', notes, httpErrors: [],
    csvDate: null, csvRow: null, numbers: [], bonus: null, sources: [],
    archive: null, lotteryIe: null, verified: false,
  }, extra) }];
}

// Set to 'yyyy-MM-dd' to test the node against a draw that has already happened, then
// put it back to null. Both pages must still list that date - lottery.ie's history page
// holds only about the last five draws, so an override older than that is pointless.
const TARGET_OVERRIDE = null;

let targetKey = null;
try {
  targetKey = TARGET_OVERRIDE || $now.setZone('Europe/Dublin').toFormat('yyyy-MM-dd');

  // 1. Did we actually get two pages? A fetch failure is never "not published".
  const httpErrors = [];
  const read = (node) => {
    const item = $(node).first();          // regular output (3.2): always an item
    if (!item) { httpErrors.push(`${node}: no item returned`); return ''; }
    if (item.json.error) { httpErrors.push(`${node}: ${item.json.error}`); return ''; }
    const html = item.json.data;
    if (typeof html !== 'string') { httpErrors.push(`${node}: no text body`); return ''; }
    if (html.length < 500) { httpErrors.push(`${node}: body only ${html.length} bytes`); return ''; }
    if (/Just a moment|cf-browser-verification/i.test(html)) {
      httpErrors.push(`${node}: bot challenge page, User-Agent rejected`); return '';
    }
    return html;
  };
  const archiveHtml = read('Fetch archive');
  const lotteryHtml = read('Fetch lottery.ie');
  if (httpErrors.length) {
    return result('failed', { targetKey, httpErrors,
                              reason: 'one or both sources could not be fetched' });
  }

  const fromArchive = parseArchive(archiveHtml);
  const fromLottery = parseLotteryIe(lotteryHtml);

  // 2. Both pages list many past draws. Zero parsed cannot mean "no draw yet" -
  //    it means the markup changed and the parser is blind. This is the guard
  //    that stops a silent parser failure looking like a quiet evening.
  if (!Object.keys(fromArchive).length || !Object.keys(fromLottery).length) {
    const dead = !Object.keys(fromArchive).length ? 'the archive' : 'lottery.ie';
    return result('failed', { targetKey,
      reason: `parsed 0 draws from ${dead} - page structure changed` });
  }

  const a = fromArchive[targetKey] || null;
  const b = fromLottery[targetKey] || null;

  // 3. A note naming the target date means the draw WAS on the page and
  //    validation rejected it. That is a failure, not "not published yet".
  if (!a && !b) {
    if (notes.some((n) => n.startsWith(targetKey))) {
      return result('failed', { targetKey,
        reason: `${targetKey} is published but failed validation - see notes` });
    }
    return result('not_published', { targetKey });
  }
  // One page has it and the other does not. The row is real, so it goes down the same
  // path as ok and is built and proved the same way - but nothing cross-checked it, so
  // it leaves as one_source. The email subject is the only thing that says so.
  const verified = Boolean(a && b);
  const draw = a || b;
  const sources = [a && 'irish.national-lottery.com', b && 'lottery.ie'].filter(Boolean);

  // 4. Cross-check, when there are two rows to check. scripts/scrape_lotto.py:185-208
  //    Two sources that disagree is the one case where nothing is usable: one of them is
  //    a Plus row or a bad parse, and there is no way to tell which from here.
  if (verified && (a.main.join(',') !== b.main.join(',') || a.bonus !== b.bonus)) {
    return result('failed', { targetKey, archive: a, lotteryIe: b,
      reason: `sources disagree - archive ${a.main.join(',')}+${a.bonus}, ` +
              `lottery.ie ${b.main.join(',')}+${b.bonus}` });
  }

  // 5. Build the row, then prove the finished string against the section 4
  //    contract and read it back. Nothing leaves as ok unless the exact text
  //    that would be written to the CSV parses back to the numbers checked above.
  const [y, mo, d] = targetKey.split('-').map(Number);
  const csvDate = `${pad(d)} ${MON[mo - 1]} ${y}`;
  const csvRow = [csvDate, ...draw.main.map(pad), pad(draw.bonus)].join(',');
  if (!CSV_ROW_RE.test(csvRow)) {
    return result('failed', { targetKey,
      reason: `built row breaks the CSV contract: "${csvRow}"` });
  }
  const back = csvRow.split(',');
  if (back[0] !== csvDate ||
      back.slice(1, 7).map(Number).join(',') !== draw.main.join(',') ||
      Number(back[7]) !== draw.bonus) {
    return result('failed', { targetKey,
      reason: `row does not round-trip: "${csvRow}"` });
  }

  return result(verified ? 'ok' : 'one_source', { targetKey, csvDate, csvRow,
    numbers: draw.main, bonus: draw.bonus, archive: a, lotteryIe: b, sources, verified,
    reason: verified ? ''
      : `only ${a ? 'the archive' : 'lottery.ie'} has ${targetKey} - row not cross-checked` });

} catch (err) {
  return result('failed', { targetKey,
    reason: `code node exception: ${err && err.message ? err.message : err}` });
}
```

Node-reference note: `$('Fetch archive')` must match the exact node names you give the two HTTP
nodes. If your n8n version puts a text response under a different property than `data`, adjust the
two `.data` reads - run the node once and look at the output panel.

### 3.5 The Switch node and the retry

Three statuses need three destinations, so use **one Switch node**, not IF nodes. An IF has exactly
two outputs, so three routes would take two of them chained; worse, the two tests cannot be combined
into one IF whatever combinator is chosen - `AND` is never true, because `status` cannot hold two
values at once, and `OR` is true for both `ok` and `not_published`, which would send a
`not_published` item down the `ok` branch and email a result built from `null` fields.

**Switch**, Mode **Rules**, four rules on `{{ $json.status }}`, each with *Rename Output* on:

| # | Condition | Output name | Goes to |
|:--|:--|:--|:--|
| 1 | equals `ok` | `ok` | 3.6, the duplicate check |
| 2 | equals `not_published` | `not published` | the attempt counter below, then Wait and retry |
| 3 | equals `one_source` | `one source` | 3.6, the duplicate check - wire it into the same node as `ok` |
| 4 | equals `failed` | `failed` | **Send failure email** (section 5) |

**Set Options > Fallback Output > Extra Output, and wire it to Send failure email.** This is the
one setting on this node that can reintroduce a silent failure: the default is *None*, which
**discards** an item matching no rule. `status` is only ever those three values today, so the
fallback should never fire - which is exactly why it must not be left pointing at the bin. If a
future edit adds a status and forgets a rule, the fallback turns a vanished draw into an email.

**Every route except "already in the CSV" ends in an email.** Silence is not a state this workflow
is allowed to reach.

**The attempt counter must reset itself.** A bare counter in workflow static data persists across
executions, so after three lifetime attempts the workflow would give up on every future draw - and
do it silently. Key the counter on the draw date; a new date then resets it with no maintenance:

```javascript
// Code node "Count attempt", between the not_published output and the Wait node.
const store = $getWorkflowStaticData('global');
const key = $json.targetKey;
if (store.retryKey !== key) { store.retryKey = key; store.attempts = 0; }
store.attempts += 1;
return [{ json: { ...$json, attempt: store.attempts,
                  reason: `no result published by 21:50 (${store.attempts} attempts)` } }];
```

Then an **IF "attempts left"**: `{{ $json.attempt }}` less than `3` -> **Wait** 15 minutes -> back to
**Fetch archive**, the head of the chain, so both sources are re-fetched. Otherwise -> **Send
failure email**. Three attempts at 21:05, 21:20 and 21:35 cover publication out to about 21:50.
Only `not_published` retries: a `one_source` item already has its row, and waiting for a second
source that may be behind a changed page would only delay it.

### 3.6 HTTP Request - the current CSV

| Field | Value |
|:--|:--|
| URL | `https://raw.githubusercontent.com/alex2t/lotto-ml/main/data/irish500.csv` |
| Response format | Text |

Then an IF node comparing dates. The file is **newest-first**, so the current newest draw is line 2
(line 1 is the header):

```
{{ $json.data.split('\n')[1].split(',')[0] }}      // e.g. "16 Sep 2026"
```

**Guard that expression, and compare dates rather than strings.** Two faults to avoid. If the fetch
404s or returns an empty body, `split('\n')[1]` is `undefined` and `.split(',')` throws - losing a
draw that has just passed every check in 3.4. And an equality test against line 2 only catches a
re-run of the **newest** draw: a date that is older but already present is not equal to the top row,
so it would be reported as new, emailed, and in Phase 2B inserted after the header - a duplicate row,
out of order, against both rules in section 4.

Give this node **On Error: Continue (using regular output)** too, and decide in a Code node:

```javascript
// Code node "Read current CSV head".
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const toStamp = (s) => {
  const m = /^(\d{2}) ([A-Za-z]{3}) (\d{4})$/.exec(s || '');
  const i = m ? MON.indexOf(m[2]) : -1;
  return i === -1 ? null : Date.UTC(Number(m[3]), i, Number(m[1]));
};

const parsed = $('Parse and validate').first().json;
const item = $('Fetch current CSV').first();
const csv = item && !item.json.error && typeof item.json.data === 'string' ? item.json.data : '';
const newest = (csv.split('\n')[1] || '').split(',')[0] || null;

const fail = (reason) => [{ json: { ...parsed, status: 'failed', newest, reason } }];

// Cannot prove the draw is absent, so do not claim it is new. Email it and let a
// person look. Never end quietly on a CSV that could not be read.
if (!newest) return fail('could not read the current irish500.csv to check for a duplicate');

const newestAt = toStamp(newest);
const scrapedAt = toStamp(parsed.csvDate);
if (newestAt === null) return fail(`top row of irish500.csv is not a date: "${newest}"`);
if (scrapedAt === null) return fail(`scraped date is not in DD Mon YYYY form: "${parsed.csvDate}"`);

if (scrapedAt === newestAt) return [{ json: { ...parsed, newest, isNew: false } }];
if (scrapedAt < newestAt) {
  return fail(`scraped ${parsed.csvDate} is older than the newest row ${newest} - ` +
              `this workflow only ever scrapes the current draw`);
}
return [{ json: { ...parsed, newest, isNew: true } }];
```

**To exercise this node before a draw exists**, pin two items on *Parse and validate* - one whose
`csvDate` is the top row of `data/irish500.csv` and one later than it. Both are written out in
section 8, step 4; paste the whole item, because flipping only `status` to `ok` leaves `csvDate`
null and this node will (correctly) refuse it.

The IF after it tests `{{ $json.isNew }}` is true. False is the **one silent exit** in the whole
workflow, and it is silent only because it has proved the draw is already there. Everything else,
including a `failed` item from this node, routes to **Send failure email**.

`raw.githubusercontent.com` caches for a few minutes. That is harmless here - a stale copy can only
make the workflow think a draw is missing, and the Phase 2B commit re-reads the file through the
GitHub API, which is not cached.

### 3.7 Gmail - the result email

- Resource: Message, Operation: Send, To: the owner's address.
- Subject: `Irish Lotto Scrape: {{ $json.csvDate }}{{ $json.verified ? '' : '  [ONE SOURCE - NOT CROSS-CHECKED]' }}`

  **The subject is where the warning has to live**, because it is the only part read without opening
  anything. On the `one_source` path it is the whole safeguard: the row has already been through the
  duplicate check and, in Phase 2B, the commit.

- Body (plain text):

```
Draw:    {{ $json.csvDate }}
Numbers: {{ $json.numbers.join('  ') }}
Bonus:   {{ $json.bonus }}
{{ $json.verified ? '' : '
Only ' + $json.sources[0] + ' listed this draw. Nothing cross-checked
these numbers - compare them with the official result today.
' }}
CSV line for data/irish500.csv (insert directly under the header):
{{ $json.csvRow }}

Checks
  6 main numbers .................. pass
  1 bonus number .................. pass
  all seven in 1-47 ............... pass
  all seven distinct .............. pass
  main draw, not Plus 1 / Plus 2 .. pass
  CSV contract and round-trip ..... pass
  both sources agree .............. {{ $json.verified ? $json.sources.join(' + ') : 'NO - only ' + $json.sources[0] + ' had it' }}

Notes from the parser (rows it rejected; usually the Plus games):
{{ $json.notes.join('\n') }}
```

The point of printing `csvRow` in full is that during the monitoring week it is what you compare
against the published result, and it is what you could paste by hand if you wanted the draw in before
Phase 2B exists.

---

## 4. The CSV contract

From `data/irish500.csv` itself and `scripts/scrape_lotto.py:68-75,236-279`.

- **Header, line 1, exactly:** `Date,Num1,Num2,Num3,Num4,Num5,Num6,Bonus`
- **Date format:** `DD Mon YYYY` - zero-padded day, three-letter English month, four-digit year.
- **Numbers:** all seven zero-padded to two digits, main numbers ascending, bonus last.
- **A row:** `16 Sep 2026,04,07,19,20,35,42,31`
- **Order: newest first.** Line 2 is the most recent draw, the last line is `02 Jan 2021,...`. A new
  draw is **inserted after line 1**, never appended to the end.
- **Line endings: LF only**, and the file ends with a single newline. `.gitattributes:5`
  (`data/**/*.csv text eol=lf`) pins this, so a CRLF commit would be renormalised and show as a
  whole-file diff. Any Code node that rebuilds the file must join with `'\n'`.
- **De-duplication is by date.** If the date is already present the draw is skipped; an existing row
  is never corrected in place.
- **`data/irish500.csv` is already tracked by git and is not ignored.** `.gitignore` has `# data/`
  commented out. No gitignore change is needed for Phase 2B.

The file has 598 data rows covering 02 Jan 2021 to 16 Sep 2026.

---

## 5. The error path

One Gmail node named **Send failure email**, with every failure branch routed into it, plus a second
workflow with an **Error Trigger** node for anything that throws outright (an n8n restart mid-run, a
credential expiry, a node exception).

- Subject: `Irish Lotto Scrape FAILED: {{ $json.targetKey }}`
- Body:

```
The scrape for {{ $json.targetKey }} did not produce a usable row.

Reason:
{{ $json.reason }}


HTTP problems:
{{ $json.httpErrors.join('\n') }}

What each source gave for this date:
  archive:     {{ JSON.stringify($json.archive) }}
  lottery.ie:  {{ JSON.stringify($json.lotteryIe) }}

Parser notes (rows rejected, and why):
{{ $json.notes.join('\n') }}

Execution: {{ $execution.url }}
```

What the reasons mean when one arrives:

| Reason | What happened | What to do |
|:--|:--|:--|
| `only the archive has ... - row not cross-checked` | one site did not list the date: it has not published, or its markup changed. This arrives on the **result** email with `[ONE SOURCE]` in the subject, not the failure email, and the row has been committed | check the numbers against the official result the same evening. If the same site is missing every draw, that parser is broken, not the site - `Last draw, ...` vs `Draw, ...` was exactly this (F-66) |
| `sources disagree - ...` | the two sites gave different numbers | **do not commit anything**; check the official result by hand. This is the check that catches a Plus row leaking through one parser |
| `... is outside 1-47` / `duplicate ball` | the parse picked up the wrong element | the page markup changed; compare with `tests/fixtures/*.html` |
| `no result published by 21:50 (3 attempts)` | both pages parsed fine, neither listed the date | usually a delayed publication; check manually |
| `one or both sources could not be fetched` | HTTP error, timeout, empty body, or a bot-challenge page | read `HTTP problems` in the email; check the site is up and the User-Agent header is still being sent |
| `parsed 0 draws from ... - page structure changed` | the fetch worked and the parser found nothing on a page that lists the whole year | the markup changed. Compare the live page with `tests/fixtures/*.html` and fix both the Code node and `scripts/scrape_lotto.py` |
| `... is published but failed validation - see notes` | the date was on the page and `buildDraw()` rejected it | read `notes`: wrong ball count, a duplicate, or a ball outside 1-47. Never transcribe the row by hand from the page - find out why it failed |
| `code node exception: ...` | a bug in the Code node itself, or a renamed HTTP node | the `$('Fetch archive')` references must match the node names exactly |
| `could not read the current irish500.csv ...` | the raw.githubusercontent fetch failed | the draw may be fine; re-run once GitHub is reachable |

Fallback while a parser is being fixed: run `python scripts/scrape_lotto.py --dry-run` on the PC. It
prints the rows it would add, using the tested parser, and writes nothing.

---

## 6. The monitoring week (Phase 2A)

Leave the workflow email-only for one full week - three draws, Monday, Wednesday and Saturday. For
each email, check:

1. The six numbers and the bonus match the official result on lottery.ie.
2. They are the **main Lotto** numbers, not Plus 1 or Plus 2. Look at all three on the site and
   confirm the email carries the first.
3. `csvRow` is in the exact CSV format - day zero-padded, month as `Jan`..`Dec`, every number two
   digits, seven commas.
4. The email arrived within about ten minutes of 21:05.
5. `notes` is **empty**, or holds only a note you can explain. Do not expect notes about rejected
   Plus rows: the archive table carries the main draw only - `tests/fixtures/archive_rows.html` has
   three rows, all tagged `irish-lotto`, and no `irish-lotto-plus-1` or `-plus-2` anywhere - and on
   lottery.ie the word `Plus` appears in prose after the main block, not before it. Both Plus
   defences of 3.4 are guards against the page changing, not filters that fire each run. A note that
   a Plus row was rejected means the markup has changed; read it, do not tick it off.

**Go/no-go for Phase 2B:** three consecutive draws, all five points correct, no failure email in
between. Anything less, fix and restart the week.

---

## 7. Phase 2B - commit to `data/irish500.csv`

Added after the monitoring week, as the last nodes in the chain, **after** the result email - so a
commit can never happen without the email that describes it.

1. **GitHub node - get the file.** Resource: File, Operation: Get, repository `alex2t/lotto-ml`,
   file path `data/irish500.csv`, reference `main`. The response carries the content (base64) and the
   file's `sha`.
2. **Code node - insert the row.**

```javascript
const file = $('Get irish500.csv').first().json;
const csv = Buffer.from(file.content, 'base64').toString('utf8');
const lines = csv.split('\n');
const row = $('Parse and validate').first().json.csvRow;
const newest = (lines[1] || '').split(',')[0];

if (newest === row.split(',')[0]) {
  return [{ json: { skip: true, reason: `${newest} is already the newest row` } }];
}

lines.splice(1, 0, row);                     // newest-first: the new draw goes under the header
return [{ json: { skip: false, content: lines.join('\n'), sha: file.sha, row } }];
```

3. **GitHub node - edit the file.** Resource: File, Operation: Edit, same repository and path, branch
   `main`, content from the previous node, commit message
   `Add draw {{ $json.row.split(',')[0] }} (n8n{{ $json.verified ? '' : ', one source' }})`, so a row
   nothing cross-checked says so in `git log` as well as in the email. Depending on the n8n version the node may take the
   `sha` explicitly or fetch it itself - check the node's fields; if it is exposed, pass the `sha`
   from step 2, which is what makes the write fail safely if the file changed in between.

Guards, all of which must hold before the commit node runs:

- the Code node returned `status: "ok"` (both sources agreed);
- the scraped date is not already the newest row;
- the result email has been sent.

4. **Code node - sign the draw for the receiver.** The commit is the history; this is what makes
   the site change. The receiver appends the draw to the VPS's own CSV and rebuilds - see
   [`lottodraw.md`](lottodraw.md).

```javascript
const crypto = require('crypto');
const draw = $('Parse and validate').first().json;
// The field names are the ones result() in section 3.4 writes (F-76).
const body = JSON.stringify({
  date: draw.targetKey,   // "2026-09-23", yyyy-MM-dd
  main: draw.numbers,     // the six main numbers, sorted
  bonus: draw.bonus,
});
const signature = crypto
  .createHmac('sha256', $env.REBUILD_SECRET)
  .update(body)
  .digest('hex');
return [{ json: { body, signature } }];
```

5. **HTTP Request node - the rebuild.** `POST http://lotto-rebuild:8080/rebuild`, header
   `X-Lotto-Signature: {{$json.signature}}`, body `{{$json.body}}` sent **raw** with
   `Content-Type: application/json`. The signature covers the exact bytes, so letting n8n
   re-serialise the object produces a 401 that looks like a wrong secret.

   The response carries `state` and `csv_rows`. `rebuilt`, `already had it` and
   `rebuilt stale artifacts` are all success - a retried execution is meant to be free. Anything
   else, or a `csv_rows` that does not match the row count just committed to GitHub, routes into
   the same failure email as section 5. That includes `conflict` (409): the receiver already
   holds that date with other numbers, and the body's `in_csv` and `posted` say which (F-72).

**`quickpick.py` never runs on the VPS** (`plan.md` 3.5). The models are the owner's, and the site
does not read them; run it on the PC when you want new picks, then `/lotto-verify`.

---

## 8. Verification, before trusting any of it

Do these in order. The backtest is the one that matters.

1. **Manual run.** Disable the Schedule Trigger, use "Execute Workflow", and read the Code node's
   output panel. On a non-draw day it should return `not_published` - which is itself a useful check
   that the date logic uses Irish time. To exercise the real pages instead of a pinned item, set
   `TARGET_OVERRIDE` in the Code node to a date inside lottery.ie's history window (about the last
   five draws) and put it back to `null` afterwards - a left-behind override would scrape the same
   old draw every evening. Note what follows from that once the retry is wired: the run
   waits 15 minutes three times and emails a failure at about 21:50. While building, pin the Code
   node's output (step 4) or disconnect the Wait node, or every manual run costs 45 minutes and ends
   in an email you already expected.

2. **Backtest against the CSV.** Point the archive node at `results-archive-2025` and change the Code
   node's last block to return every parsed draw instead of only `targetKey`. Copy the output into a
   file and compare each produced line against the matching date in `data/irish500.csv` - 105
   draws of known-good answers (the number of 2025 draws in the file), all already verified by the Python scraper's cross-check. Every line
   must match exactly, including zero padding and ordering. If the Plus filtering is wrong, this is
   where it shows, because a Plus row's numbers will not match the recorded draw.

3. **Cross-check one live draw.** On the PC, from the repo root, run
   `python scripts/scrape_lotto.py --dry-run`. It prints the rows it would add, using the tested
   parser. It must print the same row the email carried.

4. **Drive the downstream path with pinned data.** On a non-draw day the Code node returns
   `not_published`, so the Switch's `ok` branch never runs and 3.6, 3.7 and the duplicate check stay
   untested. Do not add a test override to the Code node - pin its output instead. Open **Parse and
   validate**, click the pin icon on its output panel, choose **Edit Output**, and paste one of the
   items below. Downstream nodes then run against it on every manual execution.

   **Pinned data is used by manual executions only; a scheduled production run ignores it.** That is
   what makes this safe to leave pinned while building - but unpin it before the monitoring week, so
   what you are watching is the real parser.

   Two ways the pin appears not to work. The node must show the **thumbtack badge** on the canvas -
   pasting into *Edit Output* without saving leaves no pin, and the node simply runs. And the run
   must be **Execute Workflow**, not *Test step* on a node further down: executing one node pulls
   whatever the previous run left upstream, so you get the live `not_published` item back, with
   `csvDate: null`. If a `not_published` item ever reaches 3.6 during a full run, the Switch is
   wired to the wrong outputs - that status belongs to *Count attempt*.

   Already in the CSV, expect the quiet exit and **no email** (`isNew: false`):

   ```json
   [{ "status": "ok", "targetKey": "2026-09-16", "reason": "", "notes": [], "httpErrors": [],
      "csvDate": "16 Sep 2026", "csvRow": "16 Sep 2026,04,07,19,20,35,42,31",
      "numbers": [4, 7, 19, 20, 35, 42], "bonus": 31,
      "sources": ["irish.national-lottery.com", "lottery.ie"], "archive": null, "lotteryIe": null }]
   ```

   A genuinely new draw, expect **Gmail: result** (`isNew: true`). The date is later than the top row
   of `data/irish500.csv`, which is what 3.6 now compares:

   ```json
   [{ "status": "ok", "targetKey": "2026-09-19", "reason": "", "notes": [], "httpErrors": [],
      "csvDate": "19 Sep 2026", "csvRow": "19 Sep 2026,03,11,24,28,33,45,08",
      "numbers": [3, 11, 24, 28, 33, 45], "bonus": 8,
      "sources": ["irish.national-lottery.com", "lottery.ie"], "archive": null, "lotteryIe": null }]
   ```

   Change `"status"` to `"failed"` with a `"reason"` to exercise the Switch's `failed` output, and to
   `"not_published"` to exercise the counter, the Wait and the three-attempt cap. Both must end in an
   email. Pin a copy with `"status": "one_source"`, `"verified": false` and one entry in `"sources"`
   to check that the duplicate check accepts it and the subject line carries the warning. The first payload is the real output of the Code node run against
   `tests/fixtures/`, so the shape matches `result()` exactly - a hand-written pin that omits a field
   tests the template as much as the route.

5. **Force the failure path.** Point the lottery.ie node at a URL that 404s and run manually. The
   failure email must arrive, name the node, and carry the HTTP problem. Then break the other one the
   same way. A failure path that has never fired is not a safeguard.

6. **Check the CSV shape before the first commit.** After Phase 2B's first run, `git diff` on the repo
   must show exactly one added line, in position 2, with no line-ending change anywhere else in the
   file. A whole-file diff means the content was rebuilt with CRLF.

---

## Where the rules came from

| Rule | Source |
|:--|:--|
| browser headers | `scripts/scrape_lotto.py:29,44-51` |
| archive parsing, `irish-lotto` class token, one-ball-list rule | `scripts/scrape_lotto.py:38,79-126` |
| lottery.ie parsing, first block, Plus-before-main rule | `scripts/scrape_lotto.py:41,129-168` |
| 6 + 1, range 1-47, seven distinct | `scripts/scrape_lotto.py:54-76` |
| cross-source agreement | `scripts/scrape_lotto.py:185-208` |
| CSV row format, prepend, date de-duplication | `scripts/scrape_lotto.py:68-75,211-279` |
| LF line endings | `.gitattributes:5`, F-44 in `issue.md` |
| what these rules are tested by | `tests/test_scraper_sources.py`, `tests/fixtures/*.html` |
| roadmap context | `plan.md` sections 3.4 and Phase 2 |
