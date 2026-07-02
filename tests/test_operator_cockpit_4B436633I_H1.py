from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py"
APPLY = ROOT / "apply_4B436633I_H1_operator_cockpit_recovery_key_hotfix.py"


def test_engine_position_recovery_key_is_defined_and_used() -> None:
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "def _engine_position_recovery_key(" in text
    assert "_engine_position_recovery_key(self.settings)" in text
    assert "engine_position_recovery:{symbol_text}" in text


def test_hotfix_is_symbol_scoped_and_runtime_safe() -> None:
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "getattr(settings, \"symbol\", None)" in text
    assert "operator_cockpit:engine_position_recovery" in text
    assert "UNKNOWN" in text


def test_apply_contract_does_not_relax_safety() -> None:
    text = APPLY.read_text(encoding="utf-8")
    assert '"runtime_mutation_performed": False' in text
    assert '"order_path_mutation_performed": False' in text
    assert '"live_real_enablement_performed": False' in text
    assert '"auth_policy_relaxation_performed": False' in text
    assert '"auto_position_mutation_performed": False' in text
