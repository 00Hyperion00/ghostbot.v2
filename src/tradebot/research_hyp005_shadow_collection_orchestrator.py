"""HYP-005 shadow collection orchestrator / no-order scheduler gate.

This module builds a no-order collection plan after the HYP-005 shadow
acceptance gate blocks paper transition because the shadow ledger does not yet
contain enough observations. It never starts paper/live trading, never sends
orders, never mutates runtime configuration, and never trains or reloads models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .hyp005_shadow_observation_identity import canonical_event_key, normalize_observation_identity

HYP005_SHADOW_COLLECTION_ORCHESTRATOR_CONTRACT_VERSION = "4B.4.3.6.6.25X"
HYP005_SHADOW_COLLECTION_READY = "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY"
HYP005_SHADOW_COLLECTION_BLOCK = "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_BLOCK"
HYP005_SHADOW_COLLECTION_STATUS_IN_PROGRESS = "HYP005_SHADOW_COLLECTION_IN_PROGRESS"
HYP005_SHADOW_COLLECTION_STATUS_TARGET_MET = "HYP005_SHADOW_COLLECTION_TARGET_MET"
HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION = "4B.4.3.6.6.25AE-H4"
NO_ORDER_COLLECTION_ONLY = "NO_ORDER_COLLECTION_ONLY"
NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED = "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"

DEFAULT_REPORT_PREFIX = "4B436625X_hyp005_shadow_collection_orchestrator"
DEFAULT_PLAN_PREFIX = "4B436625X_hyp005_shadow_collection_plan"
DEFAULT_MERGED_LEDGER_PREFIX = "4B436625X_hyp005_shadow_merged_ledger"


@dataclass(frozen=True)
class Hyp005ShadowCollectionLimits:
    shadow_sample_target: int = 30
    min_shadow_days_observed: int = 30
    min_signal_capture_count: int = 25
    max_duplicate_observation_pct: float = 5.0
    scheduler_interval: str = "4h"
    collection_days: int = 30
    min_manual_reviewers: int = 1


@dataclass(frozen=True)
class ShadowCollectionCommand:
    name: str
    description: str
    powershell: str


@dataclass(frozen=True)
class ShadowCollectionPlan:
    contract_version: str
    hypothesis_id: str
    branch_name: str
    selected_strategy_family: str
    no_order_collection_only: bool
    scheduler_cadence: str
    collection_days: int
    shadow_sample_target: int
    commands: list[ShadowCollectionCommand]
    guardrails: dict[str, bool]


@dataclass(frozen=True)
class ShadowCollectionProgress:
    shadow_observation_count: int
    unique_observation_count: int
    duplicate_observation_count: int
    duplicate_observation_pct: float
    shadow_sample_target: int
    shadow_sample_target_met: bool
    progress_pct: float
    observed_symbols: list[str]
    observed_days: int


@dataclass(frozen=True)
class ShadowCollectionReport:
    contract_version: str
    phase: str
    report_type: str
    decision: str
    ok: bool
    hypothesis_id: str
    branch_name: str
    selected_strategy_family: str
    source_reports: int
    source_ledgers: int
    no_order_collection_only: bool
    runtime_probe_only: bool
    shadow_collection_ready: bool
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
    collection_status: str
    shadow_observation_count: int
    shadow_sample_target: int
    progress_pct: float
    acceptance_report_required_for_collection_ready: bool
    acceptance_report_seen: bool
    previous_acceptance_informational_only: bool
    progress: dict[str, Any]
    plan: dict[str, Any]
    reason_codes: list[str]
    warnings: list[str]
    recommendation: str


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write("\n")


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _nested_get(payload: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, Mapping):
            return default
        current = current.get(key)
    return current if current is not None else default


def _bool(payload: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
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


def validate_no_order_candidate_spec(candidate_spec: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    hypothesis_id = _first_non_empty(candidate_spec.get("hypothesis_id"), default="")
    if hypothesis_id != "HYP-005":
        reasons.append("HYP005_CANDIDATE_SPEC_MISSING_OR_MISMATCHED")

    no_order = bool(
        candidate_spec.get("no_order_shadow_only")
        or _nested_get(candidate_spec, "guardrails", "no_order_shadow_only", default=False)
        or _nested_get(candidate_spec, "candidate_spec", "no_order_shadow_only", default=False)
    )
    if not no_order:
        reasons.append("NO_ORDER_SHADOW_SPEC_NOT_CONFIRMED")

    unsafe_flags = {
        "approved_for_training_candidate": candidate_spec.get("approved_for_training_candidate"),
        "approved_for_paper_candidate": candidate_spec.get("approved_for_paper_candidate"),
        "approved_for_live_real": candidate_spec.get("approved_for_live_real"),
        "live_real_allowed": candidate_spec.get("live_real_allowed"),
        "order_actions_performed": candidate_spec.get("order_actions_performed"),
        "post_requests_allowed": candidate_spec.get("post_requests_allowed"),
    }
    for flag, value in unsafe_flags.items():
        if bool(value):
            reasons.append(f"UNSAFE_SPEC_FLAG_{flag.upper()}")

    return not reasons, reasons


def validate_logger_reports(logger_reports: Sequence[Mapping[str, Any]]) -> tuple[bool, list[str]]:
    if not logger_reports:
        return False, ["HYP005_SHADOW_LOGGER_REPORT_MISSING"]
    ready = False
    reasons: list[str] = []
    for report in logger_reports:
        if report.get("decision") == "HYP005_SHADOW_OBSERVATION_LOGGER_READY":
            ready = True
        if bool(report.get("approved_for_paper_candidate")) or bool(report.get("approved_for_live_real")):
            reasons.append("LOGGER_REPORT_UNSAFE_APPROVAL_DETECTED")
        if bool(report.get("order_actions_performed")) or bool(report.get("post_requests_allowed")):
            reasons.append("LOGGER_REPORT_UNSAFE_ACTION_DETECTED")
    if not ready:
        reasons.append("HYP005_SHADOW_LOGGER_READY_NOT_CONFIRMED")
    return not reasons, sorted(set(reasons))


def validate_acceptance_reports(acceptance_reports: Sequence[Mapping[str, Any]]) -> tuple[bool, list[str], bool]:
    if not acceptance_reports:
        return False, ["HYP005_SHADOW_ACCEPTANCE_REPORT_MISSING"], False
    paper_ready = False
    reasons: list[str] = []
    saw_block_or_ready = False
    for report in acceptance_reports:
        decision = str(report.get("decision", ""))
        if decision in {"HYP005_SHADOW_PAPER_TRANSITION_BLOCK", "HYP005_SHADOW_PAPER_TRANSITION_READY"}:
            saw_block_or_ready = True
        if decision == "HYP005_SHADOW_PAPER_TRANSITION_READY":
            paper_ready = True
        if bool(report.get("approved_for_paper_candidate")) or bool(report.get("approved_for_live_real")):
            reasons.append("ACCEPTANCE_REPORT_UNSAFE_APPROVAL_DETECTED")
        if bool(report.get("order_actions_performed")) or bool(report.get("post_requests_allowed")):
            reasons.append("ACCEPTANCE_REPORT_UNSAFE_ACTION_DETECTED")
    if not saw_block_or_ready:
        reasons.append("HYP005_SHADOW_ACCEPTANCE_DECISION_NOT_CONFIRMED")
    return not reasons, sorted(set(reasons)), paper_ready


def validate_optional_acceptance_reports(
    acceptance_reports: Sequence[Mapping[str, Any]],
) -> tuple[bool, list[str], bool, bool]:
    """Inspect previous 25W reports as informational metadata only.

    25X is upstream of 25W in the runtime DAG. Missing acceptance evidence must
    never block collection bootstrap. Unsafe flags still block collection.
    """

    if not acceptance_reports:
        return True, ["HYP005_SHADOW_ACCEPTANCE_REPORT_OPTIONAL_FOR_COLLECTION_BOOTSTRAP"], False, False

    paper_ready = False
    saw_decision = False
    unsafe_reasons: list[str] = []
    informational_reasons: list[str] = ["HYP005_SHADOW_PREVIOUS_ACCEPTANCE_INFORMATIONAL_ONLY"]
    for report in acceptance_reports:
        decision = str(report.get("decision", ""))
        if decision in {"HYP005_SHADOW_PAPER_TRANSITION_BLOCK", "HYP005_SHADOW_PAPER_TRANSITION_READY"}:
            saw_decision = True
        if decision == "HYP005_SHADOW_PAPER_TRANSITION_READY":
            paper_ready = True
        if bool(report.get("approved_for_paper_candidate")) or bool(report.get("approved_for_live_real")):
            unsafe_reasons.append("ACCEPTANCE_REPORT_UNSAFE_APPROVAL_DETECTED")
        if bool(report.get("order_actions_performed")) or bool(report.get("post_requests_allowed")):
            unsafe_reasons.append("ACCEPTANCE_REPORT_UNSAFE_ACTION_DETECTED")
    if saw_decision:
        informational_reasons.append("HYP005_SHADOW_PREVIOUS_ACCEPTANCE_DECISION_INFORMATIONAL_METADATA_SEEN")
    else:
        informational_reasons.append("HYP005_SHADOW_PREVIOUS_ACCEPTANCE_DECISION_INFORMATIONAL_METADATA_UNCONFIRMED")
    reasons = sorted(set(informational_reasons + unsafe_reasons))
    return not unsafe_reasons, reasons, paper_ready, saw_decision


def _extract_observation_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [_as_mapping(item) for item in payload if isinstance(item, Mapping)]
    if not isinstance(payload, Mapping):
        return []
    for key in (
        "observations",
        "shadow_observations",
        "ledger",
        "rows",
        "records",
        "data",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return [_as_mapping(item) for item in value if isinstance(item, Mapping)]
    return []


def load_observations_from_json(path: str | Path) -> list[dict[str, Any]]:
    return _extract_observation_rows(load_json(path))


def load_observations_from_jsonl(path: str | Path) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
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
                observations.append(dict(payload))
    return observations


def observation_key(row: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the canonical HYP-005 event identity; market-price drift must not create a new sample."""
    return (canonical_event_key(row),)


