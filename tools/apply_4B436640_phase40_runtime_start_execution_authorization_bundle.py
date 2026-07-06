from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436640"
PATCH_VERSION = "4B.4.3.6.6.40"
PATCH_NAME = "Phase 40 Runtime Start Execution Authorization Bundle"
PHASE_IDS = ["4B436640A", "4B436640B", "4B436640C", "4B436640D", "4B436640E", "4B436640F", "4B436640G", "4B436640H", "4B436640I"]
REQUIRED_FILES = ['README_APPLY_4B436640_PHASE40_BUNDLE.txt', 'docs/PHASE40_RUNTIME_START_EXECUTION_AUTHORIZATION_BUNDLE_4B436640.md', 'src/tradebot/paper_sandbox_phase40_common.py', 'tests/test_phase40_runtime_start_execution_authorization_bundle_4B436640.py', 'tools/apply_4B436640_phase40_runtime_start_execution_authorization_bundle.py', 'tools/check_4B436640_phase40_runtime_start_execution_authorization_bundle.py', 'tools/run_4B436640_phase40_runtime_start_execution_authorization_bundle.py', 'tools/rollback_4B436640_phase40_runtime_start_execution_authorization_bundle.py', 'README_APPLY_4B436640A.txt', 'docs/PAPER_SANDBOX_RUNTIME_START_EXECUTION_AUTHORIZATION_REVIEW_4B436640A.md', 'src/tradebot/paper_sandbox_runtime_start_execution_authorization_review.py', 'tests/test_paper_sandbox_runtime_start_execution_authorization_review_4B436640A.py', 'tools/apply_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py', 'tools/check_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py', 'tools/run_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py', 'tools/rollback_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py', 'README_APPLY_4B436640B.txt', 'docs/PAPER_SANDBOX_TYPED_RUNTIME_START_OPERATOR_APPROVAL_4B436640B.md', 'src/tradebot/paper_sandbox_typed_runtime_start_operator_approval.py', 'tests/test_paper_sandbox_typed_runtime_start_operator_approval_4B436640B.py', 'tools/apply_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py', 'tools/check_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py', 'tools/run_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py', 'tools/rollback_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py', 'README_APPLY_4B436640C.txt', 'docs/PAPER_SANDBOX_RUNTIME_START_PRE_EXECUTION_GATE_4B436640C.md', 'src/tradebot/paper_sandbox_runtime_start_pre_execution_gate.py', 'tests/test_paper_sandbox_runtime_start_pre_execution_gate_4B436640C.py', 'tools/apply_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py', 'tools/check_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py', 'tools/run_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py', 'tools/rollback_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py', 'README_APPLY_4B436640D.txt', 'docs/PAPER_SANDBOX_SINGLE_INSTANCE_RUNTIME_LOCK_VALIDATION_4B436640D.md', 'src/tradebot/paper_sandbox_single_instance_runtime_lock_validation.py', 'tests/test_paper_sandbox_single_instance_runtime_lock_validation_4B436640D.py', 'tools/apply_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py', 'tools/check_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py', 'tools/run_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py', 'tools/rollback_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py', 'README_APPLY_4B436640E.txt', 'docs/PAPER_SANDBOX_CONTROLLED_RUNTIME_START_COMMAND_PACKAGE_4B436640E.md', 'src/tradebot/paper_sandbox_controlled_runtime_start_command_package.py', 'tests/test_paper_sandbox_controlled_runtime_start_command_package_4B436640E.py', 'tools/apply_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py', 'tools/check_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py', 'tools/run_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py', 'tools/rollback_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py', 'README_APPLY_4B436640F.txt', 'docs/PAPER_SANDBOX_LOCAL_RUNTIME_PROCESS_START_EVIDENCE_4B436640F.md', 'src/tradebot/paper_sandbox_local_runtime_process_start_evidence.py', 'tests/test_paper_sandbox_local_runtime_process_start_evidence_4B436640F.py', 'tools/apply_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py', 'tools/check_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py', 'tools/run_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py', 'tools/rollback_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py', 'README_APPLY_4B436640G.txt', 'docs/PAPER_SANDBOX_RUNTIME_HEALTH_PROBE_ACTUAL_EVIDENCE_GATE_4B436640G.md', 'src/tradebot/paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'tests/test_paper_sandbox_runtime_health_probe_actual_evidence_gate_4B436640G.py', 'tools/apply_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'tools/check_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'tools/run_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'tools/rollback_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'README_APPLY_4B436640H.txt', 'docs/PAPER_SANDBOX_OBSERVATION_RUNTIME_METRICS_ACTUAL_EVIDENCE_GATE_4B436640H.md', 'src/tradebot/paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'tests/test_paper_sandbox_observation_runtime_metrics_actual_evidence_gate_4B436640H.py', 'tools/apply_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'tools/check_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'tools/run_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'tools/rollback_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'README_APPLY_4B436640I.txt', 'docs/PAPER_SANDBOX_RUNTIME_START_EXECUTION_CLOSURE_4B436640I.md', 'src/tradebot/paper_sandbox_runtime_start_execution_closure.py', 'tests/test_paper_sandbox_runtime_start_execution_closure_4B436640I.py', 'tools/apply_4B436640I_paper_sandbox_runtime_start_execution_closure.py', 'tools/check_4B436640I_paper_sandbox_runtime_start_execution_closure.py', 'tools/run_4B436640I_paper_sandbox_runtime_start_execution_closure.py', 'tools/rollback_4B436640I_paper_sandbox_runtime_start_execution_closure.py']


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    compile_targets = ['src/tradebot/paper_sandbox_phase40_common.py', 'tests/test_phase40_runtime_start_execution_authorization_bundle_4B436640.py', 'tools/apply_4B436640_phase40_runtime_start_execution_authorization_bundle.py', 'tools/check_4B436640_phase40_runtime_start_execution_authorization_bundle.py', 'tools/run_4B436640_phase40_runtime_start_execution_authorization_bundle.py', 'tools/rollback_4B436640_phase40_runtime_start_execution_authorization_bundle.py', 'src/tradebot/paper_sandbox_runtime_start_execution_authorization_review.py', 'tests/test_paper_sandbox_runtime_start_execution_authorization_review_4B436640A.py', 'tools/apply_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py', 'tools/check_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py', 'tools/run_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py', 'tools/rollback_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py', 'src/tradebot/paper_sandbox_typed_runtime_start_operator_approval.py', 'tests/test_paper_sandbox_typed_runtime_start_operator_approval_4B436640B.py', 'tools/apply_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py', 'tools/check_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py', 'tools/run_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py', 'tools/rollback_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py', 'src/tradebot/paper_sandbox_runtime_start_pre_execution_gate.py', 'tests/test_paper_sandbox_runtime_start_pre_execution_gate_4B436640C.py', 'tools/apply_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py', 'tools/check_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py', 'tools/run_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py', 'tools/rollback_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py', 'src/tradebot/paper_sandbox_single_instance_runtime_lock_validation.py', 'tests/test_paper_sandbox_single_instance_runtime_lock_validation_4B436640D.py', 'tools/apply_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py', 'tools/check_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py', 'tools/run_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py', 'tools/rollback_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py', 'src/tradebot/paper_sandbox_controlled_runtime_start_command_package.py', 'tests/test_paper_sandbox_controlled_runtime_start_command_package_4B436640E.py', 'tools/apply_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py', 'tools/check_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py', 'tools/run_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py', 'tools/rollback_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py', 'src/tradebot/paper_sandbox_local_runtime_process_start_evidence.py', 'tests/test_paper_sandbox_local_runtime_process_start_evidence_4B436640F.py', 'tools/apply_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py', 'tools/check_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py', 'tools/run_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py', 'tools/rollback_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py', 'src/tradebot/paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'tests/test_paper_sandbox_runtime_health_probe_actual_evidence_gate_4B436640G.py', 'tools/apply_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'tools/check_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'tools/run_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'tools/rollback_4B436640G_paper_sandbox_runtime_health_probe_actual_evidence_gate.py', 'src/tradebot/paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'tests/test_paper_sandbox_observation_runtime_metrics_actual_evidence_gate_4B436640H.py', 'tools/apply_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'tools/check_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'tools/run_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'tools/rollback_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py', 'src/tradebot/paper_sandbox_runtime_start_execution_closure.py', 'tests/test_paper_sandbox_runtime_start_execution_closure_4B436640I.py', 'tools/apply_4B436640I_paper_sandbox_runtime_start_execution_closure.py', 'tools/check_4B436640I_paper_sandbox_runtime_start_execution_closure.py', 'tools/run_4B436640I_paper_sandbox_runtime_start_execution_closure.py', 'tools/rollback_4B436640I_paper_sandbox_runtime_start_execution_closure.py']
    compile_errors: dict[str, str] = {}
    for rel in compile_targets:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception as exc:  # pragma: no cover
            compile_errors[rel] = str(exc)
    payload = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "phase_ids": PHASE_IDS,
        "phase_count": len(PHASE_IDS),
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "phase40_bundle_source_mutation_performed": True,
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
