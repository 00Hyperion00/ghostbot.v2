from __future__ import annotations

import json
import py_compile
from pathlib import Path

REQUIRED_FILES = ['README_APPLY_4B436644_PHASE44_BUNDLE.txt', 'docs/PHASE44_NO_ORDER_SOAK_EVIDENCE_ACCEPTANCE_BUNDLE_4B436644.md', 'src/tradebot/__init__.py', 'src/tradebot/paper_sandbox_phase44_common.py', 'tests/test_phase44_no_order_soak_evidence_acceptance_bundle_4B436644.py', 'tools/apply_4B436644_phase44_no_order_soak_evidence_acceptance_bundle.py', 'tools/check_4B436644_phase44_no_order_soak_evidence_acceptance_bundle.py', 'tools/run_4B436644_phase44_no_order_soak_evidence_acceptance_bundle.py', 'tools/rollback_4B436644_phase44_no_order_soak_evidence_acceptance_bundle.py', 'README_APPLY_4B436644A.txt', 'docs/PAPER_SANDBOX_NO_ORDER_SOAK_EVIDENCE_ACCEPTANCE_REVIEW_4B436644A.md', 'src/tradebot/paper_sandbox_no_order_soak_evidence_acceptance_review.py', 'tests/test_paper_sandbox_no_order_soak_evidence_acceptance_review_4B436644A.py', 'tools/apply_4B436644A_paper_sandbox_no_order_soak_evidence_acceptance_review.py', 'tools/check_4B436644A_paper_sandbox_no_order_soak_evidence_acceptance_review.py', 'tools/run_4B436644A_paper_sandbox_no_order_soak_evidence_acceptance_review.py', 'tools/rollback_4B436644A_paper_sandbox_no_order_soak_evidence_acceptance_review.py', 'README_APPLY_4B436644B.txt', 'docs/PAPER_SANDBOX_EXTERNAL_EVIDENCE_MANIFEST_CONTRACT_4B436644B.md', 'src/tradebot/paper_sandbox_external_evidence_manifest_contract.py', 'tests/test_paper_sandbox_external_evidence_manifest_contract_4B436644B.py', 'tools/apply_4B436644B_paper_sandbox_external_evidence_manifest_contract.py', 'tools/check_4B436644B_paper_sandbox_external_evidence_manifest_contract.py', 'tools/run_4B436644B_paper_sandbox_external_evidence_manifest_contract.py', 'tools/rollback_4B436644B_paper_sandbox_external_evidence_manifest_contract.py', 'README_APPLY_4B436644C.txt', 'docs/PAPER_SANDBOX_RUNTIME_PRESENCE_EVIDENCE_ACCEPTANCE_CRITERIA_4B436644C.md', 'src/tradebot/paper_sandbox_runtime_presence_evidence_acceptance_criteria.py', 'tests/test_paper_sandbox_runtime_presence_evidence_acceptance_criteria_4B436644C.py', 'tools/apply_4B436644C_paper_sandbox_runtime_presence_evidence_acceptance_criteria.py', 'tools/check_4B436644C_paper_sandbox_runtime_presence_evidence_acceptance_criteria.py', 'tools/run_4B436644C_paper_sandbox_runtime_presence_evidence_acceptance_criteria.py', 'tools/rollback_4B436644C_paper_sandbox_runtime_presence_evidence_acceptance_criteria.py', 'README_APPLY_4B436644D.txt', 'docs/PAPER_SANDBOX_HEALTH_EVIDENCE_ACCEPTANCE_CRITERIA_4B436644D.md', 'src/tradebot/paper_sandbox_health_evidence_acceptance_criteria.py', 'tests/test_paper_sandbox_health_evidence_acceptance_criteria_4B436644D.py', 'tools/apply_4B436644D_paper_sandbox_health_evidence_acceptance_criteria.py', 'tools/check_4B436644D_paper_sandbox_health_evidence_acceptance_criteria.py', 'tools/run_4B436644D_paper_sandbox_health_evidence_acceptance_criteria.py', 'tools/rollback_4B436644D_paper_sandbox_health_evidence_acceptance_criteria.py', 'README_APPLY_4B436644E.txt', 'docs/PAPER_SANDBOX_METRICS_EVIDENCE_ACCEPTANCE_CRITERIA_4B436644E.md', 'src/tradebot/paper_sandbox_metrics_evidence_acceptance_criteria.py', 'tests/test_paper_sandbox_metrics_evidence_acceptance_criteria_4B436644E.py', 'tools/apply_4B436644E_paper_sandbox_metrics_evidence_acceptance_criteria.py', 'tools/check_4B436644E_paper_sandbox_metrics_evidence_acceptance_criteria.py', 'tools/run_4B436644E_paper_sandbox_metrics_evidence_acceptance_criteria.py', 'tools/rollback_4B436644E_paper_sandbox_metrics_evidence_acceptance_criteria.py', 'README_APPLY_4B436644F.txt', 'docs/PAPER_SANDBOX_INCIDENT_BUDGET_ACCEPTANCE_CRITERIA_4B436644F.md', 'src/tradebot/paper_sandbox_incident_budget_acceptance_criteria.py', 'tests/test_paper_sandbox_incident_budget_acceptance_criteria_4B436644F.py', 'tools/apply_4B436644F_paper_sandbox_incident_budget_acceptance_criteria.py', 'tools/check_4B436644F_paper_sandbox_incident_budget_acceptance_criteria.py', 'tools/run_4B436644F_paper_sandbox_incident_budget_acceptance_criteria.py', 'tools/rollback_4B436644F_paper_sandbox_incident_budget_acceptance_criteria.py', 'README_APPLY_4B436644G.txt', 'docs/PAPER_SANDBOX_ZERO_ORDER_INVARIANT_ACCEPTANCE_CRITERIA_4B436644G.md', 'src/tradebot/paper_sandbox_zero_order_invariant_acceptance_criteria.py', 'tests/test_paper_sandbox_zero_order_invariant_acceptance_criteria_4B436644G.py', 'tools/apply_4B436644G_paper_sandbox_zero_order_invariant_acceptance_criteria.py', 'tools/check_4B436644G_paper_sandbox_zero_order_invariant_acceptance_criteria.py', 'tools/run_4B436644G_paper_sandbox_zero_order_invariant_acceptance_criteria.py', 'tools/rollback_4B436644G_paper_sandbox_zero_order_invariant_acceptance_criteria.py', 'README_APPLY_4B436644H.txt', 'docs/PAPER_SANDBOX_NO_ORDER_SOAK_ACCEPTANCE_DECISION_GATE_4B436644H.md', 'src/tradebot/paper_sandbox_no_order_soak_acceptance_decision_gate.py', 'tests/test_paper_sandbox_no_order_soak_acceptance_decision_gate_4B436644H.py', 'tools/apply_4B436644H_paper_sandbox_no_order_soak_acceptance_decision_gate.py', 'tools/check_4B436644H_paper_sandbox_no_order_soak_acceptance_decision_gate.py', 'tools/run_4B436644H_paper_sandbox_no_order_soak_acceptance_decision_gate.py', 'tools/rollback_4B436644H_paper_sandbox_no_order_soak_acceptance_decision_gate.py', 'README_APPLY_4B436644I.txt', 'docs/PAPER_SANDBOX_NO_ORDER_SOAK_EVIDENCE_ACCEPTANCE_CLOSURE_4B436644I.md', 'src/tradebot/paper_sandbox_no_order_soak_evidence_acceptance_closure.py', 'tests/test_paper_sandbox_no_order_soak_evidence_acceptance_closure_4B436644I.py', 'tools/apply_4B436644I_paper_sandbox_no_order_soak_evidence_acceptance_closure.py', 'tools/check_4B436644I_paper_sandbox_no_order_soak_evidence_acceptance_closure.py', 'tools/run_4B436644I_paper_sandbox_no_order_soak_evidence_acceptance_closure.py', 'tools/rollback_4B436644I_paper_sandbox_no_order_soak_evidence_acceptance_closure.py']


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
        "patch_id": "4B436644",
        "patch_name": "Phase 44 No-Order Soak Evidence Acceptance Bundle",
        "patch_version": "4B.4.3.6.6.44",
        "phase_count": 9,
        "phase_ids": ['4B436644A', '4B436644B', '4B436644C', '4B436644D', '4B436644E', '4B436644F', '4B436644G', '4B436644H', '4B436644I'],
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "phase44_bundle_source_mutation_performed": True,
        "runtime_start_performed": False,
        "runtime_process_start_performed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "soak_evidence_accepted_by_patch": False,
        "evidence_manifest_accepted_by_patch": False,
        "runtime_presence_evidence_accepted_by_patch": False,
        "health_evidence_accepted_by_patch": False,
        "metrics_evidence_accepted_by_patch": False,
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
