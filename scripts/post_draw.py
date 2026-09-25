#!/usr/bin/env python3
"""
Post one draw to the rebuild receiver, signed exactly as n8n signs it.

The body is `JSON.stringify({date, main, bonus})` - compact, keys in that order - and the
signature is the HMAC-SHA256 of those exact bytes with REBUILD_SECRET, sent in
X-Lotto-Signature. Use it to test the receiver before n8n is wired to it:

    $env:REBUILD_SECRET = "<the value from secrets.env>"
    python scripts/post_draw.py 2026-09-21 15 24 29 30 31 38 --bonus 11

Standard library only, like the receiver.
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8080/rebuild"


def signed_request(url: str, date: str, main: list, bonus: int, key: bytes):
    """The request n8n's Code node and HTTP Request node send between them."""
    body = json.dumps({"date": date, "main": main, "bonus": bonus}, separators=(",", ":"))
    signature = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
    return urllib.request.Request(
        url,
        data=body.encode(),
        headers={"Content-Type": "application/json", "X-Lotto-Signature": signature},
        method="POST",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Post one signed draw to the rebuild receiver.")
    parser.add_argument("date", help="the draw date, YYYY-MM-DD")
    parser.add_argument("main", nargs=6, type=int, help="the six main numbers")
    parser.add_argument("--bonus", type=int, required=True)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    key = os.environ.get("REBUILD_SECRET", "")
    if not key:
        sys.exit("Set REBUILD_SECRET in this shell to the value in secrets.env first.")

    request = signed_request(args.url, args.date, args.main, args.bonus, key.encode())
    print(f"POST {args.url}\n{request.data.decode()}\n")
    try:
        with urllib.request.urlopen(request, timeout=20 * 60) as response:
            status, reply = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        status, reply = error.code, error.read().decode()
    except urllib.error.URLError as error:
        sys.exit(f"No receiver answered at {args.url}: {error.reason}")
    print(status, json.dumps(json.loads(reply), indent=2))
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
