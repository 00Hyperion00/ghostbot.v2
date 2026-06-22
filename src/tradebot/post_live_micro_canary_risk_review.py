from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "4B.4.3.6.6.30Z"
SOURCE_30Y_CONTRACT_VERSIONS = {"4B.4.3.6.6.30Y", "4B.4.3.6.6.30Y-H1"}
SOURCE_30Y_READY_DECISION = "LIVE_REAL_MICRO_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_EMERGENCY_STOP_ARMED"
REPORT_TYPE = "post_live_micro_canary_risk_review"
REPORT_PREFIX = "4B436630Z_post_live_micro_canary_risk_review"
SOURCE_30Y_REPORT_PREFIX = "4B436630Y_live_real_micro_canary_reconciliation"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "POST_LIVE_MICRO_CANARY_RISK_REVIEW_READY_PNL_FEE_SLIPPAGE_EMERGENCY_STOP_NO_ADDITIONAL_LIVE_ORDER"
SOURCE_REQUIRED_DECISION = "POST_LIVE_MICRO_CANARY_RISK_REVIEW_30Y_H1_RECONCILIATION_REQUIRED_NO_ADDITIONAL_LIVE_ORDER"
FEE_EVIDENCE_REQUIRED_DECISION = "POST_LIVE_MICRO_CANARY_RISK_REVIEW_FEE_EVIDENCE_REQUIRED_NO_ADDITIONAL_LIVE_ORDER"
EMERGENCY_STOP_REQUIRED_DECISION = "POST_LIVE_MICRO_CANARY_RISK_REVIEW_EMERGENCY_STOP_CONTINUITY_REQUIRED_NO_ADDITIONAL_LIVE_ORDER"
ADDITIONAL_ORDER_BLOCK_DECISION = "POST_LIVE_MICRO_CANARY_RISK_REVIEW_ADDITIONAL_LIVE_ORDER_DETECTED_STOP"
NOT_READY_DECISION = "POST_LIVE_MICRO_CANARY_RISK_REVIEW_NOT_READY_NO_ADDITIONAL_LIVE_ORDER"

