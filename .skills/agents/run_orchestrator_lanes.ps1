<#
.SYNOPSIS
    Launch Gemma and DeepSeek V4 Flash orchestrator lanes side-by-side.

.DESCRIPTION
    Opens two OpenCode sessions pinned to the orchestrator agent in separate
    Windows Terminal tabs when `wt` is available, otherwise falls back to two
    PowerShell windows.

    Fresh sessions:
      .\run_orchestrator_lanes.ps1

    Fork the same existing session into two model-specific lanes:
      .\run_orchestrator_lanes.ps1 -SessionId ses_123

    Fork the most recent session into both lanes:
      .\run_orchestrator_lanes.ps1 -ContinueLast

    Preview the exact launch commands without opening windows:
      .\run_orchestrator_lanes.ps1 -ContinueLast -Preview

    Notes:
    - The top-level process always uses `--agent orchestrator`.
    - When `-SessionId` or `-ContinueLast` is used, both lanes add `--fork` so
      Gemma and V4 Flash each get their own branch of the same starting state.
#>
param(
    [ValidateSet("", "gemma", "flash")]
    [string]$Lane = "",

    [string]$Workspace = "",

    [string]$SessionId = "",

    [switch]$ContinueLast,

    [switch]$Preview
)

$agentsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = $MyInvocation.MyCommand.Path

if (-not $Workspace) {
    $Workspace = Split-Path $agentsDir -Parent
}

if ($SessionId -and $ContinueLast) {
    throw "Use either -SessionId or -ContinueLast, not both."
}

if (-not (Test-Path -LiteralPath $Workspace)) {
    throw "Workspace does not exist: $Workspace"
}

function Get-LaneConfig {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("gemma", "flash")]
        [string]$Name
    )

    switch ($Name) {
        "gemma" {
            return @{
                Name  = "gemma"
                Title = "Gemma Orchestrator"
                Model = "openrouter/google/gemma-4-26b-a4b-it"
            }
        }
        "flash" {
            return @{
                Name  = "flash"
                Title = "DeepSeek V4 Flash Orchestrator"
                Model = "openrouter/deepseek/deepseek-v4-flash"
            }
        }
    }
}

function Get-OpencodeArgs {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Model
    )

    $args = @("--agent", "orchestrator", "--model", $Model)

    if ($SessionId) {
        $args += @("--session", $SessionId, "--fork")
    }
    elseif ($ContinueLast) {
        $args += @("--continue", "--fork")
    }

    return $args
}

function Get-ChildPowerShellArgs {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("gemma", "flash")]
        [string]$ChildLane
    )

    $args = @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-File", $scriptPath,
        "-Lane", $ChildLane,
        "-Workspace", $Workspace
    )

    if ($SessionId) {
        $args += @("-SessionId", $SessionId)
    }
    elseif ($ContinueLast) {
        $args += "-ContinueLast"
    }

    return $args
}

function Format-ArgumentList {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$Args
    )

    $quoted = foreach ($arg in $Args) {
        if ($arg -match '[\s";]') {
            '"' + ($arg -replace '"', '\"') + '"'
        }
        else {
            $arg
        }
    }

    return ($quoted -join " ")
}

if ($Lane) {
    $laneConfig = Get-LaneConfig -Name $Lane
    $launchArgs = Get-OpencodeArgs -Model $laneConfig.Model

    try {
        $host.ui.RawUI.WindowTitle = $laneConfig.Title
    }
    catch {
    }

    Set-Location $Workspace
    Write-Host "Launching $($laneConfig.Title) in $Workspace"
    Write-Host ("opencode " + (Format-ArgumentList -Args $launchArgs))
    & opencode @launchArgs
    exit $LASTEXITCODE
}

$gemmaPsArgs = Get-ChildPowerShellArgs -ChildLane "gemma"
$flashPsArgs = Get-ChildPowerShellArgs -ChildLane "flash"

if ($Preview) {
    $gemmaPreview = "powershell " + (Format-ArgumentList -Args $gemmaPsArgs)
    $flashPreview = "powershell " + (Format-ArgumentList -Args $flashPsArgs)
    $wtPreview =
        "wt new-tab --title ""Gemma Orchestrator"" -d ""$Workspace"" powershell " +
        (Format-ArgumentList -Args $gemmaPsArgs) +
        " ; new-tab --title ""DeepSeek V4 Flash Orchestrator"" -d ""$Workspace"" powershell " +
        (Format-ArgumentList -Args $flashPsArgs)

    Write-Host "Windows Terminal:"
    Write-Host $wtPreview
    Write-Host ""
    Write-Host "Fallback PowerShell windows:"
    Write-Host $gemmaPreview
    Write-Host $flashPreview
    exit 0
}

$wtCommand = Get-Command wt -ErrorAction SilentlyContinue
if ($wtCommand) {
    $wtArgs = @("new-tab", "--title", "Gemma Orchestrator", "-d", $Workspace, "powershell")
    $wtArgs += $gemmaPsArgs
    $wtArgs += ";"
    $wtArgs += @("new-tab", "--title", "DeepSeek V4 Flash Orchestrator", "-d", $Workspace, "powershell")
    $wtArgs += $flashPsArgs

    & $wtCommand.Source @wtArgs
    exit $LASTEXITCODE
}

Start-Process -FilePath "powershell" -WorkingDirectory $Workspace -ArgumentList $gemmaPsArgs | Out-Null
Start-Process -FilePath "powershell" -WorkingDirectory $Workspace -ArgumentList $flashPsArgs | Out-Null
