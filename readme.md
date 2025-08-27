## Overview
Bank ETL + analytics library (src layout) for:
* Parsing PDF statements (checking & credit) into structured transactions
* Idempotent upsert into SQLite
* Pattern based auto‑categorization of uncategorized transactions
* Group + category level rolling 12‑month metrics
* CSV export of enriched rows

All functionality is exposed directly at the top level so you can do:
```py
from bank_etl import ingest_pdfs, categorize_transactions, calculate_moving_averages
```

## Source Layout
```
bank_etl/
  readme.md
  pyproject.toml
  src/
    bank_etl/
      __init__.py        # Re‑exports modules & public functions
      lib/
        utils.py         # Logging, config, hashing, date helpers
        ingest.py        # PDF discovery + extraction orchestration
        pdf_extract.py   # Low-level parsing / field extraction
        etl.py           # DB upsert, querying, CSV writing
        analysis.py      # Rolling 12‑month computations
        categorize.py    # Pattern based categorization logic
  tests/ ...             # Pytest unit tests
```

## Configuration Files
`config_db.json` (ingestion + DB) and `config_category.json` (categories + groups) live outside the installed package in your working project (example paths provided in your separate analysis repo). See schemas below.

## Quick Start
1. Install/build the package (wheel or editable install).
2. Prepare `config_db.json` and `config_category.json`.
3. Drop PDF statements into `INGESTION_PATH`.
4. Ingest, categorize, analyze.

### Ingest
```py
from bank_etl import get_logger, ingest_pdfs
logger = get_logger('bank_etl')
count = ingest_pdfs('config_db.json', logger, move_after=False)
print(count)
```

### Categorize (stand‑alone)
```py
from bank_etl import load_config, categorize_transactions
db_cfg = load_config('config_db.json')
cat_cfg = load_config('config_category.json')
db_path = db_cfg['DB_PATH']
inserted = categorize_transactions(db_path, cat_cfg['categories'])
print(f"Inserted {inserted} category rows")
```

### Analyze Groups
```py
from bank_etl import (
    get_logger, load_config, get_group_categories,
    fetch_group_data, calculate_moving_averages, write_csv
)
logger = get_logger('bank_etl')
db_cfg = load_config('config_db.json')
cat_cfg = load_config('config_category.json')
db_path = db_cfg['DB_PATH']

# Auto‑discover groups: either cat_cfg['groups'] or top-level keys (excluding 'categories')
if 'groups' in cat_cfg:
    group_names = list(cat_cfg['groups'].keys())
else:
    group_names = [k for k in cat_cfg.keys() if k not in ('categories',) and not k.startswith('_')]

for group in group_names:
    categories = get_group_categories(cat_cfg, group)
    rows = fetch_group_data(db_path, categories, logger)
    enriched = calculate_moving_averages(rows, categories, logger)
    write_csv(enriched, f'analysis_{group}.csv', logger)
```

### One‑Shot Pipeline (pseudo)
```py
from bank_etl import ingest_pdfs, categorize_transactions, load_config, get_logger
logger = get_logger()
ingest_pdfs('config_db.json', logger)
cfg = load_config('config_category.json')
db_path = load_config('config_db.json')['DB_PATH']
categorize_transactions(db_path, cfg['categories'])
```

## Top‑Level Imports
All primary functions are exported in `bank_etl.__all__`. You can import either modules:
```py
from bank_etl import utils, ingest
```
or individual functions:
```py
from bank_etl import ingest_pdfs, calculate_moving_averages
```

## Categorization Config (`categories` key)
`categories` maps category name -> list of substring (supports `*` wildcard) patterns. First match wins; unmatched transactions receive `NULL` in the category table (can be reprocessed later with an expanded mapping).

Groups can be specified either under a `groups` object or as additional top‑level keys listing category names (current config example uses top‑level keys like `house`, `car`).

