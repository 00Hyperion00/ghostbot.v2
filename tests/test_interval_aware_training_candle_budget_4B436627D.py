from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from tradebot.training.candle_budget import (
    TRAINING_CANDLE_BUDGET_VERSION,
    TrainingCandleBudgetError,
    build_training_candle_budget,
    interval_to_milliseconds,
)
from tradebot.training import train_xgb


def test_27d_contract_version() -> None:
    assert TRAINING_CANDLE_BUDGET_VERSION == "4B.4.3.6.6.27D"


@pytest.mark.parametrize(
    ("interval", "expected"),
    [("1s", 86400), ("1m", 1440), ("15m", 96), ("1h", 24), ("4h", 6), ("1d", 1)],
)
def test_27d_budget_is_interval_aware(interval: str, expected: int) -> None:
    budget = build_training_candle_budget(interval, 1)
    assert budget.requested_candles == expected


def test_27d_multiple_days_scale_linearly() -> None:
    assert build_training_candle_budget("4h", 30).requested_candles == 180
    assert build_training_candle_budget("15m", 30).requested_candles == 2880


def test_27d_rejects_invalid_interval() -> None:
    with pytest.raises(TrainingCandleBudgetError, match="TRAINING_INTERVAL_UNSUPPORTED"):
        build_training_candle_budget("banana", 30)


def test_27d_rejects_non_binance_fixed_interval() -> None:
    with pytest.raises(TrainingCandleBudgetError, match="TRAINING_INTERVAL_UNSUPPORTED"):
        build_training_candle_budget("7m", 30)


def test_27d_rejects_non_positive_days() -> None:
    with pytest.raises(TrainingCandleBudgetError, match="TRAINING_DAYS_MUST_BE_POSITIVE"):
        build_training_candle_budget("1h", 0)


def test_27d_month_interval_is_fail_closed() -> None:
    with pytest.raises(TrainingCandleBudgetError, match="TRAINING_INTERVAL_MONTH_NOT_SUPPORTED"):
        interval_to_milliseconds("1M")


def test_27d_fetch_klines_uses_interval_budget_and_trims_overshoot(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    @dataclass
    class Response:
        payload: list[list[float]]
        def raise_for_status(self) -> None:
            return None
        def json(self) -> list[list[float]]:
            return self.payload

    def fake_get(url: str, timeout: int) -> Response:
        calls.append({"url": url, "timeout": timeout})
        rows = []
        for index in range(1000):
            open_time = float(index)
            rows.append([open_time, 1.0, 2.0, 0.5, 1.5, 10.0, open_time + 1, 15.0, 1.0, 1.0, 1.0, 0.0])
        return Response(rows)

    monkeypatch.setattr(train_xgb.requests, "get", fake_get)
    monkeypatch.setattr(train_xgb.time, "sleep", lambda _seconds: None)
    frame = train_xgb.fetch_klines("ETHUSDT", "4h", 30)
    assert len(frame) == 180
    assert len(calls) == 1


def test_27d_fetch_klines_rejects_invalid_interval_before_network(monkeypatch: pytest.MonkeyPatch) -> None:
    network_called = False
    def fake_get(*_args: Any, **_kwargs: Any) -> None:
        nonlocal network_called
        network_called = True
        raise AssertionError("network must not be called")
    monkeypatch.setattr(train_xgb.requests, "get", fake_get)
    with pytest.raises(TrainingCandleBudgetError, match="TRAINING_INTERVAL_UNSUPPORTED"):
        train_xgb.fetch_klines("ETHUSDT", "bad", 30)
    assert network_called is False
