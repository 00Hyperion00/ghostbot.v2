from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_local_runtime_health_evidence import (
    NEXT_PHASE,
    READY_DECISION,
    SOURCE_DECISION,
    build_report,
)


def write_source_38f(reports_dir: Path, **overrides: object) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "status": "READY",
        "decision": SOURCE_DECISION,
        "paper_sandbox_local_runtime_activation_harness_ready": True,
        "approved_for_paper_sandbox_local_runtime_activation_harness": True,
        "paper_transition_blocked": True,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "paper_runtime_start_performed": False,
        "runtime_start_performed": False,
        "network_order_submit_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
    }
    payload.update(overrides)
    path = reports_dir / "4B436638F_paper_sandbox_local_runtime_activation_harness_20260705T124332Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_report_from_38f_source(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38f(reports_dir)
    report = build_report(reports_dir)
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_38f_status"] == "SOURCE_38F_READY"
    assert report["paper_sandbox_local_runtime_health_evidence_ready"] is True


def test_local_health_contract_is_static_no_runtime(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38f(reports_dir)
    report = build_report(reports_dir)
    assert report["local_health_evidence_contract_complete"] is True
    assert report["local_health_evidence_contract_locked"] is True
    assert report["local_health_evidence_contract_rule_count"] == 11
    assert report["local_health_evidence_contract_ready_count"] == 11
    assert report["local_health_snapshot_static_only"] is True
    assert report["runtime_process_status"] == "NOT_STARTED_BY_38G"
    assert report["runtime_health_probe_forbidden_in_38g"] is True


def test_health_probe_all_passed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38f(reports_dir)
    report = build_report(reports_dir)
    assert report["paper_sandbox_local_runtime_health_evidence_probe_complete"] is True
    assert report["paper_sandbox_local_runtime_health_evidence_probe_count"] == 15
    assert report["paper_sandbox_local_runtime_health_evidence_probe_passed_count"] == 15


def test_no_runtime_process_or_order_side_effects(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38f(reports_dir)
    report = build_report(reports_dir)
    assert report["runtime_start_performed"] is False
    assert report["runtime_process_started"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["runtime_health_probe_performed"] is False
    assert report["paper_order_submit_performed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["network_request_performed"] is False


def test_live_exchange_private_api_remain_locked(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38f(reports_dir)
    report = build_report(reports_dir)
    assert report["approved_for_live_real"] is False
    assert report["live_environment_enabled"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["exchange_submit_performed"] is False
    assert report["signed_request_performed"] is False
    assert report["private_api_access_allowed"] is False
    assert report["private_account_read_performed"] is False


def test_gate_counts_and_next_phase_locked(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38f(reports_dir)
    report = build_report(reports_dir)
    assert report["paper_sandbox_local_runtime_health_evidence_gate_complete"] is True
    assert report["paper_sandbox_local_runtime_health_evidence_gate_check_count"] == 30
    assert report["paper_sandbox_local_runtime_health_evidence_gate_ready_count"] == 30
    assert report["next_phase"] == NEXT_PHASE
    assert report["next_phase_unlock_allowed"] is False
    assert report["transition_to_next_phase_performed"] is False


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(tmp_path / "missing")
    assert report["status"] == "NOT_READY"
    assert report["source_38f_status"] == "SOURCE_38F_MISSING"
    assert report["paper_sandbox_local_runtime_health_evidence_ready"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["approved_for_live_real"] is False


def test_source_with_runtime_start_fails_closed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38f(reports_dir, runtime_start_performed=True)
    report = build_report(reports_dir)
    assert report["status"] == "NOT_READY"
    assert report["source_38f_status"] == "SOURCE_38F_NOT_READY"
    assert any("runtime_start_performed" in item for item in report["errors"])
    assert report["network_order_submit_performed"] is False


def test_run_writes_artifacts(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38f(reports_dir)
    report = build_report(reports_dir, write_artifacts=True)
    assert report["status"] == "READY"
    assert report["report_path"] is not None
    assert Path(str(report["report_path"])).exists()
    assert Path(str(report["local_health_evidence_contract_path"])).exists()
    assert Path(str(report["local_health_snapshot_path"])).exists()
    assert Path(str(report["paper_sandbox_local_runtime_health_evidence_gate_path"])).exists()
