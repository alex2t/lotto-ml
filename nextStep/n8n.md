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
              +--> [HTTP: archive]  --+
              |                       +--> [Code: parse, validate, cross-check]
              +--> [HTTP: lottery.ie]-+                |
                                                       v
                                        [IF status == "ok"] --no--> [IF "not_published"]
                                                |                        |        |
                                                |                     yes|        |no
                                                v                        v        v
                              [HTTP: current irish500.csv]         [Wait 15m]  [Gmail: FAILED]
                                                |                        |
                                                v                     (retry, max 3)
                                    [IF date newer than top row]
                                        |               |
                                     no |               | yes
                                        v               v
                                   [No-op: end]   [Gmail: result]
                                                        |
                                                        v
                                              (Phase 2B: section 7)
```

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
| On error | **Continue (using error output)** - the Code node reports the status, rather than the run dying with no email |
| Header `User-Agent` | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` |
| Header `Accept-Language` | `en-IE,en-US;q=0.9` |

Both headers are the ones `scripts/scrape_lotto.py:44-51` sends. The site returns a different page to a
request with no browser User-Agent.

### 3.3 HTTP Request - lottery.ie (cross-check source)

Identical settings, URL `https://www.lottery.ie/results/lotto/history`.

### 3.4 Code node - parse, validate, cross-check

One Code node, **Run Once for All Items**, language JavaScript. It never throws: it returns a
`status` of `ok`, `not_published` or `failed`, so the IF nodes can route the three cases. Everything
it rejects is recorded in `notes`, which goes into the email.

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
  const heads = [...html.matchAll(/<h2 aria-label="Draw, ([^"]+)"/g)];
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
const archiveItem = $('Fetch archive').first().json;
const lotteryItem = $('Fetch lottery.ie').first().json;
const archiveHtml = archiveItem.data || '';
const lotteryHtml = lotteryItem.data || '';

const today = $now.setZone('Europe/Dublin');
const targetKey = today.toFormat('yyyy-MM-dd');
const httpErrors = [];
if (archiveItem.error || archiveHtml.length < 500) httpErrors.push('archive fetch failed or empty');
if (lotteryItem.error || lotteryHtml.length < 500) httpErrors.push('lottery.ie fetch failed or empty');

const fromArchive = parseArchive(archiveHtml);
const fromLottery = parseLotteryIe(lotteryHtml);
const a = fromArchive[targetKey];
const b = fromLottery[targetKey];

function fail(reason) {
  return [{ json: { status: 'failed', reason, targetKey, notes, httpErrors,
                    archive: a || null, lotteryIe: b || null } }];
}

if (!a && !b) {
  // Neither source has today's draw yet: not an error until the retries run out.
  return [{ json: { status: 'not_published', targetKey, notes, httpErrors } }];
}
if (!a || !b) return fail(`only ${a ? 'the archive' : 'lottery.ie'} has ${targetKey}`);

// Cross-check. scripts/scrape_lotto.py:185-208
const sameMain = a.main.join(',') === b.main.join(',');
if (!sameMain || a.bonus !== b.bonus) {
  return fail(`sources disagree - archive ${a.main.join(',')}+${a.bonus}, ` +
              `lottery.ie ${b.main.join(',')}+${b.bonus}`);
}

const [y, mo, d] = targetKey.split('-').map(Number);
const csvDate = `${pad(d)} ${MON[mo - 1]} ${y}`;
const csvRow = [csvDate, ...a.main.map(pad), pad(a.bonus)].join(',');

