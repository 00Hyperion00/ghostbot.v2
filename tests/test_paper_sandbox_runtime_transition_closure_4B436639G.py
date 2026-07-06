from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_runtime_transition_closure import (
    READY_DECISION,
    REQUIRED_SOURCE_FLAGS,
    build_report,
    find_latest_source_report,
)


def write_source_report(reports_dir: Path, *, overrides: dict[str, object] | None = None, name_suffix: str = "ready") -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(REQUIRED_SOURCE_FLAGS)
    payload.update({
        "runtime_start_command_template": "python -m tradebot.paper_runtime_entry --mode paper-sandbox --config config/paper_sandbox.runtime.json --runtime-lock runtime/paper_sandbox_runtime.lock --no-network-order --no-live --no-exchange-submit",
        "final_safety_violations": [],
    })
    if overrides:
        payload.update(overrides)
    path = reports_dir / f"4B436639F_paper_sandbox_observation_runtime_metrics_20260706T121656Z_{name_suffix}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_ready_report_from_valid_39f_source(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    source = write_source_report(reports)
    report = build_report(reports)
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_39f_status"] == "SOURCE_39F_READY"
    assert report["source_39f_report"] == str(source)
    assert report["final_safety_violation_count"] == 0


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(tmp_path / "reports" / "recovery")
    assert report["status"] == "NOT_READY"
    assert report["source_39f_status"] == "SOURCE_39F_MISSING"
    assert report["approved_for_paper_sandbox_runtime_transition_closure"] is False
    assert report["runtime_start_command_executed"] is False
    assert report["network_order_submit_performed"] is False


def test_not_ready_source_fails_closed(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports, overrides={"status": "NOT_READY"})
    report = build_report(reports)
    assert report["status"] == "NOT_READY"
    assert report["source_39f_status"] == "SOURCE_39F_NOT_READY"
    assert report["approved_for_paper_runtime_start"] is False


def test_selector_ignores_artifacts(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    main = write_source_report(reports)
    artifact = reports / "4B436639F_paper_sandbox_observation_runtime_metrics_gate_20260706T121657Z_ready.json"
    artifact.write_text(json.dumps(dict(REQUIRED_SOURCE_FLAGS)), encoding="utf-8")
    selected = find_latest_source_report(reports)
    assert selected == main


def test_transition_closure_flags(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["paper_sandbox_runtime_transition_closure_complete"] is True
    assert report["paper_sandbox_runtime_transition_closure_locked"] is True
    assert report["paper_sandbox_runtime_transition_closure_ready"] is True
    assert report["runtime_transition_closure_complete"] is True
    assert report["runtime_transition_closure_locked"] is True
    assert report["runtime_transition_closure_ready"] is True
    assert report["runtime_transition_closure_only"] is True
    assert report["runtime_transition_closed"] is True
    assert report["phase_39_runtime_transition_closed"] is True
    assert report["runtime_transition_closure_contract_rule_count"] == 15
    assert report["runtime_transition_closure_contract_ready_count"] == 15


def test_runtime_network_live_exchange_remain_locked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["approved_for_paper_runtime_start"] is False
    assert report["paper_runtime_start_allowed"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["runtime_process_started"] is False
    assert report["runtime_start_performed"] is False
    assert report["runtime_start_command_executed"] is False
    assert report["network_order_submit_allowed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["exchange_submit_performed"] is False


def test_metrics_and_health_not_performed(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["observation_runtime_metrics_collection_performed"] is False
    assert report["runtime_metrics_collection_performed"] is False
    assert report["runtime_health_endpoint_called"] is False
    assert report["runtime_health_probe_performed"] is False
    assert report["runtime_health_probe_deferred_to_future_runtime"] is True


def test_probe_and_gate_counts_are_locked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["paper_sandbox_runtime_transition_closure_probe_count"] == 20
    assert report["paper_sandbox_runtime_transition_closure_probe_passed_count"] == 20
    assert report["paper_sandbox_runtime_transition_closure_check_count"] == 25
    assert report["paper_sandbox_runtime_transition_closure_ready_count"] == 25


def test_write_artifacts_creates_ready_report(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports, write_artifacts=True)
    assert report["status"] == "READY"
    assert report["report_path"] is not None
    assert Path(report["report_path"]).exists()
    assert Path(report["runtime_transition_closure_contract_path"]).exists()
    assert Path(report["runtime_transition_closure_summary_path"]).exists()


def test_next_phase_not_auto_unlocked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["next_phase"] == "4B.4.3.6.6.40A"
    assert report["next_phase_unlock_allowed"] is False
    assert report["next_phase_unlock_performed"] is False
    assert report["transition_to_next_phase_performed"] is False
