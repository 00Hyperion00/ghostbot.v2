from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.hyp005_r1_canonical_epoch_contract import (
    CANONICAL_R1_REPORTS_DIR,
    CANONICAL_R1_TASK_NAME,
    HYP005_R1_CANONICAL_EPOCH_HARDENING_VERSION,
    LEGACY_R1_REPORTS_DIR,
    LEGACY_R1_TASK_NAME,
    is_utc_artifact_filename,
    is_utc_artifact_stamp,
    resolve_active_reports_dir,
    utc_artifact_stamp,
)

ROOT = Path(__file__).resolve().parents[1]


def test_25aeh5_contract_constants_and_utc_stamp() -> None:
    assert HYP005_R1_CANONICAL_EPOCH_HARDENING_VERSION == "4B.4.3.6.6.25AE-H5"
    assert CANONICAL_R1_REPORTS_DIR == Path("reports") / "hyp005_r1_canonical"
    assert LEGACY_R1_REPORTS_DIR == Path("reports") / "hyp005_r1_isolated"
    assert CANONICAL_R1_TASK_NAME == "TradeBot_HYP005_R1_Canonical_NoOrderShadowCollection"
    assert LEGACY_R1_TASK_NAME == "TradeBot_HYP005_R1_NoOrderShadowCollection"
    stamp = utc_artifact_stamp()
    assert is_utc_artifact_stamp(stamp)
    assert is_utc_artifact_filename(f"artifact_{stamp}.json")
    assert not is_utc_artifact_filename("artifact_20260610_102956.json")


def test_25aeh5_reports_dir_resolver_prefers_canonical_with_legacy_fallback(tmp_path: Path) -> None:
    legacy = tmp_path / LEGACY_R1_REPORTS_DIR
    legacy.mkdir(parents=True)
    assert resolve_active_reports_dir(tmp_path) == legacy.resolve()
    canonical = tmp_path / CANONICAL_R1_REPORTS_DIR
    canonical.mkdir(parents=True)
    assert resolve_active_reports_dir(tmp_path) == canonical.resolve()


