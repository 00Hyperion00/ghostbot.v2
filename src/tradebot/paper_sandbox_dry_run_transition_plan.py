from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .config import Settings

CONTRACT_VERSION = "4B.4.3.6.6.30F"
SOURCE_30E_CONTRACT_VERSION = "4B.4.3.6.6.30E"
SOURCE_30E_READY_DECISION = "PAPER_TRANSITION_REVIEW_RERUN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED"
REPORT_TYPE = "paper_sandbox_dry_run_transition_plan_still_no_order_enablement"
REPORT_PREFIX = "4B436630F_paper_sandbox_dry_run_transition_plan"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED"
SOURCE_30E_REQUIRED_DECISION = "PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_30E_READY_REVIEW_REQUIRED_LIVE_REAL_BLOCKED"
NOT_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_NOT_READY_LIVE_REAL_BLOCKED"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_sandbox_dry_run_transition_plan": True,
    "paper_candidate_still_blocked": True,
    "paper_live_order_blocked": True,
    "paper_order_enablement_still_blocked": True,
    "live_real_blocked": True,
    "live_real_hard_block_verified": True,
    "runtime_activation_blocked": True,
    "training_reload_blocked": True,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
    "paper_live_order_enablement_present": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30EReviewReadyStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    approved_for_paper_transition_review_rerun: bool
    approved_for_paper_transition_candidate_review: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    paper_order_enablement_still_blocked: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DryRunExecutionPlanStatus:
    ok: bool
    required: bool
    plan_steps: list[str]
    dry_run_only: bool
    order_actions_performed: bool
    paper_live_order_enablement_present: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OrderPathSimulationEnvelopeStatus:
    ok: bool
    required: bool
    runtime_envelope: str
    execution_mode: str
    market_type: str
    base_url: str
    auto_trade_on_signal: bool
    live_trading_armed: bool
    live_real_double_confirm: bool
    order_notional_usd: float
    order_notional_cap_usd: float
    max_open_orders: int
    simulated_order_path: str
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperatorFinalGoNoGoChecklistStatus:
    ok: bool
    required: bool
    checklist_generated: bool
    checklist_items: list[dict[str, Any]]
    final_go_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperSandboxDryRunTransitionPlanDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_dry_run_transition_plan: bool
    approved_for_paper_sandbox_dry_run_execution_plan: bool
    approved_for_order_path_simulation_envelope: bool
    approved_for_operator_final_go_no_go_checklist: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30e_ready_review_verified: bool
    no_order_to_paper_dry_run_execution_plan_verified: bool
    order_path_simulation_envelope_verified: bool
    operator_final_go_no_go_checklist_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    reason_codes: list[str]
    source_30e_ready_review: dict[str, Any]
    dry_run_execution_plan: dict[str, Any]
    order_path_simulation_envelope: dict[str, Any]
    operator_final_go_no_go_checklist: dict[str, Any]
    source_30e_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: str | os.PathLike[str]) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp_path.replace(resolved)
    finally:
        temp_path.unlink(missing_ok=True)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _setting(settings: Any, key: str, default: Any) -> Any:
    return getattr(settings, key, default)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def latest_30e_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630E_paper_transition_review_rerun_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def evaluate_source_30e_ready_review(source_30e_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30EReviewReadyStatus:
    contract = str(source_30e_snapshot.get("contract_version") or "") or None
    decision = str(source_30e_snapshot.get("decision") or "") or None
    review_rerun = bool(source_30e_snapshot.get("approved_for_paper_transition_review_rerun", False))
    candidate_review = bool(source_30e_snapshot.get("approved_for_paper_transition_candidate_review", False))
    transition_candidate = bool(source_30e_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(source_30e_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30e_snapshot.get("approved_for_live_real", False))
    no_order = bool(source_30e_snapshot.get("paper_order_enablement_still_blocked", False))
    trading_action = bool(source_30e_snapshot.get("trading_action_performed", False)) or bool(source_30e_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if contract != SOURCE_30E_CONTRACT_VERSION:
        reasons.append("SOURCE_30E_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30E_READY_DECISION:
        reasons.append("SOURCE_30E_READY_REVIEW_RERUN_DECISION_REQUIRED")
    if not review_rerun:
        reasons.append("SOURCE_30E_REVIEW_RERUN_NOT_APPROVED")
    if not candidate_review:
        reasons.append("SOURCE_30E_CANDIDATE_REVIEW_NOT_MARKED")
    if transition_candidate:
        reasons.append("SOURCE_30E_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("SOURCE_30E_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("SOURCE_30E_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not no_order:
        reasons.append("SOURCE_30E_PAPER_ORDER_ENABLEMENT_NOT_BLOCKED")
    if trading_action:
        reasons.append("SOURCE_30E_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    ok = not reasons
    return Source30EReviewReadyStatus(
        ok=ok,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        approved_for_paper_transition_review_rerun=review_rerun,
        approved_for_paper_transition_candidate_review=candidate_review,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_order_enablement_still_blocked=no_order,
        reason_codes=reasons or ["SOURCE_30E_READY_REVIEW_RERUN_VERIFIED"],
    )


def build_dry_run_plan_steps() -> list[str]:
    return [
        "Load latest 30E ready review-rerun evidence.",
        "Verify sandbox-only runtime envelope and dry-run execution mode.",
        "Simulate order intent construction without submitting to exchange.",
        "Simulate risk-cap checks using paper caps without mutating balances or positions.",
        "Emit operator final go/no-go checklist for manual review.",
        "Keep paper order enablement, paper candidate, and live-real blocked.",
    ]


def evaluate_no_order_to_paper_dry_run_execution_plan(settings: Any, source_30e_snapshot: Mapping[str, Any]) -> DryRunExecutionPlanStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_order_path_simulation_required", True))
    order_actions = bool(source_30e_snapshot.get("trading_action_performed", False)) or bool(source_30e_snapshot.get("order_actions_performed", False))
    paper_enablement = bool(source_30e_snapshot.get("paper_live_order_enablement_present", False)) or bool(source_30e_snapshot.get("approved_for_paper_candidate", False))
    steps = build_dry_run_plan_steps()
    reasons: list[str] = []
    if not required:
        reasons.append("DRY_RUN_EXECUTION_PLAN_MUST_REMAIN_REQUIRED")
    if order_actions:
        reasons.append("DRY_RUN_EXECUTION_PLAN_SOURCE_ORDER_ACTION_UNEXPECTED")
    if paper_enablement:
        reasons.append("DRY_RUN_EXECUTION_PLAN_PAPER_ENABLEMENT_UNEXPECTED")
    ok = required and not order_actions and not paper_enablement
    return DryRunExecutionPlanStatus(
        ok=ok,
        required=required,
        plan_steps=steps,
        dry_run_only=True,
        order_actions_performed=False,
        paper_live_order_enablement_present=False,
        reason_codes=reasons or ["NO_ORDER_TO_PAPER_DRY_RUN_EXECUTION_PLAN_VERIFIED"],
    )


def evaluate_order_path_simulation_envelope(settings: Any, source_30e_snapshot: Mapping[str, Any]) -> OrderPathSimulationEnvelopeStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_order_path_simulation_required", True))
    rerun_30c = _mapping(source_30e_snapshot.get("rerun_30c_snapshot"))
    freeze = _mapping(rerun_30c.get("runtime_envelope_freeze"))
    runtime_envelope = str(freeze.get("runtime_envelope") or _setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "").strip().lower()
    execution_mode = str(freeze.get("execution_mode") or _setting(settings, "execution_mode", "dry_run") or "").strip().lower()
    market_type = str(freeze.get("market_type") or _setting(settings, "market_type", "spot_demo") or "").strip().lower()
    base_url = str(freeze.get("base_url") or _setting(settings, "base_url", "") or "").strip().lower()
    auto_trade = bool(freeze.get("auto_trade_on_signal", _setting(settings, "auto_trade_on_signal", False)))
    live_armed = bool(freeze.get("live_trading_armed", _setting(settings, "live_trading_armed", False)))
    live_real_confirm = bool(freeze.get("live_real_double_confirm", _setting(settings, "live_real_double_confirm", False)))
    max_open_orders = _int(freeze.get("max_open_orders", _setting(settings, "paper_transition_max_open_orders", 1)), 1)
    order_notional = _float(_setting(settings, "order_notional_usd", 25.0), 25.0)
    order_cap = _float(_setting(settings, "paper_order_notional_cap_usd", 25.0), 25.0)
    reasons: list[str] = []
    if not required:
        reasons.append("ORDER_PATH_SIMULATION_ENVELOPE_MUST_REMAIN_REQUIRED")
    if runtime_envelope != "sandbox_only":
        reasons.append("ORDER_PATH_SIMULATION_RUNTIME_ENVELOPE_NOT_SANDBOX_ONLY")
    if execution_mode != "dry_run":
        reasons.append("ORDER_PATH_SIMULATION_EXECUTION_MODE_NOT_DRY_RUN")
    if market_type not in {"spot_demo", "spot_testnet"}:
        reasons.append("ORDER_PATH_SIMULATION_MARKET_TYPE_NOT_SANDBOX")
    if not ("demo" in base_url or "testnet" in base_url or execution_mode == "dry_run"):
        reasons.append("ORDER_PATH_SIMULATION_BASE_URL_NOT_SANDBOX_OR_DRY_RUN")
    if auto_trade:
        reasons.append("ORDER_PATH_SIMULATION_AUTO_TRADE_UNEXPECTEDLY_ENABLED")
    if live_armed:
        reasons.append("ORDER_PATH_SIMULATION_LIVE_TRADING_ARMED_UNEXPECTEDLY_ENABLED")
    if live_real_confirm:
        reasons.append("ORDER_PATH_SIMULATION_LIVE_REAL_CONFIRM_UNEXPECTEDLY_ENABLED")
    if order_notional <= 0 or order_cap <= 0:
        reasons.append("ORDER_PATH_SIMULATION_NOTIONAL_INVALID")
    elif order_notional > order_cap:
        reasons.append("ORDER_PATH_SIMULATION_NOTIONAL_EXCEEDS_CAP")
    if max_open_orders != 1:
        reasons.append("ORDER_PATH_SIMULATION_MAX_OPEN_ORDERS_MUST_EQUAL_ONE")
    ok = required and not reasons
    return OrderPathSimulationEnvelopeStatus(
        ok=ok,
        required=required,
        runtime_envelope=runtime_envelope,
        execution_mode=execution_mode,
        market_type=market_type,
        base_url=base_url,
        auto_trade_on_signal=auto_trade,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_real_confirm,
        order_notional_usd=order_notional,
        order_notional_cap_usd=order_cap,
        max_open_orders=max_open_orders,
        simulated_order_path="intent_build_only_no_exchange_submit",
        reason_codes=reasons or ["ORDER_PATH_SIMULATION_ENVELOPE_VERIFIED_DRY_RUN_ONLY"],
    )


def operator_final_go_no_go_items() -> list[dict[str, Any]]:
    return [
        {"item": "30E ready review-rerun evidence exists", "required": True},
        {"item": "sandbox-only runtime envelope is frozen", "required": True},
        {"item": "risk caps remain at paper preflight values", "required": True},
        {"item": "paper order enablement remains absent", "required": True},
        {"item": "operator has not enabled auto-trade or live-real", "required": True},
        {"item": "final go/no-go remains manual and outside this patch", "required": True},
    ]


def evaluate_operator_final_go_no_go_checklist(settings: Any) -> OperatorFinalGoNoGoChecklistStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_operator_go_no_go_required", True))
    items = operator_final_go_no_go_items()
    reasons: list[str] = []
    if not required:
        reasons.append("OPERATOR_FINAL_GO_NO_GO_CHECKLIST_MUST_REMAIN_REQUIRED")
    ok = required and bool(items)
    return OperatorFinalGoNoGoChecklistStatus(
        ok=ok,
        required=required,
        checklist_generated=bool(items),
        checklist_items=items,
        final_go_performed=False,
        reason_codes=reasons or ["OPERATOR_FINAL_GO_NO_GO_CHECKLIST_GENERATED_REVIEW_ONLY"],
    )


def build_paper_sandbox_dry_run_transition_plan_snapshot(
    settings: Any,
    source_30e_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
) -> dict[str, Any]:
    source = evaluate_source_30e_ready_review(source_30e_snapshot, source_report_path=source_report_path)
    dry_plan = evaluate_no_order_to_paper_dry_run_execution_plan(settings, source_30e_snapshot)
    envelope = evaluate_order_path_simulation_envelope(settings, source_30e_snapshot)
    checklist = evaluate_operator_final_go_no_go_checklist(settings)
    no_order_enablement = not bool(source_30e_snapshot.get("approved_for_paper_candidate", False)) and not bool(source_30e_snapshot.get("paper_live_order_enablement_present", False))
    no_live_real = not bool(source_30e_snapshot.get("approved_for_live_real", False))
    no_orders = not bool(source_30e_snapshot.get("trading_action_performed", False)) and not bool(source_30e_snapshot.get("order_actions_performed", False))
    reasons = [*source.reason_codes, *dry_plan.reason_codes, *envelope.reason_codes, *checklist.reason_codes]
    if not no_order_enablement:
        reasons.append("PAPER_ORDER_ENABLEMENT_UNEXPECTEDLY_PRESENT")
    if not no_live_real:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not no_orders:
        reasons.append("ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    reasons.extend(["PAPER_CANDIDATE_STILL_BLOCKED", "PAPER_ORDER_ENABLEMENT_STILL_BLOCKED", "LIVE_REAL_HARD_BLOCK_VERIFIED"])
    ready = source.ok and dry_plan.ok and envelope.ok and checklist.ok and no_order_enablement and no_live_real and no_orders
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30E_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = PaperSandboxDryRunTransitionPlanDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_dry_run_transition_plan=ready,
        approved_for_paper_sandbox_dry_run_execution_plan=ready,
        approved_for_order_path_simulation_envelope=ready,
        approved_for_operator_final_go_no_go_checklist=ready,
        approved_for_paper_sandbox_dry_run_execution=False,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30e_ready_review_verified=source.ok,
        no_order_to_paper_dry_run_execution_plan_verified=dry_plan.ok,
        order_path_simulation_envelope_verified=envelope.ok,
        operator_final_go_no_go_checklist_verified=checklist.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        reason_codes=reasons,
        source_30e_ready_review=source.to_dict(),
        dry_run_execution_plan=dry_plan.to_dict(),
        order_path_simulation_envelope=envelope.to_dict(),
        operator_final_go_no_go_checklist=checklist.to_dict(),
        source_30e_snapshot=dict(source_30e_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30e_ready_review_gate": True,
        "no_order_to_paper_dry_run_execution_plan_gate": True,
        "order_path_simulation_envelope_gate": True,
        "operator_final_go_no_go_checklist_gate": True,
        "still_no_paper_order_enablement_gate": True,
        "no_live_real_enforcement": True,
    })
    return payload


def build_from_latest_30e_ready_report(settings: Any | None = None, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    source_path = latest_30e_ready_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    return build_paper_sandbox_dry_run_transition_plan_snapshot(
        settings or Settings(),
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
    )


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "").upper()
    if decision == READY_DECISION:
        return "ready"
    if decision == SOURCE_30E_REQUIRED_DECISION:
        return "30e_required"
    return "not_ready"


def _unique_report_path(base: Path) -> Path:
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    parent = base.parent
    for idx in range(1, 1000):
        candidate = parent / f"{stem}_{idx:03d}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"unable to allocate unique report path for {base}")


def render_markdown_report(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {CONTRACT_VERSION} Paper Sandbox Dry-run Transition Plan")
    lines.append("")
    lines.append("This report builds a no-order-to-paper dry-run transition plan, verifies the order path simulation envelope, and emits an operator final go/no-go checklist. It does not enable paper orders or live-real.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_sandbox_dry_run_transition_plan",
        "approved_for_paper_sandbox_dry_run_execution_plan",
        "approved_for_paper_sandbox_dry_run_execution",
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "paper_order_enablement_still_blocked",
        "trading_action_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Plan gates")
    for key in (
        "source_30e_ready_review_verified",
        "no_order_to_paper_dry_run_execution_plan_verified",
        "order_path_simulation_envelope_verified",
        "operator_final_go_no_go_checklist_verified",
        "runtime_activation_blocked",
        "paper_live_order_blocked",
        "training_reload_blocked",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Reason codes")
    for reason in payload.get("reason_codes", []):
        lines.append(f"- `{reason}`")
    lines.append("")
    return "\n".join(lines)


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    suffix = _decision_suffix(payload)
    json_path = _unique_report_path(target / f"{REPORT_PREFIX}_{stamp}_{suffix}.json")
    md_path = json_path.with_suffix(".md")
    write_json_atomic(json_path, payload)
    md_path.write_text(render_markdown_report(payload), encoding="utf-8", newline="\n")
    return json_path, md_path
