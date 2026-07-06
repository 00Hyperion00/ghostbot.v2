from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436658I"
PATCH_VERSION = "4B.4.3.6.6.58I"
PATCH_NAME = "Live Risk Limit Circuit Breaker Closure"
REQUIRED_FILES = [
    "README_APPLY_4B436658I.txt",
    "docs/PAPER_SANDBOX_LIVE_RISK_LIMIT_CIRCUIT_BREAKER_CLOSURE_4B436658I.md",
    "src/tradebot/paper_sandbox_live_risk_limit_circuit_breaker_closure.py",
    "tests/test_paper_sandbox_live_risk_limit_circuit_breaker_closure_4B436658I.py",
    "tools/apply_4B436658I_paper_sandbox_live_risk_limit_circuit_breaker_closure.py",
    "tools/check_4B436658I_paper_sandbox_live_risk_limit_circuit_breaker_closure.py",
    "tools/run_4B436658I_paper_sandbox_live_risk_limit_circuit_breaker_closure.py",
    "tools/rollback_4B436658I_paper_sandbox_live_risk_limit_circuit_breaker_closure.py",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in ["src/tradebot/paper_sandbox_live_risk_limit_circuit_breaker_closure.py", "tools/check_4B436658I_paper_sandbox_live_risk_limit_circuit_breaker_closure.py", "tools/run_4B436658I_paper_sandbox_live_risk_limit_circuit_breaker_closure.py", "tests/test_paper_sandbox_live_risk_limit_circuit_breaker_closure_4B436658I.py"]:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception as exc:  # pragma: no cover
            compile_errors[rel] = str(exc)
    payload = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "phase50_60_source_mutation_performed": True,
        "paper_submit_enabled_by_patch": False,
        "paper_submit_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "runtime_start_performed": False,
        "runtime_process_start_performed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "live_real_approved_by_patch": False,
        "exchange_submit_performed": False,
        "signed_request_performed": False,
        "private_api_access_allowed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "destructive_cleanup_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "git_tag_performed": False,
        "written_files": REQUIRED_FILES,
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if payload["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
