from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33J"
ROOT = Path.cwd()
FILES = [
    "src/tradebot/cockpit/__init__.py",
    "src/tradebot/cockpit/app.py",
    "src/tradebot/cockpit/broadcaster.py",
    "src/tradebot/cockpit/orchestrator.py",
    "src/tradebot/cockpit/schemas.py",
    "src/tradebot/cockpit/security.py",
    "src/tradebot/cli.py",
    "tools/check_cockpit_runtime_4B436633J.py",
]

errors: list[dict[str, str]] = []
compiled: list[str] = []
for rel in FILES:
    path = ROOT / rel
    if not path.exists():
        errors.append({"file": rel, "error": "missing"})
        continue
    try:
        py_compile.compile(str(path), doraise=True)
        compiled.append(rel)
    except Exception as exc:
        errors.append({"file": rel, "error": repr(exc)})

schemas = (ROOT / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
security = (ROOT / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
orchestrator = (ROOT / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
app = (ROOT / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
result = {
    "patch_version": PATCH_VERSION,
    "ok": not errors
    and "OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION" in schemas
    and "recovery_plan_apply.create_from_reviewed_candidate" in security
    and "entry_guard_release_only_after_verified_no_mismatch" in orchestrator
    and "/api/cockpit/recovery-plan-apply/verify-no-mismatch" in app,
    "compiled": compiled,
    "errors": errors,
    "recovery_plan_apply_verification_schema_present": "OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION" in schemas,
    "recovery_plan_apply_confirmations_present": "recovery_plan_apply.verify_no_mismatch" in security,
    "verified_no_mismatch_gate_present": "entry_guard_release_only_after_verified_no_mismatch" in orchestrator,
    "recovery_plan_apply_routes_present": "/api/cockpit/recovery-plan-apply/create-from-reviewed-candidate" in app and "/api/cockpit/recovery-plan-apply/verify-no-mismatch" in app,
    "no_auto_position_mutation_contract": "auto_position_mutation_performed" in orchestrator and "engine_position_state_mutated" in orchestrator,
}
print(json.dumps(result, indent=2, ensure_ascii=False))
raise SystemExit(0 if result["ok"] else 1)
