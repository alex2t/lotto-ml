# What is left - status on 2026-09-25

The one list of what is still to do before the site is published, and how to test the n8n
POST first. It replaces [`recap.md`](recap.md), which is kept as the record of 2026-09-24.
Open defects are in [`../issue.md`](../issue.md): its Priority summary lists what is open,
its Appendix A everything already fixed (86 items).

---

## 1. Where things stand

**The website is built** and runs on the PC at http://localhost:3000 (Docker, `nextjs-web`).
Since 2026-09-24, on `main`:

- the chat panel (F-68), with its button now a gold **Chat** pill in the nav;
- the Statistics tab as collapsible cards, each explained (F-70);
- the home page on its night-sky picture, responsive on phone, tablet and desktop, with a gold
  **Build my line** button and a navy/gold banner;
- the whole site dark by default in the Observatory palette (navy and gold), balls as solid
  fills with dark numbers, and the footer motto on every page but home.

**Tests:** 295 pytest (294 pass - F-67), 374 vitest, 102 Playwright, all passing on
2026-09-25 apart from F-67.

**Open defects** (details in `issue.md`):

| ID | Severity | In short |
|:--|:--|:--|
| F-72 | Medium | the rebuild receiver says `already had it` for a known date even when the numbers differ |
| F-67 | Low | a parity test's assertion cannot hold for a bonus ball; the engine is right |
| F-69 | Low | the freshness bin test compares with a uniform 1/3, not a fair draw |
| F-71 | Low | the first e2e tests of a full run can time out on a cold server |
| F-73 | Low | `secrets.env.example` has no `REBUILD_SECRET` line |

**The data is one draw behind.** The newest row in `data/irish500.csv` is Monday 21 Sep 2026
(15, 24, 29, 30, 31, 38, bonus 11). Wednesday 23 Sep has been drawn and is not in it, which is
why the home page shows "One draw is not in yet". Nothing brings it in by itself on the PC -
see section 3.

---

## 2. Test the n8n POST before publishing

n8n will post each new draw to the **rebuild receiver** (`rebuild_webhook.py`). The receiver
appends it to `data/irish500.csv`, runs `drawpick.py`, and the site serves the new draw. You
can make the same request yourself.

### The endpoint

| Where | URL |
|:--|:--|
| On the PC, for this test | `POST http://127.0.0.1:8080/rebuild` |
| On the VPS, from n8n | `POST http://lotto-rebuild:8080/rebuild` (Docker network only, never public) |
| Health check | `GET /health` on the same host and port |

### The request

Headers:

```
Content-Type: application/json
X-Lotto-Signature: <hex HMAC-SHA256 of the exact body, keyed with REBUILD_SECRET>
```

Body - compact JSON, keys in this order, exactly these bytes are signed:

```json
{"date":"2026-09-21","main":[15,24,29,30,31,38],"bonus":11}
```

- `date` is ISO `YYYY-MM-DD`, not in the future, and not older than the newest row in the CSV.
- `main` is six distinct integers 1-47, in any order; `bonus` is one integer 1-47, not among them.
- The 21 Sep draw's fifth number is **31**.

`scripts/post_draw.py` builds this body, signs it and prints the answer, exactly as the two
n8n nodes will (`n8n.md` section 7 steps 4-5).

### Running it on the PC

The receiver is not part of the local stack; start it for the test. You need `REBUILD_SECRET`
in `secrets.env` - at least 16 characters; F-73 is that the example file does not say so.
Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` and add it by hand.

**Terminal 1** - the receiver, the same container the VPS runs, over your `data/`:

```powershell
docker compose build data-engine
docker run --rm --name lotto-rebuild-test -p 127.0.0.1:8080:8080 `
  --env-file secrets.env -e REBUILD_PORT=8080 `
  -v "${PWD}/data:/app/data" `
  --entrypoint python lotto-data-engine:latest rebuild_webhook.py
```

The `build` matters: the image on the PC was built on 21 Sep with the old receiver, which did
not take the draw. It prints `rebuild receiver listening on 0.0.0.0:8080/rebuild`.

**Terminal 2** - the post:

```powershell
$env:REBUILD_SECRET = "<the same value as in secrets.env>"
venv\Scripts\python.exe scripts\post_draw.py 2026-09-21 15 24 29 30 31 38 --bonus 11
```

Stop the receiver with Ctrl+C in terminal 1.

### What to expect for 21 Sep

21 Sep is already the newest row, so the receiver changes nothing and runs nothing:

