from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_operator_approval_ledger import (
    APPROVAL_PHRASE_REQUIRED,
    READY_DECISION,
    OperatorApprovalEvidence,
    build_report,
    evaluate_operator_approval_ledger,
)


def _write_source_38c_ready(root: Path) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "4B436638C_paper_sandbox_dry_run_runtime_harness_20260705T122325Z_ready.json"
    payload = {
        "patch_id": "4B436638C",
        "patch_version": "4B.4.3.6.6.38C",
        "patch_name": "Paper Sandbox Dry-Run Runtime Harness",
        "status": "READY",
        "decision": "PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_READY_LOCAL_DRY_RUN_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED",
        "approved_for_paper_sandbox_dry_run_harness": True,
        "paper_sandbox_dry_run_runtime_harness_ready": True,
        "phase_38_planning_only": True,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "network_order_submit_allowed": False,
        "order_submit_performed": False,
        "runtime_start_performed": False,
        "source_38b_safety_violation_count": 0,
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_report_from_source_38c(tmp_path: Path) -> None:
    _write_source_38c_ready(tmp_path)
    report = build_report(repo_root=tmp_path, reports_dir=tmp_path / "reports" / "recovery", write_reports=False)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_38c_status"] == "SOURCE_38C_READY"
    assert report["approved_for_paper_sandbox_operator_approval_ledger"] is True


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(repo_root=tmp_path, reports_dir=tmp_path / "reports" / "recovery", write_reports=False)
    assert report["ok"] is False
    assert report["status"] == "NOT_READY"
    assert report["source_38c_status"] == "SOURCE_38C_MISSING"
    assert report["approved_for_paper_transition"] is False
    assert report["order_submit_performed"] is False


def test_approval_evidence_denies_missing_and_invalid_phrase() -> None:
    missing = evaluate_operator_approval_ledger(
        OperatorApprovalEvidence(None, "operator", "Operator", "reviewer", "20260705T000000Z", "source.json")
    )
    assert missing.result == "DENY_TYPED_APPROVAL_EVIDENCE_REQUIRED"
    assert missing.runtime_start_allowed is False

    invalid = evaluate_operator_approval_ledger(
        OperatorApprovalEvidence("APPROVE", "operator", "Operator", "reviewer", "20260705T000000Z", "source.json")
    )
    assert invalid.result == "DENY_TYPED_APPROVAL_EVIDENCE_MISMATCH"
    assert invalid.network_order_submit_allowed is False


def test_approval_evidence_requires_operator_identity() -> None:
    missing_id = evaluate_operator_approval_ledger(
        OperatorApprovalEvidence(APPROVAL_PHRASE_REQUIRED, None, "Operator", "reviewer", "20260705T000000Z", "source.json")
    )
    assert missing_id.result == "DENY_OPERATOR_IDENTITY_REQUIRED"

    missing_name = evaluate_operator_approval_ledger(
        OperatorApprovalEvidence(APPROVAL_PHRASE_REQUIRED, "operator", None, "reviewer", "20260705T000000Z", "source.json")
    )
    assert missing_name.result == "DENY_OPERATOR_NAME_REQUIRED"

    missing_role = evaluate_operator_approval_ledger(
        OperatorApprovalEvidence(APPROVAL_PHRASE_REQUIRED, "operator", "Operator", None, "20260705T000000Z", "source.json")
    )
    assert missing_role.result == "DENY_OPERATOR_ROLE_REQUIRED"


def test_valid_approval_accepted_for_review_only() -> None:
    result = evaluate_operator_approval_ledger(
        OperatorApprovalEvidence(
            APPROVAL_PHRASE_REQUIRED,
            "operator.local.review",
            "Operator Review",
            "paper_sandbox_reviewer",
            "20260705T000000Z",
            "source.json",
        )
    )
    assert result.accepted_for_review is True
    assert result.approval_valid is True
    assert result.runtime_start_allowed is False
    assert result.paper_order_submit_allowed is False
    assert result.network_order_submit_allowed is False
    assert result.exchange_submit_allowed is False


def test_ready_report_safety_and_counts(tmp_path: Path) -> None:
    _write_source_38c_ready(tmp_path)
    report = build_report(repo_root=tmp_path, reports_dir=tmp_path / "reports" / "recovery", write_reports=False)
    assert report["operator_approval_ledger_rule_count"] == 9
    assert report["operator_approval_ledger_ready_count"] == 9
    assert report["operator_approval_ledger_probe_count"] == 12
    assert report["operator_approval_ledger_probe_passed_count"] == 12
    assert report["paper_sandbox_operator_approval_ledger_gate_check_count"] == 32
    assert report["paper_sandbox_operator_approval_ledger_gate_ready_count"] == 32
    assert report["final_safety_violation_count"] == 0


def test_no_runtime_no_network_order_guard(tmp_path: Path) -> None:
    _write_source_38c_ready(tmp_path)
    report = build_report(repo_root=tmp_path, reports_dir=tmp_path / "reports" / "recovery", write_reports=False)
    assert report["no_runtime_start_no_network_order_guard_complete"] is True
    assert report["paper_runtime_start_performed"] is False
    assert report["paper_order_submit_performed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["network_request_performed"] is False
    assert report["signed_request_performed"] is False


def test_write_reports_creates_canonical_artifacts(tmp_path: Path) -> None:
    _write_source_38c_ready(tmp_path)
    report = build_report(repo_root=tmp_path, reports_dir=tmp_path / "reports" / "recovery", write_reports=True)
    for key in [
        "operator_approval_ledger_policy_path",
        "operator_approval_ledger_probe_path",
        "no_runtime_start_no_network_order_guard_path",
        "paper_sandbox_operator_approval_ledger_gate_path",
        "report_path",
    ]:
        assert report[key]
        assert Path(report[key]).exists()
