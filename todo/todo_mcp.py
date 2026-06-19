"""
todo_mcp.py -- fastmcp sqlite-backed todo server for Copilot CLI.

Purpose:
    Provides todo management tools that Copilot calls autonomously based on
    session context. Todos are scoped to a workspace (project-local .todo/todos.db)
    when workspace_root is supplied; otherwise they land in the global fallback DB.

Preconditions:
    - fastmcp installed: pip install fastmcp

Failure modes:
    - DB write failure: propagates sqlite3.Error
    - Invalid todo_id: raises ValueError
    - Invalid workspace_root: raises ValueError (non-absolute path)
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

GLOBAL_DB_PATH = Path(r"C:\Users\user\todos.db")

mcp = FastMCP("todo")


def _get_db_path(workspace_root: str | None) -> Path:
    """
    Resolve the DB path for a given workspace root.

    Require: workspace_root is None or an absolute path string.
    Guarantee: returns an absolute Path; parent dirs are created if needed.
    Maintain: project todos live in {workspace_root}/.todo/todos.db; global in GLOBAL_DB_PATH.
    """
    if workspace_root is None:
        return GLOBAL_DB_PATH
    p = Path(workspace_root).resolve()
    if not p.is_absolute():
        raise ValueError(f"workspace_root must be an absolute path, got: {workspace_root!r}")
    db_dir = p / ".todo"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "todos.db"


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            task      TEXT    NOT NULL,
            priority  TEXT    NOT NULL DEFAULT 'normal',
            project   TEXT,
            done      INTEGER NOT NULL DEFAULT 0,
            created   TEXT    NOT NULL,
            updated   TEXT    NOT NULL
        )
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


def _scope_label(workspace_root: str | None) -> str:
    if workspace_root is None:
        return "[global]"
    return f"[{Path(workspace_root).name}]"


@mcp.tool()
def add_todo(
    task: str,
    priority: str = "normal",
    project: str = None,
    workspace_root: str | None = None,
) -> str:
    """
    Add a new todo item.

    Call this when a follow-up action is identified during a task that won't
    be completed immediately. Always pass workspace_root as the git root of the
    current repo so the todo is stored project-locally.

    Args:
        task:           Description of the work to be done.
        priority:       'low', 'normal', or 'high'. Default 'normal'.
        project:        Optional label to sub-group todos within the workspace.
        workspace_root: Absolute path to the project root. Todos are stored in
                        {workspace_root}/.todo/todos.db. If omitted, falls back
                        to the global todos.db.

    Returns:
        Confirmation with the assigned todo ID and scope.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db(workspace_root) as conn:
        cur = conn.execute(
            "INSERT INTO todos (task, priority, project, created, updated) VALUES (?,?,?,?,?)",
            (task, priority, project, now, now),
        )
        conn.commit()
        return f"Added todo #{cur.lastrowid} {_scope_label(workspace_root)}: {task}"


@mcp.tool()
def list_todos(
    project: str = None,
    include_done: bool = False,
    workspace_root: str | None = None,
) -> str:
    """
    List todo items.

    Call this automatically at the start of every session to surface pending
    work. Always pass workspace_root as the git root of the current repo to
    see only that project's todos.

    Args:
        project:        Filter by project label. If None, returns all in scope.
        include_done:   Include completed items. Default False.
        workspace_root: Absolute path to the project root. Reads from
                        {workspace_root}/.todo/todos.db. If omitted, reads the
                        global todos.db.

    Returns:
        Formatted list of todos prefixed with scope, grouped by priority.
    """
    with _db(workspace_root) as conn:
        query = "SELECT * FROM todos WHERE 1=1"
        params: list = []
        if not include_done:
            query += " AND done = 0"
        if project:
            query += " AND project = ?"
            params.append(project)
        query += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, id"
        rows = conn.execute(query, params).fetchall()

    if not rows:
        return f"No pending todos {_scope_label(workspace_root)}."

    scope = _scope_label(workspace_root)
    lines = [f"Todos {scope}:"]
    for row in rows:
        status = "x" if row["done"] else " "
        proj = f" [{row['project']}]" if row["project"] else ""
        lines.append(f"[{status}] #{row['id']} ({row['priority']}){proj} {row['task']}")
    return "\n".join(lines)