def test_25aeh5_active_tools_use_explicit_utc_stamps() -> None:
    logger = (ROOT / "tools/run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py").read_text(encoding="utf-8")
    orchestrator = (ROOT / "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py").read_text(encoding="utf-8")
    acceptance = (ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py").read_text(encoding="utf-8")
    audit = (ROOT / "tools/run_hyp005_shadow_operator_runbook_4B436625Y.py").read_text(encoding="utf-8")
    assert "stamp = utc_artifact_stamp()" in logger
    assert "ts = utc_artifact_stamp()" in orchestrator
    assert "stamp = utc_artifact_stamp()" in acceptance
    assert "ts = utc_artifact_stamp()" in audit


def test_25aeh5_acceptance_source_attribution_separates_metadata_from_ledgers() -> None:
    acceptance = (ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py").read_text(encoding="utf-8")
    assert "collection reports are metadata, never observation-ledger inputs" in acceptance
    assert 'report["ledger_input_paths"] = [str(path) for path in input_paths]' in acceptance
    assert 'report["source_collection_reports"] = len(collection_paths)' in acceptance
    assert 'paths.append(Path(raw))\n    for raw in args.collection_report_json' not in acceptance


def test_25aeh5_canonical_cycle_is_explicit_jsonl_fail_closed_dag() -> None:
    script = (ROOT / "tools/run_hyp005_r1_canonical_epoch_cycle_4B436625AEH5.ps1").read_text(encoding="utf-8")
    assert "reports\\hyp005_r1_canonical" in script
    assert '--ledger-jsonl "$($LatestLoggerLedgerJsonl.FullName)"' in script
    assert '--ledger-jsonl "$($LatestMergedLedgerJsonl.FullName)"' in script
    assert "HYP005_CANONICAL_25V_FAILED" in script
    assert "HYP005_CANONICAL_25X_FAILED" in script
    assert "HYP005_CANONICAL_25W_FAILED" in script
    assert "HYP005_CANONICAL_25Y_FAILED" in script
    assert script.index("run_hyp005_shadow_observation_logger") < script.index("run_hyp005_shadow_collection_orchestrator")
    assert script.index("run_hyp005_shadow_collection_orchestrator") < script.index("run_hyp005_shadow_acceptance_readiness")
    assert script.index("run_hyp005_shadow_acceptance_readiness") < script.index("run_hyp005_shadow_operator_runbook")


def test_25aeh5_registration_is_manual_and_preserves_legacy_disabled_guard() -> None:
    script = (ROOT / "tools/register_hyp005_r1_canonical_epoch_task_4B436625AEH5.ps1").read_text(encoding="utf-8")
    assert "Register-ScheduledTask" in script
    assert CANONICAL_R1_TASK_NAME in script
    assert LEGACY_R1_TASK_NAME in script
    assert "must remain Disabled" in script
    apply_text = (ROOT / "tools/apply_4B436625AE_H5_hyp005_r1_canonical_epoch_hardening.py").read_text(encoding="utf-8")
    assert "Register-ScheduledTask -TaskName" not in apply_text
    assert "subprocess.run" not in apply_text


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_h5_artifacts(reports: Path, *, stamp: str) -> None:
    reports.mkdir(parents=True)
    merged = reports / f"4B436625X_hyp005_shadow_merged_ledger_{stamp}.jsonl"
    merged.write_text(json.dumps({"observation_id": "HYP-005-BNBUSDT-4h-2026-06-05T040000Z"}) + "\n", encoding="utf-8")
    _write_json(reports / f"4B436625V_hyp005_shadow_observation_logger_{stamp}.json", {"decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY"})
    _write_json(reports / f"4B436625X_hyp005_shadow_collection_orchestrator_{stamp}.json", {"decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY"})
    _write_json(
        reports / f"4B436625W_hyp005_shadow_observation_acceptance_{stamp}.json",
        {
            "decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
            "source_ledgers": [str(merged)],
            "ledger_input_paths": [str(merged)],
            "collection_report_paths": [str(reports / f"4B436625X_hyp005_shadow_collection_orchestrator_{stamp}.json")],
            "source_collection_reports": 1,
        },
    )
    _write_json(
        reports / f"4B436625Y_hyp005_shadow_operator_daily_audit_{stamp}.json",
        {"source_ledgers": 1, "source_reports": 3, "approved_for_live_real": False},
    )


def test_25aeh5_checker_passes_for_utc_canonical_chain(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "hyp005_r1_canonical"
    _seed_h5_artifacts(reports, stamp="20260610_072956Z")
    checker = ROOT / "tools/check_hyp005_r1_canonical_epoch_hardening_4B436625AEH5.py"
    completed = subprocess.run(
        [sys.executable, str(checker), "--project-root", str(ROOT), "--reports-dir", str(reports), "--once-json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["utc_stamp_artifacts_ready"] is True
    assert payload["acceptance_source_attribution_ready"] is True
    assert payload["audit_source_attribution_ready"] is True
    assert payload["dashboard_source_alignment_ready"] is True
    assert payload["ok"] is True


def test_25aeh5_checker_blocks_non_utc_artifact_name(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "hyp005_r1_canonical"
    _seed_h5_artifacts(reports, stamp="20260610_102956")
    checker = ROOT / "tools/check_hyp005_r1_canonical_epoch_hardening_4B436625AEH5.py"
    completed = subprocess.run(
        [sys.executable, str(checker), "--project-root", str(ROOT), "--reports-dir", str(reports), "--once-json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["utc_stamp_artifacts_ready"] is False
    assert payload["ok"] is False


def test_25aeh5_cockpit_prefers_canonical_source_with_legacy_fallback() -> None:
    cockpit = (ROOT / "src/tradebot/operator_cockpit_v2_read_only.py").read_text(encoding="utf-8")
    assert 'OPERATOR_COCKPIT_V2_CANONICAL_EPOCH_HARDENING_VERSION = "4B.4.3.6.6.25AE-H5"' in cockpit
    assert "resolve_active_reports_dir(project_root)" in cockpit
    assert "resolve_active_reports_dir(root)" in cockpit
    assert "CANONICAL_R1_TASK_NAME" in cockpit
