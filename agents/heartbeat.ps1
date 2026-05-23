<#
.SYNOPSIS
    Watchdog harness for OpenCode orchestrator sessions (task-graph edition).

.DESCRIPTION
    Launches an orchestrator session backed by a SQLite task graph. The orchestrator
    records liveness by calling record_heartbeat(task_id) via the task-graph MCP on
    every turn. This watchdog polls the DB directly — no stdout parsing required.

    The orchestrator signals completion by calling update_status(root_id, 'done').
    The watchdog exits cleanly when it observes that status.

    Stall conditions:
      - last_heartbeat on root task not updated within STALL_THRESHOLD_SECONDS (300s)
      - No first heartbeat recorded within NO_FIRST_HB_THRESHOLD_SECONDS (120s)
      - Time outlier: elapsed is a MAD outlier vs task history

    On stall:
      - Kill session, rotate sampler profile + fresh seed
      - Reset root task status to 'pending' (keeps child states for resume)
      - Relaunch with same task_id so orchestrator resumes from graph state

    Termination:
      - root task status = 'done'  -> clean exit 0
      - max retries exhausted      -> exit 1

.PARAMETER Task
    The task string to pass to opencode run.

.PARAMETER WorkDir
    Working directory for the opencode session. Defaults to current location.

.PARAMETER InitialProfile
    Starting sampler profile: balanced | conservative | creative. Default: balanced.

.PARAMETER MaxRetries
    Maximum session attempts before giving up. Default: 9 (3 profiles x 3 seeds).

.PARAMETER AgentName
    Agent to invoke. Default: orchestrator. Use 'pi' to run pi in command-test mode.

.PARAMETER TaskId
    If provided, resume an existing root task (skip creation). Useful after manual
    intervention or when re-running a partially-completed session.

.EXAMPLE
    .\heartbeat.ps1 -Task "migrate all SKILL.md files to new format"

.EXAMPLE
    .\heartbeat.ps1 -AgentName pi -Task "run .\sync_skills.ps1 -y" -WorkDir "C:\Users\user\Documents\dev\skills"
#>
param(
    [Parameter(Mandatory)]
    [string]$Task,

    [string]$WorkDir = $PWD,

    [ValidateSet("balanced", "conservative", "creative")]
    [string]$InitialProfile = "balanced",

    [int]$MaxRetries = 9,

    [ValidateSet("orchestrator", "pi")]
    [string]$AgentName = "orchestrator",

    [string]$TaskId = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Constants ─────────────────────────────────────────────────────────────────

$SAMPLER_ROTATION            = @("balanced", "conservative", "creative")
$MAD_SCALE                   = 1.4826
$STALL_THRESHOLD_SECONDS     = 300   # no heartbeat update = stall
$NO_FIRST_HB_THRESHOLD_SEC   = 120   # no first heartbeat at all = stall
$POLL_INTERVAL_SECONDS       = 15

$SAMPLER_PROFILES = @{
    balanced = @{
        temperature       = 0.7
        top_p             = 0.9
        frequency_penalty = 0.3
        presence_penalty  = 0.1
    }
    conservative = @{
        temperature       = 0.1
        top_p             = 1.0
        frequency_penalty = 0.0
        presence_penalty  = 0.0
    }
    creative = @{
        temperature       = 1.2
        top_p             = 0.95
        frequency_penalty = 0.5
        presence_penalty  = 0.4
    }
}

# ── SQLite DB helpers (via python -c to avoid string-escaping hell) ───────────

function New-RootTask([string]$db, [string]$title) {
    $tid = python -c @"
import sqlite3, uuid, time, sys
db, title = sys.argv[1], sys.argv[2]
tid = uuid.uuid4().hex[:12]
con = sqlite3.connect(db)
con.execute('PRAGMA journal_mode=WAL')
con.execute('PRAGMA busy_timeout=5000')
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
            (tid, title, time.time()))
con.commit()
print(tid)
"@ $db $title 2>$null
    if ($LASTEXITCODE -ne 0) { return "" }
    return ($tid | Out-String).Trim()
}

