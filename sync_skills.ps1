<#
.SYNOPSIS
    Reconcile and sync skills across all known local locations.

.DESCRIPTION
    1. Checks non-master mirrors for .md files newer than the last git commit.
    2. Reports potential local promotions (skill files edited outside master).
    3. Diff/merge them back to master before overwriting.
    4. Reconciles ~/.claude harness config against the harness\claude vault.
    5. Syncs master -> all local mirrors via robocopy /MIR.
    6. Provides WinSCP guidance for the remote server.

    Tracked scope: root-level .md files + all */SKILL.md + all *.md in skill subdirs.
    Master copy: C:\Users\user\Documents\dev\skills

    HARNESS SCOPE (Step 4.5). ~/.claude is the primary harness, not merely a skills
    mirror, so its authored config is version-controlled in $Master\harness\claude:
      files : CLAUDE.md, SOUL.md, AGENTS.md, settings.json
      dirs  : agents\, rules\, docs\, commands\, hooks\, output-styles\
    Excluded by contract: settings.local.json (the local-override/secrets lane), plus
    runtime state -- sessions\, jobs\, cache\, *.log, *.lock, history.jsonl.
    The live ~/.claude tree is NEVER robocopy /MIR'd; every write is a targeted
    single-file copy, so a stale vault can never delete live harness state. Only .md
    files are eligible for LLM merge -- structured files (settings.json, hooks) are
    flagged on conflict rather than line-spliced into something that will not parse.
    The vault is excluded from both the local mirror push and the remote sync, so it
    never lands inside any */skills/ tree.

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

.PARAMETER Priority
    Mirror label (.claude, .copilot, opencode, .hermes, .pi) to rank FIRST when
    reconciling. Rank is a tie-breaker only -- it never makes the process less
    additive. It applies at exactly three junctions:
      1. New file present in several mirrors with differing content.
      2. Untracked file where master and mirror differ but mtimes cannot separate them.
      3. The LLM keep/drop pass, where a residual conflict resolves toward the
         ranked source instead of the default "when uncertain, keep master".
    Omit it and master (dev/skills) is 1st rank, which is the historical behaviour.

.EXAMPLE
    .\sync_skills.ps1
    .\sync_skills.ps1 -DryRun
    .\sync_skills.ps1 -Force
    .\sync_skills.ps1 -Priority .claude
    .\sync_skills.ps1 -OverwriteDownstream -y
    .\sync_skills.ps1 -Username root -Password hunter2 -y
