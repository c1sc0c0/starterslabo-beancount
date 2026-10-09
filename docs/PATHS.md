# Path configuration — export & books flat files

Both [`starterslabo-export`](https://github.com/c1sc0c0/starterslabo-export) and [`starterslabo-beancount`](https://github.com/c1sc0c0/starterslabo-beancount) share the same resolver: `scripts/paths.py`.

**Goal:** put Rapport CSVs and Beancount books wherever *you* want (a private data repo, a Nexus vault folder, Nextcloud, …) without hardcoding paths in the public skills.

---

## Quick start (pick one)

### A) Single data root (recommended)

```bash
mkdir -p ~/labo-data/{export,books}
# put main.bean etc. under books/ (see README / reference.md)
cat > ~/labo-data/starterslabo.yaml <<'EOF'
export_dir: export
books_dir: books
EOF

export STARTERSLABO_DATA=~/labo-data
# or: export STARTERSLABO_CONFIG=~/labo-data/starterslabo.yaml
```

### B) Env vars only

```bash
export STARTERSLABO_EXPORT_DIR=~/labo-data/export
export STARTERSLABO_BOOKS=~/labo-data/books
```

### C) CLI (one-off)

```bash
python scripts/sync_rapport.py --output ~/labo-data/export --force
python scripts/sync_books.py --from-export ~/labo-data/export --books-dir ~/labo-data/books
```

### D) Defaults (zero config)

| Skill | Default |
|-------|---------|
| Export | `<skill-root>/rapport-export/` |
| Beancount | First `books/main.bean` found walking cwd / parents |

Fine for a solo clone next to a local `books/` folder.

---

## Resolution order

Highest wins:

1. **CLI** — `--output` / `--from-export` / `--books-dir`
2. **Env** — `STARTERSLABO_EXPORT_DIR`, `STARTERSLABO_BOOKS`
3. **Data root** — `STARTERSLABO_DATA` → `{export,books}` subdirs (or names from YAML)
4. **Config file** — `STARTERSLABO_CONFIG`, else first `starterslabo.yaml` / `.yml` found walking parents of cwd and the skill install; also checks `nexus/starterslabo/starterslabo.yaml` and `data/raw/StartersLabo/starterslabo.yaml` under each parent (Phoenix-style layouts)
5. **Legacy** — export → skill `rapport-export/`; books → walk for `main.bean`

Inspect what will be used:

```bash
python scripts/sync_rapport.py --print-paths
python scripts/sync_books.py --print-paths
```

---

## `starterslabo.yaml`

Copy [`starterslabo.yaml.example`](../starterslabo.yaml.example) next to your data:

```yaml
# Optional absolute/relative base for the keys below.
# If omitted, relative paths resolve against this file's directory.
# data_root: .

export_dir: export
books_dir: books
```

| Key | Meaning |
|-----|---------|
| `data_root` | Optional base directory |
| `export_dir` | Rapport CSV folder (relative to `data_root` or config dir, or absolute) |
| `books_dir` | Beancount root with `main.bean` |

**Never put passwords in this file.** Portal login stays in `STARTERSLABO_EMAIL` / `STARTERSLABO_PASSWORD` or the export skill’s `scripts/.env`.

---

## Example layouts

### Generic (GitHub user)

```text
my-labo-workspace/
  starterslabo.yaml          # export_dir: export, books_dir: books
  export/                    # gitignored CSVs
  books/
    main.bean
    …
  .cursor/skills/
    starterslabo-export/
    starterslabo-beancount/
```

```bash
export STARTERSLABO_DATA=/path/to/my-labo-workspace
```

### Phoenix / Nexus (optional private vault)

Some users keep flat files under a personal vault, e.g.:

```text
…/nexus/starterslabo/
  starterslabo.yaml
  export/
  books/
```

```bash
export STARTERSLABO_CONFIG=/absolute/path/to/nexus/starterslabo/starterslabo.yaml
```

Skills stay cloneable anywhere. Only **data** lives in the vault. This is an integration pattern — **not required** to use the skills.

---

## Privacy

| Put in public skill repos | Keep private |
|---------------------------|--------------|
| `paths.py`, docs, fixtures, templates | `export/*.csv`, `books/inbox/`, `books/generated/`, JSONL |
| `starterslabo.yaml.example` | Real accounting dumps |
| — | Portal `.env` |

---

## Related docs

- [OVERVIEW.md](OVERVIEW.md) — end-to-end pipeline for humans
- Skill `SKILL.md` / `README.md` — agent + install instructions
- `reference.md` — JSONL fields, double-entry rules, CLI
