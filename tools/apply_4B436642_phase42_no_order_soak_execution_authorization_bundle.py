from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436642"
PATCH_VERSION = "4B.4.3.6.6.42"
PATCH_NAME = "Phase 42 No-Order Soak Execution Authorization Bundle"
PHASE_IDS = ['4B436642A', '4B436642B', '4B436642C', '4B436642D', '4B436642E', '4B436642F', '4B436642G', '4B436642H', '4B436642I']
REQUIRED_FILES = ['README_APPLY_4B436642_PHASE42_BUNDLE.txt', 'docs/PHASE42_NO_ORDER_SOAK_EXECUTION_AUTHORIZATION_BUNDLE_4B436642.md', 'src/tradebot/__init__.py', 'src/tradebot/paper_sandbox_phase42_common.py', 'tests/test_phase42_no_order_soak_execution_authorization_bundle_4B436642.py', 'tools/apply_4B436642_phase42_no_order_soak_execution_authorization_bundle.py', 'tools/check_4B436642_phase42_no_order_soak_execution_authorization_bundle.py', 'tools/run_4B436642_phase42_no_order_soak_execution_authorization_bundle.py', 'tools/rollback_4B436642_phase42_no_order_soak_execution_authorization_bundle.py', 'README_APPLY_4B436642A.txt', 'docs/PAPER_SANDBOX_NO_ORDER_SOAK_EXECUTION_AUTHORIZATION_REVIEW_4B436642A.md', 'src/tradebot/paper_sandbox_no_order_soak_execution_authorization_review.py', 'tests/test_paper_sandbox_no_order_soak_execution_authorization_review_4B436642A.py', 'tools/apply_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py', 'tools/check_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py', 'tools/run_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py', 'tools/rollback_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py', 'README_APPLY_4B436642B.txt', 'docs/PAPER_SANDBOX_TYPED_NO_ORDER_SOAK_EXECUTION_APPROVAL_4B436642B.md', 'src/tradebot/paper_sandbox_typed_no_order_soak_execution_approval.py', 'tests/test_paper_sandbox_typed_no_order_soak_execution_approval_4B436642B.py', 'tools/apply_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py', 'tools/check_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py', 'tools/run_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py', 'tools/rollback_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py', 'README_APPLY_4B436642C.txt', 'docs/PAPER_SANDBOX_EXTERNAL_RUNTIME_SOAK_START_HANDOFF_CONTRACT_4B436642C.md', 'src/tradebot/paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'tests/test_paper_sandbox_external_runtime_soak_start_handoff_contract_4B436642C.py', 'tools/apply_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'tools/check_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'tools/run_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'tools/rollback_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'README_APPLY_4B436642D.txt', 'docs/PAPER_SANDBOX_RUNTIME_PRESENCE_EVIDENCE_ACCEPTANCE_GATE_4B436642D.md', 'src/tradebot/paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'tests/test_paper_sandbox_runtime_presence_evidence_acceptance_gate_4B436642D.py', 'tools/apply_4B436642D_paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'tools/check_4B436642D_paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'tools/run_4B436642D_paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'tools/rollback_4B436642D_paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'README_APPLY_4B436642E.txt', 'docs/PAPER_SANDBOX_LOCALHOST_HEALTH_PROBE_EVIDENCE_GATE_4B436642E.md', 'src/tradebot/paper_sandbox_localhost_health_probe_evidence_gate.py', 'tests/test_paper_sandbox_localhost_health_probe_evidence_gate_4B436642E.py', 'tools/apply_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py', 'tools/check_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py', 'tools/run_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py', 'tools/rollback_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py', 'README_APPLY_4B436642F.txt', 'docs/PAPER_SANDBOX_NO_ORDER_RUNTIME_METRICS_EVIDENCE_COLLECTION_GATE_4B436642F.md', 'src/tradebot/paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'tests/test_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate_4B436642F.py', 'tools/apply_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'tools/check_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'tools/run_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'tools/rollback_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'README_APPLY_4B436642G.txt', 'docs/PAPER_SANDBOX_SOAK_INCIDENT_BUDGET_ENFORCEMENT_REVIEW_4B436642G.md', 'src/tradebot/paper_sandbox_soak_incident_budget_enforcement_review.py', 'tests/test_paper_sandbox_soak_incident_budget_enforcement_review_4B436642G.py', 'tools/apply_4B436642G_paper_sandbox_soak_incident_budget_enforcement_review.py', 'tools/check_4B436642G_paper_sandbox_soak_incident_budget_enforcement_review.py', 'tools/run_4B436642G_paper_sandbox_soak_incident_budget_enforcement_review.py', 'tools/rollback_4B436642G_paper_sandbox_soak_incident_budget_enforcement_review.py', 'README_APPLY_4B436642H.txt', 'docs/PAPER_SANDBOX_NO_ORDER_SOAK_EXECUTION_ACCEPTANCE_REVIEW_4B436642H.md', 'src/tradebot/paper_sandbox_no_order_soak_execution_acceptance_review.py', 'tests/test_paper_sandbox_no_order_soak_execution_acceptance_review_4B436642H.py', 'tools/apply_4B436642H_paper_sandbox_no_order_soak_execution_acceptance_review.py', 'tools/check_4B436642H_paper_sandbox_no_order_soak_execution_acceptance_review.py', 'tools/run_4B436642H_paper_sandbox_no_order_soak_execution_acceptance_review.py', 'tools/rollback_4B436642H_paper_sandbox_no_order_soak_execution_acceptance_review.py', 'README_APPLY_4B436642I.txt', 'docs/PAPER_SANDBOX_NO_ORDER_SOAK_EXECUTION_CLOSURE_4B436642I.md', 'src/tradebot/paper_sandbox_no_order_soak_execution_closure.py', 'tests/test_paper_sandbox_no_order_soak_execution_closure_4B436642I.py', 'tools/apply_4B436642I_paper_sandbox_no_order_soak_execution_closure.py', 'tools/check_4B436642I_paper_sandbox_no_order_soak_execution_closure.py', 'tools/run_4B436642I_paper_sandbox_no_order_soak_execution_closure.py', 'tools/rollback_4B436642I_paper_sandbox_no_order_soak_execution_closure.py']
COMPILE_TARGETS = ['src/tradebot/__init__.py', 'src/tradebot/paper_sandbox_phase42_common.py', 'tests/test_phase42_no_order_soak_execution_authorization_bundle_4B436642.py', 'tools/apply_4B436642_phase42_no_order_soak_execution_authorization_bundle.py', 'tools/check_4B436642_phase42_no_order_soak_execution_authorization_bundle.py', 'tools/run_4B436642_phase42_no_order_soak_execution_authorization_bundle.py', 'tools/rollback_4B436642_phase42_no_order_soak_execution_authorization_bundle.py', 'src/tradebot/paper_sandbox_no_order_soak_execution_authorization_review.py', 'tests/test_paper_sandbox_no_order_soak_execution_authorization_review_4B436642A.py', 'tools/apply_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py', 'tools/check_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py', 'tools/run_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py', 'tools/rollback_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py', 'src/tradebot/paper_sandbox_typed_no_order_soak_execution_approval.py', 'tests/test_paper_sandbox_typed_no_order_soak_execution_approval_4B436642B.py', 'tools/apply_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py', 'tools/check_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py', 'tools/run_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py', 'tools/rollback_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py', 'src/tradebot/paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'tests/test_paper_sandbox_external_runtime_soak_start_handoff_contract_4B436642C.py', 'tools/apply_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'tools/check_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'tools/run_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'tools/rollback_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py', 'src/tradebot/paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'tests/test_paper_sandbox_runtime_presence_evidence_acceptance_gate_4B436642D.py', 'tools/apply_4B436642D_paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'tools/check_4B436642D_paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'tools/run_4B436642D_paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'tools/rollback_4B436642D_paper_sandbox_runtime_presence_evidence_acceptance_gate.py', 'src/tradebot/paper_sandbox_localhost_health_probe_evidence_gate.py', 'tests/test_paper_sandbox_localhost_health_probe_evidence_gate_4B436642E.py', 'tools/apply_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py', 'tools/check_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py', 'tools/run_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py', 'tools/rollback_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py', 'src/tradebot/paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'tests/test_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate_4B436642F.py', 'tools/apply_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'tools/check_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'tools/run_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'tools/rollback_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py', 'src/tradebot/paper_sandbox_soak_incident_budget_enforcement_review.py', 'tests/test_paper_sandbox_soak_incident_budget_enforcement_review_4B436642G.py', 'tools/apply_4B436642G_paper_sandbox_soak_incident_budget_enforcement_review.py', 'tools/check_4B436642G_paper_sandbox_soak_incident_budget_enforcement_review.py', 'tools/run_4B436642G_paper_sandbox_soak_incident_budget_enforcement_review.py', 'tools/rollback_4B436642G_paper_sandbox_soak_incident_budget_enforcement_review.py', 'src/tradebot/paper_sandbox_no_order_soak_execution_acceptance_review.py', 'tests/test_paper_sandbox_no_order_soak_execution_acceptance_review_4B436642H.py', 'tools/apply_4B436642H_paper_sandbox_no_order_soak_execution_acceptance_review.py', 'tools/check_4B436642H_paper_sandbox_no_order_soak_execution_acceptance_review.py', 'tools/run_4B436642H_paper_sandbox_no_order_soak_execution_acceptance_review.py', 'tools/rollback_4B436642H_paper_sandbox_no_order_soak_execution_acceptance_review.py', 'src/tradebot/paper_sandbox_no_order_soak_execution_closure.py', 'tests/test_paper_sandbox_no_order_soak_execution_closure_4B436642I.py', 'tools/apply_4B436642I_paper_sandbox_no_order_soak_execution_closure.py', 'tools/check_4B436642I_paper_sandbox_no_order_soak_execution_closure.py', 'tools/run_4B436642I_paper_sandbox_no_order_soak_execution_closure.py', 'tools/rollback_4B436642I_paper_sandbox_no_order_soak_execution_closure.py']


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in COMPILE_TARGETS:
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
        "phase42_bundle_source_mutation_performed": True,
        "runtime_start_performed": False,
        "runtime_process_start_performed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "soak_execution_performed_by_patch": False,
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
