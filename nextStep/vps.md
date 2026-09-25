# Phase 5: the VPS

How to put the stack on the server, and what will bite if you do it in the wrong order.

This is the build document for `plan.md` Phase 5, and it is written for someone sitting at a
VPS with a domain pointed at it. **The owner's VPS is at Hostinger and already runs n8n
behind Traefik** - section 2.1 is the part that differs for it. Everything it describes is built and tested locally -
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
  (or, on Hostinger, Traefik - section 2.1) asks Let's Encrypt for a certificate on first
  start, and an unresolvable name means a failed challenge and a rate-limited retry.
- Docker and the compose plugin on the host. No Python, no Node: that is the point of the
  engine image.
- Ports 80 and 443 open. 80 is not optional - the HTTP-01 challenge and the HTTPS redirect
  both use it.
- The repository on the host. **The code travels through GitHub, not a registry**: the images
  are built on the VPS from the clone (section 3.3), so nothing is pushed to Docker Hub or
  GHCR. The repository is private, so the clone needs a credential - a fine-grained GitHub
  token with read access to `alex2t/lotto-ml` only:

  ```bash
  cd /opt
  git clone https://github.com/alex2t/lotto-ml.git lotto-ml   # user: alex2t, password: the token
  cd lotto-ml
  ```

  `data/irish500.csv` and the artifacts come with it; `secrets.env` and `.env` do not
  (gitignored) and are created by hand in section 3.2.

### 2.1 On Hostinger: the VPS already runs n8n

**Hostinger is the machine; Caddy is a program on it.** They are not alternatives - Caddy
runs as the `reverse-proxy` container on whatever VPS the stack is on. What matters on this
VPS is that n8n is already there, and Hostinger's one-click n8n template puts it behind
**Traefik, which already holds ports 80 and 443**. Caddy cannot bind them as well, so the
stack goes behind that Traefik instead: `docker-compose.hostinger.yml` is a third overlay
that takes Caddy off 80/443, has it serve plain HTTP on the Docker network (keeping the
security headers and the health check), and gives Traefik the labels to route the site's
hostname to it and fetch the certificate. The receiver joins Traefik's network so n8n can
reach it, and is told Traefik must not route it.

Built and checked with `docker compose config` and `tests/test_docker_stack.py` on
2026-09-26; **not yet run against a live Traefik.**

**First, confirm what holds the ports** (on the VPS):

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}'
```

A `traefik` container with `0.0.0.0:80->80` and `0.0.0.0:443->443` is the case this section
covers. If nothing holds 80/443, skip this section: the plain two-file deploy with Caddy is
right.

**Then read the three names Traefik uses** from the n8n container (`n8n` below - use the
name `docker ps` showed):

```bash
# the network n8n shares with Traefik -> TRAEFIK_NETWORK
docker inspect n8n --format '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}} {{end}}'

# the router labels -> the entrypoint and the certresolver
docker inspect n8n --format '{{range $k, $v := .Config.Labels}}{{$k}}={{$v}}{{"\n"}}{{end}}' | grep traefik
```

Look for `...entrypoints=websecure` and `...tls.certresolver=mytlschallenge` - those are the
names in n8n's own Docker Compose example, which the overlay defaults to. If yours differ,
put yours in `.env` (section 3.2).

**DNS at Hostinger:** hPanel > Domains > DNS / Nameservers: an `A` record for the site's
hostname (for example `lotto.yourdomain.com`) pointing at the VPS's IP - the same way the n8n
hostname already points there. **Firewall:** if the VPS firewall is on in hPanel, 80 and 443
are already open for n8n; nothing new needs opening, because the site uses the same ports
through Traefik and the receiver publishes none.

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
# On Hostinger behind Traefik (section 2.1) - the names read from the n8n container:
TRAEFIK_NETWORK=root_default
TRAEFIK_ENTRYPOINT=websecure
TRAEFIK_CERTRESOLVER=mytlschallenge
```

`secrets.env` - what is handed to the containers verbatim, never interpolated:

```dotenv
ADMIN_USERNAME=owner
ADMIN_PASSWORD_HASH=$2b$12$...
SESSION_SECRET=<64 hex characters>
REBUILD_SECRET=<32+ characters>
```

What each one is for:

