"""HYP-005 shadow operator runbook / daily no-order audit pack.

This module summarizes the HYP-005 no-order shadow collection chain for the
operator. It reads the 25U candidate spec, 25V logger reports, 25X collection
orchestrator reports, 25W acceptance/readiness reports, and shadow ledgers. It
then writes a daily audit pack and dashboard snapshot.

It is intentionally non-executable from a trading perspective: it never starts
paper/live trading, never sends orders, never mutates runtime configuration,
never trains, and never reloads models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

HYP005_SHADOW_OPERATOR_AUDIT_CONTRACT_VERSION = "4B.4.3.6.6.25Y"
HYP005_R1_OPERATOR_COMMANDS_SCOPE_HOTFIX_VERSION = "4B.4.3.6.6.25AE-H2"
HYP005_SHADOW_OPERATOR_AUDIT_READY = "HYP005_SHADOW_OPERATOR_AUDIT_READY"
HYP005_SHADOW_OPERATOR_AUDIT_BLOCK = "HYP005_SHADOW_OPERATOR_AUDIT_BLOCK"
NO_ORDER_OPERATOR_AUDIT_ONLY = "NO_ORDER_OPERATOR_AUDIT_ONLY"
PAPER_TRANSITION_READINESS_IS_NOT_PAPER_PERMISSION = "PAPER_TRANSITION_READINESS_IS_NOT_PAPER_PERMISSION"
NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED = "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"

DEFAULT_REPORT_PREFIX = "4B436625Y_hyp005_shadow_operator_daily_audit"
DEFAULT_DASHBOARD_PREFIX = "4B436625Y_hyp005_shadow_operator_dashboard"
DEFAULT_RUNBOOK_PREFIX = "4B436625Y_hyp005_shadow_operator_runbook"


@dataclass(frozen=True)
class Hyp005ShadowOperatorAuditLimits:
    shadow_sample_target: int = 30
    min_shadow_days_observed: int = 30
    min_signal_capture_count: int = 25
    min_data_quality_pct: float = 98.0
    max_missing_fields_pct: float = 1.0
    daily_audit_required: bool = True
    paper_transition_requires_separate_enablement: bool = True
    live_transition_requires_separate_gate: bool = True


@dataclass(frozen=True)
class OperatorCommand:
    name: str
    description: str
    powershell: str


@dataclass(frozen=True)
class ShadowOperatorDashboard:
    contract_version: str
    hypothesis_id: str
    branch_name: str
    selected_strategy_family: str
    dashboard_status: str
    no_order_operator_audit_only: bool
    latest_logger_decision: str
    latest_collection_decision: str
    latest_acceptance_decision: str
    shadow_observation_count: int
    shadow_sample_target: int
    progress_pct: float
    paper_transition_ready: bool
    paper_transition_requires_separate_enablement: bool
    active_blockers: list[str]
    next_operator_actions: list[str]
    last_report_paths: dict[str, str]


@dataclass(frozen=True)
class ShadowOperatorAuditReport:
    contract_version: str
    phase: str
    report_type: str
    decision: str
    ok: bool
    generated_at_utc: str
    hypothesis_id: str
    branch_name: str
    selected_strategy_family: str
    source_reports: int
    source_ledgers: int
    no_order_operator_audit_only: bool
    runtime_probe_only: bool
    daily_audit_ready: bool
    dashboard_status: str
    shadow_observation_count: int
    shadow_sample_target: int
    progress_pct: float
    latest_logger_decision: str
    latest_collection_decision: str
    latest_acceptance_decision: str
    paper_transition_ready: bool
    approved_for_operator_audit: bool
    approved_for_shadow_collection: bool
    approved_for_paper_transition_candidate: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    live_real_allowed: bool
    post_requests_allowed: bool
    config_mutation_performed: bool
    order_actions_performed: bool
    reload_performed: bool
    training_performed: bool
    paper_trading_started: bool
    dashboard: dict[str, Any]
    commands: list[dict[str, Any]]
    active_blockers: list[str]
    reason_codes: list[str]
    warnings: list[str]
    recommendation: str


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_markdown(path: str | Path, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _nested_get(payload: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, Mapping):
            return default
        current = current.get(key)
    return current if current is not None else default


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _first_non_empty(*values: Any, default: str = "UNKNOWN") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.upper() not in {"NONE", "NULL", "UNKNOWN"}:
            return text
    return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _latest_by_generated_at(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not reports:
        return {}
    return dict(reports[-1])


def _observation_key(observation: Mapping[str, Any]) -> str:
    return "|".join(
        str(observation.get(key, "")).strip()
        for key in (
            "timestamp_utc",
            "symbol",
            "timeframe",
            "strategy_family",
            "sweep_direction",
            "entry_reference_price",
        )
    )


def load_observations_from_json(path: str | Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, Mapping):
        rows = _as_list(payload.get("observations"))
    else:
        rows = []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def load_observations_from_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, Mapping):
                rows.append(dict(payload))
    return rows


def merge_observations(observation_sets: Iterable[Iterable[Mapping[str, Any]]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    duplicates = 0
    for observation_set in observation_sets:
        for observation in observation_set:
            key = _observation_key(observation)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            merged.append(dict(observation))
    return merged, duplicates


def validate_no_order_candidate_spec(candidate_spec: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if _first_non_empty(candidate_spec.get("hypothesis_id"), default="") != "HYP-005":
        reasons.append("HYP005_CANDIDATE_SPEC_MISSING_OR_MISMATCHED")

    no_order = _bool(candidate_spec.get("no_order_shadow_only")) or _bool(
        _nested_get(candidate_spec, "guardrails", "no_order_shadow_only", default=False)
    )
    if not no_order:
        reasons.append("NO_ORDER_SHADOW_SPEC_NOT_CONFIRMED")

    unsafe_flags = (
        "approved_for_training_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "live_real_allowed",
        "order_actions_performed",
        "paper_trading_started",
        "post_requests_allowed",
    )
    for flag in unsafe_flags:
        if _bool(candidate_spec.get(flag)):
            reasons.append(f"UNSAFE_SPEC_FLAG_{flag.upper()}")
    return not reasons, reasons


def _scan_unsafe_report_flags(reports: Sequence[Mapping[str, Any]], prefix: str) -> list[str]:
    reasons: list[str] = []
    unsafe_flags = (
        "approved_for_training_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "live_real_allowed",
        "order_actions_performed",
        "paper_trading_started",
        "training_performed",
        "reload_performed",
        "config_mutation_performed",
        "post_requests_allowed",
    )
    for report in reports:
        for flag in unsafe_flags:
            if _bool(report.get(flag)):
                reasons.append(f"{prefix}_UNSAFE_{flag.upper()}_DETECTED")
    return reasons


def summarize_progress(
    latest_collection: Mapping[str, Any],
    latest_acceptance: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    limits: Hyp005ShadowOperatorAuditLimits,
) -> tuple[int, int, float]:
    collection_progress = _as_mapping(latest_collection.get("progress"))
    count = _int(
        collection_progress.get("shadow_observation_count"),
        default=_int(latest_collection.get("shadow_observation_count"), default=len(observations)),
    )
    if count <= 0:
        count = _int(latest_acceptance.get("shadow_observation_count"), default=len(observations))
    target = _int(collection_progress.get("shadow_sample_target"), default=limits.shadow_sample_target)
    if target <= 0:
        target = limits.shadow_sample_target
    progress_pct = min(100.0, round((float(count) / float(target)) * 100.0, 6)) if target else 0.0
    return count, target, progress_pct


def build_operator_commands(
    *,
    candidate_spec_path: str,
    symbols: Sequence[str],
    interval: str,
    days: int,
    base_url: str,
    out_dir: str,
) -> list[OperatorCommand]:
    symbol_csv = ",".join(symbols)
    logger = (
        "python tools/run_hyp005_shadow_observation_logger_4B436625V.py `\n"
        f"  --candidate-spec-json {candidate_spec_path} `\n"
        f"  --symbols {symbol_csv} `\n"
        f"  --interval {interval} `\n"
        f"  --days {days} `\n"
        f"  --base-url {base_url} `\n"
        f"  --out-dir {out_dir} `\n"
        "  --review-ok"
    )
    orchestrator = (
        "python tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py `\n"
        f"  --candidate-spec-json {candidate_spec_path} `\n"
        f"  --reports-dir {out_dir} `\n"
        "  --include-all `\n"
        f"  --symbols {symbol_csv} `\n"
        f"  --interval {interval} `\n"
        f"  --days {days} `\n"
        f"  --base-url {base_url} `\n"
        f"  --out-dir {out_dir} `\n"
        "  --review-ok"
    )
    acceptance = (
        "python tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py `\n"
        f"  --reports-dir {out_dir} `\n"
        "  --include-all `\n"
        f"  --out-dir {out_dir} `\n"
        "  --review-ok"
    )
    audit = (
        "python tools/run_hyp005_shadow_operator_runbook_4B436625Y.py `\n"
        f"  --candidate-spec-json {candidate_spec_path} `\n"
        f"  --reports-dir {out_dir} `\n"
        "  --include-all `\n"
        f"  --symbols {symbol_csv} `\n"
        f"  --interval {interval} `\n"
        f"  --days {days} `\n"
        f"  --base-url {base_url} `\n"
        f"  --out-dir {out_dir} `\n"
        "  --review-ok"
    )
    return [
        OperatorCommand("run_25v_logger", "Collect no-order shadow observations from public market data.", logger),
        OperatorCommand("run_25x_orchestrator", "Merge ledgers, deduplicate observations, and update collection progress.", orchestrator),
        OperatorCommand("run_25w_acceptance", "Check paper-transition readiness without enabling paper trading.", acceptance),
        OperatorCommand("run_25y_daily_audit", "Regenerate the operator audit pack and dashboard snapshot.", audit),
    ]


def build_hyp005_shadow_operator_audit_report(
    *,
    candidate_spec: Mapping[str, Any],
    candidate_spec_path: str,
    logger_reports: Sequence[Mapping[str, Any]],
    collection_reports: Sequence[Mapping[str, Any]],
    acceptance_reports: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    ledger_source_count: int,
    symbols: Sequence[str],
    interval: str,
    days: int,
    base_url: str,
    out_dir: str,
    limits: Hyp005ShadowOperatorAuditLimits | None = None,
) -> ShadowOperatorAuditReport:
    limits = limits or Hyp005ShadowOperatorAuditLimits()
    reason_codes: list[str] = []
    warnings: list[str] = []

    spec_ok, spec_reasons = validate_no_order_candidate_spec(candidate_spec)
    reason_codes.extend(spec_reasons)

    latest_logger = _latest_by_generated_at(logger_reports)
    latest_collection = _latest_by_generated_at(collection_reports)
    latest_acceptance = _latest_by_generated_at(acceptance_reports)

    logger_ready = any(report.get("decision") == "HYP005_SHADOW_OBSERVATION_LOGGER_READY" for report in logger_reports)
    collection_ready = any(report.get("decision") == "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY" for report in collection_reports)
    acceptance_seen = any(
        report.get("decision") in {"HYP005_SHADOW_PAPER_TRANSITION_BLOCK", "HYP005_SHADOW_PAPER_TRANSITION_READY"}
        for report in acceptance_reports
    )

    if not logger_reports or not logger_ready:
        reason_codes.append("HYP005_SHADOW_LOGGER_READY_NOT_CONFIRMED")
    else:
        reason_codes.append("HYP005_SHADOW_LOGGER_READY_CONFIRMED")

    if not collection_reports or not collection_ready:
        reason_codes.append("HYP005_SHADOW_COLLECTION_ORCHESTRATOR_NOT_CONFIRMED")
    else:
        reason_codes.append("HYP005_SHADOW_COLLECTION_ORCHESTRATOR_CONFIRMED")

    if not acceptance_reports or not acceptance_seen:
        reason_codes.append("HYP005_SHADOW_ACCEPTANCE_DECISION_NOT_CONFIRMED")
    else:
        reason_codes.append("HYP005_SHADOW_ACCEPTANCE_DECISION_CONFIRMED")

    reason_codes.extend(_scan_unsafe_report_flags(logger_reports, "LOGGER_REPORT"))
    reason_codes.extend(_scan_unsafe_report_flags(collection_reports, "COLLECTION_REPORT"))
    reason_codes.extend(_scan_unsafe_report_flags(acceptance_reports, "ACCEPTANCE_REPORT"))

    observation_count, sample_target, progress_pct = summarize_progress(latest_collection, latest_acceptance, observations, limits)
    latest_logger_decision = _first_non_empty(latest_logger.get("decision"), default="UNKNOWN")
    latest_collection_decision = _first_non_empty(latest_collection.get("decision"), default="UNKNOWN")
    latest_acceptance_decision = _first_non_empty(latest_acceptance.get("decision"), default="UNKNOWN")
    paper_transition_ready = latest_acceptance_decision == "HYP005_SHADOW_PAPER_TRANSITION_READY" or _bool(
        latest_acceptance.get("paper_transition_ready")
    )

    active_blockers: list[str] = []
    if observation_count < sample_target:
        active_blockers.append("SHADOW_SAMPLE_COUNT_BELOW_TARGET")
    if latest_acceptance_decision == "HYP005_SHADOW_PAPER_TRANSITION_BLOCK":
        active_blockers.append("PAPER_TRANSITION_BLOCKED_BY_25W")
    if not paper_transition_ready:
        active_blockers.append("PAPER_TRANSITION_READY_FALSE")
    if not collection_ready:
        active_blockers.append("COLLECTION_ORCHESTRATOR_NOT_READY")
    if not logger_ready:
        active_blockers.append("LOGGER_NOT_READY")

    if active_blockers:
        warnings.append("SHADOW_OPERATOR_ATTENTION_REQUIRED")
    if observation_count == 0:
        warnings.append("SHADOW_LEDGER_EMPTY")
    if paper_transition_ready:
        warnings.append("PAPER_TRANSITION_READY_REQUIRES_SEPARATE_ENABLEMENT")

    unsafe_reason_present = any("UNSAFE" in code for code in reason_codes)
    chain_ok = spec_ok and logger_ready and collection_ready and acceptance_seen and not unsafe_reason_present
    decision = HYP005_SHADOW_OPERATOR_AUDIT_READY if chain_ok else HYP005_SHADOW_OPERATOR_AUDIT_BLOCK

    hypothesis_id = _first_non_empty(candidate_spec.get("hypothesis_id"), latest_collection.get("hypothesis_id"), default="HYP-005")
    branch_name = _first_non_empty(
        candidate_spec.get("branch_name"),
        latest_collection.get("branch_name"),
        latest_acceptance.get("branch_name"),
        default="liquidity_sweep_reversal_vol_compression",
    )
    selected_strategy_family = _first_non_empty(
        candidate_spec.get("selected_strategy_family"),
        latest_collection.get("selected_strategy_family"),
        latest_acceptance.get("selected_strategy_family"),
        default="long_liquidity_sweep_reversal",
    )

    dashboard_status = "PAPER_TRANSITION_READY_REVIEW_ONLY" if paper_transition_ready else "SHADOW_COLLECTION_IN_PROGRESS"
    if decision != HYP005_SHADOW_OPERATOR_AUDIT_READY:
        dashboard_status = "AUDIT_CHAIN_BLOCKED"

    commands = build_operator_commands(
        candidate_spec_path=candidate_spec_path,
        symbols=symbols,
        interval=interval,
        days=days,
        base_url=base_url,
        out_dir=out_dir,
    )
    next_actions = [
        "Run 25V after each 4h candle close or at least once daily.",
        "Run 25X to merge/deduplicate ledgers and update progress.",
        "Run 25W to keep paper-transition readiness blocked until acceptance metrics pass.",
        "Do not train, reload, paper trade, live trade, or send orders from this audit pack.",
    ]
    if paper_transition_ready:
        next_actions.insert(0, "Open a separate manual paper-enablement gate; do not start paper trading directly.")

    last_report_paths = {
        "candidate_spec_json": candidate_spec_path,
        "latest_logger_decision": latest_logger_decision,
        "latest_collection_decision": latest_collection_decision,
        "latest_acceptance_decision": latest_acceptance_decision,
    }
    dashboard = ShadowOperatorDashboard(
        contract_version=HYP005_SHADOW_OPERATOR_AUDIT_CONTRACT_VERSION,
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        selected_strategy_family=selected_strategy_family,
        dashboard_status=dashboard_status,
        no_order_operator_audit_only=True,
        latest_logger_decision=latest_logger_decision,
        latest_collection_decision=latest_collection_decision,
        latest_acceptance_decision=latest_acceptance_decision,
        shadow_observation_count=observation_count,
        shadow_sample_target=sample_target,
        progress_pct=progress_pct,
        paper_transition_ready=paper_transition_ready,
        paper_transition_requires_separate_enablement=True,
        active_blockers=sorted(set(active_blockers)),
        next_operator_actions=next_actions,
        last_report_paths=last_report_paths,
    )

    safe_reasons = sorted(set(reason_codes + [NO_ORDER_OPERATOR_AUDIT_ONLY, NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED]))
    if paper_transition_ready:
        recommendation = (
            "HYP-005 shadow observations appear paper-transition ready for review only. Do not start paper trading; "
            "open a separate paper-enablement gate with manual approval."
        )
    else:
        recommendation = (
            "HYP-005 daily no-order audit pack is ready. Keep collecting shadow observations until the 25W acceptance "
            "gate passes; do not train, reload, paper trade, live trade, or send orders."
        )
    if decision == HYP005_SHADOW_OPERATOR_AUDIT_BLOCK:
        recommendation = (
            "HYP-005 operator audit chain is incomplete or unsafe. Fix the missing/unsafe report chain before relying on "
            "the daily audit pack; do not train, reload, paper trade, live trade, or send orders."
        )

    return ShadowOperatorAuditReport(
        contract_version=HYP005_SHADOW_OPERATOR_AUDIT_CONTRACT_VERSION,
        phase=HYP005_SHADOW_OPERATOR_AUDIT_CONTRACT_VERSION,
        report_type="hyp005_shadow_operator_daily_no_order_audit_pack",
        decision=decision,
        ok=decision == HYP005_SHADOW_OPERATOR_AUDIT_READY,
        generated_at_utc=utc_iso(),
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        selected_strategy_family=selected_strategy_family,
        source_reports=len(logger_reports) + len(collection_reports) + len(acceptance_reports),
        source_ledgers=ledger_source_count,
        no_order_operator_audit_only=True,
        runtime_probe_only=True,
        daily_audit_ready=decision == HYP005_SHADOW_OPERATOR_AUDIT_READY,
        dashboard_status=dashboard_status,
        shadow_observation_count=observation_count,
        shadow_sample_target=sample_target,
        progress_pct=progress_pct,
        latest_logger_decision=latest_logger_decision,
        latest_collection_decision=latest_collection_decision,
        latest_acceptance_decision=latest_acceptance_decision,
        paper_transition_ready=paper_transition_ready,
        approved_for_operator_audit=decision == HYP005_SHADOW_OPERATOR_AUDIT_READY,
        approved_for_shadow_collection=decision == HYP005_SHADOW_OPERATOR_AUDIT_READY,
        approved_for_paper_transition_candidate=False,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        live_real_allowed=False,
        post_requests_allowed=False,
        config_mutation_performed=False,
        order_actions_performed=False,
        reload_performed=False,
        training_performed=False,
        paper_trading_started=False,
        dashboard=asdict(dashboard),
        commands=[asdict(command) for command in commands],
        active_blockers=sorted(set(active_blockers)),
        reason_codes=safe_reasons,
        warnings=sorted(set(warnings)),
        recommendation=recommendation,
    )


def as_serializable_report(report: ShadowOperatorAuditReport) -> dict[str, Any]:
    return asdict(report)


def write_markdown_report(path: str | Path, payload: Mapping[str, Any]) -> None:
    lines = [
        "# 4B.4.3.6.6.25Y HYP-005 Shadow Operator Daily No-Order Audit Pack",
        "",
        f"- contract_version: `{payload.get('contract_version')}`",
        f"- decision: **{payload.get('decision')}**",
        f"- hypothesis_id: `{payload.get('hypothesis_id')}`",
        f"- branch_name: `{payload.get('branch_name')}`",
        f"- selected_strategy_family: `{payload.get('selected_strategy_family')}`",
        f"- dashboard_status: `{payload.get('dashboard_status')}`",
        f"- shadow_observation_count: `{payload.get('shadow_observation_count')}`",
        f"- shadow_sample_target: `{payload.get('shadow_sample_target')}`",
        f"- progress_pct: `{payload.get('progress_pct')}`",
        f"- paper_transition_ready: `{payload.get('paper_transition_ready')}`",
        "",
        "## Guardrails",
        "",
        f"- no_order_operator_audit_only: `{payload.get('no_order_operator_audit_only')}`",
        f"- post_requests_allowed: `{payload.get('post_requests_allowed')}`",
        f"- order_actions_performed: `{payload.get('order_actions_performed')}`",
        f"- training_performed: `{payload.get('training_performed')}`",
        f"- reload_performed: `{payload.get('reload_performed')}`",
        f"- paper_trading_started: `{payload.get('paper_trading_started')}`",
        f"- approved_for_paper_candidate: `{payload.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{payload.get('approved_for_live_real')}`",
        "",
        "## Active Blockers",
        "",
    ]
    blockers = _as_list(payload.get("active_blockers"))
    lines.extend([f"- `{item}`" for item in blockers] if blockers else ["- none"])
    lines.extend(["", "## Reason Codes", ""])
    lines.extend([f"- `{item}`" for item in _as_list(payload.get("reason_codes"))])
    lines.extend(["", "## Warnings", ""])
    warnings = _as_list(payload.get("warnings"))
    lines.extend([f"- `{item}`" for item in warnings] if warnings else ["- none"])
    lines.extend(["", "## Operator Commands", ""])
    for command in _as_list(payload.get("commands")):
        if isinstance(command, Mapping):
            lines.append(f"### {command.get('name')}")
            lines.append("")
            lines.append(str(command.get("description", "")))
            lines.append("")
            lines.append("```powershell")
            lines.append(str(command.get("powershell", "")))
            lines.append("```")
            lines.append("")
    lines.extend(["## Recommendation", "", str(payload.get("recommendation", "")), ""])
    write_markdown(path, "\n".join(lines))


def write_runbook_markdown(path: str | Path, payload: Mapping[str, Any]) -> None:
    lines = [
        "# HYP-005 Daily No-Order Operator Runbook",
        "",
        "This runbook is generated by 4B.4.3.6.6.25Y. It is an audit and operating checklist only.",
        "It does not enable paper trading, live trading, model training, model reload, or order actions.",
        "",
        "## Current Status",
        "",
        f"- Dashboard status: `{payload.get('dashboard_status')}`",
        f"- Shadow progress: `{payload.get('shadow_observation_count')}/{payload.get('shadow_sample_target')}`",
        f"- Paper transition ready: `{payload.get('paper_transition_ready')}`",
        "",
        "## Daily No-Order Loop",
        "",
        "Run these commands after each 4h candle close or at least once daily.",
        "",
    ]
    for command in _as_list(payload.get("commands")):
        if isinstance(command, Mapping):
            lines.append(f"### {command.get('name')}")
            lines.append("")
            lines.append("```powershell")
            lines.append(str(command.get("powershell", "")))
            lines.append("```")
            lines.append("")
    lines.extend(
        [
            "## Hard Stops",
            "",
            "- Do not start paper trading from this runbook.",
            "- Do not enable live trading from this runbook.",
            "- Do not train or reload a model from this runbook.",
            "- Do not send orders from this runbook.",
            "- A future paper-transition gate must be separate and manually reviewed.",
            "",
        ]
    )
    write_markdown(path, "\n".join(lines))
