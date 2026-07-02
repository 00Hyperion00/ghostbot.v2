from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33I-H1"
ROOT = Path.cwd()
FILES = [
    "src/tradebot/cockpit/__init__.py",
    "src/tradebot/cockpit/app.py",
    "src/tradebot/cockpit/broadcaster.py",
    "src/tradebot/cockpit/orchestrator.py",
    "src/tradebot/cockpit/schemas.py",
    "src/tradebot/cockpit/security.py",
    "src/tradebot/cli.py",
    "tools/check_cockpit_runtime_4B436633I.py",
    "tools/check_cockpit_runtime_4B436633I_H1.py",
]

errors: list[dict[str, str]] = []
compiled: list[str] = []
for rel in FILES:
    path = ROOT / rel
    if not path.exists():
        if rel.endswith("_H1.py"):
            continue
        errors.append({"file": rel, "error": "missing"})
        continue
    try:
        py_compile.compile(str(path), doraise=True)
        compiled.append(rel)
    except Exception as exc:  # pragma: no cover - helper script output
        errors.append({"file": rel, "error": repr(exc)})

orchestrator = (ROOT / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
helper_defined = "def _engine_position_recovery_key(" in orchestrator
helper_used = "_engine_position_recovery_key(self.settings)" in orchestrator
symbol_scoped_key = "engine_position_recovery:{symbol_text}" in orchestrator
no_auto_position_mutation_contract = "auto_position_mutation_performed" in orchestrator or "engine_position_state_mutated" in orchestrator

result = {
    "patch_version": PATCH_VERSION,
    "ok": not errors and helper_defined and helper_used and symbol_scoped_key,
    "compiled": compiled,
    "errors": errors,
    "engine_position_recovery_key_defined": helper_defined,
    "engine_position_recovery_key_used": helper_used,
    "symbol_scoped_recovery_key": symbol_scoped_key,
    "snapshot_nameerror_hotfix_contract": helper_defined and helper_used,
    "no_auto_position_mutation_contract_still_present": no_auto_position_mutation_contract,
}
print(json.dumps(result, indent=2, ensure_ascii=False))
raise SystemExit(0 if result["ok"] else 1)
