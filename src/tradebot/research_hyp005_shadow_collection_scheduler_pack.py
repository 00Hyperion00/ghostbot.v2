from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HYP005_SHADOW_SCHEDULER_PACK_CONTRACT_VERSION = "4B.4.3.6.6.25Z"
HYP005_SHADOW_SCHEDULER_PACK_HOTFIX_VERSION = "4B.4.3.6.6.25Z_H1"
REPORT_PREFIX = "4B436625Z_hyp005_shadow_collection_scheduler_pack"
PACK_PREFIX = "4B436625Z_hyp005_windows_task_scheduler_pack"

HYP005_SCHEDULER_PACK_READY = "HYP005_SHADOW_SCHEDULER_PACK_READY"
HYP005_SCHEDULER_PACK_BLOCK = "HYP005_SHADOW_SCHEDULER_PACK_BLOCK"
NO_ORDER_SCHEDULER_PACK_ONLY = True
WINDOWS_TASK_SCHEDULER_MANUAL_IMPORT_ONLY = True
PAPER_TRANSITION_READINESS_IS_NOT_PAPER_PERMISSION = True
NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED = "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"


@dataclass(frozen=True)
class Hyp005SchedulerPackLimits:
    min_shadow_sample_target: int = 30
    default_interval: str = "4h"
    default_days: int = 30
    default_task_name: str = "TradeBot_HYP005_NoOrderShadowCollection"
    default_run_every_hours: int = 4


@dataclass(frozen=True)
class SchedulerPackRequest:
    reports_dir: str = "reports"
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
    interval: str = "4h"
    days: int = 30
    base_url: str = "https://api.binance.com"
    task_name: str = "TradeBot_HYP005_NoOrderShadowCollection"
    run_every_hours: int = 4
    python_executable: str = "python"


