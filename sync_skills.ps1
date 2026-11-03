<#
.SYNOPSIS
    Export selected canonical skill packages without destructive mirroring or model merges.
.DESCRIPTION
    CURRENT: ~/.skills is the master; ~/.harness/adapter.py is the writer.
    Legacy reconciliation/remote-sync implementation is preserved in sync_skills-legacy-20261024.ps1.
    Spec: ~/.harness/docs/playbooks/memory-and-harness-integration.md R10-R12.
    No package or legacy content is deleted; unique/divergent resources are preserved.
#>
param(
    [string[]]$Skill,
    [switch]$DryRun,
    [switch]$Check,
    [switch]$Force,
    [switch]$OverwriteDownstream,
    [Alias('y')][switch]$Yes,
    [string]$Priority,
    [string]$Username,
    [string]$Password,
    [string]$OllamaUrl,
    [string]$OllamaModel
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Master = Join-Path $env:USERPROFILE '.skills'
if ($Username -or $Password) { throw 'Remote synchronization is separate; this command exports local canonical skills only.' }
if ($Check -and ($Force -or $OverwriteDownstream)) { throw 'Check cannot apply changes.' }
if (-not $Skill) {
    $Skill = @(Get-ChildItem -LiteralPath $Master -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } | Select-Object -ExpandProperty Name)
}
if ($Skill.Count -eq 0) { throw 'No canonical skill packages selected.' }
$adapter = Join-Path $env:USERPROFILE '.harness/adapter.py'
$python = Join-Path $env:USERPROFILE 'py310/Scripts/python.exe'
$arguments = @($adapter, '--target', 'skills', '--skill') + $Skill
if ($Check) { $arguments += '--check' }
elseif (-not $DryRun -and ($Force -or $OverwriteDownstream -or $Yes)) { $arguments += @('--apply', '--reconcile') }
else { $arguments += '--reconcile' }
& $python @arguments
exit $LASTEXITCODE
