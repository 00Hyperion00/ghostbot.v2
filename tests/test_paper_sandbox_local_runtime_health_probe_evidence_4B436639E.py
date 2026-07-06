from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_local_runtime_health_probe_evidence import (
    HEALTH_PROBE_ENDPOINT_TEMPLATE,
    READY_DECISION,
    REQUIRED_SOURCE_FLAGS,
    build_report,
    find_latest_source_report,
)


def write_source_report(reports_dir: Path, *, overrides: dict[str, object] | None = None, name_suffix: str = "ready") -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(REQUIRED_SOURCE_FLAGS)
    payload.update(
        {
            "runtime_start_command_template": "python -m tradebot.paper_runtime_entry --mode paper-sandbox --config config/paper_sandbox.runtime.json --runtime-lock runtime/paper_sandbox_runtime.lock --no-network-order --no-live --no-exchange-submit",
            "final_safety_violations": [],
        }
    )
    if overrides:
        payload.update(overrides)
    path = reports_dir / f"4B436639D_paper_sandbox_local_runtime_process_start_gate_20260706T100216Z_{name_suffix}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_ready_report_from_valid_39d_source(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    source = write_source_report(reports)
    report = build_report(reports)
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_39d_status"] == "SOURCE_39D_READY"
    assert report["source_39d_report"] == str(source)
    assert report["final_safety_violation_count"] == 0


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(tmp_path / "reports" / "recovery")
    assert report["status"] == "NOT_READY"
    assert report["source_39d_status"] == "SOURCE_39D_MISSING"
    assert report["runtime_health_endpoint_called"] is False
    assert report["runtime_process_started"] is False
    assert report["network_order_submit_performed"] is False


def test_not_ready_source_fails_closed(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports, overrides={"status": "NOT_READY"})
    report = build_report(reports)
    assert report["status"] == "NOT_READY"
    assert report["source_39d_status"] == "SOURCE_39D_NOT_READY"
    assert report["approved_for_paper_sandbox_local_runtime_health_probe_evidence"] is False


def test_latest_main_ready_report_selection_ignores_artifacts(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    main = write_source_report(reports)
    artifact = reports / "4B436639D_paper_sandbox_local_runtime_process_start_gate_probe_20260706T100216Z_ready.json"
    artifact.write_text(json.dumps({"status": "READY"}), encoding="utf-8")
    selected = find_latest_source_report(reports)
    assert selected == main


def test_health_probe_evidence_contract_declared_only(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["local_runtime_health_probe_evidence_contract_complete"] is True
    assert report["local_runtime_health_probe_evidence_contract_locked"] is True
    assert report["local_runtime_health_probe_evidence_contract_ready"] is True
    assert report["health_probe_evidence_contract_only"] is True
    assert report["health_probe_evidence_schema_declared"] is True
    assert report["health_probe_endpoint_template"] == HEALTH_PROBE_ENDPOINT_TEMPLATE
    assert report["health_probe_collection_deferred"] is True


def test_health_probe_not_called_and_runtime_not_started(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["runtime_process_status"] == "NOT_STARTED_BY_39E"
    assert report["runtime_process_started"] is False
    assert report["runtime_start_performed"] is False
    assert report["runtime_health_endpoint_called"] is False
    assert report["runtime_health_probe_performed"] is False
    assert report["health_probe_evidence_collection_performed"] is False


def test_probe_counts_are_locked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["paper_sandbox_local_runtime_health_probe_evidence_probe_count"] == 20
    assert report["paper_sandbox_local_runtime_health_probe_evidence_probe_passed_count"] == 20
    assert report["paper_sandbox_local_runtime_health_probe_evidence_check_count"] == 28
    assert report["paper_sandbox_local_runtime_health_probe_evidence_ready_count"] == 28


def test_network_live_exchange_remain_locked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["network_order_submit_allowed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["network_request_performed"] is False
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["exchange_submit_performed"] is False
    assert report["private_api_access_allowed"] is False


def test_write_artifacts_creates_ready_report(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports, write_artifacts=True)
    assert report["status"] == "READY"
    assert report["report_path"] is not None
    assert Path(report["report_path"]).exists()
    assert Path(report["local_runtime_health_probe_evidence_contract_path"]).exists()
    assert Path(report["health_probe_evidence_schema_path"]).exists()
    assert Path(report["future_health_probe_evidence_sample_path"]).exists()


def test_next_phase_not_auto_unlocked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["next_phase"] == "4B.4.3.6.6.39F"
    assert report["next_phase_unlock_allowed"] is False
    assert report["next_phase_unlock_performed"] is False
    assert report["transition_to_next_phase_performed"] is False
