# register-service.ps1 — Run elevated to register skill-router as a Windows Service.
# Usage: Start-Process pwsh -Verb RunAs -ArgumentList "-File C:\Users\user\.skills\retrieve-skills\register-service.ps1"
#
# Creates NSSM service "skill-router" with:
# - Auto-start on boot
# - Auto-restart on crash (5s delay)
# - SSLKEYLOGFILE cleared (Avast workaround)
# - HF_HUB_OFFLINE=1 (no network calls after first model cache)

$ErrorActionPreference = "Stop"
$nssm = "C:\Users\user\.pi\bin\nssm.exe"
$serviceName = "skill-router"
$python = "F:\Python\mcp\retrieve-skills\Scripts\python.exe"
$appDir = "C:\Users\user\.skills\retrieve-skills"

# Remove old if exists
& $nssm stop $serviceName 2>$null
& $nssm remove $serviceName confirm 2>$null
Start-Sleep -Seconds 2

# Install service
& $nssm install $serviceName $python "server.py"
& $nssm set $serviceName AppDirectory $appDir
& $nssm set $serviceName AppEnvironmentExtra @"
PYTHONIOENCODING=utf-8
PYTHONUTF8=1
SSLKEYLOGFILE=
SKILL_STORE=C:\Users\user\.skills
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HOME=C:\Users\user
USERPROFILE=C:\Users\user
HF_HOME=F:\hf_cache\huggingface
"@
& $nssm set $serviceName AppExit Default Restart
& $nssm set $serviceName AppRestartDelay 5000
& $nssm set $serviceName AppStdout "$appDir\service_stdout.log"
& $nssm set $serviceName AppStderr "$appDir\service_stderr.log"
& $nssm set $serviceName AppStdoutCreationDisposition 4
& $nssm set $serviceName AppStderrCreationDisposition 4
& $nssm set $serviceName AppRotateFiles 1
& $nssm set $serviceName AppRotateBytes 5242880
& $nssm set $serviceName DisplayName "Skill Router MCP"
& $nssm set $serviceName Description "Retrieve-skills MCP server on :8765. Auto-restarts on failure."
& $nssm set $serviceName Start SERVICE_AUTO_START

# Start it
& $nssm start $serviceName

Write-Host "`n=== Service registered and started ===" -ForegroundColor Green
Write-Host "Name: $serviceName"
Write-Host "Port: 8765"
Write-Host "Logs: $appDir\service_stderr.log"
Write-Host "`nVerify: Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing"
