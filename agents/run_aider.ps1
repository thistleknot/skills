<#
.SYNOPSIS
    Route a bounded coding task directly to @aider via orchestrator.

.DESCRIPTION
    `--agent aider` is blocked by oh-my-opencode-slim (aider is a subagent-only
    in the npm package; preset additions have no effect).  This wrapper forces
    the orchestrator to dispatch the task to @aider immediately by prefixing
    the prompt with an unambiguous directive.

    Usage:
        .\run_aider.ps1 "Rewrite function foo in src\bar.py to use list comprehension"

    The working directory MUST be the agents\ folder (so opencode discovers opencode.json).
    This script enforces that automatically.
#>
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Task
)

$agentsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $agentsDir

$prompt = @"
AIDER DIRECT: delegate this entire task to @aider with no additional orchestration or subtask routing. @aider handles it end-to-end.

Task: $Task
"@

opencode run $prompt
