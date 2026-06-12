from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Final

TRAINING_CANDLE_BUDGET_VERSION: Final[str] = "4B.4.3.6.6.27D"
TRAINING_INTERVAL_AWARE_BUDGET: Final[bool] = True
TRAINING_HISTORICAL_RANGE_ACCURACY_HARDENING: Final[bool] = True

_INTERVAL_RE = re.compile(r"^(?P<count>[1-9][0-9]*)(?P<unit>[smhdwM])$")
_SUPPORTED_FIXED_INTERVALS: Final[frozenset[str]] = frozenset({
    "1s", "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w",
})
_MILLISECONDS_PER_UNIT: Final[dict[str, int]] = {
    "s": 1_000,
    "m": 60_000,
    "h": 60 * 60_000,
    "d": 24 * 60 * 60_000,
    "w": 7 * 24 * 60 * 60_000,
}


class TrainingCandleBudgetError(ValueError):
    """Raised when a historical training range cannot be represented safely."""


@dataclass(frozen=True, slots=True)
class TrainingCandleBudget:
    contract_version: str
    interval: str
    interval_milliseconds: int
    requested_days: int
    candles_per_day: float
    requested_candles: int
    range_milliseconds: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def interval_to_milliseconds(interval: str) -> int:
    normalized = str(interval or "").strip()
    match = _INTERVAL_RE.fullmatch(normalized)
    if match is None:
        raise TrainingCandleBudgetError(f"TRAINING_INTERVAL_UNSUPPORTED:{normalized or '<empty>'}")
    count = int(match.group("count"))
    unit = match.group("unit")
    if unit == "M":
        raise TrainingCandleBudgetError("TRAINING_INTERVAL_MONTH_NOT_SUPPORTED")
    if normalized not in _SUPPORTED_FIXED_INTERVALS:
        raise TrainingCandleBudgetError(f"TRAINING_INTERVAL_UNSUPPORTED:{normalized}")
    return count * _MILLISECONDS_PER_UNIT[unit]


def build_training_candle_budget(interval: str, days: int) -> TrainingCandleBudget:
    requested_days = int(days)
    if requested_days <= 0:
        raise TrainingCandleBudgetError("TRAINING_DAYS_MUST_BE_POSITIVE")
    interval_ms = interval_to_milliseconds(interval)
    range_ms = requested_days * 24 * 60 * 60_000
    requested_candles, remainder = divmod(range_ms, interval_ms)
    if remainder:
        raise TrainingCandleBudgetError("TRAINING_RANGE_NOT_DIVISIBLE_BY_INTERVAL")
    if requested_candles <= 0:
        raise TrainingCandleBudgetError("TRAINING_CANDLE_BUDGET_EMPTY")
    return TrainingCandleBudget(
        contract_version=TRAINING_CANDLE_BUDGET_VERSION,
        interval=str(interval).strip(),
        interval_milliseconds=interval_ms,
        requested_days=requested_days,
        candles_per_day=(24 * 60 * 60_000) / interval_ms,
        requested_candles=requested_candles,
        range_milliseconds=range_ms,
    )
