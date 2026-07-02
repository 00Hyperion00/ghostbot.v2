
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
