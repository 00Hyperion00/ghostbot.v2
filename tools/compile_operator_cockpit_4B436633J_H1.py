from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33J-H1"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _root()
    targets = [
        root / "src/tradebot/cockpit/__init__.py",
        root / "src/tradebot/cockpit/app.py",
        root / "src/tradebot/cockpit/broadcaster.py",
        root / "src/tradebot/cockpit/orchestrator.py",
        root / "src/tradebot/cockpit/schemas.py",
        root / "src/tradebot/cockpit/security.py",
        root / "src/tradebot/cli.py",
        root / "tools/check_cockpit_runtime_4B436633J.py",
        root / "tools/check_cockpit_runtime_4B436633J_H1.py",
    ]
    compiled: list[str] = []
    errors: list[dict[str, str]] = []
    for target in targets:
        if not target.exists():
            errors.append({"file": str(target.relative_to(root)), "error": "missing"})
            continue
        try:
            py_compile.compile(str(target), doraise=True)
            compiled.append(str(target.relative_to(root)))
        except Exception as exc:
            errors.append({"file": str(target.relative_to(root)), "error": str(exc)})
    app_text = (root / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    bad_signature_absent = "operator_id = require_operator_identity(context)" not in app_text
    recovery_apply_action_identity_fixed = all(fragment in app_text for fragment in [
        'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.create_plan")',
        'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.confirm_plan")',
        'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.verify_completion")',
        'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.create_from_reviewed_candidate")',
        'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.confirm_manual_external_recovery")',
        'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.verify_no_mismatch")',
    ])
    ok = not errors and bad_signature_absent and recovery_apply_action_identity_fixed
    print(json.dumps({
        "patch_version": PATCH_VERSION,
        "ok": ok,
        "compiled": compiled,
        "errors": errors,
        "bad_operator_identity_signature_absent": bad_signature_absent,
        "recovery_apply_action_identity_fixed": recovery_apply_action_identity_fixed,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "auto_position_mutation_performed": False,
    }, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
