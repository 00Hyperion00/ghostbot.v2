from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from .config import Settings
except Exception:  # pragma: no cover - defensive import fallback for isolated tooling tests
    class Settings:  # type: ignore[no-redef]
        post_freeze_release_candidate_review_enabled: bool = True
        post_freeze_no_live_submit_required: bool = True
        post_freeze_release_candidate_finalization_token: str = "FINALIZE_32A_RELEASE_CANDIDATE_REVIEW"
        post_freeze_capital_cap_hard_limit_usdt: float = 50.0
        post_freeze_second_micro_canary_hard_cap_usdt: float = 10.0

CONTRACT_VERSION = "4B.4.3.6.6.32A"
SOURCE_31B_CONTRACT_VERSION = "4B.4.3.6.6.31B"
SOURCE_31B_READY_DECISION = "RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_READY_FINAL_AUDIT_SNAPSHOT_NO_FURTHER_LIVE_ORDER"
REPORT_TYPE = "post_freeze_release_candidate_review"
REPORT_PREFIX = "4B436632A_post_freeze_release_candidate_review"
SOURCE_31B_REPORT_PREFIX = "4B436631B_release_hygiene_bad_evidence_ledger_cleanup"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
FINALIZATION_TOKEN = "FINALIZE_32A_RELEASE_CANDIDATE_REVIEW"

READY_DECISION = "POST_FREEZE_RELEASE_CANDIDATE_REVIEW_READY_SECOND_MICRO_CANARY_ELIGIBILITY_GATE_NO_LIVE_ORDER_SUBMIT"
SOURCE_31B_REQUIRED_DECISION = "POST_FREEZE_RELEASE_CANDIDATE_REVIEW_31B_READY_REQUIRED_NO_LIVE_ORDER_SUBMIT"
CAPITAL_CAP_REQUIRED_DECISION = "POST_FREEZE_RELEASE_CANDIDATE_REVIEW_CAPITAL_CAP_REQUIRED_NO_LIVE_ORDER_SUBMIT"
EMERGENCY_STOP_REQUIRED_DECISION = "POST_FREEZE_RELEASE_CANDIDATE_REVIEW_EMERGENCY_STOP_REQUIRED_NO_LIVE_ORDER_SUBMIT"
OPERATOR_APPROVAL_REQUIRED_DECISION = "POST_FREEZE_RELEASE_CANDIDATE_REVIEW_OPERATOR_APPROVAL_REQUIRED_NO_LIVE_ORDER_SUBMIT"
NOT_READY_DECISION = "POST_FREEZE_RELEASE_CANDIDATE_REVIEW_NOT_READY_NO_LIVE_ORDER_SUBMIT"

DEFAULT_CAPITAL_CAP_HARD_LIMIT_USDT = 50.0
DEFAULT_SECOND_MICRO_HARD_CAP_USDT = 10.0
DEFAULT_MAX_SLIPPAGE_BPS_LIMIT = 100.0

