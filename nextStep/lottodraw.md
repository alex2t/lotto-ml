# Getting a new draw onto the VPS

How the row n8n scraped becomes the artifacts the site serves, without `drawpick.py` running
more often than there are draws.

This is the build document for the last gap in the chain. Phase 2A scrapes and emails;
[`n8n.md`](n8n.md) section 7 commits the row to GitHub; [`vps.md`](vps.md) stands the stack
up. What has never been designed is the step between the commit and the rebuild - and the
receiver as it exists today has a hole in exactly that place.

---

## 1. The problem, stated plainly

`rebuild_webhook.py` runs `drawpick.py` when a signed request arrives. It rebuilds from
**whatever CSV is already on the VPS disk**, and nothing puts the new row there. So a webhook
that only says "a draw happened" regenerates the same 24 artifacts from the same unchanged
input: a minute of work for no change.

The fix is to send the draw in the webhook body. n8n is posting anyway.

```
  n8n  --- signed POST, the draw in the body --->  rebuild-receiver
   |                                                     |
   |                                            append to irish500.csv
   +--- commit to GitHub (n8n.md 7) ---+                 |
            history and backup                      drawpick.py
                                                          |
                                                    data/*.json
                                                          |
                                              the site, no restart
```

GitHub still gets the commit. It stops being something the VPS has to reach at rebuild time.

---

## 2. The rule that matters most

**A retry must cost nothing.** `drawpick.py` is about 35 seconds on the owner's PC and about
a minute in the container, under 250 MB. Three of those a week is nothing. Thirty is a
different conversation, and nothing about n8n guarantees it posts exactly once - a timeout on
our side, a retried execution, a workflow re-run by hand, all send the same draw again.

So the receiver does not rebuild because it was asked. **It rebuilds because the data
changed.**

| What arrives | What happens | Cost |
|:--|:--|:--|
| A draw whose date is not in the CSV | append, then rebuild | one run |
| The same draw again | recognised by date, nothing appended, nothing rebuilt | none |
| The same draw again, but the artifacts are older than the CSV | no append, **rebuild** | one run, and it is the run that was missing |
| A draw that fails validation | rejected, nothing written | none |
| Anything unsigned | rejected before it is read | none |

The third row is the one that is easy to leave out. If the append succeeds and `drawpick.py`
then fails - a bad phase, a full disk, the container restarting mid-run - the row is in the
CSV and the artifacts are stale. A receiver that only checks "do I already have this date?"
would answer "yes, nothing to do" for ever, and the site would sit on old numbers with
everything reporting success. Comparing the artifacts' age against the CSV's is what makes a
plain retry the repair.

---

## 3. What n8n sends

One POST, to the receiver, after the GitHub commit node succeeds.

```
POST http://lotto-rebuild:8080/rebuild
X-Lotto-Signature: <hex HMAC-SHA256 of the exact body, key REBUILD_SECRET>
Content-Type: application/json

{"date": "2026-09-19", "main": [10, 11, 20, 28, 41, 44], "bonus": 2}
```

- **`date` is ISO**, `YYYY-MM-DD`. The CSV stores `19 Sep 2026`; converting is the receiver's
  job, not n8n's, so there is one place that knows the file's format.
- **`main` is six integers**, any order. The receiver sorts them.
- **`bonus` is one integer**, and is not one of the six.

The Code node that signs it, before the HTTP Request node:

```javascript
const crypto = require('crypto');
// The field names are the ones result() in n8n.md section 3.4 writes (F-76).
const draw = $('Parse and validate').first().json;
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

The HTTP Request node must send **`{{$json.body}}` verbatim** as the raw body. The signature
covers the exact bytes; letting n8n re-serialise the object will produce different bytes and
a 401 that looks like a wrong secret.

---

## 4. What the receiver does with it

In order, refusing at the first thing that is wrong.

1. **Check the signature** over the raw body, constant time. Already built. A bad one gets
   401 and nothing is read further.
2. **Validate the draw.** The signature proves where it came from, not that it is right, and
   this is the code that writes the file everything downstream reads:
   - `date` parses as a real date, is not in the future, and is not older than the newest row
     already in the CSV;
   - `main` is exactly 6 integers, all 1-47, all distinct;
   - `bonus` is an integer 1-47 and not among the six.

   These are the rules `scripts/scrape_lotto.py` and the n8n Code node already apply. They
   are applied again here because a validation that lives only upstream is a validation the
   file does not have.
3. **Look for the date in the CSV.** Present means this draw is already in: skip to step 6
   without writing anything.
4. **Append it**, formatted as the file wants it - `19 Sep 2026,10,11,20,28,41,44,02`, the
   numbers zero-padded to two digits, **inserted immediately after the header** because the
   file is newest-first, and written **LF** (F-44: the artifacts and the CSV are stored LF so
   a Windows run and a container run do not produce a whole-file diff).
5. **Write atomically** - a temp file in the same directory, then a rename. A crash halfway
   through a direct write leaves a truncated CSV, and `drawpick.py` would read it without
   complaint.
6. **Rebuild, if it is needed.** Needed means either the CSV changed in step 4, or the oldest
   expected artifact is older than the CSV. Otherwise return without running anything.
7. **Report what happened**, in the body of the response, so n8n's failure email has
   something to say and a human has something to read:

```json
{
  "state": "rebuilt",
  "draw": "2026-09-19",
  "appended": true,
  "csv_rows": 600,
  "seconds": 58.4,
  "artifacts": 25
}
```

`state` is one of `rebuilt`, `already had it`, `rebuilt stale artifacts`, `rejected`,
`conflict` or `failed`. n8n treats anything but the first three as a failure to email about.
`conflict` (409, F-72) is a date the file already holds with other numbers: the row stays,
nothing is rebuilt, and the body carries both - `in_csv` and `posted` - so the email can say
which number disagrees.

---

## 5. Drift, and why it is acceptable

The VPS CSV is written by the receiver; the GitHub CSV is written by n8n. If one leg succeeds
and the other does not, they differ.

**We accept that and detect it.** `csv_rows` in the response is the row count after the
append, and n8n knows what it expects that to be - it has just committed the same row to
GitHub. A mismatch goes in the same email as any other failure.

The alternative - having the receiver fetch the CSV from GitHub so there is one source of
truth - costs a network call on every rebuild, a token if the repository is private, and a
new failure mode where GitHub being slow stops the site updating. The CSV is reconstructible
from either side in a `git checkout`, so the cheaper arrangement is the right one here.

**Repair, if they do drift:** copy the file from the repository onto the VPS and post any
draw to the receiver. The date will already be present, the artifacts will be older than the
CSV, and step 6's second condition rebuilds from the corrected file.

---

## 6. What is already built

| Piece | State |
|:--|:--|
| HMAC-signed requests, constant-time comparison | built, `rebuild_webhook.py` |
| One rebuild at a time, second request gets 409 | built |
| Oversized body refused before it is read | built |
| Refuses to start without a secret | built |
| Runs `drawpick.py` and reports its exit code and log tail | built |
| `/health` for the container healthcheck | built |
| Not published, not proxied, no Docker socket | built, `docker-compose.prod.yml` |
| The draw in the body, validated at the receiver | built, `parse_draw()` |
| ISO date to `19 Sep 2026` in one place | built, `format_row()` |
| Dedupe by date; append after the header, zero-padded, LF | built, `handle_draw()`, `append_draw()` |
| Atomic write - temp file then rename | built, `append_draw()` |
| Rebuild only when the CSV changed or the artifacts are stale | built, `artifact_state()` |
| The response of section 4, with `csv_rows` | built |
| The engine's log decoded as UTF-8, not the locale codec (F-65) | built, `run_drawpick()` |
| 32 tests | built, `tests/test_rebuild_webhook.py` |

**Sections 3 and 4 are built.** What is left is not code: the two n8n nodes of section 3,
which are built in n8n itself, against the design in [`n8n.md`](n8n.md) section 7.

---

## 7. Checklist

- [x] The payload of section 3: `date`, `main`, `bonus`, validated at the receiver against the
      same rules `scrape_lotto.py` applies. `parse_draw()`, which raises `Rejected` and never
      reaches the file.
- [x] Date conversion in one place - ISO on the wire, `19 Sep 2026` in the file. `CSV_DATE_FORMAT`
      is read by `format_row()` and by `row_date()`, so the writer and the reader cannot disagree.
- [x] Dedupe by date: a draw already in the CSV appends nothing. A date older than the newest row
      is rejected, so the only date that can already be present is the newest one.
- [x] The row inserted after the header, zero-padded, LF (F-44).
- [x] Atomic write - temp file, then rename, with an `fsync` before it.
- [x] Rebuild only when the CSV changed, **or** the artifacts are older than the CSV.
      `artifact_state()` reads `drawpick.EXPECTED_ARTIFACTS` rather than a second copy of the list.
- [x] The response of section 4, including `csv_rows` for the drift check.
- [x] Tests: a new draw rebuilds; the same draw twice rebuilds once; a stale-artifact retry
      rebuilds without appending; a malformed draw is rejected and writes nothing; a
      half-written CSV is impossible; the row lands after the header with LF endings.
      31 tests, ~22s. The existing tests posted an empty body and now post a real draw - the
      receiver's contract changed by design, not to make anything pass.
- [x] `n8n.md` gains the Code node and the HTTP Request node, after the section 7 commit node,
      with the non-200 branch routed into the existing failure email. Section 7, steps 4 and 5.
- [x] `vps.md` section 4 updated - it described a body-less webhook.
- [x] Run it locally end to end: posted a synthetic draw at the real repo, the CSV grew by one
      row, `drawpick.py` rewrote the 25 artifacts in 39.5s, and the same request again
      answered `already had it` in 0.0s without running anything. That run is what found
      F-65: the engine's emoji killed the log reader thread, so a rebuild that had worked
      came back as a crash.
      The site serving it without a restart is `npm --prefix frontend run test:integration`,
      which appends a row, runs `drawpick.py` and asserts the new draw is served.

---

## 8. Where the facts came from

| Fact | Source |
|:--|:--|
| the receiver's current behaviour | `rebuild_webhook.py`, `tests/test_rebuild_webhook.py` |
| it is not proxied and gets no Docker socket | `docker-compose.prod.yml`, [`vps.md`](vps.md) 4 |
| the CSV is newest-first, the row goes after the header | [`n8n.md`](n8n.md) 4, 7 |
| the CSV and artifacts are stored LF | F-44 in `issue.md`, `.gitattributes` |
| de-duplication is by date, and a row is never corrected in place | [`n8n.md`](n8n.md) 4 |
| the validation rules for a draw | `scripts/scrape_lotto.py`, [`n8n.md`](n8n.md) 3 |
| a failed phase must exit non-zero | F-43 in `issue.md` |
| `drawpick.py` takes about 35s on the PC, about a minute in the container | measured 2026-09-21, the integration test and the container run |
| `quickpick.py` never runs on the VPS | `plan.md` 3.5, root `CLAUDE.md` |
