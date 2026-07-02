from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33E"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    files = sorted((root / "src/tradebot/cockpit").glob("*.py")) + [root / "src/tradebot/cli.py"]
    compiled: list[str] = []
    errors: list[dict[str, str]] = []
    for file_path in files:
        try:
            py_compile.compile(str(file_path), doraise=True)
            compiled.append(file_path.relative_to(root).as_posix())
        except Exception as exc:
            errors.append({"path": file_path.relative_to(root).as_posix(), "error": str(exc)})
    payload = {
        "patch_version": PATCH_VERSION,
        "ok": not errors,
        "compiled": compiled,
        "errors": errors,
        "powershell_glob_required": False,
        "action_audit_runtime_lock_compile_contract": True,
        "stale_lock_diagnostic_present": (root / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8").find("inspect_runtime_lock") >= 0,
        "red_risk_entry_guard_present": (root / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8").find("RED_RISK_BADGE_ENTRY_GUARD") >= 0,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
