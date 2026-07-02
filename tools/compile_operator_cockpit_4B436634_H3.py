from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.34-H3"
ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/tradebot/cockpit/schemas.py",
    "src/tradebot/cockpit/security.py",
    "src/tradebot/cockpit/orchestrator.py",
    "src/tradebot/cockpit/app.py",
    "tools/check_cockpit_runtime_4B436634.py",
    "tools/compile_operator_cockpit_4B436634_H3.py",
]


def main() -> int:
    compiled = []
    errors = []
    for rel in FILES:
        path = ROOT / rel
        try:
            py_compile.compile(str(path), doraise=True)
            compiled.append(rel.replace("/", "\\"))
        except Exception as exc:
            errors.append({"file": rel, "error": str(exc)})
    orchestrator_text = (ROOT / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    checks = {
        "force_buy_result_binding_present": "def _build_force_buy_execution_binding" in orchestrator_text,
        "authorization_consumption_safety_present": "authorization_should_be_consumed" in orchestrator_text and "FORCE_BUY_RESULT_NOT_BOUND_OR_NOT_ACCEPTED" in orchestrator_text,
        "post_entry_position_detection_present": "def _position_present_from_status" in orchestrator_text,
        "protective_exit_mandatory_verification_present": "post_entry_protective_exit_verified" in orchestrator_text,
        "no_fill_no_protection_fail_closed_present": "NO_FILL_NO_PROTECTION_FAIL_CLOSED" in orchestrator_text,
        "force_buy_does_not_consume_on_missing_binding": "consumption_blocked_reason" in orchestrator_text,
    }
    payload = {"patch_version": PATCH_VERSION, "ok": not errors and all(checks.values()), "compiled": compiled, "errors": errors, **checks}
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
