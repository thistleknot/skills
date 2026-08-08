<#
  register-anneal-task.ps1 - weekly Task Scheduler job that runs `mem anneal` as SYSTEM,
  evicting stale, under-recalled Chroma memory-log bits. Run ELEVATED (SYSTEM principal).
  Mirrors the always-on service pattern: the job survives reboot and runs whether or not a
  user is logged on. Anneal does no embedding, so it only needs the mem-chroma service up.
#>
param(
  [string]$At  = '3:00AM',
  [string]$Day = 'Sunday'
)
$ErrorActionPreference = 'Stop'
$app    = $PSScriptRoot
$task   = 'mem-anneal'
$runner = Join-Path $app 'run-anneal.cmd'

$action    = New-ScheduledTaskAction -Execute $runner -WorkingDirectory $app
$trigger   = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $At
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName $task -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force `
    -Description 'Weekly: evict stale, under-recalled Chroma memory-log bits (mem anneal).' | Out-Null

Get-ScheduledTask -TaskName $task | Format-List TaskName, State
$info = Get-ScheduledTaskInfo -TaskName $task
Write-Host "next run: $($info.NextRunTime)"
Write-Host "done."
