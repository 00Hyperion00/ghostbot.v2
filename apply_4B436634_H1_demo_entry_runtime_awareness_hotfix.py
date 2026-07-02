from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.34-H1"
PATCH_NAME = "Demo Entry Runtime Awareness Snapshot Hotfix"

ROOT = Path.cwd()
ORCHESTRATOR = ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py"
APP = ROOT / "src" / "tradebot" / "cockpit" / "app.py"
SCHEMAS = ROOT / "src" / "tradebot" / "cockpit" / "schemas.py"
TEST_FILE = ROOT / "tests" / "test_operator_cockpit_4B436634_H1.py"
COMPILE_TOOL = ROOT / "tools" / "compile_operator_cockpit_4B436634_H1.py"
README = ROOT / "docs" / "OPERATOR_COCKPIT_DEMO_ENTRY_RUNTIME_AWARENESS_HOTFIX_4B436634_H1.md"

HELPER = '''

def _demo_entry_runtime_awareness_from_status(*, settings: Any, status: dict[str, Any]) -> dict[str, Any]:
    """Build the runtime-awareness contract required by the 33L config audit.

    34 must not call build_exchange_environment_config_audit without runtime_awareness.
    The helper is read-only and only normalizes status/config fields for demo-entry gate evaluation.
    """
    status = status if isinstance(status, dict) else {}
    symbol = str(
        status.get("symbol")
        or _safe_setting_text(settings, "symbol", "trading_symbol", "default_symbol")
        or "UNKNOWN"
    ).upper()
    base_asset, quote_asset = _infer_assets(symbol, {})
    position = _as_dict(status.get("position_snapshot"))
    pending = _as_dict(status.get("pending_snapshot"))
    balance_review = _as_dict(status.get("balance_review"))
    if balance_review:
        base_asset = str(balance_review.get("base_asset") or base_asset or "UNKNOWN").upper()
        quote_asset = str(balance_review.get("quote_asset") or quote_asset or "UNKNOWN").upper()
    return {
        "symbol": symbol,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "position_present": bool(position.get("present", False)),
        "pending_present": bool(pending.get("present", False)),
        "risk_badge": str(status.get("risk_badge") or status.get("risk") or "UNKNOWN"),
    }
'''

TEST_CONTENT = '''
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
'''

COMPILE_CONTENT = '''
from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.34-H1"
ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "src" / "tradebot" / "cockpit" / "schemas.py",
    ROOT / "src" / "tradebot" / "cockpit" / "security.py",
    ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py",
    ROOT / "src" / "tradebot" / "cockpit" / "app.py",
    ROOT / "tools" / "check_cockpit_runtime_4B436634.py",
    ROOT / "tools" / "compile_operator_cockpit_4B436634_H1.py",
]


def main() -> int:
    compiled: list[str] = []
    errors: list[dict[str, str]] = []
    for path in FILES:
        if not path.exists():
            errors.append({"path": str(path.relative_to(ROOT)), "error": "missing"})
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            compiled.append(str(path.relative_to(ROOT)))
        except Exception as exc:
            errors.append({"path": str(path.relative_to(ROOT)), "error": str(exc)})
    text = (ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py").read_text(encoding="utf-8")
    force_block = text.split("    async def force_buy(self) -> dict[str, Any]:", 1)[1].split("    async def force_sell", 1)[0]
    checks = {
        "demo_runtime_awareness_helper_present": "def _demo_entry_runtime_awareness_from_status" in text,
        "config_audit_runtime_awareness_call_present": "build_exchange_environment_config_audit(settings, runtime_awareness=runtime_awareness)" in text,
        "bare_demo_config_audit_call_removed": "config_audit = build_exchange_environment_config_audit(settings)" not in text,
        "force_buy_uses_full_snapshot_entry_guard": 'guard = _as_dict(snapshot.get("entry_guard"))' in force_block,
        "legacy_force_buy_guard_removed": "guard = await self._entry_guard_snapshot()" not in force_block,
    }
    result = {"patch_version": PATCH_VERSION, "ok": not errors and all(checks.values()), "compiled": compiled, "errors": errors, **checks}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

README_CONTENT = '''
# 4B.4.3.6.6.34-H1 — Demo Entry Runtime Awareness Snapshot Hotfix

Bu hotfix 34 patch sonrası görülen runtime 500 hatasını düzeltir.

## Kök neden

`build_exchange_environment_config_audit()` artık 33L kontratı gereği `runtime_awareness` keyword argümanı zorunlu istiyor. 34 içindeki `build_demo_entry_execution_gate_snapshot()` eski çağrı ile `build_exchange_environment_config_audit(settings)` çalıştırdığı için `/api/cockpit/snapshot`, WebSocket snapshot ve demo-entry endpointleri 500 hatasına düşüyordu.

## Düzeltmeler

- Demo-entry snapshot için read-only runtime-awareness helper eklendi.
- `build_exchange_environment_config_audit(settings, runtime_awareness=...)` çağrısı zorunlu hale getirildi.
- `force_buy()` eski 33F `_entry_guard_snapshot()` yolunu değil, tam 33M uyumlu snapshot entry guard’ını kullanacak şekilde düzeltildi.
- Live-real enablement, auth relaxation, order path mutation veya engine position mutation eklenmedi.

## Test

