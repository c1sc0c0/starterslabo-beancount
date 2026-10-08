#!/usr/bin/env python3
"""Emit Beancount transactions from starterslabo JSONL intermediate records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


META_SAFE = re.compile(r'["\\]')


def books_root() -> Path:
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
    return here.parents[2]


def load_mapping(path: Path) -> dict:
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data


def load_payees(path: Path) -> dict[str, str]:
    if not path.exists() or yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(data.get("aliases") or {})


def escape_meta(value: str) -> str:
    return META_SAFE.sub(lambda m: "\\" + m.group(0), value)


def quote_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def fmt_amount(amount: str) -> str:
    return f"{float(amount):.2f}"


def normalize_payee(payee: str, aliases: dict[str, str]) -> str:
    return aliases.get(payee, payee)


def expense_account(portal_code: str, mapping: dict) -> str:
    accounts = mapping.get("accounts") or {}
    defaults = mapping.get("defaults") or {}
    if portal_code and portal_code in accounts:
        return accounts[portal_code]
    return defaults.get("unknown_expense", "Expenses:610999:Other")


def purchase_is_paid(rec: dict, mapping: dict) -> bool:
    markers = [str(m).lower() for m in (mapping.get("purchase_paid_markers") or [])]
    state = (rec.get("payment_state") or "").strip().lower()
    open_amt = (rec.get("open_amount") or "").strip().lower().replace(",", ".")
    if state in markers:
        return True
    if open_amt in {"", "0", "0.0", "0.00"}:
        # empty open on purchase often means settled via labo
        if state in markers or state == "":
            return True
    return False


def existing_ids_from_ledger(paths: list[Path]) -> set[str]:
    ids: set[str] = set()
    pat = re.compile(r'^\s*starterslabo_id:\s*"([^"]+)"\s*$')
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = pat.match(line)
            if m:
                ids.add(m.group(1))
    return ids


def emit_sale(rec: dict, mapping: dict, aliases: dict[str, str]) -> str:
    defaults = mapping.get("defaults") or {}
    payee = normalize_payee(rec["payee"], aliases)
    amount = fmt_amount(rec["amount"])
    currency = rec.get("currency") or mapping.get("currency") or "EUR"
    recv = defaults.get("receivables", "Assets:Receivables:Customers")
    income = defaults.get("income", "Income:Sales")
    lines = [
        f'{rec["date"]} * {quote_string(payee)} {quote_string(rec["narration"])}',
        f'  starterslabo_id: {quote_string(rec["id"])}',
        f'  status: {quote_string(rec.get("status") or "")}',
    ]
    if rec.get("boekstuknr"):
        lines.append(f'  boekstuknr: {quote_string(rec["boekstuknr"])}')
    if rec.get("needs_review"):
        lines.append("  needs_review: TRUE")
    lines.append(f"  {recv}  {amount} {currency}")
    lines.append(f"  {income}  -{amount} {currency}")
    return "\n".join(lines) + "\n"


def emit_werkingsbijdrage(rec: dict, mapping: dict) -> str:
    """Accrue portal werkingsbijdrage against Starterslabo clearing."""
    defaults = mapping.get("defaults") or {}
    amount = fmt_amount(rec["amount"])
    currency = rec.get("currency") or mapping.get("currency") or "EUR"
    expense = defaults.get(
        "werkingsbijdrage", "Expenses:Starterslabo:Werkingsbijdrage"
    )
    clearing = defaults.get("clearing", "Assets:Clearing:Starterslabo")
    lines = [
        f'{rec["date"]} * {quote_string(rec.get("payee") or "Starterslabo")} '
        f'{quote_string(rec["narration"])}',
        f'  starterslabo_id: {quote_string(rec["id"])}',
        f'  status: {quote_string(rec.get("status") or "resultatenrekening")}',
        '  source: "resultatenrekening"',
    ]
    if rec.get("period"):
        lines.append(f'  period: {quote_string(str(rec["period"]))}')
    if rec.get("needs_review"):
        lines.append("  needs_review: TRUE")
    lines.append(f"  {expense}  {amount} {currency}")
    lines.append(f"  {clearing}  -{amount} {currency}")
    return "\n".join(lines) + "\n"


def emit_purchase(rec: dict, mapping: dict, aliases: dict[str, str]) -> str:
    defaults = mapping.get("defaults") or {}
    payee = normalize_payee(rec["payee"], aliases)
    amount = fmt_amount(rec["amount"])
    currency = rec.get("currency") or mapping.get("currency") or "EUR"
    expense = expense_account(rec.get("portal_account") or "", mapping)
    paid = purchase_is_paid(rec, mapping)
    credit = (
        defaults.get("clearing", "Assets:Clearing:Starterslabo")
        if paid
        else defaults.get("payables", "Liabilities:Payables:Suppliers")
    )
    lines = [
        f'{rec["date"]} * {quote_string(payee)} {quote_string(rec["narration"])}',
        f'  starterslabo_id: {quote_string(rec["id"])}',
        f'  status: {quote_string(rec.get("status") or "")}',
    ]
    if rec.get("portal_account"):
        lines.append(f'  portal_account: {quote_string(rec["portal_account"])}')
    if rec.get("boekstuknr"):
        lines.append(f'  boekstuknr: {quote_string(rec["boekstuknr"])}')
    if rec.get("needs_review"):
        lines.append("  needs_review: TRUE")
    lines.append(f"  {expense}  {amount} {currency}")
    lines.append(f"  {credit}  -{amount} {currency}")
    return "\n".join(lines) + "\n"


def emit_posting_group(
    boekstuknr: str,
    lines_rec: list[dict],
    mapping: dict,
) -> str:
    """Emit one multi-leg transaction from grootboek posting lines.

    If legs do not balance, pad to Equity:Conversions and flag needs_review.
    """
    defaults = mapping.get("defaults") or {}
    currency = mapping.get("currency") or "EUR"
    date_s = sorted({r["date"] for r in lines_rec if r.get("date")})[0]
    narration = f"Grootboek {boekstuknr}".strip()
    group_id = f"posting-group:{boekstuknr or lines_rec[0]['id']}"
    postings: list[tuple[str, float]] = []
    for r in lines_rec:
        code = r.get("portal_account") or ""
        # Heuristic: 6xxxxx / 61xxxx expenses; 7xxxxx income; else clearing
        acct = expense_account(code, mapping) if code.startswith("6") else None
        if code.startswith("7"):
            acct = defaults.get("income", "Income:Sales")
        if not acct:
            acct = defaults.get("clearing", "Assets:Clearing:Starterslabo")
        postings.append((acct, float(r["amount"])))

    total = sum(a for _, a in postings)
    out = [
        f"{date_s} * {quote_string('Starterslabo')} {quote_string(narration)}",
        f'  starterslabo_id: {quote_string(group_id)}',
        f'  boekstuknr: {quote_string(boekstuknr)}',
        "  needs_review: TRUE",
        '  source: "grootboekhistoriek"',
    ]
    for acct, amt in postings:
        sign = "" if amt >= 0 else "-"
        out.append(f"  {acct}  {sign}{abs(amt):.2f} {currency}")
    if abs(total) > 0.0001:
        # Balancing stub — review required
        bal = -total
        sign = "" if bal >= 0 else "-"
        out.append(
            f"  Equity:Conversions  {sign}{abs(bal):.2f} {currency}"
        )
    return "\n".join(out) + "\n"


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Emit Beancount from starterslabo JSONL")
    p.add_argument(
        "--in",
        dest="infile",
        type=Path,
        default=None,
        help="JSONL input (default: books/imports/starterslabo/transactions.jsonl)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output .bean (default: books/generated/starterslabo.bean)",
    )
    p.add_argument(
        "--mapping",
        type=Path,
        default=None,
        help="accounts.yaml path",
    )
    p.add_argument(
        "--payees",
        type=Path,
        default=None,
        help="payees.yaml path",
    )
    p.add_argument(
        "--ledger",
        type=Path,
        default=None,
        help="Optional main.bean — skip IDs already present outside --out",
    )
    p.add_argument(
        "--skip-postings",
        action="store_true",
        help="Do not emit grootboek posting groups",
    )
    args = p.parse_args(argv)

    root = books_root()
    infile = (
        args.infile or root / "imports" / "starterslabo" / "transactions.jsonl"
    ).expanduser().resolve()
    out = (args.out or root / "generated" / "starterslabo.bean").expanduser().resolve()
    mapping_path = (args.mapping or root / "mapping" / "accounts.yaml").resolve()
    payees_path = (args.payees or root / "mapping" / "payees.yaml").resolve()

    if not infile.exists():
        print(f"JSONL not found: {infile}", file=sys.stderr)
        return 2

    mapping = load_mapping(mapping_path)
    aliases = load_payees(payees_path)
    records = read_jsonl(infile)

    skip_ids: set[str] = set()
    if args.ledger:
        ledger = args.ledger.expanduser().resolve()
        # Collect IDs from manual.bean and any non-generated includes
        candidates = [
            root / "manual.bean",
            root / "accounts.bean",
        ]
        if ledger.exists():
            candidates.append(ledger)
        skip_ids = existing_ids_from_ledger(candidates)
        # Do not skip IDs that only lived in previous generated file — we regenerate it.

    sales = [r for r in records if r.get("kind") == "sale"]
    purchases = [r for r in records if r.get("kind") == "purchase"]
    contributions = [r for r in records if r.get("kind") == "werkingsbijdrage"]
    postings = [r for r in records if r.get("kind") == "posting"]

    chunks: list[str] = [
        "; Auto-generated from starterslabo-export CSVs via emit_beancount.py",
        f"; Generated: {date.today().isoformat()}",
        "; Do not edit by hand — put adjustments in manual.bean",
        "",
    ]

    emitted = 0
    skipped = 0

    for rec in sorted(sales, key=lambda r: (r["date"], r["id"])):
        if rec["id"] in skip_ids:
            skipped += 1
            continue
        chunks.append(emit_sale(rec, mapping, aliases))
        emitted += 1

    for rec in sorted(purchases, key=lambda r: (r["date"], r["id"])):
        if rec["id"] in skip_ids:
            skipped += 1
            continue
        chunks.append(emit_purchase(rec, mapping, aliases))
        emitted += 1

    for rec in sorted(contributions, key=lambda r: (r["date"], r["id"])):
        if rec["id"] in skip_ids:
            skipped += 1
            continue
        chunks.append(emit_werkingsbijdrage(rec, mapping))
        emitted += 1

    if not args.skip_postings and postings:
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in postings:
            key = r.get("boekstuknr") or r["id"]
            groups[key].append(r)
        for key in sorted(groups):
            group_id = f"posting-group:{key}"
            if group_id in skip_ids:
                skipped += 1
                continue
            chunks.append(emit_posting_group(key, groups[key], mapping))
            emitted += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {emitted} transaction(s) → {out}" + (f" (skipped {skipped} existing)" if skipped else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
