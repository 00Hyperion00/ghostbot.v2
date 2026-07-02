from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33F"

def main() -> None:
    root = Path(__file__).resolve().parents[1]
    files = sorted((root / "src/tradebot/cockpit").glob("*.py")) + [root / "src/tradebot/cli.py"]
    compiled = []
    errors = []
    for file_path in files:
        try:
            py_compile.compile(str(file_path), doraise=True)
            compiled.append(file_path.relative_to(root).as_posix())
        except Exception as exc:
            errors.append({"path": file_path.relative_to(root).as_posix(), "error": str(exc)})
    orch = (root / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    app = (root / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    js = (root / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    payload = {"patch_version": PATCH_VERSION, "ok": not errors, "compiled": compiled, "errors": errors, "powershell_glob_required": False, "risk_reconciliation_compile_contract": True, "always_on_entry_guard_present": "always_on_entry_guard_snapshot" in orch, "entry_block_until_reconciled_present": "ENTRY_BLOCK_UNTIL_RECONCILED" in orch, "risk_reconciliation_routes_present": "/api/cockpit/risk-reconciliation" in app, "reconcile_wizard_ui_present": "renderRiskReconciliation" in js}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
