#!/usr/bin/env python3
"""
The rebuild receiver: runs drawpick.py when a new draw has been committed.

This is the second half of Phase 2B. n8n commits the row to GitHub for history, then posts
the draw here; this appends it to the VPS's own data/irish500.csv and rewrites the artifacts
the website serves. It lives in the data-engine image because that is the only container
with Python, the analysis code and write access to data/. The design is
nextStep/lottodraw.md.

Design notes, in order of how much trouble they save:

- **It rebuilds because the data changed, not because it was asked** (F-64). A draw already
  in the CSV appends nothing and runs nothing, so a retried n8n execution is free. The one
  exception is the repair case: artifacts older than the CSV mean an append survived a run
  that did not, and the same request is what fixes it.

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
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PATH = "/rebuild"
SIGNATURE_HEADER = "X-Lotto-Signature"
MAX_BODY_BYTES = 64 * 1024

CSV_RELATIVE = "data/irish500.csv"
CSV_DATE_FORMAT = "%d %b %Y"
LINE_SIZE = 6
NUMBER_MAX = 47

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


class Rejected(Exception):
    """The body is signed but the draw in it is not one we will write to the CSV."""


def parse_draw(body: bytes, newest_in_csv=None) -> dict:
    """The payload of nextStep/lottodraw.md section 3, validated. Raises Rejected."""
    try:
        payload = json.loads(body or b"")
    except ValueError:
        raise Rejected("body is not JSON")
    if not isinstance(payload, dict):
        raise Rejected("body is not an object")

    try:
        drawn_on = datetime.strptime(str(payload.get("date")), "%Y-%m-%d").date()
    except ValueError:
        raise Rejected("date must be ISO YYYY-MM-DD")
    if drawn_on > date.today():
        raise Rejected("date is in the future")
    if newest_in_csv is not None and drawn_on < newest_in_csv:
        raise Rejected(f"date is older than the newest row ({newest_in_csv.isoformat()})")

    main = payload.get("main")
    if not isinstance(main, list) or len(main) != LINE_SIZE:
        raise Rejected(f"main must be {LINE_SIZE} numbers")
    if not all(isinstance(n, int) and not isinstance(n, bool) for n in main):
        raise Rejected("main must be integers")
    if len(set(main)) != LINE_SIZE:
        raise Rejected("main numbers must be distinct")
    if not all(1 <= n <= NUMBER_MAX for n in main):
        raise Rejected(f"main numbers must be 1-{NUMBER_MAX}")

    bonus = payload.get("bonus")
    if not isinstance(bonus, int) or isinstance(bonus, bool):
        raise Rejected("bonus must be an integer")
    if not 1 <= bonus <= NUMBER_MAX:
        raise Rejected(f"bonus must be 1-{NUMBER_MAX}")
    if bonus in main:
        raise Rejected("bonus must not be one of the main numbers")

    return {"date": drawn_on, "main": sorted(main), "bonus": bonus}


def csv_path(repo_root: str) -> Path:
    return Path(repo_root) / CSV_RELATIVE


def csv_lines(path: Path) -> list:
    """The file as lines, without endings. The CSV is stored LF (F-44)."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return text.rstrip("\n").split("\n")


def row_date(line: str):
    """The date of a CSV row, or None for the header or a blank line."""
    try:
        return datetime.strptime(line.split(",")[0].strip(), CSV_DATE_FORMAT).date()
    except (ValueError, IndexError):
        return None


def newest_row(lines: list):
    """The first data row; the file is newest-first."""
    for line in lines[1:]:
        if row_date(line):
            return line
    return None


def newest_date(lines: list):
    """The date of the first data row."""
    row = newest_row(lines)
    return row_date(row) if row else None


def row_numbers(line: str) -> dict:
    """The six main numbers of a CSV row, sorted, and its bonus - comparable with a draw."""
    numbers = [int(value) for value in line.split(",")[1:]]
    return {"main": sorted(numbers[:LINE_SIZE]), "bonus": numbers[LINE_SIZE]}


