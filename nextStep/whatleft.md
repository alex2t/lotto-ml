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

**Tests:** 302 pytest (301 pass - F-67), 374 vitest, 102 Playwright, all passing on
2026-09-25 apart from F-67.

**Open defects** (details in `issue.md`):

| ID | Severity | In short |
|:--|:--|:--|
| F-67 | Low | a parity test's assertion cannot hold for a bonus ball; the engine is right |
| F-69 | Low | the freshness bin test compares with a uniform 1/3, not a fair draw |
| F-71 | Low | the first e2e tests of a full run can time out on a cold server |

F-72 (the receiver matched a draw by date alone) and F-73 (no `REBUILD_SECRET` in the example
secrets file) were fixed on 2026-09-25 and are in `issue.md`'s Appendix A.

**The data is one draw behind.** The newest row in `data/irish500.csv` is Monday 21 Sep 2026
(15, 24, 29, 30, 31, 38, bonus 11). Wednesday 23 Sep (02, 12, 17, 26, 30, 37, bonus 10) has
been drawn and is not in it, which is why the home page shows "One draw is not in yet".
Nothing brings it in by itself on the PC - the Postman test in section 2 is what does.

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

### The request - the 23 Sep 2026 draw

Wednesday 23 Sep 2026: **02, 12, 17, 26, 30, 37, bonus 10**. It is not in `data/` yet (the
newest row is 21 Sep), so this post exercises the whole chain: append, rebuild, serve.

Headers:

```
Content-Type: application/json
X-Lotto-Signature: <hex HMAC-SHA256 of the exact body, keyed with REBUILD_SECRET>
```

Body:

```json
{"date":"2026-09-23","main":[2,12,17,26,30,37],"bonus":10}
```

- `date` is ISO `YYYY-MM-DD`, not in the future, and not older than the newest row in the CSV.
- `main` is six distinct integers 1-47, in any order; `bonus` is one integer 1-47, not among
  them. Write `2`, not `02` - a leading zero is not valid JSON. The CSV row is zero-padded by
  the receiver.
- The signature covers the exact bytes sent. Postman computes it for you with the script below.

### 1. Start the receiver on the PC

The receiver is not part of the local stack; start it for the test. You need `REBUILD_SECRET`
in `secrets.env` - at least 16 characters; `secrets.env.example` shows the line.
Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` and add it by hand.

In PowerShell, from the project folder - the same container the VPS runs, over your `data/`:

```powershell
docker compose build data-engine
docker run --rm --name lotto-rebuild-test -p 127.0.0.1:8080:8080 `
  --env-file secrets.env -e REBUILD_PORT=8080 `
  -v "${PWD}/data:/app/data" `
  --entrypoint python lotto-data-engine:latest rebuild_webhook.py
```

The `build` keeps the image current: the one built on 21 Sep carried the old receiver, which did
not take the draw. It was rebuilt on 2026-09-25, so the build is quick unless the code changed. It prints `rebuild receiver listening on 0.0.0.0:8080/rebuild`. Leave it running;
Ctrl+C stops it when you are done.

### 2. Set up Postman

Use the Postman desktop app - the web version cannot reach `127.0.0.1` without its agent.

1. **Environment** - create one with a variable `REBUILD_SECRET`, type *secret*, value the same
   as in `secrets.env`. Select it.
2. **Request** - `POST http://127.0.0.1:8080/rebuild`.
3. **Body** - *raw*, *JSON*, and paste the body above.
4. **Scripts > Pre-request** - paste:

   ```javascript
   const body = pm.request.body.raw;
   const secret = pm.environment.get("REBUILD_SECRET");
   const signature = CryptoJS.HmacSHA256(body, secret).toString(CryptoJS.enc.Hex);
   pm.request.headers.upsert({ key: "X-Lotto-Signature", value: signature });
   ```

   It signs whatever is in the body at the moment you press Send, the way n8n's Code node will
   (`n8n.md` section 7 step 4), so editing the body never leaves a stale signature.
5. Optional: `GET http://127.0.0.1:8080/health` first - `{"state": "listening", ...}`.

**Send.** The request waits while `drawpick.py` runs, about a minute; Postman's default
timeout (none) is fine.

(`scripts/post_draw.py 2026-09-23 2 12 17 26 30 37 --bonus 10` sends the same request from a
terminal, if you ever want it without Postman.)

### 3. What to expect

**Status `200`**, with this body - `seconds` will differ:

```json
{
  "draw": "2026-09-23",
  "appended": true,
  "csv_rows": 601,
  "seconds": 60.0,
  "artifacts": 25,
  "state": "rebuilt"
}
```

- `appended: true` - the draw was new and is now row 2 of `data/irish500.csv`:
  `23 Sep 2026,02,12,17,26,30,37,10`
- `csv_rows: 601` - one more than the 600 before.
- `state: rebuilt` - `drawpick.py` ran and exited 0; `artifacts: 25` means every artifact it is
  expected to write is there.

This is what `rebuild_webhook.py` answers for a new draw (`handle_draw()`, lines 196-231) and
what `tests/test_rebuild_webhook.py` asserts on a stubbed engine. It has not been run against
your real `data/` - the first real append is this test.

A `500` with `"state": "failed"` means `drawpick.py` failed; the body carries the tail of its
log. The row stays in the CSV, so sending again once it is fixed repairs the artifacts
(`rebuilt stale artifacts`).

### 4. Then try these

| Send | Answer |
|:--|:--|
| the same 23 Sep request again | `200 "already had it"`, `appended: false`, `seconds: 0` - a retried n8n run costs nothing |
| 21 Sep (`15,24,29,30,31,38`, bonus 11) | `400 "date is older than the newest row (2026-09-23)"` |
| 23 Sep with another number, e.g. `[2,12,17,26,30,36]` | `409 {"state": "conflict", "in_csv": ..., "posted": ...}` - the row stays, nothing is rebuilt (F-72) |
| `"bonus": 12` (one of the main numbers) | `400 "bonus must not be one of the main numbers"` |
| `"main": [2,12,17,26,30]` | `400 "main must be 6 numbers"` |
| a date after today | `400 "date is in the future"` |
| a different `REBUILD_SECRET` in the environment | `401 {"error": "bad signature"}` |
| no `X-Lotto-Signature` header (script disabled) | `401 {"error": "bad signature"}` |

### 5. Afterwards

`data/irish500.csv` and `data/*.json` are tracked, so `git status` shows them changed. The 23
Sep draw is real, so **commit them** as the new draw - or `git checkout -- data/` to undo the
test and send it again later.

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
   +-- the 23 Sep draw into data/                                        (your Postman test, section 2)
   +-- lottodraw.md: the two n8n nodes - sign, then POST                 (n8n.md section 7 steps 4-5)
   +-- web.md step 2: compare each statistic on both sites               (could send work back)
   +-- chat.md: a capped OpenRouter key in secrets.env                   (the panel runs without it)
   |
  n8n.md section 6: three clean draws, all five checks, no failure email
   |
  n8n.md section 7: Phase 2B nodes, then section 8's backtest against the CSV
   |
  web.md steps 4-5: deploy to the Hostinger VPS behind its Traefik (vps.md 2.1), point the domain, one week and three draws
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
