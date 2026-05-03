<#
.SYNOPSIS
    Reconcile and sync skills across all known local locations.

.DESCRIPTION
    1. Checks non-master mirrors for .md files newer than the last git commit.
    2. Reports potential local promotions (skill files edited outside master).
    3. Diff/merge them back to master before overwriting.
    4. Syncs master -> all local mirrors via robocopy /MIR.
    5. Provides WinSCP guidance for the remote server.

    Tracked scope: root-level .md files + all */SKILL.md + all *.md in skill subdirs.
    Master copy: C:\Users\user\Documents\dev\skills

.PARAMETER Force
    Skip reconciliation, just sync master -> mirrors.

.PARAMETER DryRun
    Report what would be done without making any changes.

.EXAMPLE
    .\sync_skills.ps1
    .\sync_skills.ps1 -DryRun
    .\sync_skills.ps1 -Force
#>
param(
    [switch]$Force,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Configuration ────────────────────────────────────────────────────────────
$Master  = "C:\Users\user\Documents\dev\skills"
$Mirrors = @(
    "C:\Users\user\.copilot\skills",
    "C:\Users\user\.config\opencode\skills"
)
$RemoteUser = "root"
$RemoteHost = "192.168.3.17"
$RemotePath = "/root/.copilot/skills"

# Root-level files to track (relative names)
$RootTracked = @("README.md", "copilot-instructions.md", "MEMORY_SKILLS_PLAN.md", "AGENTS.md")

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Header($msg) {
    Write-Host "`n$('─' * 60)" -ForegroundColor DarkGray
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "$('─' * 60)" -ForegroundColor DarkGray
}

function Get-TrackedFiles($root) {
    $files = [System.Collections.Generic.List[string]]::new()
    if (-not (Test-Path $root)) { return $files }

    # Root-level tracked files
    foreach ($name in $RootTracked) {
        $p = Join-Path $root $name
        if (Test-Path $p) { $files.Add($p) }
    }

    # All .md files inside skill subdirectories (1 level deep)
    Get-ChildItem $root -Directory | ForEach-Object {
        Get-ChildItem $_.FullName -Filter "*.md" -File -ErrorAction SilentlyContinue | ForEach-Object {
            $files.Add($_.FullName)
        }
    }
    return $files
}

function Get-RelPath($file, $base) {
    $file.Substring($base.TrimEnd('\').Length).TrimStart('\')
}

function Show-Diff($masterFile, $mirrorFile) {
    # git diff --no-index gives a unified diff without needing a repo
    $diff = git diff --no-index --unified=3 -- $masterFile $mirrorFile 2>&1
    if ($diff) {
        # Show at most 80 lines to avoid flooding
        $diff | Select-Object -First 80 | Write-Host -ForegroundColor DarkYellow
        $lineCount = @($diff).Count
        if ($lineCount -gt 80) {
            Write-Host "  ... ($($lineCount - 80) more lines)" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "  (no diff output)" -ForegroundColor DarkGray
    }
}

# ── Step 1: Last commit timestamp ─────────────────────────────────────────────
Write-Header "Reading last commit timestamp"
$lastCommitStr = git -C $Master log -1 --format="%ci" 2>$null
if (-not $lastCommitStr) {
    Write-Warning "Cannot read git log from $Master -- treating all mirror files as potentially new."
    $lastCommit = [datetime]::MinValue
} else {
    $lastCommit = [datetime]::Parse($lastCommitStr.Trim())
}
Write-Host "  Last commit : $lastCommit"
Write-Host "  Master      : $Master"
if ($DryRun) { Write-Host "  [DRY RUN -- no changes will be made]" -ForegroundColor Magenta }

# ── Step 2: Detect new skill folders in mirrors not in master ─────────────────
Write-Header "Checking for skill folders missing from master"
$newFolders = [System.Collections.Generic.List[hashtable]]::new()

foreach ($mirror in $Mirrors) {
    if (-not (Test-Path $mirror)) { continue }
    Get-ChildItem $mirror -Directory | ForEach-Object {
        $rel = $_.Name
        $masterCounterpart = Join-Path $Master $rel
        if (-not (Test-Path $masterCounterpart)) {
            $newFolders.Add(@{ Mirror = $mirror; MirrorLabel = (Split-Path $mirror -Leaf); FolderName = $rel; FullPath = $_.FullName })
            Write-Host "  [NEW FOLDER] $rel  <- $mirror" -ForegroundColor Yellow
        }
    }
}
if ($newFolders.Count -eq 0) { Write-Host "  None." -ForegroundColor Green }

# ── Step 3: Detect locally-modified tracked files ─────────────────────────────
Write-Header "Checking tracked .md files newer than last commit"
$needsMerge = [System.Collections.Generic.List[hashtable]]::new()

foreach ($mirror in $Mirrors) {
    if (-not (Test-Path $mirror)) {
        Write-Host "  [MISSING] $mirror" -ForegroundColor DarkGray
        continue
    }
    $mirrorFiles = Get-TrackedFiles $mirror
    $count = 0
    foreach ($mf in $mirrorFiles) {
        $rel          = Get-RelPath $mf $mirror
        $masterFile   = Join-Path $Master $rel
        $mfTime       = (Get-Item $mf).LastWriteTime

        if ($mfTime -gt $lastCommit) {
            $masterContent = if (Test-Path $masterFile) { Get-Content $masterFile -Raw } else { $null }
            $mirrorContent = Get-Content $mf -Raw
            if ($masterContent -ne $mirrorContent) {
                $count++
                Write-Host ("  [NEWER] {0,-55} {1}" -f $rel, $mfTime.ToString("yyyy-MM-dd HH:mm")) -ForegroundColor Yellow
                $needsMerge.Add(@{
                    Mirror      = $mirror
                    MirrorLabel = Split-Path $mirror -Leaf
                    Rel         = $rel
                    MirrorFile  = $mf
                    MasterFile  = $masterFile
                    MirrorTime  = $mfTime
                    MasterExists = (Test-Path $masterFile)
                })
            }
        }
    }
    if ($count -eq 0) { Write-Host "  [OK] $mirror -- no locally-modified files" -ForegroundColor Green }
}

# ── Step 4: Reconciliation ────────────────────────────────────────────────────
$pendingFolderCopies = @()

if (($needsMerge.Count -gt 0 -or $newFolders.Count -gt 0) -and -not $Force) {
    Write-Header "Reconciliation"

    # Handle new folders first
    if ($newFolders.Count -gt 0) {
        Write-Host "`nNew skill folders found in mirrors (not in master):" -ForegroundColor Yellow
        foreach ($item in $newFolders) {
            Write-Host "  [$($item.MirrorLabel)] $($item.FolderName)" -ForegroundColor Yellow
        }
        $resp = Read-Host "`nCopy these new folders to master? [y/n/d=show contents first] (default: d)"
        if ($resp -eq '') { $resp = 'd' }
        foreach ($item in $newFolders) {
            if ($resp -eq 'd') {
                Write-Host "`n  Contents of $($item.FolderName):" -ForegroundColor Cyan
                Get-ChildItem $item.FullPath | ForEach-Object { Write-Host "    $($_.Name)" }
                $choice = Read-Host "  Copy '$($item.FolderName)' to master? [y/n]"
                if ($choice -eq 'y') { $pendingFolderCopies += $item }
            } elseif ($resp -eq 'y') {
                $pendingFolderCopies += $item
            }
        }
    }

    # Handle modified files
    if ($needsMerge.Count -gt 0) {
        Write-Host "`n$($needsMerge.Count) tracked file(s) in mirrors are newer than last commit and differ from master." -ForegroundColor Yellow
        $resp = Read-Host "How to handle? [y=copy all to master / n=skip all / d=diff each] (default: d)"
        if ($resp -eq '') { $resp = 'd' }

        foreach ($item in $needsMerge) {
            if ($resp -eq 'y') {
                if (-not $DryRun) {
                    $parent = Split-Path $item.MasterFile -Parent
                    if (-not (Test-Path $parent)) { New-Item $parent -ItemType Directory -Force | Out-Null }
                    Copy-Item $item.MirrorFile $item.MasterFile -Force
                }
                Write-Host "  Copied : $($item.Rel)" -ForegroundColor Green
            } elseif ($resp -eq 'd') {
                Write-Host "`n[$($item.MirrorLabel)] $($item.Rel)  (mirror: $($item.MirrorTime.ToString('yyyy-MM-dd HH:mm')))" -ForegroundColor Cyan
                if (-not $item.MasterExists) {
                    Write-Host "  [NEW FILE -- does not exist in master]" -ForegroundColor Magenta
                }
                Show-Diff $item.MasterFile $item.MirrorFile
                $choice = Read-Host "  Copy to master? [y/n]"
                if ($choice -eq 'y') {
                    if (-not $DryRun) {
                        $parent = Split-Path $item.MasterFile -Parent
                        if (-not (Test-Path $parent)) { New-Item $parent -ItemType Directory -Force | Out-Null }
                        Copy-Item $item.MirrorFile $item.MasterFile -Force
                    }
                    Write-Host "  Copied : $($item.Rel)" -ForegroundColor Green
                } else {
                    Write-Host "  Skipped: $($item.Rel)" -ForegroundColor DarkGray
                }
            } else {
                Write-Host "  Skipped all." -ForegroundColor DarkGray
                break
            }
        }
    }

    # Apply folder copies
    foreach ($item in $pendingFolderCopies) {
        $dest = Join-Path $Master $item.FolderName
        if (-not $DryRun) {
            robocopy $item.FullPath $dest /E /NJH /NJS /NDL /NC /NS | Out-Null
        }
        Write-Host "  Copied folder: $($item.FolderName) -> master" -ForegroundColor Green
    }

    # Offer to commit any changes we just merged
    $masterStatus = git -C $Master status --short 2>$null
    if ($masterStatus) {
        Write-Host "`nMaster has uncommitted changes after merge:" -ForegroundColor Yellow
        Write-Host $masterStatus
        if (-not $DryRun) {
            $commit = Read-Host "Commit merged changes now? [y/n]"
            if ($commit -eq 'y') {
                git -C $Master add -A
                git -C $Master commit -m "Merge locally-promoted skills back to master`n`nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
                Write-Host "  Committed." -ForegroundColor Green
            }
        }
    }
} elseif ($needsMerge.Count -gt 0 -and $Force) {
    Write-Host "`n[Force] Skipping reconciliation for $($needsMerge.Count) newer file(s)." -ForegroundColor Yellow
}

# ── Step 5: Sync master -> local mirrors ──────────────────────────────────────
Write-Header "Syncing master -> local mirrors"

foreach ($mirror in $Mirrors) {
    Write-Host "  -> $mirror"
    if ($DryRun) {
        robocopy $Master $mirror /MIR /L /NJH /NJS /NDL /NC /NS /XD ".git" ".todo" /XF "*.pyc" 2>&1 |
            Where-Object { $_ -match '\S' } | Select-Object -First 20 | ForEach-Object { Write-Host "     $_" -ForegroundColor DarkGray }
    } else {
        robocopy $Master $mirror /MIR /NJH /NJS /NDL /NC /NS /XD ".git" ".todo" /XF "*.pyc" | Out-Null
        $rc = $LASTEXITCODE
        if ($rc -le 1) {
            Write-Host "     OK (exit $rc)" -ForegroundColor Green
        } else {
            Write-Host "     WARN: robocopy exit $rc" -ForegroundColor Yellow
        }
    }
}

# ── Step 6: Remote guidance ───────────────────────────────────────────────────
Write-Header "Remote: $RemoteUser@${RemoteHost}:$RemotePath"

Write-Host @"
  Option A — WinSCP CLI (if winscp.com is on PATH):
    winscp.com /command ``
      "open sftp://$RemoteUser@$RemoteHost" ``
      "synchronize remote `"$Master`" $RemotePath" ``
      "exit"

  Option B — rsync (via WSL or Git Bash):
    rsync -avz --delete "$($Master.Replace('\','/'))" $RemoteUser@${RemoteHost}:$RemotePath

  Option C — Manual WinSCP:
    Host    : $RemoteHost
    User    : $RemoteUser
    Remote  : $RemotePath
    Local   : $Master
    Mode    : Mirror (remote = local, delete extras)
"@ -ForegroundColor DarkGray

$launch = Read-Host "`nLaunch WinSCP now? [y/n]"
if ($launch -eq 'y') {
    $inputUser = Read-Host "  SSH username (default: $RemoteUser)"
    if ($inputUser -ne '') { $RemoteUser = $inputUser }
    $securePwd  = Read-Host "  SSH password" -AsSecureString
    $plainPwd   = [System.Net.NetworkCredential]::new('', $securePwd).Password

    $wscp = Get-Command "winscp.com" -ErrorAction SilentlyContinue
    if ($wscp) {
        Write-Host "  Launching WinSCP..." -ForegroundColor Green
        & winscp.com /command `
            "open sftp://${RemoteUser}:${plainPwd}@$RemoteHost" `
            "synchronize remote `"$Master`" $RemotePath" `
            "exit"
    } else {
        Write-Host "  winscp.com not found on PATH. Open WinSCP manually and sync:" -ForegroundColor Yellow
        Write-Host "    $Master  -->  $RemoteUser@${RemoteHost}:$RemotePath"
    }
}

Write-Header "Done"
if ($DryRun) { Write-Host "  [DRY RUN - no changes were made]" -ForegroundColor Magenta }