def format_row(draw: dict) -> str:
    """`19 Sep 2026,10,11,20,28,41,44,02` - the format the file already holds."""
    numbers = ",".join(f"{n:02d}" for n in draw["main"] + [draw["bonus"]])
    return f"{draw['date'].strftime(CSV_DATE_FORMAT)},{numbers}"


def append_draw(path: Path, draw: dict, lines: list) -> None:
    """Insert the row after the header and replace the file atomically.

    A direct write that is interrupted leaves a truncated CSV that drawpick.py would read
    without complaint, so the new content goes to a temp file in the same directory first.
    """
    content = "\n".join([lines[0], format_row(draw)] + lines[1:]) + "\n"
    temp = path.with_name(path.name + ".new")
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def expected_artifacts() -> list:
    """drawpick.py's own list, so the two can never drift."""
    from drawpick import EXPECTED_ARTIFACTS

    return EXPECTED_ARTIFACTS


def artifact_state(repo_root: str) -> tuple:
    """(how many expected artifacts exist, whether any is missing or older than the CSV)."""
    csv_mtime = csv_path(repo_root).stat().st_mtime
    present = 0
    stale = False
    for relative in expected_artifacts():
        path = Path(repo_root) / relative
        if not path.exists():
            stale = True
        else:
            present += 1
            if path.stat().st_mtime < csv_mtime:
                stale = True
    return present, stale


def handle_draw(repo_root: str, body: bytes) -> tuple:
    """Append the draw if it is new, rebuild if the data changed or the artifacts are stale.

    A draw for the date already in the file with other numbers is a 409 conflict: nothing is
    written or rebuilt. Returns (http status, response body). Raises Rejected for a draw we
    will not write.
    """
    path = csv_path(repo_root)
    lines = csv_lines(path)
    newest = newest_date(lines)
    draw = parse_draw(body, newest)

    # A date older than the newest row is already rejected, so the only date that can
    # already be in the file is the newest one.
    appended = draw["date"] != newest
    if not appended:
        # The same date is the same draw only if the numbers agree (F-72). If they do not,
        # one side misread it: keep the row, rebuild nothing, and say so.
        held = row_numbers(newest_row(lines))
        posted = {"main": draw["main"], "bonus": draw["bonus"]}
        if held != posted:
            return 409, {
                "state": "conflict",
                "draw": draw["date"].isoformat(),
                "appended": False,
                "csv_rows": len(lines) - 1,
                "in_csv": held,
                "posted": posted,
            }
    else:
        append_draw(path, draw, lines)

    _, stale = artifact_state(repo_root)
    result = {
        "draw": draw["date"].isoformat(),
        "appended": appended,
        "csv_rows": len(csv_lines(path)) - 1,
    }

    if not appended and not stale:
        result.update(state="already had it", seconds=0.0,
                      artifacts=artifact_state(repo_root)[0])
        return 200, result

    run = run_drawpick(repo_root)
    result["seconds"] = run["seconds"]
    result["artifacts"] = artifact_state(repo_root)[0]
    if run["state"] != "ok":
        result.update(state="failed", **{k: v for k, v in run.items() if k != "state"})
        return 500, result
    result["state"] = "rebuilt" if appended else "rebuilt stale artifacts"
    return 200, result


def run_drawpick(repo_root: str) -> dict:
    """Run the engine once and report what happened. Never raises."""
    started = time.time()
    try:
        finished = subprocess.run(
            [sys.executable, "drawpick.py"],
            cwd=repo_root,
            capture_output=True,
            # The engine prints emoji. text=True decodes with the locale codec, which is
            # cp1252 on the owner's PC and raises on the first one, killing the reader
            # thread and leaving stdout as None - a successful rebuild reported as a crash.
            encoding="utf-8",
            errors="replace",
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

        # The CSV is read, compared and appended under the lock, so two draws arriving
        # together cannot both decide they are new.
        try:
            global _last_result
            try:
                status, result = handle_draw(self.repo_root, body)
            except Rejected as rejected:
                self._reply(400, {"state": "rejected", "error": str(rejected)})
                return
            _last_result = result
            self._reply(status, result)
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
