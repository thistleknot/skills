<#
.SYNOPSIS
    Route a bounded coding task directly to @aider via orchestrator.

.DESCRIPTION
    `--agent aider` is blocked by oh-my-opencode-slim (aider is a subagent-only
    in the npm package; preset additions have no effect).  This wrapper forces
    the orchestrator to dispatch the task to @aider immediately by prefixing
    the prompt with an unambiguous directive.

    Runs from the repo root (parent of agents\) so the entire repo is inside
    opencode's workspace sandbox — avoids PITFALL 11 external-path rejections.

    Usage:
        .\run_aider.ps1 "Rewrite function foo in src\bar.py to use list comprehension"
#>
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Task
)

$agentsDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $agentsDir

$prompt = @"
AIDER DIRECT: use the task tool RIGHT NOW to spawn @aider and have it complete this task. Do not describe what you will do — call the task spawn tool immediately.

Task: $Task
"@

opencode run $prompt
