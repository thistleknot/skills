# copilot_todo_setup.ps1
#
# Adds a sqlite-backed todo MCP server to GitHub Copilot CLI on Windows.
# Run after copilot_memory_setup.ps1.
#
#   .\copilot_todo_setup.ps1
#
# What this does:
#   1. Writes ~/.copilot/todo_mcp.py (fastmcp server backed by sqlite)
#   2. Registers the server in ~/.copilot/mcp-config.json
#   3. Appends autonomous trigger rules to ~/.copilot/copilot-instructions.md
#
# Tools registered (Copilot calls these automatically per instructions):
#   add_todo      - when deferred follow-up work is identified during a task
#   list_todos    - at the start of every session to surface pending work
#   complete_todo - when a todo item is finished
#   update_todo   - when scope or priority of a todo changes
#   remove_todo   - when a todo is no longer relevant
#
# Storage: ~/.copilot/todos.db (global, shared across all projects)
# Copilot CLI launches this server automatically on session start via mcp-config.json.

$ErrorActionPreference = "Stop"

$CopilotDir  = Join-Path $HOME ".copilot"
$McpServer   = Join-Path $CopilotDir "todo_mcp.py"
$McpConfig   = Join-Path $CopilotDir "mcp-config.json"
$GlobalInstr = Join-Path $CopilotDir "copilot-instructions.md"
$TodoDb      = Join-Path $CopilotDir "todos.db"

if (-not (Test-Path $CopilotDir)) {
    Write-Error "~/.copilot not found. Run copilot_memory_setup.ps1 first."
    exit 1
}

# ── 1. MCP server ──────────────────────────────────────────────────────────────

Set-Content -Path $McpServer -Encoding UTF8 -Value @"
"""
todo_mcp.py -- fastmcp sqlite-backed todo server for Copilot CLI.

Purpose:
    Provides todo management tools that Copilot calls autonomously based on
    session context. All state persists in a sqlite db across sessions.

Preconditions:
    - fastmcp installed: pip install fastmcp

Failure modes:
    - DB write failure: propagates sqlite3.Error
    - Invalid todo_id: raises ValueError
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

DB_PATH = Path(r"$TodoDb")

mcp = FastMCP("todo")


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
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


@mcp.tool()
def add_todo(task: str, priority: str = "normal", project: str = None) -> str:
    """
    Add a new todo item.

    Call this when a follow-up action is identified during a task that won't
    be completed immediately. Examples: a refactor spotted while fixing a bug,
    a benchmark that should be run later, a config change deferred to next session.

    Args:
        task:     Description of the work to be done.
        priority: 'low', 'normal', or 'high'. Default 'normal'.
        project:  Optional project name to scope the todo.

    Returns:
        Confirmation with the assigned todo ID.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO todos (task, priority, project, created, updated) VALUES (?,?,?,?,?)",
            (task, priority, project, now, now)
        )
        conn.commit()
        return f"Added todo #{cur.lastrowid}: {task}"


@mcp.tool()
def list_todos(project: str = None, include_done: bool = False) -> str:
    """
    List todo items.

    Call this automatically at the start of every session to surface pending
    work before beginning any task. Also call when the user asks what's pending
    or what to work on next.

    Args:
        project:      Filter by project name. If None, returns all projects.
        include_done: Include completed items. Default False.

    Returns:
        Formatted list of todos, grouped by priority.
    """
    with _db() as conn:
        query = "SELECT * FROM todos WHERE 1=1"
        params = []
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
    """
    Mark a todo item as complete.

    Call this when a task that was previously added as a todo has been finished
    during the current session.

    Args:
        todo_id: The numeric ID of the todo to complete (from list_todos).

    Returns:
        Confirmation string.

    Raises:
        ValueError: todo_id does not exist.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db() as conn:
        cur = conn.execute(
            "UPDATE todos SET done=1, updated=? WHERE id=?", (now, todo_id)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"No todo with id {todo_id}")
        return f"Completed todo #{todo_id}"


@mcp.tool()
def update_todo(todo_id: int, task: str = None, priority: str = None, project: str = None) -> str:
    """
    Update the description, priority, or project of a todo.

    Call this when the scope or priority of a deferred task changes based on
    new information discovered during the current session.

    Args:
        todo_id:  The numeric ID of the todo to update.
        task:     New task description. If None, unchanged.
        priority: New priority ('low', 'normal', 'high'). If None, unchanged.
        project:  New project name. If None, unchanged.

    Returns:
        Confirmation string.

    Raises:
        ValueError: todo_id does not exist.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db() as conn:
        row = conn.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
        if not row:
            raise ValueError(f"No todo with id {todo_id}")
        new_task     = task     if task     is not None else row["task"]
        new_priority = priority if priority is not None else row["priority"]
        new_project  = project  if project  is not None else row["project"]
        conn.execute(
            "UPDATE todos SET task=?, priority=?, project=?, updated=? WHERE id=?",
            (new_task, new_priority, new_project, now, todo_id)
        )
        conn.commit()
        return f"Updated todo #{todo_id}"