RISK_FLAGS: dict[str, bool] = {
    "post_live_micro_canary_risk_review_only": True,
    "patch_network_submit_disabled": True,
    "patch_exchange_submit_performed": False,
    "patch_network_submit_attempted": False,
    "patch_live_real_order_performed": False,
    "additional_live_order_approved": False,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30YStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    source_ready: bool
    source_30x_submit_request_verified: bool
    source_mismatch_zero_verified: bool
    source_emergency_stop_armed_verified: bool
    source_further_live_real_submit_blocked: bool
    source_patch_network_submit_attempted: bool
    source_patch_exchange_submit_performed: bool
    source_additional_exchange_submit_approved: bool
    exchange_order_id: str | None
    symbol: str | None
    side: str | None
    filled_quantity: float
    avg_fill_price: float
    fill_notional_usd: float
    ledger_notional_usd: float
    fee_amount_from_source: float | None
    fee_asset_from_source: str | None
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RiskMetricsStatus:
    ok: bool
    pnl_evidence_verified: bool
    fee_evidence_verified: bool
    slippage_evidence_verified: bool
    mark_price_for_review: float
    reference_price: float
    filled_quantity: float
    avg_fill_price: float
    fill_notional_usd: float
    fee_amount: float
    fee_asset: str | None
    side: str | None
    unrealized_pnl_usd: float
    unrealized_pnl_pct: float
    slippage_usd: float
    slippage_pct: float
    fee_notional_ratio: float
    max_abs_slippage_pct_allowed: float
    max_abs_unrealized_pnl_pct_allowed: float
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ContinuityStatus:
    ok: bool
    emergency_stop_continuity_verified: bool
    kill_switch_continuity_verified: bool
    no_additional_live_order_verified: bool
    no_additional_network_submit_verified: bool
    no_additional_exchange_submit_verified: bool
    emergency_stop_armed: bool
    kill_switch_armed: bool
    additional_live_order_count: int
    additional_network_submit_count: int
    additional_exchange_submit_count: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PostLiveMicroCanaryRiskReviewSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_post_live_micro_canary_risk_review: bool
    approved_for_live_real_continuation: bool
    approved_for_additional_live_order: bool
    source_30y_h1_reconciliation_verified: bool
    real_fill_risk_review_verified: bool
    pnl_evidence_verified: bool
    fee_evidence_verified: bool
    slippage_evidence_verified: bool
    emergency_stop_continuity_verified: bool
    no_additional_live_order_verified: bool
    mismatch_zero_continuity_verified: bool
    patch_network_submit_attempted: bool
    patch_exchange_submit_performed: bool
    patch_live_real_order_performed: bool
    additional_live_order_count: int
    additional_network_submit_count: int
    additional_exchange_submit_count: int
    exchange_order_id: str | None
    symbol: str | None
    side: str | None
    filled_quantity: float
    avg_fill_price: float
    fill_notional_usd: float
    fee_amount: float
    fee_asset: str | None
    mark_price_for_review: float
    reference_price: float
    unrealized_pnl_usd: float
    unrealized_pnl_pct: float
    slippage_usd: float
    slippage_pct: float
    fee_notional_ratio: float
    reason_codes: list[str]
    source_30y: dict[str, Any]
    risk_metrics: dict[str, Any]
    continuity: dict[str, Any]
    source_30y_snapshot: dict[str, Any]
    operator_notes: str | None

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
        tmp = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp.replace(resolved)
    finally:
        tmp.unlink(missing_ok=True)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _boolish(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _nested_get(payload: Mapping[str, Any], paths: Iterable[tuple[str, ...]], default: Any = None) -> Any:
    for path in paths:
        cur: Any = payload
        ok = True
        for key in path:
            cur_map = _mapping(cur)
            if key not in cur_map:
                ok = False
                break
            cur = cur_map[key]
        if ok and cur is not None:
            return cur
    return default


def latest_valid_30y_h1_reconciliation_report(reports_dir: str | os.PathLike[str]) -> tuple[Path | None, dict[str, Any]]:
    base = Path(reports_dir)
    if not base.exists():
        return None, {}
    candidates = sorted(base.glob(f"{SOURCE_30Y_REPORT_PREFIX}_*_ready.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            payload = load_json(path)
        except Exception:
            continue
        status = evaluate_source_30y_h1_reconciliation(payload, source_report_path=path)
        if status.ok:
            return path, payload
    return None, {}


def evaluate_source_30y_h1_reconciliation(source_payload: Mapping[str, Any], source_report_path: str | os.PathLike[str] | None = None) -> Source30YStatus:
    reasons: list[str] = []
    contract_version = _str_or_none(source_payload.get("contract_version"))
    decision = _str_or_none(source_payload.get("decision"))
    execution = _mapping(source_payload.get("execution_evidence"))
    reconciliation = _mapping(source_payload.get("reconciliation"))
    source_30x = _mapping(source_payload.get("source_30x"))
    submit_request = _mapping(source_payload.get("submit_request_snapshot"))

    if contract_version not in SOURCE_30Y_CONTRACT_VERSIONS:
        reasons.append("SOURCE_30Y_CONTRACT_VERSION_NOT_ACCEPTED")
    if decision != SOURCE_30Y_READY_DECISION:
        reasons.append("SOURCE_30Y_DECISION_NOT_READY")

    source_ready = decision == SOURCE_30Y_READY_DECISION
    source_30x_verified = _boolish(source_payload.get("source_30x_submit_request_verified"), False)
    mismatch_zero = _boolish(source_payload.get("mismatch_zero_verified"), False) and _int(source_payload.get("mismatch_count"), 999999) == 0
    emergency_stop = _boolish(source_payload.get("emergency_stop_armed_verified"), False)
    further_blocked = _boolish(source_payload.get("further_live_real_submit_blocked"), False)
    patch_network_submit_attempted = _boolish(source_payload.get("patch_network_submit_attempted"), False)
    patch_exchange_submit_performed = _boolish(source_payload.get("patch_exchange_submit_performed"), False)
    add_exchange_approved = _boolish(source_payload.get("approved_for_additional_exchange_submit"), False)

    if not source_30x_verified:
        reasons.append("SOURCE_30X_REQUEST_NOT_VERIFIED")
    if not mismatch_zero:
        reasons.append("SOURCE_30Y_MISMATCH_NOT_ZERO")
    if not emergency_stop:
        reasons.append("SOURCE_30Y_EMERGENCY_STOP_NOT_ARMED")
    if not further_blocked:
        reasons.append("SOURCE_30Y_FURTHER_LIVE_REAL_NOT_BLOCKED")
    if patch_network_submit_attempted:
        reasons.append("SOURCE_30Y_PATCH_NETWORK_SUBMIT_ATTEMPTED")
    if patch_exchange_submit_performed:
        reasons.append("SOURCE_30Y_PATCH_EXCHANGE_SUBMIT_PERFORMED")
    if add_exchange_approved:
        reasons.append("SOURCE_30Y_APPROVED_ADDITIONAL_EXCHANGE_SUBMIT")

    exchange_order_id = _str_or_none(_nested_get(source_payload, [("execution_evidence", "exchange_order_id"), ("execution_evidence_snapshot", "exchange_order_id")]))
    symbol = _str_or_none(_nested_get(source_payload, [("execution_evidence", "symbol"), ("source_30x", "request_symbol"), ("submit_request_snapshot", "symbol")]))
    side = _str_or_none(_nested_get(source_payload, [("execution_evidence", "side"), ("source_30x", "request_side"), ("submit_request_snapshot", "side")]))
    filled_qty = _float(_nested_get(source_payload, [("execution_evidence", "filled_quantity"), ("reconciliation", "ledger_filled_quantity")]), 0.0)
    avg_fill_price = _float(_nested_get(source_payload, [("execution_evidence", "avg_fill_price")]), 0.0)
    fill_notional = _float(_nested_get(source_payload, [("execution_evidence", "fill_notional_usd"), ("reconciliation", "ledger_notional_usd")]), 0.0)
    ledger_notional = _float(_nested_get(source_payload, [("reconciliation", "ledger_notional_usd"), ("execution_evidence", "fill_notional_usd")]), 0.0)
    fee_amount = _nested_get(source_payload, [("execution_evidence", "fee_amount"), ("execution_evidence_snapshot", "fee_amount")], None)
    fee_asset = _str_or_none(_nested_get(source_payload, [("execution_evidence", "fee_asset"), ("execution_evidence_snapshot", "fee_asset")], None))
    fee_amount_float = None if fee_amount is None else _float(fee_amount, 0.0)

    if not exchange_order_id:
        reasons.append("EXCHANGE_ORDER_ID_MISSING")
    if filled_qty <= 0:
        reasons.append("FILLED_QUANTITY_NOT_POSITIVE")
    if avg_fill_price <= 0:
        reasons.append("AVG_FILL_PRICE_NOT_POSITIVE")
    if fill_notional <= 0 and ledger_notional <= 0:
        reasons.append("NOTIONAL_NOT_POSITIVE")

    return Source30YStatus(
        ok=len(reasons) == 0,
        source_report_path=str(source_report_path) if source_report_path is not None else None,
        source_contract_version=contract_version,
        source_decision=decision,
        source_ready=source_ready,
        source_30x_submit_request_verified=source_30x_verified,
        source_mismatch_zero_verified=mismatch_zero,
        source_emergency_stop_armed_verified=emergency_stop,
        source_further_live_real_submit_blocked=further_blocked,
        source_patch_network_submit_attempted=patch_network_submit_attempted,
        source_patch_exchange_submit_performed=patch_exchange_submit_performed,
        source_additional_exchange_submit_approved=add_exchange_approved,
        exchange_order_id=exchange_order_id,
        symbol=symbol,
        side=side,
        filled_quantity=filled_qty,
        avg_fill_price=avg_fill_price,
        fill_notional_usd=fill_notional if fill_notional > 0 else ledger_notional,
        ledger_notional_usd=ledger_notional,
        fee_amount_from_source=fee_amount_float,
        fee_asset_from_source=fee_asset,
        reason_codes=reasons,
    )


def evaluate_risk_metrics(
    source_status: Source30YStatus,
    *,
    fee_amount: float | None = None,
    fee_asset: str | None = None,
    review_mark_price: float | None = None,
    reference_price: float | None = None,
    max_abs_slippage_pct_allowed: float = 2.5,
    max_abs_unrealized_pnl_pct_allowed: float = 5.0,
) -> RiskMetricsStatus:
    reasons: list[str] = []
    fee = source_status.fee_amount_from_source if fee_amount is None else fee_amount
    fee_asset_final = source_status.fee_asset_from_source if fee_asset is None else fee_asset
    qty = source_status.filled_quantity
    avg = source_status.avg_fill_price
    notional = source_status.fill_notional_usd if source_status.fill_notional_usd > 0 else qty * avg
    mark = avg if review_mark_price is None else _float(review_mark_price, avg)
    ref = avg if reference_price is None else _float(reference_price, avg)
    side = (source_status.side or "BUY").upper()

    if not source_status.ok:
        reasons.append("SOURCE_30Y_NOT_OK")
    if fee is None:
        reasons.append("FEE_AMOUNT_REQUIRED")
        fee = 0.0
    if fee_asset_final is None:
        reasons.append("FEE_ASSET_REQUIRED")
    if qty <= 0:
        reasons.append("FILLED_QUANTITY_NOT_POSITIVE")
    if avg <= 0:
        reasons.append("AVG_FILL_PRICE_NOT_POSITIVE")
    if mark <= 0:
        reasons.append("REVIEW_MARK_PRICE_NOT_POSITIVE")
    if ref <= 0:
        reasons.append("REFERENCE_PRICE_NOT_POSITIVE")
    if notional <= 0:
        reasons.append("FILL_NOTIONAL_NOT_POSITIVE")

    if side == "SELL":
        unrealized_pnl = (avg - mark) * qty
        slippage = (avg - ref) * qty
    else:
        unrealized_pnl = (mark - avg) * qty
        slippage = (avg - ref) * qty
    denominator = max(notional, 1e-12)
    unrealized_pnl_pct = (unrealized_pnl / denominator) * 100.0
    slippage_pct = ((avg - ref) / max(ref, 1e-12)) * 100.0
    fee_ratio = (_float(fee, 0.0) / max(qty, 1e-12)) if (fee_asset_final or "").upper() in {"ETH", "BTC", "BNB"} else (_float(fee, 0.0) / denominator)

    if abs(slippage_pct) > max_abs_slippage_pct_allowed:
        reasons.append("SLIPPAGE_LIMIT_EXCEEDED")
    if abs(unrealized_pnl_pct) > max_abs_unrealized_pnl_pct_allowed:
        reasons.append("UNREALIZED_PNL_LIMIT_EXCEEDED")

    return RiskMetricsStatus(
        ok=len(reasons) == 0,
        pnl_evidence_verified="UNREALIZED_PNL_LIMIT_EXCEEDED" not in reasons and "REVIEW_MARK_PRICE_NOT_POSITIVE" not in reasons,
        fee_evidence_verified="FEE_AMOUNT_REQUIRED" not in reasons and "FEE_ASSET_REQUIRED" not in reasons,
        slippage_evidence_verified="SLIPPAGE_LIMIT_EXCEEDED" not in reasons and "REFERENCE_PRICE_NOT_POSITIVE" not in reasons,
        mark_price_for_review=round(mark, 12),
        reference_price=round(ref, 12),
        filled_quantity=round(qty, 12),
        avg_fill_price=round(avg, 12),
        fill_notional_usd=round(notional, 12),
        fee_amount=round(_float(fee, 0.0), 12),
        fee_asset=fee_asset_final,
        side=side,
        unrealized_pnl_usd=round(unrealized_pnl, 12),
        unrealized_pnl_pct=round(unrealized_pnl_pct, 12),
        slippage_usd=round(slippage, 12),
        slippage_pct=round(slippage_pct, 12),
        fee_notional_ratio=round(fee_ratio, 12),
        max_abs_slippage_pct_allowed=max_abs_slippage_pct_allowed,
        max_abs_unrealized_pnl_pct_allowed=max_abs_unrealized_pnl_pct_allowed,
        reason_codes=reasons,
    )


def evaluate_continuity(
    *,
    source_status: Source30YStatus,
    emergency_stop_armed: bool,
    kill_switch_armed: bool = True,
    additional_live_order_count: int = 0,
    additional_network_submit_count: int = 0,
    additional_exchange_submit_count: int = 0,
) -> ContinuityStatus:
    reasons: list[str] = []
    if not source_status.source_emergency_stop_armed_verified:
        reasons.append("SOURCE_EMERGENCY_STOP_NOT_ARMED")
    if not emergency_stop_armed:
        reasons.append("EMERGENCY_STOP_CONTINUITY_NOT_ARMED")
    if not kill_switch_armed:
        reasons.append("KILL_SWITCH_CONTINUITY_NOT_ARMED")
    if additional_live_order_count != 0:
        reasons.append("ADDITIONAL_LIVE_ORDER_DETECTED")
    if additional_network_submit_count != 0:
        reasons.append("ADDITIONAL_NETWORK_SUBMIT_DETECTED")
    if additional_exchange_submit_count != 0:
        reasons.append("ADDITIONAL_EXCHANGE_SUBMIT_DETECTED")

    return ContinuityStatus(
        ok=len(reasons) == 0,
        emergency_stop_continuity_verified=source_status.source_emergency_stop_armed_verified and emergency_stop_armed,
        kill_switch_continuity_verified=kill_switch_armed,
        no_additional_live_order_verified=additional_live_order_count == 0,
        no_additional_network_submit_verified=additional_network_submit_count == 0,
        no_additional_exchange_submit_verified=additional_exchange_submit_count == 0,
        emergency_stop_armed=emergency_stop_armed,
        kill_switch_armed=kill_switch_armed,
        additional_live_order_count=additional_live_order_count,
        additional_network_submit_count=additional_network_submit_count,
        additional_exchange_submit_count=additional_exchange_submit_count,
        reason_codes=reasons,
    )


def build_post_live_micro_canary_risk_review_snapshot(
    source_payload: Mapping[str, Any],
    *,
    source_report_path: str | os.PathLike[str] | None = None,
    fee_amount: float | None = None,
    fee_asset: str | None = None,
    review_mark_price: float | None = None,
    reference_price: float | None = None,
    emergency_stop_armed: bool = False,
    kill_switch_armed: bool = True,
    additional_live_order_count: int = 0,
    additional_network_submit_count: int = 0,
    additional_exchange_submit_count: int = 0,
    max_abs_slippage_pct_allowed: float = 2.5,
    max_abs_unrealized_pnl_pct_allowed: float = 5.0,
    operator_notes: str | None = None,
) -> dict[str, Any]:
    source_status = evaluate_source_30y_h1_reconciliation(source_payload, source_report_path=source_report_path)
    metrics = evaluate_risk_metrics(
        source_status,
        fee_amount=fee_amount,
        fee_asset=fee_asset,
        review_mark_price=review_mark_price,
        reference_price=reference_price,
        max_abs_slippage_pct_allowed=max_abs_slippage_pct_allowed,
        max_abs_unrealized_pnl_pct_allowed=max_abs_unrealized_pnl_pct_allowed,
    )
    continuity = evaluate_continuity(
        source_status=source_status,
        emergency_stop_armed=emergency_stop_armed,
        kill_switch_armed=kill_switch_armed,
        additional_live_order_count=additional_live_order_count,
        additional_network_submit_count=additional_network_submit_count,
        additional_exchange_submit_count=additional_exchange_submit_count,
    )
    reasons = list(dict.fromkeys([*source_status.reason_codes, *metrics.reason_codes, *continuity.reason_codes]))

    if not source_status.ok:
        decision = SOURCE_REQUIRED_DECISION
    elif not metrics.fee_evidence_verified:
        decision = FEE_EVIDENCE_REQUIRED_DECISION
    elif any(code in reasons for code in {"ADDITIONAL_LIVE_ORDER_DETECTED", "ADDITIONAL_NETWORK_SUBMIT_DETECTED", "ADDITIONAL_EXCHANGE_SUBMIT_DETECTED"}):
        decision = ADDITIONAL_ORDER_BLOCK_DECISION
    elif not continuity.emergency_stop_continuity_verified or not continuity.kill_switch_continuity_verified:
        decision = EMERGENCY_STOP_REQUIRED_DECISION
    elif metrics.ok and continuity.ok:
        decision = READY_DECISION
    else:
        decision = NOT_READY_DECISION

    approved = decision == READY_DECISION
    snapshot = PostLiveMicroCanaryRiskReviewSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=source_status.source_contract_version or "UNKNOWN",
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_post_live_micro_canary_risk_review=approved,
        approved_for_live_real_continuation=False,
        approved_for_additional_live_order=False,
        source_30y_h1_reconciliation_verified=source_status.ok,
        real_fill_risk_review_verified=approved,
        pnl_evidence_verified=metrics.pnl_evidence_verified,
        fee_evidence_verified=metrics.fee_evidence_verified,
        slippage_evidence_verified=metrics.slippage_evidence_verified,
        emergency_stop_continuity_verified=continuity.emergency_stop_continuity_verified,
        no_additional_live_order_verified=continuity.no_additional_live_order_verified,
        mismatch_zero_continuity_verified=source_status.source_mismatch_zero_verified,
        patch_network_submit_attempted=False,
        patch_exchange_submit_performed=False,
        patch_live_real_order_performed=False,
        additional_live_order_count=continuity.additional_live_order_count,
        additional_network_submit_count=continuity.additional_network_submit_count,
        additional_exchange_submit_count=continuity.additional_exchange_submit_count,
        exchange_order_id=source_status.exchange_order_id,
        symbol=source_status.symbol,
        side=source_status.side,
        filled_quantity=metrics.filled_quantity,
        avg_fill_price=metrics.avg_fill_price,
        fill_notional_usd=metrics.fill_notional_usd,
        fee_amount=metrics.fee_amount,
        fee_asset=metrics.fee_asset,
        mark_price_for_review=metrics.mark_price_for_review,
        reference_price=metrics.reference_price,
        unrealized_pnl_usd=metrics.unrealized_pnl_usd,
        unrealized_pnl_pct=metrics.unrealized_pnl_pct,
        slippage_usd=metrics.slippage_usd,
        slippage_pct=metrics.slippage_pct,
        fee_notional_ratio=metrics.fee_notional_ratio,
        reason_codes=reasons,
        source_30y=source_status.to_dict(),
        risk_metrics=metrics.to_dict(),
        continuity=continuity.to_dict(),
        source_30y_snapshot=dict(source_payload),
        operator_notes=operator_notes,
    )
    return snapshot.to_dict()


def build_from_latest_30y_h1_reconciliation(
    reports_dir: str | os.PathLike[str],
    *,
    fee_amount: float | None = None,
    fee_asset: str | None = None,
    review_mark_price: float | None = None,
    reference_price: float | None = None,
    emergency_stop_armed: bool = False,
    kill_switch_armed: bool = True,
    additional_live_order_count: int = 0,
    additional_network_submit_count: int = 0,
    additional_exchange_submit_count: int = 0,
    max_abs_slippage_pct_allowed: float = 2.5,
    max_abs_unrealized_pnl_pct_allowed: float = 5.0,
    operator_notes: str | None = None,
) -> dict[str, Any]:
    source_path, source_payload = latest_valid_30y_h1_reconciliation_report(reports_dir)
    if source_path is None:
        return build_post_live_micro_canary_risk_review_snapshot(
            {},
            fee_amount=fee_amount,
            fee_asset=fee_asset,
            review_mark_price=review_mark_price,
            reference_price=reference_price,
            emergency_stop_armed=emergency_stop_armed,
            kill_switch_armed=kill_switch_armed,
            additional_live_order_count=additional_live_order_count,
            additional_network_submit_count=additional_network_submit_count,
            additional_exchange_submit_count=additional_exchange_submit_count,
            max_abs_slippage_pct_allowed=max_abs_slippage_pct_allowed,
            max_abs_unrealized_pnl_pct_allowed=max_abs_unrealized_pnl_pct_allowed,
            operator_notes=operator_notes,
        )
    return build_post_live_micro_canary_risk_review_snapshot(
        source_payload,
        source_report_path=source_path,
        fee_amount=fee_amount,
        fee_asset=fee_asset,
        review_mark_price=review_mark_price,
        reference_price=reference_price,
        emergency_stop_armed=emergency_stop_armed,
        kill_switch_armed=kill_switch_armed,
        additional_live_order_count=additional_live_order_count,
        additional_network_submit_count=additional_network_submit_count,
        additional_exchange_submit_count=additional_exchange_submit_count,
        max_abs_slippage_pct_allowed=max_abs_slippage_pct_allowed,
        max_abs_unrealized_pnl_pct_allowed=max_abs_unrealized_pnl_pct_allowed,
        operator_notes=operator_notes,
    )


def report_suffix_for_decision(decision: str) -> str:
    if decision == READY_DECISION:
        return "ready"
    if decision == SOURCE_REQUIRED_DECISION:
        return "30y_h1_required"
    if decision == FEE_EVIDENCE_REQUIRED_DECISION:
        return "fee_required"
    if decision == EMERGENCY_STOP_REQUIRED_DECISION:
        return "emergency_stop_required"
    if decision == ADDITIONAL_ORDER_BLOCK_DECISION:
        return "additional_order_detected"
    return "not_ready"


def markdown_summary(payload: Mapping[str, Any]) -> str:
    lines = [
        f"# {CONTRACT_VERSION} Post Live Micro-Canary Risk Review",
        "",
        f"- Decision: `{payload.get('decision')}`",
        f"- Source contract: `{payload.get('source_contract_version')}`",
        f"- Exchange order ID: `{payload.get('exchange_order_id')}`",
        f"- Symbol: `{payload.get('symbol')}`",
        f"- Side: `{payload.get('side')}`",
        f"- Filled quantity: `{payload.get('filled_quantity')}`",
        f"- Average fill price: `{payload.get('avg_fill_price')}`",
        f"- Fill notional USD: `{payload.get('fill_notional_usd')}`",
        f"- Fee: `{payload.get('fee_amount')} {payload.get('fee_asset')}`",
        f"- Unrealized PnL USD: `{payload.get('unrealized_pnl_usd')}`",
        f"- Unrealized PnL pct: `{payload.get('unrealized_pnl_pct')}`",
        f"- Slippage USD: `{payload.get('slippage_usd')}`",
        f"- Slippage pct: `{payload.get('slippage_pct')}`",
        f"- Emergency stop continuity: `{payload.get('emergency_stop_continuity_verified')}`",
        f"- Additional live order count: `{payload.get('additional_live_order_count')}`",
        f"- Patch network submit attempted: `{payload.get('patch_network_submit_attempted')}`",
        f"- Approved for additional live order: `{payload.get('approved_for_additional_live_order')}`",
        "",
        "## Reason codes",
    ]
    reasons = payload.get("reason_codes") if isinstance(payload.get("reason_codes"), list) else []
    if reasons:
        lines.extend(f"- `{reason}`" for reason in reasons)
    else:
        lines.append("- `NONE`")
    return "\n".join(lines) + "\n"


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str]) -> tuple[Path, Path]:
    base = Path(reports_dir)
    suffix = report_suffix_for_decision(str(payload.get("decision")))
    stem = f"{REPORT_PREFIX}_{utc_stamp()}_{suffix}"
    json_path = base / f"{stem}.json"
    md_path = base / f"{stem}.md"
    write_json_atomic(json_path, payload)
    write_json_atomic(md_path, markdown_summary(payload))
    return json_path, md_path
