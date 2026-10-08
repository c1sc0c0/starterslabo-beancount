# Beancount ingest — reference

## Pipeline

```
starterslabo-export/rapport-export/*.csv
        ↓ sync_books (copy)
books/inbox/
        ↓ normalize.py
books/imports/starterslabo/transactions.jsonl
        ↓ emit_beancount.py
books/generated/starterslabo.bean
        ↓ include
books/main.bean  →  bean-check / bean-query / fava
```

## Intermediate JSONL fields

| Field | Notes |
|-------|--------|
| `kind` | `sale` \| `purchase` \| `werkingsbijdrage` \| `verzekering` \| `posting` |
| `id` | `sale:…` / `purchase:…` — sha256 of key fields or `boekstuknr` |
| `date` | `YYYY-MM-DD` |
| `payee` | Klant / Leverancier |
| `amount` | Decimal string, EUR |
| `portal_account` | Six-digit rekening from `Type kosten` |
| `payment_state` | e.g. `betaald` |
| `needs_review` | Pending status or missing account / boekstuknr |

## Double-entry rules (v1)

### Sale

```
Assets:Receivables:Customers    AMOUNT EUR
Income:Sales                   -AMOUNT EUR
```

### Purchase

```
Expenses:{code}:{slug}          AMOUNT EUR
Assets:Clearing:Starterslabo   -AMOUNT EUR   ; if paid via labo
; or
Liabilities:Payables:Suppliers -AMOUNT EUR   ; if open
```

### Resultatenrekening accruals (`werkingsbijdrage`, `verzekering`)

For each period row (`YYYYMM`) and each column with amount &gt; 0, on the **last day of that month**:

```
Expenses:Starterslabo:Werkingsbijdrage   AMOUNT EUR   ; column Werkingsbijdrage
Expenses:Starterslabo:Verzekering        AMOUNT EUR   ; column Verzekering (often one-off)
Assets:Clearing:Starterslabo            -AMOUNT EUR
```

Stable ids: `werkingsbijdrage:YYYYMM`, `verzekering:YYYYMM`. **Zeros are skipped** (so verzekering is not repeated every month). Portal figures are a *raming* → `needs_review: TRUE`.

### Grootboek posting group

One transaction per `boekstuknr`; unbalanced residual → `Equity:Conversions` + `needs_review`.

## Chart skeleton (`accounts.bean`)

Open at least:

- `Assets:Receivables:Customers`
- `Assets:Clearing:Starterslabo`
- `Liabilities:Payables:Suppliers`
- `Income:Sales`
- `Expenses:612125:Software` (and other codes in `accounts.yaml`)
- `Equity:Opening`, `Equity:Conversions`
- `Expenses:Starterslabo:Werkingsbijdrage`

## `main.bean`

```beancount
include "options.bean"
include "accounts.bean"
include "manual.bean"
include "generated/starterslabo.bean"
```

## CLI

```text
normalize.py --inbox DIR --out transactions.jsonl [--include-pending|--no-include-pending]
emit_beancount.py --in JSONL --out generated.bean [--mapping YAML] [--ledger main.bean]
sync_books.py [--from-export DIR] [--no-copy] [--skip-check]
```

Exit `2` = missing paths/credentials-like setup errors. `bean-check` non-zero = ledger invalid.

## Grootboekhistoriek schema (portal)

Live export (header row):

`Rekening`, `Omschrijving`, _(spacer)_, `Factuurdatum`, `Boekstuknr`, `Omschrijving factuur`, `MvH`, `btw-code`

Title row above headers: `Boekingen`.

**Live spike:** data rows are often empty (tree not expanded into the Excel widget). `normalize_grootboek` then returns `[]`; invoice MVP still applies. Fixture `fixtures/grootboekhistoriek.csv` exercises multi-leg emit. See workspace `books/docs/grootboekhistoriek.md` when present.

## BQL snippets

See `queries/*.bql` — expenses by account, sales by payee, receivables, `needs_review` filter.

## Privacy checklist

- [ ] No real CSVs in the skill git tree (only `fixtures/`)
- [ ] Workspace gitignores `books/inbox`, `books/generated/*`, `*.jsonl`
- [ ] No portal passwords in docs
