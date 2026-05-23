"""

Purpose:
    Provides a shared task graph that agents use to coordinate work and emit
    liveness heartbeats. Each task node has a status state machine and a
    last_heartbeat timestamp. The orchestrator creates a root task at session
    start, creates child tasks when delegating, and calls record_heartbeat
    periodically. The external watchdog (heartbeat.ps1) polls the SQLite DB
    to detect stalls and clean termination.

    Workspace-scoped: <workspace_root>/.task_graph.db, or global fallback.

Preconditions:
    - fastmcp installed: pip install fastmcp

Failure modes:
    - task_id not found: raises ValueError
    - invalid status: raises ValueError
    - DB write failure: propagates sqlite3.Error
"""

import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

GLOBAL_DB_PATH = Path(r"C:\Users\user\.task_graph.db")
VALID_STATUSES = {"pending", "in_progress", "done", "blocked"}
VALID_EDGE_TYPES = {"parent_of", "depends_on", "assigned_to", "produced_by"}

mcp = FastMCP("task-graph")


def _get_db_path(workspace_root: str | None) -> Path:
    """
    Resolve DB path for a given workspace root.

    Require: workspace_root is None or an absolute path string.
    Guarantee: returns absolute Path; parent directory exists.
    Maintain: project graphs live in {workspace_root}/.task_graph.db.
    """
    if workspace_root is None:
        return GLOBAL_DB_PATH
    p = Path(workspace_root).resolve()
    if not p.is_absolute():
        raise ValueError(f"workspace_root must be absolute, got: {workspace_root!r}")
    return p / ".task_graph.db"


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id             TEXT PRIMARY KEY,
            title          TEXT NOT NULL,
            description    TEXT,
            status         TEXT NOT NULL DEFAULT 'pending',
            assigned_to    TEXT,
            result         TEXT,
            last_heartbeat REAL,
            parent_id      TEXT REFERENCES tasks(id),
            created_at     REAL NOT NULL DEFAULT (unixepoch()),
            updated_at     REAL NOT NULL DEFAULT (unixepoch())
        );
        CREATE TABLE IF NOT EXISTS edges (
            from_id   TEXT NOT NULL REFERENCES tasks(id),
            edge_type TEXT NOT NULL,
            to_id     TEXT NOT NULL REFERENCES tasks(id),
            PRIMARY KEY (from_id, edge_type, to_id)
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_parent   ON tasks(parent_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
    """)
    conn.commit()


@contextmanager
def _db(workspace_root: str | None = None):
    db_path = _get_db_path(workspace_root)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_task(
    title: str,
    description: str = "",
    parent_id: str | None = None,
    workspace_root: str | None = None,
) -> str:
    """
    Create a new task node in the graph.

    Call when decomposing work into subtasks or when a subagent creates a
    bounded work unit. Returns the task_id to use in subsequent tool calls.

    Args:
        title:          Short task name visible in watchdog logs.
        description:    Full task context and acceptance criteria.
        parent_id:      Optional parent task ID. Automatically creates a
                        parent_of edge if provided.
        workspace_root: Git root. Tasks stored in <root>/.task_graph.db.
                        Pass workspace_root on every call.

    Returns:
        "created task_id=<id>"
    """
    task_id = _short_id()
    now = time.time()
    with _db(workspace_root) as conn:
        conn.execute(
            "INSERT INTO tasks (id, title, description, last_heartbeat, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, title, description, now, now, now),
        )
        if parent_id:
            conn.execute(
                "INSERT OR IGNORE INTO edges (from_id, edge_type, to_id) "
                "VALUES (?, 'parent_of', ?)",
                (parent_id, task_id),
            )
        conn.commit()
    return f"created task_id={task_id}"


@mcp.tool()
def assign_task(
    task_id: str,
    agent_name: str,
    workspace_root: str | None = None,
) -> str:
    """
    Assign a task to an agent.

    Sets assigned_to on the task node. Call this after create_task, before
    including the task_id in the subagent's prompt.

    Args:
        task_id:        Task to assign.
        agent_name:     Agent name (e.g. 'coder', 'handyman', 'debugger').
        workspace_root: Git root.

    Returns:
        "assigned task_id=<id> to agent=<name>"

    Raises:
        ValueError: task_id not found.
    """
    now = time.time()
    with _db(workspace_root) as conn:
        row = conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"task_id={task_id!r} not found")
        conn.execute(
            "UPDATE tasks SET assigned_to=?, updated_at=? WHERE id=?",
            (agent_name, now, task_id),
        )
        conn.execute(
            "INSERT OR REPLACE INTO edges (from_id, edge_type, to_id) "
            "VALUES (?, 'assigned_to', ?)",
            (task_id, agent_name),
        )
        conn.commit()
    return f"assigned task_id={task_id} to agent={agent_name}"


@mcp.tool()
def update_status(
    task_id: str,
    status: str,
    workspace_root: str | None = None,
) -> str:
    """
    Update the status of a task.

    Valid transitions: pending -> in_progress -> done | blocked.

    Calling update_status(root_task_id, 'done') is the session termination
    signal. The watchdog exits cleanly when it sees root task status='done'.

    Args:
        task_id:        Task to update.
        status:         One of: pending, in_progress, done, blocked.
        workspace_root: Git root.

    Returns:
        "updated task_id=<id> status=<status>"

    Raises:
        ValueError: task_id not found or invalid status string.
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status {status!r}. Must be one of {sorted(VALID_STATUSES)}")
    now = time.time()
    with _db(workspace_root) as conn:
        row = conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"task_id={task_id!r} not found")
        conn.execute(
            "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
            (status, now, task_id),
        )
        conn.commit()
    return f"updated task_id={task_id} status={status}"


@mcp.tool()
def record_heartbeat(
    task_id: str,
    workspace_root: str | None = None,
) -> str:
    """
    Record a liveness heartbeat for a task.

    The orchestrator MUST call this as the FIRST action on every turn.
    The watchdog declares a stall if last_heartbeat is not updated within
    the stall threshold (default: 300 seconds).

    Subagents should also call this if they are doing long-running work,
    but it is mandatory for the orchestrator's root task on every turn.

    Args:
        task_id:        Task (usually the root task) to heartbeat.
        workspace_root: Git root.

    Returns:
        "heartbeat task_id=<id> at=<epoch>"
    """
    now = time.time()
    with _db(workspace_root) as conn:
        conn.execute(
            "UPDATE tasks SET last_heartbeat=?, updated_at=? WHERE id=?",
            (now, now, task_id),
        )
        conn.commit()
    return f"heartbeat task_id={task_id} at={now:.0f}"


@mcp.tool()
def write_result(
    task_id: str,
    result: str,
    workspace_root: str | None = None,
) -> str:
    """
    Write the result or blocker description for a task.

    Call this BEFORE calling update_status('done') or update_status('blocked').
    Keep result compact (<= 512 chars). This is what the orchestrator reads to
    understand what the subagent produced.

    Args:
        task_id:        Task to write result for.
        result:         Compact result summary or blocker description.
        workspace_root: Git root.

    Returns:
        "wrote result for task_id=<id>"

    Raises:
        ValueError: task_id not found.
    """
    now = time.time()
    with _db(workspace_root) as conn:
        row = conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"task_id={task_id!r} not found")
        conn.execute(
            "UPDATE tasks SET result=?, updated_at=? WHERE id=?",
            (result, now, task_id),
        )
        conn.commit()
    return f"wrote result for task_id={task_id}"


