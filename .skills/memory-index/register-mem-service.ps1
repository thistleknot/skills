<#
  register-mem-service.ps1 - installs the memory vector store (chroma) as an NSSM service.
  Mirrors phone-storage-guard / litellm-windows-service conventions
  (auto-start, restart-on-exit, rotating logs). Run ELEVATED (nssm install/start needs admin).

  The service OWNS the Chroma store so many sessions/agents query it concurrently without
  SQLite lock contention. mem.py auto-connects to it (falls back to the local file if down).
  Nothing else needs to start it.
#>
$app = $PSScriptRoot
New-Item -ItemType Directory -Force (Join-Path $app 'logs') | Out-Null
Start-Transcript -Path (Join-Path $app 'logs\register-mem-service.log') -Force | Out-Null

# --- config (must match mem.py MEM_CHROMA_* / MEM_DIR) -----------------------
# To make memory GLOBAL across all projects, point $MemDir at a shared dir (e.g.
# 'C:\Users\user\.claude\memory') and set MEM_DIR to the same for every agent.
$MemDir  = 'C:\Users\user\.claude\projects\C--Users-user-Documents-dev-skills\memory'
$Host_   = '127.0.0.1'
$Port    = 8055

$nssm    = 'C:\Users\user\.pi\bin\nssm.exe'
$svc     = 'mem-chroma'
$chroma  = 'C:\Users\user\py310\Scripts\chroma.exe'
$store   = Join-Path $MemDir '.chroma'
$svclog  = Join-Path $app 'logs\mem-chroma.service.log'

New-Item -ItemType Directory -Force $store | Out-Null

# clean any prior instance
& $nssm stop $svc 2>$null
& $nssm remove $svc confirm 2>$null

# install + configure
& $nssm install $svc $chroma
& $nssm set $svc AppParameters "run --path `"$store`" --host $Host_ --port $Port"
& $nssm set $svc AppDirectory $MemDir
& $nssm set $svc AppEnvironmentExtra 'HOME=C:\Users\user' 'USERPROFILE=C:\Users\user' 'ANONYMIZED_TELEMETRY=False'
& $nssm set $svc AppStdout $svclog
& $nssm set $svc AppStderr $svclog
& $nssm set $svc AppRotateFiles 1
& $nssm set $svc AppRotateOnline 1
& $nssm set $svc AppRotateBytes 5242880
& $nssm set $svc Start SERVICE_AUTO_START
& $nssm set $svc AppExit Default Restart
& $nssm set $svc AppRestartDelay 3000
& $nssm set $svc AppThrottle 5000
& $nssm set $svc DisplayName 'Memory Vector Store (chroma)'
& $nssm set $svc Description "Serves the harness memory embed-and-retrieve index on ${Host_}:${Port}. Owned store; mem.py clients connect here."

# start + verify
& $nssm start $svc
Start-Sleep -Seconds 3
Get-Service $svc | Format-List Name, Status, StartType
try {
    $hb = Invoke-RestMethod -Uri "http://${Host_}:${Port}/api/v2/heartbeat" -TimeoutSec 5
    Write-Host "heartbeat OK: $($hb | ConvertTo-Json -Compress)"
} catch {
    Write-Warning "service started but heartbeat failed - check $svclog"
}
Write-Host "done."
Stop-Transcript | Out-Null