function Reset-RootTask([string]$db, [string]$tid) {
    python -c @"
import sqlite3, time, sys
db, tid = sys.argv[1], sys.argv[2]
con = sqlite3.connect(db)
con.execute("UPDATE tasks SET status='pending', last_heartbeat=?, updated_at=? WHERE id=?",
            (time.time(), time.time(), tid))
con.commit()
"@ $db $tid 2>$null | Out-Null
}

function Get-TaskState([string]$db, [string]$tid) {
    $json = python -c @"
import sqlite3, json, sys
db, tid = sys.argv[1], sys.argv[2]
row = sqlite3.connect(db).execute(
    'SELECT status, last_heartbeat FROM tasks WHERE id=?', [tid]).fetchone()
print(json.dumps({'status': row[0] if row else 'missing',
                  'heartbeat': row[1] if row else None}))
"@ $db $tid 2>$null
    if ($json) { return $json | ConvertFrom-Json }
    return [PSCustomObject]@{ status = "missing"; heartbeat = $null }
}

# ── Session helpers ───────────────────────────────────────────────────────────

function Get-Seed { Get-Random -Minimum 1 -Maximum ([int]::MaxValue) }

function Get-DurationStats([double[]]$history) {
    if ($history.Count -lt 3) { return $null }
    $sorted = $history | Sort-Object
    $median = $sorted[[int]($sorted.Count / 2)]
    $devs   = $sorted | ForEach-Object { [Math]::Abs($_ - $median) }
    $mad    = ($devs | Sort-Object)[[int]($devs.Count / 2)]
    return @{ Median = $median; MAD = $mad }
}