@mcp.tool()
def get_task(
    task_id: str,
    workspace_root: str | None = None,
) -> str:
    """
    Get a task node with its status, result, and edges.

    Args:
        task_id:        Task to retrieve.
        workspace_root: Git root.

    Returns:
        Formatted task details including edges.

    Raises:
        ValueError: task_id not found.
    """
    with _db(workspace_root) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"task_id={task_id!r} not found")
        edges = conn.execute(
            "SELECT edge_type, to_id FROM edges WHERE from_id=?", (task_id,)
        ).fetchall()

    lines = [
        f"task_id     : {row['id']}",
        f"title       : {row['title']}",
        f"status      : {row['status']}",
        f"assigned_to : {row['assigned_to'] or '-'}",
        f"parent_id   : {row['parent_id'] or '-'}",
        f"last_hb     : {row['last_heartbeat'] or '-'}",
        f"result      : {(row['result'] or '-')[:200]}",
    ]
    if edges:
        lines.append("edges:")
        for e in edges:
            lines.append(f"  {e['edge_type']} -> {e['to_id']}")
    return "\n".join(lines)


@mcp.tool()
def list_by_status(
    status: str,
    assigned_to: str | None = None,
    workspace_root: str | None = None,
) -> str:
    """
    List tasks by status, optionally filtered to a specific agent.

    Use to check progress: list_by_status('in_progress') shows active work,
    list_by_status('blocked') reveals blockers before declaring done.

    Args:
        status:         One of: pending, in_progress, done, blocked.
        assigned_to:    Optional agent name filter.
        workspace_root: Git root.

    Returns:
        Formatted list of matching tasks.
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status {status!r}. Must be one of {sorted(VALID_STATUSES)}")
    with _db(workspace_root) as conn:
        if assigned_to:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status=? AND assigned_to=? ORDER BY created_at",
                (status, assigned_to),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status=? ORDER BY created_at",
                (status,),
            ).fetchall()

    if not rows:
        return f"No tasks with status={status!r}"
    lines = [f"Tasks status={status!r}:"]
    for row in rows:
        agent = f" [{row['assigned_to']}]" if row["assigned_to"] else ""
        lines.append(f"  {row['id']}{agent}: {row['title']}")
    return "\n".join(lines)


@mcp.tool()
def get_children(
    task_id: str,
    workspace_root: str | None = None,
) -> str:
    """
    Get all direct child tasks of a given task.

    Use after delegating to subagents to check whether all children are done.
    When every child is status='done', the orchestrator may terminate.

    Args:
        task_id:        Parent task ID (usually the root task).
        workspace_root: Git root.

    Returns:
        Formatted list of child tasks with statuses and result previews.
    """
    with _db(workspace_root) as conn:
        children = conn.execute(
            "SELECT t.* FROM tasks t "
            "JOIN edges e ON e.to_id = t.id AND e.edge_type = 'parent_of' "
            "WHERE e.from_id = ? ORDER BY t.created_at",
            (task_id,),
        ).fetchall()

    if not children:
        return f"No children for task_id={task_id!r}"
    lines = [f"Children of {task_id}:"]
    for row in children:
        agent = f" [{row['assigned_to']}]" if row["assigned_to"] else ""
        result_hint = f" -> {row['result'][:60]}" if row["result"] else ""
        lines.append(f"  {row['id']} {row['status']}{agent}: {row['title']}{result_hint}")
    return "\n".join(lines)


@mcp.tool()
def get_blocked(
    workspace_root: str | None = None,
) -> str:
    """
    Get all blocked tasks in the workspace.

    Call before declaring a session complete to ensure no children are stuck.

    Args:
        workspace_root: Git root.

    Returns:
        Formatted list of blocked tasks with their blocker descriptions.
    """
    with _db(workspace_root) as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status='blocked' ORDER BY updated_at DESC"
        ).fetchall()

    if not rows:
        return "No blocked tasks."
    lines = ["Blocked tasks:"]
    for row in rows:
        agent = f" [{row['assigned_to']}]" if row["assigned_to"] else ""
        blocker = f": {row['result'][:120]}" if row["result"] else ""
        lines.append(f"  {row['id']}{agent}: {row['title']}{blocker}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task graph MCP server")
    parser.add_argument("--port", type=int, default=None, help="Run as HTTP server on this port")
    args = parser.parse_args()

    if args.port:
        mcp.run(transport="streamable-http", host="localhost", port=args.port)
    else:
        mcp.run()