#>
param(
    [switch]$Force,
    [switch]$OverwriteDownstream,
    [switch]$DryRun,
    [string]$Username,
    [string]$Password,
    [string]$OllamaUrl = "http://localhost:11434",
    [string]$OllamaModel = "qwen3.5:4b",
    [Alias('rank')][string]$Priority = '',
    [Alias('y')][switch]$Yes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Configuration ────────────────────────────────────────────────────────────
$Master  = "C:\Users\user\Documents\dev\skills"
$Mirrors = @(
    "C:\Users\user\.copilot\skills",
    "C:\Users\user\.config\opencode\skills",
    "C:\Users\user\.claude\skills",
    "C:\Users\user\.hermes\skills",
    "C:\Users\user\.pi\skills"
)
$RemoteUser = "root"
$RemoteHost = "192.168.3.17"
$RemotePaths = @(
    "/root/.copilot/skills",
    "/root/.claude/skills"
)

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

# Every mirror path ends in '\skills', so its leaf is always 'skills' and useless
# for telling mirrors apart in logs / .conflict artifacts. Use the parent dir name
# (.copilot, opencode, .claude, .hermes, .pi) so output names the real source.
function Get-MirrorLabel($mirror) {
    $parent = Split-Path $mirror -Parent
    if ([string]::IsNullOrEmpty($parent)) { return (Split-Path $mirror -Leaf) }
    return (Split-Path $parent -Leaf)
}

# ── Rank resolution ───────────────────────────────────────────────────────────
# $Priority names the mirror whose version wins a tie. Empty => master is 1st rank
# (historical behaviour). Matching is leading-dot- and case-insensitive so
# '-Priority claude', '-Priority .claude' and '-Priority .CLAUDE' all resolve.
# An unrecognised label is a typo, and silently falling back to master-first would
# hide it -- so fail loudly rather than sync with the wrong rank.
$script:PriorityLabel = ''
if (-not [string]::IsNullOrWhiteSpace($Priority)) {
    $knownLabels = @($Mirrors | ForEach-Object { Get-MirrorLabel $_ })
    $want = $Priority.Trim().TrimStart('.')
    $match = @($knownLabels | Where-Object { $_.TrimStart('.') -ieq $want })
    if ($match.Count -eq 0) {
        throw "Unknown -Priority '$Priority'. Known mirror labels: $($knownLabels -join ', ') (or omit -Priority to rank master first)."
    }
    $script:PriorityLabel = $match[0]
}

# True when $label is the ranked-first source for tie-breaking.
function Test-IsPriority($label) {
    if ([string]::IsNullOrEmpty($script:PriorityLabel)) { return $false }
    return ($label -eq $script:PriorityLabel)
}

function Show-Diff($masterFile, $mirrorFile) {
    # git diff --no-index gives a unified diff without needing a repo.
    # -c core.autocrlf=false suppresses git's "LF will be replaced by CRLF" stderr
    # warning, which under $ErrorActionPreference='Stop' would otherwise surface as
    # a fatal NativeCommandError and abort the whole reconciliation.
    $diff = git -c core.autocrlf=false diff --no-index --unified=3 -- $masterFile $mirrorFile 2>&1 |
            Where-Object { $_ -notmatch '^warning:' }
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
function Get-SyncCase($masterContent, $mirrorContent, $baseContent, $masterTime = $null, $mirrorTime = $null, $mirrorLabel = $null) {
    if ($null -eq $baseContent) {
        # No committed base (untracked/new file) — a 3-way compare is impossible.
        # Fall back to mtime so a STALE downstream copy never wins over a newer master.
        if ($masterContent -eq $mirrorContent) { return 'no-op' }
        if ($null -eq $masterContent) { return 'fast-forward-mirror' }   # master absent -> mirror is the only content
        if ($null -ne $masterTime -and $null -ne $mirrorTime) {
            if ($mirrorTime -gt $masterTime) { return 'fast-forward-mirror' }   # mirror newer -> promote
            if ($masterTime -gt $mirrorTime) { return 'fast-forward-master' }   # master newer -> keep master
        }
        # Rank junction 2: mtimes cannot separate them (equal or unknown) and the
        # content differs. Without a rank this is an unresolvable tie -> conflict.
        # With one, the ranked source wins; mtime still takes precedence above, so
        # rank never promotes a demonstrably STALE copy over a newer master.
        if (Test-IsPriority $mirrorLabel) { return 'fast-forward-mirror' }
        return 'conflict'   # equal/unknown mtimes but differing content -> let review/merge decide, never blind-copy
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

# ── Multi-mirror LLM merge engine (master = anchor) ───────────────────────────
# Model: master working copy is the source of truth. Every mirror is a set of
# proposed line-level changes AGAINST master. Identical changes across mirrors are
# deduplicated. An LLM decides per change whether to KEEP (apply) or DROP. On any
# ambiguity, conflict, or LLM failure we KEEP MASTER and write a .conflict artifact
# (master is never silently overwritten by an older/lesser mirror copy).

$script:OllamaReachable = $null
$script:ResolvedModel   = $OllamaModel

function Test-OllamaUp {
    if ($null -ne $script:OllamaReachable) { return $script:OllamaReachable }
    try {
        $tags = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -TimeoutSec 5 -ErrorAction Stop
        $names = @($tags.models | ForEach-Object { $_.name })
        if ($names -notcontains $OllamaModel) {
            if ($names.Count -gt 0) {
                $script:ResolvedModel = $names[0]
                Write-Host "  [OLLAMA] Model '$OllamaModel' not found; using '$($script:ResolvedModel)'." -ForegroundColor Yellow
            }
        }
        $script:OllamaReachable = $true
    } catch {
        $script:OllamaReachable = $false
    }
    return $script:OllamaReachable
}

# Parse master->mirror diff into discrete change records using git -U0 hunks.
function Get-HunkChanges($masterContent, $mirrorContent) {
    $changes = [System.Collections.Generic.List[hashtable]]::new()
    $tmpA = [System.IO.Path]::GetTempFileName()
    $tmpB = [System.IO.Path]::GetTempFileName()
    try {
        # BOM-less writes: Set-Content -Encoding UTF8 (Windows PowerShell 5.1) prepends
        # a BOM, which turns an "empty master" temp file into a 1-line file and makes
        # git report a phantom line-1 change. WriteAllText with a BOM-less encoder keeps
        # empty content truly empty so diffs stay honest.
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($tmpA, [string]$masterContent, $utf8NoBom)
        [System.IO.File]::WriteAllText($tmpB, [string]$mirrorContent, $utf8NoBom)
        $diff = git -c core.autocrlf=false diff --no-index --unified=0 -- $tmpA $tmpB 2>$null
        $cur = $null
        foreach ($line in $diff) {
            if ($line -match '^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@') {
                if ($null -ne $cur) { $changes.Add($cur) }
                $oldStart = [int]$Matches[1]
                $oldCount = if ($Matches[2]) { [int]$Matches[2] } else { 1 }
                $cur = @{
                    OldStart = $oldStart
                    OldCount = $oldCount
                    Removed  = [System.Collections.Generic.List[string]]::new()
                    Added    = [System.Collections.Generic.List[string]]::new()
                }
            } elseif ($null -ne $cur -and $line.StartsWith('-') -and -not $line.StartsWith('---')) {
                $cur.Removed.Add($line.Substring(1))
            } elseif ($null -ne $cur -and $line.StartsWith('+') -and -not $line.StartsWith('+++')) {
                $cur.Added.Add($line.Substring(1))
            }
        }
        if ($null -ne $cur) { $changes.Add($cur) }
    } finally {
        Remove-Item $tmpA, $tmpB -Force -ErrorAction SilentlyContinue
    }
    return $changes
}

function ConvertTo-ChangeKey($c) {
    # Identical (location + removed + added) => the same change, regardless of mirror.
    $sep = [char]0x241F
    return ('{0}|{1}|R={2}|A={3}' -f $c.OldStart, $c.OldCount, ($c.Removed -join $sep), ($c.Added -join $sep))
}

function Invoke-OllamaDecisions($rel, $changes) {
    if (-not (Test-OllamaUp)) { return $null }
    $sb = [System.Text.StringBuilder]::new()
    foreach ($c in $changes) {
        $type = if ($c.OldCount -eq 0) { 'INSERT' } elseif ($c.Added.Count -eq 0) { 'DELETE' } else { 'REPLACE' }
        [void]$sb.AppendLine("### Change $($c.Id)  [$type]  at master line $($c.OldStart)  (proposed by: $($c.Mirrors -join ', '))")
        if ($c.Removed.Count -gt 0) {
            [void]$sb.AppendLine('REMOVES from master:')
            foreach ($l in $c.Removed) { [void]$sb.AppendLine("  - $l") }
        }
        if ($c.Added.Count -gt 0) {
            [void]$sb.AppendLine('ADDS to master:')
            foreach ($l in $c.Added) { [void]$sb.AppendLine("  + $l") }
        }
        [void]$sb.AppendLine('')
    }
    # Rank junction 3. The default tie-break is "when uncertain, DROP" (keep master).
    # A rank overrides that tie-break ONLY for changes the ranked source proposed, and
    # ONLY where the model is otherwise undecided -- the additive/anti-deletion rules
    # above it still bind, so rank cannot license wholesale removal of master content.
    $rankRule = if ([string]::IsNullOrEmpty($script:PriorityLabel)) {
        "- RANK: master is ranked 1st. When uncertain, DROP. Never lose master content silently."
    } else {
        @"
- RANK: '$($script:PriorityLabel)' is ranked 1st, ahead of master, for this run.
  When you are UNCERTAIN about a change and its 'proposed by' list includes
  '$($script:PriorityLabel)', decide KEEP. That source is the operator's current
  working copy and its edits are the more recent intent.
  When you are uncertain about a change NOT proposed by '$($script:PriorityLabel)',
  decide DROP as usual. Rank breaks ties only -- it never licenses deleting
  substantial master content, which the DROP rules above still forbid.
"@
    }
    $prompt = @"
/no_think
You reconcile skill files. The MASTER copy is the CURRENT SOURCE OF TRUTH. Below are
proposed line-level changes that mirror copies would apply to master for file: $rel

For EACH change id, decide KEEP (apply to master) or DROP (leave master unchanged).
Rules:
- KEEP genuinely additive or improving content (new sections, clarifications, more detail).
- DROP a change that merely deletes substantial existing master content, unless the
  removed text is clearly obsolete or self-contradictory.
- If a change looks like an OLDER / less-complete mirror removing content master already
  has, DROP it.
$rankRule

Changes:
$($sb.ToString())
You MUST return exactly one decision object for EACH of these change ids: $(($changes | ForEach-Object { $_.Id }) -join ', ').
"@
    $schema = @{
        type       = 'object'
        properties = @{
            decisions = @{
                type  = 'array'
                items = @{
                    type       = 'object'
                    properties = @{
                        id     = @{ type = 'integer' }
                        keep   = @{ type = 'boolean' }
                        reason = @{ type = 'string' }
                    }
                    required = @('id', 'keep', 'reason')
                }
            }
        }
        required = @('decisions')
    }
    $body = @{
        model   = $script:ResolvedModel
        prompt  = $prompt
        stream  = $false
        format  = $schema
        # API-level thinking toggle. Reasoning models (qwen3.5:*) ignore an in-prompt
        # /no_think and route all output to the thinking channel, leaving 'response'
        # empty. think=false forces the answer into 'response' so structured output works.
        think   = $false
        options = @{ temperature = 0 }
    } | ConvertTo-Json -Depth 12
    try {
        $resp = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 300 -ErrorAction Stop
        $raw = if ($resp.PSObject.Properties.Name -contains 'response') { $resp.response } else { $null }
        if ([string]::IsNullOrWhiteSpace($raw)) {
            Write-Host "  [OLLAMA ERROR] $rel : empty response from model" -ForegroundColor Red
            return $null
        }
        $parsed = $raw | ConvertFrom-Json -ErrorAction Stop
        # Strict-mode-safe: accessing a missing property throws under Set-StrictMode,
        # so probe for the field before dereferencing it.
        if ($null -eq $parsed -or ($parsed.PSObject.Properties.Name -notcontains 'decisions')) {
            Write-Host "  [OLLAMA ERROR] $rel : model returned no 'decisions' field (weak/non-conforming output)" -ForegroundColor Red
            return $null
        }
        return @($parsed.decisions)
    } catch {
        Write-Host "  [OLLAMA ERROR] $rel : $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# Reconcile one rel-path across all mirrors. Returns a result hashtable with Status:
#   'no-op'   — no real changes
#   'merged'  — Content holds the rebuilt master
#   'flag'    — keep master; Reason + Changes describe why
function Invoke-MultiMirrorMerge($entry) {
    $masterContent = $entry.MasterContent

    # 0. Pure-additive new file. Master has no copy of this path, so every mirror
    # version is brand-new content (think: an untracked file in git). There is
    # nothing to 3-way merge — splicing hunks into a zero-line master crashes the
    # rebuild ("Change out of range"), so fold the new skill straight in. If mirrors
    # disagree on the new content, that IS a real conflict; flag it.
    if ([string]::IsNullOrEmpty($masterContent)) {
        $distinct = @(@($entry.Mirrors | ForEach-Object { $_.Content }) | Sort-Object -Unique)
        if ($distinct.Count -eq 1) {
            return @{ Status = 'added'; Content = $distinct[0]; MirrorCount = $entry.Mirrors.Count }
        }
        # Rank junction 1: mirrors disagree on brand-new content. There is no master
        # copy to fall back on, so without a rank this can only be flagged. With one,
        # the ranked mirror's version is taken as authoritative.
        $ranked = @($entry.Mirrors | Where-Object { Test-IsPriority $_.Label })
        if ($ranked.Count -gt 0) {
            return @{
                Status      = 'added'
                Content     = $ranked[0].Content
                MirrorCount = $entry.Mirrors.Count
                RankedBy    = $ranked[0].Label
            }
        }
        return @{
            Status  = 'flag'
            Reason  = "New file with $($distinct.Count) differing versions across $($entry.Mirrors.Count) mirror(s)"
            Changes = @()
        }
    }

    # 1. Collect + deduplicate changes across every mirror.
    $byKey = [ordered]@{}
    foreach ($m in $entry.Mirrors) {
        foreach ($c in (Get-HunkChanges $masterContent $m.Content)) {
            $k = ConvertTo-ChangeKey $c
            if ($byKey.Contains($k)) {
                if ($byKey[$k].Mirrors -notcontains $m.Label) { [void]$byKey[$k].Mirrors.Add($m.Label) }
            } else {
                $c.Mirrors = [System.Collections.Generic.List[string]]::new()
                $c.Mirrors.Add($m.Label)
                $byKey[$k] = $c
            }
        }
    }
    $changes = @($byKey.Values)
    if ($changes.Count -eq 0) { return @{ Status = 'no-op' } }
    for ($i = 0; $i -lt $changes.Count; $i++) { $changes[$i].Id = $i + 1 }

    # 2. LLM keep/drop decision per change.
    $decisions = Invoke-OllamaDecisions $entry.Rel $changes
    if ($null -eq $decisions) {
        return @{ Status = 'flag'; Reason = 'LLM unreachable or failed'; Changes = $changes }
    }
    $keep = @{}
    foreach ($d in $decisions) { $keep[[int]$d.id] = [bool]$d.keep }
    # Every change must get an explicit verdict. Missing coverage (e.g. a starved/weak
    # model returning [] or a partial list) is ambiguity, not consent to drop — flag it
    # so real additive changes are never silently lost.
    $covered = @($changes | Where-Object { $keep.ContainsKey($_.Id) }).Count
    if ($covered -lt $changes.Count) {
        return @{ Status = 'flag'; Reason = "LLM returned $covered/$($changes.Count) decisions (incomplete)"; Changes = $changes; Decisions = $decisions }
    }
    $kept = @($changes | Where-Object { $keep[$_.Id] })
    if ($kept.Count -eq 0) { return @{ Status = 'no-op'; Changes = $changes; Decisions = $decisions } }

    # 3. Kept changes must not overlap on master lines (else we cannot apply both).
    $sorted = @($kept | Sort-Object OldStart)
    for ($i = 1; $i -lt $sorted.Count; $i++) {
        $prev = $sorted[$i - 1]; $curr = $sorted[$i]
        $prevEnd = $prev.OldStart + [Math]::Max($prev.OldCount, 1) - 1
        if ($curr.OldStart -le $prevEnd -or
            ($curr.OldStart -eq $prev.OldStart -and ($curr.OldCount -eq 0 -or $prev.OldCount -eq 0))) {
            return @{ Status = 'flag'; Reason = 'Kept changes overlap on master lines'; Changes = $changes; Decisions = $decisions }
        }
    }

    # 4. Rebuild master by splicing kept changes bottom-up (indices stay valid).
    $lines = [System.Collections.Generic.List[string]]::new()
    if (-not [string]::IsNullOrEmpty($masterContent)) {
        $lines.AddRange([string[]]$masterContent.Split("`n"))
    }
    foreach ($c in @($kept | Sort-Object OldStart -Descending)) {
        if ($c.OldCount -gt 0) {
            $idx = $c.OldStart - 1
            if ($idx -lt 0 -or ($idx + $c.OldCount) -gt $lines.Count) {
                return @{ Status = 'flag'; Reason = 'Change out of range during rebuild'; Changes = $changes; Decisions = $decisions }
            }
            $lines.RemoveRange($idx, $c.OldCount)
            if ($c.Added.Count -gt 0) { $lines.InsertRange($idx, [string[]]$c.Added) }
        } else {
            $idx = $c.OldStart
            if ($idx -lt 0 -or $idx -gt $lines.Count) {
                return @{ Status = 'flag'; Reason = 'Insertion out of range during rebuild'; Changes = $changes; Decisions = $decisions }
            }
            if ($c.Added.Count -gt 0) { $lines.InsertRange($idx, [string[]]$c.Added) }
        }
    }
    return @{ Status = 'merged'; Content = ($lines -join "`n"); Kept = $kept; Changes = $changes; Decisions = $decisions }
}

function Write-ConflictArtifact($entry, $result) {
    $conflictFile = (Join-Path $Master $entry.Rel) + '.conflict'
    $sb = [System.Text.StringBuilder]::new()
    [void]$sb.AppendLine("# MANUAL MERGE REQUIRED: $($entry.Rel)")
    [void]$sb.AppendLine("# Reason: $($result.Reason)")
    [void]$sb.AppendLine('# Master was left UNCHANGED. Review the proposed mirror changes below, then delete this file.')
    [void]$sb.AppendLine('#')
    if ($result.ContainsKey('Changes')) {
        foreach ($c in $result.Changes) {
            [void]$sb.AppendLine("## Change $($c.Id) at master line $($c.OldStart) (mirrors: $($c.Mirrors -join ', '))")
            foreach ($l in $c.Removed) { [void]$sb.AppendLine("- $l") }
            foreach ($l in $c.Added)   { [void]$sb.AppendLine("+ $l") }
            [void]$sb.AppendLine('')
        }
    }
    if (-not $DryRun) { Set-Content $conflictFile $sb.ToString() -Encoding UTF8 }
    Write-Host "  Conflict artifact: $conflictFile" -ForegroundColor Red
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
if ($script:PriorityLabel) {
    Write-Host "  Rank 1st    : $($script:PriorityLabel) (tie-breaks resolve toward this mirror, not master)" -ForegroundColor Cyan
} else {
    Write-Host "  Rank 1st    : master (default; pass -Priority <label> to rank a mirror ahead of it)" -ForegroundColor DarkGray
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
                    MirrorLabel = (Get-MirrorLabel $mirror)
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
Write-Header "Checking tracked .md files that differ from master"
$needsMerge = [System.Collections.Generic.List[hashtable]]::new()
# Per-rel-path aggregation across ALL mirrors (master = anchor) for the LLM engine.
$byPath = [ordered]@{}

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
            $masterExists = Test-Path $masterFile

            # Direction is NOT decided by timestamp here. master is the anchor; any
            # mirror whose content differs contributes proposed changes the LLM judges.
            $masterContent = if ($masterExists) { Normalize-LineEndings (Get-Content $masterFile -Raw) } else { $null }
            $mirrorContent = Normalize-LineEndings (Get-Content $mf -Raw)
            if ($masterContent -ne $mirrorContent) {
                $count++
                Write-Host ("  [DIFF] {0,-55} {1}" -f $rel, $mfTime.ToString("yyyy-MM-dd HH:mm")) -ForegroundColor Yellow
                $needsMerge.Add(@{
                    Mirror      = $mirror
                    MirrorLabel = Get-MirrorLabel $mirror
                    Rel         = $rel
                    MirrorFile  = $mf
                    MasterFile  = $masterFile
                    MirrorTime  = $mfTime
                    MasterExists = $masterExists
                })

                $mirrorLabel = Get-MirrorLabel $mirror
                if (-not $byPath.Contains($rel)) {
                    $byPath[$rel] = @{
                        Rel           = $rel
                        MasterFile    = $masterFile
                        MasterContent = $masterContent
                        MasterExists  = $masterExists
                        Mirrors       = [System.Collections.Generic.List[hashtable]]::new()
                    }
                }
                $byPath[$rel].Mirrors.Add(@{ Label = $mirrorLabel; File = $mf; Content = $mirrorContent })
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
            if (-not (Test-Path $item.FullPath)) {
                Write-Host "  [GONE] $($item.FolderName) -- folder removed since scan; skipping." -ForegroundColor DarkGray
                continue
            }
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
            if (-not (Test-Path $item.FullPath)) {
                Write-Host "  [GONE] $($item.FolderName) -- folder removed since scan; skipping." -ForegroundColor DarkGray
                continue
            }
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
            # Mirror file may have been moved/deleted between scan and reconciliation
            # (e.g. a skill relocated while the script waits at a prompt). Never fatal.
            if (-not (Test-Path $item.MirrorFile)) {
                $item['SyncCase'] = 'gone'
                Write-Host "  [GONE] $($item.Rel) ($($item.MirrorLabel)) -- mirror file removed since scan; skipping." -ForegroundColor DarkGray
                continue
            }
            $baseContent   = Get-BaseContent $item.Rel
            $masterContent = if ($item.MasterExists) { Normalize-LineEndings (Get-Content $item.MasterFile -Raw) } else { $null }
            $mirrorContent = Normalize-LineEndings (Get-Content $item.MirrorFile -Raw)
            $masterTime    = if ($item.MasterExists) { (Get-Item $item.MasterFile).LastWriteTime } else { $null }
            $case = Get-SyncCase $masterContent $mirrorContent $baseContent $masterTime $item.MirrorTime $item.MirrorLabel
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

        # Auto mode (-y / 'y'): multi-mirror, change-deduplicated, LLM-judged merge.
        # master is the anchor; nothing here can silently overwrite master.
        if ($resp -eq 'y') {
            if (-not (Test-OllamaUp)) {
                Write-Host "  [OLLAMA DOWN] $OllamaUrl unreachable -- keeping master for all diffs; writing .conflict artifacts." -ForegroundColor Red
            } else {
                Write-Host "  Using model: $($script:ResolvedModel)" -ForegroundColor DarkGray
            }
            foreach ($entry in @($byPath.Values)) {
                $result = Invoke-MultiMirrorMerge $entry
                switch ($result.Status) {
                    'added' {
                        Write-ToMaster $entry $result.Content
                        if ($result.Contains('RankedBy')) {
                            Write-Host "  [ADD/RANK]  $($entry.Rel) -- new skill, mirrors disagreed; took '$($result.RankedBy)' as 1st rank (of $($result.MirrorCount) mirror(s))." -ForegroundColor Cyan
                        } else {
                            Write-Host "  [ADD]       $($entry.Rel) -- new skill folded into master (additive; from $($result.MirrorCount) mirror(s))." -ForegroundColor Green
                        }
                    }
                    'merged' {
                        Write-ToMaster $entry $result.Content
                        Write-Host "  [LLM-MERGE] $($entry.Rel) -- kept $($result.Kept.Count)/$($result.Changes.Count) change(s) from $($entry.Mirrors.Count) mirror(s)" -ForegroundColor Green
                    }
                    'flag' {
                        Write-Host "  [FLAG]      $($entry.Rel) -- $($result.Reason); master kept." -ForegroundColor Yellow
                        Write-ConflictArtifact $entry $result
                    }
                    default {
                        Write-Host "  [NO-OP]     $($entry.Rel) -- no changes applied (master already current)." -ForegroundColor DarkGray
                    }
                }
            }
        }

        foreach ($item in $needsMerge) {
            if ($resp -eq 'n') {
                Write-Host "  Skipped all." -ForegroundColor DarkGray
                break
            }
            if ($item['SyncCase'] -eq 'gone') { continue }   # vanished at classification
            if (-not (Test-Path $item.MirrorFile)) {
                Write-Host "  [GONE] $($item.Rel) -- mirror file removed mid-run; skipped." -ForegroundColor DarkGray
                continue
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

            if ($resp -eq 'y') { continue }  # auto handled by multi-mirror engine above

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
            } elseif ($syncCase -eq 'fast-forward-master') {
                # Master is newer than this mirror; copying the mirror would DOWNGRADE master.
                # Skip — Step 5 pushes master downstream to refresh the stale mirror.
                Write-Host "  Master is newer than this mirror; keeping master (it will push downstream). Skipped." -ForegroundColor DarkGray
            } else {
                # Fast-forward (mirror newer/additive): simple copy prompt
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
        if (-not (Test-Path $item.FullPath)) {
            Write-Host "  [GONE] Folder vanished before copy: $($item.FolderName) -- skipped." -ForegroundColor Yellow
            continue
        }
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

# ── Step 4.5: Reconcile ~/.claude harness config <-> master vault ────────────
# ~/.claude is no longer just a skills mirror -- it is the primary harness, and its
# authored config (CLAUDE.md, SOUL.md, agents/, rules/, docs/, hooks/, settings.json)
# is edited in place and lives nowhere else. This step version-controls it.
#
# Vault  : $Master\harness\claude   (git-tracked; namespaced so it cannot collide
#                                    with master's pre-existing root agents/ folder,
#                                    and /XD-excluded from the Step 5 mirror push so
#                                    it is never sprayed into every */skills/ tree)
# Live   : $env:USERPROFILE\.claude (authoritative working copy)
#
# Direction is symmetric and uses the SAME 3-way machinery as skills (Get-SyncCase,
# rank tie-break, Invoke-LlmMerge). Two hard guardrails distinguish it from Step 5:
#   1. NEVER robocopy /MIR the live tree. Deleting live harness state is unrecoverable,
#      so every write here is a targeted single-file copy.
#   2. Only .md files are eligible for LLM merge. A line-spliced .json or .ps1 can be
#      syntactically broken by a merge that looks fine line-by-line, so non-markdown
#      conflicts are flagged for human review and both sides are left untouched.
$ClaudeHome  = Join-Path $env:USERPROFILE '.claude'
$ClaudeVault = Join-Path $Master 'harness\claude'
# Mirror/remote pushes exclude the whole harness ROOT, not just harness\claude.
# Excluding only the leaf still lets robocopy /MIR create an empty 'harness' shell in
# every mirror -- harmless but confusing, since it looks like a partial leak.
$ClaudeVaultRoot = Join-Path $Master 'harness'

# Allowlist. Authored config only -- runtime state (sessions/, jobs/, cache/, logs,
# lockfiles) is deliberately absent, and settings.local.json is the documented
# local-override/secrets lane so it is excluded by contract, not by accident.
$ClaudeRootFiles = @('CLAUDE.md', 'SOUL.md', 'AGENTS.md', 'settings.json')
$ClaudeDirs      = @('agents', 'rules', 'docs', 'commands', 'hooks', 'output-styles')
$ClaudeExcludeRx = '(^|\\)(settings\.local\.json|.*\.log|.*\.lock|.*\.status\.json|history\.jsonl|stats-cache\.json)$'

# Enumerate allowlisted paths under a root, returned as root-relative paths.
function Get-HarnessRelPaths($root) {
    $rels = [System.Collections.Generic.List[string]]::new()
    if (-not (Test-Path $root)) { return $rels }
    foreach ($name in $ClaudeRootFiles) {
        if (Test-Path (Join-Path $root $name)) { $rels.Add($name) }
    }
    foreach ($dir in $ClaudeDirs) {
        $full = Join-Path $root $dir
        if (-not (Test-Path $full)) { continue }
        Get-ChildItem $full -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
            $rels.Add((Get-RelPath $_.FullName $root))
        }
    }
    return @($rels | Where-Object { $_ -notmatch $ClaudeExcludeRx })
}

# Single-file copy with parent-dir creation. The ONLY write primitive in this step.
function Copy-HarnessFile($srcFile, $dstFile, $track) {
    if ($DryRun) { return }
    $parent = Split-Path $dstFile -Parent
    if (-not (Test-Path $parent)) { New-Item $parent -ItemType Directory -Force | Out-Null }
    Copy-Item $srcFile $dstFile -Force
    if ($track) { [void]$touchedPaths.Add($dstFile) }
}

if ($skipReconciliation) {
    Write-Header "Harness config (~/.claude): skipped"
    Write-Host "  [SKIP] Reconciliation disabled in current mode." -ForegroundColor DarkGray
} elseif (-not (Test-Path $ClaudeHome)) {
    Write-Header "Harness config (~/.claude): not found"
    Write-Host "  [SKIP] $ClaudeHome does not exist." -ForegroundColor DarkGray
} else {
    Write-Header "Reconciling harness config: ~/.claude <-> harness\claude"

    $liveRels  = Get-HarnessRelPaths $ClaudeHome
    $vaultRels = Get-HarnessRelPaths $ClaudeVault
    $allRels   = @(@($liveRels) + @($vaultRels) | Sort-Object -Unique)

    if ($allRels.Count -eq 0) {
        Write-Host "  Nothing allowlisted found under $ClaudeHome." -ForegroundColor DarkGray
    }

    $hStats = @{ Promoted = 0; Pushed = 0; Merged = 0; Flagged = 0; NoOp = 0; Restored = 0 }

    foreach ($rel in $allRels) {
        $liveFile  = Join-Path $ClaudeHome  $rel
        $vaultFile = Join-Path $ClaudeVault $rel
        $liveOk    = Test-Path $liveFile
        $vaultOk   = Test-Path $vaultFile
        $isMd      = [System.IO.Path]::GetExtension($rel) -ieq '.md'

        # New in live, absent from vault -> pure capture. Always additive.
        if ($liveOk -and -not $vaultOk) {
            Copy-HarnessFile $liveFile $vaultFile $true
            Write-Host "  [CAPTURE]   $rel -- new in ~/.claude, added to vault." -ForegroundColor Green
            $hStats.Promoted++
            continue
        }

        # In vault but gone from live. Could be an intentional delete OR data loss, and
        # the two are indistinguishable from here -- so never silently restore. Ask.
        if ($vaultOk -and -not $liveOk) {
            Write-Host "  [ABSENT]    $rel -- in vault, missing from ~/.claude." -ForegroundColor Yellow
            # AutoYesChoice is 'n' here, unlike every other prompt in this script. A
            # deliberate delete and accidental data loss look identical from here, and
            # an unattended -y run must not resurrect a rule the operator removed on
            # purpose. The vault copy is retained either way, so declining loses nothing.
            $choice = Read-Choice "    Restore it to ~/.claude? [y/n]" 'n' 'n'
            if ($choice -eq 'y') {
                Copy-HarnessFile $vaultFile $liveFile $false
                Write-Host "    Restored to $liveFile" -ForegroundColor Green
                $hStats.Restored++
            } else {
                Write-Host "    Left alone (vault copy retained as history)." -ForegroundColor DarkGray
            }
            continue
        }

        $liveContent  = Normalize-LineEndings (Get-Content $liveFile  -Raw -ErrorAction SilentlyContinue)
        $vaultContent = Normalize-LineEndings (Get-Content $vaultFile -Raw -ErrorAction SilentlyContinue)
        if ($liveContent -eq $vaultContent) { $hStats.NoOp++; continue }

        # 3-way against the committed vault copy. Live plays the 'mirror' role and
        # carries the '.claude' label, so -Priority .claude ranks it ahead of the vault
        # exactly as it does for skills.
        $vaultRel  = Join-Path 'harness\claude' $rel
        $base      = Get-BaseContent $vaultRel
        $liveTime  = (Get-Item $liveFile).LastWriteTime
        $vaultTime = (Get-Item $vaultFile).LastWriteTime
        $case = Get-SyncCase $vaultContent $liveContent $base $vaultTime $liveTime '.claude'

        switch ($case) {
            'fast-forward-mirror' {
                Copy-HarnessFile $liveFile $vaultFile $true
                Write-Host "  [PROMOTE]   $rel -- ~/.claude is ahead; captured to vault." -ForegroundColor Green
                $hStats.Promoted++
            }
            'fast-forward-master' {
                Copy-HarnessFile $vaultFile $liveFile $false
                Write-Host "  [PUSH]      $rel -- vault is ahead; pushed to ~/.claude." -ForegroundColor Cyan
                $hStats.Pushed++
            }
            'conflict' {
                if (-not $isMd) {
                    # Line-splicing structured text can produce a file that merges cleanly
                    # and still fails to parse. Never risk it on settings.json or a hook.
                    Write-Host "  [FLAG]      $rel -- both sides diverged (non-markdown; no auto-merge). Both copies left as-is." -ForegroundColor Yellow
                    if (-not $DryRun) {
                        $art = "$vaultFile.conflict"
                        $d = git -c core.autocrlf=false diff --no-index --unified=3 -- $vaultFile $liveFile 2>&1 |
                             Where-Object { $_ -notmatch '^warning:' }
                        Set-Content $art (@(
                            "# MANUAL MERGE REQUIRED: $rel",
                            "# vault: $vaultFile",
                            "# live : $liveFile",
                            "# Structured (non-markdown) file -- auto-merge disabled by contract.",
                            "# Reconcile by hand, then delete this file.",
                            "#"
                        ) + $d -join "`n") -Encoding UTF8
                    }
                    $hStats.Flagged++
                } else {
                    $merged = Invoke-LlmMerge $vaultRel $base $vaultContent $liveContent
                    if ($null -eq $merged) {
                        Write-Host "  [FLAG]      $rel -- merge failed; both copies left as-is (.conflict written)." -ForegroundColor Yellow
                        $hStats.Flagged++
                    } else {
                        if (-not $DryRun) {
                            $parent = Split-Path $vaultFile -Parent
                            if (-not (Test-Path $parent)) { New-Item $parent -ItemType Directory -Force | Out-Null }
                            Set-Content $vaultFile $merged -Encoding UTF8 -NoNewline
                            Set-Content $liveFile  $merged -Encoding UTF8 -NoNewline
                            [void]$touchedPaths.Add($vaultFile)
                        }
                        Write-Host "  [MERGE]     $rel -- both sides diverged; merged into vault AND ~/.claude." -ForegroundColor Green
                        $hStats.Merged++
                    }
                }
            }
            default { $hStats.NoOp++ }
        }
    }

    Write-Host ("`n  Harness: {0} promoted, {1} pushed, {2} merged, {3} flagged, {4} restored, {5} unchanged." -f `
        $hStats.Promoted, $hStats.Pushed, $hStats.Merged, $hStats.Flagged, $hStats.Restored, $hStats.NoOp) -ForegroundColor Cyan

    # Commit the vault separately from the skills reconciliation above -- staging only
    # harness paths keeps unrelated worktree changes out of the commit.
    $vaultDirty = @($touchedPaths | Where-Object { $_ -like "$ClaudeVault*" })
    if ($vaultDirty.Count -gt 0 -and -not $DryRun) {
        $commit = Read-Choice "`n  Commit harness config changes to master? [y/n]" '' 'y'
        if ($commit -eq 'y') {
            git -C $Master add -- $vaultDirty
            $staged = git -C $Master diff --cached --name-only 2>$null
            if ($staged) {
                git -C $Master commit -m "Sync ~/.claude harness config to harness/claude vault`n`nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
                Write-Host "  Committed." -ForegroundColor Green
            } else {
                Write-Host "  Nothing staged; skipped commit." -ForegroundColor DarkGray
            }
        }
    }
}

# ── Step 5: Sync master -> local mirrors ──────────────────────────────────────
Write-Header "Syncing master -> local mirrors"

foreach ($mirror in $Mirrors) {
    Write-Host "  -> $mirror"
    if ($DryRun) {
        robocopy $Master $mirror /MIR /L /NJH /NJS /NDL /NC /NS /XD ".git" ".todo" "__pycache__" ".pytest_cache" ".react_agent" "ms-playwright" "node_modules" "$ClaudeVaultRoot" /XF "*.pyc" "*.db" "*.jsonl" "*.exe" "*.dll" "*.pak" 2>&1 |
            Where-Object { $_ -match '\S' } | Select-Object -First 20 | ForEach-Object { Write-Host "     $_" -ForegroundColor DarkGray }
    } else {
        robocopy $Master $mirror /MIR /NJH /NJS /NDL /NC /NS /XD ".git" ".pytest_cache" ".todo" ".react_agent" "__pycache__" ".copilot" "ms-playwright" "node_modules" "$ClaudeVaultRoot" /XF "*.pyc" "*.db" "*.jsonl" "*.exe" "*.dll" "*.pak" | Out-Null
        $rc = $LASTEXITCODE
        if ($rc -le 1) {
            Write-Host "     OK (exit $rc)" -ForegroundColor Green
        } elseif ($rc -eq 3) {
            # 3 = files copied + extra files present. Not an error.
            Write-Host "     OK (exit 3: copied, extras present)" -ForegroundColor Green
        } else {
            Write-Host "     WARN: robocopy exit $rc" -ForegroundColor Yellow
        }

        # /XD exempts a dir from purging as well as from copying, so a 'harness' shell
        # left by an earlier run would persist forever. Remove it -- but ONLY when it
        # is genuinely empty, so this can never delete mirror content. Scoped to the
        # mirror; the live ~/.claude tree is never touched by this step.
        $shell = Join-Path $mirror 'harness'
        if (Test-Path $shell) {
            $contents = @(Get-ChildItem $shell -Recurse -File -Force -ErrorAction SilentlyContinue)
            if ($contents.Count -eq 0) {
                Remove-Item $shell -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "     Cleared empty 'harness' shell." -ForegroundColor DarkGray
            } else {
                Write-Host "     WARN: $shell is NOT empty ($($contents.Count) file(s)); left in place for review." -ForegroundColor Yellow
            }
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
Write-Header "Remote: $RemoteUser@${RemoteHost} -> $($RemotePaths -join ', ')"

foreach ($RemotePath in $RemotePaths) {
    Write-Host @"
  [$RemotePath]
  Option A -- WinSCP CLI (if winscp.com is on PATH):
    winscp.com /command ``
      "open sftp://$RemoteUser@$RemoteHost" ``
      "synchronize remote -filemask=""|.git/;.gitignore;harness/;.copilot/;.config/;.DS_Store;.*/;pytest_cache/;todo/;react_agent/;__pycache__/;copilot/;ms-playwright/;node_modules/;*.exe;*.dll;*.pak;`$Recycle.Bin/;`$AV_ASW/;`$AV_ASW`$VAULT/;*[0-9a-f][0-9a-f][0-9a-f][0-9a-f]*""  ""$Master"" $RemotePath" ``
      "exit"

  Option B -- rsync (via WSL or Git Bash):
    rsync -avz --delete --exclude='.*' --exclude='harness/' "$($Master.Replace('\','/'))" $RemoteUser@${RemoteHost}:$RemotePath

  Option C -- Manual WinSCP:
    Host    : $RemoteHost
    User    : $RemoteUser
    Remote  : $RemotePath
    Local   : $Master
    Mode    : Mirror (remote = local, delete extras)
"@ -ForegroundColor DarkGray
}

if ($DryRun) {
    # A dry run must never mutate the remote. Report and skip.
    Write-Host "`n  [DRY] Skipping remote sync launch (dry run)." -ForegroundColor Magenta
    $launch = 'n'
} elseif ($Yes) {
    # Non-interactive: only push to the remote when credentials were explicitly
    # supplied. Otherwise skip rather than blast the remote or block on a password
    # prompt (Read-Host has no auto-answer).
    if ($Username -and $Password) {
        $launch = 'y'
    } else {
        Write-Host "`n  [AUTO] Remote sync skipped (pass -Username and -Password to enable in -Yes mode)." -ForegroundColor DarkGray
        $launch = 'n'
    }
} else {
    $launch = Read-Choice "`nLaunch WinSCP now? [y/n]" '' 'y'
}
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

    foreach ($RemotePath in $RemotePaths) {
        Write-Host "  -> $RemoteUser@${RemoteHost}:$RemotePath" -ForegroundColor Cyan
        if ($wscp) {
            & winscp.com /command "open sftp://${RemoteUser}:${plainPwd}@$RemoteHost" "synchronize remote -filemask=|.git/;.gitignore;harness/;.copilot/;.config/;.DS_Store;.*/;pytest_cache/;todo/;react_agent/;__pycache__/;copilot/;ms-playwright/;node_modules/;*.exe;*.dll;*.pak;`$Recycle.Bin/;`$AV_ASW/;`$AV_ASW`$VAULT/;*[0-9a-f][0-9a-f][0-9a-f][0-9a-f]* ""$Master"" $RemotePath" "exit"
            if ($LASTEXITCODE -eq 0) {
                Write-Host "     OK" -ForegroundColor Green
            } else {
                Write-Host "     WARN: WinSCP exited $LASTEXITCODE" -ForegroundColor Yellow
            }
        } elseif ($rsync) {
            # rsync --delete = override downstream; remote changes are silently discarded (by design)
            Write-Host "  winscp.com not found -- falling back to rsync (override remote)..." -ForegroundColor Yellow
            $localFwd = $Master.Replace('\', '/')
            $sshPass  = "sshpass -p '$plainPwd'"
            & bash -c "$sshPass rsync -az --delete --exclude='.*' --exclude='*.db' --exclude='*.jsonl' --exclude='*.pyc' --exclude='ms-playwright' --exclude='node_modules' --exclude='*.exe' --exclude='*.dll' --exclude='*.pak' '${localFwd}/' '${RemoteUser}@${RemoteHost}:${RemotePath}/'"
            if ($LASTEXITCODE -eq 0) {
                Write-Host "     rsync OK" -ForegroundColor Green
            } else {
                Write-Host "     rsync exited $LASTEXITCODE -- check connectivity" -ForegroundColor Red
            }
        } else {
            Write-Host "  Neither winscp.com nor rsync found. Sync manually:" -ForegroundColor Yellow
            Write-Host "    $Master  -->  $RemoteUser@${RemoteHost}:$RemotePath" -ForegroundColor DarkGray
        }
    }
}

# ── Step 8: Dry-run preview of what would sync to remote ─────────────────────
if (-not $DryRun) {
    $previewChoice = Read-Choice "`nPreview what would sync to remote next time? [y/n]" '' 'n'
    if ($previewChoice -eq 'y') {
        Write-Header "Remote sync preview (robocopy /L - files that differ from master)"
        Write-Host "  Files listed below would be transferred on next remote sync." -ForegroundColor DarkGray
        robocopy $Master "$env:TEMP\__sync_preview_dummy__" /MIR /L /NJH /NJS /NC /NS /XD ".git" ".pytest_cache" ".todo" ".react_agent" "__pycache__" ".copilot" "ms-playwright" "node_modules" "$ClaudeVaultRoot" /XF "*.pyc" "*.db" "*.jsonl" "*.exe" "*.dll" "*.pak" 2>&1 |
            Where-Object { $_ -match '\S' } | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    }
}

Write-Header "Done"
if ($DryRun) { Write-Host "  [DRY RUN - no changes were made]" -ForegroundColor Magenta }
exit 0
