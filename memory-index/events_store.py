#!/usr/bin/env python3
"""Session-event store: the capture half of the memory loop.

Thesis
------
Memory that depends on the model remembering to write it does not get written.
The `SessionStart` read layer (`membank.py`) already proved the point for reads:
a prose instruction is discretionary, a harness hook is not. This module owns the
write side of the same trade for raw events -- every lifecycle event lands in
SQLite whether or not anything is later judged worth remembering. Judgment is a
separate, offline concern (`dream.py`); conflating the two is what makes capture
lossy, because a capture path that must decide is a capture path that can decline.

Adapted from neo4j-labs/meta-knowledge-graph `hooks/log_event.py`. Its graph is a
per-session linked list of typed event nodes -- a relational schema in graph
clothing -- so it ports to SQLite by replacing `[:NEXT]` with `prev_event_id`
plus a monotonic `seq`. We keep its mechanisms (deterministic event ids, payload
truncation, the extraction-subprocess guard) and drop its store.

Necessary conditions
--------------------
- Capture must never be able to fail a session. Every public function here is
  called from a hook, so the caller's contract is "swallow everything, exit 0".
  This is the documented exception to the fail-fast rule: the alternative to a
  dropped event is a dead session, and a dropped event is strictly cheaper.
- Event identity must be deterministic. Two hook configurations can be active at
  once (a user `settings.json` and a plugin), and Claude Code hands both the
  identical stdin payload. Hashing the payload collapses the double-fire to one
  row instead of double-counting the same turn as evidence.
- The store must be resumable. `sessions.last_dreamed_at` is the watermark that
  makes the distillation pass idempotent and killable mid-run.

Design decisions
----------------
- Transcripts are NOT stored. MKG stores a dialog-filtered transcript snapshot on
  every event; that multiplies the same conversation across every row in the
  session and is the single largest privacy surface in the design. Prompts and
  assistant messages already carry the dialog, once each.
- `project_slug` is the git-root basename, matching the `workspace_root`
  convention the todo tools use, so event scope and todo scope agree.
- WAL journal mode: hooks fire concurrently (a `PostToolUse` can overlap the next
  `PreToolUse`), and the default rollback journal serialises them into lock
  contention.

Invariants
----------
- `(session_id, seq)` is unique and gap-free per session.
- `prev_event_id` chains every event in a session back to its first, whose
  `prev_event_id` is NULL.
- `event_id` is unique globally; re-inserting a known id is a silent no-op.

Failure modes
-------------
- DB unwritable (locked, read-only, missing parent) -> `log_event` returns False.
  Never raises to the hook.
- Payload not JSON / empty -> nothing written, returns False.
- Clock skew across sessions: `timestamp` is UTC ISO-8601 from this process, so
  ordering within a session relies on `seq`, not on time.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path

# MKG's cap. Long enough for a real tool result to stay diagnostic, short enough
# that one `Read` of a large file cannot dominate the store.
MAX_PAYLOAD_CHARS = 4000

# Lifecycle events that describe the session, not work inside a project.
PROJECT_NEUTRAL_EVENTS = frozenset({"SessionStart", "SessionEnd"})

# Claude Code fires this instead of PostToolUse when a tool call fails. Folding it
# into PostToolUse keeps "what happened on this tool" answerable with one query.
TOOL_FAILURE_EVENT = "PostToolUseFailure"

DEFAULT_DB_NAME = "events.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    project_slug    TEXT,
    cwd             TEXT,
    started_at      TEXT,
    ended_at        TEXT,
    last_dreamed_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    event_id               TEXT PRIMARY KEY,
    session_id             TEXT NOT NULL,
    prev_event_id          TEXT,
    seq                    INTEGER NOT NULL,
    event_name             TEXT NOT NULL,
    timestamp              TEXT NOT NULL,
    project_slug           TEXT,
    tool_name              TEXT,
    tool_input             TEXT,
    tool_response          TEXT,
    tool_error             TEXT,
    prompt                 TEXT,
    last_assistant_message TEXT,
    model                  TEXT,
    source                 TEXT,
    UNIQUE (session_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_events_session   ON events (session_id, seq);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
CREATE INDEX IF NOT EXISTS idx_events_project   ON events (project_slug, timestamp);
"""


def in_extraction_subprocess() -> bool:
    """True inside the `claude -p` the dream pass spawns to distil memories.

    That nested session loads this same hook config, so its own events would be
    captured and then distilled on the next pass -- the model's summary of a
    session becomes evidence about that session, and the loop compounds. MKG hit
    the same recursion and guards it the same way.
    """
    return bool(os.environ.get("MEM_IN_EXTRACTION"))


def default_db_path() -> Path:
    return Path(os.path.expanduser("~")) / "memory-bank" / DEFAULT_DB_NAME


