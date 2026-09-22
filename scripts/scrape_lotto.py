#!/usr/bin/env python3
"""
scripts/scrape_lotto.py
=======================
Automated web scraper for the Irish National Lottery results.
Scrapes the most recent draws (Monday, Wednesday and Saturday) and updates
data/irish500.csv atomically.

Two sources, both implemented:
- Primary: https://irish.national-lottery.com/irish-lotto/results-archive-YYYY
- Fallback: https://www.lottery.ie/results/lotto/history

Whichever source is used for the data, the other is used to verify it: dates present
in both must carry identical numbers or nothing is written. Both parsers reject any
row that is not the main Lotto draw - the same page carries Lotto Plus 1 and Plus 2,
which share the draw date.
"""

import sys
import os
import re
import argparse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

CSV_FILE = Path("data/irish500.csv")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
MAX_BALL = 47

PRIMARY_NAME = "irish.national-lottery.com"
FALLBACK_NAME = "lottery.ie"
FALLBACK_URL = "https://www.lottery.ie/results/lotto/history"

# The archive table marks each ball with its game. Lotto Plus rows carry
# 'irish-lotto-plus-1' / '-plus-2', so the token must match exactly.
ARCHIVE_GAME_TOKEN = "irish-lotto"

# lottery.ie renders every ball with this class, for all three games.
LOTTERY_IE_BALL = r'<div class="flex font-bold rounded-full[^"]*">(\d{1,2})</div>'


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch URL with browser headers."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-IE,en-US;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def build_draw(dt: datetime, main_balls: List[int], bonus_balls: List[int]) -> Optional[Dict]:
    """
    Validate one parsed draw and format it for the CSV.

    Returns None if the draw is not a well-formed main Lotto result: 6 main balls,
    1 bonus, all within 1-47 and all seven distinct.
    """
    if len(main_balls) != 6 or len(bonus_balls) != 1:
        return None

    all_nums = main_balls + bonus_balls
    if not all(1 <= n <= MAX_BALL for n in all_nums) or len(set(all_nums)) != 7:
        return None

    date_str = dt.strftime("%d %b %Y")
    main_formatted = [f"{n:02d}" for n in main_balls]
    return {
        "dt": dt,
        "date_str": date_str,
        "main": main_balls,
        "bonus": bonus_balls[0],
        "csv_row": f"{date_str},{','.join(main_formatted)},{bonus_balls[0]:02d}",
    }


def parse_archive_table(html: str) -> List[Dict]:
    """
    Parse draw results from the results-archive table.

    Main-draw verification: the row's date link carries the game in its path
    (`/irish-lotto/results-...`, so a Plus row's link does not match), the row must
    hold exactly one ball list so the link and the balls cannot refer to different
    games, and every ball must carry the `irish-lotto` class token.
    """
    draws = []

    for block in re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE):
        date_match = re.search(r'/irish-lotto/results-(\d{2})-(\d{2})-(\d{4})', block)
        if not date_match:
            continue
        day, month, year = date_match.groups()
        dt = datetime(int(year), int(month), int(day))

        balls_lists = re.findall(r'<ul class="balls">(.*?)</ul>', block, re.DOTALL)
        if len(balls_lists) != 1:
            if balls_lists:
                print(f"  Skipping {dt:%d %b %Y}: row holds {len(balls_lists)} ball lists, "
                      f"cannot tell which game the link belongs to")
            continue

        main_balls = []
        bonus_balls = []
        wrong_game = False
        for cls, num in re.findall(r'<li class="([^"]*)">(\d+)</li>', balls_lists[0]):
            tokens = cls.split()
            if ARCHIVE_GAME_TOKEN not in tokens:
                wrong_game = True
                break
            if 'bonus-ball' in tokens:
                bonus_balls.append(int(num))
            else:
                main_balls.append(int(num))

        if wrong_game:
            print(f"  Skipping {dt:%d %b %Y}: balls are not tagged {ARCHIVE_GAME_TOKEN}")
            continue

        draw = build_draw(dt, main_balls, bonus_balls)
        if draw:
            draws.append(draw)

    draws.sort(key=lambda x: x["dt"], reverse=True)
    return draws


def parse_lottery_ie(html: str) -> List[Dict]:
    """
    Parse draw results from the lottery.ie history page.

    Each draw section holds three games in order - Lotto, then Lotto Plus 1 and
    Plus 2 - under repeated 'Winning numbers' / 'Bonus' labels with no game heading
    to key on. The main draw is the first pair. If a Plus marker appears before it the
    order has changed, and the section is skipped rather than guessed at.
    """
    draws = []
    # The newest draw is headed 'Last draw, ...', every older one 'Draw, ...'.
    headers = list(re.finditer(r'<h2 aria-label="(?:Last draw|Draw), ([^"]+)"', html))

    for i, header in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(html)
        section = html[header.start():end]

        label = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', header.group(1))
        try:
            dt = datetime.strptime(label, "%A, %B %d, %Y")
        except ValueError:
            print(f"  Skipping section: cannot parse date {header.group(1)!r}")
            continue

        main_at = section.find('>Winning numbers<')
        bonus_at = section.find('>Bonus<')
        if main_at == -1 or bonus_at <= main_at:
            continue
        if 'Plus' in section[:main_at]:
            print(f"  Skipping {dt:%d %b %Y}: a Plus game precedes the main draw block")
            continue

        main_balls = [int(n) for n in re.findall(LOTTERY_IE_BALL, section[main_at:bonus_at])]
        bonus_balls = [int(n) for n in re.findall(LOTTERY_IE_BALL, section[bonus_at:])[:1]]

        draw = build_draw(dt, main_balls, bonus_balls)
        if draw:
            draws.append(draw)

    draws.sort(key=lambda x: x["dt"], reverse=True)
    return draws


