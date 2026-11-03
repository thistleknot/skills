<#
.SYNOPSIS
    Smoke test for Windows batch troubleshooting through OpenCode.

.DESCRIPTION
    Runs OpenCode against C:\Users\user\Documents\dev\spec_dec.bat and asserts that:
      1. the batch is executed from the named workspace
      2. the agent does not loop on bash/cmd wrapper narration
      3. a concrete removed-flag error is surfaced quickly

    This is the regression test for the Windows batch-shell dithering failure mode.
#>
param(
    [string]$WorkDir = "C:\Users\user\Documents\dev",
    [string]$ScriptName = "spec_dec.bat",
    [int]$TimeoutSeconds = 45
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert([string]$label, [bool]$condition) {
    if ($condition) {
        Write-Host "  [PASS] $label" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $label" -ForegroundColor Red
        $script:failed = $true
    }
}

$script:failed = $false
$scriptPath = Join-Path $WorkDir $ScriptName
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing smoke-test batch file: $scriptPath"
}

$prompt = @"
From the workspace root, troubleshoot the Windows batch file $ScriptName.

Rules:
- Execute it exactly once with the native Windows launcher: cmd /c .\$ScriptName
- Do not narrate shell selection.
- Do not try bash, quoting variants, or a second wrapper.
- If the batch fails, return the concrete failing flag and replacement guidance from stderr.
- Stop after the first decisive result.
"@

$opencodeCmd = Get-Command opencode -ErrorAction Stop
$stdout = [IO.Path]::GetTempFileName()
$stderr = "$stdout.err"
$escapedPrompt = $prompt.Replace('"', '\"')
$cmdLine = "powershell.exe -ExecutionPolicy Bypass -File `"$($opencodeCmd.Path)`" run --dir `"$WorkDir`" `"$escapedPrompt`""
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/d", "/c", $cmdLine `
    -WorkingDirectory $WorkDir `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru -NoNewWindow

if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    try { $proc.Kill() } catch { }
    throw "OpenCode smoke test timed out after $TimeoutSeconds seconds"
}

$out = ""
if (Test-Path -LiteralPath $stdout) { $out += Get-Content -LiteralPath $stdout -Raw }
if (Test-Path -LiteralPath $stderr) { $out += "`n" + (Get-Content -LiteralPath $stderr -Raw) }
$sw.Stop()

Write-Host ""
Write-Host "== smoke_spec_dec ==" -ForegroundColor Cyan
Write-Host "  workdir : $WorkDir"
Write-Host "  script  : $scriptPath"
Write-Host "  elapsed : $([math]::Round($sw.Elapsed.TotalSeconds, 1))s"
Write-Host ""

Assert "completed within timeout budget" ($sw.Elapsed.TotalSeconds -le $TimeoutSeconds)
Assert "no bash/cmd shell dithering loop" (-not ($out -match "Actually, I'll use bash" -or $out -match "Wait, I'll use bash"))
Assert "batch failure surfaced" ($out -match "argument has been removed" -or $out -match "FAIL_FLAG:")
Assert "current removed flag identified" ($out -match "--draft-min" -or $out -match "--spec-draft-n-min")

Remove-Item $stdout, $stderr -Force -ErrorAction SilentlyContinue

if ($failed) { exit 1 }
