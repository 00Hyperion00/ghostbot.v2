from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_observation_metrics_gate import (
    NEXT_PHASE,
    READY_DECISION,
    SOURCE_DECISION,
    build_report,
)


def write_source_38g(reports_dir: Path, **overrides: object) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "status": "READY",
        "decision": SOURCE_DECISION,
        "paper_sandbox_local_runtime_health_evidence_ready": True,
        "approved_for_paper_sandbox_local_runtime_health_evidence": True,
        "paper_transition_blocked": True,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "runtime_process_started": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "network_order_submit_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
    }
    payload.update(overrides)
    path = reports_dir / "4B436638G_paper_sandbox_local_runtime_health_evidence_20260705T125039Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_report_from_38g_source(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38g(reports_dir)
    report = build_report(reports_dir)
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_38g_status"] == "SOURCE_38G_READY"
    assert report["paper_sandbox_observation_metrics_gate_ready"] is True


def test_static_observation_contract_is_no_runtime_no_collection(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38g(reports_dir)
    report = build_report(reports_dir)
    assert report["static_observation_metrics_contract_complete"] is True
    assert report["static_observation_metrics_contract_locked"] is True
    assert report["static_observation_metrics_contract_rule_count"] == 12
    assert report["static_observation_metrics_contract_ready_count"] == 12
    assert report["static_observation_metrics_only"] is True
    assert report["observation_metrics_collection_performed"] is False
    assert report["network_market_data_collection_performed"] is False


def test_observation_snapshot_counts_are_static(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38g(reports_dir)
    report = build_report(reports_dir)
    assert report["static_observation_metrics_snapshot_complete"] is True
    assert report["static_observation_metrics_snapshot_ready"] is True
    assert report["observation_metric_item_count"] == 11
    assert report["observation_metric_ready_count"] == 11
    assert report["observation_runtime_sample_count"] == 0
    assert report["observation_static_metric_count"] == 11


def test_probe_all_passed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38g(reports_dir)
    report = build_report(reports_dir)
    assert report["paper_sandbox_observation_metrics_gate_probe_complete"] is True
    assert report["paper_sandbox_observation_metrics_gate_probe_count"] == 17
    assert report["paper_sandbox_observation_metrics_gate_probe_passed_count"] == 17


def test_no_runtime_process_or_order_side_effects(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38g(reports_dir)
    report = build_report(reports_dir)
    assert report["runtime_start_performed"] is False
    assert report["runtime_process_started"] is False
    assert report["runtime_health_probe_performed"] is False
    assert report["paper_order_submit_performed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["network_request_performed"] is False


def test_live_exchange_private_api_remain_locked(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38g(reports_dir)
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
    write_source_38g(reports_dir)
    report = build_report(reports_dir)
    assert report["paper_sandbox_observation_metrics_gate_check_complete"] is True
    assert report["paper_sandbox_observation_metrics_gate_check_count"] == 32
    assert report["paper_sandbox_observation_metrics_gate_ready_count"] == 32
    assert report["next_phase"] == NEXT_PHASE
    assert report["next_phase_unlock_allowed"] is False
    assert report["transition_to_next_phase_performed"] is False



def test_source_selection_prefers_main_ready_report_over_newer_gate_artifact(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    ready_path = write_source_38g(reports_dir)
    gate_path = reports_dir / "4B436638G_paper_sandbox_local_runtime_health_evidence_gate_20990101T000000Z.json"
    gate_path.write_text(json.dumps({"gate_name": "paper_sandbox_local_runtime_health_evidence_gate"}), encoding="utf-8")
    report = build_report(reports_dir)
    assert report["status"] == "READY"
    assert report["source_38g_status"] == "SOURCE_38G_READY"
    assert report["source_38g_report"] == str(ready_path)
    assert "_gate_" not in str(report["source_38g_report"])

def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(tmp_path / "missing")
    assert report["status"] == "NOT_READY"
    assert report["source_38g_status"] == "SOURCE_38G_MISSING"
    assert report["paper_sandbox_observation_metrics_gate_ready"] is False
    assert report["runtime_start_performed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["approved_for_live_real"] is False


def test_source_with_runtime_start_fails_closed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38g(reports_dir, runtime_start_performed=True)
    report = build_report(reports_dir)
    assert report["status"] == "NOT_READY"
    assert report["source_38g_status"] == "SOURCE_38G_NOT_READY"
    assert any("runtime_start_performed" in item for item in report["errors"])
    assert report["network_order_submit_performed"] is False


def test_run_writes_artifacts(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    write_source_38g(reports_dir)
    report = build_report(reports_dir, write_artifacts=True)
    assert report["status"] == "READY"
    assert report["report_path"] is not None
    assert Path(str(report["report_path"])).exists()
    assert Path(str(report["static_observation_metrics_contract_path"])).exists()
    assert Path(str(report["static_observation_metrics_snapshot_path"])).exists()
    assert Path(str(report["paper_sandbox_observation_metrics_gate_path"])).exists()
