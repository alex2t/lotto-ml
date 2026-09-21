# Phase 5: the VPS

How to put the stack on the server, and what will bite if you do it in the wrong order.

This is the build document for `plan.md` Phase 5, and it is written for someone sitting at a
fresh VPS with a domain pointed at it. Everything it describes is built and tested locally -
the proxy config, the production overlay, the rebuild receiver - except the one thing only
the server can do, which is actually run it. **The steps here have not been executed against
a live VPS.**

---

## 1. What is being deployed

```
                    the internet
                         |
                    443  |  80
                +--------v--------+
                |  reverse-proxy  |  caddy:2-alpine, automatic HTTPS
                +--------+--------+
                         | nextjs-web:3000 (internal only)
                +--------v--------+
                |   nextjs-web    |  the site, data/ mounted read-only
                +-----------------+

   n8n ---(signed POST, internal network)---> rebuild-receiver ---> drawpick.py
                                                      |
                                                 data/ read-write
```

Three containers serve the site; a fourth, `data-engine`, runs once and exits, rewriting
`data/*.json` before the site starts. `streamlit-web` stays in the base compose file for the
side-by-side period but nothing public points at it.

**What is NOT on the VPS:** `quickpick.py`, `ml_lotto/`, `lottery_picks.txt`, `model_metrics/`.
Models are trained on the owner's PC and the VPS never needs them. The Review page's admin
half says so plainly when the picks file is absent, which on the VPS it always is.

---

## 2. Before the first deploy

- A DNS A record for the site's hostname pointing at the VPS, **already propagated**. Caddy
  asks Let's Encrypt for a certificate on first start, and an unresolvable name means a
  failed challenge and a rate-limited retry.
- Docker and the compose plugin on the host. No Python, no Node: that is the point of the
  engine image.
- Ports 80 and 443 open. 80 is not optional - the HTTP-01 challenge and the HTTPS redirect
  both use it.
- The repository on the host, at `/var/www/lotto-system` or wherever suits.

---

## 3. The deploy, in order

### 3.1 The trap that is worth reading first

`./data` is bind-mounted **over** the image's own directory, so the container's user must be
able to write the host's `data/`. The containers run as UID:GID 1000:1000 by default. Docker
Desktop on Windows and macOS hides this; a Linux VPS does not, and the failure mode is the
engine exiting non-zero on its first write (F-45).

Either make the host directory match:

```bash
sudo chown -R 1000:1000 data
```

or make the containers match the host user, in `.env`:

```bash
id -u   # e.g. 1001
id -g
```

```dotenv
UID=1001
GID=1001
```

Both work. Doing neither means the stack never starts.

### 3.2 The two env files

They are separate on purpose. Compose reads `.env` for its own variable substitution, and a
bcrypt hash is full of `$` signs that it would try to expand there - that was F-58, and the
same expansion bit a second time one layer up.

`.env` - what compose substitutes into the compose files:

```dotenv
DOMAIN=lotto.example.com
UID=1000
GID=1000
```

`secrets.env` - what is handed to the containers verbatim, never interpolated:

```dotenv
ADMIN_USERNAME=owner
ADMIN_PASSWORD_HASH=$2b$12$...
SESSION_SECRET=<64 hex characters>
REBUILD_SECRET=<32+ characters>
```

Generate them on the PC, not the server:

```bash
node -e "console.log(require('./frontend/node_modules/bcryptjs').hashSync(process.argv[1],12))" "the-password"
node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"   # twice
```

Both files are gitignored and dockerignored. `.env.example` and `secrets.env.example` are
the committed templates.

### 3.3 Build and start

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The engine runs first and must exit 0; `nextjs-web` waits on
`service_completed_successfully`, so a failed rebuild means no site rather than a site
serving half-written artifacts (F-43).

Watch the first start, because this is where the certificate is issued:

```bash
docker compose logs -f reverse-proxy
```

### 3.4 Check it

```bash
curl -sS https://$DOMAIN/api/health                # {"status":"ok","latestDraw":"..."}
curl -sSI https://$DOMAIN | grep -i strict-transport
curl -sS -o /dev/null -w '%{http_code}\n' https://$DOMAIN/api/download/data   # 401
curl -sS -o /dev/null -w '%{http_code}\n' http://<vps-ip>:3000/              # must fail
```

The last one matters: the site must not be reachable around the proxy, where there is no TLS
and none of the security headers. `tests/test_docker_stack.py` asserts the overlay clears
the published port, but only the server proves it.

Then walk the five destinations in a browser - Home, Pick, Explore, Numbers, Review - and
log in once to download the bundle.

---

## 4. The rebuild receiver

n8n commits a draw to `data/irish500.csv`, then asks the VPS to rewrite the artifacts. That
is `rebuild-receiver`, the only network-facing thing in this repo that writes files, which is
why it is built the way it is:

- **It never gets the Docker socket.** A receiver that shells out to `docker run` needs the
  socket, which is root on the host. It runs `drawpick.py` in its own process instead.
- **It is not proxied.** Caddy forwards to `nextjs-web` and nothing else, and the service
  publishes no port. n8n reaches it over a shared Docker network at
  `http://lotto-rebuild:8080/rebuild`.