function Build-TempConfig([string]$profile, [int]$seed, [string]$baseConfigPath) {
    $raw  = Get-Content $baseConfigPath -Raw
    $cfg  = $raw | ConvertFrom-Json

    $params = [hashtable]$SAMPLER_PROFILES[$profile].Clone()
    $params["seed"] = $seed

    foreach ($model in $cfg.provider.openrouter.models.PSObject.Properties) {
        $variants = $model.Value.variants
        if (-not $variants) { continue }
        foreach ($vname in $variants.PSObject.Properties.Name) {
            if ($vname -match "orchestrator|balanced|conservative|creative|lean") {
                $variants.$vname | Add-Member -NotePropertyName modelKwargs `
                    -NotePropertyValue ([PSCustomObject]$params) -Force
            }
        }
    }

    $tmpPath = [IO.Path]::ChangeExtension([IO.Path]::GetTempFileName(), ".json")
    $cfg | ConvertTo-Json -Depth 15 | Set-Content $tmpPath -Encoding UTF8
    return $tmpPath
}

function Start-Session([string]$configPath, [string]$agent, [string]$prompt, [string]$workDir) {
    $logOut    = [IO.Path]::GetTempFileName()
    $logErr    = "$logOut.err"
    # opencode has no --config flag; it discovers opencode.json by walking up from cwd.
    # Run from PSScriptRoot (agents/) so it finds agents/opencode.json, pass --dir for workspace.
    $agentsDir = Split-Path $configPath -Parent

    $proc = Start-Process -FilePath "opencode" `
        -ArgumentList "run", "--agent", $agent, "--dir", $workDir, $prompt `
        -WorkingDirectory $agentsDir `
        -RedirectStandardOutput $logOut `
        -RedirectStandardError  $logErr `
        -PassThru -NoNewWindow

    return @{ Proc = $proc; Log = $logOut; Err = $logErr }
}

function Stop-Session($session) {
    try { if (-not $session.Proc.HasExited) { $session.Proc.Kill() } } catch { }
    Remove-Item $session.Log, $session.Err -Force -ErrorAction SilentlyContinue
}

# ── Main ──────────────────────────────────────────────────────────────────────

$baseConfigPath = Join-Path $PSScriptRoot "opencode.json"
$dbPath         = Join-Path $WorkDir ".task_graph.db"
$profileIdx     = $SAMPLER_ROTATION.IndexOf($InitialProfile)
$taskHistory    = [System.Collections.Generic.List[double]]::new()
$retryCount     = 0
$finalSuccess   = $false

# Create or reuse root task
if ($TaskId) {
    $taskId = $TaskId
    Write-Host "  Resuming task_id=$taskId" -ForegroundColor DarkGray
} else {
    $taskId = New-RootTask $dbPath $Task
    if (-not $taskId) {
        Write-Host "ERROR: failed to create root task in $dbPath" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "== heartbeat watchdog ==" -ForegroundColor Cyan
Write-Host "  agent   : $AgentName"
Write-Host "  task    : $Task"
Write-Host "  workdir : $WorkDir"
Write-Host "  task_id : $taskId"
Write-Host "  db      : $dbPath"
Write-Host ""

while ($retryCount -lt $MaxRetries) {
    $profile = $SAMPLER_ROTATION[$profileIdx % 3]
    $seed    = Get-Seed
    $tmpCfg  = Build-TempConfig $profile $seed $baseConfigPath

    # Reset root task status; child task states are preserved for resume
    Reset-RootTask $dbPath $taskId

    # Embed task_id and workspace_root into prompt so orchestrator can call MCP tools
    $augTask = "[task_id=$taskId,workspace_root=$WorkDir] $Task"

    $session     = Start-Session $tmpCfg $AgentName $augTask $WorkDir
    $start       = Get-Date
    $firstHbSeen = $false
    $done        = $false
    $stall       = $false

    Write-Host ">> attempt $($retryCount + 1) | profile=$profile | seed=$seed" -ForegroundColor Cyan

    while (-not $session.Proc.HasExited) {
        Start-Sleep $POLL_INTERVAL_SECONDS

        $state   = Get-TaskState $dbPath $taskId
        $elapsed = ((Get-Date) - $start).TotalSeconds

        # ── Done signal ──────────────────────────────────────────────────────
        if ($state.status -eq "done") {
            $done = $true; break
        }

        # ── Track first heartbeat ────────────────────────────────────────────
        if (-not $firstHbSeen -and $state.heartbeat -ne $null) {
            $firstHbSeen = $true
            Write-Host "  [HB] first heartbeat at ${elapsed}s" -ForegroundColor DarkGray
        }

        # ── Stall: no first heartbeat within threshold ───────────────────────
        if (-not $firstHbSeen -and $elapsed -gt $NO_FIRST_HB_THRESHOLD_SEC) {
            Write-Host "  [STALL] no heartbeat within ${NO_FIRST_HB_THRESHOLD_SEC}s" -ForegroundColor Yellow
            $stall = $true; break
        }

        # ── Stall: heartbeat gone stale ──────────────────────────────────────
        if ($firstHbSeen -and $state.heartbeat -ne $null) {
            $nowEpoch  = [DateTimeOffset]::Now.ToUnixTimeSeconds()
            $staleness = $nowEpoch - [long][Math]::Floor($state.heartbeat)
            if ($staleness -gt $STALL_THRESHOLD_SECONDS) {
                Write-Host "  [STALL] heartbeat stale by ${staleness}s (> ${STALL_THRESHOLD_SECONDS}s)" -ForegroundColor Yellow
                $stall = $true; break
            }
        }

        # ── Time outlier ─────────────────────────────────────────────────────
        $stats = Get-DurationStats ([double[]]$taskHistory.ToArray())
        if ($stats) {
            $threshold = $stats.Median + 3 * $MAD_SCALE * $stats.MAD
            if ($elapsed -gt $threshold) {
                Write-Host "  [TIME OVERRUN] ${elapsed}s > $([int]$threshold)s outlier threshold" -ForegroundColor Yellow
                $stall = $true; break
            }
        }
    }

    # Session may have exited cleanly — do one final status check
    if (-not $done) {
        $state = Get-TaskState $dbPath $taskId
        if ($state.status -eq "done") { $done = $true }
    }

    $elapsed = ((Get-Date) - $start).TotalSeconds
    $taskHistory.Add($elapsed)
    Stop-Session $session
    Remove-Item $tmpCfg -Force -ErrorAction SilentlyContinue

    if ($done) {
        Write-Host "OK done (profile=$profile seed=$seed $([int]$elapsed)s)" -ForegroundColor Green
        $finalSuccess = $true
        break
    }

    $retryCount++
    $profileIdx++
    Write-Host "  rotating -> $($SAMPLER_ROTATION[$profileIdx % 3])..." -ForegroundColor DarkGray
}

if (-not $finalSuccess) {
    Write-Host "FAILED max retries ($MaxRetries) exhausted" -ForegroundColor Red
    exit 1
}
