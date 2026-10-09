# How Beancount ingest works (human overview)

This skill turns **Rapport CSVs** from [`starterslabo-export`](https://github.com/c1sc0c0/starterslabo-export) into a **[Beancount](https://beancount.github.io/)** plain-text ledger. Agents (and you) can then run `bean-check`, `bean-query`, or Fava.

Unofficial. Not affiliated with Starterslabo or Beancount.

---

## Big picture

```text
mijn.starterslabo.be (Rapport)
        │  starterslabo-export
        ▼
export/*.csv                    ← configurable (docs/PATHS.md)
        │  sync_books.py
        ▼
books/inbox/                    ← copy of CSVs
        │  normalize.py
        ▼
imports/…/transactions.jsonl    ← intermediate IR
        │  emit_beancount.py
        ▼
generated/starterslabo.bean     ← machine-owned (do not hand-edit)
        │  include
        ▼
main.bean  →  bean-check / bean-query / fava
```

Hand-written adjustments go in `manual.bean`. Mapping of portal rekeningen → expense accounts lives in `mapping/accounts.yaml`.

---

## What gets booked (MVP)

| Source | Effect |
|--------|--------|
| `verkopen.csv` | Receivables ↔ Income:Sales |
| `aankopen.csv` | Expenses:{rekening} ↔ Clearing (paid) or Payables (open) |
| `resultatenrekening.csv` | Werkingsbijdrage + Verzekering (non-zero months) ↔ Clearing |
| `grootboekhistoriek*.csv` | Multi-leg by `boekstuknr` when detail rows exist (often empty) |

Each portal row gets a stable `starterslabo_id` in metadata so re-imports skip duplicates already present in `manual.bean`.

Details and posting templates: [`reference.md`](../reference.md).

---

## Where books live

**Configurable** — do not hardcode a single workspace path.

| Mode | Where |
|------|--------|
| Zero config | First `books/main.bean` found from cwd upward |
| Recommended | `books_dir` in `starterslabo.yaml` / `STARTERSLABO_BOOKS` / `STARTERSLABO_DATA` |
| One-off | `--books-dir /path/to/books` |

Export CSVs and books should usually share one **data root** so `sync_books` finds the export automatically. See [PATHS.md](PATHS.md).

**Nexus tip (optional):** some setups keep `export/` + `books/` under a private vault folder with `starterslabo.yaml`. Public GitHub clones keep working with defaults or their own YAML — no Phoenix dependency.

---

## Day-to-day

```bash
# 1) Refresh CSVs (sister skill)
python …/starterslabo-export/scripts/sync_rapport.py --force

# 2) Inspect where books will be written
python scripts/sync_books.py --print-paths

# 3) Import
python scripts/sync_books.py

# 4) Ask the ledger
bean-query /path/to/books/main.bean \
  "SELECT account, sum(position) WHERE year=2026 AND month=9 GROUP BY account"
```

Or open Fava: `fava books/main.bean`.

---

## Safety model

| Layer | Behaviour |
|-------|-----------|
| Regenerated file | `generated/starterslabo.bean` only — never edit by hand |
| Manual entries | `manual.bean` |
| VAT | No invented VAT splits in v1 (`needs_review` instead) |
| Privacy | Fixtures in this repo are synthetic; real inbox/generated stay private |
| Portal | Read-only via export skill |

---

## Docs map

| Audience | File |
|----------|------|
| Agents (short) | [`SKILL.md`](../SKILL.md) |
| Humans (install) | [`README.md`](../README.md) |
| Paths | [`PATHS.md`](PATHS.md) |
| IR / postings / CLI | [`reference.md`](../reference.md) |
| Export side | [export OVERVIEW](https://github.com/c1sc0c0/starterslabo-export/blob/main/docs/OVERVIEW.md) |
