---
name: lessons-learned
description: >
  Local SQLite3 catalog for agentic ops lessons — failure modes, model quirks,
  routing anti-patterns, config gotchas, and what was learned the hard way.
  Local file only — no server, no MCP.
status: active
last_validated: 2026-06-02
---

# Lessons Learned

A SQLite3 file at the project root for recording recurring failures and
operational knowledge that the agent fleet accumulates over time.
Stdlib `sqlite3` only — no server, no ORM, no MCP.

## Setup

```python
import sqlite3

con = sqlite3.connect("LESSONS_LEARNED.sqlite3")
con.executescript("""
CREATE TABLE IF NOT EXISTS lessons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category        TEXT    NOT NULL,
    symptom         TEXT    NOT NULL,
    root_cause      TEXT    NOT NULL,
    resolution      TEXT    NOT NULL,
    agent_context   TEXT,
    model           TEXT,
    file_scope      TEXT,
    count           INTEGER DEFAULT 1,
    tags            TEXT,
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS tags (
    tag   TEXT PRIMARY KEY,
    count INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS metadata (
    key          TEXT PRIMARY KEY,
    value        TEXT,
    date_updated DATE DEFAULT CURRENT_DATE
);
INSERT OR IGNORE INTO metadata (key, value) VALUES ('version', '1');
INSERT OR IGNORE INTO metadata (key, value) VALUES ('last_migration', '2026-06-02');
""")
con.commit()
con.close()
```

## Record a Lesson

Idempotent — dedup by (category, symptom) fingerprint.

```python
import sqlite3, hashlib

con = sqlite3.connect("LESSONS_LEARNED.sqlite3")

lesson = {
    "category": "routing",
    "symptom": "debugger on qwen3.6-35b spent $1.00/M output on simple trace classification",
    "root_cause": "Over-provisioned model for a classification-only task",
    "resolution": "Swap debugger to step-3.5-flash (lean variant) — 3x cheaper output, identical classification quality",
    "agent_context": "debugger",
    "model": "qwen/qwen3.6-35b-a3b",
    "file_scope": "plugins/oh-my-opencode-slim/oh-my-opencode-slim.json",
    "tags": "cost,model-selection,debugger"
}

fp = hashlib.sha256(f"{lesson['category']}|{lesson['symptom']}".encode()).hexdigest()
existing = con.execute("SELECT id, count FROM lessons WHERE rowid IN (SELECT rowid FROM lessons WHERE category=? AND symptom=?)",
                       (lesson["category"], lesson["symptom"])).fetchone()

if existing:
    con.execute("UPDATE lessons SET count=count+1, updated_at=datetime('now') WHERE id=?", (existing[0],))
else:
    con.execute("""INSERT INTO lessons (category, symptom, root_cause, resolution, agent_context, model, file_scope, tags)
                   VALUES (?,?,?,?,?,?,?,?)""",
               (lesson["category"], lesson["symptom"], lesson["root_cause"], lesson["resolution"],
                lesson["agent_context"], lesson["model"], lesson["file_scope"], lesson["tags"]))
    for t in lesson["tags"].split(","):
        t = t.strip()
        con.execute("INSERT INTO tags (tag, count) VALUES (?, 1) ON CONFLICT(tag) DO UPDATE SET count=count+1", (t,))

con.commit()
con.close()
```

## Key Queries

```sql
-- scan all lessons
SELECT id, category, substr(symptom,1,80), count FROM lessons ORDER BY count DESC, updated_at DESC;

-- find lessons matching a tag
SELECT id, category, symptom, root_cause FROM lessons WHERE tags LIKE '%debugger%';

-- most frequent categories
SELECT category, COUNT(*) as c FROM lessons GROUP BY category ORDER BY c DESC;

-- lessons for a specific agent context
SELECT id, symptom, resolution FROM lessons WHERE agent_context='debugger';

-- recently updated
SELECT id, category, symptom, updated_at FROM lessons ORDER BY updated_at DESC LIMIT 10;
```

## Conventions

- `category` — one of: `routing`, `model-selection`, `prompt-engineering`,
  `config`, `tool-call`, `scope-creep`, `cost`, `anti-pattern`
- `symptom` — what the user or agent observed. Be specific enough to dedup.
- `root_cause` — the structural condition that made the symptom possible
- `resolution` — what fixed it, committed or not
- `agent_context` — which agent was involved (`orchestrator`, `debugger`, etc.)
- `tags` — comma-separated keywords for cross-filtering
- Dedup happens on (category, symptom) hash — if the same lesson fires again,
  `count` is incremented instead of duplicating
- `con.commit()` is never optional

## Role in the Memory Stack

This skill is the **correction-capture surface** that feeds `agentic_kg_memory`'s
overnight synthesis. Each row is a correction in Brain's sense: a logged dead-end
plus its fix.

The `(category, symptom, root_cause, resolution)` tuple maps to an
`event_type: "correction"` Episode:
- `symptom` → what was observed (the failed output)
- `root_cause` → why it failed
- `resolution` → the correction applied
- `agent_context` + `file_scope` → source provenance for the wiki link-back

On each overnight synthesis pass, `agentic_kg_memory` should query this table for
rows updated since the last run and ingest them as correction episodes. High-`count`
rows are strong reinforcement signals — the same dead end recurring means the wiki
has not yet absorbed the lesson.
