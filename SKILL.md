---
name: starterslabo-beancount
description: >-
  Ingest starterslabo-export Rapport CSVs into a Beancount plain-text ledger
  (normalize → JSONL → .bean, bean-check, BQL queries). Use when the user
  mentions Beancount, plain text accounting, Fava, importing verkopen/aankopen
  into a ledger, or syncing Starters Labo books for LLM queries.
---

# Starters Labo — Beancount ingest

Unofficial. Not affiliated with Starterslabo or Beancount.

Turn **Rapport CSVs** from [`starterslabo-export`](https://github.com/c1sc0c0/starterslabo-export) into a **Beancount** ledger via a JSONL intermediate format. Designed so an agent can sync, validate (`bean-check`), and query books safely.

**Never commit** real `books/inbox/`, `generated/*.bean`, or `transactions.jsonl` (customer/supplier PII). This skill ships **synthetic fixtures only**.

**Docs:** [docs/OVERVIEW.md](docs/OVERVIEW.md) (human pipeline) · [docs/PATHS.md](docs/PATHS.md) (where files land) · [reference.md](reference.md) (postings / IR).

## Books + export directories (important)

Do **not** hardcode `books/`. Resolve with `scripts/paths.py` (same module as the export skill):

1. `--books-dir` / `--from-export`
2. `STARTERSLABO_BOOKS` / `STARTERSLABO_EXPORT_DIR`
3. `STARTERSLABO_DATA` / `starterslabo.yaml` (`books_dir`, `export_dir`)
4. Legacy: walk for `books/main.bean`; export → skill `rapport-export/`

```bash
.venv/bin/python scripts/sync_books.py --print-paths
```

Copy [`starterslabo.yaml.example`](starterslabo.yaml.example) beside the user’s data root so export and books share one config. Full rules: [docs/PATHS.md](docs/PATHS.md).

Expected layout under `books_dir`:

```
books/
  main.bean
  accounts.bean
  options.bean
  manual.bean
  mapping/accounts.yaml
  mapping/payees.yaml
  imports/starterslabo/   # optional local copies of scripts
  inbox/                  # gitignored
  generated/              # gitignored
```

Copy mapping templates from `scripts/*.yaml.example` if starting fresh.

## Workflow

```
Progress:
- [ ] 1. Ensure books_dir exists + deps installed; confirm --print-paths
- [ ] 2. Refresh CSVs via starterslabo-export (--force if needed)
- [ ] 3. Run sync_books.py (normalize → emit → bean-check)
- [ ] 4. Answer questions with bean-query / queries/*.bql
- [ ] 5. Do not commit inbox/generated/JSONL or print secrets
```

### Setup

```bash
# Workspace venv (or skill .venv)
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
# Ensure books/ tree exists (see README / docs/OVERVIEW.md)
```

### Sync

```bash
# Portal CSVs (sister skill) — uses shared path config
python /path/to/starterslabo-export/scripts/sync_rapport.py --force

# Into Beancount
.venv/bin/python scripts/sync_books.py
# or: --from-export DIR --books-dir DIR
```

### Queries

```bash
bean-query "$(python scripts/sync_books.py --print-paths | awk -F': ' '/books_dir/{print $2}')/main.bean" \
  "SELECT account, sum(position) WHERE year = 2026 AND month = 9 GROUP BY account"
```

Or use canned BQL under `queries/`.

### Fixtures (no portal)

```bash
.venv/bin/python scripts/sync_books.py \
  --from-export fixtures --books-dir /path/to/books --skip-check
```

## Safety

| Rule | Detail |
|------|--------|
| Portal | Read-only via export skill |
| Ledger | Regenerates `generated/starterslabo.bean`; edits go in `manual.bean` |
| VAT | No invented VAT splits in v1 (`needs_review` instead) |
| Privacy | No real CSVs/beans in this public skill repo |

## Scripts

| File | Role |
|------|------|
| `scripts/sync_books.py` | Copy inbox → normalize → emit → bean-check |
| `scripts/normalize.py` | CSV → JSONL |
| `scripts/emit_beancount.py` | JSONL → `.bean` |
| `scripts/reconcile.py` | Optional resultatenrekening peek |
| `scripts/paths.py` | Shared export/books path resolver |

## Install this skill

```bash
git clone https://github.com/c1sc0c0/starterslabo-beancount.git .cursor/skills/starterslabo-beancount
git clone https://github.com/c1sc0c0/starterslabo-beancount.git ~/.cursor/skills/starterslabo-beancount
git clone https://github.com/c1sc0c0/starterslabo-beancount.git .claude/skills/starterslabo-beancount
git clone https://github.com/c1sc0c0/starterslabo-beancount.git ~/.claude/skills/starterslabo-beancount
```
