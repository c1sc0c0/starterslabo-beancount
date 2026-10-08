#!/usr/bin/env python3
"""Normalize starterslabo-export Rapport CSVs into JSONL intermediate records.

Reads verkopen.csv + aankopen.csv (and optionally grootboekhistoriek*.csv).
Writes one JSON object per line to transactions.jsonl.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

PORTAL_ACCOUNT_RE = re.compile(r"^(\d{6})\s*(?:-\s*(.*))?$")


def books_root() -> Path:
    """Resolve private books/ directory.

    Order: STARTERSLABO_BOOKS env → walk parents for books/main.bean →
    legacy path when this file lives in books/imports/starterslabo/.
    """
    import os

    env = (os.environ.get("STARTERSLABO_BOOKS") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "books"
        if (candidate / "main.bean").exists():
            return candidate
        if parent.name == "books" and (parent / "main.bean").exists():
            return parent
    # scripts living at books/imports/starterslabo/normalize.py
    return here.parents[2]


def stable_id(kind: str, date: str, payee: str, amount: str, narration: str, boekstuknr: str) -> str:
    if boekstuknr.strip():
        raw = f"{kind}|boekstuknr|{boekstuknr.strip()}"
    else:
        raw = f"{kind}|{date}|{payee}|{amount}|{narration}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{kind}:{digest}"


def parse_amount(value: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip().replace("\xa0", " ").replace(" ", "")
    if not text:
        return None
    # Belgian "0,00" / Excel-exported "592.08"
    text = text.replace(",", ".")
    if text.count(".") > 1:
        # thousand separators: 1.234.56 → invalid for us; strip middle dots
        parts = text.split(".")
        text = "".join(parts[:-1]) + "." + parts[-1]
    try:
        amount = float(text)
    except ValueError:
        return None
    # Canonical string without scientific notation
    if amount == int(amount) and abs(amount) < 1e12:
        return str(int(amount)) if abs(amount - int(amount)) < 1e-9 else f"{amount}"
    return f"{amount:.2f}".rstrip("0").rstrip(".") if "." in f"{amount:.2f}" else f"{amount:.2f}"


def normalize_amount_str(value: str) -> str | None:
    parsed = parse_amount(value)
    if parsed is None:
        return None
    # Always two decimals for money in IR
    return f"{float(parsed):.2f}"


def find_header_row(rows: list[list[str]], required: set[str]) -> tuple[int, list[str]] | None:
    for i, row in enumerate(rows):
        cells = [c.strip() for c in row]
        if required.issubset(set(cells)):
            return i, cells
    return None


def read_csv_rows(path: Path) -> list[list[str]]:
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.reader(text.splitlines()))


def parse_portal_account(type_kosten: str) -> tuple[str, str]:
    text = (type_kosten or "").strip()
    m = PORTAL_ACCOUNT_RE.match(text)
    if not m:
        return "", text
    return m.group(1), (m.group(2) or "").strip()


def is_total_or_junk(date: str, amount: str | None, payee: str) -> bool:
    if not date and not payee:
        return True
    if not date:
        return True
    if amount is None:
        return True
    return False


def normalize_sales(path: Path, include_pending: bool) -> list[dict]:
    rows = read_csv_rows(path)
    found = find_header_row(rows, {"Factuurdatum", "Factuurbedrag", "Klant"})
    if not found:
        print(f"warning: no verkopen header in {path.name}", file=sys.stderr)
        return []
    header_i, headers = found
    idx = {h: i for i, h in enumerate(headers)}
    out: list[dict] = []
    for rnum, row in enumerate(rows[header_i + 1 :], start=header_i + 2):
        def cell(name: str) -> str:
            i = idx.get(name)
            if i is None or i >= len(row):
                return ""
            return (row[i] or "").strip()

        date = cell("Factuurdatum")
        payee = cell("Klant")
        amount = normalize_amount_str(cell("Factuurbedrag"))
        if is_total_or_junk(date, amount, payee):
            continue
        status = cell("Status")
        if not include_pending and status.lower() == "in behandeling":
            continue
        boekstuknr = cell("Boekstuknr")
        narration = cell("Type") or "Verkoopfactuur"
        open_amt = cell("Nog openstaand")
        rid = stable_id("sale", date, payee, amount or "", narration, boekstuknr)
        out.append(
            {
                "source": "starterslabo",
                "kind": "sale",
                "id": rid,
                "date": date,
                "payee": payee,
                "narration": narration,
                "amount": amount,
                "currency": "EUR",
                "status": status,
                "boekstuknr": boekstuknr,
                "open_amount": open_amt,
                "portal_account": "",
                "portal_account_label": "",
                "payment_state": "",
                "needs_review": status.lower() == "in behandeling" or not boekstuknr,
                "csv_file": path.name,
                "csv_row": rnum,
            }
        )
    return out


def normalize_purchases(path: Path, include_pending: bool) -> list[dict]:
    rows = read_csv_rows(path)
    found = find_header_row(rows, {"Factuurdatum", "Leverancier", "Factuurbedrag"})
    if not found:
        print(f"warning: no aankopen header in {path.name}", file=sys.stderr)
        return []
    header_i, headers = found
    idx = {h: i for i, h in enumerate(headers)}
    out: list[dict] = []
    for rnum, row in enumerate(rows[header_i + 1 :], start=header_i + 2):
        def cell(name: str) -> str:
            i = idx.get(name)
            if i is None or i >= len(row):
                return ""
            return (row[i] or "").strip()

        date = cell("Factuurdatum")
        payee = cell("Leverancier")
        amount = normalize_amount_str(cell("Factuurbedrag"))
        if is_total_or_junk(date, amount, payee):
            continue
        status = cell("Status")
        if not include_pending and status.lower() == "in behandeling":
            continue
        type_kosten = cell("Type kosten")
        code, label = parse_portal_account(type_kosten)
        boekstuknr = cell("Boekstuknr")
        payment_state = cell("Te betalen a. leverancier")
        open_amt = cell("Nog openstaand")
        narration = label or type_kosten or "Aankoop"
        rid = stable_id("purchase", date, payee, amount or "", narration, boekstuknr)
        out.append(
            {
                "source": "starterslabo",
                "kind": "purchase",
                "id": rid,
                "date": date,
                "payee": payee,
                "narration": narration,
                "amount": amount,
                "currency": "EUR",
                "status": status,
                "boekstuknr": boekstuknr,
                "open_amount": open_amt,
                "portal_account": code,
                "portal_account_label": label,
                "payment_state": payment_state,
                "needs_review": (not code) or status.lower() == "in behandeling",
                "csv_file": path.name,
                "csv_row": rnum,
            }
        )
    return out


def normalize_grootboek(path: Path) -> list[dict]:
    """Phase-2: parse grootboek / detail CSVs into posting-line IR.

    Groups by boekstuknr when present. Empty detail sheets yield [].
    """
    rows = read_csv_rows(path)
    # Try common header variants from portal widgets
    candidates = [
        {"Factuurdatum", "Boekstuknr", "Rekening"},
        {"Factuurdatum", "Boekstuknr", "Omschrijving"},
        {"docdate", "bkstnr", "Reknr"},
        {"Rekening", "Omschrijving", "Factuurdatum"},
    ]
    found = None
    for req in candidates:
        found = find_header_row(rows, req)
        if found:
            break
    if not found:
        # Soft fail — many exports are empty shells
        return []
    header_i, headers = found
    idx = {h: i for i, h in enumerate(headers)}

    def cell(row: list[str], name: str) -> str:
        for key in (name, name.lower(), name.title()):
            i = idx.get(key)
            if i is not None and i < len(row):
                return (row[i] or "").strip()
        # fuzzy
        for h, i in idx.items():
            if name.lower() in h.lower() and i < len(row):
                return (row[i] or "").strip()
        return ""

    lines: list[dict] = []
    for rnum, row in enumerate(rows[header_i + 1 :], start=header_i + 2):
        date = cell(row, "Factuurdatum") or cell(row, "docdate")
        rekening = cell(row, "Rekening") or cell(row, "Reknr")
        boekstuknr = cell(row, "Boekstuknr") or cell(row, "bkstnr")
        omschrijving = cell(row, "Omschrijving") or cell(row, "Omschrijving factuur")
        bedrag = normalize_amount_str(
            cell(row, "Bedrag") or cell(row, "MvH") or cell(row, "Factuurbedrag")
        )
        if not date and not rekening and not boekstuknr:
            continue
        if bedrag is None and not rekening:
            continue
        code, label = parse_portal_account(rekening) if rekening else ("", "")
        if not code and rekening.isdigit() and len(rekening) == 6:
            code, label = rekening, omschrijving
        rid = stable_id(
            "posting",
            date,
            rekening,
            bedrag or "0",
            omschrijving,
            boekstuknr or f"{path.name}:{rnum}",
        )
        lines.append(
            {
                "source": "starterslabo",
                "kind": "posting",
                "id": rid,
                "date": date or "1970-01-01",
                "payee": "",
                "narration": omschrijving or label or "Grootboek",
                "amount": bedrag or "0.00",
                "currency": "EUR",
                "status": "",
                "boekstuknr": boekstuknr,
                "open_amount": "",
                "portal_account": code or rekening,
                "portal_account_label": label,
                "payment_state": "",
                "btw_code": cell(row, "btw-code") or cell(row, "btw_code"),
                "needs_review": True,
                "csv_file": path.name,
                "csv_row": rnum,
            }
        )
    return lines


def discover_files(inbox: Path) -> dict[str, list[Path]]:
    return {
        "sales": sorted(inbox.glob("verkopen*.csv")),
        "purchases": sorted(inbox.glob("aankopen*.csv")),
        "grootboek": sorted(
            list(inbox.glob("grootboekhistoriek*.csv"))
            + list(inbox.glob("*grootboek*.csv"))
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Normalize Rapport CSVs → JSONL")
    p.add_argument(
        "--inbox",
        type=Path,
        default=None,
        help="Directory with verkopen.csv / aankopen.csv (default: books/inbox)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSONL path (default: books/imports/starterslabo/transactions.jsonl)",
    )
    p.add_argument(
        "--include-pending",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include 'In behandeling' rows (default: true)",
    )
    p.add_argument(
        "--skip-grootboek",
        action="store_true",
        help="Do not parse grootboekhistoriek CSVs",
    )
    args = p.parse_args(argv)

    root = books_root()
    inbox = (args.inbox or root / "inbox").expanduser().resolve()
    out = (
        args.out or root / "imports" / "starterslabo" / "transactions.jsonl"
    ).expanduser().resolve()

    if not inbox.is_dir():
        print(f"Inbox not found: {inbox}", file=sys.stderr)
        return 2

    files = discover_files(inbox)
    records: list[dict] = []
    for path in files["sales"]:
        records.extend(normalize_sales(path, args.include_pending))
    for path in files["purchases"]:
        records.extend(normalize_purchases(path, args.include_pending))
    if not args.skip_grootboek:
        for path in files["grootboek"]:
            # Avoid double-counting empty resultaten detail named *grootboek*
            if path.name.startswith("resultatenrekening"):
                gb = normalize_grootboek(path)
                if gb:
                    records.extend(gb)
            elif "grootboek" in path.name:
                records.extend(normalize_grootboek(path))

    # Deduplicate by id (last wins)
    by_id: dict[str, dict] = {}
    for rec in records:
        by_id[rec["id"]] = rec
    ordered = sorted(by_id.values(), key=lambda r: (r["date"], r["kind"], r["id"]))

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for rec in ordered:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    counts: dict[str, int] = {}
    for rec in ordered:
        counts[rec["kind"]] = counts.get(rec["kind"], 0) + 1
    print(f"Wrote {len(ordered)} record(s) → {out}")
    for kind, n in sorted(counts.items()):
        print(f"  {kind}: {n}")
    if not ordered:
        if not files["sales"] and not files["purchases"] and not files["grootboek"]:
            print("warning: no verkopen/aankopen/grootboek CSVs in inbox", file=sys.stderr)
            return 2
        print(
            "warning: CSVs present but no data rows "
            "(grootboekhistoriek is often header-only until portal tree expands)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
