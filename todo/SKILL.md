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

- `C:\Users\user\.copilot\todo_mcp.py`
- `C:\Users\user\.copilot\todos.db`
- `C:\Users\user\.copilot\mcp-config.json`
- `C:\Users\user\.copilot\copilot-instructions.md`

If a TOML-based Copilot config exists, also check:

- `C:\Users\user\.config\github-copilot\config.toml`

In the current machine state, `mcp-config.json` exists and `config.toml` does not.
Only edit the TOML file if that installation actually uses one.

### Setup actions

When running setup, do all of the following:

1. Write `C:\Users\user\.copilot\todo_mcp.py`
2. Ensure `C:\Users\user\.copilot\todos.db` exists
3. Register the `todo` MCP server in `C:\Users\user\.copilot\mcp-config.json`
4. If `C:\Users\user\.config\github-copilot\config.toml` exists, mirror the registration there
5. Ensure `C:\Users\user\.copilot\copilot-instructions.md` contains the todo trigger rules

### MCP registration snippet

```json
{
  "mcpServers": {
    "todo": {
      "type": "local",
      "command": "python",
      "args": ["C:\\Users\\user\\.copilot\\todo_mcp.py"]
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

DB_PATH = Path(r"C:\Users\user\.copilot\todos.db")
mcp = FastMCP("todo")


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
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


@mcp.tool()
def add_todo(task: str, priority: str = "normal", project: str | None = None) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO todos (task, priority, project, created, updated) VALUES (?,?,?,?,?)",
            (task, priority, project, now, now),
        )
        conn.commit()
        return f"Added todo #{cur.lastrowid}: {task}"


@mcp.tool()
def list_todos(project: str | None = None, include_done: bool = False) -> str:
    with _db() as conn:
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
        return "No pending todos."

    lines = []
    for row in rows:
        status = "x" if row["done"] else " "
        proj = f" [{row['project']}]" if row["project"] else ""
        lines.append(f"[{status}] #{row['id']} ({row['priority']}){proj} {row['task']}")
    return "\n".join(lines)


@mcp.tool()
def complete_todo(todo_id: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db() as conn:
        cur = conn.execute("UPDATE todos SET done=1, updated=? WHERE id=?", (now, todo_id))
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"No todo with id {todo_id}")
        return f"Completed todo #{todo_id}"


@mcp.tool()
def update_todo(
    todo_id: int,
    task: str | None = None,
    priority: str | None = None,
    project: str | None = None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db() as conn:
        row = conn.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
        if not row:
            raise ValueError(f"No todo with id {todo_id}")

        new_task = task if task is not None else row["task"]
        new_priority = priority if priority is not None else row["priority"]
        new_project = project if project is not None else row["project"]
        conn.execute(
            "UPDATE todos SET task=?, priority=?, project=?, updated=? WHERE id=?",
            (new_task, new_priority, new_project, now, todo_id),
        )
        conn.commit()
        return f"Updated todo #{todo_id}"


@mcp.tool()
def remove_todo(todo_id: int) -> str:
    with _db() as conn:
        cur = conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"No todo with id {todo_id}")
        return f"Removed todo #{todo_id}"


if __name__ == "__main__":
    mcp.run()
```

The tool surface should expose:

- `add_todo`
- `list_todos`
- `complete_todo`
- `update_todo`
- `remove_todo`

### Autonomous trigger rules

The setup step should also ensure `C:\Users\user\.copilot\copilot-instructions.md`
contains rules equivalent to:

```markdown
## Todo and Memory Autonomous Triggers

At the start of every session:
- Call list_todos to surface pending work before doing anything else

During any task:
- Call add_todo when a follow-up action is identified that won't be done immediately
- Call complete_todo when a previously added todo is finished
- Call update_todo when the scope or priority of a deferred task changes
- Call remove_todo when a todo is no longer relevant

After completing any significant task:
- Call update_memory on activeContext.md and progress.md to record what changed
- Call add_todo for any deferred work identified during the task
```

## Trigger-to-Action Map

The skill should operate when the LLM recognizes requests like these:

- **"what's pending?"** -> `list_todos`
- **"remind me later to..."** -> `add_todo`
- **"mark that done"** -> `complete_todo`
- **"change the priority / scope"** -> `update_todo`
- **"drop that item"** -> `remove_todo`

At the start of a new session:

- call `list_todos`

During work:

- convert deferred follow-ups into `add_todo`

When work finishes:

- call `complete_todo` for items actually completed

## Minimal Output Contract

When using this skill, report:

- which setup files were created or updated
- whether the MCP server was registered
- which todo action was taken
- which todo ids changed