@mcp.tool()
def complete_todo(todo_id: int, workspace_root: str | None = None) -> str:
    """
    Mark a todo item as complete.

    Args:
        todo_id:        The ID of the todo (from list_todos in the same scope).
        workspace_root: Must match the workspace_root used when the todo was created.

    Returns:
        Confirmation string.

    Raises:
        ValueError: todo_id does not exist in the specified scope.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db(workspace_root) as conn:
        cur = conn.execute(
            "UPDATE todos SET done=1, updated=? WHERE id=?", (now, todo_id)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(
                f"No todo #{todo_id} in scope {_scope_label(workspace_root)}. "
                "Check that workspace_root matches the one used when the todo was added."
            )
        return f"Completed todo #{todo_id} {_scope_label(workspace_root)}"


@mcp.tool()
def update_todo(
    todo_id: int,
    task: str = None,
    priority: str = None,
    project: str = None,
    workspace_root: str | None = None,
) -> str:
    """
    Update the description, priority, or project label of a todo.

    Args:
        todo_id:        The ID of the todo (from list_todos in the same scope).
        task:           New task description. If None, unchanged.
        priority:       New priority ('low', 'normal', 'high'). If None, unchanged.
        project:        New project label. If None, unchanged.
        workspace_root: Must match the workspace_root used when the todo was created.

    Returns:
        Confirmation string.

    Raises:
        ValueError: todo_id does not exist in the specified scope.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db(workspace_root) as conn:
        row = conn.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
        if not row:
            raise ValueError(
                f"No todo #{todo_id} in scope {_scope_label(workspace_root)}. "
                "Check that workspace_root matches the one used when the todo was added."
            )
        new_task     = task     if task     is not None else row["task"]
        new_priority = priority if priority is not None else row["priority"]
        new_project  = project  if project  is not None else row["project"]
        conn.execute(
            "UPDATE todos SET task=?, priority=?, project=?, updated=? WHERE id=?",
            (new_task, new_priority, new_project, now, todo_id),
        )
        conn.commit()
        return f"Updated todo #{todo_id} {_scope_label(workspace_root)}"


@mcp.tool()
def remove_todo(todo_id: int, workspace_root: str | None = None) -> str:
    """
    Permanently delete a todo item.

    Use complete_todo instead if the work was actually done.

    Args:
        todo_id:        The ID of the todo (from list_todos in the same scope).
        workspace_root: Must match the workspace_root used when the todo was created.

    Returns:
        Confirmation string.

    Raises:
        ValueError: todo_id does not exist in the specified scope.
    """
    with _db(workspace_root) as conn:
        cur = conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(
                f"No todo #{todo_id} in scope {_scope_label(workspace_root)}. "
                "Check that workspace_root matches the one used when the todo was added."
            )
        return f"Removed todo #{todo_id} {_scope_label(workspace_root)}"


@mcp.tool()
def get_capabilities() -> str:
    """
    Returns a formatted list of all available tools (local and MCP) that can be called
    in this session. Use this if you are uncertain which tools exist or receive an
    'unavailable tool' error.

    Returns:
        Multiline string: "Available tools:\n- name: description"
    """
    tools = [
        # Core local tools
        ("bash", "Execute a PowerShell command"),
        ("edit", "Edit a file by replacing exact string"),
        ("write", "Write content to a file"),
        ("read", "Read a file or directory"),
        ("grep", "Search file contents using regex"),
        ("glob", "Find files by glob pattern"),
        ("task", "Create a new task for the agent harness"),
        ("subtask", "Run a child worker session"),
        ("skill", "Load a specialized skill"),
        ("webfetch", "Fetch a URL with better extraction"),
        ("websearch_web_search_exa", "Search the web"),
        ("context7_query-docs", "Query documentation for a library"),
        ("context7_resolve-library-id", "Resolve a library ID"),
        ("council_session", "Launch a multi-LLM council session"),
        ("ast_grep_search", "Search code patterns with AST"),
        ("ast_grep_replace", "Replace code patterns with AST"),
        ("grep_app_searchGitHub", "Find code examples from GitHub"),
        ("read_session", "Read a previous session transcript"),
        ("auto_continue", "Toggle auto-continuation for todos"),
        ("question", "Ask the user a question"),
        ("todowrite", "Create/update a structured todo list"),
        # MCP: todo
        ("add_todo", "Add a new todo item"),
        ("list_todos", "List todo items"),
        ("complete_todo", "Mark a todo as complete"),
        ("update_todo", "Update a todo"),
        ("remove_todo", "Remove a todo"),
        # MCP: task-graph
        ("create_task", "Create a new task node"),
        ("assign_task", "Assign a task to an agent"),
        ("update_status", "Update task status"),
        ("record_heartbeat", "Record a liveness heartbeat"),
        ("write_result", "Write task result"),
        ("get_task", "Get a task node details"),
        ("list_by_status", "List tasks by status"),
        ("get_children", "Get child tasks"),
        ("get_blocked", "Get blocked tasks"),
        # MCP: memory-bank
        ("memory-bank_list_memory", "List memory bank files"),
        ("memory-bank_search_memory", "Search memory bank"),
        ("memory-bank_update_memory", "Update memory bank"),
    ]
    return "Available tools:\n" + "\n".join([f"- {name}: {desc}" for name, desc in tools])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Todo MCP server")
    parser.add_argument("--port", type=int, default=None, help="Run as HTTP server on this port")
    args = parser.parse_args()

    if args.port:
        mcp.run(transport="streamable-http", host="localhost", port=args.port)
    else:
        mcp.run()