RISK_FLAGS: dict[str, bool] = {
    "post_freeze_release_candidate_review_only": True,
    "final_audit_snapshot_review_only": True,
    "second_micro_canary_eligibility_gate_only": True,
    "no_live_order_submit_contract": True,
    "approved_for_exchange_submit": False,
    "approved_for_additional_exchange_submit": False,
    "approved_for_live_real_order": False,
    "approved_for_second_micro_canary_order_submit": False,
    "patch_exchange_submit_performed": False,
    "patch_network_submit_attempted": False,
    "patch_live_real_order_performed": False,
    "additional_exchange_submit_performed": False,
    "additional_network_submit_attempted": False,
    "additional_live_real_order_performed": False,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source31BStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    source_31a_h3_freeze_audit_closure_verified: bool
    bad_evidence_history_explained: bool
    bad_evidence_quarantined: bool
    final_audit_snapshot_written: bool
    no_further_live_orders_verified: bool
    emergency_stop_continuity_verified: bool
    no_code_path_live_submit_verified: bool
    approved_for_additional_exchange_submit: bool
    approved_for_live_real_continuation: bool
    approved_for_live_real_order: bool
    patch_network_submit_attempted: bool
    patch_exchange_submit_performed: bool
    patch_live_real_order_performed: bool
    additional_exchange_submit_performed: bool
    additional_network_submit_attempted: bool
    additional_live_real_order_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CapitalCapStatus:
    ok: bool
    capital_cap_usdt: float | None
    second_micro_max_notional_usdt: float | None
    daily_loss_limit_usdt: float | None
    max_slippage_bps: float | None
    capital_cap_confirmed: bool
    second_micro_canary_notional_confirmed: bool
    daily_loss_limit_confirmed: bool
    slippage_limit_confirmed: bool
    capital_cap_hard_limit_usdt: float
    second_micro_hard_cap_usdt: float
    max_slippage_bps_limit: float
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperatorReviewStatus:
    ok: bool
    operator_id: str | None
    finalization_token_verified: bool
    emergency_stop_armed: bool
    audit_comment: str | None
    live_real_continuation_risk_decision: str
    no_live_order_submit_confirmed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PostFreezeReleaseCandidateSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_post_freeze_release_candidate_review: bool
    approved_for_live_real_continuation_candidate: bool
    approved_for_second_micro_canary_eligibility_gate: bool
    approved_for_exchange_submit: bool
    approved_for_additional_exchange_submit: bool
    approved_for_live_real_order: bool
    approved_for_second_micro_canary_order_submit: bool
    source_31b_release_hygiene_verified: bool
    final_audit_snapshot_reviewed: bool
    live_real_continuation_risk_decision: str
    capital_cap_confirmed: bool
    capital_cap_usdt: float | None
    second_micro_canary_eligible_candidate: bool
    second_micro_max_notional_usdt: float | None
    daily_loss_limit_usdt: float | None
    max_slippage_bps: float | None
    emergency_stop_armed_verified: bool
    no_live_order_submit_verified: bool
    no_code_path_live_submit_verified: bool
    patch_exchange_submit_performed: bool
    patch_network_submit_attempted: bool
    patch_live_real_order_performed: bool
    additional_exchange_submit_performed: bool
    additional_network_submit_attempted: bool
    additional_live_real_order_performed: bool
    reason_codes: list[str]
    source_31b: dict[str, Any]
    capital_cap: dict[str, Any]
    operator_review: dict[str, Any]
    source_31b_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _boolish(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default if value is None else bool(value)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:  # NaN / infinities
        return None
    return parsed


def load_json(path: str | os.PathLike[str]) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent, delete=False) as handle:
        tmp = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp.replace(resolved)
    finally:
        tmp.unlink(missing_ok=True)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def evaluate_source_31b_release_hygiene(source_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source31BStatus:
    contract = str(source_snapshot.get("contract_version") or "") or None
    decision = str(source_snapshot.get("decision") or "") or None
    source_31a = _boolish(source_snapshot.get("source_31a_h3_freeze_audit_closure_verified"), False)
    bad_explained = _boolish(source_snapshot.get("bad_evidence_history_explained"), False)
    quarantined = _boolish(source_snapshot.get("bad_evidence_quarantined"), False)
    final_audit = _boolish(source_snapshot.get("final_audit_snapshot_written"), False)
    no_further = _boolish(source_snapshot.get("no_further_live_orders_verified"), False)
    emergency = _boolish(source_snapshot.get("emergency_stop_continuity_verified"), False)
    no_code_path = _boolish(source_snapshot.get("no_code_path_live_submit_verified"), True)
    additional_approved = _boolish(source_snapshot.get("approved_for_additional_exchange_submit"), False)
    continuation = _boolish(source_snapshot.get("approved_for_live_real_continuation"), False)
    live_order_approved = _boolish(source_snapshot.get("approved_for_live_real_order"), False)
    patch_network = _boolish(source_snapshot.get("patch_network_submit_attempted"), False)
    patch_exchange = _boolish(source_snapshot.get("patch_exchange_submit_performed"), False)
    patch_live = _boolish(source_snapshot.get("patch_live_real_order_performed"), False)
    additional_exchange = _boolish(source_snapshot.get("additional_exchange_submit_performed"), False)
    additional_network = _boolish(source_snapshot.get("additional_network_submit_attempted"), False)
    additional_live = _boolish(source_snapshot.get("additional_live_real_order_performed"), False)
    ok = (
        contract == SOURCE_31B_CONTRACT_VERSION
        and decision == SOURCE_31B_READY_DECISION
        and source_31a
        and bad_explained
        and quarantined
        and final_audit
        and no_further
        and emergency
        and no_code_path
        and not additional_approved
        and not continuation
        and not live_order_approved
        and not patch_network
        and not patch_exchange
        and not patch_live
        and not additional_exchange
        and not additional_network
        and not additional_live
    )
    reasons: list[str] = []
    if contract != SOURCE_31B_CONTRACT_VERSION:
        reasons.append("SOURCE_31B_CONTRACT_VERSION_REQUIRED")
    if decision != SOURCE_31B_READY_DECISION:
        reasons.append("SOURCE_31B_READY_DECISION_REQUIRED")
    if not source_31a:
        reasons.append("SOURCE_31B_MUST_VERIFY_31A_H3_FREEZE_CLOSURE")
    if not bad_explained:
        reasons.append("SOURCE_31B_BAD_EVIDENCE_HISTORY_EXPLANATION_REQUIRED")
    if not quarantined:
        reasons.append("SOURCE_31B_BAD_EVIDENCE_QUARANTINE_REQUIRED")
    if not final_audit:
        reasons.append("SOURCE_31B_FINAL_AUDIT_SNAPSHOT_REQUIRED")
    if not no_further:
        reasons.append("SOURCE_31B_NO_FURTHER_LIVE_ORDERS_REQUIRED")
    if not emergency:
        reasons.append("SOURCE_31B_EMERGENCY_STOP_CONTINUITY_REQUIRED")
    if not no_code_path:
        reasons.append("SOURCE_31B_NO_CODE_PATH_LIVE_SUBMIT_REQUIRED")
    if additional_approved or continuation or live_order_approved:
        reasons.append("SOURCE_31B_MUST_NOT_APPROVE_FURTHER_LIVE_REAL")
    if patch_network or patch_exchange or patch_live:
        reasons.append("SOURCE_31B_PATCH_SUBMIT_MUST_BE_FALSE")
    if additional_exchange or additional_network or additional_live:
        reasons.append("SOURCE_31B_ADDITIONAL_LIVE_ORDER_MUST_BE_FALSE")
    return Source31BStatus(
        ok=ok,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        source_31a_h3_freeze_audit_closure_verified=source_31a,
        bad_evidence_history_explained=bad_explained,
        bad_evidence_quarantined=quarantined,
        final_audit_snapshot_written=final_audit,
        no_further_live_orders_verified=no_further,
        emergency_stop_continuity_verified=emergency,
        no_code_path_live_submit_verified=no_code_path,
        approved_for_additional_exchange_submit=additional_approved,
        approved_for_live_real_continuation=continuation,
        approved_for_live_real_order=live_order_approved,
        patch_network_submit_attempted=patch_network,
        patch_exchange_submit_performed=patch_exchange,
        patch_live_real_order_performed=patch_live,
        additional_exchange_submit_performed=additional_exchange,
        additional_network_submit_attempted=additional_network,
        additional_live_real_order_performed=additional_live,
        reason_codes=reasons or ["SOURCE_31B_RELEASE_HYGIENE_FINAL_AUDIT_VERIFIED"],
    )


def latest_valid_31b_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    root = Path(reports_dir)
    candidates = sorted(
        (path for path in root.glob(f"{SOURCE_31B_REPORT_PREFIX}_*_ready.json") if "_not_ready" not in path.name),
        key=lambda item: item.stat().st_mtime if item.exists() else 0.0,
        reverse=True,
    )
    for path in candidates:
        try:
            payload = load_json(path)
        except Exception:
            continue
        if isinstance(payload, Mapping) and evaluate_source_31b_release_hygiene(payload, source_report_path=str(path)).ok:
            return path, dict(payload)
    return None, {}


def load_explicit_31b_report(source_report: str | os.PathLike[str]) -> tuple[Path, dict[str, Any]]:
    path = Path(source_report).expanduser().resolve()
    payload = load_json(path)
    if not isinstance(payload, Mapping):
        raise ValueError(f"source 31B report is not a JSON object: {path}")
    return path, dict(payload)


def evaluate_capital_cap_plan(
    *,
    capital_cap_usdt: float | str | None,
    second_micro_max_notional_usdt: float | str | None,
    daily_loss_limit_usdt: float | str | None,
    max_slippage_bps: float | str | None,
    capital_cap_hard_limit_usdt: float = DEFAULT_CAPITAL_CAP_HARD_LIMIT_USDT,
    second_micro_hard_cap_usdt: float = DEFAULT_SECOND_MICRO_HARD_CAP_USDT,
    max_slippage_bps_limit: float = DEFAULT_MAX_SLIPPAGE_BPS_LIMIT,
) -> CapitalCapStatus:
    cap = _float_or_none(capital_cap_usdt)
    second = _float_or_none(second_micro_max_notional_usdt)
    daily = _float_or_none(daily_loss_limit_usdt)
    slippage = _float_or_none(max_slippage_bps)
    reasons: list[str] = []
    cap_ok = cap is not None and 0.0 < cap <= capital_cap_hard_limit_usdt
    second_ok = second is not None and 0.0 < second <= second_micro_hard_cap_usdt and (cap is not None and second <= cap)
    daily_ok = daily is not None and 0.0 < daily <= (cap or 0.0)
    slippage_ok = slippage is not None and 0.0 < slippage <= max_slippage_bps_limit
    if not cap_ok:
        reasons.append("CAPITAL_CAP_USDT_REQUIRED_WITHIN_HARD_LIMIT")
    if not second_ok:
        reasons.append("SECOND_MICRO_MAX_NOTIONAL_REQUIRED_WITHIN_CAP_AND_HARD_LIMIT")
    if not daily_ok:
        reasons.append("DAILY_LOSS_LIMIT_REQUIRED_WITHIN_CAP")
    if not slippage_ok:
        reasons.append("MAX_SLIPPAGE_BPS_REQUIRED_WITHIN_LIMIT")
    return CapitalCapStatus(
        ok=cap_ok and second_ok and daily_ok and slippage_ok,
        capital_cap_usdt=cap,
        second_micro_max_notional_usdt=second,
        daily_loss_limit_usdt=daily,
        max_slippage_bps=slippage,
        capital_cap_confirmed=cap_ok,
        second_micro_canary_notional_confirmed=second_ok,
        daily_loss_limit_confirmed=daily_ok,
        slippage_limit_confirmed=slippage_ok,
        capital_cap_hard_limit_usdt=capital_cap_hard_limit_usdt,
        second_micro_hard_cap_usdt=second_micro_hard_cap_usdt,
        max_slippage_bps_limit=max_slippage_bps_limit,
        reason_codes=reasons or ["CAPITAL_CAP_AND_SECOND_MICRO_CANARY_LIMITS_CONFIRMED"],
    )


def evaluate_operator_review(
    *,
    operator_id: str | None,
    finalization_token: str | None,
    emergency_stop_armed: bool,
    audit_comment: str | None = None,
) -> OperatorReviewStatus:
    operator_ok = bool(str(operator_id or "").strip())
    token_ok = str(finalization_token or "").strip() == FINALIZATION_TOKEN
    emergency_ok = bool(emergency_stop_armed)
    reasons: list[str] = []
    if not operator_ok:
        reasons.append("OPERATOR_ID_REQUIRED")
    if not token_ok:
        reasons.append("FINALIZATION_TOKEN_REQUIRED")
    if not emergency_ok:
        reasons.append("EMERGENCY_STOP_ARMED_REQUIRED")
    decision = "CONTINUATION_CANDIDATE_ONLY_NO_ORDER_SUBMIT" if operator_ok and token_ok and emergency_ok else "CONTINUATION_REVIEW_BLOCKED_NO_ORDER_SUBMIT"
    return OperatorReviewStatus(
        ok=operator_ok and token_ok and emergency_ok,
        operator_id=str(operator_id or "").strip() or None,
        finalization_token_verified=token_ok,
        emergency_stop_armed=emergency_ok,
        audit_comment=str(audit_comment or "").strip() or None,
        live_real_continuation_risk_decision=decision,
        no_live_order_submit_confirmed=True,
        reason_codes=reasons or ["OPERATOR_POST_FREEZE_RELEASE_CANDIDATE_REVIEW_AUTHORIZED"],
    )


def build_post_freeze_release_candidate_review_snapshot(
    settings: Any | None = None,
    source_31b_snapshot: Mapping[str, Any] | None = None,
    *,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    source_report_path: str | None = None,
    operator_id: str | None = None,
    finalization_token: str | None = None,
    audit_comment: str | None = None,
    emergency_stop_armed: bool = False,
    capital_cap_usdt: float | str | None = None,
    second_micro_max_notional_usdt: float | str | None = None,
    daily_loss_limit_usdt: float | str | None = None,
    max_slippage_bps: float | str | None = None,
) -> dict[str, Any]:
    cfg = settings or Settings()
    hard_cap = _float_or_none(getattr(cfg, "post_freeze_capital_cap_hard_limit_usdt", DEFAULT_CAPITAL_CAP_HARD_LIMIT_USDT)) or DEFAULT_CAPITAL_CAP_HARD_LIMIT_USDT
    second_hard = _float_or_none(getattr(cfg, "post_freeze_second_micro_canary_hard_cap_usdt", DEFAULT_SECOND_MICRO_HARD_CAP_USDT)) or DEFAULT_SECOND_MICRO_HARD_CAP_USDT
    source_payload = dict(_mapping(source_31b_snapshot))
    source = evaluate_source_31b_release_hygiene(source_payload, source_report_path=source_report_path)
    capital = evaluate_capital_cap_plan(
        capital_cap_usdt=capital_cap_usdt,
        second_micro_max_notional_usdt=second_micro_max_notional_usdt,
        daily_loss_limit_usdt=daily_loss_limit_usdt,
        max_slippage_bps=max_slippage_bps,
        capital_cap_hard_limit_usdt=hard_cap,
        second_micro_hard_cap_usdt=second_hard,
    )
    operator = evaluate_operator_review(
        operator_id=operator_id,
        finalization_token=finalization_token,
        emergency_stop_armed=emergency_stop_armed,
        audit_comment=audit_comment,
    )
    reasons: list[str] = []
    if not source.ok:
        reasons.extend(source.reason_codes)
    if not capital.ok:
        reasons.extend(capital.reason_codes)
    if not operator.emergency_stop_armed:
        reasons.append("EMERGENCY_STOP_ARMED_REQUIRED")
    if not operator.ok:
        reasons.extend([reason for reason in operator.reason_codes if reason != "EMERGENCY_STOP_ARMED_REQUIRED"])
    no_code_path_live_submit = True
    no_live_submit = True
    ready = source.ok and capital.ok and operator.ok and no_code_path_live_submit and no_live_submit
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_31B_REQUIRED_DECISION
    elif not operator.emergency_stop_armed:
        decision = EMERGENCY_STOP_REQUIRED_DECISION
    elif not capital.ok:
        decision = CAPITAL_CAP_REQUIRED_DECISION
    elif not operator.ok:
        decision = OPERATOR_APPROVAL_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    continuation_decision = "CONTINUATION_CANDIDATE_APPROVED_NO_ORDER_SUBMIT" if ready else "CONTINUATION_REVIEW_BLOCKED_NO_ORDER_SUBMIT"
    snapshot = PostFreezeReleaseCandidateSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_31B_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_post_freeze_release_candidate_review=ready,
        approved_for_live_real_continuation_candidate=ready,
        approved_for_second_micro_canary_eligibility_gate=ready,
        approved_for_exchange_submit=False,
        approved_for_additional_exchange_submit=False,
        approved_for_live_real_order=False,
        approved_for_second_micro_canary_order_submit=False,
        source_31b_release_hygiene_verified=source.ok,
        final_audit_snapshot_reviewed=source.final_audit_snapshot_written,
        live_real_continuation_risk_decision=continuation_decision,
        capital_cap_confirmed=capital.capital_cap_confirmed,
        capital_cap_usdt=capital.capital_cap_usdt,
        second_micro_canary_eligible_candidate=ready,
        second_micro_max_notional_usdt=capital.second_micro_max_notional_usdt,
        daily_loss_limit_usdt=capital.daily_loss_limit_usdt,
        max_slippage_bps=capital.max_slippage_bps,
        emergency_stop_armed_verified=operator.emergency_stop_armed,
        no_live_order_submit_verified=no_live_submit,
        no_code_path_live_submit_verified=no_code_path_live_submit,
        patch_exchange_submit_performed=False,
        patch_network_submit_attempted=False,
        patch_live_real_order_performed=False,
        additional_exchange_submit_performed=False,
        additional_network_submit_attempted=False,
        additional_live_real_order_performed=False,
        reason_codes=reasons or ["POST_FREEZE_RELEASE_CANDIDATE_REVIEW_READY"],
        source_31b=source.to_dict(),
        capital_cap=capital.to_dict(),
        operator_review=operator.to_dict(),
        source_31b_snapshot=source_payload,
    ).to_dict()
    snapshot.update(RISK_FLAGS)
    return snapshot


def build_from_latest_31b_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    operator_id: str | None = None,
    finalization_token: str | None = None,
    audit_comment: str | None = None,
    emergency_stop_armed: bool = False,
    capital_cap_usdt: float | str | None = None,
    second_micro_max_notional_usdt: float | str | None = None,
    daily_loss_limit_usdt: float | str | None = None,
    max_slippage_bps: float | str | None = None,
) -> dict[str, Any]:
    source_path, source = latest_valid_31b_report(reports_dir)
    return build_post_freeze_release_candidate_review_snapshot(
        settings or Settings(),
        source,
        reports_dir=reports_dir,
        source_report_path=str(source_path) if source_path else None,
        operator_id=operator_id,
        finalization_token=finalization_token,
        audit_comment=audit_comment,
        emergency_stop_armed=emergency_stop_armed,
        capital_cap_usdt=capital_cap_usdt,
        second_micro_max_notional_usdt=second_micro_max_notional_usdt,
        daily_loss_limit_usdt=daily_loss_limit_usdt,
        max_slippage_bps=max_slippage_bps,
    )


