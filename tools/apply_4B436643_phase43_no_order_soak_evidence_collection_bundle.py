from __future__ import annotations

import json
import py_compile
from pathlib import Path

REQUIRED_FILES = ['README_APPLY_4B436643_PHASE43_BUNDLE.txt', 'docs/PHASE43_NO_ORDER_SOAK_EVIDENCE_COLLECTION_BUNDLE_4B436643.md', 'src/tradebot/__init__.py', 'src/tradebot/paper_sandbox_phase43_common.py', 'tests/test_phase43_no_order_soak_evidence_collection_bundle_4B436643.py', 'tools/apply_4B436643_phase43_no_order_soak_evidence_collection_bundle.py', 'tools/check_4B436643_phase43_no_order_soak_evidence_collection_bundle.py', 'tools/run_4B436643_phase43_no_order_soak_evidence_collection_bundle.py', 'tools/rollback_4B436643_phase43_no_order_soak_evidence_collection_bundle.py', 'README_APPLY_4B436643A.txt', 'docs/PAPER_SANDBOX_NO_ORDER_SOAK_EVIDENCE_COLLECTION_REVIEW_4B436643A.md', 'src/tradebot/paper_sandbox_no_order_soak_evidence_collection_review.py', 'tests/test_paper_sandbox_no_order_soak_evidence_collection_review_4B436643A.py', 'tools/apply_4B436643A_paper_sandbox_no_order_soak_evidence_collection_review.py', 'tools/check_4B436643A_paper_sandbox_no_order_soak_evidence_collection_review.py', 'tools/run_4B436643A_paper_sandbox_no_order_soak_evidence_collection_review.py', 'tools/rollback_4B436643A_paper_sandbox_no_order_soak_evidence_collection_review.py', 'README_APPLY_4B436643B.txt', 'docs/PAPER_SANDBOX_EXTERNAL_RUNTIME_PRESENCE_EVIDENCE_COLLECTION_HANDOFF_4B436643B.md', 'src/tradebot/paper_sandbox_external_runtime_presence_evidence_collection_handoff.py', 'tests/test_paper_sandbox_external_runtime_presence_evidence_collection_handoff_4B436643B.py', 'tools/apply_4B436643B_paper_sandbox_external_runtime_presence_evidence_collection_handoff.py', 'tools/check_4B436643B_paper_sandbox_external_runtime_presence_evidence_collection_handoff.py', 'tools/run_4B436643B_paper_sandbox_external_runtime_presence_evidence_collection_handoff.py', 'tools/rollback_4B436643B_paper_sandbox_external_runtime_presence_evidence_collection_handoff.py', 'README_APPLY_4B436643C.txt', 'docs/PAPER_SANDBOX_LOCALHOST_HEALTH_EVIDENCE_COLLECTION_REVIEW_4B436643C.md', 'src/tradebot/paper_sandbox_localhost_health_evidence_collection_review.py', 'tests/test_paper_sandbox_localhost_health_evidence_collection_review_4B436643C.py', 'tools/apply_4B436643C_paper_sandbox_localhost_health_evidence_collection_review.py', 'tools/check_4B436643C_paper_sandbox_localhost_health_evidence_collection_review.py', 'tools/run_4B436643C_paper_sandbox_localhost_health_evidence_collection_review.py', 'tools/rollback_4B436643C_paper_sandbox_localhost_health_evidence_collection_review.py', 'README_APPLY_4B436643D.txt', 'docs/PAPER_SANDBOX_NO_ORDER_METRICS_EVIDENCE_COLLECTION_REVIEW_4B436643D.md', 'src/tradebot/paper_sandbox_no_order_metrics_evidence_collection_review.py', 'tests/test_paper_sandbox_no_order_metrics_evidence_collection_review_4B436643D.py', 'tools/apply_4B436643D_paper_sandbox_no_order_metrics_evidence_collection_review.py', 'tools/check_4B436643D_paper_sandbox_no_order_metrics_evidence_collection_review.py', 'tools/run_4B436643D_paper_sandbox_no_order_metrics_evidence_collection_review.py', 'tools/rollback_4B436643D_paper_sandbox_no_order_metrics_evidence_collection_review.py', 'README_APPLY_4B436643E.txt', 'docs/PAPER_SANDBOX_SOAK_WINDOW_EVIDENCE_SNAPSHOT_REVIEW_4B436643E.md', 'src/tradebot/paper_sandbox_soak_window_evidence_snapshot_review.py', 'tests/test_paper_sandbox_soak_window_evidence_snapshot_review_4B436643E.py', 'tools/apply_4B436643E_paper_sandbox_soak_window_evidence_snapshot_review.py', 'tools/check_4B436643E_paper_sandbox_soak_window_evidence_snapshot_review.py', 'tools/run_4B436643E_paper_sandbox_soak_window_evidence_snapshot_review.py', 'tools/rollback_4B436643E_paper_sandbox_soak_window_evidence_snapshot_review.py', 'README_APPLY_4B436643F.txt', 'docs/PAPER_SANDBOX_INCIDENT_BUDGET_EVIDENCE_REVIEW_4B436643F.md', 'src/tradebot/paper_sandbox_incident_budget_evidence_review.py', 'tests/test_paper_sandbox_incident_budget_evidence_review_4B436643F.py', 'tools/apply_4B436643F_paper_sandbox_incident_budget_evidence_review.py', 'tools/check_4B436643F_paper_sandbox_incident_budget_evidence_review.py', 'tools/run_4B436643F_paper_sandbox_incident_budget_evidence_review.py', 'tools/rollback_4B436643F_paper_sandbox_incident_budget_evidence_review.py', 'README_APPLY_4B436643G.txt', 'docs/PAPER_SANDBOX_ZERO_ORDER_INVARIANT_EVIDENCE_REVIEW_4B436643G.md', 'src/tradebot/paper_sandbox_zero_order_invariant_evidence_review.py', 'tests/test_paper_sandbox_zero_order_invariant_evidence_review_4B436643G.py', 'tools/apply_4B436643G_paper_sandbox_zero_order_invariant_evidence_review.py', 'tools/check_4B436643G_paper_sandbox_zero_order_invariant_evidence_review.py', 'tools/run_4B436643G_paper_sandbox_zero_order_invariant_evidence_review.py', 'tools/rollback_4B436643G_paper_sandbox_zero_order_invariant_evidence_review.py', 'README_APPLY_4B436643H.txt', 'docs/PAPER_SANDBOX_NO_ORDER_SOAK_EVIDENCE_ACCEPTANCE_GATE_4B436643H.md', 'src/tradebot/paper_sandbox_no_order_soak_evidence_acceptance_gate.py', 'tests/test_paper_sandbox_no_order_soak_evidence_acceptance_gate_4B436643H.py', 'tools/apply_4B436643H_paper_sandbox_no_order_soak_evidence_acceptance_gate.py', 'tools/check_4B436643H_paper_sandbox_no_order_soak_evidence_acceptance_gate.py', 'tools/run_4B436643H_paper_sandbox_no_order_soak_evidence_acceptance_gate.py', 'tools/rollback_4B436643H_paper_sandbox_no_order_soak_evidence_acceptance_gate.py', 'README_APPLY_4B436643I.txt', 'docs/PAPER_SANDBOX_NO_ORDER_SOAK_EVIDENCE_COLLECTION_CLOSURE_4B436643I.md', 'src/tradebot/paper_sandbox_no_order_soak_evidence_collection_closure.py', 'tests/test_paper_sandbox_no_order_soak_evidence_collection_closure_4B436643I.py', 'tools/apply_4B436643I_paper_sandbox_no_order_soak_evidence_collection_closure.py', 'tools/check_4B436643I_paper_sandbox_no_order_soak_evidence_collection_closure.py', 'tools/run_4B436643I_paper_sandbox_no_order_soak_evidence_collection_closure.py', 'tools/rollback_4B436643I_paper_sandbox_no_order_soak_evidence_collection_closure.py']


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in [path for path in REQUIRED_FILES if path.endswith('.py') and not path.startswith('tools/apply_') and not path.startswith('tools/rollback_')]:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception as exc:
            compile_errors[rel] = str(exc)
    payload = {
        "applied": not missing and not compile_errors,
        "patch_id": "4B436643",
        "patch_name": "Phase 43 No-Order Soak Evidence Collection Bundle",
        "patch_version": "4B.4.3.6.6.43",
        "phase_count": 9,
        "phase_ids": ['4B436643A', '4B436643B', '4B436643C', '4B436643D', '4B436643E', '4B436643F', '4B436643G', '4B436643H', '4B436643I'],
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "phase43_bundle_source_mutation_performed": True,
        "runtime_start_performed": False,
        "runtime_process_start_performed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "actual_evidence_collection_performed_by_patch": False,
        "runtime_presence_evidence_collected_by_patch": False,
        "health_evidence_collected_by_patch": False,
        "metrics_evidence_collected_by_patch": False,
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
