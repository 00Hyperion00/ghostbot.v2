from __future__ import annotations

import json
from pathlib import Path

from tradebot.evidence_retention_archive_policy import (
    READY_DECISION,
    build_evidence_retention_archive_policy_report,
    find_source_33e_status,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_source_33e_gate_accepts_nested_33e_run_report(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports/recovery/4B436633E_status_conflict_resolver_20260702T111131Z_ready.json",
        {
            "status": "READY",
            "decision": "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE",
            "source_gate": {"complete": True, "source_33d_runtime_safety_lockdown_complete": True},
            "status_conflict_summary": {"complete": True, "unresolved_conflict_count": 0},
            "unknown_evidence_summary": {"complete": True, "residual_unknown_count": 18},
            "malformed_json_summary": {"complete": True},
        },
    )
    source = find_source_33e_status(tmp_path)
    assert source.complete is True
    assert source.source_33d_complete is True
    assert source.status_conflict_resolution_complete is True
    assert source.unknown_evidence_triage_complete is True
    assert source.malformed_json_triage_complete is True
    assert source.unresolved_conflict_count == 0


def test_33f_ready_with_nested_33e_source(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports/recovery/4B436633E_status_conflict_resolver_20260702T111131Z_ready.json",
        {
            "status": "READY",
            "decision": "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE",
            "source_gate": {"complete": True},
            "status_conflict_summary": {"complete": True, "unresolved_conflict_count": 0},
            "unknown_evidence_summary": {"complete": True, "residual_unknown_count": 18},
            "malformed_json_summary": {"complete": True},
        },
    )
    _write_json(tmp_path / "reports/recovery/4B436633E_unknown_evidence_classifier_ledger_20260702T111131Z.json", {"records": []})
    (tmp_path / "tests/__pycache__").mkdir(parents=True)
    (tmp_path / "tests/__pycache__/x.pyc").write_bytes(b"cache")
    report = build_evidence_retention_archive_policy_report(tmp_path)
    assert report.status == "READY"
    assert report.decision == READY_DECISION
    assert report.source_33e.complete is True
    assert report.safety_snapshot.exchange_submit_performed is False
    assert report.safety_snapshot.destructive_cleanup_performed is False


def test_source_33e_gate_still_blocks_unresolved_conflict(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports/recovery/4B436633E_status_conflict_resolver_20260702T111131Z_ready.json",
        {
            "status": "READY",
            "decision": "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE",
            "source_gate": {"complete": True},
            "status_conflict_summary": {"complete": True, "unresolved_conflict_count": 1},
            "unknown_evidence_summary": {"complete": True},
            "malformed_json_summary": {"complete": True},
        },
    )
    source = find_source_33e_status(tmp_path)
    assert source.complete is False
    assert source.error == "source_33e_report_not_complete"
