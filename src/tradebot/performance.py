from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .utils import utc_ms

CONTRACT_VERSION = '4B.4.3.6.6.14'


@dataclass(slots=True)
class PerformanceConfig:
    enabled: bool = True
    window_size: int = 200
    breakeven_epsilon: float = 1e-9


def config_from_settings(settings: Any) -> PerformanceConfig:
    return PerformanceConfig(
        enabled=bool(getattr(settings, 'performance_analytics_enabled', True)),
        window_size=max(int(getattr(settings, 'performance_analytics_window_size', 200) or 200), 1),
        breakeven_epsilon=max(float(getattr(settings, 'performance_breakeven_epsilon', 1e-9) or 1e-9), 0.0),
    )


def new_entry_record(*, symbol: str, entry_price: float, qty: float, source: str, order_id: str | None, client_order_id: str | None, entry_at: int | None = None) -> dict[str, Any]:
    now = int(entry_at or utc_ms())
    return {
        'contract_version': CONTRACT_VERSION,
        'status': 'OPEN',
        'symbol': symbol,
        'entry_at': now,
        'entry_price': float(entry_price or 0.0),
        'qty': float(qty or 0.0),
        'remaining_qty': float(qty or 0.0),
        'entry_source': source,
        'order_id': order_id,
        'client_order_id': client_order_id,
        'partial_exit_count': 0,
        'partial_realized_pnl': 0.0,
        'last_exit_at': None,
        'last_exit_price': None,
    }


def update_open_trade_on_partial_exit(open_trade: dict[str, Any] | None, *, exit_price: float, exit_qty: float, pnl: float, remaining_qty: float, exit_at: int | None = None) -> dict[str, Any] | None:
    if not open_trade:
        return open_trade
    updated = dict(open_trade)
    updated['status'] = 'OPEN'
    updated['remaining_qty'] = float(remaining_qty or 0.0)
    updated['partial_exit_count'] = int(updated.get('partial_exit_count') or 0) + 1
    updated['partial_realized_pnl'] = float(updated.get('partial_realized_pnl') or 0.0) + float(pnl or 0.0)
    updated['last_exit_at'] = int(exit_at or utc_ms())
    updated['last_exit_price'] = float(exit_price or 0.0)
    return updated


def close_trade_record(open_trade: dict[str, Any] | None, *, symbol: str, entry_price: float, qty: float, exit_price: float, exit_qty: float, pnl: float, exit_source: str, fill_source: str, exit_at: int | None = None, epsilon: float = 1e-9) -> dict[str, Any]:
    now = int(exit_at or utc_ms())
    entry_at = int((open_trade or {}).get('entry_at') or now)
    entry_source = (open_trade or {}).get('entry_source')
    partial_realized = float((open_trade or {}).get('partial_realized_pnl') or 0.0)
    total_pnl = partial_realized + float(pnl or 0.0)
    notional = max(float(entry_price or 0.0) * max(float(qty or exit_qty or 0.0), 0.0), 0.0)
    pnl_pct = (total_pnl / notional * 100.0) if notional > 0 else None
    if total_pnl > epsilon:
        result = 'WIN'
    elif total_pnl < -epsilon:
        result = 'LOSS'
    else:
        result = 'BREAKEVEN'
    return {
        'contract_version': CONTRACT_VERSION,
        'status': 'CLOSED',
        'symbol': symbol,
        'entry_at': entry_at,
        'exit_at': now,
        'hold_time_sec': max(int((now - entry_at) / 1000), 0),
        'entry_price': float(entry_price or 0.0),
        'exit_price': float(exit_price or 0.0),
        'qty': float(qty or exit_qty or 0.0),
        'exit_qty': float(exit_qty or 0.0),
        'entry_source': entry_source,
        'exit_source': exit_source,
        'fill_source': fill_source,
        'realized_pnl': total_pnl,
        'realized_pnl_pct': pnl_pct,
        'result': result,
        'partial_exit_count': int((open_trade or {}).get('partial_exit_count') or 0),
        'partial_realized_pnl': partial_realized,
    }


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _round_optional(value: float | None, digits: int = 6) -> float | None:
    return round(float(value), digits) if value is not None else None


