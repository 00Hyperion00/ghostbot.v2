
from __future__ import annotations

import json
from pathlib import Path

from tradebot.canonical_evidence_phase_hygiene import (
    READY_DECISION,
    build_canonical_evidence_phase_hygiene,
    check_canonical_evidence_phase_hygiene,
    run_canonical_evidence_phase_hygiene,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_dirty_repo(root: Path) -> None:
    for dirname in ("src/tradebot", "tools", "tests", "docs", "reports/production_hardening"):
        (root / dirname).mkdir(parents=True, exist_ok=True)
    _write(root / "pyproject.toml", "[project]\nname='x'\n")
    _write(root / "README.md", "# x\n")
    _write(root / "src/tradebot/__init__.py", "")
    _write(root / "tools/apply_4B436629A_demo.py", "# apply\n")
    _write(root / "tools/check_4B436629A_demo.py", "# check\n")
    _write(root / "tools/run_4B436629A_demo.py", "# run\n")
    _write(root / "tools/rollback_4B436629A_demo.py", "# rollback\n")
    _write(root / "tests/test_demo_4B436629A.py", "def test_demo(): assert True\n")
    _write(root / "docs/DEMO_4B436629A.md", "# demo\n")
    _write(root / "tools/__pycache__/apply_4B436629A_demo.cpython-314.pyc", "bytecode-ish\n")
    _write(root / "tools/_patch_backup_4B436629A/tools/apply_4B436629A_demo.py", "# backup\n")
    _write(root / "tools/_patch_payload_4B436629A/tools/apply_4B436629A_demo.py", "# payload\n")
    _write(root / "tools/legacy_patches_4B436620/apply_4B436620a_old.py", "# legacy\n")
    _write(
        root / "reports/production_hardening/4B436629A_demo_20260101T000000Z_ready.json",
        json.dumps({"status": "READY"}),
    )
    _write(
        root / "reports/production_hardening/4B436629A_demo_20260102T000000Z_not_ready.json",
        json.dumps({"status": "NOT_READY"}),
    )
    _write(
        root / "reports/production_hardening/4B436629A_demo_20260103T000000Z_snapshot.json",
        json.dumps({"kind": "snapshot"}),
    )
    _write(
        root / "reports/production_hardening/4B436629A_demo_20260104T000000Z_approval_required.json",
        json.dumps({"status": "APPROVAL_REQUIRED"}),
    )
    _write(root / "reports/production_hardening/4B436629A_bad_evidence_20260105T000000Z.json", "{bad json")


def test_phase_hygiene_ignores_pycache_backup_payload_and_legacy(tmp_path: Path) -> None:
    _write_dirty_repo(tmp_path)

    report = build_canonical_evidence_phase_hygiene(tmp_path)

    assert report.status == "READY"
    assert report.decision == READY_DECISION
    assert report.phase_hygiene_inventory.complete is True
    assert report.phase_hygiene_inventory.phase_count >= 1
    assert report.phase_hygiene_inventory.ignored_noise_count >= 4
    categories = {item.category for item in report.phase_hygiene_inventory.ignored_noise_sample}
    assert "__pycache__" in categories
    assert "_patch_backup" in categories
    assert "_patch_payload" in categories
    assert "legacy_patches" in categories
    assert report.safety_snapshot.approved_for_live_real is False
    assert report.safety_snapshot.exchange_submit_performed is False


def test_evidence_index_and_bad_ledger_classify_reports(tmp_path: Path) -> None:
    _write_dirty_repo(tmp_path)

    report = build_canonical_evidence_phase_hygiene(tmp_path)

    assert report.canonical_evidence_index.complete is True
    assert report.canonical_evidence_index.ready_count == 1
    assert report.canonical_evidence_index.not_ready_count == 1
    assert report.canonical_evidence_index.approval_required_count == 1
    assert report.canonical_evidence_index.snapshot_count == 1
    assert report.canonical_evidence_index.malformed_json_count == 1
    assert report.bad_evidence_ledger.bad_evidence_count >= 2
    assert report.bad_evidence_ledger.malformed_json_count == 1
    assert report.bad_evidence_ledger.approval_required_count == 1


def test_run_writes_three_reports_and_check_is_safe(tmp_path: Path) -> None:
    _write_dirty_repo(tmp_path)

    report, paths = run_canonical_evidence_phase_hygiene(tmp_path, tmp_path / "reports" / "recovery")
    check = check_canonical_evidence_phase_hygiene(tmp_path)

    assert report.status == "READY"
    assert set(paths) == {"hygiene_report", "canonical_evidence_index", "bad_evidence_ledger"}
    assert all(path.is_file() for path in paths.values())
    assert check["ok"] is True
    assert check["approved_for_live_real"] is False
    assert check["approved_for_exchange_submit"] is False
    assert check["trading_action_performed"] is False
    assert check["training_performed"] is False
    assert check["reload_performed"] is False
