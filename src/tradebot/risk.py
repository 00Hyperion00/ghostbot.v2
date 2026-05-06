from __future__ import annotations

from .config import Settings
from .models import Position, RiskPlan


RISK_EVENT_PRIORITY = {
    'STOP_HIT': 1,
    'TAKE_PROFIT_HIT': 2,
    'PARTIAL_TP_HIT': 3,
    'BREAK_EVEN_ARMED': 4,
    'BREAK_EVEN_MOVED': 5,
    'TRAILING_ARMED': 6,
    'TRAILING_STOP_UPDATED': 7,
}


def build_risk_plan(position: Position, atr_value: float | None, settings: Settings) -> RiskPlan:
    entry = position.entry_price
    qty = position.qty
    if settings.sl_mode == 'atr' and atr_value:
        stop = entry - (atr_value * settings.atr_multiplier)
        risk_per_unit = max(entry - stop, 0.0)
    else:
        stop = entry * (1 - settings.fixed_stop_loss_pct / 100)
        risk_per_unit = entry - stop
    if settings.tp_mode == 'rr':
        take_profit = entry + (risk_per_unit * settings.risk_reward_ratio)
        planned_rr = settings.risk_reward_ratio
    else:
        take_profit = entry * (1 + settings.fixed_take_profit_pct / 100)
        planned_rr = (take_profit - entry) / risk_per_unit if risk_per_unit else None
    open_risk_quote = risk_per_unit * qty
    partial_tp_price = entry + (risk_per_unit * settings.partial_take_profit_rr)
    be_trigger = entry + (risk_per_unit * settings.break_even_trigger_r)
    be_stop = entry * (1 + settings.break_even_buffer_pct / 100)
    return RiskPlan(
        atr=atr_value,
        entry_price=entry,
        stop_loss=stop,
        take_profit=take_profit,
        open_risk_quote=open_risk_quote,
        planned_rr=planned_rr,
        break_even_trigger_price=be_trigger,
        break_even_stop_price=be_stop,
        trailing_enabled=settings.trailing_stop_enabled,
        partial_tp_price=partial_tp_price,
        partial_tp_close_pct=settings.partial_take_profit_close_pct,
        highest_mark_price=entry,
    )


def choose_risk_event(*events: tuple[str, float] | None) -> tuple[str, float] | None:
    active = [item for item in events if item is not None]
    if not active:
        return None
    active.sort(key=lambda item: RISK_EVENT_PRIORITY.get(item[0], 999))
    return active[0]
