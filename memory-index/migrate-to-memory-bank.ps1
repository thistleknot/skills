<#
  migrate-to-memory-bank.ps1 - relocate the harness memory to the global ~\memory-bank
  store and re-point the mem-chroma service at it. Run ELEVATED (service ops need admin).

  What it does (one coherent flip):
    1. stop + remove the current mem-chroma service (releases the old .chroma)
    2. move the atomic memory files (MEMORY.md + *.md) from the harness project dir
       into ~\memory-bank  (the big Memory Bank docs already live there)
    3. replace the harness project memory dir with a DIRECTORY JUNCTION -> ~\memory-bank
       so the harness's auto-saved memories + MEMORY.md context-load use the global store
    4. re-register + start mem-chroma pointing at ~\memory-bank\.chroma
    5. index everything (atomic memories whole; big docs chunked) via mem.py

  REVERSIBLE: delete the junction (`(Get-Item $HarnessDir).Delete()`), recreate a real
  dir, and move the atomic .md files back. The Memory Bank docs are never modified.

  NOTE: after this runs, mem.py's default dir (the harness path) resolves THROUGH the
  junction to ~\memory-bank, so no code change is needed - service + tool + harness agree.
#>
param(
  [string]$MemBank    = 'C:\Users\user\memory-bank',
  [string]$HarnessDir = 'C:\Users\user\.claude\projects\C--Users-user-Documents-dev-skills\memory',
  [string]$BindHost   = '127.0.0.1',
  [int]   $Port       = 8055
)

$ErrorActionPreference = 'Stop'
$app   = $PSScriptRoot
New-Item -ItemType Directory -Force (Join-Path $app 'logs') | Out-Null
Start-Transcript -Path (Join-Path $app 'logs\migrate-to-memory-bank.log') -Force | Out-Null

$nssm   = 'C:\Users\user\.pi\bin\nssm.exe'
$chroma = 'C:\Users\user\py310\Scripts\chroma.exe'
$py     = 'C:\Users\user\py310\Scripts\python.exe'
$svc    = 'mem-chroma'
$store  = Join-Path $MemBank '.chroma'
$svclog = Join-Path $app 'logs\mem-chroma.service.log'

if (-not (Test-Path $MemBank)) { New-Item -ItemType Directory -Force $MemBank | Out-Null }

# guard: if the harness dir is ALREADY a junction, skip the move/junction steps
$harnessItem = Get-Item $HarnessDir -ErrorAction SilentlyContinue
$alreadyLinked = $harnessItem -and $harnessItem.LinkType -eq 'Junction'
Write-Host "harness dir already junction: $alreadyLinked"

# 1. stop + remove the service so nothing holds the old .chroma
& $nssm stop   $svc 2>$null
& $nssm remove $svc confirm 2>$null
Start-Sleep -Seconds 2

if (-not $alreadyLinked) {
    # 2. move atomic memories into memory-bank (no overwrite of existing files)
    Get-ChildItem $HarnessDir -File -Filter *.md | ForEach-Object {
        $dest = Join-Path $MemBank $_.Name
        if (Test-Path $dest) { Write-Warning "exists, skipping: $($_.Name)" }
        else { Move-Item $_.FullName $dest; Write-Host "moved $($_.Name)" }
    }
    # 3. drop the old dir (incl. stale .chroma) and junction it to memory-bank
    Remove-Item $HarnessDir -Recurse -Force
    New-Item -ItemType Junction -Path $HarnessDir -Target $MemBank | Out-Null
    Write-Host "junction: $HarnessDir -> $MemBank"
}

# 4. re-register the service at memory-bank
New-Item -ItemType Directory -Force $store | Out-Null
& $nssm install $svc $chroma
& $nssm set $svc AppParameters "run --path `"$store`" --host $BindHost --port $Port"
& $nssm set $svc AppDirectory $MemBank
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
& $nssm set $svc DisplayName 'Memory Vector Store (chroma, ~\memory-bank)'
& $nssm set $svc Description "Global harness memory index on ${BindHost}:${Port} over ~\memory-bank."
& $nssm start $svc
Start-Sleep -Seconds 3

try {
    $hb = Invoke-RestMethod -Uri "http://${BindHost}:${Port}/api/v2/heartbeat" -TimeoutSec 5
    Write-Host "heartbeat OK: $($hb | ConvertTo-Json -Compress)"
} catch { Write-Warning "heartbeat failed - check $svclog" }

# 5. index everything into the new store (atomic whole; big docs chunked)
Write-Host "indexing ~\memory-bank (big docs are chunked; this can take a minute)..."
$env:MEM_DIR = $MemBank
& $py (Join-Path $app 'mem.py') index

Get-Service $svc | Format-List Name, Status, StartType
Write-Host "done."
Stop-Transcript | Out-Null
