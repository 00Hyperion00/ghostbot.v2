from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HYP005_R1_SHADOW_SCHEDULER_REGENERATION_CONTRACT_VERSION = "4B.4.3.6.6.25AE-H1"
HYP005_R1_SHADOW_SCHEDULER_HOTFIX_VERSION = "4B.4.3.6.6.25AE-H1"
HYP005_R1_REPORTS_DIR_ISOLATION_HOTFIX_VERSION = "4B.4.3.6.6.25AE-H2"
HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION = "4B.4.3.6.6.25AE-H3"
R1_RUNTIME_PATH_JOIN_SAFETY_ENFORCED = "R1_RUNTIME_PATH_JOIN_SAFETY_ENFORCED"
R1_CANONICAL_BRANCH_COMPATIBILITY_ENFORCED = "R1_CANONICAL_BRANCH_COMPATIBILITY_ENFORCED"
R1_STRICT_EXPLICIT_REPORT_CHAINING_ENFORCED = "R1_STRICT_EXPLICIT_REPORT_CHAINING_ENFORCED"
HYP005_R1_REPORTS_DIR_ISOLATION_ENFORCED = "HYP005_R1_REPORTS_DIR_ISOLATION_ENFORCED"
R1_RUNTIME_CHAIN_READS_ONLY_SCOPED_REPORTS_DIR = "R1_RUNTIME_CHAIN_READS_ONLY_SCOPED_REPORTS_DIR"
R1_EXPLICIT_REPORT_CHAINING_ENFORCED = "R1_EXPLICIT_REPORT_CHAINING_ENFORCED"
R1_EXISTING_TASK_DISABLE_BEFORE_REPLACEMENT_REQUIRED = "R1_EXISTING_TASK_DISABLE_BEFORE_REPLACEMENT_REQUIRED"
HYP005_R1_SHADOW_SCHEDULER_PACK_READY = "HYP005_R1_SHADOW_SCHEDULER_PACK_READY"
HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK = "HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK"

EXPECTED_SOURCE_DECISION = "HYP005_R1_REVALIDATION_PLANNING_READY"
EXPECTED_REFINED_BRANCH_ID = "HYP-005-R1"
EXPECTED_FRESH_LEDGER_NAMESPACE = "HYP005_R1"
EXPECTED_BASELINE_TASK_NAME = "TradeBot_HYP005_NoOrderShadowCollection"
DEFAULT_R1_TASK_NAME = "TradeBot_HYP005_R1_NoOrderShadowCollection"
DEFAULT_R1_REPORTS_SUBDIR = "reports\\hyp005_r1_isolated"
DEFAULT_REFINED_SYMBOLS = (
    "ADAUSDT",
    "BNBUSDT",
    "BTCUSDT",
    "ETHUSDT",
    "LINKUSDT",
    "LTCUSDT",
    "SOLUSDT",
    "XRPUSDT",
)
DEFAULT_PRUNED_SYMBOLS = ("AVAXUSDT", "DOGEUSDT")
REPORT_PREFIX = "4B436625AE_hyp005_r1_shadow_scheduler_regeneration_pack"
PACK_PREFIX = "4B436625AE_hyp005_r1_windows_task_scheduler_pack"

BASELINE_TASK_DISABLE_CONFIRMED_BY_OPERATOR = "BASELINE_TASK_DISABLE_CONFIRMED_BY_OPERATOR"
SOURCE_25AD_R1_REVALIDATION_PLAN_CONFIRMED = "SOURCE_25AD_R1_REVALIDATION_PLAN_CONFIRMED"
HYP005_R1_FRESH_LEDGER_NAMESPACE_ENFORCED = "HYP005_R1_FRESH_LEDGER_NAMESPACE_ENFORCED"
LEGACY_BASELINE_OBSERVATIONS_NOT_REUSED = "LEGACY_BASELINE_OBSERVATIONS_NOT_REUSED"
EIGHT_SYMBOL_REFINED_SET_ENFORCED = "EIGHT_SYMBOL_REFINED_SET_ENFORCED"
WINDOWS_TASK_REGISTRATION_REQUIRES_MANUAL_OPERATOR_ACTION = "WINDOWS_TASK_REGISTRATION_REQUIRES_MANUAL_OPERATOR_ACTION"
NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED = "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"
NO_AUTOMATIC_WINDOWS_TASK_MUTATION = "NO_AUTOMATIC_WINDOWS_TASK_MUTATION"
R1_SHADOW_SAMPLE_TARGET_VALIDATION_NORMALIZED = "R1_SHADOW_SAMPLE_TARGET_VALIDATION_NORMALIZED"