def build_from_explicit_31b_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    source_31b_report: str | os.PathLike[str],
    operator_id: str | None = None,
    finalization_token: str | None = None,
    audit_comment: str | None = None,
    emergency_stop_armed: bool = False,
    capital_cap_usdt: float | str | None = None,
    second_micro_max_notional_usdt: float | str | None = None,
    daily_loss_limit_usdt: float | str | None = None,
    max_slippage_bps: float | str | None = None,
) -> dict[str, Any]:
    source_path, source = load_explicit_31b_report(source_31b_report)
    return build_post_freeze_release_candidate_review_snapshot(
        settings or Settings(),
        source,
        reports_dir=reports_dir,
        source_report_path=str(source_path),
        operator_id=operator_id,
        finalization_token=finalization_token,
        audit_comment=audit_comment,
        emergency_stop_armed=emergency_stop_armed,
        capital_cap_usdt=capital_cap_usdt,
        second_micro_max_notional_usdt=second_micro_max_notional_usdt,
        daily_loss_limit_usdt=daily_loss_limit_usdt,
        max_slippage_bps=max_slippage_bps,
    )


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(reports_dir)
    target.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if payload.get("decision") == READY_DECISION else "not_ready"
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    final_payload = dict(payload)
    write_json_atomic(json_path, final_payload)
    lines = [
        f"# {CONTRACT_VERSION} Post-Freeze Release Candidate Review",
        "",
        "Reviews the accepted 31B audit/hygiene closure, confirms capital caps, and produces a second micro-canary eligibility gate without submitting any live order.",
        "",
        "## Decision",
        f"- `decision`: `{final_payload.get('decision')}`",
        f"- `source_31b_release_hygiene_verified`: `{final_payload.get('source_31b_release_hygiene_verified')}`",
        f"- `final_audit_snapshot_reviewed`: `{final_payload.get('final_audit_snapshot_reviewed')}`",
        f"- `live_real_continuation_risk_decision`: `{final_payload.get('live_real_continuation_risk_decision')}`",
        f"- `capital_cap_confirmed`: `{final_payload.get('capital_cap_confirmed')}`",
        f"- `capital_cap_usdt`: `{final_payload.get('capital_cap_usdt')}`",
        f"- `second_micro_canary_eligible_candidate`: `{final_payload.get('second_micro_canary_eligible_candidate')}`",
        f"- `second_micro_max_notional_usdt`: `{final_payload.get('second_micro_max_notional_usdt')}`",
        f"- `daily_loss_limit_usdt`: `{final_payload.get('daily_loss_limit_usdt')}`",
        f"- `max_slippage_bps`: `{final_payload.get('max_slippage_bps')}`",
        f"- `emergency_stop_armed_verified`: `{final_payload.get('emergency_stop_armed_verified')}`",
        f"- `approved_for_live_real_order`: `{final_payload.get('approved_for_live_real_order')}`",
        f"- `patch_network_submit_attempted`: `{final_payload.get('patch_network_submit_attempted')}`",
        "",
        "## Source",
        f"- `source_31b_report`: `{_mapping(final_payload.get('source_31b')).get('source_report_path')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in final_payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
