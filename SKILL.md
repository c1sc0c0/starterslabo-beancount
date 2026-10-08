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

## Private books location

Expected workspace layout (create once):

```
books/
  main.bean
  accounts.bean
  options.bean
  manual.bean
  mapping/accounts.yaml
  mapping/payees.yaml
  imports/starterslabo/   # or use this skill’s scripts/
  inbox/                  # gitignored
  generated/              # gitignored
```

Override with `STARTERSLABO_BOOKS=/path/to/books`.

Copy mapping templates from `scripts/*.yaml.example` if starting fresh. See [`reference.md`](reference.md) for chart and double-entry rules.

## Workflow

```
Progress:
- [ ] 1. Ensure books/ exists + deps installed
- [ ] 2. Refresh CSVs via starterslabo-export (--force if needed)
- [ ] 3. Run sync_books.py (normalize → emit → bean-check)
- [ ] 4. Answer questions with bean-query / queries/*.bql
- [ ] 5. Do not commit inbox/generated/JSONL or print secrets
```

### Setup

```bash
# Workspace
python3 -m venv .venv
.venv/bin/pip install -r .cursor/skills/starterslabo-beancount/scripts/requirements.txt
# Ensure books/ tree exists (see README)
```

### Sync

```bash
# Portal CSVs
.cursor/skills/starterslabo-export/.venv/bin/python \
  .cursor/skills/starterslabo-export/scripts/sync_rapport.py --force

# Into Beancount
.venv/bin/python .cursor/skills/starterslabo-beancount/scripts/sync_books.py
```

### Queries

```bash
.venv/bin/bean-query books/main.bean < .cursor/skills/starterslabo-beancount/queries/expenses_by_account.bql
```

### Fixtures (no portal)

```bash
STARTERSLABO_BOOKS=/path/to/books \
  .venv/bin/python scripts/sync_books.py --from-export fixtures --skip-check
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

## Install this skill

```bash
git clone https://github.com/c1sc0c0/starterslabo-beancount.git .cursor/skills/starterslabo-beancount
git clone https://github.com/c1sc0c0/starterslabo-beancount.git ~/.cursor/skills/starterslabo-beancount
git clone https://github.com/c1sc0c0/starterslabo-beancount.git .claude/skills/starterslabo-beancount
git clone https://github.com/c1sc0c0/starterslabo-beancount.git ~/.claude/skills/starterslabo-beancount
```
