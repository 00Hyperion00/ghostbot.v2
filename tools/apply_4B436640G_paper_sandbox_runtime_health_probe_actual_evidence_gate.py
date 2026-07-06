from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436640G"
PATCH_VERSION = "4B.4.3.6.6.40G"
PATCH_NAME = "Paper Sandbox Runtime Health Probe Actual Evidence Gate"
REQUIRED_FILES = [
    "README_APPLY_4B436640G.txt",
    "docs/PAPER_SANDBOX_RUNTIME_HEALTH_PROBE_ACTUAL_EVIDENCE_GATE_4B436640G.md",
    "src/tradebot/paper_sandbox_runtime_health_probe_actual_evidence_gate.py",
    "tests/test_paper_sandbox_runtime_health_probe_actual_evidence_gate_4B436640G.py",
    "tools/apply_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py",
    "tools/check_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py",
    "tools/run_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py",
    "tools/rollback_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in ["src/tradebot/paper_sandbox_runtime_health_probe_actual_evidence_gate.py", "tools/check_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py", "tools/run_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py", "tests/test_paper_sandbox_runtime_health_probe_actual_evidence_gate_4B436640G.py"]:
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
        "paper_sandbox_phase40_source_mutation_performed": True,
        "runtime_start_performed": False,
        "runtime_process_start_performed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "signed_request_performed": False,
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