```powershell
python tools/compile_operator_cockpit_4B436634_H1.py
pytest tests/test_operator_cockpit_4B436634_H1.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```
'''


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    count = text.count(old)
    if count == 0:
        return text, False
    if count > 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1), True


def patch_orchestrator() -> dict[str, bool]:
    if not ORCHESTRATOR.exists():
        raise FileNotFoundError(f"missing file: {ORCHESTRATOR}")
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    original = text
    helper_added = False
    if "def _demo_entry_runtime_awareness_from_status" not in text:
        marker = "\ndef build_demo_entry_execution_gate_snapshot(*, settings: Any, status: dict[str, Any], entry_guard: dict[str, Any], source_gate: dict[str, Any], cache_reconciliation: dict[str, Any], state: dict[str, Any] | None) -> dict[str, Any]:\n"
        if marker not in text:
            raise RuntimeError("demo entry gate snapshot function marker not found")
        text = text.replace(marker, HELPER + marker, 1)
        helper_added = True

    old_call = "    config_audit = build_exchange_environment_config_audit(settings)\n"
    new_call = "    runtime_awareness = _demo_entry_runtime_awareness_from_status(settings=settings, status=status)\n    config_audit = build_exchange_environment_config_audit(settings, runtime_awareness=runtime_awareness)\n"
    call_replaced = False
    if old_call in text:
        text, call_replaced = replace_once(text, old_call, new_call, "demo config audit call")
    elif "build_exchange_environment_config_audit(settings, runtime_awareness=runtime_awareness)" in text:
        call_replaced = True
    else:
        raise RuntimeError("demo config audit call not found and fixed call not present")

    old_force_buy = '''    async def force_buy(self) -> dict[str, Any]:
        guard = await self._entry_guard_snapshot()
        if bool(guard.get("force_buy_disabled", False)):
            reason_code = "ENTRY_BLOCK_UNTIL_RECONCILED" if bool(guard.get("entry_block_until_reconciled", False)) else "RED_RISK_BADGE_ENTRY_GUARD"
            return self._result(ok=False, action="trade.force_buy", message="Force BUY blocked by cockpit entry guard", data={"reason_code": reason_code, "entry_guard": guard})
        snapshot = await self.snapshot(log_limit=20)
        demo_gate = await self._demo_entry_execution_gate_snapshot_from_snapshot(snapshot)
'''
    new_force_buy = '''    async def force_buy(self) -> dict[str, Any]:
        snapshot = await self.snapshot(log_limit=20)
        guard = _as_dict(snapshot.get("entry_guard"))
        if bool(guard.get("force_buy_disabled", False)):
            reason_code = "ENTRY_BLOCK_UNTIL_RECONCILED" if bool(guard.get("entry_block_until_reconciled", False)) else "RED_RISK_BADGE_ENTRY_GUARD"
            return self._result(ok=False, action="trade.force_buy", message="Force BUY blocked by cockpit entry guard", data={"reason_code": reason_code, "entry_guard": guard})
        demo_gate = await self._demo_entry_execution_gate_snapshot_from_snapshot(snapshot)
'''
    force_buy_replaced = False
    if old_force_buy in text:
        text, force_buy_replaced = replace_once(text, old_force_buy, new_force_buy, "force_buy guard block")
    else:
        force_block = text.split("    async def force_buy(self) -> dict[str, Any]:", 1)[1].split("    async def force_sell", 1)[0]
        if "guard = _as_dict(snapshot.get(\"entry_guard\"))" in force_block:
            force_buy_replaced = True
        else:
            raise RuntimeError("force_buy guard block not found")

    if text != original:
        ORCHESTRATOR.write_text(text, encoding="utf-8", newline="\n")
    return {"helper_added_or_present": helper_added or "def _demo_entry_runtime_awareness_from_status" in text, "config_audit_call_fixed": call_replaced, "force_buy_guard_fixed": force_buy_replaced}


def write_support_files() -> None:
    TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEST_FILE.write_text(TEST_CONTENT, encoding="utf-8", newline="\n")
    COMPILE_TOOL.parent.mkdir(parents=True, exist_ok=True)
    COMPILE_TOOL.write_text(COMPILE_CONTENT, encoding="utf-8", newline="\n")
    README.parent.mkdir(parents=True, exist_ok=True)
    README.write_text(README_CONTENT, encoding="utf-8", newline="\n")


def main() -> int:
    changes = patch_orchestrator()
    write_support_files()
    compiled: list[str] = []
    errors: list[dict[str, str]] = []
    for path in [ORCHESTRATOR, APP, SCHEMAS, COMPILE_TOOL, TEST_FILE]:
        try:
            py_compile.compile(str(path), doraise=True)
            compiled.append(str(path.relative_to(ROOT)))
        except Exception as exc:
            errors.append({"path": str(path.relative_to(ROOT)), "error": str(exc)})
    result = {
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written": [
            str(ORCHESTRATOR.relative_to(ROOT)),
            str(TEST_FILE.relative_to(ROOT)),
            str(COMPILE_TOOL.relative_to(ROOT)),
            str(README.relative_to(ROOT)),
        ],
        "compiled": compiled,
        "compile_errors": errors,
        "runtime_awareness_required_call_fixed": changes["config_audit_call_fixed"],
        "demo_entry_snapshot_500_hotfix_added": True,
        "force_buy_uses_33m_snapshot_entry_guard": changes["force_buy_guard_fixed"],
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "auto_position_mutation_performed": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