```
200 {
  "draw": "2026-09-21",
  "appended": false,
  "csv_rows": 600,
  "state": "already had it",
  "seconds": 0.0,
  "artifacts": 25
}
```

This was checked on 2026-09-25 against a copy of `data/`, both with the receiver on the PC's
Python and in the `lotto-data-engine` container. It proves the endpoint, the signing and the
validation - not the append and the rebuild, because there is nothing to append.

The other answers you can provoke:

| Send | Answer |
|:--|:--|
| a wrong `REBUILD_SECRET` in terminal 2 | `401 {"error": "bad signature"}` |
| `--bonus 15` (a main number) | `400 {"state": "rejected", "error": "bonus must not be one of the main numbers"}` |
| `2026-09-19 ...` (older than the newest row) | `400 ... "date is older than the newest row (2026-09-21)"` |
| `2026-09-21 15 24 29 30 3 38 --bonus 11` | `200 "already had it"` - **wrong**, this is F-72 |
| a new draw, e.g. the real 23 Sep result | `200 {"appended": true, "state": "rebuilt", "seconds": ~60}` |
| the same new draw again | `200 "already had it"` - a retry costs nothing |
| nothing listening | the script prints `No receiver answered at ...` |

### Testing the whole chain

To see a draw actually arrive, post the **real 23 Sep result** from lottery.ie (not invented
numbers - the row goes into the history). The receiver then:

1. writes `23 Sep 2026,...` as row 2 of `data/irish500.csv`, zero-padded, LF;
2. runs `drawpick.py` inside the container - about a minute; the post waits for it;
3. answers `"appended": true, "state": "rebuilt"` with `csv_rows` one higher (601).

`data/irish500.csv` and `data/*.json` are tracked, so `git status` then shows them changed.
Commit them as the new draw, or `git checkout -- data/` to undo the test.

### Do I need to refresh the site?

**Reload the page - nothing else.** The Next.js site reads `data/*.json` from the mounted
folder on every request and caches each file by its modified time, so a rewritten artifact is
picked up on the next page load. No container restart and no image rebuild: the image holds
the site's code, not its data. `npm run test:integration` is the test that proves it.

After a successful new-draw post, reload http://localhost:3000: the home page shows the new
draw, and the "One draw is not in yet" banner goes once the newest scheduled draw is in.

### Does drawpick.py run automatically?

**Only when the receiver is running and receives a new draw.**

- **On the PC today: no.** Nothing runs the receiver, so nothing runs `drawpick.py`. A draw
  arrives when you run `scripts/scrape_lotto.py` and then `python drawpick.py`, or
  `scripts/docker_start.*`, which runs the engine, or when you post one as above.
- **On the VPS: yes.** `docker-compose.prod.yml` keeps `rebuild-receiver` running. After each
  draw n8n scrapes lottery.ie, commits the row to GitHub, and posts it here; the receiver runs
  `drawpick.py` (about a minute) and the site shows the draw on the next page load. A retried
  post for a draw already in the file does nothing, and posting when the artifacts are older
  than the CSV repairs them (`rebuilt stale artifacts`).
- **`quickpick.py` never runs automatically** - model training stays on the PC.

---

## 3. What is left, in order

```
  now
   |
   +-- F-72: the receiver must refuse a known date with other numbers   (code, before n8n posts)
   +-- F-73: REBUILD_SECRET in secrets.env.example                       (one line)
   +-- the 23 Sep draw into data/                                        (post it, or scrape + drawpick)
   +-- lottodraw.md: the two n8n nodes - sign, then POST                 (n8n.md section 7 steps 4-5)
   +-- web.md step 2: compare each statistic on both sites               (could send work back)
   +-- chat.md: a capped OpenRouter key in secrets.env                   (the panel runs without it)
   |
  n8n.md section 6: three clean draws, all five checks, no failure email
   |
  n8n.md section 7: Phase 2B nodes, then section 8's backtest against the CSV
   |
  web.md steps 4-5: deploy to the VPS (vps.md), point the domain, one week and three draws
   |
  web.md step 6: delete Streamlit and rewrite the six tests that import view/
   |
  web.md step 7: the manual
```

Details of each step are where they were: [`n8n.md`](n8n.md) sections 6-8,
[`lottodraw.md`](lottodraw.md), [`web.md`](web.md) section 8, [`chat.md`](chat.md)'s status,
and [`vps.md`](vps.md) for the deployment. Nothing below the monitoring week can start before
real draws have come through it.

**Also open, not blocking publication:** F-67 (a one-line test change waiting on a decision),
F-69 (the freshness verdict nobody reads yet), F-71 (warm the e2e server before the tests).
