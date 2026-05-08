from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def _load_runner_module():
    root = Path(__file__).resolve().parents[1]
    script = root / "tools" / "run_futures_funding_open_interest_edge_exploration_4B436625B.py"
    spec = importlib.util.spec_from_file_location("runner_25b", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_clamps_futures_data_start_to_retention_window() -> None:
    runner = _load_runner_module()
    end_ms = 1_800_000_000_000
    old_start_ms = end_ms - 90 * 24 * 60 * 60_000
    clamped = runner.clamp_futures_data_start_ms(old_start_ms, end_ms)
    assert clamped == end_ms - runner.FUTURES_DATA_RETENTION_MS
    assert runner.FUTURES_DATA_RETENTION_DAYS == 29


def test_optional_futures_endpoint_failure_returns_empty(monkeypatch) -> None:
    runner = _load_runner_module()

    def _raise(*args, **kwargs):
        raise RuntimeError("HTTP Error 400")

    monkeypatch.setattr(runner, "fetch_futures_data_series", _raise)
    frame = runner.safe_fetch_futures_data_series(
        "https://fapi.binance.com",
        "/futures/data/openInterestHist",
        "BTCUSDT",
        "1h",
        1,
        2,
        1,
    )
    assert isinstance(frame, pd.DataFrame)
    assert frame.empty
