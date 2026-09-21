#!/usr/bin/env python3
"""
The rebuild receiver: runs drawpick.py when a new draw has been committed.

This is the second half of Phase 2B. n8n commits the row to data/irish500.csv, then posts
here, and the artifacts the website serves are rewritten. It lives in the data-engine image
because that is the only container with Python, the analysis code and write access to data/.

Design notes, in order of how much trouble they save:

- **No Docker socket.** A receiver that shells out to `docker run` needs the socket mounted,
  which is root on the host. This runs drawpick.py in its own process instead.
- **Signed, not just secret.** The caller sends an HMAC-SHA256 of the exact body it posted,
  and the comparison is constant time. A bare token in a header is fine until it appears in
  a log or a proxy trace.
- **One rebuild at a time.** A rebuild takes about a minute and writes the files the site is
  reading; two at once would interleave writes. A second request is refused, not queued.
- **Never on the public internet by default.** It binds to the address given and is meant to
  sit on the Docker network beside n8n, not behind the public reverse proxy. See
  nextStep/vps.md.

Standard library only: the engine's dependencies are pinned exactly so the VPS and the
owner's PC compute identical artifacts (F-44), and one endpoint hit three times a week does
not justify adding a web framework to that list.
"""

import hashlib
import hmac
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATH = "/rebuild"
SIGNATURE_HEADER = "X-Lotto-Signature"
MAX_BODY_BYTES = 64 * 1024

# drawpick.py takes about a minute; well short of this, and a hung run must not hold the
# lock for ever.
REBUILD_TIMEOUT_SECONDS = 15 * 60

_lock = threading.Lock()
_last_result = {"state": "never run"}


def secret() -> bytes:
    """The shared secret, required. Refusing to start beats accepting anything."""
    value = os.environ.get("REBUILD_SECRET", "")
    if len(value) < 16:
        raise SystemExit(
            "REBUILD_SECRET must be set to at least 16 characters - refusing to start"
        )
    return value.encode()


def expected_signature(body: bytes, key: bytes) -> str:
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def signature_ok(body: bytes, sent: str, key: bytes) -> bool:
    """Constant-time comparison; a wrong length is a mismatch, not an error."""
    return hmac.compare_digest(expected_signature(body, key), (sent or "").strip())


def run_drawpick(repo_root: str) -> dict:
    """Run the engine once and report what happened. Never raises."""
    started = time.time()
    try:
        finished = subprocess.run(
            [sys.executable, "drawpick.py"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=REBUILD_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {
            "state": "timed out",
            "seconds": round(time.time() - started, 1),
            "exit_code": None,
        }

    return {
        "state": "ok" if finished.returncode == 0 else "failed",
        "seconds": round(time.time() - started, 1),
        "exit_code": finished.returncode,
        # The tail is what a failure email needs; the whole log is in the container's.
        "tail": finished.stdout.strip().splitlines()[-12:],
        "stderr_tail": finished.stderr.strip().splitlines()[-12:],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "lotto-rebuild"
    sys_version = ""

    # The secret and the working directory are set on the server object.
    @property
    def key(self) -> bytes:
        return self.server.rebuild_secret

    @property
    def repo_root(self) -> str:
        return self.server.repo_root

    def _reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - the stdlib spells it this way
        if self.path != "/health":
            self._reply(404, {"error": "not found"})
            return
        self._reply(200, {"state": "listening", "last_rebuild": _last_result})

    def do_POST(self):  # noqa: N802
        if self.path != PATH:
            self._reply(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            self._reply(413, {"error": "body too large"})
            return
        body = self.rfile.read(length) if length else b""

        if not signature_ok(body, self.headers.get(SIGNATURE_HEADER, ""), self.key):
            # Deliberately says nothing about which part was wrong.
            self._reply(401, {"error": "bad signature"})
            return

        if not _lock.acquire(blocking=False):
            self._reply(409, {"error": "a rebuild is already running"})
            return

        try:
            global _last_result
            _last_result = run_drawpick(self.repo_root)
            status = 200 if _last_result["state"] == "ok" else 500
            self._reply(status, _last_result)
        finally:
            _lock.release()

    def log_message(self, fmt, *args):
        """One line per request, to stdout, so docker logs has it."""
        sys.stdout.write(
            "%s - %s\n" % (self.address_string(), fmt % args)
        )
        sys.stdout.flush()


def serve(host: str, port: int, repo_root: str, key: bytes) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), Handler)
    server.rebuild_secret = key
    server.repo_root = repo_root
    return server


def main() -> None:
    host = os.environ.get("REBUILD_HOST", "0.0.0.0")
    port = int(os.environ.get("REBUILD_PORT", "8080"))
    repo_root = os.environ.get("REBUILD_WORKDIR", os.getcwd())

    server = serve(host, port, repo_root, secret())
    print(f"rebuild receiver listening on {host}:{port}{PATH}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
