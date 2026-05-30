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

.PARAMETER OverwriteDownstream
    Require a clean master worktree, skip mirror->master reconciliation, and
    treat master as the source of truth when syncing downstream targets.

.PARAMETER DryRun
    Report what would be done without making any changes.

.PARAMETER Username
    SSH username to use for the remote WinSCP launch step.

.PARAMETER Password
    SSH password to use for the remote WinSCP launch step.

.PARAMETER Yes
    Auto-confirm interactive yes/no prompts so the script can be re-run non-interactively.

.EXAMPLE
    .\sync_skills.ps1
    .\sync_skills.ps1 -DryRun
    .\sync_skills.ps1 -Force
    .\sync_skills.ps1 -OverwriteDownstream -y
    .\sync_skills.ps1 -Username root -Password hunter2 -y
#>
param(
    [switch]$Force,
    [switch]$OverwriteDownstream,
    [switch]$DryRun,
    [string]$Username,
    [string]$Password,
    [Alias('y')][switch]$Yes
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

if ($Username) {
    $RemoteUser = $Username
}

# Root-level files to track (relative names)
$RootTracked = @("README.md", "copilot-instructions.md", "MEMORY_SKILLS_PLAN.md", "AGENTS.md")

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Header($msg) {
    Write-Host "`n$('-' * 60)" -ForegroundColor DarkGray
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "$('-' * 60)" -ForegroundColor DarkGray
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

# Normalize line endings to LF only to prevent false conflicts on Windows.
function Normalize-LineEndings([string]$text) {
    if ($null -eq $text) { return $null }
    return $text -replace "`r`n", "`n" -replace "`r", "`n"
}

# Returns the base content of a tracked file at last commit, or $null if not tracked.
function Get-BaseContent($relPath) {
    # Check if file exists in HEAD before attempting git show
    # (files new on disk but not in HEAD would otherwise emit a stderr error record
    #  that collides with $ErrorActionPreference='Stop')
    $gitRelPath = $relPath.Replace('\', '/')
    $check = git -C $Master ls-tree HEAD -- $gitRelPath 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($check -join '').Trim())) {
        return $null
    }
    $base = git -C $Master show "HEAD:$gitRelPath" 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return (Normalize-LineEndings ($base -join "`n"))
}

function Test-PathEverTracked($relPath) {
    $gitRelPath = $relPath.Replace('\', '/')
    $history = git -C $Master log --format="%H" -1 -- $gitRelPath 2>$null
    return -not [string]::IsNullOrWhiteSpace(($history -join '').Trim())
}

# Classifies a (master, mirror) pair relative to the committed base.
# Returns: 'no-op' | 'fast-forward-mirror' | 'fast-forward-master' | 'conflict'
function Get-SyncCase($masterContent, $mirrorContent, $baseContent) {
    if ($null -eq $baseContent) {
        # File not in git yet — treat mirror as additive if it differs
        if ($masterContent -eq $mirrorContent) { return 'no-op' }
        return 'fast-forward-mirror'
    }
    $masterChanged = ($masterContent -ne $baseContent)
    $mirrorChanged = ($mirrorContent -ne $baseContent)
    if     (-not $masterChanged -and -not $mirrorChanged) { return 'no-op' }
    elseif (-not $masterChanged -and      $mirrorChanged) { return 'fast-forward-mirror' }
    elseif (     $masterChanged -and -not $mirrorChanged) { return 'fast-forward-master' }
    else                                                   { return 'conflict' }
}

# ReAct-style 3-way merge: tries up to 5 strategies in order.
# Returns merged content string on success, or $null if all 5 attempts fail.
# On failure, writes a .conflict diff file next to the master file for manual review.
function Invoke-LlmMerge($relPath, $baseContent, $masterContent, $mirrorContent) {
    $maxAttempts = 5
    $tmpBase   = [System.IO.Path]::GetTempFileName()
    $tmpMirror = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content $tmpBase   $baseContent   -Encoding UTF8 -NoNewline
        Set-Content $tmpMirror $mirrorContent -Encoding UTF8 -NoNewline

        for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
            $tmpMaster = [System.IO.Path]::GetTempFileName()
            Set-Content $tmpMaster $masterContent -Encoding UTF8 -NoNewline

            Write-Host "  [MERGE] Attempt $attempt/$maxAttempts for $relPath" -ForegroundColor Cyan

            switch ($attempt) {
                1 {
                    # Standard 3-way merge
                    git merge-file -q $tmpMaster $tmpBase $tmpMirror 2>&1 | Out-Null
                }
                2 {
                    # Union merge — include both sides verbatim for conflict regions
                    git merge-file -q --union $tmpMaster $tmpBase $tmpMirror 2>&1 | Out-Null
                }
                3 {
                    # Prefer mirror (theirs) for all conflict sections
                    git merge-file -q $tmpMaster $tmpBase $tmpMirror 2>&1 | Out-Null
                    $candidate = Get-Content $tmpMaster -Raw -Encoding UTF8
                    $resolved = $candidate -replace '(?ms)<<<<<<< [^\n]*\n.*?=======\n(.*?)>>>>>>> [^\n]*\n', '$1'
                    Set-Content $tmpMaster $resolved -Encoding UTF8 -NoNewline
                }
                4 {
                    # Prefer master (ours) for all conflict sections
                    git merge-file -q $tmpMaster $tmpBase $tmpMirror 2>&1 | Out-Null
                    $candidate = Get-Content $tmpMaster -Raw -Encoding UTF8
                    $resolved = $candidate -replace '(?ms)<<<<<<< [^\n]*\n(.*?)=======\n.*?>>>>>>> [^\n]*\n', '$1'
                    Set-Content $tmpMaster $resolved -Encoding UTF8 -NoNewline
                }
                5 {
                    # Last resort: union then strip all remaining conflict markers
                    git merge-file -q --union $tmpMaster $tmpBase $tmpMirror 2>&1 | Out-Null
                    $candidate = Get-Content $tmpMaster -Raw -Encoding UTF8
                    $resolved = $candidate -replace '(?ms)(<<<<<<< [^\n]*\n|=======\n|>>>>>>> [^\n]*\n)', ''
                    Set-Content $tmpMaster $resolved -Encoding UTF8 -NoNewline
                }
            }

            $mergedContent = Get-Content $tmpMaster -Raw -Encoding UTF8
            Remove-Item $tmpMaster -Force -ErrorAction SilentlyContinue

            if ($mergedContent -notmatch '<<<<<<< ') {
                $label = if ($attempt -eq 1) { 'Clean 3-way merge' } else { "Resolved on attempt $attempt/$maxAttempts" }
                Write-Host "  [MERGE] $label : $relPath" -ForegroundColor Green
                return $mergedContent
            }

            Write-Host "  [MERGE] Conflict markers remain after attempt $attempt/$maxAttempts" -ForegroundColor Yellow
        }

        # All 5 attempts exhausted — write conflict artifact and report to user
        Write-Host "  [MERGE ERROR] $relPath -- all $maxAttempts attempts failed. Manual merge required." -ForegroundColor Red
        $diffOut = git -c core.autocrlf=false diff --no-index --unified=3 -- $tmpBase $tmpMirror 2>&1 |
                   Where-Object { $_ -notmatch '^warning:' } | Out-String
        $conflictFile = (Join-Path $PSScriptRoot $relPath) + '.conflict'
        $conflictContent = "# MANUAL MERGE REQUIRED: $relPath`n# Apply the mirror diff below onto the master copy, then delete this file.`n#`n$diffOut"
        Set-Content $conflictFile $conflictContent -Encoding UTF8
        Write-Host "  Conflict diff written to: $conflictFile" -ForegroundColor Red
        return $null

    } finally {
        Remove-Item $tmpBase, $tmpMirror -Force -ErrorAction SilentlyContinue
    }
}

