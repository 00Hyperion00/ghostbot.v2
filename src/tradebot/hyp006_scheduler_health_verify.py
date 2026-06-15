from __future__ import annotations

import json
import locale
import os
import subprocess
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28E"
SOURCE_REGISTRATION_APPROVAL_CONTRACT_VERSION = "4B.4.3.6.6.28D"
SOURCE_CYCLE_CONTRACT_VERSION = "4B.4.3.6.6.28D"
HYPOTHESIS_ID = "HYP-006"
BRANCH_ID = "HYP-006-R1"
BRANCH_NAME = "failed_downside_sweep_reversal_continuation_short"
STRATEGY_FAMILY = "short_failed_liquidity_sweep_continuation"
PROPOSED_SCHEDULER_TASK_NAME = "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection"
REPORT_PREFIX = "4B436628E_hyp006_r1_scheduler_execution_health_verify"
LEDGER_CONTINUITY_PREFIX = "4B436628E_hyp006_r1_ledger_continuity_evidence"
NEXT_REQUIRED_GATE = "28F_HYP006_SHADOW_OPERATOR_COCKPIT_DASHBOARD_SEED_AND_ACCEPTANCE_BASELINE"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []


def load_json(path: str | os.PathLike[str] | None) -> Any:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_jsonl(path: str | os.PathLike[str] | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        text = line.strip()
        if not text:
            continue
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            rows.append(loaded)
    return rows


def _decode_subprocess_bytes(data: bytes | None) -> str:
    if not data:
        return ""
    candidates = ["utf-8-sig", locale.getpreferredencoding(False), "cp1254", "cp1252"]
    if os.name == "nt":
        candidates.append("mbcs")
    seen: set[str] = set()
    for encoding in candidates:
        if not encoding or encoding.lower() in seen:
            continue
        seen.add(encoding.lower())
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
        except LookupError:
            continue
    return data.decode("utf-8", errors="replace")


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{resolved.name}.",
        suffix=".tmp",
        dir=resolved.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp_path.replace(resolved)
    finally:
        temp_path.unlink(missing_ok=True)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "ready", "running", "success"}
    return bool(value)


def _as_int(value: Any, default: int = -1) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _contains(text: Any, needle: str) -> bool:
    return needle.lower() in str(text or "").lower()