def summarize_performance(*, trades: list[dict[str, Any]] | None, open_trade: dict[str, Any] | None, config: PerformanceConfig, symbol: str | None = None, logs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    closed = list(trades or [])[-config.window_size:]
    pnl_values = [float(t.get('realized_pnl') or 0.0) for t in closed]
    hold_values = [float(t.get('hold_time_sec') or 0.0) for t in closed if t.get('hold_time_sec') is not None]
    wins = [v for v in pnl_values if v > config.breakeven_epsilon]
    losses = [v for v in pnl_values if v < -config.breakeven_epsilon]
    breakeven = len(pnl_values) - len(wins) - len(losses)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    total = len(pnl_values)
    win_rate = (len(wins) / total * 100.0) if total else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (None if gross_profit == 0 else float('inf'))
    log_counts = summarize_event_codes(logs or [])
    return {
        'contract_version': CONTRACT_VERSION,
        'enabled': bool(config.enabled),
        'symbol': symbol,
        'window_size': config.window_size,
        'closed_trade_count': total,
        'open_trade': summarize_open_trade(open_trade),
        'realized_pnl': _round_optional(sum(pnl_values), 6) or 0.0,
        'avg_realized_pnl': _round_optional(_avg(pnl_values), 6),
        'win_count': len(wins),
        'loss_count': len(losses),
        'breakeven_count': breakeven,
        'win_rate_pct': round(win_rate, 2),
        'gross_profit': _round_optional(gross_profit, 6) or 0.0,
        'gross_loss': _round_optional(gross_loss, 6) or 0.0,
        'profit_factor': None if profit_factor is None else (round(profit_factor, 6) if profit_factor != float('inf') else 'inf'),
        'avg_hold_time_sec': _round_optional(_avg(hold_values), 3),
        'max_win': _round_optional(max(wins), 6) if wins else None,
        'max_loss': _round_optional(min(losses), 6) if losses else None,
        'last_trade': closed[-1] if closed else None,
        'guard_counts': log_counts,
        'last_updated_at': utc_ms(),
    }


def summarize_open_trade(open_trade: dict[str, Any] | None) -> dict[str, Any]:
    if not open_trade:
        return {'present': False}
    entry_at = open_trade.get('entry_at')
    age = max(int((utc_ms() - int(entry_at)) / 1000), 0) if entry_at else None
    return {
        'present': True,
        'symbol': open_trade.get('symbol'),
        'entry_at': entry_at,
        'age_sec': age,
        'entry_price': open_trade.get('entry_price'),
        'qty': open_trade.get('qty'),
        'remaining_qty': open_trade.get('remaining_qty'),
        'entry_source': open_trade.get('entry_source'),
        'partial_exit_count': int(open_trade.get('partial_exit_count') or 0),
        'partial_realized_pnl': round(float(open_trade.get('partial_realized_pnl') or 0.0), 6),
    }


def summarize_event_codes(logs: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        'auto_trade_skip': 0,
        'auto_entry_blocked': 0,
        'auto_exit_blocked': 0,
        'risk_exit_triggered': 0,
        'order_canceled': 0,
    }
    code_map = {
        'AUTO_TRADE_SKIP': 'auto_trade_skip',
        'AUTO_ENTRY_BLOCKED': 'auto_entry_blocked',
        'AUTO_EXIT_BLOCKED': 'auto_exit_blocked',
        'RISK_EXIT_TRIGGERED': 'risk_exit_triggered',
        'ORDER_CANCELED': 'order_canceled',
    }
    for item in logs:
        key = code_map.get(str(item.get('code') or ''))
        if key:
            counts[key] += 1
    return counts


def append_trade(trades: list[dict[str, Any]] | None, trade: dict[str, Any], *, window_size: int) -> list[dict[str, Any]]:
    payload = list(trades or [])
    payload.append(trade)
    return payload[-max(int(window_size or 1), 1):]