- **Requests are signed**, not just secret-bearing: HMAC-SHA256 over the exact body, compared
  in constant time. A bare token is fine until it turns up in a proxy log.
- **One rebuild at a time.** A second request while one is running gets 409, not a queue
  slot: a rebuild rewrites the files the site is reading.

If n8n and the lotto stack are not on the same Docker network, attach them:

```bash
docker network connect lotto-ml-system_default <n8n-container>
```

The n8n side, in a Code node before the HTTP Request node:

```javascript
const crypto = require('crypto');
const body = JSON.stringify({ draw: $json.date });
const signature = crypto
  .createHmac('sha256', $env.REBUILD_SECRET)
  .update(body)
  .digest('hex');
return [{ json: { body, signature } }];
```

and the HTTP Request node posts `{{$json.body}}` with header
`X-Lotto-Signature: {{$json.signature}}`. A non-200 is a failure the workflow must email
about, exactly like the parse failures in [`n8n.md`](n8n.md) section 5.

Check it by hand from the host:

```bash
BODY='{"draw":"manual"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$REBUILD_SECRET" | awk '{print $2}')
docker compose exec rebuild-receiver \
  python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8080/health').read())"
```

---

## 5. Keeping it running

**Backups.** `data/irish500.csv` is the only irreplaceable file - every artifact can be
rebuilt from it in a minute. It is in git, so the repository is the backup; a VPS-side copy
is belt and braces.

**The Caddy volume.** `caddy_data` holds the certificates. Pruning it means re-issuing on the
next start, and Let's Encrypt rate-limits that. `docker compose down` keeps it;
`docker compose down -v` does not.

**Updating the site:**

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build nextjs-web
```

The engine only needs rebuilding when `lotto_analysis/`, `drawpick.py` or
`requirements-engine.txt` changed.

**Rolling back** is `git checkout <previous>` and the same command. The artifacts are
regenerated from the CSV, so a rollback of code does not strand the data.

**Logs:** `docker compose logs -f nextjs-web reverse-proxy rebuild-receiver`. The receiver
prints one line per request; the proxy prints one per request with its status.

---

## 6. Phase 5 checklist

Built and provable locally; the unticked rows need the server itself.

- [x] The production overlay: Caddy is the only thing publishing a port, `nextjs-web` stops
      publishing 3000, everything restarts unless stopped, and both the site and the receiver
      are health-checked.
- [x] Caddy configured for automatic HTTPS, with HSTS, `nosniff`, `DENY` framing, a referrer
      policy and a content security policy. Validated against `caddy:2-alpine` with both a
      real hostname and `:80`.
- [x] `/api/health` reads an artifact, so a container that is listening but cannot see
      `data/` is reported unhealthy rather than serving errors.
- [x] The rebuild receiver: signed requests, one rebuild at a time, no Docker socket, not
      proxied, refuses to start without a secret. 16 tests in
      `tests/test_rebuild_webhook.py`.
- [x] The deployment runbook - this file - including the UID/GID trap and the two env files.
- [x] The whole overlay run locally, 2026-09-21: the proxy serves the site on port 80 with
      `X-Frame-Options: DENY`, `nosniff`, the referrer policy and the CSP, `/api/health` answers
      `{"status":"ok","latestDraw":"2026-09-19"}`, port 3000 refuses a connection, and the receiver
      took a signed request, ran `drawpick.py` in the container, rewrote the artifacts and answered
      `200 ok` while an unsigned one got `401 bad signature`. The site then served the rebuilt
      artifacts with no restart. The container's rebuild differed from the host's only in
      `generated_date` and `analysis_date`, which is F-46 holding across platforms again.
- [ ] **Deploy the stack on the VPS.** Needs the server.
- [ ] **Verify public access to every destination without login, from an external browser.**
- [ ] **Test the admin login and the data bundle download over HTTPS.**
- [ ] **The end-to-end integration test**: n8n ingests a draw -> commits the row -> posts to
      the receiver -> the VPS rebuilds -> the site shows the new draw -> download the bundle
      to the PC -> `quickpick.py` locally. Sections 3 and 4 above are the two halves of it;
      the local half is already proved by
      `npm --prefix frontend run test:integration`, which appends a row, runs `drawpick.py`
      and asserts the site serves the new draw without a restart.

---

## 7. Where the facts came from

| Fact | Source |
|:--|:--|
| the bind mount needs a matching uid | F-45 in `issue.md`, `scripts/CLAUDE.md` |
| compose expands `$` in an interpolated value | F-58 in `issue.md` |
| a failed phase must stop the run | F-43 in `issue.md`, `lotto_analysis/analyzers/CLAUDE.md` |
| the site must not read `irish500.csv` | F-35, `frontend/CLAUDE.md` |
| `quickpick.py` never runs on the VPS | `plan.md` 3.5, root `CLAUDE.md` |
| the ingestion workflow and its failure email | [`n8n.md`](n8n.md) |
| the cutover that removes Streamlit | [`web.md`](web.md) section 8 |
