"""
Query the task graph DB and return the next pending task for aider dispatch.

Usage:
    python query_graph.py <db_path> next          # print next pending task as JSON
    python query_graph.py <db_path> list          # print all pending tasks as JSON
    python query_graph.py <db_path> assign <id>   # mark task in_progress + assigned_to=aider

Returns JSON to stdout for PowerShell to consume.
"""
import json
import sqlite3
import sys
import time
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "usage: query_graph.py <db_path> <command> [args]"}))
        sys.exit(1)

    db_path = sys.argv[1]
    cmd     = sys.argv[2]

    if not Path(db_path).exists():
        print(json.dumps({"error": f"DB not found: {db_path}"}))
        sys.exit(1)

    conn = connect(db_path)

    if cmd == "next":
        row = conn.execute(
            "SELECT id, title, description FROM tasks "
            "WHERE status = 'pending' AND (assigned_to IS NULL OR assigned_to = 'aider') "
            "ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        print(json.dumps(dict(row) if row else {}))

    elif cmd == "list":
        rows = conn.execute(
            "SELECT id, title, status, assigned_to FROM tasks "
            "WHERE status = 'pending' ORDER BY created_at ASC"
        ).fetchall()
        print(json.dumps([dict(r) for r in rows]))

    elif cmd == "assign" and len(sys.argv) >= 4:
        task_id = sys.argv[3]
        now = time.time()
        conn.execute(
            "UPDATE tasks SET status='in_progress', assigned_to='aider', "
            "last_heartbeat=?, updated_at=? WHERE id=?",
            (now, now, task_id)
        )
        conn.commit()
        print(json.dumps({"ok": True, "task_id": task_id}))

    else:
        print(json.dumps({"error": f"unknown command: {cmd}"}))
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()
