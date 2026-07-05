from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_transition_final_approval_closure import (
    APPROVAL_PHRASE,
    READY_DECISION,
    SOURCE_DECISION,
    build_report,
    find_latest_source_report,
)


def _write_source_38h(reports_dir: Path, *, ready: bool = True, artifact: bool = False) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    if artifact:
        name = "4B436638H_paper_sandbox_observation_metrics_gate_20990101T000000Z.json"
    else:
        suffix = "ready" if ready else "not_ready"
        name = f"4B436638H_paper_sandbox_observation_metrics_gate_20990101T000001Z_{suffix}.json"
    data = {
        "status": "READY" if ready else "NOT_READY",
        "decision": SOURCE_DECISION if ready else "NOT_READY_DECISION",
        "paper_sandbox_observation_metrics_gate_ready": ready,
        "approved_for_paper_sandbox_observation_metrics_gate": ready,
        "paper_transition_blocked": True,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "runtime_process_started": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "observation_metrics_collection_performed": False,
        "network_market_data_collection_performed": False,
        "network_order_submit_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "final_safety_violation_count": 0 if ready else 1,
        "final_safety_violations": [] if ready else ["not_ready"],
    }
    path = reports_dir / name
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_source_report_selection_prefers_main_38h_ready_report(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    artifact = _write_source_38h(reports_dir, ready=True, artifact=True)
    ready = _write_source_38h(reports_dir, ready=True, artifact=False)

    selected = find_latest_source_report(reports_dir)

    assert selected == ready
    assert selected != artifact
    assert selected is not None
    assert selected.name.endswith("_ready.json")


def test_ready_report_from_valid_38h_source(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    source = _write_source_38h(reports_dir, ready=True)

    report = build_report(reports_dir)

    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_38h_status"] == "SOURCE_38H_READY"
    assert report["source_38h_report"] == str(source)
    assert report["source_38h_complete"] is True
    assert report["source_38h_safety_violation_count"] == 0
    assert report["paper_transition_final_approval_closure_ready"] is True
    assert report["paper_transition_final_approval_closure_gate_ready_count"] == report["paper_transition_final_approval_closure_gate_check_count"]


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(tmp_path / "reports" / "recovery")

    assert report["ok"] is False
    assert report["status"] == "NOT_READY"
    assert report["source_38h_status"] == "SOURCE_38H_MISSING"
    assert report["paper_transition_final_approval_closure_ready"] is False
    assert report["approved_for_paper_transition"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["network_order_submit_performed"] is False


def test_not_ready_source_fails_closed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_38h(reports_dir, ready=False)

    report = build_report(reports_dir)

    assert report["status"] == "NOT_READY"
    assert report["source_38h_status"] == "SOURCE_38H_MISSING"
    assert report["approved_for_paper_transition"] is False
    assert report["paper_transition_blocked"] is True


def test_final_operator_approval_contract_requires_explicit_evidence(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_38h(reports_dir, ready=True)

    report = build_report(reports_dir)

    assert report["explicit_operator_approval_required"] is True
    assert report["operator_identity_required"] is True
    assert report["operator_id_required"] is True
    assert report["operator_name_required"] is True
    assert report["operator_role_required"] is True
    assert report["operator_approval_timestamp_required"] is True
    assert report["source_report_required"] is True
    assert report["paper_transition_final_approval_phrase_required"] == APPROVAL_PHRASE
    assert report["explicit_operator_approval_contract_rule_count"] == 12
    assert report["explicit_operator_approval_contract_ready_count"] == 12


def test_final_approval_probe_denies_runtime_network_and_transition(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_38h(reports_dir, ready=True)

    report = build_report(reports_dir)

    assert report["paper_transition_final_approval_closure_probe_complete"] is True
    assert report["paper_transition_final_approval_closure_probe_count"] == 18
    assert report["paper_transition_final_approval_closure_probe_passed_count"] == 18
    assert report["typed_final_approval_missing_denied"] is True
    assert report["typed_final_approval_invalid_denied"] is True
    assert report["operator_identity_missing_denied"] is True
    assert report["valid_final_approval_evidence_accepted_for_review"] is True
    assert report["valid_final_approval_evidence_runtime_denied_no_submit"] is True
    assert report["valid_final_approval_evidence_network_order_denied"] is True
    assert report["valid_final_approval_evidence_transition_denied_without_separate_action"] is True


def test_no_runtime_process_network_order_live_or_exchange_submit(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_38h(reports_dir, ready=True)

    report = build_report(reports_dir)

    assert report["paper_transition_approval_performed"] is False
    assert report["approved_for_paper_transition"] is False
    assert report["paper_transition_blocked"] is True
    assert report["paper_transition_ready"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["runtime_process_started"] is False
    assert report["runtime_start_performed"] is False
    assert report["runtime_health_probe_performed"] is False
    assert report["paper_order_submit_performed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["network_request_performed"] is False
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["exchange_submit_performed"] is False
    assert report["signed_request_performed"] is False
    assert report["private_api_access_allowed"] is False


def test_next_phase_not_auto_unlocked(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_38h(reports_dir, ready=True)

    report = build_report(reports_dir)

    assert report["next_phase"] == "4B.4.3.6.6.39A"
    assert report["next_phase_unlock_allowed"] is False
    assert report["next_phase_unlock_performed"] is False
    assert report["transition_to_next_phase_performed"] is False


def test_write_artifacts_creates_ready_report_and_supporting_evidence(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_38h(reports_dir, ready=True)

    report = build_report(reports_dir, write_artifacts=True)

    assert report["status"] == "READY"
    assert report["report_path"] is not None
    assert Path(report["report_path"]).exists()
    assert report["explicit_operator_approval_contract_path"] is not None
    assert Path(report["explicit_operator_approval_contract_path"]).exists()
    assert report["paper_transition_final_approval_closure_probe_path"] is not None
    assert Path(report["paper_transition_final_approval_closure_probe_path"]).exists()
    assert report["paper_transition_final_approval_closure_gate_path"] is not None
    assert Path(report["paper_transition_final_approval_closure_gate_path"]).exists()


def test_report_has_no_destructive_or_git_mutations(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_38h(reports_dir, ready=True)

    report = build_report(reports_dir)

    for key in (
        "git_add_performed",
        "git_commit_performed",
        "git_tag_performed",
        "git_push_performed",
        "file_delete_performed",
        "file_move_performed",
        "report_delete_performed",
        "report_move_performed",
        "report_archive_performed",
        "report_dedup_performed",
        "destructive_cleanup_performed",
    ):
        assert report[key] is False
