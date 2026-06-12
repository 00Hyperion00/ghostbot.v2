from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tradebot.ai.decision_contract import (
    AI_DECISION_CONTRACT_VERSION,
    AIDecisionContractError,
    assert_startup_reload_parity,
    build_decision_contract,
    decision_contract_from_settings,
)
from tradebot.ai.provider import XGBoostSignalProvider


def test_27e_contract_version_and_default_fingerprint_are_stable() -> None:
    contract = build_decision_contract()
    assert AI_DECISION_CONTRACT_VERSION == "4B.4.3.6.6.27E"
    assert len(contract.fingerprint()) == 64
    assert contract.snapshot()["contract_version"] == "4B.4.3.6.6.27E"


def test_27e_settings_contract_preserves_all_threshold_fields() -> None:
    settings = SimpleNamespace(
        ai_confidence_threshold=0.61,
        ai_buy_threshold=0.71,
        ai_sell_threshold=0.66,
        ai_hold_band_low=0.41,
        ai_hold_band_high=0.54,
        ai_indecision_margin=0.07,
        ai_threshold_profile="operator_locked",
    )
    assert decision_contract_from_settings(settings).threshold_kwargs() == {
        "threshold": 0.61,
        "buy_threshold": 0.71,
        "sell_threshold": 0.66,
        "hold_band_low": 0.41,
        "hold_band_high": 0.54,
        "indecision_margin": 0.07,
        "threshold_profile": "operator_locked",
    }


def test_27e_invalid_hold_band_fails_closed() -> None:
    with pytest.raises(AIDecisionContractError, match="MODEL_THRESHOLD_HOLD_BAND_INVALID"):
        build_decision_contract(hold_band_low=0.70, hold_band_high=0.50)


def test_27e_threshold_out_of_range_fails_closed() -> None:
    with pytest.raises(AIDecisionContractError, match="MODEL_THRESHOLD_CONFIG_INVALID:buy_threshold"):
        build_decision_contract(buy_threshold=1.01)


def test_27e_startup_reload_mismatch_fails_closed() -> None:
    startup = build_decision_contract(buy_threshold=0.64)
    reload_contract = build_decision_contract(buy_threshold=0.65)
    with pytest.raises(AIDecisionContractError, match="MODEL_THRESHOLD_STARTUP_RELOAD_MISMATCH"):
        assert_startup_reload_parity(startup, reload_contract)


def test_27e_provider_startup_applies_full_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(XGBoostSignalProvider, "_load_model", lambda self: True)
    provider = XGBoostSignalProvider(
        "dummy.ubj",
        threshold=0.61,
        buy_threshold=0.71,
        sell_threshold=0.66,
        hold_band_low=0.41,
        hold_band_high=0.54,
        indecision_margin=0.07,
        threshold_profile="operator_locked",
    )
    assert provider.decision_contract.threshold_kwargs()["buy_threshold"] == 0.71
    assert provider.decision_contract.threshold_kwargs()["threshold_profile"] == "operator_locked"


def test_27e_provider_reload_applies_contract_atomically(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(XGBoostSignalProvider, "_load_model", lambda self: True)
    provider = XGBoostSignalProvider("dummy.ubj")
    candidate = SimpleNamespace(model=object(), model_path="next.ubj", schema_path="next.schema.json", feature_schema=SimpleNamespace(feature_lag=1), feature_lag=1)
    monkeypatch.setattr(provider, "_load_candidate", lambda path: candidate)
    assert provider.reload(model_path="next.ubj", buy_threshold=0.73, threshold_profile="operator_locked") is True
    assert provider.buy_threshold == 0.73
    assert provider.threshold_profile == "operator_locked"
    assert provider.model_path == "next.ubj"


def test_27e_provider_reload_invalid_contract_keeps_previous_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(XGBoostSignalProvider, "_load_model", lambda self: True)
    provider = XGBoostSignalProvider("dummy.ubj", buy_threshold=0.64)
    monkeypatch.setattr(provider, "_load_candidate", lambda path: (_ for _ in ()).throw(AssertionError("must not load model")))
    assert provider.reload(model_path="next.ubj", hold_band_low=0.90, hold_band_high=0.10) is False
    assert provider.buy_threshold == 0.64


def test_27e_engine_startup_uses_settings_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/engine.py").read_text(encoding="utf-8")
    assert "startup_ai_contract = decision_contract_from_settings(settings)" in text
    assert "**startup_ai_contract.threshold_kwargs()" in text


def test_27e_api_reload_has_parity_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/api.py").read_text(encoding="utf-8")
    assert "assert_startup_reload_parity(startup_contract, requested_contract)" in text
    assert "AI_RELOAD_BLOCKED_DECISION_CONTRACT" in text


def test_27e_standalone_service_has_parity_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/ai/service.py").read_text(encoding="utf-8")
    assert "assert_startup_reload_parity(startup_contract, requested_contract)" in text
    assert "TRADEBOT_AI_BUY_THRESHOLD" in text


def _run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    return subprocess.run([sys.executable, str(root / "tools/check_ai_startup_reload_threshold_parity_4B436627E.py"), *args, "--once-json"], cwd=root, env=env, text=True, capture_output=True, check=False)


def test_27e_checker_reports_parity_without_mutation() -> None:
    completed = _run_checker("--startup-buy-threshold", "0.71", "--reload-buy-threshold", "0.71")
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["reload_performed"] is False
    assert payload["trading_action_performed"] is False


def test_27e_checker_reports_mismatch_without_mutation() -> None:
    completed = _run_checker("--startup-buy-threshold", "0.71", "--reload-buy-threshold", "0.72")
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["reason_code"] == "MODEL_THRESHOLD_STARTUP_RELOAD_MISMATCH"
    assert "buy_threshold" in payload["diff"]
    assert payload["reload_performed"] is False