@dataclass(frozen=True)
class SchedulerPackArtifacts:
    pack_dir: str
    shadow_cycle_ps1: str
    register_task_ps1: str
    task_xml: str
    operator_readme_md: str
    generated_paths: list[str]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def write_text(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _as_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _find_latest(pattern: str, reports_dir: str | Path) -> Path | None:
    root = Path(reports_dir)
    if not root.exists():
        return None
    matches = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _normalize_symbols(symbols: str | Iterable[str] | None) -> tuple[str, ...]:
    if symbols is None:
        return ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
    if isinstance(symbols, str):
        parts = [part.strip().upper() for part in symbols.split(",")]
    else:
        parts = [str(part).strip().upper() for part in symbols]
    return tuple(part for part in parts if part)


def _safe_get(payload: dict[str, Any], key: str, default: Any = None) -> Any:
    return payload.get(key, default)


def _latest_candidate_spec_path(audit: dict[str, Any], reports_dir: str | Path) -> str:
    explicit = audit.get("candidate_spec_json") or audit.get("latest_candidate_spec_json")
    if explicit:
        return str(explicit)
    latest = _find_latest("4B436625U_hyp005_no_order_shadow_candidate_spec_*.json", reports_dir)
    return str(latest) if latest is not None else "reports\\4B436625U_hyp005_no_order_shadow_candidate_spec_latest.json"


def validate_25y_audit_for_scheduler_pack(audit: dict[str, Any]) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    warnings: list[str] = []

    if audit.get("contract_version") not in {"4B.4.3.6.6.25Y", HYP005_SHADOW_SCHEDULER_PACK_CONTRACT_VERSION}:
        # 25Y reports created by older patch may omit contract_version in pasted summaries; rely on decision too.
        if audit.get("decision") != "HYP005_SHADOW_OPERATOR_AUDIT_READY":
            reasons.append("HYP005_25Y_OPERATOR_AUDIT_NOT_READY")

    if audit.get("decision") != "HYP005_SHADOW_OPERATOR_AUDIT_READY":
        reasons.append("HYP005_25Y_OPERATOR_AUDIT_DECISION_NOT_READY")

    if not _as_bool(audit.get("no_order_operator_audit_only", audit.get("no_order_scheduler_pack_only", True))):
        reasons.append("NO_ORDER_OPERATOR_AUDIT_FLAG_MISSING")

    if _as_bool(audit.get("approved_for_paper_candidate")):
        reasons.append("UNSAFE_PAPER_APPROVAL_DETECTED")
    if _as_bool(audit.get("approved_for_live_real")):
        reasons.append("UNSAFE_LIVE_APPROVAL_DETECTED")
    if _as_bool(audit.get("approved_for_training_candidate")):
        reasons.append("UNSAFE_TRAINING_APPROVAL_DETECTED")

    if audit.get("latest_logger_decision") not in {None, "HYP005_SHADOW_OBSERVATION_LOGGER_READY"}:
        reasons.append("LATEST_LOGGER_NOT_READY")
    if audit.get("latest_collection_decision") not in {None, "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY"}:
        reasons.append("LATEST_COLLECTION_ORCHESTRATOR_NOT_READY")

    if audit.get("paper_transition_ready") is True:
        warnings.append("PAPER_TRANSITION_READY_REQUIRES_SEPARATE_ENABLEMENT")
    else:
        warnings.append("PAPER_TRANSITION_STILL_BLOCKED_OR_PENDING")

    shadow_count = int(audit.get("shadow_observation_count") or 0)
    target = int(audit.get("shadow_sample_target") or 30)
    if shadow_count < target:
        warnings.append("SHADOW_COLLECTION_IN_PROGRESS")

    return sorted(set(reasons)), sorted(set(warnings))


def _build_shadow_cycle_ps1(request: SchedulerPackRequest, candidate_spec_json: str) -> str:
    symbols = ",".join(request.symbols)
    return f"""# Auto-generated by {HYP005_SHADOW_SCHEDULER_PACK_CONTRACT_VERSION}
# HYP-005 no-order shadow collection cycle.
# Safety: this script does not train, reload, paper trade, live trade, or send orders.

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

Write-Host "[HYP-005] Starting no-order shadow cycle..."

{request.python_executable} tools/run_hyp005_shadow_observation_logger_4B436625V.py `
  --candidate-spec-json "{candidate_spec_json}" `
  --symbols "{symbols}" `
  --interval "{request.interval}" `
  --days {request.days} `
  --base-url "{request.base_url}" `
  --out-dir "{request.reports_dir}" `
  --review-ok

{request.python_executable} tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py `
  --reports-dir "{request.reports_dir}" `
  --include-all `
  --symbols "{symbols}" `
  --interval "{request.interval}" `
  --days {request.days} `
  --base-url "{request.base_url}" `
  --out-dir "{request.reports_dir}" `
  --review-ok

{request.python_executable} tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py `
  --reports-dir "{request.reports_dir}" `
  --include-all `
  --out-dir "{request.reports_dir}" `
  --review-ok

{request.python_executable} tools/run_hyp005_shadow_operator_runbook_4B436625Y.py `
  --reports-dir "{request.reports_dir}" `
  --include-all `
  --symbols "{symbols}" `
  --interval "{request.interval}" `
  --days {request.days} `
  --base-url "{request.base_url}" `
  --out-dir "{request.reports_dir}" `
  --review-ok

Write-Host "[HYP-005] No-order shadow cycle completed. Paper/live/order permissions remain closed."
"""


def _build_register_task_ps1(request: SchedulerPackRequest) -> str:
    return f"""# Auto-generated by {HYP005_SHADOW_SCHEDULER_PACK_CONTRACT_VERSION}
# Manual registration helper for Windows Task Scheduler.
# It registers only the no-order shadow collection cycle script.
# Review before running. This script still does not enable paper/live trading.

$ErrorActionPreference = "Stop"
$PackDir = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $PackDir
$TaskName = "{request.task_name}"
$CycleScript = Join-Path $PackDir "run_hyp005_shadow_cycle_no_order.ps1"

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$CycleScript`""
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddHours(4) -RepetitionInterval (New-TimeSpan -Hours {request.run_every_hours}) -RepetitionDuration (New-TimeSpan -Days 3650)

# 25Z-H1 compatibility hotfix:
# Some Windows PowerShell ScheduledTasks builds do not expose -DisallowStartIfOnBatteries
# or -AllowStartIfOnBatteries as New-ScheduledTaskSettingsSet parameters. Build the
# settings with only broadly supported parameters, then set optional battery fields
# only when the returned object exposes them.
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable
$SettingPropertyNames = @($Settings.PSObject.Properties.Name)
if ($SettingPropertyNames -contains "DisallowStartIfOnBatteries") {{
  $Settings.DisallowStartIfOnBatteries = $true
}}
if ($SettingPropertyNames -contains "StopIfGoingOnBatteries") {{
  $Settings.StopIfGoingOnBatteries = $true
}}
if ($SettingPropertyNames -contains "AllowStartIfOnBatteries") {{
  $Settings.AllowStartIfOnBatteries = $false
}}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "HYP-005 no-order shadow collection cycle. No paper/live/order actions." -Force

Write-Host "Registered task: $TaskName"
Write-Host "Cycle script: $CycleScript"
Write-Host "Safety: no paper/live/order actions are enabled by this task."
"""


def _build_task_xml(request: SchedulerPackRequest) -> str:
    return f"""<?xml version=\"1.0\" encoding=\"UTF-16\"?>
<Task version=\"1.4\" xmlns=\"http://schemas.microsoft.com/windows/2004/02/mit/task\">
  <RegistrationInfo>
    <Description>HYP-005 no-order shadow collection cycle. Generated by {HYP005_SHADOW_SCHEDULER_PACK_CONTRACT_VERSION}. No paper/live/order actions.</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <Repetition>
        <Interval>PT{request.run_every_hours}H</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
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
  <Actions Context=\"Author\">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-NoProfile -ExecutionPolicy Bypass -File run_hyp005_shadow_cycle_no_order.ps1</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def _build_readme_md(request: SchedulerPackRequest, audit: dict[str, Any]) -> str:
    symbols = ",".join(request.symbols)
    return f"""# HYP-005 No-Order Shadow Collection Scheduler Pack

- contract_version: `{HYP005_SHADOW_SCHEDULER_PACK_CONTRACT_VERSION}`
- task_name: `{request.task_name}`
- cadence_hours: `{request.run_every_hours}`
- symbols: `{symbols}`
- interval: `{request.interval}`
- days: `{request.days}`
- base_url: `{request.base_url}`

## Safety

This pack is no-order only. It does not train, reload, paper trade, live trade, mutate config, or send orders.

## Current State From 25Y

- latest_logger_decision: `{audit.get('latest_logger_decision')}`
- latest_collection_decision: `{audit.get('latest_collection_decision')}`
- latest_acceptance_decision: `{audit.get('latest_acceptance_decision')}`
- shadow_observation_count: `{audit.get('shadow_observation_count', 0)}`
- shadow_sample_target: `{audit.get('shadow_sample_target', 30)}`
- paper_transition_ready: `{audit.get('paper_transition_ready', False)}`

## Manual Steps

1. Review `run_hyp005_shadow_cycle_no_order.ps1`.
2. Run it manually once from PowerShell.
3. Review the generated 25V/25X/25W/25Y reports.
4. Only after review, optionally run `register_hyp005_shadow_cycle_task.ps1` as a Windows Task Scheduler helper.

## Important

Paper-transition readiness is not paper permission. Paper/live remain blocked until a separate explicit enablement gate exists and passes.
"""


def write_scheduler_pack(
    *,
    out_dir: str | Path,
    timestamp: str,
    request: SchedulerPackRequest,
    candidate_spec_json: str,
    audit: dict[str, Any],
) -> SchedulerPackArtifacts:
    pack_dir = Path(out_dir) / f"{PACK_PREFIX}_{timestamp}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    shadow_cycle_ps1 = pack_dir / "run_hyp005_shadow_cycle_no_order.ps1"
    register_task_ps1 = pack_dir / "register_hyp005_shadow_cycle_task.ps1"
    task_xml = pack_dir / "hyp005_shadow_collection_task.xml"
    operator_readme_md = pack_dir / "README_HYP005_NO_ORDER_SCHEDULER.md"

    write_text(shadow_cycle_ps1, _build_shadow_cycle_ps1(request, candidate_spec_json))
    write_text(register_task_ps1, _build_register_task_ps1(request))
    write_text(task_xml, _build_task_xml(request))
    write_text(operator_readme_md, _build_readme_md(request, audit))

    generated = [str(shadow_cycle_ps1), str(register_task_ps1), str(task_xml), str(operator_readme_md)]
    return SchedulerPackArtifacts(
        pack_dir=str(pack_dir),
        shadow_cycle_ps1=str(shadow_cycle_ps1),
        register_task_ps1=str(register_task_ps1),
        task_xml=str(task_xml),
        operator_readme_md=str(operator_readme_md),
        generated_paths=generated,
    )


def build_hyp005_shadow_scheduler_pack_report(
    *,
    operator_audit: dict[str, Any],
    request: SchedulerPackRequest | None = None,
    out_dir: str | Path = "reports",
    timestamp: str | None = None,
    review_ok: bool = False,
) -> dict[str, Any]:
    request = request or SchedulerPackRequest()
    timestamp = timestamp or utc_timestamp()
    reasons, warnings = validate_25y_audit_for_scheduler_pack(operator_audit)

    if not review_ok:
        reasons.append("REVIEW_OK_REQUIRED")

    candidate_spec_json = _latest_candidate_spec_path(operator_audit, request.reports_dir)

    decision = HYP005_SCHEDULER_PACK_BLOCK if reasons else HYP005_SCHEDULER_PACK_READY
    ok = not reasons

    artifacts: SchedulerPackArtifacts | None = None
    if ok:
        artifacts = write_scheduler_pack(
            out_dir=out_dir,
            timestamp=timestamp,
            request=request,
            candidate_spec_json=candidate_spec_json,
            audit=operator_audit,
        )

    shadow_count = int(operator_audit.get("shadow_observation_count") or 0)
    target = int(operator_audit.get("shadow_sample_target") or 30)
    progress_pct = round((shadow_count / target * 100.0), 6) if target > 0 else 0.0

    payload: dict[str, Any] = {
        "contract_version": HYP005_SHADOW_SCHEDULER_PACK_CONTRACT_VERSION,
        "phase": "4B.4.3.6.6.25Z",
        "report_type": "hyp005_shadow_collection_scheduler_pack",
        "decision": decision,
        "ok": ok,
        "hypothesis_id": operator_audit.get("hypothesis_id", "HYP-005"),
        "branch_name": operator_audit.get("branch_name", "liquidity_sweep_reversal_vol_compression"),
        "selected_strategy_family": operator_audit.get("selected_strategy_family", "long_liquidity_sweep_reversal"),
        "no_order_scheduler_pack_only": True,
        "windows_task_scheduler_manual_import_only": True,
        "scheduler_pack_ready": ok,
        "task_name": request.task_name,
        "run_every_hours": request.run_every_hours,
        "symbols": list(request.symbols),
        "interval": request.interval,
        "days": request.days,
        "base_url": request.base_url,
        "shadow_observation_count": shadow_count,
        "shadow_sample_target": target,
        "progress_pct": progress_pct,
        "latest_logger_decision": operator_audit.get("latest_logger_decision"),
        "latest_collection_decision": operator_audit.get("latest_collection_decision"),
        "latest_acceptance_decision": operator_audit.get("latest_acceptance_decision"),
        "paper_transition_ready": bool(operator_audit.get("paper_transition_ready")),
        "approved_for_scheduler_pack": ok,
        "approved_for_shadow_collection": ok,
        "approved_for_paper_transition_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "post_requests_allowed": False,
        "reason_codes": sorted(set(reasons + ([NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED] if ok else []))),
        "warnings": warnings,
        "candidate_spec_json": candidate_spec_json,
        "artifacts": asdict(artifacts) if artifacts else None,
        "recommendation": (
            "HYP-005 no-order Windows scheduler pack is ready. Review scripts manually before optional Task Scheduler registration; do not train, reload, paper trade, live trade, or send orders."
            if ok
            else "HYP-005 scheduler pack is blocked. Fix missing 25Y/25V/25X/25W chain evidence; do not automate collection yet."
        ),
        "guardrails": {
            "no_order_scheduler_pack_only": True,
            "windows_task_scheduler_manual_import_only": True,
            "paper_transition_readiness_is_not_paper_permission": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
        },
    }
    return payload


def render_report_md(report: dict[str, Any]) -> str:
    artifacts = report.get("artifacts") or {}
    lines = [
        "# 4B.4.3.6.6.25Z HYP-005 Shadow Collection Scheduler Pack",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- strategy: `{report.get('selected_strategy_family')}`",
        f"- task_name: `{report.get('task_name')}`",
        f"- cadence_hours: `{report.get('run_every_hours')}`",
        f"- shadow progress: `{report.get('shadow_observation_count')}/{report.get('shadow_sample_target')}` ({report.get('progress_pct')}%)",
        f"- paper_transition_ready: `{report.get('paper_transition_ready')}`",
        "",
        "## Guardrails",
        "",
        "- no_order_scheduler_pack_only: `True`",
        "- windows_task_scheduler_manual_import_only: `True`",
        "- post_requests_allowed: `False`",
        "- config_mutation_performed: `False`",
        "- order_actions_performed: `False`",
        "- reload_performed: `False`",
        "- live_real_allowed: `False`",
        "",
        "## Artifacts",
        "",
    ]
    if artifacts:
        for key in ["shadow_cycle_ps1", "register_task_ps1", "task_xml", "operator_readme_md"]:
            lines.append(f"- {key}: `{artifacts.get(key)}`")
    else:
        lines.append("- Scheduler artifacts were not written because the gate blocked.")
    lines.extend([
        "",
        "## Reason Codes",
        "",
        f"`{report.get('reason_codes', [])}`",
        "",
        "## Warnings",
        "",
        f"`{report.get('warnings', [])}`",
        "",
        "## Recommendation",
        "",
        str(report.get("recommendation", "")),
        "",
        "## Policy",
        "",
        "This pack does not enable paper/live trading. Task Scheduler registration is manual-review only and runs the no-order shadow collection cycle.",
    ])
    return "\n".join(lines) + "\n"


def write_scheduler_pack_report(report: dict[str, Any], out_dir: str | Path, timestamp: str | None = None) -> tuple[str, str]:
    timestamp = timestamp or utc_timestamp()
    root = Path(out_dir)
    json_path = root / f"{REPORT_PREFIX}_{timestamp}.json"
    md_path = root / f"{REPORT_PREFIX}_{timestamp}.md"
    write_json(json_path, report)
    write_text(md_path, render_report_md(report))
    return str(json_path), str(md_path)


def discover_latest_operator_audit(reports_dir: str | Path) -> Path | None:
    return _find_latest("4B436625Y_hyp005_shadow_operator_daily_audit_*.json", reports_dir)
