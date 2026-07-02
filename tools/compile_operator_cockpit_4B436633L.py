from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33L"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    targets = [
        root / "src/tradebot/cockpit/__init__.py",
        root / "src/tradebot/cockpit/app.py",
        root / "src/tradebot/cockpit/broadcaster.py",
        root / "src/tradebot/cockpit/orchestrator.py",
        root / "src/tradebot/cockpit/schemas.py",
        root / "src/tradebot/cockpit/security.py",
        root / "src/tradebot/cli.py",
        root / "tools/check_cockpit_runtime_4B436633K.py",
        root / "tools/check_cockpit_runtime_4B436633L.py",
    ]
    compiled: list[str] = []
    errors: list[dict[str, str]] = []
    for target in targets:
        if not target.exists():
            continue
        try:
            py_compile.compile(str(target), doraise=True)
            compiled.append(str(target.relative_to(root)))
        except Exception as exc:
            errors.append({"file": str(target.relative_to(root)), "error": str(exc)})
    orchestrator = (root / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    app = (root / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    security = (root / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    result = {
        "patch_version": PATCH_VERSION,
        "ok": not errors,
        "compiled": compiled,
        "errors": errors,
        "exchange_environment_source_gate_present": "build_exchange_environment_source_gate_snapshot" in orchestrator,
        "fresh_exchange_balance_read_required": "fresh_exchange_balance_read_required" in orchestrator,
        "stale_engine_balance_snapshot_rejection_present": "STALE_ENGINE_BALANCE_SNAPSHOT_REJECTED" in orchestrator,
        "verified_fresh_source_preflight_required": "no_mismatch_from_verified_fresh_source" in orchestrator,
        "exchange_environment_routes_present": "/api/cockpit/exchange-environment-source-gate/capture-fresh-balance" in app,
        "exchange_environment_confirmations_present": "CONFIRM_CAPTURE_FRESH_EXCHANGE_BALANCE_SOURCE" in security,
        "no_auto_position_mutation_contract": "auto_position_mutation_performed" in orchestrator,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "auto_position_mutation_performed": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
