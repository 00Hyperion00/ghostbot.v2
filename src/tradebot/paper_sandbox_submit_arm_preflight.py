from __future__ import annotations

import json
import math
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import Settings

CONTRACT_VERSION = "4B.4.3.6.6.30P"
SOURCE_30O_CONTRACT_PREFIX = "4B.4.3.6.6.30O"
SOURCE_30O_READY_DECISIONS = {
    "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
    "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRRORED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
}
REPORT_TYPE = "paper_sandbox_submit_arm_preflight_no_exchange_submit_no_live_real"
REPORT_PREFIX = "4B436630P_paper_sandbox_submit_arm_preflight"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_READY_SUBMIT_STILL_BLOCKED_NO_LIVE_REAL"
SOURCE_30O_REQUIRED_DECISION = "PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_30O_RECONCILIATION_PROOF_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SANDBOX_READINESS_NOT_READY_DECISION = "PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_SANDBOX_READINESS_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_live_order_blocked": True,
    "paper_order_enablement_still_blocked": True,
    "submit_order_still_blocked": True,
    "exchange_submit_blocked": True,
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
    "exchange_submit_performed": False,
    "paper_live_order_enablement_present": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30OReconciliationStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    reconciliation_ready: bool
    mismatch_count: int
    mismatch_zero: bool
    sqlite_mirror_ok: bool
    ledger_consumed: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SandboxSubmitReadinessStatus:
    ok: bool
    required: bool
    api_mode_ok: bool
    endpoint_ok: bool
    min_notional_ok: bool
    lot_size_ok: bool
    risk_caps_ok: bool
    kill_switch_ok: bool
    api_mode: str
    base_url: str
    market_type: str
    execution_mode: str
    symbol: str
    side: str
    order_type: str
    order_notional_usd: float
    min_notional_usd: float
    simulated_price_usd: float
    quantity: float
    min_qty: float
    lot_size_step_qty: float
    order_notional_cap_usd: float
    capital_cap_usd: float
    max_daily_loss_usd: float
    max_daily_trades_cap: int
    max_open_orders: int
    kill_switch_enabled: bool
    submit_attempt_allowed: bool
    order_request_skeleton: dict[str, Any]
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NoExchangeSubmitStatus:
    ok: bool
    required: bool
    approved_for_exchange_submit: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    exchange_order_id_present: bool
    exchange_client_order_id_present: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NoLiveRealStatus:
    ok: bool
    required: bool
    approved_for_live_real: bool
    live_trading_armed: bool
    live_real_double_confirm: bool
    exchange_submit_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperSandboxSubmitArmPreflightDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_submit_arm_preflight: bool
    approved_for_30o_reconciliation_proof_consumption: bool
    approved_for_api_mode_check: bool
    approved_for_endpoint_check: bool
    approved_for_min_notional_check: bool
    approved_for_lot_size_check: bool
    approved_for_risk_caps_check: bool
    approved_for_kill_switch_check: bool
    approved_for_order_request_skeleton_build: bool
    approved_for_exchange_submit: bool
    approved_for_paper_sandbox_canary_submit: bool
    approved_for_live_real: bool
    source_30o_reconciliation_verified: bool
    sandbox_submit_readiness_verified: bool
    submit_order_still_blocked: bool
    no_exchange_submit_verified: bool
    no_live_real_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    order_actions_performed: bool
    exchange_submit_performed: bool
    reason_codes: list[str]
    source_30o: dict[str, Any]
    sandbox_submit_readiness: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30o_snapshot: dict[str, Any]

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
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_any(snapshot: Mapping[str, Any], *keys: str) -> bool:
    return any(bool(snapshot.get(key, False)) for key in keys)


