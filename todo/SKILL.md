---
name: todo
description: >
  SQLite-backed todo MCP setup and usage protocol. Use when installing or operating
  a persistent todo tool for Copilot CLI, especially when the user says `todo setup`
  or asks to capture, list, update, complete, or remove deferred work.
status: active
last_validated: 2026-04-28
---

# Todo MCP Skill

## Scope Boundary

This skill is for **persistent task tracking**.

It owns:
- sqlite-backed todo persistence
- MCP tool setup for todos
- trigger-to-tool mapping for deferred work
- explicit file/config paths for installation

It does **not** own:
- project memory-bank markdown files
- semantic KG retrieval
- triplet clustering or throughline ranking

Those belong to `memory-bank` and `agentic_kg_memory`.

This skill is the canonical setup surface. `todo\SKILL.md` should be sufficient
for an agent to install and operate the todo server without relying on a
separate PowerShell bootstrap file.

## Setup Mode

If the user invokes **`todo setup`**, treat that as an installation request.

### Required paths

Use these paths on this Windows machine:

- `C:\Users\user\Documents\dev\skills\todo\todo_mcp.py` — **canonical location; lives in this repo**
- `C:\Users\user\todos.db` — global fallback DB (used when no `workspace_root`)
- `C:\Users\user\.copilot\mcp-config.json`
- `C:\Users\user\.copilot\copilot-instructions.md`

`todo_mcp.py` is versioned here alongside `SKILL.md`. Do not copy it to `.copilot\`.
The MCP config simply points at this repo path.

Project-local todos are stored in `{project_root}\.todo\todos.db`.
Add `.todo\` to the project's `.gitignore` during setup.

If a TOML-based Copilot config exists, also check:

- `C:\Users\user\.config\github-copilot\config.toml`

In the current machine state, `mcp-config.json` exists and `config.toml` does not.
Only edit the TOML file if that installation actually uses one.

### Setup actions

When running setup, do all of the following:

1. Confirm `C:\Users\user\Documents\dev\skills\todo\todo_mcp.py` exists (it is the canonical source; update it in-place from the scaffold below if needed)
2. Ensure `C:\Users\user\todos.db` exists
3. Register the `todo` MCP server in `C:\Users\user\.copilot\mcp-config.json` pointing at the skills repo path
4. If `C:\Users\user\.config\github-copilot\config.toml` exists, mirror the registration there
5. Ensure `C:\Users\user\.copilot\copilot-instructions.md` contains the todo trigger rules

### MCP registration snippet

```json
{
  "mcpServers": {
    "todo": {
      "type": "local",
      "command": "python",
      "args": ["C:\\Users\\user\\Documents\\dev\\skills\\todo\\todo_mcp.py"]
    }
  }
}
```

### Python server scaffold

Keep the full setup logic here in agent-readable markdown rather than depending
on an external bootstrap script.

```python
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

GLOBAL_DB_PATH = Path(r"C:\Users\user\todos.db")
mcp = FastMCP("todo")


