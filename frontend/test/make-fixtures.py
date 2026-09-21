"""
Rebuilds frontend/test/fixtures/ from data/.

The fixtures are a trimmed copy of the real artifacts: every file as written, except
lotto_draw_history.json and irish500.csv, which keep only their most recent entries so the
committed fixtures stay small. The CSV is there for the admin download route only - no other
part of the site may read it (F-35). Run from the project root after an artifact's shape changes:

    python frontend/test/make-fixtures.py
"""
import json
import shutil
from pathlib import Path

KEEP_DRAWS = 30
KEEP_CSV_ROWS = 30
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data"
DST = Path(__file__).resolve().parent / "fixtures"


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    for path in sorted(SRC.glob("*.json")):
        if path.name == "lotto_draw_history.json":
            history = json.loads(path.read_text(encoding="utf-8"))
            kept = {d: history[d] for d in sorted(history)[-KEEP_DRAWS:]}
            (DST / path.name).write_text(
                json.dumps(kept, indent=2), encoding="utf-8", newline="\n"
            )
        else:
            shutil.copyfile(path, DST / path.name)
        print(f"wrote {path.name}")

    csv = (SRC / "irish500.csv").read_text(encoding="utf-8").splitlines()
    kept = csv[: KEEP_CSV_ROWS + 1]
    (DST / "irish500.csv").write_text(
        chr(10).join(kept) + chr(10), encoding="utf-8", newline=chr(10)
    )
    print("wrote irish500.csv")


if __name__ == "__main__":
    main()