def merge_observations(observation_sets: Iterable[Iterable[Mapping[str, Any]]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[tuple[str, ...]] = set()
    merged: list[dict[str, Any]] = []
    duplicate_count = 0
    for observations in observation_sets:
        for raw_row in observations:
            row = normalize_observation_identity(raw_row)
            key = observation_key(row)
            if key in seen:
                duplicate_count += 1
                continue
            seen.add(key)
            merged.append(row)
    merged.sort(key=lambda item: str(item.get("timestamp_utc") or item.get("timestamp") or ""))
    return merged, duplicate_count


def compute_progress(
    observations: Sequence[Mapping[str, Any]],
    duplicate_count: int,
    limits: Hyp005ShadowCollectionLimits,
) -> ShadowCollectionProgress:
    unique_count = len(observations)
    total_rows = unique_count + duplicate_count
    duplicate_pct = round((duplicate_count / total_rows) * 100.0, 6) if total_rows else 0.0
    symbols = sorted({str(row.get("symbol")) for row in observations if row.get("symbol")})
    days = sorted({str(row.get("timestamp_utc", ""))[:10] for row in observations if row.get("timestamp_utc")})
    progress_pct = round(min(100.0, (unique_count / max(1, limits.shadow_sample_target)) * 100.0), 6)
    return ShadowCollectionProgress(
        shadow_observation_count=unique_count,
        unique_observation_count=unique_count,
        duplicate_observation_count=duplicate_count,
        duplicate_observation_pct=duplicate_pct,
        shadow_sample_target=limits.shadow_sample_target,
        shadow_sample_target_met=unique_count >= limits.shadow_sample_target,
        progress_pct=progress_pct,
        observed_symbols=symbols,
        observed_days=len(days),
    )


def build_shadow_collection_plan(
    *,
    candidate_spec_path: str,
    symbols: Sequence[str],
    interval: str,
    days: int,
    base_url: str,
    out_dir: str,
    limits: Hyp005ShadowCollectionLimits,
    hypothesis_id: str,
    branch_name: str,
    selected_strategy_family: str,
) -> ShadowCollectionPlan:
    symbol_arg = ",".join(sorted({str(symbol).upper() for symbol in symbols if symbol}))
    logger_command = (
        "python tools/run_hyp005_shadow_observation_logger_4B436625V.py `\n"
        f"  --candidate-spec-json {candidate_spec_path} `\n"
        f"  --symbols {symbol_arg} `\n"
        f"  --interval {interval} `\n"
        f"  --days {days} `\n"
        f"  --base-url {base_url} `\n"
        f"  --out-dir {out_dir} `\n"
        "  --review-ok"
    )
    acceptance_command = (
        "python tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py `\n"
        f"  --reports-dir {out_dir} `\n"
        "  --include-all `\n"
        f"  --out-dir {out_dir} `\n"
        "  --review-ok"
    )
    return ShadowCollectionPlan(
        contract_version=HYP005_SHADOW_COLLECTION_ORCHESTRATOR_CONTRACT_VERSION,
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        selected_strategy_family=selected_strategy_family,
        no_order_collection_only=True,
        scheduler_cadence="Run after each fully closed 4h candle, or at least once daily until acceptance target is met.",
        collection_days=days,
        shadow_sample_target=limits.shadow_sample_target,
        commands=[
            ShadowCollectionCommand(
                name="collect_shadow_observations_no_order",
                description="Refresh no-order HYP-005 shadow observations. This command must remain GET-only and order-disabled.",
                powershell=logger_command,
            ),
            ShadowCollectionCommand(
                name="evaluate_shadow_acceptance_readiness",
                description="Re-evaluate paper-transition readiness from accumulated shadow ledgers. This does not enable paper trading.",
                powershell=acceptance_command,
            ),
        ],
        guardrails={
            "no_order_collection_only": True,
            "runtime_probe_only": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "training_performed": False,
            "paper_trading_started": False,
            "live_real_allowed": False,
            "paper_transition_requires_separate_gate": True,
            "live_transition_requires_separate_gate": True,
        },
    )


def build_hyp005_shadow_collection_orchestrator_report(
    *,
    candidate_spec: Mapping[str, Any],
    candidate_spec_path: str,
    logger_reports: Sequence[Mapping[str, Any]],
    acceptance_reports: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    duplicate_observation_count: int,
    ledger_source_count: int,
    symbols: Sequence[str],
    interval: str = "4h",
    days: int = 30,
    base_url: str = "https://api.binance.com",
    out_dir: str = "reports",
    limits: Hyp005ShadowCollectionLimits | None = None,
) -> ShadowCollectionReport:
    limits = limits or Hyp005ShadowCollectionLimits(collection_days=days, scheduler_interval=interval)
    spec_ok, spec_reasons = validate_no_order_candidate_spec(candidate_spec)
    logger_ok, logger_reasons = validate_logger_reports(logger_reports)
    acceptance_safe, acceptance_reasons, paper_ready_seen, acceptance_seen = validate_optional_acceptance_reports(acceptance_reports)

    hypothesis_id = _first_non_empty(
        candidate_spec.get("hypothesis_id"),
        _nested_get(candidate_spec, "candidate_spec", "hypothesis_id"),
        default="HYP-005",
    )
    branch_name = _first_non_empty(
        candidate_spec.get("branch_name"),
        _nested_get(candidate_spec, "candidate_spec", "branch_name"),
        default="liquidity_sweep_reversal_vol_compression",
    )
    selected_strategy_family = _first_non_empty(
        candidate_spec.get("selected_strategy_family"),
        candidate_spec.get("strategy_family"),
        _nested_get(candidate_spec, "candidate_spec", "selected_strategy_family"),
        _nested_get(candidate_spec, "candidate_spec", "strategy_family"),
        default="long_liquidity_sweep_reversal",
    )

    progress = compute_progress(observations, duplicate_observation_count, limits)
    plan = build_shadow_collection_plan(
        candidate_spec_path=candidate_spec_path,
        symbols=symbols,
        interval=interval,
        days=days,
        base_url=base_url,
        out_dir=out_dir,
        limits=limits,
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        selected_strategy_family=selected_strategy_family,
    )

    reasons: list[str] = []
    warnings: list[str] = []
    if spec_ok:
        reasons.append("HYP005_SHADOW_CANDIDATE_SPEC_CONFIRMED")
    else:
        reasons.extend(spec_reasons)
    if logger_ok:
        reasons.append("HYP005_SHADOW_LOGGER_READY_CONFIRMED")
    else:
        reasons.extend(logger_reasons)
    reasons.extend(acceptance_reasons)
    if acceptance_seen:
        reasons.append("HYP005_SHADOW_PREVIOUS_ACCEPTANCE_METADATA_SEEN")
    else:
        reasons.append("HYP005_SHADOW_ACCEPTANCE_NOT_REQUIRED_FOR_25X_COLLECTION_READY")
    if paper_ready_seen:
        warnings.append("PAPER_TRANSITION_READY_ALREADY_PRESENT_REQUIRES_SEPARATE_ENABLEMENT")

    if progress.duplicate_observation_pct > limits.max_duplicate_observation_pct:
        warnings.append("SHADOW_DUPLICATE_OBSERVATIONS_ELEVATED")
    if not progress.shadow_sample_target_met:
        warnings.append("SHADOW_SAMPLE_COLLECTION_IN_PROGRESS")

    ready = spec_ok and logger_ok and acceptance_safe
    collection_status = (
        HYP005_SHADOW_COLLECTION_STATUS_TARGET_MET
        if progress.shadow_sample_target_met
        else HYP005_SHADOW_COLLECTION_STATUS_IN_PROGRESS
    )
    if ready:
        decision = HYP005_SHADOW_COLLECTION_READY
        reasons.extend([
            "NO_ORDER_SHADOW_COLLECTION_PLAN_READY",
            NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED,
        ])
        recommendation = (
            "HYP-005 no-order shadow collection orchestrator is ready. Collection progress is independent from downstream 25W paper-transition readiness. Keep running the logger/scheduler; do not train, reload, paper trade, or enable live trading."
        )
    else:
        decision = HYP005_SHADOW_COLLECTION_BLOCK
        reasons.append("HYP005_SHADOW_COLLECTION_PREREQUISITES_NOT_MET")
        recommendation = (
            "HYP-005 shadow collection prerequisites are incomplete. Fix the no-order spec/logger safety evidence before scheduling collection; downstream 25W acceptance is not a 25X bootstrap prerequisite. Do not train, reload, paper trade, or enable live trading."
        )

    return ShadowCollectionReport(
        contract_version=HYP005_SHADOW_COLLECTION_ORCHESTRATOR_CONTRACT_VERSION,
        phase="4B.4.3.6.6.25X",
        report_type="hyp005_shadow_collection_orchestrator_no_order_scheduler_gate",
        decision=decision,
        ok=ready,
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        selected_strategy_family=selected_strategy_family,
        source_reports=len(logger_reports) + len(acceptance_reports) + 1,
        source_ledgers=ledger_source_count,
        no_order_collection_only=True,
        runtime_probe_only=True,
        shadow_collection_ready=ready,
        approved_for_shadow_collection=ready,
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
        collection_status=collection_status,
        shadow_observation_count=progress.shadow_observation_count,
        shadow_sample_target=progress.shadow_sample_target,
        progress_pct=progress.progress_pct,
        acceptance_report_required_for_collection_ready=False,
        acceptance_report_seen=acceptance_seen,
        previous_acceptance_informational_only=True,
        progress=asdict(progress),
        plan={
            **asdict(plan),
            "commands": [asdict(command) for command in plan.commands],
        },
        reason_codes=sorted(set(reasons)),
        warnings=sorted(set(warnings)),
        recommendation=recommendation,
    )


def write_markdown_report(path: str | Path, report: Mapping[str, Any]) -> None:
    progress = _as_mapping(report.get("progress"))
    plan = _as_mapping(report.get("plan"))
    commands = plan.get("commands") if isinstance(plan.get("commands"), list) else []
    lines = [
        "# 4B.4.3.6.6.25X HYP-005 Shadow Collection Orchestrator",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- selected_strategy_family: `{report.get('selected_strategy_family')}`",
        f"- shadow_collection_ready: `{report.get('shadow_collection_ready')}`",
        f"- no_order_collection_only: `{report.get('no_order_collection_only')}`",
        f"- approved_for_shadow_collection: `{report.get('approved_for_shadow_collection')}`",
        f"- approved_for_paper_transition_candidate: `{report.get('approved_for_paper_transition_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- collection_status: `{report.get('collection_status')}`",
        f"- acceptance_report_required_for_collection_ready: `{report.get('acceptance_report_required_for_collection_ready')}`",
        "",
        "## Progress",
        "",
        f"- shadow_observation_count: `{progress.get('shadow_observation_count')}`",
        f"- shadow_sample_target: `{progress.get('shadow_sample_target')}`",
        f"- progress_pct: `{progress.get('progress_pct')}`",
        f"- duplicate_observation_count: `{progress.get('duplicate_observation_count')}`",
        f"- duplicate_observation_pct: `{progress.get('duplicate_observation_pct')}`",
        "",
        "## Commands",
        "",
    ]
    for command in commands:
        command_map = _as_mapping(command)
        lines.extend([
            f"### {command_map.get('name')}",
            "",
            str(command_map.get("description", "")),
            "",
            "```powershell",
            str(command_map.get("powershell", "")),
            "```",
            "",
        ])
    lines.extend([
        "## Guardrails",
        "",
        "- This gate does not send orders.",
        "- This gate does not start paper trading.",
        "- This gate does not enable live trading.",
        "- This gate does not train or reload models.",
        "- Paper-transition readiness requires a separate gate and manual review.",
        "",
        "## Reason Codes",
        "",
        "```",
        json.dumps(report.get("reason_codes", []), indent=2),
        "```",
        "",
        "## Warnings",
        "",
        "```",
        json.dumps(report.get("warnings", []), indent=2),
        "```",
        "",
        f"Recommendation: {report.get('recommendation')}",
        "",
    ])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def as_serializable_report(report: ShadowCollectionReport) -> dict[str, Any]:
    return asdict(report)

# 25AE-H4 marker inventory:
# HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION
# HYP005_SHADOW_ACCEPTANCE_REPORT_OPTIONAL_FOR_COLLECTION_BOOTSTRAP
# HYP005_SHADOW_ACCEPTANCE_NOT_REQUIRED_FOR_25X_COLLECTION_READY
# acceptance_report_required_for_collection_ready
# previous_acceptance_informational_only
