<#
.SYNOPSIS
    Smoke test for the task-graph harness via pi.

.DESCRIPTION
    Verifies the end-to-end plumbing without running a full orchestrator session:
      1. Creates a root task in .task_graph.db
      2. Runs pi with a trivial command to confirm pi works
      3. Manually simulates heartbeat + done via Python
      4. Asserts the DB reflects expected state

    Run from the agents/ directory or pass WorkDir explicitly.

.PARAMETER WorkDir
    Git root containing .task_graph.db. Defaults to parent of this script.
#>
param(
    [string]$WorkDir = (Split-Path $PSScriptRoot -Parent)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$dbPath  = Join-Path $WorkDir ".task_graph.db"
$mcp     = Join-Path $WorkDir "todo\task_graph_mcp.py"
$pass    = 0
$fail    = 0

function Assert([string]$label, [bool]$condition) {
    if ($condition) {
        Write-Host "  [PASS] $label" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "  [FAIL] $label" -ForegroundColor Red
        $script:fail++
    }
}

Write-Host ""
Write-Host "== test_harness smoke test ==" -ForegroundColor Cyan
Write-Host "  workdir : $WorkDir"
Write-Host "  db      : $dbPath"
Write-Host ""

# ── 1. task_graph_mcp.py imports cleanly ─────────────────────────────────────
Write-Host "-- 1. MCP import check"
$importOk = python -c "import sys; sys.path.insert(0,'$WorkDir'); from todo.task_graph_mcp import mcp; print('ok')" 2>&1 | Out-String
Assert "task_graph_mcp.py imports ok" ($importOk -match "ok")

# ── 2. Create root task ───────────────────────────────────────────────────────
Write-Host "-- 2. Create root task"
$taskId = python -c @"
import sqlite3, uuid, time, sys
db = sys.argv[1]
tid = uuid.uuid4().hex[:12]
con = sqlite3.connect(db)
con.execute('PRAGMA journal_mode=WAL')
con.executescript('''
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, title TEXT, description TEXT,
  status TEXT NOT NULL DEFAULT "pending", assigned_to TEXT, result TEXT,
  last_heartbeat REAL, parent_id TEXT,
  created_at REAL NOT NULL DEFAULT (unixepoch()),
  updated_at REAL NOT NULL DEFAULT (unixepoch()));
CREATE TABLE IF NOT EXISTS edges (
  from_id TEXT NOT NULL, edge_type TEXT NOT NULL, to_id TEXT NOT NULL,
  PRIMARY KEY (from_id, edge_type, to_id));
''')
con.execute("INSERT OR IGNORE INTO tasks (id, title, status, last_heartbeat) VALUES (?,?,'pending',?)",
            (tid, 'smoke-test-root', time.time()))
con.commit()
print(tid)
"@ $dbPath 2>$null
$taskId = ($taskId | Out-String).Trim()
Assert "root task created (id=$taskId)" ($taskId.Length -eq 12)

# ── 3. Verify pi runs a trivial command ───────────────────────────────────────
Write-Host "-- 3. Pi trivial command"
$piOut = Push-Location $PSScriptRoot; opencode run --agent pi "echo smoke-test-ok" 2>&1 | Out-String; Pop-Location
Assert "pi executed trivial command" ($piOut -match "smoke-test-ok")

# ── 4. Simulate heartbeat ─────────────────────────────────────────────────────
Write-Host "-- 4. Heartbeat simulation"
python -c @"
import sqlite3, time, sys
db, tid = sys.argv[1], sys.argv[2]
con = sqlite3.connect(db)
con.execute("UPDATE tasks SET last_heartbeat=?, updated_at=? WHERE id=?",
            (time.time(), time.time(), tid))
con.commit()
"@ $dbPath $taskId 2>$null | Out-Null

$hbVal = python -c @"
import sqlite3, sys
db, tid = sys.argv[1], sys.argv[2]
row = sqlite3.connect(db).execute('SELECT last_heartbeat FROM tasks WHERE id=?', [tid]).fetchone()
print('set' if row and row[0] else 'missing')
"@ $dbPath $taskId 2>$null | Out-String
Assert "heartbeat recorded in DB" ($hbVal -match "set")

# ── 5. Mark done and verify ───────────────────────────────────────────────────
Write-Host "-- 5. Done signal"
python -c @"
import sqlite3, time, sys
db, tid = sys.argv[1], sys.argv[2]
con = sqlite3.connect(db)
con.execute("UPDATE tasks SET status='done', result='smoke test passed', updated_at=? WHERE id=?",
            (time.time(), tid))
con.commit()
"@ $dbPath $taskId 2>$null | Out-Null

$statusVal = python -c @"
import sqlite3, sys
db, tid = sys.argv[1], sys.argv[2]
row = sqlite3.connect(db).execute('SELECT status FROM tasks WHERE id=?', [tid]).fetchone()
print(row[0] if row else 'missing')
"@ $dbPath $taskId 2>$null | Out-String
Assert "root task status=done" ($statusVal -match "done")

# ── Cleanup test task ─────────────────────────────────────────────────────────
python -c @"
import sqlite3, sys
db, tid = sys.argv[1], sys.argv[2]
con = sqlite3.connect(db)
con.execute("DELETE FROM tasks WHERE id=?", (tid,))
con.commit()
"@ $dbPath $taskId 2>$null | Out-Null

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Results: $pass passed, $fail failed" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })
if ($fail -gt 0) { exit 1 }
