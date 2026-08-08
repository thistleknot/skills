<#
.SYNOPSIS
    Route a bounded coding task directly to @aider via orchestrator.

.DESCRIPTION
    Two modes:

    1. Explicit task (default):
         .\run_aider.ps1 "Create function foo in src\bar.py"

    2. Pull from task graph (no arg or -FromGraph):
         .\run_aider.ps1
         .\run_aider.ps1 -FromGraph

       Queries the nearest .task_graph.db walking up from the current directory,
       picks the oldest pending task assigned to (or unassigned for) aider,
       marks it in_progress, and dispatches it with [task_id=<id>] prefix so
       @aider updates the graph on completion.

    opencode is launched from agents\ so the workspace covers that directory.
    For writes outside agents\, @aider uses bash (has bash:allow permission).

    Rules:
    - Never use --agent aider (blocked by oh-my-opencode-slim — PITFALL 13)
    - Always use --agent orchestrator for the top-level session. Bare `opencode run`
      falls back to the default `build` agent and bypasses the custom hierarchy.
    - Prompt must say "use the task tool RIGHT NOW to spawn @aider" to prevent
      orchestrator from narrating instead of calling the spawn tool
#>
param(
    [Parameter(Position=0)]
    [string]$Task = "",

    [switch]$FromGraph
)

$agentsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $agentsDir

# ── Resolve task graph DB ──────────────────────────────────────────────────
function Find-TaskGraphDb {
    $dir = Get-Location
    while ($dir) {
        $candidate = Join-Path $dir ".task_graph.db"
        if (Test-Path $candidate) { return $candidate }
        $parent = Split-Path $dir -Parent
        if ($parent -eq $dir) { break }
        $dir = $parent
    }
    return $null
}

# ── Pull from graph if no explicit task ───────────────────────────────────
$taskId = $null
if ($FromGraph -or $Task -eq "") {
    $dbPath = Find-TaskGraphDb
    if (-not $dbPath) {
        Write-Error "No .task_graph.db found. Provide a task string or create tasks first."
        exit 1
    }
    $json = python "$agentsDir\query_graph.py" $dbPath next
    $obj  = $json | ConvertFrom-Json
    if (-not $obj.id) {
        Write-Host "No pending aider tasks in graph."
        exit 0
    }
    $taskId = $obj.id
    $Task   = if ($obj.description -and $obj.description -ne "") { $obj.description } else { $obj.title }
    # Mark in_progress
    python "$agentsDir\query_graph.py" $dbPath assign $taskId | Out-Null
    Write-Host "Dispatching task_id=$taskId : $($obj.title)"
}

# ── Build dispatch prompt ─────────────────────────────────────────────────
$taskLine = if ($taskId) { "[task_id=$taskId,workspace_root=C:\Users\user\Documents\dev\skills] $Task" } else { $Task }

$prompt = @"
AIDER DIRECT: use the task tool RIGHT NOW to spawn @aider and have it complete this task. Do not describe what you will do — call the task spawn tool immediately.

Task: $taskLine
"@

opencode run --agent orchestrator $prompt
