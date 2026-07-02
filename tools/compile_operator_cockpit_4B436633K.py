from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33K"


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
        root / "tools/check_cockpit_runtime_4B436633J_H1.py",
        root / "tools/check_cockpit_runtime_4B436633K.py",
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
    orchestrator = (root / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    app = (root / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    security = (root / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    checks = {
        "external_recovery_evidence_gate_present": "build_external_recovery_evidence_gate_snapshot" in orchestrator,
        "evidence_routes_present": "/api/cockpit/external-recovery-evidence/capture" in app and "/api/cockpit/external-recovery-evidence/verify-no-mismatch-safe-apply" in app,
        "evidence_confirmations_present": "CONFIRM_CAPTURE_EXTERNAL_RECOVERY_EVIDENCE" in security and "CONFIRM_VERIFY_RECOVERY_NO_MISMATCH_WITH_EVIDENCE" in security,
        "fresh_snapshot_gate_present": "post_recovery_snapshot_fresh" in orchestrator,
        "entry_guard_evidence_gate_present": "EXTERNAL_RECOVERY_EVIDENCE_NOT_VERIFIED" in orchestrator,
        "no_auto_position_mutation_contract": "auto_position_mutation_performed" in orchestrator and "engine_position_state_mutated" in orchestrator,
    }
    ok = not errors and all(checks.values())
    payload = {
        "patch_version": PATCH_VERSION,
        "ok": ok,
        "compiled": compiled,
        "errors": errors,
        **checks,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "auto_position_mutation_performed": False,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
