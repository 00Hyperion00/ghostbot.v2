from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33l_schema_version_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION" in text
    assert "4B.4.3.6.6.33L" in text


def test_33l_security_confirmations_present() -> None:
    text = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert '"exchange_environment.verify_consistency": "CONFIRM_VERIFY_EXCHANGE_ENVIRONMENT_CONSISTENCY"' in text
    assert '"exchange_environment.capture_fresh_balance": "CONFIRM_CAPTURE_FRESH_EXCHANGE_BALANCE_SOURCE"' in text
    assert '"exchange_environment.clear": "CONFIRM_CLEAR_EXCHANGE_ENVIRONMENT_SOURCE_GATE"' in text


def test_33l_orchestrator_source_gate_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_exchange_environment_source_gate_snapshot" in text
    assert "fetch_fresh_exchange_balance_source" in text
    assert "capture_fresh_exchange_balance_source" in text
    assert "verify_recovery_no_mismatch_from_fresh_exchange_source" in text
    assert "STALE_ENGINE_BALANCE_SNAPSHOT_REJECTED" in text
    assert "NO_MISMATCH_VERIFIED_FROM_FRESH_EXCHANGE_SOURCE" in text
    assert "engine_status_balances" in text
    assert "auto_position_mutation_performed" in text


def test_33l_routes_present() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "/api/cockpit/exchange-environment-source-gate" in text
    assert "/api/cockpit/exchange-environment-source-gate/verify-consistency" in text
    assert "/api/cockpit/exchange-environment-source-gate/capture-fresh-balance" in text
    assert "/api/cockpit/exchange-environment-source-gate/clear" in text


def test_33l_runtime_helper_present() -> None:
    helper = (_root() / "tools/check_cockpit_runtime_4B436633L.py").read_text(encoding="utf-8")
    assert "exchange_environment_source_gate" in helper
    assert "fresh_exchange_balance_verified" in helper
    assert "no_mismatch_from_verified_fresh_source" in helper


def test_33l_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436633L.py"), doraise=True)
    py_compile.compile(str(_root() / "tools/compile_operator_cockpit_4B436633L.py"), doraise=True)
