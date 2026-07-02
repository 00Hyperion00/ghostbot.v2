from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py"


def _text() -> str:
    return ORCH.read_text(encoding="utf-8")


def test_demo_entry_mark_price_spec_fallback_present() -> None:
    text = _text()
    assert "def _extract_mark_price(status: dict[str, Any], spec: dict[str, Any] | None = None)" in text
    assert 'spec.get("mark_price")' in text
    assert "mark_price = _extract_mark_price(status, spec)" in text


def test_demo_entry_gate_uses_33m_stabilized_entry_guard() -> None:
    text = _text()
    assert "def _entry_guard_ready_for_demo_entry" in text
    assert 'entry_guard.get("entry_guard_release_authorized", False)' in text
    assert 'cache_reconciliation.get("entry_guard_release_stabilized_after_safe_apply", False)' in text
    assert "entry_guard_ready = _entry_guard_ready_for_demo_entry(entry_guard=entry_guard, cache_reconciliation=cache_reconciliation)" in text


def test_h2_remains_fail_closed_and_no_live_real_enablement() -> None:
    text = _text()
    helper = text.split("def _entry_guard_ready_for_demo_entry", 1)[1].split("def build_demo_entry_execution_gate_snapshot", 1)[0]
    assert 'risk_badge == "GREEN"' in helper
    assert 'not entry_guard.get("force_buy_disabled", False)' in helper
    assert 'not entry_guard.get("entry_block_until_reconciled", False)' in helper
    assert '"live_real_enablement_performed": False' in text
    assert '"auto_position_mutation_performed": False' in text
