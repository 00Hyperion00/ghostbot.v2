from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradebot.repo_hygiene_evidence_retention import evaluate

READY_SOURCE = {
    "status": "READY",
    "decision": "INSTALL_CONTRACT_LAUNCHER_ALIGNMENT_HOTFIX_READY_NO_SUBMIT_P0_1_CLOSED",
    "p0_install_contract_alignment_closed": True,
    "p0_install_contract_alignment_closed_by": "4B.4.3.6.6.37B-H1",
    "production_hardening_p0_1_ready": True,
    "p0_hardening_closed_gap_count_after_37b_h1": 1,
    "p0_hardening_open_gap_count_after_37b_h1": 9,
    "phase_37_planning_only": True,
    "network_request_performed": False,
    "exchange_submit_performed": False,
    "order_submit_performed": False,
}


def seed_source(root: Path, payload: dict[str, object] | None = None) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "4B436637B_H1_install_contract_launcher_alignment_hotfix_20260703T124527Z_ready.json"
    path.write_text(json.dumps(payload or READY_SOURCE), encoding="utf-8")
    return path


def test_ready_repo_hygiene_evidence_retention(tmp_path: Path) -> None:
    seed_source(tmp_path)
    (tmp_path / "tools" / "_patch_backup_4B436637B_H1_20260703T124518Z").mkdir(parents=True)
    payload = evaluate(tmp_path)
    assert payload["status"] == "READY"
    assert payload["decision"] == "REPO_HYGIENE_EVIDENCE_RETENTION_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_2_LOCKED"
    assert payload["canonical_reports_policy_complete"] is True
    assert payload["patch_backup_retention_guard_complete"] is True
    assert payload["p0_repo_hygiene_evidence_retention_closed"] is True
    assert payload["p0_hardening_closed_gap_count_after_37c"] == 2
    assert payload["p0_hardening_open_gap_count_after_37c"] == 8
    assert payload["repo_hygiene_cleanup_performed"] is False
    assert payload["report_delete_performed"] is False
    assert payload["archive_move_performed"] is False
    assert payload["network_request_performed"] is False
    assert payload["exchange_submit_performed"] is False


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    payload = evaluate(tmp_path)
    assert payload["status"] == "NOT_READY"
    assert payload["source_37b_h1_status"] == "SOURCE_37B_H1_MISSING"
    assert "SOURCE_37B_H1_READY_REPORT_NOT_FOUND" in payload["errors"]


def test_source_safety_violation_is_not_ready(tmp_path: Path) -> None:
    source = dict(READY_SOURCE)
    source["exchange_submit_performed"] = True
    seed_source(tmp_path, source)
    payload = evaluate(tmp_path)
    assert payload["status"] == "NOT_READY"
    assert payload["source_37b_h1_safety_violation_count"] == 1
    assert "SOURCE_37B_H1_SAFETY_VIOLATION" in payload["errors"]


def test_run_script_writes_reports_without_cleanup(tmp_path: Path) -> None:
    seed_source(tmp_path)
    script = ROOT / "tools" / "run_4B436637C_repo_hygiene_evidence_retention.py"
    result = subprocess.run(
        [sys.executable, str(script), "--repo-root", str(tmp_path), "--reports-dir", str(tmp_path / "reports" / "recovery"), "--once-json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "READY"
    assert Path(payload["report_path"]).exists()
    assert Path(payload["canonical_reports_policy_path"]).exists()
    assert Path(payload["patch_backup_retention_guard_path"]).exists()
    assert payload["file_delete_performed"] is False
    assert payload["destructive_cleanup_performed"] is False