def scrape(name: str, url: str, parser) -> List[Dict]:
    """Fetch and parse one source. Returns [] if it is unreachable or unparseable."""
    print(f"Fetching {name}: {url}")
    try:
        html = fetch_url(url)
    except Exception as e:
        print(f"  {name} unreachable: {type(e).__name__}: {e}")
        return []

    draws = parser(html)
    print(f"  {name}: parsed {len(draws)} valid main-draw result(s)")
    return draws


def cross_check(draws: List[Dict], other: List[Dict]) -> Tuple[int, List[str]]:
    """
    Compare two sources on the dates they share.

    Returns (dates_agreed, mismatches). A date held by only one source is not a
    mismatch - the fallback page carries only the most recent draws.
    """
    other_by_date = {d["dt"].date(): d for d in other}
    agreed = 0
    mismatches = []

    for draw in draws:
        twin = other_by_date.get(draw["dt"].date())
        if not twin:
            continue
        if sorted(draw["main"]) == sorted(twin["main"]) and draw["bonus"] == twin["bonus"]:
            agreed += 1
        else:
            mismatches.append(
                f"{draw['date_str']}: {sorted(draw['main'])}+{draw['bonus']} "
                f"vs {sorted(twin['main'])}+{twin['bonus']}"
            )

    return agreed, mismatches


def get_existing_dates(csv_path: Path) -> Tuple[str, set]:
    """Get header and set of dates already present in the CSV (string & normalized)."""
    if not csv_path.exists():
        return "Date,Num1,Num2,Num3,Num4,Num5,Num6,Bonus", set()

    with open(csv_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    header = lines[0] if lines else "Date,Num1,Num2,Num3,Num4,Num5,Num6,Bonus"
    existing_dates = set()
    for row in lines[1:]:
        parts = row.split(",")
        if parts:
            d_str = parts[0].strip()
            existing_dates.add(d_str)
            for fmt in ("%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    existing_dates.add(datetime.strptime(d_str, fmt).date())
                    break
                except ValueError:
                    pass

    return header, existing_dates


def update_csv_with_draws(csv_path: Path, new_draws: List[Dict], dry_run: bool = False) -> int:
    """Prepend new draws to CSV file atomically."""
    if not new_draws:
        print("No new draws to add.")
        return 0

    header, existing_dates = get_existing_dates(csv_path)

    # Filter out draws that already exist (check both string and date object)
    draws_to_add = [
        d for d in new_draws
        if d["date_str"] not in existing_dates and d["dt"].date() not in existing_dates
    ]
    if not draws_to_add:
        print("All scraped draws already exist in the dataset.")
        return 0

    print(f"Found {len(draws_to_add)} new draw(s) to add:")
    for d in draws_to_add:
        print(f"  + {d['csv_row']}")

    if dry_run:
        print("[DRY RUN] No files modified.")
        return len(draws_to_add)

    # Read all existing lines
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    existing_rows = lines[1:] if len(lines) > 1 else []

    # Sort draws_to_add descending so newest is at the top
    draws_to_add.sort(key=lambda x: x["dt"], reverse=True)
    new_rows = [d["csv_row"] for d in draws_to_add]

    # Write updated CSV
    all_lines = [header] + new_rows + existing_rows
    temp_path = csv_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines) + "\n")

    os.replace(temp_path, csv_path)
    print(f"Updated {csv_path} (Total draws: {len(all_lines) - 1})")
    return len(draws_to_add)


def main():
    parser = argparse.ArgumentParser(description="Scrape latest Irish Lotto winning numbers")
    parser.add_argument("--dry-run", action="store_true", help="Check for new draws without updating CSV")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="Year archive to scrape")
    parser.add_argument("--skip-verify", action="store_true",
                        help="Use one source only, without cross-checking the other")
    args = parser.parse_args()

    primary_url = f"https://irish.national-lottery.com/irish-lotto/results-archive-{args.year}"
    primary = scrape(PRIMARY_NAME, primary_url, parse_archive_table)

    fallback = []
    if not primary or not args.skip_verify:
        fallback = scrape(FALLBACK_NAME, FALLBACK_URL, parse_lottery_ie)

    if primary:
        source, draws, other = PRIMARY_NAME, primary, fallback
    elif fallback:
        print(f"Primary source yielded nothing - falling back to {FALLBACK_NAME}")
        source, draws, other = FALLBACK_NAME, fallback, []
    else:
        print("Both sources failed to yield a valid draw. Check connection, Cloudflare, or markup.")
        sys.exit(1)

    if other:
        agreed, mismatches = cross_check(draws, other)
        if mismatches:
            print(f"Sources disagree on {len(mismatches)} date(s) - refusing to write:")
            for line in mismatches:
                print(f"  ! {line}")
            sys.exit(1)
        print(f"Verified {agreed} shared date(s) against {FALLBACK_NAME}")
    elif not args.skip_verify:
        print(f"Unverified: {FALLBACK_NAME} returned no draws to cross-check against")

    latest = draws[0]
    print(f"Using {source}. Latest draw: {latest['date_str']} "
          f"(Numbers: {latest['main']} + Bonus: {latest['bonus']})")

    added = update_csv_with_draws(CSV_FILE, draws, dry_run=args.dry_run)
    if added > 0 and not args.dry_run:
        print("\nNext step: Run 'python drawpick.py' and 'python quickpick.py' to refresh models and analysis.")


if __name__ == "__main__":
    main()
