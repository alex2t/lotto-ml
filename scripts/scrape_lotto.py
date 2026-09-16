#!/usr/bin/env python3
"""
scripts/scrape_lotto.py
=======================
Automated web scraper for the Irish National Lottery results.
Scrapes the most recent draw (including Monday, Wednesday, Saturday draws)
and updates data/irish500.csv atomically.

Supports:
- Primary source: https://irish.national-lottery.com/irish-lotto/results-archive-2026
- Backup / Alternative parser: https://www.lottery.ie/results/lotto/history
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


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch URL with browser User-Agent."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def parse_archive_table(html: str) -> List[Dict]:
    """Parse draw results from the results archive table."""
    draws = []
    draw_blocks = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)

    for block in draw_blocks:
        date_match = re.search(r'/irish-lotto/results-(\d{2})-(\d{2})-(\d{4})', block)
        if not date_match:
            continue
        day, month, year = date_match.groups()
        dt = datetime(int(year), int(month), int(day))
        date_str = dt.strftime("%d %b %Y")

        balls_ul = re.search(r'<ul class="balls">(.*?)</ul>', block, re.DOTALL)
        if not balls_ul:
            continue

        lis = re.findall(r'<li class="([^"]*)">(\d+)</li>', balls_ul.group(1))
        main_balls = []
        bonus_balls = []
        for cls, num in lis:
            if 'bonus-ball' in cls:
                bonus_balls.append(int(num))
            else:
                main_balls.append(int(num))

        if len(main_balls) == 6 and len(bonus_balls) == 1:
            # Validate ranges and uniqueness across all 7 balls (C-14 fix)
            all_nums = main_balls + bonus_balls
            if all(1 <= n <= 47 for n in all_nums) and len(set(all_nums)) == 7:
                main_formatted = [f"{n:02d}" for n in main_balls]
                bonus_formatted = f"{bonus_balls[0]:02d}"
                csv_row = f"{date_str},{','.join(main_formatted)},{bonus_formatted}"
                draws.append({
                    "dt": dt,
                    "date_str": date_str,
                    "main": main_balls,
                    "bonus": bonus_balls[0],
                    "csv_row": csv_row
                })

    draws.sort(key=lambda x: x["dt"], reverse=True)
    return draws


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
    print(f"✓ Successfully updated {csv_path} (Total draws: {len(all_lines) - 1})")
    return len(draws_to_add)


def main():
    parser = argparse.ArgumentParser(description="Scrape latest Irish Lotto winning numbers")
    parser.add_argument("--dry-run", action="store_true", help="Check for new draws without updating CSV")
    parser.add_argument("--year", type=int, default=2026, help="Year archive to scrape (default: 2026)")
    args = parser.parse_args()

    url = f"https://irish.national-lottery.com/irish-lotto/results-archive-{args.year}"
    print(f"Fetching Irish Lotto results from: {url}")

    try:
        html = fetch_url(url)
        draws = parse_archive_table(html)
        if not draws:
            print(f"✗ Failed to parse any valid draws from {url}. Check connection, Cloudflare, or markup.")
            sys.exit(1)

        print(f"Scraped {len(draws)} valid draws for {args.year}.")
        latest = draws[0]
        print(f"Latest draw found: {latest['date_str']} (Numbers: {latest['main']} + Bonus: {latest['bonus']})")

        added = update_csv_with_draws(CSV_FILE, draws, dry_run=args.dry_run)
        if added > 0 and not args.dry_run:
            print("\nNext step: Run 'python drawpick.py' and 'python quickpick.py' to refresh models and analysis.")
    except Exception as e:
        print(f"✗ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