## Configuration: `config_db.json`
| Field | Description |
|-------|-------------|
| DB_PATH | Path to SQLite database file |
| TABLE_NAME | Name of transactions table (e.g. `transactions`) |
| INGESTION_PATH | Directory with incoming statement PDFs |
| PDF_STORAGE | Directory to move processed PDFs (archive) |
| DOC_PATTERNS | Nested object containing regex for credit/checking recognition + filename patterns |

Example (abridged):
```json
{
  "DB_PATH": "./sqlite/bank.db",
  "TABLE_NAME": "transactions",
  "INGESTION_PATH": "../bank/pdf",
  "PDF_STORAGE": "../bank/pdf/processed",
  "DOC_PATTERNS": {
    "CHECKING": {
      "PATTERN": "^\\d{2}/\\d{2}\\s+.*?(-?\\d+\\.\\d{2})$",
      "FILENAME_PATTERN": "STMSSCM"
    },
    "CREDIT": {
      "PATTERN": "^\\d{2}/\\d{2}\\s+.*?(-?\\d+\\.\\d{2})$",
      "FILENAME_PATTERN": "VISASTMT"
    }
  }
}
```

## Configuration: `config_category.json`
Example structure (abridged):
```json
{
  "categories": {
    "water": ["CITY WATER"],
    "groceries": ["KROGER", "ALDI*"],
    "ignore": ["Transfer"]
  },
  "house": ["water"],
  "essentials": ["groceries", "water"]
}
```
Patterns accept `*` wildcards (e.g. `ALDI*`).

## Data Model
Transactions are upserted into a single table (name from `TABLE_NAME`).
```sql
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  transaction_date TEXT,
  post_date TEXT,
  reference_number TEXT,
  description TEXT,
  amount REAL,
  account_type TEXT,
  update_datetime TEXT DEFAULT (datetime('now'))
);
```

Additional category mapping table (optional legacy pattern):
```sql
CREATE TABLE IF NOT EXISTS category (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  transaction_id INTEGER,
  category TEXT,
  FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);
```

## Rolling 12‑Month Logic
For each group:
1. Fetch transactions whose category is in that group's category list.
2. Determine contiguous month range (fills gaps without data).
3. Aggregate per (month, category): total + count.
4. Compute rolling (up to) 12‑month averages per category and for the entire group.
5. Annotate each original row with:
   * `month`
   * `category_12mo_avg`
   * `group_12mo_avg`
   * `category_12mo_count`
   * `group_12mo_count`

## Library Module Summary
| Module | Purpose |
|--------|---------|
| `utils` / `lib.utils` | Logging, config, hashing, date helpers (`parse_month`, `month_iter`) |
| `ingest` / `lib.ingest` | PDF discovery, parsing orchestration (`ingest_pdfs`) |
| `pdf_extract` / `lib.pdf_extract` | Low-level extraction for checking / credit statements |
| `etl` / `lib.etl` | Upsert (`update_sqlite_table`), querying, CSV writing |
| `analysis` / `lib.analysis` | Rolling 12‑month averages (`calculate_moving_averages`) |
| `categorize` / `lib.categorize` | Pattern compilation + assignment (`categorize_transactions`) |

## Extending
* Add new statement patterns: extend `DOC_PATTERNS` and optionally new extraction function in `pdf_extract.py`.
* New analytics: implement helper(s) in `analysis.py` and append derived fields before CSV export.
* Packaging / entry point: expose a console script via `pyproject.toml` if distributing (for example `bank-etl = bank_etl.cli:main`).

## Troubleshooting
| Symptom | Hint |
|---------|------|
| No PDFs processed | Confirm `INGESTION_PATH` and filename patterns match actual files |
| Zero transactions extracted | Review regex in `DOC_PATTERNS` against sample PDF lines |
| Averages all zero | Ensure categories in group match those assigned to transactions |
| Duplicate rows | Verify hashing / upsert logic and uniqueness constraints |

## Next Ideas
* More granular duplicate detection (hash over normalized fields)
* Optional incremental month cache
* PowerShell wrapper parity for Windows native usage
* Bulk recategorization + diff report

Modular, configuration‑driven ETL + analytics toolkit.