@dataclass(frozen=True)
class Hyp005R1SchedulerPackLimits:
    shadow_sample_target: int = 30
    refined_symbol_count: int = 8
    run_every_hours: int = 4
    interval: str = "4h"
    days: int = 30


@dataclass(frozen=True)
class Hyp005R1SchedulerPackRequest:
    reports_dir: str = "reports"
    out_dir: str = "reports"
    r1_reports_subdir: str = DEFAULT_R1_REPORTS_SUBDIR
    baseline_task_name: str = EXPECTED_BASELINE_TASK_NAME
    r1_task_name: str = DEFAULT_R1_TASK_NAME
    run_every_hours: int = 4
    interval: str = "4h"
    days: int = 30
    base_url: str = "https://api.binance.com"
    python_executable: str = "python"


@dataclass(frozen=True)
class Hyp005R1SchedulerPackArtifacts:
    pack_dir: str
    r1_runtime_candidate_spec_json: str
    shadow_cycle_ps1: str
    register_task_ps1: str
    task_xml: str
    operator_readme_md: str
    generated_paths: list[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_file_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _latest_file(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _sorted_unique_symbols(values: Iterable[Any]) -> list[str]:
    return sorted({str(value).strip().upper() for value in values if str(value).strip()})


def _coerce_int(value: Any) -> int | None:
    """Normalize JSON scalar values without accepting lossy numeric conversions."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def _resolve_shadow_sample_target(source_25ad: dict[str, Any], spec: dict[str, Any]) -> tuple[int | None, str | None, dict[str, Any]]:
    """Resolve the canonical 25AD revalidation target.

    25AD stores the authoritative target inside refined_candidate_spec. Older
    fixtures also exposed a top-level value. The H1 hotfix accepts both shapes
    and normalizes string/int JSON scalar representations.
    """
    limits = source_25ad.get("limits") if isinstance(source_25ad.get("limits"), dict) else {}
    candidates: tuple[tuple[str, Any], ...] = (
        ("refined_candidate_spec.shadow_sample_target", spec.get("shadow_sample_target")),
        ("shadow_sample_target", source_25ad.get("shadow_sample_target")),
        ("limits.revalidation_sample_target", limits.get("revalidation_sample_target")),
    )
    diagnostic_candidates: list[dict[str, Any]] = []
    for source, raw_value in candidates:
        normalized = _coerce_int(raw_value)
        diagnostic_candidates.append({"source": source, "raw_value": raw_value, "normalized_value": normalized})
        if normalized is not None:
            return normalized, source, {"candidates": diagnostic_candidates, "selected_source": source, "normalized_value": normalized}
    return None, None, {"candidates": diagnostic_candidates, "selected_source": None, "normalized_value": None}


def _resolve_starting_unique_shadow_count(source_25ad: dict[str, Any], spec: dict[str, Any]) -> int | None:
    root_value = _coerce_int(source_25ad.get("starting_unique_shadow_observation_count"))
    if root_value is not None:
        return root_value
    return _coerce_int(spec.get("starting_unique_shadow_observation_count"))


def _extract_plan_symbols(source_25ad: dict[str, Any]) -> tuple[list[str], list[str]]:
    spec = source_25ad.get("refined_candidate_spec") if isinstance(source_25ad.get("refined_candidate_spec"), dict) else {}
    refined = source_25ad.get("recommended_refined_symbols")
    if not isinstance(refined, list):
        refined = spec.get("symbols")
    if not isinstance(refined, list):
        refined_arg = str(source_25ad.get("recommended_refined_symbols_arg") or spec.get("symbols_arg") or "")
        refined = [part for part in refined_arg.split(",") if part.strip()]
    pruned = source_25ad.get("recommended_pruned_symbols")
    if not isinstance(pruned, list):
        pruned = spec.get("excluded_symbols")
    return _sorted_unique_symbols(refined if isinstance(refined, list) else []), _sorted_unique_symbols(pruned if isinstance(pruned, list) else [])


def _resolve_latest_25ad(reports_dir: Path, input_json: Path | None) -> tuple[dict[str, Any], Path | None]:
    path = input_json or _latest_file(reports_dir, "4B436625AD_hyp005_baseline_freeze_refined_revalidation_planning_*.json")
    return (_read_json(path), path) if path is not None and path.exists() else ({}, None)


def _resolve_latest_25u_candidate_spec(reports_dir: Path, source_candidate_spec_json: Path | None) -> tuple[dict[str, Any], Path | None]:
    path = source_candidate_spec_json or _latest_file(reports_dir, "4B436625U_hyp005_no_order_shadow_candidate_spec_*.json")
    if path is None or not path.exists():
        return {}, None
    payload = _read_json(path)
    nested = payload.get("candidate_spec")
    return (nested, path) if isinstance(nested, dict) else (payload, path)


def _validate_25ad_plan(source_25ad: dict[str, Any], *, baseline_task_disabled_confirmed: bool) -> tuple[list[str], list[str], list[str], list[str], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []
    refined, pruned = _extract_plan_symbols(source_25ad)
    spec = source_25ad.get("refined_candidate_spec") if isinstance(source_25ad.get("refined_candidate_spec"), dict) else {}
    resolved_target, resolved_target_source, target_validation = _resolve_shadow_sample_target(source_25ad, spec)
    resolved_starting_count = _resolve_starting_unique_shadow_count(source_25ad, spec)

    if source_25ad.get("decision") != EXPECTED_SOURCE_DECISION:
        blockers.append("SOURCE_25AD_R1_REVALIDATION_PLAN_NOT_READY")
    if source_25ad.get("refined_branch_id") != EXPECTED_REFINED_BRANCH_ID:
        blockers.append("REFINED_BRANCH_ID_NOT_HYP005_R1")
    if source_25ad.get("fresh_ledger_namespace") != EXPECTED_FRESH_LEDGER_NAMESPACE:
        blockers.append("FRESH_LEDGER_NAMESPACE_NOT_HYP005_R1")
    if resolved_starting_count != 0:
        blockers.append("R1_STARTING_UNIQUE_SHADOW_COUNT_NOT_ZERO")
    if resolved_target != 30:
        blockers.append("R1_SHADOW_SAMPLE_TARGET_NOT_30")
    if source_25ad.get("approved_for_next_scheduler_pack_patch") is not True:
        blockers.append("NEXT_SCHEDULER_PACK_PATCH_NOT_APPROVED")
    if spec.get("legacy_baseline_observation_reuse_allowed") is not False:
        blockers.append("LEGACY_BASELINE_OBSERVATION_REUSE_NOT_EXPLICITLY_BLOCKED")
    if source_25ad.get("baseline_observations_reused_in_refined_branch") is True or spec.get("legacy_baseline_observations_reused") is True:
        blockers.append("LEGACY_BASELINE_OBSERVATION_REUSE_DETECTED")
    if refined != sorted(DEFAULT_REFINED_SYMBOLS):
        blockers.append("REFINED_EIGHT_SYMBOL_SET_MISMATCH")
    if pruned != sorted(DEFAULT_PRUNED_SYMBOLS):
        blockers.append("PRUNED_SYMBOL_SET_MISMATCH")
    if set(refined).intersection(pruned):
        blockers.append("PRUNED_SYMBOL_PRESENT_IN_REFINED_SET")
    if not baseline_task_disabled_confirmed:
        blockers.append("BASELINE_TASK_DISABLED_CONFIRMATION_REQUIRED")

    for unsafe_field in ("approved_for_paper_candidate", "approved_for_live_real", "approved_for_training_candidate"):
        if source_25ad.get(unsafe_field) is True:
            blockers.append(f"UNSAFE_{unsafe_field.upper()}_DETECTED")
    if source_25ad.get("post_requests_allowed") is True:
        blockers.append("UNSAFE_POST_REQUEST_PERMISSION_DETECTED")

    if source_25ad.get("approved_for_scheduler_regeneration") is False:
        warnings.append("SCHEDULER_REGENERATION_REQUIRES_SEPARATE_OPERATOR_PATCH_CONFIRMED")
    if resolved_target_source != "shadow_sample_target":
        warnings.append(R1_SHADOW_SAMPLE_TARGET_VALIDATION_NORMALIZED)
    warnings.append("WINDOWS_TASK_REGISTRATION_REMAINS_MANUAL")
    target_validation.update(
        {
            "hotfix_version": HYP005_R1_SHADOW_SCHEDULER_HOTFIX_VERSION,
            "runtime_chain_hotfix_version": HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION,
            "reports_dir_isolation_hotfix_version": HYP005_R1_REPORTS_DIR_ISOLATION_HOTFIX_VERSION,
            "reports_dir_isolation_enforced": True,
            "runtime_path_join_safety_enforced": True,
            "canonical_branch_compatibility_enforced": True,
            "strict_explicit_report_chaining_enforced": True,
            "runtime_chain_reads_only_scoped_reports_dir": True,
            "explicit_report_chaining_enforced": True,
            "baseline_reports_root_read_by_runtime_chain": False,
            "existing_r1_task_disable_before_replacement_required": True,
            "expected_shadow_sample_target": 30,
            "resolved_shadow_sample_target": resolved_target,
            "resolved_starting_unique_shadow_observation_count": resolved_starting_count,
        }
    )
    return sorted(set(blockers)), sorted(set(warnings)), refined, pruned, target_validation


def _runtime_candidate_spec(source_25u_spec: dict[str, Any], source_25ad: dict[str, Any], refined: list[str], pruned: list[str]) -> dict[str, Any]:
    runtime = copy.deepcopy(source_25u_spec) if source_25u_spec else {}
    if not isinstance(runtime, dict):
        runtime = {}
    runtime.update(
        {
            "candidate_spec_contract_version": HYP005_R1_SHADOW_SCHEDULER_REGENERATION_CONTRACT_VERSION,
            "candidate_spec_type": "hyp005_r1_eight_symbol_fresh_no_order_runtime_candidate_spec",
            "hypothesis_id": "HYP-005",
            "branch_name": "liquidity_sweep_reversal_vol_compression",
            "refined_branch_name": "liquidity_sweep_reversal_vol_compression_r1_pruned_symbol_revalidation",
            "candidate_variant": "r1_pruned_symbol_revalidation",
            "refined_branch_id": EXPECTED_REFINED_BRANCH_ID,
            "fresh_ledger_namespace": EXPECTED_FRESH_LEDGER_NAMESPACE,
            "symbols": refined,
            "symbols_arg": ",".join(refined),
            "excluded_symbols": pruned,
            "starting_unique_shadow_observation_count": 0,
            "shadow_sample_target": 30,
            "legacy_baseline_observation_reuse_allowed": False,
            "legacy_baseline_observations_reused": False,
            "baseline_observation_carry_forward_allowed": False,
            "source_25ad_contract_version": source_25ad.get("contract_version"),
            "source_25ad_decision": source_25ad.get("decision"),
            "baseline_evidence_digest_sha256": source_25ad.get("baseline_evidence_digest_sha256")
            or (source_25ad.get("baseline_evidence_snapshot") or {}).get("baseline_evidence_digest_sha256"),
        }
    )
    runtime.setdefault("strategy_family", "long_liquidity_sweep_reversal")
    guardrails = runtime.get("guardrails") if isinstance(runtime.get("guardrails"), dict) else {}
    guardrails.update(
        {
            "no_order_shadow_only": True,
            "observation_only": True,
            "runtime_probe_only": True,
            "orders_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "training_allowed": False,
            "model_reload_allowed": False,
            "post_requests_allowed": False,
            "paper_transition_requires_new_gate": True,
            "live_transition_requires_separate_gate": True,
        }
    )
    runtime["guardrails"] = guardrails
    return runtime


def _build_cycle_ps1(request: Hyp005R1SchedulerPackRequest, refined: list[str]) -> str:
    symbols = ",".join(refined)
    return f'''# Auto-generated by {HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION}
# HYP-005-R1 eight-symbol isolated fresh-ledger no-order shadow cycle.
# Safety: no training, reload, paper trade, live trade, POST request, or order action.

$ErrorActionPreference = "Stop"
$PackDir = $PSScriptRoot
$ReportsDir = Split-Path -Parent $PackDir
$ProjectRoot = Split-Path -Parent $ReportsDir
if (-not (Test-Path (Join-Path $ProjectRoot "tools"))) {{
  $ProjectRoot = Split-Path -Parent $PackDir
}}
Set-Location $ProjectRoot

$env:PYTHONPATH = "src"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$R1ReportsDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "{request.r1_reports_subdir}"))
$ExpectedR1ReportsDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "{DEFAULT_R1_REPORTS_SUBDIR}"))
$CandidateSpec = Join-Path $PackDir "hyp005_r1_runtime_candidate_spec.json"

if ($R1ReportsDir -ne $ExpectedR1ReportsDir) {{
  throw "HYP-005-R1 reports-dir isolation violation. Expected: $ExpectedR1ReportsDir Actual: $R1ReportsDir"
}}
if ($R1ReportsDir -eq [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "reports"))) {{
  throw "HYP-005-R1 reports-dir isolation violation: project reports root is forbidden."
}}
New-Item -ItemType Directory -Force -Path $R1ReportsDir | Out-Null

Write-Host "[HYP-005-R1] Starting isolated eight-symbol fresh-ledger no-order shadow cycle..."
Write-Host "[HYP-005-R1] Fresh namespace: {EXPECTED_FRESH_LEDGER_NAMESPACE}"
Write-Host "[HYP-005-R1] Isolated reports dir: $R1ReportsDir"

{request.python_executable} tools/run_hyp005_shadow_observation_logger_4B436625V.py `
  --candidate-spec-json "$CandidateSpec" `
  --symbols "{symbols}" `
  --interval "{request.interval}" `
  --days {request.days} `
  --base-url "{request.base_url}" `
  --out-dir "$R1ReportsDir" `
  --review-ok

$LatestLoggerReport = Get-ChildItem -File -Path (Join-Path $R1ReportsDir "4B436625V_hyp005_shadow_observation_logger_*.json") |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
$LatestLoggerLedger = Get-ChildItem -File -Path (Join-Path $R1ReportsDir "4B436625V_hyp005_shadow_observation_ledger_*.json") |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $LatestLoggerReport -or -not $LatestLoggerLedger) {{
  throw "HYP-005-R1 isolated logger report/ledger not found."
}}

{request.python_executable} tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py `
  --candidate-spec-json "$CandidateSpec" `
  --logger-report-json "$($LatestLoggerReport.FullName)" `
  --ledger-json "$($LatestLoggerLedger.FullName)" `
  --reports-dir "$R1ReportsDir" `
  --strict-explicit-chain `
  --symbols "{symbols}" `
  --interval "{request.interval}" `
  --days {request.days} `
  --base-url "{request.base_url}" `
  --out-dir "$R1ReportsDir" `
  --review-ok

$LatestCollectionReport = Get-ChildItem -File -Path (Join-Path $R1ReportsDir "4B436625X_hyp005_shadow_collection_orchestrator_*.json") |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
$LatestMergedLedger = Get-ChildItem -File -Path (Join-Path $R1ReportsDir "4B436625X_hyp005_shadow_merged_ledger_*.json") |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $LatestCollectionReport -or -not $LatestMergedLedger) {{
  throw "HYP-005-R1 isolated collection report/merged ledger not found."
}}

{request.python_executable} tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py `
  --collection-report-json "$($LatestCollectionReport.FullName)" `
  --ledger-json "$($LatestMergedLedger.FullName)" `
  --reports-dir "$R1ReportsDir" `
  --strict-explicit-chain `
  --out-dir "$R1ReportsDir" `
  --review-ok

$LatestAcceptanceReport = Get-ChildItem -File -Path (Join-Path $R1ReportsDir "4B436625W_hyp005_shadow_observation_acceptance_*.json") |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $LatestAcceptanceReport) {{ throw "HYP-005-R1 isolated acceptance report not found." }}

{request.python_executable} tools/run_hyp005_shadow_operator_runbook_4B436625Y.py `
  --candidate-spec-json "$CandidateSpec" `
  --logger-report-json "$($LatestLoggerReport.FullName)" `
  --collection-report-json "$($LatestCollectionReport.FullName)" `
  --acceptance-report-json "$($LatestAcceptanceReport.FullName)" `
  --ledger-json "$($LatestMergedLedger.FullName)" `
  --reports-dir "$R1ReportsDir" `
  --strict-explicit-chain `
  --symbols "{symbols}" `
  --interval "{request.interval}" `
  --days {request.days} `
  --base-url "{request.base_url}" `
  --out-dir "$R1ReportsDir" `
  --review-ok

Write-Host "[HYP-005-R1] Cycle completed. R1 reports-dir isolated; baseline reports root was not read. Paper/live/order remain disabled."
'''


def _build_register_ps1(request: Hyp005R1SchedulerPackRequest) -> str:
    return f'''# Auto-generated by {HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION}
# Manual operator-reviewed Windows Task Scheduler registration helper.
# Safety: baseline task and any existing R1 task must be Disabled before replacement.

$ErrorActionPreference = "Stop"
$PackDir = $PSScriptRoot
$BaselineTaskName = "{request.baseline_task_name}"
$TaskName = "{request.r1_task_name}"
$CycleScript = Join-Path $PackDir "run_hyp005_r1_shadow_cycle_no_order.ps1"

$BaselineTask = Get-ScheduledTask -TaskName $BaselineTaskName -ErrorAction Stop
if ($BaselineTask.State -ne "Disabled") {{
  throw "Baseline task '$BaselineTaskName' must be Disabled before HYP-005-R1 registration. Current state: $($BaselineTask.State)"
}}
$ExistingR1Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $ExistingR1Task -and $ExistingR1Task.State -ne "Disabled") {{
  throw "Existing R1 task '$TaskName' must be Disabled before H2 replacement. Current state: $($ExistingR1Task.State)"
}}

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$CycleScript`""
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddHours(4) -RepetitionInterval (New-TimeSpan -Hours {request.run_every_hours}) -RepetitionDuration (New-TimeSpan -Days 3650)
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable
$SettingPropertyNames = @($Settings.PSObject.Properties.Name)
if ($SettingPropertyNames -contains "DisallowStartIfOnBatteries") {{ $Settings.DisallowStartIfOnBatteries = $true }}
if ($SettingPropertyNames -contains "StopIfGoingOnBatteries") {{ $Settings.StopIfGoingOnBatteries = $true }}
if ($SettingPropertyNames -contains "AllowStartIfOnBatteries") {{ $Settings.AllowStartIfOnBatteries = $false }}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "HYP-005-R1 isolated fresh-ledger no-order shadow collection cycle. No paper/live/order actions." -Force

Write-Host "Registered task: $TaskName"
Write-Host "Baseline task confirmed Disabled: $BaselineTaskName"
Write-Host "Existing R1 task disable/replacement guard: PASS"
Write-Host "Cycle script: $CycleScript"
Write-Host "Safety: HYP005_R1 isolated fresh ledger only; no paper/live/order actions are enabled."
'''


def _build_task_xml(request: Hyp005R1SchedulerPackRequest) -> str:
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>HYP-005-R1 eight-symbol fresh-ledger no-order shadow collection. Generated by {HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION}. No paper/live/order actions.</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <Repetition><Interval>PT{request.run_every_hours}H</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>
      <StartBoundary>2026-01-01T04:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
  </Settings>
  <Actions Context="Author">
    <Exec><Command>powershell.exe</Command><Arguments>-NoProfile -ExecutionPolicy Bypass -File run_hyp005_r1_shadow_cycle_no_order.ps1</Arguments></Exec>
  </Actions>
</Task>
'''


def _build_readme(request: Hyp005R1SchedulerPackRequest, refined: list[str], pruned: list[str]) -> str:
    return f'''# HYP-005-R1 Eight-Symbol Fresh-Ledger No-Order Scheduler Pack

Generated by `{HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION}`.

## Safety contract

- Baseline task must be disabled before registration.
- Windows Task Scheduler registration remains a manual operator action.
- Fresh ledger namespace: `{EXPECTED_FRESH_LEDGER_NAMESPACE}`.
- Isolated refined reports directory: `{request.r1_reports_subdir}`.
- Project-level `reports` root is forbidden as an R1 runtime input.
- 25X / 25W / 25Y read only the isolated R1 reports directory.
- Logger, collection, and acceptance reports are explicitly chained.
- Legacy baseline reports and ledgers are not read by the generated cycle.
- Existing R1 task must be Disabled before H2 replacement registration.
- Paper/live/order/training/reload permissions remain closed.

## Refined symbols

`{','.join(refined)}`

## Pruned symbols

`{','.join(pruned)}`

## Register after review

```powershell
powershell -ExecutionPolicy Bypass -File .\\register_hyp005_r1_shadow_cycle_task.ps1
```
'''


def build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
    reports_dir: Path | str,
    *,
    out_dir: Path | str = "reports",
    input_json: Path | str | None = None,
    source_candidate_spec_json: Path | str | None = None,
    request: Hyp005R1SchedulerPackRequest | None = None,
    baseline_task_disabled_confirmed: bool = False,
    review_ok: bool = False,
    timestamp: str | None = None,
) -> dict[str, Any]:
    reports_path = Path(reports_dir)
    out_path = Path(out_dir)
    req = request or Hyp005R1SchedulerPackRequest(reports_dir=str(reports_path), out_dir=str(out_path))
    requested_r1_subdir = str(req.r1_reports_subdir).replace("/", "\\").lower()
    expected_r1_subdir = str(DEFAULT_R1_REPORTS_SUBDIR).replace("/", "\\").lower()
    source_25ad, source_25ad_path = _resolve_latest_25ad(reports_path, Path(input_json) if input_json else None)
    source_25u, source_25u_path = _resolve_latest_25u_candidate_spec(reports_path, Path(source_candidate_spec_json) if source_candidate_spec_json else None)
    blockers, warnings, refined, pruned, target_validation = _validate_25ad_plan(source_25ad, baseline_task_disabled_confirmed=baseline_task_disabled_confirmed)
    if requested_r1_subdir != expected_r1_subdir:
        blockers.append("R1_REPORTS_SUBDIR_NOT_ISOLATED")
    if not review_ok:
        blockers.append("REVIEW_OK_REQUIRED")
    if source_25ad_path is None:
        blockers.append("SOURCE_25AD_REPORT_NOT_FOUND")
    if source_25u_path is None:
        blockers.append("SOURCE_25U_RUNTIME_CANDIDATE_SPEC_NOT_FOUND")
    blockers = sorted(set(blockers))
    stamp = timestamp or _utc_file_stamp()
    artifacts: Hyp005R1SchedulerPackArtifacts | None = None

    if not blockers:
        pack_dir = out_path / f"{PACK_PREFIX}_{stamp}"
        pack_dir.mkdir(parents=True, exist_ok=True)
        candidate_spec = _runtime_candidate_spec(source_25u, source_25ad, refined, pruned)
        candidate_spec_path = pack_dir / "hyp005_r1_runtime_candidate_spec.json"
        cycle_path = pack_dir / "run_hyp005_r1_shadow_cycle_no_order.ps1"
        register_path = pack_dir / "register_hyp005_r1_shadow_cycle_task.ps1"
        xml_path = pack_dir / "TradeBot_HYP005_R1_NoOrderShadowCollection.xml"
        readme_path = pack_dir / "README_HYP005_R1_SCHEDULER_PACK.md"
        _write_json(candidate_spec_path, candidate_spec)
        _write_text(cycle_path, _build_cycle_ps1(req, refined))
        _write_text(register_path, _build_register_ps1(req))
        _write_text(xml_path, _build_task_xml(req))
        _write_text(readme_path, _build_readme(req, refined, pruned))
        generated = [str(path) for path in (candidate_spec_path, cycle_path, register_path, xml_path, readme_path)]
        artifacts = Hyp005R1SchedulerPackArtifacts(
            pack_dir=str(pack_dir),
            r1_runtime_candidate_spec_json=str(candidate_spec_path),
            shadow_cycle_ps1=str(cycle_path),
            register_task_ps1=str(register_path),
            task_xml=str(xml_path),
            operator_readme_md=str(readme_path),
            generated_paths=generated,
        )

    decision = HYP005_R1_SHADOW_SCHEDULER_PACK_READY if not blockers else HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK
    reason_codes = []
    if decision == HYP005_R1_SHADOW_SCHEDULER_PACK_READY:
        reason_codes = [
            BASELINE_TASK_DISABLE_CONFIRMED_BY_OPERATOR,
            SOURCE_25AD_R1_REVALIDATION_PLAN_CONFIRMED,
            HYP005_R1_FRESH_LEDGER_NAMESPACE_ENFORCED,
            LEGACY_BASELINE_OBSERVATIONS_NOT_REUSED,
            EIGHT_SYMBOL_REFINED_SET_ENFORCED,
            WINDOWS_TASK_REGISTRATION_REQUIRES_MANUAL_OPERATOR_ACTION,
            NO_AUTOMATIC_WINDOWS_TASK_MUTATION,
            NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED,
            R1_SHADOW_SAMPLE_TARGET_VALIDATION_NORMALIZED,
            HYP005_R1_REPORTS_DIR_ISOLATION_ENFORCED,
            R1_RUNTIME_CHAIN_READS_ONLY_SCOPED_REPORTS_DIR,
            R1_EXPLICIT_REPORT_CHAINING_ENFORCED,
            R1_EXISTING_TASK_DISABLE_BEFORE_REPLACEMENT_REQUIRED,
            R1_RUNTIME_PATH_JOIN_SAFETY_ENFORCED,
            R1_CANONICAL_BRANCH_COMPATIBILITY_ENFORCED,
            R1_STRICT_EXPLICIT_REPORT_CHAINING_ENFORCED,
        ]
    return {
        "contract_version": HYP005_R1_SHADOW_SCHEDULER_REGENERATION_CONTRACT_VERSION,
        "hotfix_version": HYP005_R1_SHADOW_SCHEDULER_HOTFIX_VERSION,
        "runtime_chain_hotfix_version": HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION,
        "reports_dir_isolation_hotfix_version": HYP005_R1_REPORTS_DIR_ISOLATION_HOTFIX_VERSION,
        "reports_dir_isolation_enforced": True,
        "runtime_path_join_safety_enforced": True,
        "canonical_branch_compatibility_enforced": True,
        "strict_explicit_report_chaining_enforced": True,
        "runtime_chain_reads_only_scoped_reports_dir": True,
        "explicit_report_chaining_enforced": True,
        "baseline_reports_root_read_by_runtime_chain": False,
        "existing_r1_task_disable_before_replacement_required": True,
        "report_type": "hyp005_r1_eight_symbol_no_order_shadow_scheduler_regeneration_pack",
        "generated_at_utc": _utc_now_iso(),
        "decision": decision,
        "ok": decision == HYP005_R1_SHADOW_SCHEDULER_PACK_READY,
        "source_25ad_report": str(source_25ad_path) if source_25ad_path else None,
        "source_25u_runtime_candidate_spec": str(source_25u_path) if source_25u_path else None,
        "refined_branch_id": EXPECTED_REFINED_BRANCH_ID,
        "fresh_ledger_namespace": EXPECTED_FRESH_LEDGER_NAMESPACE,
        "r1_reports_subdir": req.r1_reports_subdir,
        "isolated_runtime_reports_dir": req.r1_reports_subdir,
        "baseline_task_name": req.baseline_task_name,
        "r1_task_name": req.r1_task_name,
        "baseline_task_disabled_confirmed": baseline_task_disabled_confirmed,
        "recommended_pruned_symbols": pruned,
        "refined_symbols": refined,
        "refined_symbols_arg": ",".join(refined),
        "starting_unique_shadow_observation_count": 0,
        "shadow_sample_target": 30,
        "shadow_sample_target_validation": target_validation,
        "run_every_hours": req.run_every_hours,
        "approved_for_scheduler_pack_generation": decision == HYP005_R1_SHADOW_SCHEDULER_PACK_READY,
        "approved_for_scheduler_registration": False,
        "scheduler_registration_requires_manual_operator_action": True,
        "scheduler_registration_script_checks_baseline_disabled_state": True,
        "baseline_scheduler_disable_performed": False,
        "windows_task_mutation_performed": False,
        "config_mutation_performed": False,
        "legacy_baseline_observation_reuse_allowed": False,
        "legacy_baseline_observations_reused": False,
        "training_performed": False,
        "reload_performed": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_trading_started": False,
        "live_trading_started": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
        "reason_codes": sorted(reason_codes),
        "warnings": warnings,
        "blockers": blockers,
        "artifacts": asdict(artifacts) if artifacts else None,
        "recommendation": (
            "HYP-005-R1 isolated fresh-ledger scheduler pack is ready for manual operator registration after the baseline task and any existing R1 task are confirmed Disabled. "
            "Keep paper/live/order/training/reload disabled; 25X/25W/25Y must read only the isolated R1 reports directory."
            if decision == HYP005_R1_SHADOW_SCHEDULER_PACK_READY
            else "HYP-005-R1 scheduler regeneration pack is blocked. Resolve blockers; do not mutate Windows tasks, reuse baseline observations, train, reload, paper trade, live trade, or send orders."
        ),
    }


def write_hyp005_r1_shadow_scheduler_regeneration_pack_report(report: dict[str, Any], out_dir: Path | str, *, timestamp: str | None = None) -> dict[str, Path]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or _utc_file_stamp()
    json_path = out_path / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_path / f"{REPORT_PREFIX}_{stamp}.md"
    _write_json(json_path, report)
    lines = [
        f"# {HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION} HYP-005-R1 Scheduler Regeneration Pack",
        "",
        f"- decision: `{report['decision']}`",
        f"- refined_branch_id: `{report['refined_branch_id']}`",
        f"- fresh_ledger_namespace: `{report['fresh_ledger_namespace']}`",
        f"- refined_symbols: `{report['refined_symbols_arg']}`",
        f"- baseline_task_disabled_confirmed: `{report['baseline_task_disabled_confirmed']}`",
        f"- approved_for_scheduler_registration: `{report['approved_for_scheduler_registration']}`",
        f"- approved_for_paper_candidate: `{report['approved_for_paper_candidate']}`",
        f"- approved_for_live_real: `{report['approved_for_live_real']}`",
        "",
        f"Recommendation: {report['recommendation']}",
    ]
    _write_text(md_path, "\n".join(lines) + "\n")
    return {"report_json": json_path, "report_md": md_path}
