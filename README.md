# Starters Labo — Beancount ingest

Unofficial [Cursor](https://cursor.com) / [Claude Code](https://code.claude.com) skill that ingests **Rapport CSVs** from [`starterslabo-export`](https://github.com/c1sc0c0/starterslabo-export) into a **[Beancount](https://beancount.github.io/)** plain-text ledger.

Pipeline: **CSV → JSONL → `.bean` → `bean-check`**, with canned BQL queries for LLM agents.

Not affiliated with Starterslabo. **Credentials and real accounting dumps are never stored in this repo** (fixtures are synthetic).

## Install

Clone **as the skill folder** (`SKILL.md` at the root):

```bash
git clone https://github.com/c1sc0c0/starterslabo-beancount.git .cursor/skills/starterslabo-beancount
git clone https://github.com/c1sc0c0/starterslabo-beancount.git ~/.cursor/skills/starterslabo-beancount
git clone https://github.com/c1sc0c0/starterslabo-beancount.git .claude/skills/starterslabo-beancount
git clone https://github.com/c1sc0c0/starterslabo-beancount.git ~/.claude/skills/starterslabo-beancount
```

Start a new agent chat so the skill is picked up.

## Private books/ (once per workspace)

Create a `books/` directory beside your project (gitignored for inbox/generated):

```bash
mkdir -p books/{mapping,imports/starterslabo,generated,inbox,queries}
cp .cursor/skills/starterslabo-beancount/scripts/accounts.yaml.example books/mapping/accounts.yaml
cp .cursor/skills/starterslabo-beancount/scripts/payees.yaml.example books/mapping/payees.yaml
cp .cursor/skills/starterslabo-beancount/queries/*.bql books/queries/
```

Add `main.bean` / `accounts.bean` / `options.bean` / `manual.bean` as in [`reference.md`](reference.md) (or copy from a StartersLabo workspace that already has them).

```bash
python3 -m venv .venv
.venv/bin/pip install -r .cursor/skills/starterslabo-beancount/scripts/requirements.txt
```

## Use

Tell the agent:

> Sync my Starters Labo Rapport export into Beancount and show expenses by account.

Or manually:

```bash
# 1) Portal → CSV (sister skill)
.cursor/skills/starterslabo-export/.venv/bin/python \
  .cursor/skills/starterslabo-export/scripts/sync_rapport.py --force

# 2) CSV → Beancount
.venv/bin/python .cursor/skills/starterslabo-beancount/scripts/sync_books.py

# 3) Query
.venv/bin/bean-query books/main.bean < .cursor/skills/starterslabo-beancount/queries/expenses_by_account.bql
```

Optional UI: `.venv/bin/fava books/main.bean`

### Fixture dry-run (no portal)

```bash
.venv/bin/python .cursor/skills/starterslabo-beancount/scripts/sync_books.py \
  --from-export .cursor/skills/starterslabo-beancount/fixtures
```

## What gets booked (MVP)

| CSV | Beancount effect |
|-----|------------------|
| `verkopen.csv` | Dr Receivables / Cr Income:Sales |
| `aankopen.csv` | Dr Expenses:{rekening} / Cr Clearing (if betaald) or Payables |
| `grootboekhistoriek*.csv` | Multi-leg groups by `boekstuknr` when rows exist (often empty from portal) |

Stable metadata: `starterslabo_id`. Regenerated file: `books/generated/starterslabo.bean`. Hand edits: `books/manual.bean`.

## Privacy

| Path | In this repo? |
|------|----------------|
| `fixtures/*.csv` | Yes — synthetic only |
| Real `rapport-export/` / `books/inbox/` | **No** (gitignore in your workspace) |
| Real `generated/*.bean` | **No** |

Before push: `git status` must not list real customer names or portal passwords.

## Related

- [starterslabo-export](https://github.com/c1sc0c0/starterslabo-export) — Rapport → CSV  
- [starterlabo-invoices](https://github.com/c1sc0c0/starterlabo-invoices) — verkoopfactuur drafts  
- [starterslabo-skills](https://github.com/c1sc0c0/starterslabo-skills) — skill index  

## License

MIT for this skill’s code and instructions. Starterslabo’s portal and Beancount remain their respective owners.
