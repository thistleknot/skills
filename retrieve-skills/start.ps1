# start.ps1 — Robust launcher for skill-router with auto-restart on crash.
# Usage: Start-Process pwsh -ArgumentList "-File C:\Users\user\.claude\skills\retrieve-skills\start.ps1" -WindowStyle Hidden
# Stop:  Stop-Process -Id (Get-Content .\router.pid)
#
# Guarantees:
# - stdout/stderr always captured in server.log
# - PID recorded in router.pid
# - Auto-restart with exponential backoff (2s, 4s, 8s, capped at 30s)
# - Resets backoff after 60s of healthy runtime

param(
    [int]$Port = 8765,
    [string]$Python = "c:\users\user\py310\Scripts\python.exe",
    [int]$MaxBackoff = 30
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Avast sets SSLKEYLOGFILE to its proxy path; Python's ssl.create_default_context()
# tries to open it for writing -> PermissionError crash. Unset for this process tree.
$env:SSLKEYLOGFILE = $null

$logFile = Join-Path $scriptDir "server.log"
$pidFile = Join-Path $scriptDir "router.pid"
$watcherPidFile = Join-Path $scriptDir "watcher.pid"

# Record THIS watcher's PID so it can be killed cleanly
$PID | Set-Content $watcherPidFile

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] [watcher] $msg" | Add-Content $logFile
}

function Test-Health {
    try {
        $resp = Invoke-WebRequest "http://127.0.0.1:${Port}/health" -UseBasicParsing -TimeoutSec 5
        return $resp.StatusCode -eq 200
    } catch {
        return $false
    }
}

# Kill anything on our port first
try {
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess |
        Sort-Object -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
} catch {}

$backoff = 2
$restartCount = 0

Write-Log "Watcher starting (PID=$PID). Will supervise server.py on port $Port."

while ($true) {
    Write-Log "Starting server.py (attempt $($restartCount + 1), backoff=${backoff}s)"

    # Start the server process with output redirected to log
    $proc = Start-Process -FilePath $Python -ArgumentList "server.py" `
        -WorkingDirectory $scriptDir `
        -RedirectStandardOutput "$scriptDir\server_stdout.log" `
        -RedirectStandardError "$scriptDir\server_stderr.log" `
        -PassThru -NoNewWindow

    $proc.Id | Set-Content $pidFile
    Write-Log "Server started with PID=$($proc.Id)"

    # Wait for health (up to 180s for model loading/warmup)
    $healthy = $false
    for ($i = 0; $i -lt 180; $i++) {
        if ($proc.HasExited) {
            Write-Log "Server exited during startup with code $($proc.ExitCode)"
            break
        }
        if (Test-Health) {
            $healthy = $true
            Write-Log "Health check passed after ${i}s"
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not $healthy -and -not $proc.HasExited) {
        Write-Log "Health check failed after 180s; killing server"
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }

    if ($healthy) {
        # Monitor: check health every 10s, restart on failure
        $startTime = Get-Date
        while ($true) {
            Start-Sleep -Seconds 10

            if ($proc.HasExited) {
                Write-Log "Server exited unexpectedly with code $($proc.ExitCode)"
                break
            }

            if (-not (Test-Health)) {
                Write-Log "Health check failed while running; checking again in 5s..."
                Start-Sleep -Seconds 5
                if (-not (Test-Health)) {
                    Write-Log "Health still failing; killing and restarting"
                    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                    break
                }
            }

            # Reset backoff after 60s of stable runtime
            $elapsed = ((Get-Date) - $startTime).TotalSeconds
            if ($elapsed -gt 60 -and $backoff -gt 2) {
                $backoff = 2
                Write-Log "Stable for ${elapsed}s; backoff reset to 2s"
            }
        }
    }

    # Append the process-specific logs into the main server.log
    if (Test-Path "$scriptDir\server_stdout.log") {
        Get-Content "$scriptDir\server_stdout.log" | Add-Content $logFile
        Remove-Item "$scriptDir\server_stdout.log" -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path "$scriptDir\server_stderr.log") {
        Get-Content "$scriptDir\server_stderr.log" | Add-Content $logFile
        Remove-Item "$scriptDir\server_stderr.log" -Force -ErrorAction SilentlyContinue
    }

    $restartCount++
    Write-Log "Sleeping ${backoff}s before restart..."
    Start-Sleep -Seconds $backoff
    $backoff = [Math]::Min($backoff * 2, $MaxBackoff)
}
