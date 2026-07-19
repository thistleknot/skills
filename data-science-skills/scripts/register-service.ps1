# Registers the data-science-skills FastMCP server as an auto-start,
# auto-restart Windows service via NSSM.
#
# This is litellm-windows-service's register-litellm-service.ps1 retargeted
# at mcp_server.py -- same NSSM procedure, same traps (see that skill's
# SKILL.md Traps section for why each setting below is there, especially the
# PYTHONIOENCODING/PYTHONUTF8 pair: any Python service on this machine hits
# the same cp1252-banner-crash trap on a plain launch).
#
# Run ELEVATED (admin). Idempotent. Self-logs via transcript so results are
# readable even when launched with
#   Start-Process -Verb RunAs -ArgumentList '-File', <this>
#
# Adjust the paths/port below for your machine, then run elevated.
$Nssm      = "$HOME\.pi\bin\nssm.exe"
$Python    = "$HOME\py310\Scripts\python.exe"           # adjust to the venv running fastmcp/psycopg2/torch
$Server    = "$PSScriptRoot\mcp_server.py"
$Port      = 8765                                        # FastMCP's own bind port, if it exposes one over HTTP
$Log       = "$HOME\.pi\tmp\data-science-skills-mcp.log"
$Svc       = 'data-science-skills-mcp'

$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null
try { Stop-Transcript | Out-Null } catch {}
Start-Transcript -Path "$HOME\.pi\tmp\register-dss-result.log" -Force | Out-Null

Write-Host "== whoami:" (whoami)
Write-Host "== is admin:" ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# Free the port: stop any manual instance holding it (skip if the server
# doesn't bind a TCP port directly -- e.g. stdio-only MCP transport).
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Host "== stopping port holder PID $($_.OwningProcess)"; Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

# Clean slate (safe if service doesn't exist yet).
& $Nssm stop   $Svc 2>&1 | Write-Host
& $Nssm remove $Svc confirm 2>&1 | Write-Host

# Install + configure.
& $Nssm install $Svc $Python $Server 2>&1 | Write-Host
& $Nssm set $Svc AppDirectory (Split-Path $Server) 2>&1 | Write-Host
& $Nssm set $Svc AppEnvironmentExtra PYTHONIOENCODING=utf-8 PYTHONUTF8=1 2>&1 | Write-Host   # REQUIRED: cp1252 banner crash
& $Nssm set $Svc AppStdout $Log 2>&1 | Write-Host
& $Nssm set $Svc AppStderr $Log 2>&1 | Write-Host
& $Nssm set $Svc AppRotateFiles 1 2>&1 | Write-Host
& $Nssm set $Svc AppRotateOnline 1 2>&1 | Write-Host
& $Nssm set $Svc AppRotateBytes 5242880 2>&1 | Write-Host
& $Nssm set $Svc Start SERVICE_AUTO_START 2>&1 | Write-Host
& $Nssm set $Svc AppExit Default Restart 2>&1 | Write-Host          # auto-restart on crash (NSSM default)
& $Nssm set $Svc AppRestartDelay 3000 2>&1 | Write-Host
& $Nssm set $Svc AppThrottle 5000 2>&1 | Write-Host
& $Nssm set $Svc DisplayName 'Data Science Skills MCP' 2>&1 | Write-Host
& $Nssm set $Svc Description 'FastMCP retrieval service over the stackskills skills_master pgvector collection' 2>&1 | Write-Host

# Start + verify (a Python service may take longer than litellm to bind --
# torch/transformers model loads for ColBERT happen lazily on first request
# in mcp_server.py, but FastMCP's own listener should still come up quickly;
# poll rather than assuming instant readiness, per the litellm skill's trap).
& $Nssm start $Svc 2>&1 | Write-Host
Write-Host "== service:" (Get-Service $Svc | Select-Object -Expand Status)
for ($i=0; $i -lt 12; $i++) {
    $up = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($up) { break }; Start-Sleep 3
}
Write-Host "== port $Port listening:" ([bool]$up) "PID:" ($up.OwningProcess)
Write-Host "== NOTE: if this MCP server uses stdio transport instead of HTTP, the port"
Write-Host "==       check above will never pass -- check 'Get-Service $Svc' status and"
Write-Host "==       the log at $Log instead."
Write-Host "== DONE =="
Stop-Transcript | Out-Null
