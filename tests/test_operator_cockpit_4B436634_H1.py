
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py"


def _text() -> str:
    return ORCH.read_text(encoding="utf-8")


def test_demo_entry_config_audit_uses_runtime_awareness() -> None:
    text = _text()
    assert "def _demo_entry_runtime_awareness_from_status" in text
    assert "runtime_awareness = _demo_entry_runtime_awareness_from_status(settings=settings, status=status)" in text
    assert "build_exchange_environment_config_audit(settings, runtime_awareness=runtime_awareness)" in text
    assert "config_audit = build_exchange_environment_config_audit(settings)" not in text


def test_force_buy_uses_full_snapshot_entry_guard_after_33m() -> None:
    text = _text()
    force_buy = text.split("    async def force_buy(self) -> dict[str, Any]:", 1)[1].split("    async def force_sell", 1)[0]
    assert "snapshot = await self.snapshot(log_limit=20)" in force_buy
    assert 'guard = _as_dict(snapshot.get("entry_guard"))' in force_buy
    assert "guard = await self._entry_guard_snapshot()" not in force_buy
    assert "DEMO_ENTRY_EXECUTION_GATE_NOT_READY" in force_buy


def test_no_trade_enablement_or_position_mutation_contracts() -> None:
    text = _text()
    assert "live_real_enablement_performed" in text
    assert "auto_position_mutation_performed" in text
    assert "await self.engine.force_buy()" in text
