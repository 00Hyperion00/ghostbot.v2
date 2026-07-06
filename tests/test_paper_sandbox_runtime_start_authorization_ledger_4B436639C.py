from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.paper_sandbox_runtime_start_authorization_ledger import (
    AUTHORIZATION_PHRASE,
    AUTHORIZATION_SCOPE,
    READY_DECISION,
    REQUIRED_SOURCE_FLAGS,
    build_report,
    evaluate_runtime_start_authorization,
    find_latest_source_report,
)


def write_source_report(reports_dir: Path, *, overrides: dict[str, object] | None = None, name_suffix: str = "ready") -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(REQUIRED_SOURCE_FLAGS)
    payload.update(
        {
            "runtime_start_command_template": "python -m tradebot.paper_runtime_entry --mode paper-sandbox --config config/paper_sandbox.runtime.json --runtime-lock runtime/paper_sandbox_runtime.lock --no-network-order --no-live --no-exchange-submit",
            "phase_39_command_contract_review": True,
            "final_safety_violations": [],
        }
    )
    if overrides:
        payload.update(overrides)
    path = reports_dir / f"4B436639B_paper_sandbox_runtime_start_command_contract_20260706T000000Z_{name_suffix}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_ready_report_from_valid_39b_source(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    source = write_source_report(reports)
    report = build_report(reports)
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_39b_report"] == str(source)
    assert report["source_39b_status"] == "SOURCE_39B_READY"
    assert report["final_safety_violation_count"] == 0


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(tmp_path / "reports" / "recovery")
    assert report["status"] == "NOT_READY"
    assert report["ok"] is False
    assert report["source_39b_status"] == "SOURCE_39B_MISSING"
    assert report["runtime_start_command_executed"] is False
    assert report["network_order_submit_performed"] is False


def test_not_ready_source_fails_closed(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports, overrides={"status": "NOT_READY"}, name_suffix="ready")
    report = build_report(reports)
    assert report["status"] == "NOT_READY"
    assert report["source_39b_status"] == "SOURCE_39B_NOT_READY"
    assert report["approved_for_paper_sandbox_runtime_start_authorization_ledger"] is False


def test_latest_main_ready_report_selection_ignores_artifacts(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    main = write_source_report(reports)
    artifact = reports / "4B436639B_runtime_start_command_contract_20260706T000001Z.json"
    artifact.write_text(json.dumps({"status": "READY"}), encoding="utf-8")
    selected = find_latest_source_report(reports)
    assert selected == main


def test_valid_authorization_is_review_only(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    sample = report["runtime_start_operator_authorization_valid_evidence_sample"]
    assert sample["approval_phrase"] == AUTHORIZATION_PHRASE
    assert sample["approval_scope"] == AUTHORIZATION_SCOPE
    assert sample["runtime_start_allowed"] is False
    assert sample["runtime_start_command_executed"] is False
    assert sample["network_order_submit_allowed"] is False


def test_invalid_authorization_phrase_denied(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    source_report = report["source_report"]
    source = type("Source", (), {"report_path": source_report})()
    result = evaluate_runtime_start_authorization({"approval_phrase": "BAD"}, source)  # type: ignore[arg-type]
    assert result["result"] == "DENY_RUNTIME_START_AUTHORIZATION_PHRASE_MISMATCH"
    assert result["runtime_start_allowed"] is False


def test_probe_counts_are_locked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["paper_sandbox_runtime_start_authorization_ledger_probe_count"] == 23
    assert report["paper_sandbox_runtime_start_authorization_ledger_probe_passed_count"] == 23
    assert report["paper_sandbox_runtime_start_authorization_ledger_gate_check_count"] == 39
    assert report["paper_sandbox_runtime_start_authorization_ledger_gate_ready_count"] == 39


def test_runtime_and_network_remain_locked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["runtime_start_command_execution_allowed"] is False
    assert report["runtime_start_command_executed"] is False
    assert report["runtime_process_started"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["network_order_submit_allowed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False


def test_write_artifacts_creates_ready_report(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports, write_artifacts=True)
    assert report["status"] == "READY"
    assert report["report_path"] is not None
    assert Path(report["report_path"]).exists()
    assert Path(report["explicit_runtime_start_authorization_ledger_path"]).exists()
    assert Path(report["runtime_start_operator_authorization_sample_path"]).exists()


def test_command_execution_is_not_approved_by_authorization_ledger(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["approved_for_paper_runtime_start"] is False
    assert report["paper_runtime_start_authorization_performed"] is False
    assert report["paper_runtime_start_authorization_ready"] is False
    assert report["runtime_start_command_execution_performed"] is False
