from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tradebot.position_sizing import (
    POSITION_SIZING_CONTRACT_VERSION,
    PositionSizingError,
    build_entry_sizing_decision,
    normalize_sizing_mode,
    validate_sizing_settings,
)


def _settings(**overrides: object) -> SimpleNamespace:
    payload: dict[str, object] = {
        "sizing_mode": "fixed_quote",
        "order_notional_usd": 25.0,
        "risk_percent_quote_balance": 2.5,
        "quote_balance_reserve_usd": 0.0,
        "max_quote_budget_usd": 0.0,
        "min_notional_buffer_multiplier": 1.10,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _rules(**overrides: object) -> SimpleNamespace:
    payload: dict[str, object] = {
        "step_size": 0.0001,
        "min_qty": 0.0001,
        "max_qty": 1000.0,
        "min_notional": 5.0,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _build(*, settings: SimpleNamespace | None = None, rules: SimpleNamespace | None = None, free_quote: float = 1000.0, price: float = 2500.0):
    return build_entry_sizing_decision(
        settings=settings or _settings(),
        symbol_rules=rules or _rules(),
        free_quote_balance=free_quote,
        reference_price=price,
    )


def test_27f_contract_version_is_stable() -> None:
    assert POSITION_SIZING_CONTRACT_VERSION == "4B.4.3.6.6.27F"


def test_27f_fixed_quote_preserves_legacy_default_budget() -> None:
    decision = _build()
    assert decision.sizing_mode == "fixed_quote"
    assert decision.quote_budget == 25.0
    assert decision.quantity == 0.01
    assert decision.order_notional == 25.0


def test_27f_risk_percent_mode_uses_usable_quote_balance() -> None:
    decision = _build(settings=_settings(sizing_mode="risk_percent_quote_balance", risk_percent_quote_balance=2.5), free_quote=1000.0)
    assert decision.quote_budget == 25.0
    assert decision.quantity == 0.01


def test_27f_risk_percent_uses_reserve_before_budget() -> None:
    decision = _build(settings=_settings(sizing_mode="risk_percent_quote_balance", risk_percent_quote_balance=10.0, quote_balance_reserve_usd=200.0), free_quote=1000.0, price=1000.0)
    assert decision.usable_quote_balance == 800.0
    assert decision.requested_quote_budget == 80.0
    assert decision.quote_budget == 80.0


def test_27f_optional_max_quote_budget_caps_entry() -> None:
    decision = _build(settings=_settings(sizing_mode="risk_percent_quote_balance", risk_percent_quote_balance=25.0, max_quote_budget_usd=40.0), free_quote=1000.0, price=1000.0)
    assert decision.requested_quote_budget == 250.0
    assert decision.quote_budget == 40.0
    assert decision.max_quote_budget_applied is True


def test_27f_legacy_risk_percent_alias_is_normalized() -> None:
    assert normalize_sizing_mode("risk_percent") == "risk_percent_quote_balance"
    decision = _build(settings=_settings(sizing_mode="risk_percent", risk_percent_quote_balance=2.5))
    assert decision.legacy_sizing_mode_alias_used is True


def test_27f_unknown_sizing_mode_fails_closed() -> None:
    with pytest.raises(PositionSizingError, match="SIZING_MODE_UNSUPPORTED"):
        validate_sizing_settings(_settings(sizing_mode="martingale"))


def test_27f_invalid_risk_percent_fails_closed() -> None:
    with pytest.raises(PositionSizingError, match="SIZING_RISK_PERCENT_INVALID"):
        _build(settings=_settings(sizing_mode="risk_percent_quote_balance", risk_percent_quote_balance=101.0))


def test_27f_non_positive_quote_balance_fails_closed() -> None:
    with pytest.raises(PositionSizingError, match="SIZING_QUOTE_BALANCE_NON_POSITIVE"):
        _build(free_quote=0.0)


def test_27f_reserve_cannot_consume_entire_quote_balance() -> None:
    with pytest.raises(PositionSizingError, match="SIZING_USABLE_QUOTE_BALANCE_NON_POSITIVE"):
        _build(settings=_settings(quote_balance_reserve_usd=1000.0), free_quote=1000.0)


def test_27f_missing_step_size_fails_closed() -> None:
    with pytest.raises(PositionSizingError, match="SIZING_SYMBOL_FILTERS_MISSING:step_size"):
        _build(rules=_rules(step_size=0.0))


def test_27f_missing_min_notional_fails_closed() -> None:
    with pytest.raises(PositionSizingError, match="SIZING_SYMBOL_FILTERS_MISSING:min_notional"):
        _build(rules=_rules(min_notional=0.0))


def test_27f_budget_below_buffered_min_notional_fails_closed() -> None:
    with pytest.raises(PositionSizingError, match="SIZING_QUOTE_BUDGET_BELOW_MIN_NOTIONAL"):
        _build(settings=_settings(order_notional_usd=5.0), rules=_rules(min_notional=5.0), price=2500.0)


def test_27f_quantity_is_rounded_down_to_step_without_overspend() -> None:
    decision = _build(settings=_settings(order_notional_usd=25.0), rules=_rules(step_size=0.003), price=1000.0)
    assert decision.raw_quantity == 0.025
    assert decision.quantity == 0.024
    assert decision.order_notional == 24.0
    assert decision.order_notional <= decision.quote_budget


def test_27f_max_qty_filter_caps_quantity() -> None:
    decision = _build(settings=_settings(order_notional_usd=100.0), rules=_rules(step_size=0.01, min_qty=0.01, max_qty=0.05), price=1000.0)
    assert decision.quantity == 0.05
    assert decision.max_qty_applied is True
    assert decision.order_notional == 50.0


def test_27f_engine_entry_hook_and_exit_path_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/engine.py").read_text(encoding="utf-8")
    assert "build_entry_sizing_decision(" in text
    assert "ENTRY_SIZING_VERIFIED" in text
    assert "requested_qty = float(requested_qty_override)" in text


def test_27f_config_safety_exposes_position_sizing_snapshot() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/config_safety.py").read_text(encoding="utf-8")
    assert "validate_sizing_settings(cfg)" in text
    assert "'position_sizing': sizing_snapshot" in text


def _run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    return subprocess.run(
        [sys.executable, str(root / "tools/check_risk_percent_position_sizing_4B436627F.py"), *args, "--once-json"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_27f_checker_reports_read_only_risk_percent_decision() -> None:
    completed = _run_checker("--sizing-mode", "risk_percent_quote_balance", "--free-quote-balance", "1000", "--risk-percent-quote-balance", "2.5")
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["decision"]["quote_budget"] == 25.0
    assert payload["network_request_performed"] is False
    assert payload["trading_action_performed"] is False


def test_27f_checker_reports_fail_closed_unsupported_mode() -> None:
    completed = _run_checker("--sizing-mode", "martingale")
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["reason_code"] == "SIZING_MODE_UNSUPPORTED:martingale"
    assert payload["trading_action_performed"] is False