def validate_registration_approval_report(report: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    payload = _mapping(report)
    reasons: list[str] = []
    if payload.get("contract_version") != SOURCE_REGISTRATION_APPROVAL_CONTRACT_VERSION:
        reasons.append("REGISTRATION_APPROVAL_CONTRACT_VERSION_MISMATCH")
    if payload.get("decision") != "HYP006_R1_CANONICAL_NO_ORDER_SHADOW_REGISTRATION_APPROVED":
        reasons.append("REGISTRATION_APPROVAL_DECISION_NOT_APPROVED")
    if payload.get("approved_for_canonical_no_order_shadow_registration") is not True:
        reasons.append("CANONICAL_REGISTRATION_NOT_APPROVED")
    if payload.get("approved_for_shadow_collection") is not True:
        reasons.append("NO_ORDER_SHADOW_COLLECTION_NOT_APPROVED")
    for unsafe_flag in ("approved_for_paper_candidate", "approved_for_live_real", "approved_for_training_candidate"):
        if payload.get(unsafe_flag) is not False:
            reasons.append(f"UNSAFE_APPROVAL_{unsafe_flag.upper()}")
    for mutation_flag in (
        "config_mutation_performed",
        "scheduler_mutation_performed",
        "scheduler_task_created",
        "scheduler_task_modified",
        "trading_action_performed",
        "training_performed",
        "reload_performed",
        "order_actions_performed",
    ):
        if payload.get(mutation_flag) is not False:
            reasons.append(f"UNSAFE_REGISTRATION_{mutation_flag.upper()}")
    return not reasons, reasons


def validate_cycle_report(report: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    payload = _mapping(report)
    reasons: list[str] = []
    if payload.get("contract_version") != SOURCE_CYCLE_CONTRACT_VERSION:
        reasons.append("CYCLE_CONTRACT_VERSION_MISMATCH")
    if payload.get("decision") != "HYP006_R1_CANONICAL_NO_ORDER_SHADOW_COLLECTION_CYCLE_READY":
        reasons.append("CYCLE_DECISION_NOT_READY")
    if payload.get("branch_id") != BRANCH_ID:
        reasons.append("CYCLE_BRANCH_ID_MISMATCH")
    if payload.get("approved_for_shadow_collection") is not True:
        reasons.append("CYCLE_SHADOW_COLLECTION_NOT_APPROVED")
    for unsafe_flag in ("approved_for_paper_candidate", "approved_for_live_real", "approved_for_training_candidate"):
        if payload.get(unsafe_flag) is not False:
            reasons.append(f"UNSAFE_CYCLE_{unsafe_flag.upper()}")
    for mutation_flag in (
        "config_mutation_performed",
        "scheduler_mutation_performed",
        "scheduler_task_created",
        "scheduler_task_modified",
        "trading_action_performed",
        "training_performed",
        "reload_performed",
        "order_actions_performed",
    ):
        if payload.get(mutation_flag) is not False:
            reasons.append(f"UNSAFE_CYCLE_{mutation_flag.upper()}")
    summary = _mapping(payload.get("shadow_summary"))
    if _as_int(summary.get("shadow_observation_count"), 0) <= 0:
        reasons.append("CYCLE_OBSERVATION_COUNT_ZERO")
    if _as_int(summary.get("new_unique_shadow_observation_count"), 0) <= 0:
        reasons.append("CYCLE_NEW_UNIQUE_OBSERVATION_COUNT_ZERO")
    return not reasons, reasons


def summarize_ledger_continuity(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ids = [str(row.get("observation_id")) for row in rows if row.get("observation_id")]
    duplicate_ids = sorted([item for item, count in Counter(ids).items() if count > 1])
    returns: list[float] = []
    symbols: list[str] = []
    contract_versions: set[str] = set()
    unsafe_rows: list[str] = []
    for row in rows:
        mapping = _mapping(row)
        if mapping.get("symbol"):
            symbols.append(str(mapping["symbol"]).upper())
        if mapping.get("contract_version"):
            contract_versions.add(str(mapping["contract_version"]))
        try:
            returns.append(float(mapping.get("forward_return_bps_final_short_probe")))
        except (TypeError, ValueError):
            pass
        if mapping.get("order_actions_performed") is True or mapping.get("trading_action_performed") is True:
            unsafe_rows.append(str(mapping.get("observation_id", "<unknown>")))
    wins = sum(1 for item in returns if item > 0)
    losses = sum(1 for item in returns if item < 0)
    gross_profit = sum(item for item in returns if item > 0)
    gross_loss_abs = abs(sum(item for item in returns if item < 0))
    sorted_returns = sorted(returns)
    median: float | None
    if not sorted_returns:
        median = None
    elif len(sorted_returns) % 2:
        median = round(sorted_returns[len(sorted_returns) // 2], 6)
    else:
        mid = len(sorted_returns) // 2
        median = round((sorted_returns[mid - 1] + sorted_returns[mid]) / 2.0, 6)
    return {
        "ledger_row_count": len(rows),
        "unique_observation_ids": len(set(ids)),
        "duplicate_observation_ids": duplicate_ids,
        "duplicate_observation_count": len(duplicate_ids),
        "contract_versions": sorted(contract_versions),
        "branch_id_ok": all(_mapping(row).get("branch_id") == BRANCH_ID for row in rows) if rows else False,
        "no_order_rows_ok": not unsafe_rows,
        "unsafe_rows": unsafe_rows,
        "symbols_observed": sorted(set(symbols)),
        "symbols_observed_count": len(set(symbols)),
        "matured_count": len(returns),
        "win_count": wins,
        "loss_count": losses,
        "win_rate_pct": round((wins / len(returns)) * 100.0, 6) if returns else 0.0,
        "net_return_bps": round(sum(returns), 6) if returns else 0.0,
        "mean_return_bps": round(sum(returns) / len(returns), 6) if returns else None,
        "median_return_bps": median,
        "profit_factor": round(gross_profit / gross_loss_abs, 6) if gross_loss_abs else (999.0 if gross_profit > 0 else 0.0),
        "best_return_bps": round(max(returns), 6) if returns else None,
        "worst_return_bps": round(min(returns), 6) if returns else None,
        "sample_observation_ids": ids[:20],
    }


def validate_ledger_continuity(rows: Sequence[Mapping[str, Any]], *, min_rows: int = 1) -> tuple[bool, list[str], dict[str, Any]]:
    summary = summarize_ledger_continuity(rows)
    reasons: list[str] = []
    if summary["ledger_row_count"] < min_rows:
        reasons.append("LEDGER_ROW_COUNT_BELOW_MINIMUM")
    if summary["duplicate_observation_count"]:
        reasons.append("LEDGER_DUPLICATE_OBSERVATION_IDS_PRESENT")
    if not summary["branch_id_ok"]:
        reasons.append("LEDGER_BRANCH_ID_MISMATCH")
    if not summary["no_order_rows_ok"]:
        reasons.append("LEDGER_UNSAFE_ORDER_OR_TRADING_FLAG_PRESENT")
    if SOURCE_CYCLE_CONTRACT_VERSION not in summary["contract_versions"]:
        reasons.append("LEDGER_SOURCE_CONTRACT_VERSION_MISSING")
    return not reasons, reasons, summary


def normalize_task_probe(raw_probe: Mapping[str, Any] | None) -> dict[str, Any]:
    probe = dict(raw_probe or {})
    actions = probe.get("actions")
    if isinstance(actions, Sequence) and not isinstance(actions, (str, bytes, bytearray)) and actions:
        first_action = _mapping(actions[0])
    else:
        first_action = _mapping(probe.get("action"))
    task_name = probe.get("task_name") or probe.get("TaskName") or probe.get("taskName") or probe.get("name")
    exists = probe.get("exists")
    if exists is None:
        exists = bool(task_name or probe.get("state") or probe.get("last_task_result") is not None)
    return {
        "exists": _as_bool(exists),
        "task_name": str(task_name or ""),
        "state": str(probe.get("state") or probe.get("State") or ""),
        "last_task_result": _as_int(probe.get("last_task_result", probe.get("LastTaskResult")), -1),
        "number_of_missed_runs": _as_int(probe.get("number_of_missed_runs", probe.get("NumberOfMissedRuns")), 0),
        "last_run_time": probe.get("last_run_time") or probe.get("LastRunTime"),
        "next_run_time": probe.get("next_run_time") or probe.get("NextRunTime"),
        "action_execute": str(first_action.get("execute") or first_action.get("Execute") or probe.get("action_execute") or ""),
        "action_arguments": str(first_action.get("arguments") or first_action.get("Arguments") or probe.get("action_arguments") or ""),
        "working_directory": str(first_action.get("working_directory") or first_action.get("WorkingDirectory") or probe.get("working_directory") or ""),
        "raw_probe_available": bool(raw_probe),
    }


def validate_scheduler_task_health(raw_probe: Mapping[str, Any] | None, *, task_name: str = PROPOSED_SCHEDULER_TASK_NAME) -> tuple[bool, list[str], dict[str, Any]]:
    probe = normalize_task_probe(raw_probe)
    reasons: list[str] = []
    if not probe["exists"]:
        reasons.append("SCHEDULER_TASK_NOT_FOUND")
    if probe["task_name"] and probe["task_name"] != task_name:
        reasons.append("SCHEDULER_TASK_NAME_MISMATCH")
    if probe["last_task_result"] != 0:
        reasons.append("SCHEDULER_LAST_TASK_RESULT_NOT_ZERO")
    if probe["number_of_missed_runs"] > 0:
        reasons.append("SCHEDULER_MISSED_RUNS_PRESENT")

    action_execute = probe["action_execute"]
    action_arguments = probe["action_arguments"]
    python_direct_action = _contains(action_execute, "python") or _contains(action_execute, "py.exe")
    powershell_wrapper_action = _contains(action_execute, "powershell") and _contains(
        action_arguments,
        "run_hyp006_r1_canonical_shadow_scheduler.ps1",
    )
    if not (python_direct_action or powershell_wrapper_action):
        reasons.append("SCHEDULER_ACTION_EXECUTE_NOT_SUPPORTED")

    if python_direct_action:
        required_argument_fragments = [
            "run_4B436628D_hyp006_canonical_shadow_cycle.py",
            "--registration-approval-json",
            "--registration-json",
            "--out-dir",
            "--review-ok",
        ]
    else:
        required_argument_fragments = [
            "run_hyp006_r1_canonical_shadow_scheduler.ps1",
            "ExecutionPolicy",
            "Bypass",
        ]
    for fragment in required_argument_fragments:
        if not _contains(action_arguments, fragment):
            reasons.append(f"SCHEDULER_ACTION_ARGUMENT_MISSING_{fragment.upper().replace('-', '_').replace('.', '_')}")
    return not reasons, reasons, probe


def probe_windows_task_scheduler(task_name: str = PROPOSED_SCHEDULER_TASK_NAME) -> dict[str, Any]:
    if os.name != "nt":
        return {"exists": False, "task_name": task_name, "probe_error": "WINDOWS_TASK_SCHEDULER_PROBE_UNAVAILABLE_ON_NON_WINDOWS"}
    script = rf'''
$ErrorActionPreference = 'Stop'
$taskName = {json.dumps(task_name)}
try {{
  $task = Get-ScheduledTask -TaskName $taskName
  $info = Get-ScheduledTaskInfo -TaskName $taskName
  $action = @($task.Actions)[0]
  [PSCustomObject]@{{
    exists = $true
    task_name = $task.TaskName
    state = [string]$task.State
    last_task_result = [int]$info.LastTaskResult
    number_of_missed_runs = [int]$info.NumberOfMissedRuns
    last_run_time = [string]$info.LastRunTime
    next_run_time = [string]$info.NextRunTime
    action_execute = [string]$action.Execute
    action_arguments = [string]$action.Arguments
    working_directory = [string]$action.WorkingDirectory
  }} | ConvertTo-Json -Depth 8 -Compress
}} catch {{
  [PSCustomObject]@{{
    exists = $false
    task_name = $taskName
    probe_error = [string]$_.Exception.Message
  }} | ConvertTo-Json -Depth 8 -Compress
}}
'''
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = _decode_subprocess_bytes(completed.stdout).strip()
    stderr = _decode_subprocess_bytes(completed.stderr).strip()
    if not output:
        return {"exists": False, "task_name": task_name, "probe_error": stderr or "EMPTY_POWERSHELL_OUTPUT"}
    try:
        parsed = json.loads(output)
        return parsed if isinstance(parsed, dict) else {"exists": False, "task_name": task_name, "probe_error": "UNEXPECTED_POWERSHELL_JSON"}
    except json.JSONDecodeError as exc:
        return {"exists": False, "task_name": task_name, "probe_error": f"POWERSHELL_JSON_PARSE_ERROR:{exc}", "raw_output": output[:500], "raw_stderr": stderr[:500]}


def build_scheduler_execution_health_report(
    *,
    registration_approval_report: Mapping[str, Any] | None,
    cycle_report: Mapping[str, Any] | None,
    ledger_rows: Sequence[Mapping[str, Any]],
    task_probe: Mapping[str, Any] | None,
    operator_execution_review: bool,
    source_paths: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    approval_ok, approval_reasons = validate_registration_approval_report(registration_approval_report)
    cycle_ok, cycle_reasons = validate_cycle_report(cycle_report)
    ledger_ok, ledger_reasons, ledger_summary = validate_ledger_continuity(ledger_rows)
    scheduler_ok, scheduler_reasons, scheduler_probe = validate_scheduler_task_health(task_probe)
    blockers: list[str] = []
    blockers.extend(approval_reasons)
    blockers.extend(cycle_reasons)
    blockers.extend(ledger_reasons)
    blockers.extend(scheduler_reasons)
    if not operator_execution_review:
        blockers.append("NO_OPERATOR_EXECUTION_HEALTH_REVIEW")
    ok = bool(approval_ok and cycle_ok and ledger_ok and scheduler_ok and operator_execution_review)
    return {
        "contract_version": CONTRACT_VERSION,
        "report_type": "hyp006_r1_canonical_shadow_scheduler_execution_health_no_order_ledger_continuity_evidence_pack",
        "decision": "HYP006_R1_CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_READY" if ok else "HYP006_R1_CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_BLOCKED",
        "ok": ok,
        "generated_at_utc": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "source_paths": dict(source_paths or {}),
        "registration_approval_validation": {"ok": approval_ok, "reasons": approval_reasons},
        "cycle_validation": {"ok": cycle_ok, "reasons": cycle_reasons},
        "ledger_continuity_validation": {"ok": ledger_ok, "reasons": ledger_reasons},
        "scheduler_task_health_validation": {"ok": scheduler_ok, "reasons": scheduler_reasons},
        "operator_execution_review_recorded": bool(operator_execution_review),
        "scheduler_task_health": scheduler_probe,
        "ledger_continuity_summary": ledger_summary,
        "cycle_shadow_summary": dict(_mapping(_mapping(cycle_report).get("shadow_summary"))),
        "blockers": sorted(set(blockers)),
        "reason_codes": [
            "CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_VERIFY",
            "WINDOWS_TASK_REGISTRATION_HEALTH_CHECK",
            "NO_ORDER_LEDGER_CONTINUITY_EVIDENCE_PACK",
            "PAPER_LIVE_GATES_REMAIN_CLOSED",
            "NO_TRAINING_RELOAD_ORDER_ENABLEMENT",
        ],
        "risk_items": [
            {"level": "critical", "code": "NO_ORDER_SHADOW_ONLY", "detail": "Scheduler health validates collection only, not trading edge."},
            {"level": "warning", "code": "PAPER_LIVE_STILL_BLOCKED", "detail": "Acceptance metrics require separate 28F+ evidence."},
            {"level": "warning", "code": "SHORT_SIDE_COSTS_STILL_UNMODELED", "detail": "Funding, borrow, liquidation, and execution costs remain outside acceptance."},
        ],
        "recommendation": "Continue HYP-006-R1 canonical no-order shadow collection and proceed to 28F dashboard/acceptance baseline only if scheduler health is ready. Do not train, reload, paper trade, live trade, or send orders.",
        "read_only": True,
        "no_order_scheduler_health_verify_only": True,
        "post_requests_allowed": False,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "branch_state_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "approved_for_shadow_collection_continuity": ok,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_transition_candidate_found": False,
        "next_required_gate": NEXT_REQUIRED_GATE,
        "warnings": ["28F_REQUIRED_BEFORE_ANY_ACCEPTANCE_OR_PAPER_TRANSITION_CANDIDACY"],
    }


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    summary = _mapping(payload.get("ledger_continuity_summary"))
    scheduler = _mapping(payload.get("scheduler_task_health"))
    lines = [
        "# 4B.4.3.6.6.28E HYP-006-R1 Scheduler Execution Health",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- branch_id: `{payload.get('branch_id')}`",
        f"- task_name: `{scheduler.get('task_name')}`",
        f"- last_task_result: `{scheduler.get('last_task_result')}`",
        f"- ledger_row_count: `{summary.get('ledger_row_count')}`",
        f"- unique_observation_ids: `{summary.get('unique_observation_ids')}`",
        f"- mean_return_bps: `{summary.get('mean_return_bps')}`",
        f"- profit_factor: `{summary.get('profit_factor')}`",
        f"- approved_for_paper_candidate: `{payload.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{payload.get('approved_for_live_real')}`",
        f"- next_required_gate: `{payload.get('next_required_gate')}`",
        "",
        "## Recommendation",
        "",
        str(payload.get("recommendation", "")),
    ]
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_health_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str]) -> tuple[Path, Path, Path]:
    target_dir = Path(out_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_json = target_dir / f"{REPORT_PREFIX}_{stamp}.json"
    continuity_json = target_dir / f"{LEDGER_CONTINUITY_PREFIX}_{stamp}.json"
    report_md = target_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(report_json, payload)
    write_json_atomic(continuity_json, payload.get("ledger_continuity_summary", {}))
    write_markdown(report_md, payload)
    return report_json, continuity_json, report_md
