# Registers a LiteLLM proxy as an auto-start, auto-restart Windows service via NSSM.
# Run ELEVATED (admin). Idempotent. Self-logs via transcript so results are readable
# even when launched with `Start-Process -Verb RunAs -ArgumentList '-File', <this>`.
#
# Adjust the five paths/port below for your machine, then run elevated.
$Nssm      = "$HOME\.pi\bin\nssm.exe"
$LiteLLM   = "$HOME\py310\Scripts\litellm.exe"          # the console-script entry (self-invokes python)
$Config    = "$HOME\.pi\litellm_config.yaml"
$Port      = 4000
$Log       = "$HOME\.pi\tmp\litellm-service.log"
$Svc       = 'litellm'

$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null
try { Stop-Transcript | Out-Null } catch {}
Start-Transcript -Path "$HOME\.pi\tmp\register-result.log" -Force | Out-Null

Write-Host "== whoami:" (whoami)
Write-Host "== is admin:" ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# Free the port: stop any manual instance holding it.
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Host "== stopping port holder PID $($_.OwningProcess)"; Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

# Clean slate (safe if service doesn't exist yet).
& $Nssm stop   $Svc 2>&1 | Write-Host
& $Nssm remove $Svc confirm 2>&1 | Write-Host

# Install + configure.
& $Nssm install $Svc $LiteLLM 2>&1 | Write-Host
& $Nssm set $Svc AppParameters "--config $Config --port $Port" 2>&1 | Write-Host
& $Nssm set $Svc AppDirectory (Split-Path $Config) 2>&1 | Write-Host
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
& $Nssm set $Svc DisplayName 'LiteLLM Proxy' 2>&1 | Write-Host
& $Nssm set $Svc Description 'OpenAI-compatible local model gateway' 2>&1 | Write-Host

# Start + verify (litellm binds the port ~10-20s AFTER the service reports Running).
& $Nssm start $Svc 2>&1 | Write-Host
Write-Host "== service:" (Get-Service $Svc | Select-Object -Expand Status)
for ($i=0; $i -lt 12; $i++) {
    $up = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($up) { break }; Start-Sleep 3
}
Write-Host "== port $Port listening:" ([bool]$up) "PID:" ($up.OwningProcess)
Write-Host "== DONE =="
Stop-Transcript | Out-Null
