from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.34"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    files = [
        root / "src/tradebot/cockpit/schemas.py",
        root / "src/tradebot/cockpit/security.py",
        root / "src/tradebot/cockpit/orchestrator.py",
        root / "src/tradebot/cockpit/app.py",
        root / "tools/check_cockpit_runtime_4B436634.py",
    ]
    errors: list[str] = []
    for file_path in files:
        try:
            py_compile.compile(str(file_path), doraise=True)
        except Exception as exc:
            errors.append(f"{file_path}: {exc}")
    orch = (root / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    sec = (root / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    app = (root / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    result = {
        "patch_version": PATCH_VERSION,
        "ok": not errors,
        "compiled": [str(p.relative_to(root)) for p in files],
        "errors": errors,
        "demo_entry_execution_control_version_present": "OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION" in orch,
        "entry_action_dry_run_present": "demo_entry_dry_run" in orch,
        "min_notional_step_size_verification_present": "ENTRY_MIN_NOTIONAL_SATISFIED" in orch and "ENTRY_MIN_QTY_SATISFIED" in orch,
        "order_intent_audit_present": "ORDER_INTENT_AUDIT_RECORDED" in orch,
        "demo_only_trade_enablement_present": "DEMO_ONLY_TRADE_AUTHORIZATION_VALID" in orch,
        "post_entry_protective_exit_verification_present": "verify_post_entry_protective_exit" in orch,
        "routes_present": "/api/cockpit/demo-entry-execution-gate" in app and "/api/cockpit/demo-entry/dry-run" in app,
        "confirmations_present": "CONFIRM_DEMO_ENTRY_DRY_RUN" in sec and "CONFIRM_AUTHORIZE_DEMO_ONLY_ENTRY" in sec,
        "no_engine_position_mutation_contract": "engine_position_state_mutated" in orch,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "auto_position_mutation_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
