#!/usr/bin/env python3
"""End-to-end: copy inbox CSVs (optional) → normalize → emit → bean-check."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from normalize import books_root, main as normalize_main  # noqa: E402
from emit_beancount import main as emit_main  # noqa: E402


def default_export_dir(books: Path) -> Path:
    root = books.parent
    candidates = [
        root / ".cursor" / "skills" / "starterslabo-export" / "rapport-export",
        root / ".cursor" / "skills" / "starterslabo-rapport" / "rapport-export",
        _SCRIPTS.parent / "fixtures",
    ]
    for c in candidates:
        if c.is_dir() and any(c.glob("*.csv")):
            return c
    return candidates[0]


def bean_check_bin() -> list[str]:
    for path in (
        books_root().parent / ".venv" / "bin" / "bean-check",
        _SCRIPTS.parent / ".venv" / "bin" / "bean-check",
        Path(shutil.which("bean-check") or ""),
    ):
        if path and path.exists():
            return [str(path)]
    return ["bean-check"]


def run_bean_check(ledger: Path) -> int:
    cmd = bean_check_bin() + [str(ledger)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print(
            "bean-check not found — pip install -r scripts/requirements.txt",
            file=sys.stderr,
        )
        return 2
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode == 0:
        print(f"bean-check OK: {ledger}")
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sync Starterslabo CSVs into Beancount")
    p.add_argument("--from-export", type=Path, default=None)
    p.add_argument("--no-copy", action="store_true")
    p.add_argument("--skip-check", action="store_true")
    p.add_argument(
        "--include-pending",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = p.parse_args(argv)

    root = books_root()
    if not (root / "main.bean").exists():
        print(
            f"No books/main.bean at {root}. Copy templates/ from this skill "
            "or set STARTERSLABO_BOOKS.",
            file=sys.stderr,
        )
        return 2

    inbox = root / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (root / "generated").mkdir(parents=True, exist_ok=True)

    if not args.no_copy:
        src = (args.from_export or default_export_dir(root)).expanduser().resolve()
        if not src.is_dir():
            print(f"Export dir not found: {src}", file=sys.stderr)
            return 2
        copied = 0
        for path in src.glob("*.csv"):
            shutil.copy2(path, inbox / path.name)
            copied += 1
        if (src / "manifest.json").exists():
            shutil.copy2(src / "manifest.json", inbox / "manifest.json")
        print(f"Copied {copied} CSV(s) from {src} → {inbox}")

    rc = normalize_main(
        [
            "--inbox",
            str(inbox),
            "--out",
            str(root / "imports" / "starterslabo" / "transactions.jsonl"),
            "--include-pending" if args.include_pending else "--no-include-pending",
        ]
    )
    if rc != 0:
        return rc

    mapping = root / "mapping" / "accounts.yaml"
    payees = root / "mapping" / "payees.yaml"
    emit_args = [
        "--in",
        str(root / "imports" / "starterslabo" / "transactions.jsonl"),
        "--out",
        str(root / "generated" / "starterslabo.bean"),
        "--ledger",
        str(root / "main.bean"),
    ]
    if mapping.exists():
        emit_args.extend(["--mapping", str(mapping)])
    if payees.exists():
        emit_args.extend(["--payees", str(payees)])

    rc = emit_main(emit_args)
    if rc != 0:
        return rc

    if args.skip_check:
        return 0
    return run_bean_check(root / "main.bean")


if __name__ == "__main__":
    raise SystemExit(main())
