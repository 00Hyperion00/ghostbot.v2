from __future__ import annotations

from pathlib import Path

from tradebot.release_audit_pytest_collection_hygiene import (
    DECISION,
    FINAL_PHASE_DECISION,
    PYTEST_INI_CONTENT,
    SAFETY_LOCKS,
    build_release_audit_snapshot,
    discover_legacy_collection_directories,
    verify_pytest_collection_config,
)


def test_phase61_pytest_ini_content_isolates_legacy_collection_dirs() -> None:
    assert "testpaths" in PYTEST_INI_CONTENT
    assert "tests" in PYTEST_INI_CONTENT
    assert "_patch_backup*" in PYTEST_INI_CONTENT
    assert "_patch_payload*" in PYTEST_INI_CONTENT
    assert "legacy_patches" in PYTEST_INI_CONTENT
    assert "--import-mode=importlib" in PYTEST_INI_CONTENT
    assert "--ignore-glob=tools/_patch_backup_*" in PYTEST_INI_CONTENT
    assert "--ignore-glob=tools/_patch_payload_*" in PYTEST_INI_CONTENT


def test_phase61_snapshot_preserves_all_trading_safety_locks(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "pytest.ini").write_text(PYTEST_INI_CONTENT, encoding="utf-8")
    snapshot = build_release_audit_snapshot(tmp_path)
    assert snapshot["ok"] is True
    assert snapshot["status"] == "READY"
    assert snapshot["phase_61_closed"] is True
    assert snapshot["decision"] == DECISION
    assert snapshot["final_phase_decision"] == FINAL_PHASE_DECISION
    assert snapshot["final_safety_violation_count"] == 0
    assert snapshot["next_phase_unlock_allowed"] is False
    assert snapshot["manual_governance_required_for_any_live_action"] is True
    for key in SAFETY_LOCKS:
        assert snapshot[key] is False


def test_phase61_detects_but_excludes_legacy_collection_dirs(tmp_path: Path) -> None:
    (tmp_path / "tools" / "_patch_backup_legacy" / "tests").mkdir(parents=True)
    (tmp_path / "tools" / "_patch_payload_legacy").mkdir(parents=True)
    (tmp_path / "legacy_patches").mkdir()
    findings = discover_legacy_collection_directories(tmp_path)
    paths = {finding.path for finding in findings}
    assert "tools/_patch_backup_legacy" in paths
    assert "tools/_patch_payload_legacy" in paths
    assert "legacy_patches" in paths
    assert all(finding.excluded_by_pytest_config for finding in findings)


def test_phase61_blocks_when_pytest_config_missing(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    status = verify_pytest_collection_config(tmp_path)
    assert status["pytest_ini_present"] is False
    assert status["canonical_test_discovery_configured"] is False
    snapshot = build_release_audit_snapshot(tmp_path)
    assert snapshot["ok"] is False
    assert snapshot["status"] == "BLOCKED"
    assert snapshot["phase_61_closed"] is False