def _get_db_path(workspace_root: str | None) -> Path:
    if workspace_root is None:
        return GLOBAL_DB_PATH
    p = Path(workspace_root).resolve()
    if not p.is_absolute():
        raise ValueError(f"workspace_root must be an absolute path, got: {workspace_root!r}")
    db_dir = p / ".todo"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "todos.db"


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            task      TEXT    NOT NULL,
            priority  TEXT    NOT NULL DEFAULT 'normal',
            project   TEXT,
            done      INTEGER NOT NULL DEFAULT 0,
            created   TEXT    NOT NULL,
            updated   TEXT    NOT NULL
        )
        """
    )
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
def add_todo(task: str, priority: str = "normal", project: str | None = None, workspace_root: str | None = None) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db(workspace_root) as conn:
        cur = conn.execute(
            "INSERT INTO todos (task, priority, project, created, updated) VALUES (?,?,?,?,?)",
            (task, priority, project, now, now),
        )
        conn.commit()
        return f"Added todo #{cur.lastrowid} {_scope_label(workspace_root)}: {task}"


@mcp.tool()
def list_todos(project: str | None = None, include_done: bool = False, workspace_root: str | None = None) -> str:
    with _db(workspace_root) as conn:
        query = "SELECT * FROM todos WHERE 1=1"
        params: list[object] = []
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
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db(workspace_root) as conn:
        cur = conn.execute("UPDATE todos SET done=1, updated=? WHERE id=?", (now, todo_id))
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(
                f"No todo #{todo_id} in scope {_scope_label(workspace_root)}. "
                "Check workspace_root matches the one used when the todo was added."
            )
        return f"Completed todo #{todo_id} {_scope_label(workspace_root)}"


@mcp.tool()
def update_todo(
    todo_id: int,
    task: str | None = None,
    priority: str | None = None,
    project: str | None = None,
    workspace_root: str | None = None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db(workspace_root) as conn:
        row = conn.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
        if not row:
            raise ValueError(
                f"No todo #{todo_id} in scope {_scope_label(workspace_root)}. "
                "Check workspace_root matches the one used when the todo was added."
            )
        new_task = task if task is not None else row["task"]
        new_priority = priority if priority is not None else row["priority"]
        new_project = project if project is not None else row["project"]
        conn.execute(
            "UPDATE todos SET task=?, priority=?, project=?, updated=? WHERE id=?",
            (new_task, new_priority, new_project, now, todo_id),
        )
        conn.commit()
        return f"Updated todo #{todo_id} {_scope_label(workspace_root)}"


@mcp.tool()
def remove_todo(todo_id: int, workspace_root: str | None = None) -> str:
    with _db(workspace_root) as conn:
        cur = conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(
                f"No todo #{todo_id} in scope {_scope_label(workspace_root)}. "
                "Check workspace_root matches the one used when the todo was added."
            )
        return f"Removed todo #{todo_id} {_scope_label(workspace_root)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Todo MCP server")
    parser.add_argument("--port", type=int, default=None, help="Run as HTTP server on this port")
    args = parser.parse_args()

    if args.port:
        mcp.run(transport="streamable-http", host="localhost", port=args.port)
    else:
        mcp.run()
```

The tool surface should expose:

- `add_todo`
- `list_todos`
- `complete_todo`
- `update_todo`
- `remove_todo`

### Autonomous trigger rules

Before calling any todo tool, determine the git root of the current working
directory (`git rev-parse --show-toplevel`) and pass it as `workspace_root`.
If the session is not inside a git repo, omit `workspace_root` (global fallback).

The setup step should also ensure `C:\Users\user\.copilot\copilot-instructions.md`
contains rules equivalent to:

```markdown
## Todo and Memory Autonomous Triggers

### Workspace root
Always determine the git root of the current working directory before calling
any todo tool. Pass that path as `workspace_root` on every todo call.
If the session is not inside a git repo, omit `workspace_root`.

At the start of every session:
- Call list_todos(workspace_root=<git_root>) to surface pending work before doing anything else

During any task:
- Call add_todo(workspace_root=<git_root>) when a follow-up action is identified that won't be done immediately
- Call complete_todo(workspace_root=<git_root>) when a previously added todo is finished
- Call update_todo(workspace_root=<git_root>) when the scope or priority of a deferred task changes
- Call remove_todo(workspace_root=<git_root>) when a todo is no longer relevant

After completing any significant task:
- Call update_memory on activeContext.md and progress.md to record what changed
- Call add_todo(workspace_root=<git_root>) for any deferred work identified during the task
```

## Trigger-to-Action Map

The skill should operate when the LLM recognizes requests like these:

- **"what's pending?"** -> `list_todos(workspace_root=<git_root>)`
- **"remind me later to..."** -> `add_todo(workspace_root=<git_root>)`
- **"mark that done"** -> `complete_todo(workspace_root=<git_root>)`
- **"change the priority / scope"** -> `update_todo(workspace_root=<git_root>)`
- **"drop that item"** -> `remove_todo(workspace_root=<git_root>)`

At the start of a new session:

- call `list_todos(workspace_root=<git_root>)`

During work:

- convert deferred follow-ups into `add_todo(workspace_root=<git_root>)`

When work finishes:

- call `complete_todo(workspace_root=<git_root>)` for items actually completed

### Project-local storage

Todos created with a `workspace_root` are stored in `{workspace_root}\.todo\todos.db`.
Each project has its own isolated DB. Add `.todo\` to the project's `.gitignore`
so todo state is not committed.

The global fallback `C:\Users\user\todos.db` is only used when `workspace_root`
is omitted (e.g., session is not inside a git repo).

## Minimal Output Contract

When using this skill, report:

- which setup files were created or updated
- whether the MCP server was registered
- which todo action was taken
- which todo ids changed
<!-- consolidation:see-also:start -->
## See Also
[[memory-bank]]
<!-- consolidation:see-also:end -->