@mcp.tool()
def remove_todo(todo_id: int) -> str:
    """
    Permanently delete a todo item.

    Call this when a todo is no longer relevant and should not appear in future
    listings. Use complete_todo instead if the work was actually done.

    Args:
        todo_id: The numeric ID of the todo to remove.

    Returns:
        Confirmation string.

    Raises:
        ValueError: todo_id does not exist.
    """
    with _db() as conn:
        cur = conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"No todo with id {todo_id}")
        return f"Removed todo #{todo_id}"


if __name__ == "__main__":
    mcp.run()
"@
Write-Host "  wrote: todo_mcp.py"

# ── 2. MCP config registration ─────────────────────────────────────────────────

if (Test-Path $McpConfig) {
    $config = Get-Content $McpConfig -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $config.mcpServers) {
        $config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{})
    }
    $config.mcpServers | Add-Member -NotePropertyName "todo" -NotePropertyValue ([PSCustomObject]@{
        type    = "local"
        command = "python"
        args    = @($McpServer)
    }) -Force
    $config | ConvertTo-Json -Depth 10 | Set-Content $McpConfig -Encoding UTF8
    Write-Host "  merged into: mcp-config.json"
} else {
    [PSCustomObject]@{
        mcpServers = [PSCustomObject]@{
            "todo" = [PSCustomObject]@{
                type    = "local"
                command = "python"
                args    = @($McpServer)
            }
        }
    } | ConvertTo-Json -Depth 10 | Set-Content $McpConfig -Encoding UTF8
    Write-Host "  created: mcp-config.json"
}

# ── 3. Append autonomous trigger rules to copilot-instructions.md ──────────────

$todoRules = @'


## Todo and Memory Autonomous Triggers

At the start of every session:
- Call list_todos to surface pending work before doing anything else

During any task:
- Call add_todo when a follow-up action is identified that won't be done immediately
- Call complete_todo when a previously added todo is finished
- Call update_todo when the scope or priority of a deferred task changes
- Call remove_todo when a todo is no longer relevant

After completing any significant task (architectural decision, completed feature,
resolved blocker - not answering a question or writing a snippet):
- Call update_memory on activeContext.md and progress.md to record what changed
- Call add_todo for any deferred work identified during the task
'@

if (Test-Path $GlobalInstr) {
    if (-not (Select-String -Path $GlobalInstr -Pattern "Todo and Memory Autonomous Triggers" -Quiet)) {
        Add-Content -Path $GlobalInstr -Value $todoRules -Encoding UTF8
        Write-Host "  appended autonomous trigger rules to: copilot-instructions.md"
    } else {
        Write-Host "  trigger rules already present in: copilot-instructions.md"
    }
} else {
    Set-Content -Path $GlobalInstr -Value $todoRules.Trim() -Encoding UTF8
    Write-Host "  created: copilot-instructions.md"
}

# ── Done ───────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Done. Restart Copilot CLI for the new server to take effect."
Write-Host ""
Write-Host "Todo server : $McpServer"
Write-Host "Todo db     : $TodoDb"
Write-Host "MCP config  : $McpConfig"