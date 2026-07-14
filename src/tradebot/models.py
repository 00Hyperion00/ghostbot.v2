from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from .enums import BotState


@dataclass(slots=True)
class Balance:
    free: float = 0.0
    locked: float = 0.0
    dust: float = 0.0

    @property
    def total(self) -> float:
        return self.free + self.locked


@dataclass(slots=True)
class SymbolRules:
    symbol: str
    base_asset: str
    quote_asset: str
    tick_size: float
    step_size: float
    min_qty: float
    max_qty: float
    min_notional: float
    price_precision: int | None = None
    quantity_precision: int | None = None


@dataclass(slots=True)
class Candle:
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    taker_buy_quote_volume: float | None = None
    closed: bool = True


@dataclass(slots=True)
class SignalDecision:
    signal: str = "HOLD"
    trend: str = "UNKNOWN"
    reason: str = "Henüz değerlendirme yok"
    provider: str = "technical"
    confidence: float | None = None
    last_evaluated_close_time: int | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PendingOrder:
    side: str
    price: float
    qty: float
    status: str = "NEW"
    order_id: str | None = None
    client_order_id: str | None = None
    source: str = "manual"
    submitted_at: int = 0
    reconcile_attempts: int = 0
    cancel_requested: bool = False
    partial_executed_qty: float = 0.0
    remaining_qty: float | None = None
    last_reconcile_at: int | None = None
    deferred: bool = False
    missing_count: int = 0
    cancel_requested_at: int | None = None
    last_live_status: str | None = None
    last_status_at: int | None = None
    last_fill_qty: float = 0.0
    last_fill_price: float | None = None
    last_reconcile_reason: str | None = None
    last_reconcile_error: str | None = None
    late_fill_detected: bool = False


@dataclass(slots=True)
class RiskPlan:
    atr: float | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    open_risk_quote: float | None = None
    planned_rr: float | None = None
    break_even_trigger_price: float | None = None
    break_even_stop_price: float | None = None
    trailing_enabled: bool = False
    partial_tp_price: float | None = None
    partial_tp_close_pct: float | None = None
    break_even_armed: bool = False
    break_even_moved: bool = False
    trailing_armed: bool = False
    trailing_stop: float | None = None
    highest_mark_price: float | None = None
    partial_tp_triggered: bool = False
    last_exit_reason: str | None = None
    last_evaluated_mark_price: float | None = None
    last_evaluated_at: int | None = None


@dataclass(slots=True)
class Position:
    qty: float
    entry_price: float
    source: str
    order_id: str | None = None
    client_order_id: str | None = None
    opened_at: int = 0
    risk_plan: RiskPlan | None = None


@dataclass(slots=True)
class SessionStats:
    day_key: str | None = None
    daily_realized_pnl: float = 0.0
    daily_trade_count: int = 0
    consecutive_losses: int = 0
    last_closed_pnl: float = 0.0


@dataclass(slots=True)
class ExitIntent:
    kind: str
    source: str
    trigger_price: float
    created_at: int


