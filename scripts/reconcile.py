#!/usr/bin/env python3
"""Optional sanity check: compare resultsrekening CSV totals to ledger income/expenses.

Not a full close — portal resultatenrekening is indicative only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def books_root() -> Path:
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    from paths import books_dir

    return books_dir()


def parse_resultaten(path: Path) -> list[dict]:
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    header_i = None
    for i, row in enumerate(rows):
        if any("Jaar" in (c or "") and "maand" in (c or "").lower() for c in row):
            header_i = i
            break
        if "Omzet" in row:
            header_i = i
            break
    if header_i is None:
        return []
    headers = [h.strip() for h in rows[header_i]]
    out = []
    for row in rows[header_i + 1 :]:
        if not any(row):
            continue
        item = {headers[j]: (row[j] if j < len(row) else "") for j in range(len(headers))}
        # skip pure total rows without period key when both empty
        out.append(item)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compare resultatenrekening CSV to books (informational)")
    p.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to resultatenrekening.csv (default: books/inbox/resultatenrekening.csv)",
    )
    args = p.parse_args(argv)
    root = books_root()
    path = (args.csv or root / "inbox" / "resultatenrekening.csv").expanduser().resolve()
    if not path.exists():
        print(f"Missing {path}", file=sys.stderr)
        return 2
    rows = parse_resultaten(path)
    print(f"Parsed {len(rows)} resultatenrekening row(s) from {path.name}")
    print("Note: use bean-query for ledger P&L; this CSV is an indicative portal view.")
    for row in rows[:10]:
        period = row.get("Jaar & maand") or row.get("Jaar & maand".replace(" ", "\xa0")) or ""
        omzet = row.get("Omzet", "")
        resultaat = row.get("Resultaat", "")
        print(f"  period={period!r} omzet={omzet!r} resultaat={resultaat!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