function Read-Choice($Prompt, $Default = '', $AutoYesChoice = 'y') {
    if ($Yes) {
        Write-Host "  [AUTO] $Prompt -> $AutoYesChoice" -ForegroundColor DarkGray
        return $AutoYesChoice
    }

    $response = Read-Host $Prompt
    if ([string]::IsNullOrWhiteSpace($response)) {
        return $Default
    }

    return $response.Trim().ToLowerInvariant()
}

function Get-GitStatusLines($repoPath) {
    $status = git -C $repoPath status --porcelain 2>$null
    if ($LASTEXITCODE -ne 0) {
        return [string[]]@()
    }

    return [string[]]@($status | Where-Object { $_ -match '\S' })
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
$masterStatusAtStart = @(Get-GitStatusLines $Master)
$masterIsClean = ($masterStatusAtStart.Length -eq 0)
$skipReconciliation = ($Force -or $OverwriteDownstream)

if ($OverwriteDownstream -and -not $masterIsClean) {
    throw "OverwriteDownstream requires a clean master worktree. Commit, stash, or discard local changes first."
}

Write-Host "  Last commit : $lastCommit"
Write-Host "  Master      : $Master"
Write-Host "  Master clean: $(if ($masterIsClean) { 'yes' } else { 'no' })"
if ($Force) {
    Write-Host "  Mode        : force (skip reconciliation; sync master -> mirrors)" -ForegroundColor Yellow
}
if ($OverwriteDownstream) {
    Write-Host "  Mode        : overwrite downstream (clean master is source of truth)" -ForegroundColor Yellow
}
if ($DryRun) { Write-Host "  [DRY RUN -- no changes will be made]" -ForegroundColor Magenta }

# ── Step 2: Detect new skill folders in mirrors not in master ─────────────────
Write-Header "Checking for skill folders missing from master"
$newFolders = [System.Collections.Generic.List[hashtable]]::new()
$staleFolders = [System.Collections.Generic.List[hashtable]]::new()
$seenFolderNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

if ($skipReconciliation) {
    Write-Host "  [SKIP] Reconciliation disabled in current mode; master will be pushed downstream." -ForegroundColor DarkGray
} else {
    foreach ($mirror in $Mirrors) {
        if (-not (Test-Path $mirror)) { continue }
        Get-ChildItem $mirror -Directory | ForEach-Object {
            $rel = $_.Name
            $masterCounterpart = Join-Path $Master $rel
            if (-not (Test-Path $masterCounterpart)) {
                if (-not $seenFolderNames.Add($rel)) {
                    Write-Host "  [DUPLICATE MIRROR] $rel  <- $mirror (already recorded from another mirror)" -ForegroundColor DarkGray
                    return
                }

                $entry = @{
                    Mirror = $mirror
                    MirrorLabel = (Split-Path $mirror -Leaf)
                    FolderName = $rel
                    FullPath = $_.FullName
                }

                if (Test-PathEverTracked $rel) {
                    $staleFolders.Add($entry)
                    Write-Host "  [STALE MIRROR] $rel  <- $mirror (path exists in git history but is absent in master)" -ForegroundColor Magenta
                } else {
                    $newFolders.Add($entry)
                    Write-Host "  [NEW FOLDER] $rel  <- $mirror" -ForegroundColor Yellow
                }
            }
        }
    }
    if ($newFolders.Count -eq 0 -and $staleFolders.Count -eq 0) { Write-Host "  None." -ForegroundColor Green }
}

# ── Step 3: Detect locally-modified tracked files ─────────────────────────────
Write-Header "Checking tracked .md files newer than last commit"
$needsMerge = [System.Collections.Generic.List[hashtable]]::new()

if ($skipReconciliation) {
    Write-Host "  [SKIP] Reconciliation disabled in current mode; downstream edits will not be promoted." -ForegroundColor DarkGray
} else {
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
                $masterContent = if (Test-Path $masterFile) { Normalize-LineEndings (Get-Content $masterFile -Raw) } else { $null }
                $mirrorContent = Normalize-LineEndings (Get-Content $mf -Raw)
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
}

# ── Step 4: Reconciliation ────────────────────────────────────────────────────
$pendingFolderCopies = @()
$touchedPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

if (($needsMerge.Count -gt 0 -or $newFolders.Count -gt 0 -or $staleFolders.Count -gt 0) -and -not $skipReconciliation) {
    Write-Header "Reconciliation"

    # Handle stale mirror folders first
    if ($staleFolders.Count -gt 0) {
        Write-Host "`nMirror-only skill folders with prior git history (likely stale, not new):" -ForegroundColor Magenta
        foreach ($item in $staleFolders) {
            Write-Host "  [$($item.MirrorLabel)] $($item.FolderName)" -ForegroundColor Magenta
        }
        $resp = Read-Choice "`nRestore these stale mirror folders into master? [y/n/d=show contents first] (default: n)" 'n' 'y'
        foreach ($item in $staleFolders) {
            if ($resp -eq 'd') {
                Write-Host "`n  Contents of stale mirror folder $($item.FolderName):" -ForegroundColor Cyan
                Get-ChildItem $item.FullPath | ForEach-Object { Write-Host "    $($_.Name)" }
                $choice = Read-Choice "  Restore '$($item.FolderName)' to master? [y/n]" '' 'y'
                if ($choice -eq 'y') { $pendingFolderCopies += $item }
            } elseif ($resp -eq 'y') {
                $pendingFolderCopies += $item
            }
        }
    }

    # Handle truly new folders next
    if ($newFolders.Count -gt 0) {
        Write-Host "`nNew skill folders found in mirrors (not in master):" -ForegroundColor Yellow
        foreach ($item in $newFolders) {
            Write-Host "  [$($item.MirrorLabel)] $($item.FolderName)" -ForegroundColor Yellow
        }
        $resp = Read-Choice "`nCopy these new folders to master? [y/n/d=show contents first] (default: d)" 'd' 'y'
        foreach ($item in $newFolders) {
            if ($resp -eq 'd') {
                Write-Host "`n  Contents of $($item.FolderName):" -ForegroundColor Cyan
                Get-ChildItem $item.FullPath | ForEach-Object { Write-Host "    $($_.Name)" }
                $choice = Read-Choice "  Copy '$($item.FolderName)' to master? [y/n]" '' 'y'
                if ($choice -eq 'y') { $pendingFolderCopies += $item }
            } elseif ($resp -eq 'y') {
                $pendingFolderCopies += $item
            }
        }
    }

    # Handle modified files — with skill-sync case classification
    if ($needsMerge.Count -gt 0) {

        # Pre-classify each item so the user sees a summary before deciding
        $conflicts    = [System.Collections.Generic.List[hashtable]]::new()
        $fastForwards = [System.Collections.Generic.List[hashtable]]::new()
        foreach ($item in $needsMerge) {
            $baseContent   = Get-BaseContent $item.Rel
            $masterContent = if ($item.MasterExists) { Normalize-LineEndings (Get-Content $item.MasterFile -Raw) } else { $null }
            $mirrorContent = Normalize-LineEndings (Get-Content $item.MirrorFile -Raw)
            $case = Get-SyncCase $masterContent $mirrorContent $baseContent
            $item['SyncCase']    = $case
            $item['BaseContent'] = $baseContent
            if ($case -eq 'conflict') { $conflicts.Add($item) } else { $fastForwards.Add($item) }
        }

        $ffCount  = $fastForwards.Count
        $cfCount  = $conflicts.Count
        Write-Host "`n$($needsMerge.Count) tracked file(s) differ from master:" -ForegroundColor Yellow
        Write-Host "  Fast-forward (mirror additive): $ffCount" -ForegroundColor Cyan
        Write-Host "  Conflict (both sides diverged): $cfCount" -ForegroundColor Magenta

        $resp = Read-Choice "How to handle? [y=auto-apply all / n=skip all / d=review each] (default: d)" 'd' 'y'

        # Helper: write content to master file
        function Write-ToMaster($item, $content) {
            if (-not $DryRun) {
                $parent = Split-Path $item.MasterFile -Parent
                if (-not (Test-Path $parent)) { New-Item $parent -ItemType Directory -Force | Out-Null }
                Set-Content $item.MasterFile $content -Encoding UTF8 -NoNewline
                [void]$touchedPaths.Add($item.MasterFile)
            }
        }

        foreach ($item in $needsMerge) {
            if ($resp -eq 'n') {
                Write-Host "  Skipped all." -ForegroundColor DarkGray
                break
            }

            $syncCase      = $item['SyncCase']
            $baseContent   = $item['BaseContent']
            $masterContent = if ($item.MasterExists) { Normalize-LineEndings (Get-Content $item.MasterFile -Raw) } else { $null }
            $mirrorContent = Normalize-LineEndings (Get-Content $item.MirrorFile -Raw)

            $caseLabel = switch ($syncCase) {
                'fast-forward-mirror'  { '[FAST-FWD]' }
                'fast-forward-master'  { '[AHEAD]   ' }
                'conflict'             { '[CONFLICT]' }
                default                { '[NO-OP]   ' }
            }
            $caseColor = if ($syncCase -eq 'conflict') { 'Magenta' } else { 'Cyan' }

            if ($resp -eq 'y') {
                # Auto-apply: fast-forwards are deterministic; conflicts need LLM merge
                if ($syncCase -eq 'fast-forward-mirror') {
                    Write-ToMaster $item $mirrorContent
                    Write-Host "  $caseLabel Copied  : $($item.Rel)" -ForegroundColor Green
                } elseif ($syncCase -eq 'fast-forward-master') {
                    Write-Host "  $caseLabel Skipped : $($item.Rel) (master already ahead)" -ForegroundColor DarkGray
                } elseif ($syncCase -eq 'conflict') {
                    Write-Host "  $caseLabel $($item.Rel) -- invoking LLM merge" -ForegroundColor Magenta
                    $merged = Invoke-LlmMerge $item.Rel $baseContent $masterContent $mirrorContent
                    if ($null -ne $merged) {
                        Write-ToMaster $item $merged
                        Write-Host "  $caseLabel Merged  : $($item.Rel)" -ForegroundColor Green
                        if ($merged -match '<!--\s*MERGE-CONFLICT') {
                            Write-Host "  [WARN] MERGE-CONFLICT marker present - flag for human review before commit." -ForegroundColor Yellow
                        }
                    } else {
                        Write-Host "  $caseLabel Skipped : $($item.Rel) (manual merge required -- see .conflict file)" -ForegroundColor Red
                    }
                }
                continue
            }

            # Review mode (d): show case, then offer appropriate choices
            Write-Host "`n$caseLabel [$($item.MirrorLabel)] $($item.Rel)  (mirror: $($item.MirrorTime.ToString('yyyy-MM-dd HH:mm')))" -ForegroundColor $caseColor
            if (-not $item.MasterExists) {
                Write-Host "  [NEW FILE -- does not exist in master]" -ForegroundColor Magenta
            }

            if ($syncCase -eq 'conflict') {
                Write-Host "  Both master and mirror have changed since last commit." -ForegroundColor Magenta
                Show-Diff $item.MasterFile $item.MirrorFile
                $choice = Read-Choice "  Action? [y=copy mirror / m=llm-merge / n=skip / d=show full diff] (default: m)" 'm' 'm'
                if ($choice -eq 'd') {
                    Show-Diff $item.MasterFile $item.MirrorFile
                    $choice = Read-Choice "  Action? [y=copy mirror / m=llm-merge / n=skip] (default: m)" 'm' 'm'
                }
                if ($choice -eq 'y') {
                    Write-ToMaster $item $mirrorContent
                    Write-Host "  Copied mirror -> master (no merge): $($item.Rel)" -ForegroundColor Green
                } elseif ($choice -eq 'm') {
                    $merged = Invoke-LlmMerge $item.Rel $baseContent $masterContent $mirrorContent
                    if ($null -ne $merged) {
                        Write-ToMaster $item $merged
                        Write-Host "  Merged : $($item.Rel)" -ForegroundColor Green
                        if ($merged -match '<!--\s*MERGE-CONFLICT') {
                            Write-Host "  [WARN] MERGE-CONFLICT marker present - review before committing." -ForegroundColor Yellow
                        }
                    }
                } else {
                    Write-Host "  Skipped: $($item.Rel)" -ForegroundColor DarkGray
                }
            } else {
                # Fast-forward: simple copy prompt
                Show-Diff $item.MasterFile $item.MirrorFile
                $choice = Read-Choice "  Copy to master? [y/n]" '' 'y'
                if ($choice -eq 'y') {
                    Write-ToMaster $item $mirrorContent
                    Write-Host "  Copied : $($item.Rel)" -ForegroundColor Green
                } else {
                    Write-Host "  Skipped: $($item.Rel)" -ForegroundColor DarkGray
                }
            }
        }
    }

    # Apply folder copies
    foreach ($item in $pendingFolderCopies) {
        $dest = Join-Path $Master $item.FolderName
        if (-not $DryRun) {
            robocopy $item.FullPath $dest /E /NJH /NJS /NDL /NC /NS | Out-Null
            [void]$touchedPaths.Add($dest)
        }
        Write-Host "  Copied folder: $($item.FolderName) -> master" -ForegroundColor Green
    }

    # Offer to commit any changes we just merged
    $masterStatus = git -C $Master status --short 2>$null
    if ($masterStatus) {
        Write-Host "`nMaster has uncommitted changes after merge:" -ForegroundColor Yellow
        Write-Host $masterStatus
        if (-not $DryRun) {
            $commit = Read-Choice "Commit merged changes now? [y/n]" '' 'y'
            if ($commit -eq 'y') {
                if ($touchedPaths.Count -eq 0) {
                    Write-Host "  No reconciliation changes were applied; nothing to commit." -ForegroundColor DarkGray
                } else {
                    $pathsToStage = @($touchedPaths)
                    Write-Host "  Staging only reconciliation paths (unrelated worktree changes are left alone)." -ForegroundColor DarkGray
                    git -C $Master add -- $pathsToStage
                    $stagedPaths = git -C $Master diff --cached --name-only 2>$null
                    if ($stagedPaths) {
                        git -C $Master commit -m "Merge locally-promoted skills back to master`n`nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
                        Write-Host "  Committed." -ForegroundColor Green
                    } else {
                        Write-Host "  No reconciliation changes were staged; skipped commit." -ForegroundColor DarkGray
                    }
                }
            }
        }
    }
} elseif (($needsMerge.Count -gt 0 -or $newFolders.Count -gt 0 -or $staleFolders.Count -gt 0) -and $skipReconciliation) {
    Write-Host "`n[Skip] Reconciliation bypassed; master will overwrite downstream targets." -ForegroundColor Yellow
}

# ── Step 5: Sync master -> local mirrors ──────────────────────────────────────
Write-Header "Syncing master -> local mirrors"

foreach ($mirror in $Mirrors) {
    Write-Host "  -> $mirror"
    if ($DryRun) {
        robocopy $Master $mirror /MIR /L /NJH /NJS /NDL /NC /NS /XD ".git" ".todo" "__pycache__" ".pytest_cache" ".react_agent" /XF "*.pyc" "*.db" "*.jsonl" 2>&1 |
            Where-Object { $_ -match '\S' } | Select-Object -First 20 | ForEach-Object { Write-Host "     $_" -ForegroundColor DarkGray }
    } else {
        robocopy $Master $mirror /MIR /NJH /NJS /NDL /NC /NS /XD ".git" ".pytest_cache" ".todo" ".react_agent" "__pycache__" ".copilot" /XF "*.pyc" "*.db" "*.jsonl" | Out-Null
        $rc = $LASTEXITCODE
        if ($rc -le 1) {
            Write-Host "     OK (exit $rc)" -ForegroundColor Green
        } else {
            Write-Host "     WARN: robocopy exit $rc" -ForegroundColor Yellow
        }
    }
}

# ── Step 6: Deploy opencode config files ─────────────────────────────────────
Write-Header "Deploying opencode config files"

$opencodeConfig = "$env:USERPROFILE\.config\opencode"
$deployMap = @(
    @{ Src = "$Master\agents\opencode.json";                                          Dst = "$opencodeConfig\opencode.json" },
    @{ Src = "$Master\plugins\oh-my-opencode-slim\oh-my-opencode-slim.json";          Dst = "$opencodeConfig\oh-my-opencode-slim.json" },
    @{ Src = "$Master\plugins\oh-my-opencode-slim\orchestrator.md";                   Dst = "$opencodeConfig\oh-my-opencode-slim\orchestrator.md" },
    @{ Src = "$Master\agents\orchestrator.agent.md";                                  Dst = "$opencodeConfig\oh-my-opencode-slim\orchestrator.deepseek.md" },
    @{ Src = "$Master\agents\orchestrator.gemma.md";                                  Dst = "$opencodeConfig\oh-my-opencode-slim\orchestrator.gemma.md" }
)

foreach ($item in $deployMap) {
    if (-not (Test-Path $item.Src)) {
        Write-Host "  [SKIP] Source not found: $($item.Src)" -ForegroundColor DarkGray
        continue
    }
    $label = Split-Path $item.Src -Leaf
    if ($DryRun) {
        Write-Host "  [DRY] Would copy $label -> $($item.Dst)" -ForegroundColor DarkGray
    } else {
        $destDir = Split-Path $item.Dst -Parent
        if (-not (Test-Path $destDir)) { New-Item $destDir -ItemType Directory -Force | Out-Null }
        Copy-Item $item.Src $item.Dst -Force
        Write-Host "  Deployed: $label -> $($item.Dst)" -ForegroundColor Green
    }
}
Write-Host "  NOTE: orchestrator prompt variants are deployed from source templates." -ForegroundColor DarkGray
Write-Host "        DeepSeek: agents\orchestrator.agent.md -> orchestrator.deepseek.md" -ForegroundColor DarkGray
Write-Host "        Gemma   : agents\orchestrator.gemma.md -> orchestrator.gemma.md" -ForegroundColor DarkGray

# ── Step 7: Remote guidance ───────────────────────────────────────────────────
Write-Header "Remote: $RemoteUser@${RemoteHost}:$RemotePath"

Write-Host @"
  Option A -- WinSCP CLI (if winscp.com is on PATH):
    winscp.com /command ``
      "open sftp://$RemoteUser@$RemoteHost" ``
      "synchronize remote -filemask=""|.git/;.gitignore;.copilot/;.config/;.DS_Store;.*/;pytest_cache/;todo/;react_agent/;__pycache__/;copilot/;`$Recycle.Bin/;`$AV_ASW/;`$AV_ASW`$VAULT/;*[0-9a-f][0-9a-f][0-9a-f][0-9a-f]*""  ""$Master"" $RemotePath" ``
      "exit"

  Option B -- rsync (via WSL or Git Bash):
    rsync -avz --delete --exclude='.*' "$($Master.Replace('\','/'))" $RemoteUser@${RemoteHost}:$RemotePath

  Option C -- Manual WinSCP:
    Host    : $RemoteHost
    User    : $RemoteUser
    Remote  : $RemotePath
    Local   : $Master
  Mode    : Mirror (remote = local, delete extras)
"@ -ForegroundColor DarkGray

$launch = Read-Choice "`nLaunch WinSCP now? [y/n]" '' 'y'
if ($launch -eq 'y') {
    if (-not $Username) {
        $inputUser = Read-Host "  SSH username (default: $RemoteUser)"
        if ($inputUser -ne '') { $RemoteUser = $inputUser }
    }

    if ($Password) {
        $plainPwd = $Password
    } else {
        $securePwd = Read-Host "  SSH password" -AsSecureString
        $plainPwd = [System.Net.NetworkCredential]::new('', $securePwd).Password
    }

    $wscp  = Get-Command "winscp.com" -ErrorAction SilentlyContinue
    $rsync = Get-Command "rsync"      -ErrorAction SilentlyContinue

    if ($wscp) {
        Write-Host "  Launching WinSCP (override remote)..." -ForegroundColor Green
        & winscp.com /command "open sftp://${RemoteUser}:${plainPwd}@$RemoteHost" "synchronize remote -filemask=|.git/;.gitignore;.copilot/;.config/;.DS_Store;.*/;pytest_cache/;todo/;react_agent/;__pycache__/;copilot/;`$Recycle.Bin/;`$AV_ASW/;`$AV_ASW`$VAULT/;*[0-9a-f][0-9a-f][0-9a-f][0-9a-f]* ""$Master"" $RemotePath" "exit"
    } elseif ($rsync) {
        # rsync --delete = override downstream; remote changes are silently discarded (by design)
        Write-Host "  winscp.com not found -- falling back to rsync (override remote)..." -ForegroundColor Yellow
        $localFwd = $Master.Replace('\', '/')
        $sshPass  = "sshpass -p '$plainPwd'"
        & bash -c "$sshPass rsync -az --delete --exclude='.*' --exclude='*.db' --exclude='*.jsonl' --exclude='*.pyc' '${localFwd}/' '${RemoteUser}@${RemoteHost}:${RemotePath}/'"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  rsync OK" -ForegroundColor Green
        } else {
            Write-Host "  rsync exited $LASTEXITCODE -- check connectivity" -ForegroundColor Red
        }
    } else {
        Write-Host "  Neither winscp.com nor rsync found. Sync manually:" -ForegroundColor Yellow
        Write-Host "    $Master  -->  $RemoteUser@${RemoteHost}:$RemotePath" -ForegroundColor DarkGray
    }
}

Write-Header "Done"
if ($DryRun) { Write-Host "  [DRY RUN - no changes were made]" -ForegroundColor Magenta }
exit 0
