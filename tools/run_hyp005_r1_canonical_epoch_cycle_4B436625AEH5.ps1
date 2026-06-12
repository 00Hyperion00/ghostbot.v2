# 4B.4.3.6.6.25AE-H5 HYP-005-R1 canonical epoch fail-closed no-order shadow cycle.
# Safety: no training, reload, paper trade, live trade, POST request or order action.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:PYTHONPATH = "src"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

$CanonicalReportsDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "reports\hyp005_r1_canonical"))
$ForbiddenLegacyDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "reports\hyp005_r1_isolated"))
$ForbiddenReportsRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "reports"))
$Symbols = "ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT"

if ($CanonicalReportsDir -eq $ForbiddenLegacyDir -or $CanonicalReportsDir -eq $ForbiddenReportsRoot) {
    throw "HYP005_R1_CANONICAL_REPORTS_DIR_ISOLATION_VIOLATION"
}

New-Item -ItemType Directory -Force -Path $CanonicalReportsDir | Out-Null

$CandidateSpec = Get-ChildItem -Path (Join-Path $ProjectRoot "reports") -Recurse -Filter "hyp005_r1_runtime_candidate_spec.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $CandidateSpec) {
    throw "HYP005_R1_RUNTIME_CANDIDATE_SPEC_NOT_FOUND"
}

Write-Host "[25AE-H5] Starting canonical no-order shadow cycle..."
Write-Host "[25AE-H5] Canonical reports dir: $CanonicalReportsDir"

python tools/run_hyp005_shadow_observation_logger_4B436625V.py `
    --candidate-spec-json "$($CandidateSpec.FullName)" `
    --symbols $Symbols `
    --interval 4h `
    --days 30 `
    --base-url https://api.binance.com `
    --out-dir "$CanonicalReportsDir" `
    --review-ok
if ($LASTEXITCODE -ne 0) { throw "HYP005_CANONICAL_25V_FAILED" }

$LatestLogger = Get-ChildItem "$CanonicalReportsDir\4B436625V_hyp005_shadow_observation_logger_*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
$LatestLoggerLedgerJsonl = Get-ChildItem "$CanonicalReportsDir\4B436625V_hyp005_shadow_observation_ledger_*.jsonl" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $LatestLogger -or $null -eq $LatestLoggerLedgerJsonl) {
    throw "HYP005_CANONICAL_25V_ARTIFACTS_NOT_FOUND"
}

python tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py `
    --candidate-spec-json "$($CandidateSpec.FullName)" `
    --logger-report-json "$($LatestLogger.FullName)" `
    --ledger-jsonl "$($LatestLoggerLedgerJsonl.FullName)" `
    --reports-dir "$CanonicalReportsDir" `
    --strict-explicit-chain `
    --symbols $Symbols `
    --interval 4h `
    --days 30 `
    --base-url https://api.binance.com `
    --out-dir "$CanonicalReportsDir" `
    --review-ok
if ($LASTEXITCODE -ne 0) { throw "HYP005_CANONICAL_25X_FAILED" }

$LatestCollection = Get-ChildItem "$CanonicalReportsDir\4B436625X_hyp005_shadow_collection_orchestrator_*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
$LatestMergedLedgerJsonl = Get-ChildItem "$CanonicalReportsDir\4B436625X_hyp005_shadow_merged_ledger_*.jsonl" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $LatestCollection -or $null -eq $LatestMergedLedgerJsonl) {
    throw "HYP005_CANONICAL_25X_ARTIFACTS_NOT_FOUND"
}

python tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py `
    --collection-report-json "$($LatestCollection.FullName)" `
    --ledger-jsonl "$($LatestMergedLedgerJsonl.FullName)" `
    --reports-dir "$CanonicalReportsDir" `
    --strict-explicit-chain `
    --out-dir "$CanonicalReportsDir" `
    --review-ok
if ($LASTEXITCODE -ne 0) { throw "HYP005_CANONICAL_25W_FAILED" }

$LatestAcceptance = Get-ChildItem "$CanonicalReportsDir\4B436625W_hyp005_shadow_observation_acceptance_*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $LatestAcceptance) {
    throw "HYP005_CANONICAL_25W_ARTIFACT_NOT_FOUND"
}

python tools/run_hyp005_shadow_operator_runbook_4B436625Y.py `
    --candidate-spec-json "$($CandidateSpec.FullName)" `
    --logger-report-json "$($LatestLogger.FullName)" `
    --collection-report-json "$($LatestCollection.FullName)" `
    --acceptance-report-json "$($LatestAcceptance.FullName)" `
    --ledger-jsonl "$($LatestMergedLedgerJsonl.FullName)" `
    --reports-dir "$CanonicalReportsDir" `
    --strict-explicit-chain `
    --symbols $Symbols `
    --interval 4h `
    --days 30 `
    --base-url https://api.binance.com `
    --out-dir "$CanonicalReportsDir" `
    --review-ok
if ($LASTEXITCODE -ne 0) { throw "HYP005_CANONICAL_25Y_FAILED" }

python tools/check_hyp005_shadow_observation_identity_chain_4B436625VH2.py `
    --reports-dir "$CanonicalReportsDir" `
    --require-runtime-chain `
    --once-json
if ($LASTEXITCODE -ne 0) { throw "HYP005_CANONICAL_25VH2_CHAIN_CHECK_FAILED" }

python tools/check_hyp005_r1_canonical_epoch_hardening_4B436625AEH5.py `
    --project-root "$ProjectRoot" `
    --reports-dir "$CanonicalReportsDir" `
    --once-json
if ($LASTEXITCODE -ne 0) { throw "HYP005_CANONICAL_25AEH5_CHAIN_CHECK_FAILED" }

Write-Host "[25AE-H5] Canonical cycle PASS. Paper/live/order remain disabled."