@dataclass(slots=True)
class RuntimeState:
    last_reconcile_result: str | None = None
    startup_hygiene_snapshot: dict | None = None
    startup_hygiene_repaired: bool = False
    startup_hygiene_reason_codes: list | None = None
    state: str = BotState.STOPPED.value
    ws_status: str = "DISCONNECTED"
    symbol: str = "ETHUSDT"
    last_signal: str = "HOLD"
    signal_reason: str = "Henüz değerlendirme yok"
    trend: str = "UNKNOWN"
    pending: PendingOrder | None = None
    position: Position | None = None
    balances: dict[str, Balance] = field(default_factory=dict)
    auto_debug: str = "-"
    auto_guard: str = "cooldown 5s"
    live_order_status: str = "-"
    last_preflight: str = "-"
    last_order_event: str = "Henüz emir yok"
    active_exit_intent: ExitIntent | None = None
    session: SessionStats = field(default_factory=SessionStats)
    safe_mode: bool = False
    safe_mode_until: int | None = None
    last_signal_key: str | None = None
    last_signal_provider: str | None = None
    last_signal_confidence: float | None = None
    last_signal_metrics: dict[str, Any] = field(default_factory=dict)
    last_evaluated_close_time: int | None = None
    safe_mode_source: str | None = None
    safe_mode_reason_code: str | None = None
    recovery_snapshot: dict[str, Any] | None = None
    startup_hygiene: dict[str, Any] | None = None
    model_quality_snapshot: dict[str, Any] | None = None
    performance_open_trade: dict[str, Any] | None = None
    performance_trades: list[dict[str, Any]] = field(default_factory=list)
    performance_snapshot: dict[str, Any] | None = None
    config_safety_snapshot: dict[str, Any] | None = None
    diagnostics_snapshot: dict[str, Any] | None = None
    reconciliation_snapshot: dict[str, Any] | None = None
    decision_audit_snapshot: dict[str, Any] | None = None
    entry_lock_until: int | None = None
    dust_snapshot: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def conv(v: Any) -> Any:
            if hasattr(v, '__dataclass_fields__'):
                return {k: conv(getattr(v, k)) for k in v.__dataclass_fields__}
            if isinstance(v, dict):
                return {k: conv(val) for k, val in v.items()}
            if isinstance(v, list):
                return [conv(i) for i in v]
            return v
        return conv(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "RuntimeState":
        payload = payload or {}
        state = cls()
        for key, value in payload.items():
            if key == 'balances':
                state.balances = {k: Balance(**v) for k, v in (value or {}).items()}
            elif key == 'pending' and value:
                state.pending = PendingOrder(**value)
            elif key == 'position' and value:
                rp = value.get('risk_plan')
                value = dict(value)
                value['risk_plan'] = RiskPlan(**{k: v for k, v in rp.items() if k in RiskPlan.__dataclass_fields__}) if rp else None
                state.position = Position(**value)
            elif key == 'session' and value:
                state.session = SessionStats(**value)
            elif key == 'active_exit_intent' and value:
                state.active_exit_intent = ExitIntent(**value)
            elif hasattr(state, key):
                setattr(state, key, value)
        return state


@dataclass(slots=True)
class LogEvent:
    ts: int
    level: str
    code: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

# >>> 4B436662F_H6_MODELS_FINAL
# 4B.4.3.6.6.62F-H6 RuntimeState slot compatibility.

from dataclasses import dataclass as _h6_dataclass
from typing import Any as _H6Any

try:
    _Phase62FH6OriginalRuntimeState = RuntimeState  # type: ignore[name-defined]
except NameError:
    @_h6_dataclass
    class RuntimeState:  # type: ignore[no-redef]
        state: str = "FLAT"
        ws_status: str = "DISCONNECTED"
        symbol: str = "ETHUSDT"
        pending: _H6Any = None
        position: _H6Any = None
        last_reconcile_result: str | None = None
        active_anomaly_code: str | None = None
        active_anomaly_message: str | None = None
        active_anomaly_details: _H6Any = None
        startup_hygiene_snapshot: _H6Any = None
else:
    class _Phase62FH6RuntimeState(_Phase62FH6OriginalRuntimeState):
        __slots__ = (
            "__dict__",
            "active_anomaly_code",
            "active_anomaly_message",
            "active_anomaly_details",
            "startup_hygiene_snapshot",
        )

        def __init__(self, *args: _H6Any, **kwargs: _H6Any) -> None:
            active_anomaly_code = kwargs.pop("active_anomaly_code", None)
            active_anomaly_message = kwargs.pop("active_anomaly_message", None)
            active_anomaly_details = kwargs.pop("active_anomaly_details", None)
            startup_hygiene_snapshot = kwargs.pop("startup_hygiene_snapshot", None)
            super().__init__(*args, **kwargs)
            self.active_anomaly_code = active_anomaly_code
            self.active_anomaly_message = active_anomaly_message
            self.active_anomaly_details = active_anomaly_details
            self.startup_hygiene_snapshot = startup_hygiene_snapshot

    RuntimeState = _Phase62FH6RuntimeState  # type: ignore[assignment,misc]
# <<< 4B436662F_H6_MODELS_FINAL