def project_slug(cwd: str | None) -> str:
    """Git-root basename for `cwd`, or 'global' outside a repo.

    Mirrors the `workspace_root` rule the todo tools use, so a memory's scope and
    a todo's scope name the same thing.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd or None,
        )
    except (OSError, subprocess.SubprocessError):
        return "global"
    root = out.stdout.strip()
    if out.returncode != 0 or not root:
        return "global"
    return Path(root).name or "global"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open the store, creating schema on first use.

    Require   - parent directory exists (it is `~/memory-bank`, created by the
                memory-bank bootstrap).
    Guarantee - returns a connection whose schema is current.
    """
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def _truncate(value) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) > MAX_PAYLOAD_CHARS:
        dropped = len(text) - MAX_PAYLOAD_CHARS
        text = text[:MAX_PAYLOAD_CHARS] + f"...[truncated {dropped} chars]"
    return text


def normalize_tool_failure(data: dict) -> dict:
    """Fold Claude Code's `PostToolUseFailure` into the `PostToolUse` shape.

    Done before hashing so the event id stays deterministic regardless of which
    hook name delivered it.
    """
    if data.get("hook_event_name") != TOOL_FAILURE_EVENT:
        return data
    folded = dict(data)
    folded["hook_event_name"] = "PostToolUse"
    folded["tool_error"] = (
        data.get("tool_error")
        or data.get("error")
        or data.get("tool_response")
        or "tool call failed"
    )
    folded["source_event"] = TOOL_FAILURE_EVENT
    return folded


def event_id_for(data: dict, session_id: str, event_name: str) -> str:
    """Deterministic id: same payload delivered twice yields one row."""
    sig = sha1(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    return f"{session_id}:{event_name}:{sig}"


def log_event(data: dict, db_path: Path | None = None) -> bool:
    """Append one lifecycle event to its session's chain.

    Require   - `data` is a decoded hook payload; may be missing any key.
    Guarantee - on success exactly one `events` row exists for this payload and
                the session row is upserted. Returns False on any storage
                failure without raising.
    Maintain  - `seq` is contiguous per session; `prev_event_id` points at the
                previous event or NULL for the first.
    Assert    - a duplicate `event_id` is a no-op, not an error.
    """
    if in_extraction_subprocess():
        return False

    data = normalize_tool_failure(data)
    session_id = str(data.get("session_id") or "unknown")
    event_name = str(data.get("hook_event_name") or "unknown")
    timestamp = datetime.now(timezone.utc).isoformat()
    cwd = data.get("cwd")
    slug = project_slug(cwd)
    event_id = event_id_for(data, session_id, event_name)

    try:
        conn = connect(db_path)
    except Exception:
        # Broader than sqlite3.Error on purpose: mkdir on a bad path raises
        # OSError, and every storage failure here has the same disposition --
        # drop the event, never surface it to the session.
        return False

    try:
        with conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, project_slug, cwd, started_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    project_slug = COALESCE(excluded.project_slug, sessions.project_slug),
                    cwd          = COALESCE(excluded.cwd, sessions.cwd)
                """,
                (session_id, slug, cwd, timestamp),
            )
            if event_name == "SessionEnd":
                conn.execute(
                    "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
                    (timestamp, session_id),
                )

            prev = conn.execute(
                "SELECT event_id, seq FROM events WHERE session_id = ? "
                "ORDER BY seq DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            prev_id = prev["event_id"] if prev else None
            seq = (prev["seq"] + 1) if prev else 0

            conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id, session_id, prev_event_id, seq, event_name, timestamp,
                    project_slug, tool_name, tool_input, tool_response, tool_error,
                    prompt, last_assistant_message, model, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    session_id,
                    prev_id,
                    seq,
                    event_name,
                    timestamp,
                    None if event_name in PROJECT_NEUTRAL_EVENTS else slug,
                    data.get("tool_name"),
                    _truncate(data.get("tool_input")),
                    _truncate(data.get("tool_response")),
                    _truncate(data.get("tool_error")),
                    _truncate(data.get("prompt")),
                    _truncate(data.get("last_assistant_message")),
                    data.get("model"),
                    data.get("source"),
                ),
            )
    except Exception:
        return False
    finally:
        conn.close()
    return True


def undreamed_sessions(conn: sqlite3.Connection, since: str | None = None,
                       session_id: str | None = None) -> list[sqlite3.Row]:
    """Sessions with events newer than their watermark.

    `since` is an ISO-8601 lower bound on event timestamp; `session_id` pins one
    session and ignores the watermark, which is what `--session` needs for a
    re-run after a bad extraction.
    """
    if session_id:
        return conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchall()
    sql = """
        SELECT s.* FROM sessions s
        JOIN events e ON e.session_id = s.session_id
        WHERE (s.last_dreamed_at IS NULL OR e.timestamp > s.last_dreamed_at)
    """
    params: list = []
    if since:
        sql += " AND e.timestamp >= ?"
        params.append(since)
    sql += " GROUP BY s.session_id ORDER BY MAX(e.timestamp)"
    return conn.execute(sql, params).fetchall()


def session_events(conn: sqlite3.Connection, session_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM events WHERE session_id = ? ORDER BY seq", (session_id,)
    ).fetchall()


def mark_dreamed(conn: sqlite3.Connection, session_id: str) -> None:
    """Advance the watermark. Called per session, immediately after its write --
    the checkpoint that makes killing a long run free."""
    with conn:
        conn.execute(
            "UPDATE sessions SET last_dreamed_at = ? WHERE session_id = ?",
            (datetime.now(timezone.utc).isoformat(), session_id),
        )
