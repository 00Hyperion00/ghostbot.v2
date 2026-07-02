from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33i_schema_contract_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_VERSION" in text
    assert "4B.4.3.6.6.33I" in text


def test_33i_security_confirmations_present() -> None:
    text = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert '"engine_position_recovery.create_plan": "CONFIRM_CREATE_ENGINE_POSITION_RECOVERY_PLAN"' in text
    assert '"engine_position_recovery.confirm_plan": "CONFIRM_CONFIRM_ENGINE_POSITION_RECOVERY_PLAN"' in text
    assert '"engine_position_recovery.verify_completion": "CONFIRM_VERIFY_ENGINE_POSITION_RECOVERY_COMPLETE"' in text
    assert '"engine_position_recovery.clear_plan": "CONFIRM_CLEAR_ENGINE_POSITION_RECOVERY_PLAN"' in text


def test_33i_orchestrator_recovery_gate_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_engine_position_recovery_gate_snapshot" in text
    assert "create_engine_position_recovery_plan" in text
    assert "confirm_engine_position_recovery_plan" in text
    assert "verify_engine_position_recovery_completion" in text
    assert "ENGINE_POSITION_RECOVERY_NOT_VERIFIED" in text
    assert "auto_position_mutation_performed" in text
    assert "engine_position_state_mutated" in text
    assert "live_real_enablement" not in text.lower()
    assert "order_path_mutation" not in text.lower()


def test_33i_routes_present() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "/api/cockpit/engine-position-recovery-gate" in text
    assert "/api/cockpit/engine-position-recovery/create-plan" in text
    assert "/api/cockpit/engine-position-recovery/confirm-plan" in text
    assert "/api/cockpit/engine-position-recovery/verify-completion" in text
    assert "/api/cockpit/engine-position-recovery/clear-plan" in text


def test_33i_ui_and_helper_present() -> None:
    html = (_root() / "src/tradebot/cockpit/static/index.html").read_text(encoding="utf-8")
    js = (_root() / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    helper = (_root() / "tools/check_cockpit_runtime_4B436633I.py").read_text(encoding="utf-8")
    assert "Engine Position Recovery Gate" in html
    assert "renderEnginePositionRecoveryGate" in js
    assert "CONFIRM_VERIFY_ENGINE_POSITION_RECOVERY_COMPLETE" in js
    assert "engine_position_recovery_gate" in helper


def test_33i_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436633I.py"), doraise=True)
