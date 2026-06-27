param(
    [string]$Phase = "33A",
    [string]$Branch = "",
    [switch]$SkipInstall,
    [switch]$SkipPytest,
    [switch]$AllowDirty,
    [switch]$NoGitPull
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Invoke-NativeChecked {
    param(
        [string]$Exe,
        [string[]]$Args,
        [string]$StepName
    )
    Write-Step $StepName
    Write-Host "> $Exe $($Args -join ' ')"
    & $Exe @Args
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "$StepName failed with exit code $code"
    }
}

function Get-NativeOutput {
    param(
        [string]$Exe,
        [string[]]$Args
    )
    $output = & $Exe @Args 2>&1
    $code = $LASTEXITCODE
    return [PSCustomObject]@{ Code = $code; Output = $output }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..")
Set-Location $repoRoot

$phaseKey = $Phase.Trim().ToUpperInvariant()
$runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$runDir = Join-Path $repoRoot "reports\operator_runs"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$logPath = Join-Path $runDir "phase_${phaseKey}_${runStamp}.txt"
$latestPath = Join-Path $runDir "phase_${phaseKey}_latest.txt"
$summaryPath = Join-Path $runDir "phase_${phaseKey}_${runStamp}.json"
$latestSummaryPath = Join-Path $runDir "phase_${phaseKey}_latest.json"

$status = "FAIL"
$startedAt = (Get-Date).ToString("o")
$failure = ""

Start-Transcript -Path $logPath -Force | Out-Null
try {
    Write-Step "Operator phase runner started"
    Write-Host "Phase      : $phaseKey"
    Write-Host "Repo root  : $repoRoot"
    Write-Host "Log path   : $logPath"
    Write-Host "SkipInstall: $($SkipInstall.IsPresent)"
    Write-Host "SkipPytest : $($SkipPytest.IsPresent)"

    Invoke-NativeChecked -Exe "git" -Args @("rev-parse", "--is-inside-work-tree") -StepName "Verify git repository"

    $dirtyBefore = Get-NativeOutput -Exe "git" -Args @("status", "--short")
    Write-Step "Initial git status"
    if ($dirtyBefore.Output) {
        $dirtyBefore.Output | ForEach-Object { Write-Host $_ }
    } else {
        Write-Host "clean"
    }

    if ($Branch.Trim() -ne "" -and -not $NoGitPull.IsPresent) {
        if ($dirtyBefore.Output -and -not $AllowDirty.IsPresent) {
            throw "Working tree is dirty. Commit/stash changes or rerun with -AllowDirty. Branch switch/pull blocked."
        }
        Invoke-NativeChecked -Exe "git" -Args @("fetch", "origin", $Branch) -StepName "Fetch target branch"
        Invoke-NativeChecked -Exe "git" -Args @("checkout", $Branch) -StepName "Checkout target branch"
        Invoke-NativeChecked -Exe "git" -Args @("pull", "--ff-only", "origin", $Branch) -StepName "Fast-forward target branch"
    } elseif ($NoGitPull.IsPresent) {
        Write-Step "Git pull skipped by -NoGitPull"
    } else {
        Write-Step "No target branch supplied; staying on current branch"
    }

    $branchOut = Get-NativeOutput -Exe "git" -Args @("branch", "--show-current")
    $commitOut = Get-NativeOutput -Exe "git" -Args @("rev-parse", "--short", "HEAD")
    Write-Step "Resolved git ref"
    Write-Host "Branch: $($branchOut.Output)"
    Write-Host "Commit: $($commitOut.Output)"

    $venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        if ($SkipInstall.IsPresent) {
            Write-Step "Virtualenv missing; using system python because -SkipInstall was supplied"
            $pythonExe = "python"
        } else {
            Invoke-NativeChecked -Exe "py" -Args @("-3.11", "-m", "venv", ".venv") -StepName "Create Python 3.11 virtualenv"
            $pythonExe = $venvPython
        }
    } else {
        $pythonExe = $venvPython
    }

    Invoke-NativeChecked -Exe $pythonExe -Args @("--version") -StepName "Verify Python"

    if (-not $SkipInstall.IsPresent) {
        Invoke-NativeChecked -Exe $pythonExe -Args @("-m", "pip", "install", "--upgrade", "pip") -StepName "Upgrade pip"
        Invoke-NativeChecked -Exe $pythonExe -Args @("-m", "pip", "install", "-e", ".") -StepName "Install project editable"
    } else {
        Write-Step "Install skipped by -SkipInstall"
    }

    if (-not $SkipPytest.IsPresent) {
        Invoke-NativeChecked -Exe $pythonExe -Args @("-m", "pytest") -StepName "Run pytest"
    } else {
        Write-Step "Pytest skipped by -SkipPytest"
    }

    $phaseTools = @{
        "33A" = "tools\generate_33a_production_freeze_baseline_audit.py"
        "33B" = "tools\generate_33b_api_fail_closed_security_audit.py"
        "33C" = "tools\generate_33c_lifecycle_separation_audit.py"
    }

    if ($phaseTools.ContainsKey($phaseKey)) {
        $toolPath = Join-Path $repoRoot $phaseTools[$phaseKey]
        if (Test-Path $toolPath) {
            Invoke-NativeChecked -Exe $pythonExe -Args @($toolPath) -StepName "Run phase $phaseKey audit tool"
        } else {
            Write-Step "Phase $phaseKey audit tool not found yet"
            Write-Host "Expected: $toolPath"
            Write-Host "This is acceptable only for runner bootstrap. The real phase patch must add this tool."
        }
    } else {
        Write-Step "No audit tool mapping for phase $phaseKey"
    }

    $finalStatus = Get-NativeOutput -Exe "git" -Args @("status", "--short")
    Write-Step "Final git status"
    if ($finalStatus.Output) {
        $finalStatus.Output | ForEach-Object { Write-Host $_ }
    } else {
        Write-Host "clean"
    }

    $status = "PASS"
}
catch {
    $failure = $_.Exception.Message
    Write-Host ""
    Write-Host "RUNNER_FAILURE: $failure"
    $status = "FAIL"
}
finally {
    $endedAt = (Get-Date).ToString("o")
    $branchFinal = ""
    $commitFinal = ""
    try { $branchFinal = (& git branch --show-current 2>$null | Out-String).Trim() } catch { $branchFinal = "unknown" }
    try { $commitFinal = (& git rev-parse --short HEAD 2>$null | Out-String).Trim() } catch { $commitFinal = "unknown" }

    $summary = [ordered]@{
        phase = $phaseKey
        status = $status
        started_at = $startedAt
        ended_at = $endedAt
        branch = $branchFinal
        commit = $commitFinal
        log_path = $logPath
        failure = $failure
        skip_install = $SkipInstall.IsPresent
        skip_pytest = $SkipPytest.IsPresent
    }
    $summary | ConvertTo-Json -Depth 5 | Set-Content -Path $summaryPath -Encoding UTF8
    Copy-Item -Path $summaryPath -Destination $latestSummaryPath -Force

    Stop-Transcript | Out-Null
    Copy-Item -Path $logPath -Destination $latestPath -Force

    Write-Host ""
    Write-Host "Operator runner status: $status"
    Write-Host "Latest log           : $latestPath"
    Write-Host "Latest summary       : $latestSummaryPath"

    if ($status -ne "PASS") {
        exit 1
    }
}
