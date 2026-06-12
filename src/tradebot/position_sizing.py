from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any

POSITION_SIZING_CONTRACT_VERSION = "4B.4.3.6.6.27F"
SUPPORTED_SIZING_MODES = frozenset({"fixed_quote", "risk_percent_quote_balance"})
LEGACY_SIZING_MODE_ALIASES = {"risk_percent": "risk_percent_quote_balance"}


class PositionSizingError(ValueError):
    """Fail-closed quantity contract violation."""

    def __init__(self, reason_code: str, message: str | None = None) -> None:
        self.reason_code = reason_code
        super().__init__(message or reason_code)


def _decimal(value: object, *, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise PositionSizingError(f"SIZING_VALUE_INVALID:{field}") from error
    if not parsed.is_finite():
        raise PositionSizingError(f"SIZING_VALUE_INVALID:{field}")
    return parsed


def _float(value: Decimal) -> float:
    return float(value)


def _round_down_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        raise PositionSizingError("SIZING_SYMBOL_FILTERS_MISSING:step_size")
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def normalize_sizing_mode(value: object) -> str:
    raw = str(value or "").strip()
    canonical = LEGACY_SIZING_MODE_ALIASES.get(raw, raw)
    if canonical not in SUPPORTED_SIZING_MODES:
        raise PositionSizingError(f"SIZING_MODE_UNSUPPORTED:{raw or '<empty>'}")
    return canonical


@dataclass(frozen=True, slots=True)
class SizingSettingsSnapshot:
    contract_version: str
    sizing_mode: str
    legacy_sizing_mode_alias_used: bool
    order_notional_usd: float
    risk_percent_quote_balance: float
    quote_balance_reserve_usd: float
    max_quote_budget_usd: float
    min_notional_buffer_multiplier: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EntrySizingDecision:
    contract_version: str
    ok: bool
    reason_code: str
    sizing_mode: str
    legacy_sizing_mode_alias_used: bool
    free_quote_balance: float
    quote_balance_reserve_usd: float
    usable_quote_balance: float
    requested_quote_budget: float
    max_quote_budget_usd: float
    max_quote_budget_applied: bool
    quote_budget: float
    reference_price: float
    raw_quantity: float
    quantity: float
    step_size: float
    min_qty: float
    max_qty: float
    max_qty_applied: bool
    min_notional: float
    min_notional_buffer_multiplier: float
    required_min_notional: float
    order_notional: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_sizing_settings(settings: Any) -> SizingSettingsSnapshot:
    raw_mode = str(getattr(settings, "sizing_mode", "fixed_quote") or "")
    mode = normalize_sizing_mode(raw_mode)
    order_notional = _decimal(getattr(settings, "order_notional_usd", 0.0), field="order_notional_usd")
    risk_percent = _decimal(getattr(settings, "risk_percent_quote_balance", 0.0), field="risk_percent_quote_balance")
    reserve = _decimal(getattr(settings, "quote_balance_reserve_usd", 0.0), field="quote_balance_reserve_usd")
    max_budget = _decimal(getattr(settings, "max_quote_budget_usd", 0.0), field="max_quote_budget_usd")
    min_buffer = _decimal(getattr(settings, "min_notional_buffer_multiplier", 0.0), field="min_notional_buffer_multiplier")

    if mode == "fixed_quote" and order_notional <= 0:
        raise PositionSizingError("SIZING_FIXED_QUOTE_BUDGET_NON_POSITIVE")
    if mode == "risk_percent_quote_balance" and not (Decimal("0") < risk_percent <= Decimal("100")):
        raise PositionSizingError("SIZING_RISK_PERCENT_INVALID")
    if reserve < 0:
        raise PositionSizingError("SIZING_QUOTE_RESERVE_NEGATIVE")
    if max_budget < 0:
        raise PositionSizingError("SIZING_MAX_QUOTE_BUDGET_NEGATIVE")
    if min_buffer < 1:
        raise PositionSizingError("SIZING_MIN_NOTIONAL_BUFFER_INVALID")

    return SizingSettingsSnapshot(
        contract_version=POSITION_SIZING_CONTRACT_VERSION,
        sizing_mode=mode,
        legacy_sizing_mode_alias_used=raw_mode in LEGACY_SIZING_MODE_ALIASES,
        order_notional_usd=_float(order_notional),
        risk_percent_quote_balance=_float(risk_percent),
        quote_balance_reserve_usd=_float(reserve),
        max_quote_budget_usd=_float(max_budget),
        min_notional_buffer_multiplier=_float(min_buffer),
    )


def build_entry_sizing_decision(
    *,
    settings: Any,
    symbol_rules: Any,
    free_quote_balance: object,
    reference_price: object,
) -> EntrySizingDecision:
    """Build a deterministic, quote-balance-bounded BUY quantity or fail closed."""
    config = validate_sizing_settings(settings)
    free_quote = _decimal(free_quote_balance, field="free_quote_balance")
    price = _decimal(reference_price, field="reference_price")
    reserve = _decimal(config.quote_balance_reserve_usd, field="quote_balance_reserve_usd")
    max_budget = _decimal(config.max_quote_budget_usd, field="max_quote_budget_usd")
    min_buffer = _decimal(config.min_notional_buffer_multiplier, field="min_notional_buffer_multiplier")

    if free_quote <= 0:
        raise PositionSizingError("SIZING_QUOTE_BALANCE_NON_POSITIVE")
    if price <= 0:
        raise PositionSizingError("SIZING_REFERENCE_PRICE_NON_POSITIVE")
    usable_quote = free_quote - reserve
    if usable_quote <= 0:
        raise PositionSizingError("SIZING_USABLE_QUOTE_BALANCE_NON_POSITIVE")

    step_size = _decimal(getattr(symbol_rules, "step_size", 0.0), field="step_size")
    min_qty = _decimal(getattr(symbol_rules, "min_qty", 0.0), field="min_qty")
    max_qty = _decimal(getattr(symbol_rules, "max_qty", 0.0), field="max_qty")
    min_notional = _decimal(getattr(symbol_rules, "min_notional", 0.0), field="min_notional")
    if step_size <= 0:
        raise PositionSizingError("SIZING_SYMBOL_FILTERS_MISSING:step_size")
    if min_qty <= 0:
        raise PositionSizingError("SIZING_SYMBOL_FILTERS_MISSING:min_qty")
    if max_qty < 0:
        raise PositionSizingError("SIZING_SYMBOL_RULES_INVALID:max_qty")
    if max_qty > 0 and max_qty < min_qty:
        raise PositionSizingError("SIZING_SYMBOL_RULES_INVALID:max_qty")
    if min_notional <= 0:
        raise PositionSizingError("SIZING_SYMBOL_FILTERS_MISSING:min_notional")

    if config.sizing_mode == "fixed_quote":
        requested_budget = _decimal(config.order_notional_usd, field="order_notional_usd")
    else:
        risk_percent = _decimal(config.risk_percent_quote_balance, field="risk_percent_quote_balance")
        requested_budget = usable_quote * risk_percent / Decimal("100")

    quote_budget = min(requested_budget, usable_quote)
    max_budget_applied = max_budget > 0 and quote_budget > max_budget
    if max_budget_applied:
        quote_budget = max_budget
    if quote_budget <= 0:
        raise PositionSizingError("SIZING_QUOTE_BUDGET_NON_POSITIVE")

    required_min_notional = min_notional * min_buffer
    if quote_budget < required_min_notional:
        raise PositionSizingError("SIZING_QUOTE_BUDGET_BELOW_MIN_NOTIONAL")

    raw_qty = quote_budget / price
    qty = _round_down_to_step(raw_qty, step_size)
    max_qty_applied = max_qty > 0 and qty > max_qty
    if max_qty_applied:
        qty = _round_down_to_step(max_qty, step_size)
    if qty <= 0:
        raise PositionSizingError("SIZING_QUANTITY_ROUNDED_TO_ZERO")
    if qty < min_qty:
        raise PositionSizingError("SIZING_QUANTITY_BELOW_MIN_QTY")

    order_notional = qty * price
    if order_notional < required_min_notional:
        raise PositionSizingError("SIZING_ORDER_NOTIONAL_BELOW_BUFFERED_MIN_NOTIONAL")
    if order_notional > usable_quote:
        raise PositionSizingError("SIZING_QUOTE_BUDGET_EXCEEDS_AVAILABLE_BALANCE")
    if order_notional > quote_budget:
        raise PositionSizingError("SIZING_ORDER_NOTIONAL_EXCEEDS_QUOTE_BUDGET")

    return EntrySizingDecision(
        contract_version=POSITION_SIZING_CONTRACT_VERSION,
        ok=True,
        reason_code="SIZING_ENTRY_QUANTITY_VERIFIED",
        sizing_mode=config.sizing_mode,
        legacy_sizing_mode_alias_used=config.legacy_sizing_mode_alias_used,
        free_quote_balance=_float(free_quote),
        quote_balance_reserve_usd=_float(reserve),
        usable_quote_balance=_float(usable_quote),
        requested_quote_budget=_float(requested_budget),
        max_quote_budget_usd=_float(max_budget),
        max_quote_budget_applied=max_budget_applied,
        quote_budget=_float(quote_budget),
        reference_price=_float(price),
        raw_quantity=_float(raw_qty),
        quantity=_float(qty),
        step_size=_float(step_size),
        min_qty=_float(min_qty),
        max_qty=_float(max_qty),
        max_qty_applied=max_qty_applied,
        min_notional=_float(min_notional),
        min_notional_buffer_multiplier=_float(min_buffer),
        required_min_notional=_float(required_min_notional),
        order_notional=_float(order_notional),
    )
