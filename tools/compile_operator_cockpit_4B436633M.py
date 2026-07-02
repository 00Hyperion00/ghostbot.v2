from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33M"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _root()
    files = [
        root / "src/tradebot/cockpit/schemas.py",
        root / "src/tradebot/cockpit/security.py",
        root / "src/tradebot/cockpit/orchestrator.py",
        root / "src/tradebot/cockpit/app.py",
        root / "tools/check_cockpit_runtime_4B436633M.py",
    ]
    errors: list[str] = []
    compiled: list[str] = []
    for path in files:
        if not path.exists():
            errors.append(f"missing:{path.relative_to(root)}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            compiled.append(str(path.relative_to(root)))
        except Exception as exc:  # pragma: no cover
            errors.append(f"compile_failed:{path.relative_to(root)}:{exc}")
    orchestrator = (root / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    schemas = (root / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    result = {
        "patch_version": PATCH_VERSION,
        "ok": not errors,
        "compiled": compiled,
        "errors": errors,
        "engine_status_balance_cache_reconciliation_version_present": "OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION" in schemas,
        "runtime_snapshot_override_present": "runtime_snapshot_override_active" in orchestrator,
        "stale_engine_balance_invalidated_present": "stale_engine_balance_invalidated" in orchestrator,
        "risk_badge_recompute_present": "risk_badge_recomputed_from_verified_fresh_source" in orchestrator,
        "entry_guard_final_release_consistency_present": "ENTRY_GUARD_RELEASE_STABILIZED_AFTER_SAFE_APPLY" in orchestrator,
        "no_engine_position_mutation_contract": "engine_position_state_mutated" in orchestrator and "auto_position_mutation_performed" in orchestrator,
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