| Variable | Read by | Used for |
|:--|:--|:--|
| `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH` | `nextjs-web` | the one admin login at `/login`; only the bcrypt hash is stored, never the password |
| `SESSION_SECRET` | `nextjs-web`, `frontend/lib/auth/session.ts` | signs the admin cookie (`lotto_admin`, 2 hours) handed out after a login. Every admin request - the data download at `/api/download/data`, the admin half of Review - checks that signature. Anyone holding it could forge the cookie, so it is long, random and different on the PC and the VPS. The public pages never use it; changing it only logs the admin out |
| `REBUILD_SECRET` | `rebuild-receiver`, and n8n | the key n8n signs each posted draw with; the receiver refuses to start without it. The **same** value goes into n8n's environment |
| `OPENROUTER_API_KEY` | `nextjs-web` | the chat panel's model layer; optional |

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

**On Hostinger behind Traefik**, the same with the third file. Put the list in `.env` once so
every later command is short:

```dotenv
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml:docker-compose.hostinger.yml
```

```bash
docker compose build
docker compose up -d
```

The engine runs first and must exit 0; `nextjs-web` waits on
`service_completed_successfully`, so a failed rebuild means no site rather than a site
serving half-written artifacts (F-43).

Watch the first start, because this is where the certificate is issued - by Caddy, or on
Hostinger by Traefik:

```bash
docker compose logs -f reverse-proxy          # Caddy
docker logs -f <traefik-container> 2>&1 | grep -i -E "acme|lotto|error"   # Hostinger
```

### 3.4 Check it

```bash
curl -sS https://$DOMAIN/api/health                # {"status":"ok","latestDraw":"..."}
curl -sSI https://$DOMAIN | grep -i strict-transport
curl -sS -o /dev/null -w '%{http_code}\n' https://$DOMAIN/api/download/data   # 401
curl -sS -o /dev/null -w '%{http_code}\n' http://<vps-ip>:3000/              # must fail
curl -sS -o /dev/null -w '%{http_code}\n' http://<vps-ip>:8501/              # must fail
```

Run the last two from the PC, not the VPS. They matter: neither site may be reachable around
the proxy, where there is no TLS and none of the security headers. The overlay clears 3000
and keeps Streamlit's 8501 on the server's loopback (F-75); `tests/test_docker_stack.py`
asserts both, but only the server proves it. For the side-by-side week, open Streamlit
through a tunnel: `ssh -L 8501:127.0.0.1:8501 root@<vps-ip>`, then http://localhost:8501.

Then walk the five destinations in a browser - Home, Pick, Explore, Numbers, Review - and
log in once to download the bundle.

---

## 4. The rebuild receiver

n8n commits a draw to GitHub, then **posts that draw to the VPS**, which appends it to its own
`data/irish500.csv` and rewrites the artifacts. That is `rebuild-receiver`, the only
network-facing thing in this repo that writes files, which is why it is built the way it is:

- **It never gets the Docker socket.** A receiver that shells out to `docker run` needs the
  socket, which is root on the host. It runs `drawpick.py` in its own process instead.
- **It is not proxied.** Caddy forwards to `nextjs-web` and nothing else, and the service
  publishes no port. n8n reaches it over a shared Docker network at
  `http://lotto-rebuild:8080/rebuild`.
- **Requests are signed**, not just secret-bearing: HMAC-SHA256 over the exact body, compared
  in constant time. A bare token is fine until it turns up in a proxy log.
- **One rebuild at a time.** A second request while one is running gets 409, not a queue
  slot: a rebuild rewrites the files the site is reading.
- **It rebuilds because the data changed, not because it was asked.** A draw already in the
  CSV appends nothing and runs nothing, so a retried execution is free. The exception is the
  repair case: if the artifacts are older than the CSV - an append that succeeded before a
  failed run - the same request rebuilds. See [`lottodraw.md`](lottodraw.md).

On Hostinger with `docker-compose.hostinger.yml` they already share Traefik's network - the
overlay puts the receiver on it. Otherwise, if n8n and the lotto stack are not on the same
Docker network, attach them:

```bash
docker network connect lotto-ml_default <n8n-container>   # the project is named after the folder
```

**The draw travels in the body.** The receiver is what converts the ISO date to the
`19 Sep 2026` the file holds, and what validates the numbers again before writing them:

```
{"date": "2026-09-19", "main": [10, 11, 20, 28, 41, 44], "bonus": 2}
```

The n8n nodes that build and sign it are in [`n8n.md`](n8n.md) section 7. The reply says what
happened - `rebuilt`, `already had it`, `rebuilt stale artifacts`, `rejected`, `conflict` or `failed` -
with `csv_rows` for the drift check against GitHub. The first three are success; anything
else is a failure the workflow must email about, exactly like the parse failures in
[`n8n.md`](n8n.md) section 5.

Check it by hand from the host. Posting the same draw twice must rebuild once:

```bash
BODY='{"date":"2026-09-19","main":[10,11,20,28,41,44],"bonus":2}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$REBUILD_SECRET" | awk '{print $2}')
docker compose exec -T -e BODY="$BODY" -e SIG="$SIG" rebuild-receiver python -c "import os,urllib.request as u; r=u.Request('http://127.0.0.1:8080/rebuild', data=os.environ['BODY'].encode(), headers={'X-Lotto-Signature': os.environ['SIG'], 'Content-Type': 'application/json'}); print(u.urlopen(r).read().decode())"
```

`/health` needs no signature and runs nothing:

```bash
docker compose exec -T rebuild-receiver python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8080/health').read())"
```

---

## 5. Keeping it running

**Backups.** `data/irish500.csv` is the only irreplaceable file - every artifact can be
rebuilt from it in a minute. It is in git, so the repository is the backup; a VPS-side copy
is belt and braces.

**The Caddy volume.** `caddy_data` holds the certificates. Pruning it means re-issuing on the
next start, and Let's Encrypt rate-limits that. `docker compose down` keeps it;
`docker compose down -v` does not.

**Updating the site - discard the server's `data/` first** (F-74). The receiver appends each
draw to `data/irish500.csv` and the engine rewrites `data/*.json`, and both are tracked in
git, so after the first draw the clone has local changes and a bare `git pull` stops with
"Your local changes ... would be overwritten". Discarding them loses nothing: n8n commits
each draw to GitHub **before** it posts it here, so GitHub holds every row the server has,
and the engine regenerates the artifacts from the pulled CSV on the next start.

```bash
git checkout -- data/
git pull
docker compose up -d --build        # with COMPOSE_FILE in .env; the engine reruns first
```

Never commit from the VPS: its `data/` is a working copy of what GitHub already has.

**Rolling back** is `git checkout -- data/`, `git checkout <previous>` and the same
`up`. The artifacts are regenerated from the CSV, so a rollback of code does not strand the
data.

**Logs:** `docker compose logs -f nextjs-web reverse-proxy rebuild-receiver`. The receiver
prints one line per request; the proxy prints one per request with its status.

---

## 6. Phase 5 checklist

Built and provable locally; the unticked rows need the server itself.

- [x] The production overlay: Caddy is the only thing publishing a port to the internet,
      `nextjs-web` stops publishing 3000, Streamlit's 8501 stays on loopback (F-75), everything
      restarts unless stopped, and both the site and the receiver are health-checked.
- [x] The Hostinger overlay (`docker-compose.hostinger.yml`, section 2.1): Caddy behind the
      existing Traefik, the receiver on Traefik's network and opted out of routing. Checked with
      `docker compose config` and `tests/test_docker_stack.py`, 2026-09-26; not yet run against
      a live Traefik.
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
| Streamlit must not be public on the VPS | F-75 in `issue.md` |
| the server's `data/` is discarded before a pull | F-74 in `issue.md` |
| Hostinger's n8n template runs behind Traefik on 80/443 | the owner, 2026-09-26; confirm with `docker ps` (section 2.1) |
| compose expands `$` in an interpolated value | F-58 in `issue.md` |
| a failed phase must stop the run | F-43 in `issue.md`, `lotto_analysis/analyzers/CLAUDE.md` |
| the site must not read `irish500.csv` | F-35, `frontend/CLAUDE.md` |
| `quickpick.py` never runs on the VPS | `plan.md` 3.5, root `CLAUDE.md` |
| the ingestion workflow and its failure email | [`n8n.md`](n8n.md) |
| the cutover that removes Streamlit | [`web.md`](web.md) section 8 |