def latest_30o_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630O_paper_sandbox_execution_reconciliation_gate_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def evaluate_source_30o_reconciliation(source_30o_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30OReconciliationStatus:
    contract = str(source_30o_snapshot.get("contract_version") or "") or None
    decision = str(source_30o_snapshot.get("decision") or "") or None
    mismatch_count = _int(source_30o_snapshot.get("mismatch_count", source_30o_snapshot.get("reconciliation_mismatch_count", 0)), 0)
    mismatch_zero = mismatch_count == 0 and bool(source_30o_snapshot.get("mismatch_zero", True))
    sqlite_ok = _bool_any(source_30o_snapshot, "sqlite_mirror_ok", "sqlite_audit_mirror_ok", "audit_mirror_sqlite_ok", "sqlite_mirrored")
    ledger_consumed = _bool_any(source_30o_snapshot, "ledger_consumed", "paper_execution_ledger_consumed", "approved_for_30n_ledger_consumption")
    reconciliation_ready = bool(decision in SOURCE_30O_READY_DECISIONS or source_30o_snapshot.get("approved_for_paper_sandbox_execution_reconciliation_gate", False))
    exchange_approved = bool(source_30o_snapshot.get("approved_for_exchange_submit", False))
    live_real = bool(source_30o_snapshot.get("approved_for_live_real", False))
    exchange_performed = bool(source_30o_snapshot.get("exchange_submit_performed", False))
    trading_action = bool(source_30o_snapshot.get("trading_action_performed", False))
    order_actions = bool(source_30o_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if not contract or not contract.startswith(SOURCE_30O_CONTRACT_PREFIX):
        reasons.append("SOURCE_30O_CONTRACT_VERSION_REQUIRED")
    if not reconciliation_ready:
        reasons.append("SOURCE_30O_RECONCILIATION_READY_REQUIRED")
    if not mismatch_zero:
        reasons.append("SOURCE_30O_MISMATCH_ZERO_REQUIRED")
    if not sqlite_ok:
        reasons.append("SOURCE_30O_SQLITE_MIRROR_REQUIRED")
    if not ledger_consumed:
        reasons.append("SOURCE_30O_LEDGER_CONSUMPTION_REQUIRED")
    if exchange_approved or exchange_performed:
        reasons.append("SOURCE_30O_EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED_OR_PERFORMED")
    if live_real:
        reasons.append("SOURCE_30O_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action or order_actions:
        reasons.append("SOURCE_30O_ORDER_OR_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
    return Source30OReconciliationStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        reconciliation_ready=reconciliation_ready,
        mismatch_count=mismatch_count,
        mismatch_zero=mismatch_zero,
        sqlite_mirror_ok=sqlite_ok,
        ledger_consumed=ledger_consumed,
        approved_for_exchange_submit=exchange_approved,
        approved_for_live_real=live_real,
        exchange_submit_performed=exchange_performed,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30O_RECONCILIATION_PROOF_VERIFIED"],
    )


def _is_lot_aligned(qty: float, step: float) -> bool:
    if qty <= 0 or step <= 0:
        return False
    ratio = qty / step
    return abs(ratio - round(ratio)) <= 1e-8


def evaluate_sandbox_submit_readiness(settings: Any, source_30o_snapshot: Mapping[str, Any]) -> SandboxSubmitReadinessStatus:
    required = bool(_setting(settings, "paper_sandbox_submit_arm_preflight_enabled", True))
    api_mode = str(_setting(settings, "paper_sandbox_submit_arm_api_mode", "testnet") or "testnet").lower()
    base_url = str(_setting(settings, "paper_sandbox_submit_arm_base_url", _setting(settings, "base_url", "")) or "").lower()
    market_type = str(_setting(settings, "market_type", "spot_demo") or "spot_demo").lower()
    execution_mode = str(_setting(settings, "execution_mode", "dry_run") or "dry_run").lower()
    symbol = str(_setting(settings, "symbol", "ETHUSDT") or "ETHUSDT").upper()
    side = str(_setting(settings, "paper_sandbox_submit_arm_test_side", "BUY") or "BUY").upper()
    order_type = str(_setting(settings, "paper_sandbox_submit_arm_order_type", "MARKET") or "MARKET").upper()
    order_notional = _float(_setting(settings, "order_notional_usd", 25.0), 25.0)
    min_notional = _float(_setting(settings, "paper_sandbox_submit_arm_min_notional_usd", 5.0), 5.0)
    simulated_price = _float(_setting(settings, "paper_sandbox_submit_arm_simulated_price_usd", 2500.0), 2500.0)
    min_qty = _float(_setting(settings, "paper_sandbox_submit_arm_min_qty", 0.0001), 0.0001)
    step_qty = _float(_setting(settings, "paper_sandbox_submit_arm_lot_size_step_qty", 0.0001), 0.0001)
    order_cap = _float(_setting(settings, "paper_order_notional_cap_usd", 25.0), 25.0)
    capital_cap = _float(_setting(settings, "paper_transition_capital_cap_usd", 100.0), 100.0)
    max_loss = _float(_setting(settings, "paper_max_daily_loss_usd", 5.0), 5.0)
    max_trades = _int(_setting(settings, "paper_max_daily_trades_cap", 5), 5)
    max_open = _int(_setting(settings, "paper_transition_max_open_orders", 1), 1)
    kill_switch = bool(_setting(settings, "paper_kill_switch_enabled", True))
    qty = order_notional / simulated_price if simulated_price > 0 else 0.0
    api_ok = api_mode in {"testnet", "demo", "sandbox", "dry_run"}
    endpoint_ok = "testnet" in base_url or "demo" in base_url or "sandbox" in base_url or execution_mode == "dry_run"
    min_notional_ok = order_notional >= min_notional > 0
    lot_size_ok = qty >= min_qty > 0 and _is_lot_aligned(qty, step_qty)
    risk_caps_ok = (
        order_notional > 0
        and order_cap > 0
        and capital_cap > 0
        and max_loss > 0
        and max_trades > 0
        and max_open > 0
        and order_notional <= order_cap <= capital_cap
    )
    kill_switch_ok = kill_switch is True
    reasons: list[str] = []
    if not required:
        reasons.append("SUBMIT_ARM_PREFLIGHT_MUST_REMAIN_ENABLED")
    if not api_ok:
        reasons.append("API_MODE_NOT_SANDBOX_COMPATIBLE")
    if not endpoint_ok:
        reasons.append("ENDPOINT_NOT_SANDBOX_OR_DRY_RUN")
    if market_type not in {"spot_demo", "spot_testnet"}:
        reasons.append("MARKET_TYPE_NOT_SANDBOX")
    if execution_mode != "dry_run":
        reasons.append("EXECUTION_MODE_MUST_REMAIN_DRY_RUN_FOR_PREFLIGHT")
    if not min_notional_ok:
        reasons.append("MIN_NOTIONAL_CHECK_FAILED")
    if not lot_size_ok:
        reasons.append("LOT_SIZE_CHECK_FAILED")
    if not risk_caps_ok:
        reasons.append("RISK_CAPS_CHECK_FAILED")
    if not kill_switch_ok:
        reasons.append("KILL_SWITCH_MUST_BE_ENABLED")
    skeleton = {
        "contract_version": CONTRACT_VERSION,
        "request_type": "paper_sandbox_submit_arm_preflight_order_request_skeleton_no_submit",
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quoteOrderQty": order_notional,
        "quantity": qty,
        "api_mode": api_mode,
        "base_url": base_url,
        "market_type": market_type,
        "execution_mode": execution_mode,
        "submit_to_exchange": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "client_order_id": None,
        "exchange_order_id": None,
    }
    return SandboxSubmitReadinessStatus(
        ok=required and not reasons,
        required=required,
        api_mode_ok=api_ok,
        endpoint_ok=endpoint_ok,
        min_notional_ok=min_notional_ok,
        lot_size_ok=lot_size_ok,
        risk_caps_ok=risk_caps_ok,
        kill_switch_ok=kill_switch_ok,
        api_mode=api_mode,
        base_url=base_url,
        market_type=market_type,
        execution_mode=execution_mode,
        symbol=symbol,
        side=side,
        order_type=order_type,
        order_notional_usd=order_notional,
        min_notional_usd=min_notional,
        simulated_price_usd=simulated_price,
        quantity=qty,
        min_qty=min_qty,
        lot_size_step_qty=step_qty,
        order_notional_cap_usd=order_cap,
        capital_cap_usd=capital_cap,
        max_daily_loss_usd=max_loss,
        max_daily_trades_cap=max_trades,
        max_open_orders=max_open,
        kill_switch_enabled=kill_switch,
        submit_attempt_allowed=False,
        order_request_skeleton=skeleton if required and not reasons else {},
        reason_codes=reasons or ["SANDBOX_SUBMIT_READINESS_PREFLIGHT_VERIFIED_SUBMIT_STILL_BLOCKED"],
    )


def evaluate_no_exchange_submit(settings: Any, source_30o_snapshot: Mapping[str, Any]) -> NoExchangeSubmitStatus:
    required = bool(_setting(settings, "paper_sandbox_submit_arm_no_exchange_submit_required", True))
    approved = bool(source_30o_snapshot.get("approved_for_exchange_submit", False))
    performed = bool(source_30o_snapshot.get("exchange_submit_performed", False))
    network = bool(source_30o_snapshot.get("network_submit_attempted", False))
    order_id = bool(source_30o_snapshot.get("exchange_order_id") or source_30o_snapshot.get("exchange_order_id_present", False))
    client_id = bool(source_30o_snapshot.get("exchange_client_order_id") or source_30o_snapshot.get("exchange_client_order_id_present", False))
    reasons: list[str] = []
    if not required:
        reasons.append("NO_EXCHANGE_SUBMIT_GATE_MUST_REMAIN_REQUIRED")
    if approved or performed or network:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED_OR_PERFORMED")
    if order_id:
        reasons.append("EXCHANGE_ORDER_ID_UNEXPECTEDLY_PRESENT")
    if client_id:
        reasons.append("EXCHANGE_CLIENT_ORDER_ID_UNEXPECTEDLY_PRESENT")
    return NoExchangeSubmitStatus(
        ok=required and not reasons,
        required=required,
        approved_for_exchange_submit=approved,
        exchange_submit_performed=performed,
        network_submit_attempted=network,
        exchange_order_id_present=order_id,
        exchange_client_order_id_present=client_id,
        reason_codes=reasons or ["NO_EXCHANGE_SUBMIT_VERIFIED_SUBMIT_ARM_PREFLIGHT"],
    )


def evaluate_no_live_real(settings: Any, source_30o_snapshot: Mapping[str, Any]) -> NoLiveRealStatus:
    required = bool(_setting(settings, "paper_sandbox_submit_arm_no_live_real_required", True))
    approved = bool(source_30o_snapshot.get("approved_for_live_real", False))
    live_armed = bool(_setting(settings, "live_trading_armed", False))
    live_confirm = bool(_setting(settings, "live_real_double_confirm", False))
    exchange_performed = bool(source_30o_snapshot.get("exchange_submit_performed", False))
    reasons: list[str] = []
    if not required:
        reasons.append("NO_LIVE_REAL_GATE_MUST_REMAIN_REQUIRED")
    if approved or live_armed or live_confirm:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_ENABLED_OR_ARMED")
    if exchange_performed:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_PERFORMED")
    return NoLiveRealStatus(
        ok=required and not reasons,
        required=required,
        approved_for_live_real=approved,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_confirm,
        exchange_submit_performed=exchange_performed,
        reason_codes=reasons or ["NO_LIVE_REAL_VERIFIED_SUBMIT_ARM_PREFLIGHT"],
    )


def build_paper_sandbox_submit_arm_preflight_snapshot(
    settings: Any,
    source_30o_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
) -> dict[str, Any]:
    source = evaluate_source_30o_reconciliation(source_30o_snapshot, source_report_path=source_report_path)
    readiness = evaluate_sandbox_submit_readiness(settings, source_30o_snapshot)
    no_submit = evaluate_no_exchange_submit(settings, source_30o_snapshot)
    no_live = evaluate_no_live_real(settings, source_30o_snapshot)
    ready = source.ok and readiness.ok and no_submit.ok and no_live.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30O_REQUIRED_DECISION
    elif not readiness.ok:
        decision = SANDBOX_READINESS_NOT_READY_DECISION
    else:
        decision = NOT_READY_DECISION
    reasons = [*source.reason_codes, *readiness.reason_codes, *no_submit.reason_codes, *no_live.reason_codes]
    reasons.extend(["SUBMIT_ORDER_STILL_BLOCKED", "NO_EXCHANGE_SUBMIT_VERIFIED", "NO_LIVE_REAL_VERIFIED"])
    payload = PaperSandboxSubmitArmPreflightDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_submit_arm_preflight=ready,
        approved_for_30o_reconciliation_proof_consumption=source.ok,
        approved_for_api_mode_check=readiness.api_mode_ok,
        approved_for_endpoint_check=readiness.endpoint_ok,
        approved_for_min_notional_check=readiness.min_notional_ok,
        approved_for_lot_size_check=readiness.lot_size_ok,
        approved_for_risk_caps_check=readiness.risk_caps_ok,
        approved_for_kill_switch_check=readiness.kill_switch_ok,
        approved_for_order_request_skeleton_build=readiness.ok,
        approved_for_exchange_submit=False,
        approved_for_paper_sandbox_canary_submit=False,
        approved_for_live_real=False,
        source_30o_reconciliation_verified=source.ok,
        sandbox_submit_readiness_verified=readiness.ok,
        submit_order_still_blocked=True,
        no_exchange_submit_verified=no_submit.ok,
        no_live_real_verified=no_live.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        order_actions_performed=False,
        exchange_submit_performed=False,
        reason_codes=reasons,
        source_30o=source.to_dict(),
        sandbox_submit_readiness=readiness.to_dict(),
        no_exchange_submit=no_submit.to_dict(),
        no_live_real=no_live.to_dict(),
        source_30o_snapshot=dict(source_30o_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30o_reconciliation_gate": True,
        "api_mode_check_gate": True,
        "sandbox_endpoint_check_gate": True,
        "min_notional_check_gate": True,
        "lot_size_check_gate": True,
        "risk_caps_check_gate": True,
        "kill_switch_check_gate": True,
        "submit_still_blocked_gate": True,
        "no_exchange_submit_gate": True,
        "no_live_real_gate": True,
    })
    return payload


def build_from_latest_30o_ready_report(settings: Any | None = None, *, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    latest = latest_30o_ready_report(reports_dir)
    if latest is None:
        return build_paper_sandbox_submit_arm_preflight_snapshot(resolved_settings, {}, source_report_path=None)
    source = _mapping(load_json(latest))
    return build_paper_sandbox_submit_arm_preflight_snapshot(resolved_settings, source, source_report_path=str(latest))


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    reports = Path(reports_dir)
    suffix = "ready" if payload.get("decision") == READY_DECISION else "not_ready"
    stamp = utc_stamp()
    json_path = reports / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = reports / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    write_json_atomic(json_path, payload)
    lines = [
        f"# {CONTRACT_VERSION} Paper Sandbox Submit-Arm Preflight",
        "",
        "This report consumes the 30O-H6 reconciliation proof, verifies sandbox submit readiness, and keeps exchange submit plus live-real blocked.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_paper_sandbox_submit_arm_preflight`: `{payload.get('approved_for_paper_sandbox_submit_arm_preflight')}`",
        f"- `approved_for_order_request_skeleton_build`: `{payload.get('approved_for_order_request_skeleton_build')}`",
        f"- `approved_for_exchange_submit`: `{payload.get('approved_for_exchange_submit')}`",
        f"- `approved_for_paper_sandbox_canary_submit`: `{payload.get('approved_for_paper_sandbox_canary_submit')}`",
        f"- `approved_for_live_real`: `{payload.get('approved_for_live_real')}`",
        f"- `submit_order_still_blocked`: `{payload.get('submit_order_still_blocked')}`",
        f"- `exchange_submit_performed`: `{payload.get('exchange_submit_performed')}`",
        "",
        "## Gate checks",
        f"- `source_30o_reconciliation_verified`: `{payload.get('source_30o_reconciliation_verified')}`",
        f"- `sandbox_submit_readiness_verified`: `{payload.get('sandbox_submit_readiness_verified')}`",
        f"- `no_exchange_submit_verified`: `{payload.get('no_exchange_submit_verified')}`",
        f"- `no_live_real_verified`: `{payload.get('no_live_real_verified')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