return [{ json: {
  status: 'ok', targetKey, csvDate, csvRow,
  numbers: a.main, bonus: a.bonus,
  sources: ['irish.national-lottery.com', 'lottery.ie'],
  checks: {
    mainCount: a.main.length === 6, bonusCount: 1, range: true, distinct: true,
    sourcesAgree: true, notPlus: true,
  },
  notes,
} }];
```

Node-reference note: `$('Fetch archive')` must match the exact node names you give the two HTTP
nodes. If your n8n version puts a text response under a different property than `data`, adjust the
two `.data` reads - run the node once and look at the output panel.

### 3.5 IF nodes and the retry

- **IF "parsed ok"**: `{{ $json.status }}` equals `ok` -> continue to 3.6. Otherwise -> next IF.
- **IF "not published yet"**: `{{ $json.status }}` equals `not_published` -> **Wait** node, 15
  minutes, then back to the two HTTP nodes. Cap it at 3 attempts (a counter in workflow static data,
  or three explicit Wait/retry branches - the first is tidier, the second is easier to read on the
  canvas). After the third, route to the error email with reason "no result published by 21:50".
- Anything else (`failed`) goes straight to the error email of section 5.

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

If that equals the scraped `csvDate`, the draw is already in the repository: end quietly, no email.
Otherwise continue.

`raw.githubusercontent.com` caches for a few minutes. That is harmless here - a stale copy can only
make the workflow think a draw is missing, and the Phase 2B commit re-reads the file through the
GitHub API, which is not cached.

### 3.7 Gmail - the result email

- Resource: Message, Operation: Send, To: the owner's address.
- Subject: `Irish Lotto Scrape: {{ $json.csvDate }}`
- Body (plain text):

```
Draw:    {{ $json.csvDate }}
Numbers: {{ $json.numbers.join('  ') }}
Bonus:   {{ $json.bonus }}

CSV line for data/irish500.csv (insert directly under the header):
{{ $json.csvRow }}

Checks
  6 main numbers .................. pass
  1 bonus number .................. pass
  all seven in 1-47 ............... pass
  all seven distinct .............. pass
  main draw, not Plus 1 / Plus 2 .. pass
  both sources agree .............. {{ $json.sources.join(' + ') }}

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
| `only the archive has ...` / `only lottery.ie has ...` | one site has not published yet, or its markup changed | re-run manually in an hour; if it repeats, the parser for the silent source needs fixing |
| `sources disagree - ...` | the two sites gave different numbers | **do not commit anything**; check the official result by hand. This is the check that catches a Plus row leaking through one parser |
| `... is outside 1-47` / `duplicate ball` | the parse picked up the wrong element | the page markup changed; compare with `tests/fixtures/*.html` |
| `no result published by 21:50` | nothing on either page an hour after the draw | usually a delayed publication; check manually |
| `archive fetch failed or empty` | HTTP error, block, or an empty body | check the site is up and the User-Agent header is still being sent |

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
5. The parser notes mention the Plus rows being rejected - that is the filter proving it ran.

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
   `Add draw {{ $json.row.split(',')[0] }} (n8n)`. Depending on the n8n version the node may take the
   `sha` explicitly or fetch it itself - check the node's fields; if it is exposed, pass the `sha`
   from step 2, which is what makes the write fail safely if the file changed in between.

Guards, all of which must hold before the commit node runs:

- the Code node returned `status: "ok"` (both sources agreed);
- the scraped date is not already the newest row;
- the result email has been sent.

**After the commit, the website does not change yet.** `data/*.json` is rebuilt by `drawpick.py`, and
the models by `quickpick.py` (`scripts/CLAUDE.md`). The rebuild trigger - `plan.md`'s
`POST /api/webhook/rebuild` to the VPS, which runs the `data-engine` container - is the second half of
Phase 2B and is not designed here. Until it exists, run `python drawpick.py` and `python quickpick.py`
by hand after each ingested draw, then `/lotto-verify`.

---

## 8. Verification, before trusting any of it

Do these in order. The backtest is the one that matters.

1. **Manual run.** Disable the Schedule Trigger, use "Execute Workflow", and read the Code node's
   output panel. On a non-draw day it should return `not_published` - which is itself a useful check
   that the date logic uses Irish time.

2. **Backtest against the CSV.** Point the archive node at `results-archive-2025` and change the Code
   node's last block to return every parsed draw instead of only `targetKey`. Copy the output into a
   file and compare each produced line against the matching date in `data/irish500.csv` - 105
   draws of known-good answers (the number of 2025 draws in the file), all already verified by the Python scraper's cross-check. Every line
   must match exactly, including zero padding and ordering. If the Plus filtering is wrong, this is
   where it shows, because a Plus row's numbers will not match the recorded draw.

3. **Cross-check one live draw.** On the PC, from the repo root, run
   `python scripts/scrape_lotto.py --dry-run`. It prints the rows it would add, using the tested
   parser. It must print the same row the email carried.

4. **Force the failure path.** Point the lottery.ie node at a URL that 404s and run manually. The
   failure email must arrive, name the node, and carry the HTTP problem. Then break the other one the
   same way. A failure path that has never fired is not a safeguard.

5. **Check the CSV shape before the first commit.** After Phase 2B's first run, `git diff` on the repo
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
