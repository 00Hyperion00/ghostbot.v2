from __future__ import annotations

import json
from pathlib import Path

from tradebot.evidence_retention_archive_policy import (
    READY_DECISION,
    build_evidence_retention_archive_policy_report,
    write_evidence_retention_archive_policy_report,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_repo(root: Path) -> None:
    (root / "src/tradebot").mkdir(parents=True, exist_ok=True)
    (root / "tools/_patch_backup_4B436633E_H1_20260101T000000Z").mkdir(parents=True, exist_ok=True)
    (root / "tools/_patch_backup_4B436633E_H1_20260101T000000Z/file.txt").write_text("backup", encoding="utf-8")
    (root / "tools/_patch_payload_4B436633E").mkdir(parents=True, exist_ok=True)
    (root / "tools/_patch_payload_4B436633E/payload.txt").write_text("payload", encoding="utf-8")
    (root / "tests/__pycache__").mkdir(parents=True, exist_ok=True)
    (root / "tests/__pycache__/x.pyc").write_bytes(b"cache")
    _write_json(
        root / "reports/recovery/4B436633E_status_conflict_resolver_20260702T111131Z_ready.json",
        {
            "status": "READY",
            "decision": "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE",
            "source_33d_complete": True,
            "status_conflict_resolution_complete": True,
            "unknown_evidence_triage_complete": True,
            "malformed_json_triage_complete": True,
            "unresolved_conflict_count": 0,
            "residual_unknown_count": 18,
        },
    )
    _write_json(root / "reports/recovery/4B436633E_status_conflict_resolver_20260702T110610Z_not_ready.json", {"status": "NOT_READY"})
    _write_json(root / "reports/recovery/4B436633E_unknown_evidence_classifier_ledger_20260702T111131Z.json", {"records": []})


def test_policy_report_ready(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    report = build_evidence_retention_archive_policy_report(tmp_path)
    assert report.status == "READY"
    assert report.decision == READY_DECISION
    assert report.source_33e.complete is True
    assert report.report_retention.complete is True
    assert report.backup_payload_archive_manifest.complete is True
    assert report.non_destructive_cleanup_plan.complete is True
    assert report.evidence_aging_ledger.complete is True
    assert report.safety_snapshot.exchange_submit_performed is False
    assert report.safety_snapshot.destructive_cleanup_performed is False


def test_policy_outputs_ledgers(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    report, paths = write_evidence_retention_archive_policy_report(tmp_path, tmp_path / "reports/recovery")
    assert report.status == "READY"
    for path in paths.values():
        assert Path(path).exists()
    assert "evidence_aging_ledger_path" in paths
    assert "non_destructive_cleanup_plan_path" in paths


def test_policy_not_ready_without_33e_source(tmp_path: Path) -> None:
    report = build_evidence_retention_archive_policy_report(tmp_path)
    assert report.status == "NOT_READY"
    assert report.source_33e.complete is False
    assert report.safety_snapshot.trading_action_performed is False
