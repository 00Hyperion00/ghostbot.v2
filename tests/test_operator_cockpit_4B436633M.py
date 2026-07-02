from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33m_schema_version_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION" in text
    assert "4B.4.3.6.6.33M" in text


def test_33m_orchestrator_cache_reconciliation_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_engine_status_balance_cache_reconciliation_snapshot" in text
    assert "apply_engine_status_balance_cache_reconciliation" in text
    assert "apply_engine_status_balance_cache_reconciliation_to_source_gate" in text
    assert "RUNTIME_SNAPSHOT_OVERRIDE_ACTIVE" in text
    assert "STALE_ENGINE_BALANCE_MISMATCH_PRESENT" in text
    assert "RISK_BADGE_RECOMPUTED_FROM_VERIFIED_FRESH_SOURCE" in text
    assert "ENTRY_GUARD_RELEASE_STABILIZED_AFTER_SAFE_APPLY" in text
    assert "verified_fresh_exchange_balance_33M" in text


def test_33m_external_gate_stable_safe_apply_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "safe_apply_verified_from_fresh_source" in text
    assert "stable_fresh_source_release" in text
    assert "safe_apply_verified_from_fresh_source" in text
    assert "fresh_snapshot or stable_fresh_source_release" in text


def test_33m_runtime_helper_present() -> None:
    helper = (_root() / "tools/check_cockpit_runtime_4B436633M.py").read_text(encoding="utf-8")
    assert "engine_status_balance_cache_reconciliation" in helper
    assert "runtime_snapshot_override_active" in helper
    assert "stale_engine_balance_invalidated" in helper
    assert "entry_guard_release_stabilized_after_safe_apply" in helper


def test_33m_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436633M.py"), doraise=True)
    py_compile.compile(str(_root() / "tools/compile_operator_cockpit_4B436633M.py"), doraise=True)
