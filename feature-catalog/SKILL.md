---
name: feature-catalog
description: >
  Project-local SQLite3 feature catalog. Use when registering, querying, or
  updating this project's implemented features, file mappings, and architectural
  decisions. Local file only — no server, no MCP.
status: active
last_validated: 2026-04-28
---

# Feature Catalog

A SQLite3 file at the project root replaces flat markdown with a queryable
knowledge base. Stdlib `sqlite3` only — no server, no ORM, no MCP.

## Setup

```python
import sqlite3

con = sqlite3.connect("FEATURE_CATALOG.sqlite3")
con.executescript("""
CREATE TABLE IF NOT EXISTS features (
    feature_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name      TEXT    NOT NULL,
    short_description TEXT    NOT NULL,
    long_description  TEXT,
    category          TEXT,
    status            TEXT    DEFAULT 'implemented',
    priority          INTEGER DEFAULT 5,
    date_added        DATE    DEFAULT CURRENT_DATE,
    date_updated      DATE    DEFAULT CURRENT_DATE,
    notes             TEXT
);
CREATE TABLE IF NOT EXISTS files (
    file_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path       TEXT    NOT NULL UNIQUE,
    file_type       TEXT,
    execution_order INTEGER,
    date_added      DATE    DEFAULT CURRENT_DATE
);
CREATE TABLE IF NOT EXISTS feature_files (
    feature_id INTEGER NOT NULL REFERENCES features(feature_id),
    file_id    INTEGER NOT NULL REFERENCES files(file_id),
    role       TEXT,
    PRIMARY KEY (feature_id, file_id)
);
CREATE TABLE IF NOT EXISTS functions (
    function_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    function_name TEXT    NOT NULL,
    file_id       INTEGER NOT NULL REFERENCES files(file_id),
    signature     TEXT,
    description   TEXT,
    returns       TEXT
);
CREATE TABLE IF NOT EXISTS architectural_decisions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    decision           TEXT    NOT NULL,
    rationale          TEXT,
    before_state       TEXT,
    after_state        TEXT,
    measured_impact    REAL,
    decision_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS metadata (
    key          TEXT PRIMARY KEY,
    value        TEXT,
    date_updated DATE DEFAULT CURRENT_DATE
);
""")
con.commit()
con.close()
```

## Upsert a Feature

Idempotent — safe to re-run as a standalone script.

```python
import sqlite3
from datetime import date

con = sqlite3.connect("FEATURE_CATALOG.sqlite3")
TODAY = date.today().isoformat()
FID   = 42  # permanent; never reuse a retired ID

if con.execute("SELECT 1 FROM features WHERE feature_id=?", (FID,)).fetchone():
    con.execute("""UPDATE features SET feature_name=?, short_description=?,
        long_description=?, category=?, notes=?, date_updated=? WHERE feature_id=?""",
        ("My Feature", "One sentence from user POV.",
         "## Purpose\n...\n## How It Works\n...", "optimization",
         "Added YYYY-MM-DD.", TODAY, FID))
else:
    con.execute("""INSERT INTO features
        (feature_id, feature_name, short_description, long_description, category, notes)
        VALUES (?,?,?,?,?,?)""",
        (FID, "My Feature", "One sentence from user POV.",
         "## Purpose\n...\n## How It Works\n...", "optimization", "Added YYYY-MM-DD."))

# map files
def get_or_create_file(path, ftype=None):
    r = con.execute("SELECT file_id FROM files WHERE file_path=?", (path,)).fetchone()
    if r: return r[0]
    con.execute("INSERT INTO files (file_path, file_type) VALUES (?,?)", (path, ftype))
    return con.execute("SELECT last_insert_rowid()").fetchone()[0]

for path, role in [("src/module.py", "primary"), ("data/out.db", "output")]:
    fid = get_or_create_file(path)
    con.execute("INSERT OR IGNORE INTO feature_files VALUES (?,?,?)", (FID, fid, role))

con.commit()
con.close()
```

## Key Queries

```sql
-- scan all features
SELECT feature_id, feature_name, category, status FROM features ORDER BY feature_id DESC;

-- what files does a feature touch?
SELECT f.file_path, ff.role FROM feature_files ff
JOIN files f ON ff.file_id=f.file_id WHERE ff.feature_id=42;

-- what features touch a file?
SELECT feat.feature_id, feat.feature_name FROM feature_files ff
JOIN features feat ON ff.feature_id=feat.feature_id
JOIN files f ON ff.file_id=f.file_id WHERE f.file_path LIKE '%cli.py%';
```

## Conventions

- `short_description` — one sentence, agent-scannable
- `long_description` — markdown: Purpose / How It Works / Parameters / Why this approach
- `notes` — append-only: dates, cross-refs (`see feature_id=N`), gotchas
- `priority` — 1-10; 9+ critical, 5 normal
- `status` — `implemented` | `planned` | `deprecated` | `experimental`
- Feature IDs are permanent. Never reuse a retired ID.
- `con.commit()` is never optional.
<!-- consolidation:see-also:start -->
## See Also
[[memory-bank]]  [[mcp-tool-registry]]  [[todo]]
<!-- consolidation:see-also:end -->
