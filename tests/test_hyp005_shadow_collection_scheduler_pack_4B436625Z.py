from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_shadow_collection_scheduler_pack import (
    HYP005_SCHEDULER_PACK_BLOCK,
    HYP005_SCHEDULER_PACK_READY,
    SchedulerPackRequest,
    build_hyp005_shadow_scheduler_pack_report,
    validate_25y_audit_for_scheduler_pack,
)


def _audit() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.25Y",
        "decision": "HYP005_SHADOW_OPERATOR_AUDIT_READY",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "selected_strategy_family": "long_liquidity_sweep_reversal",
        "no_order_operator_audit_only": True,
        "latest_logger_decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY",
        "latest_collection_decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY",
        "latest_acceptance_decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
        "shadow_observation_count": 0,
        "shadow_sample_target": 30,
        "paper_transition_ready": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "approved_for_training_candidate": False,
    }


def test_25z_builds_scheduler_pack_from_25y_audit(tmp_path: Path) -> None:
    request = SchedulerPackRequest(reports_dir=str(tmp_path), symbols=("BTCUSDT", "ETHUSDT"), run_every_hours=4)
    report = build_hyp005_shadow_scheduler_pack_report(
        operator_audit=_audit(),
        request=request,
        out_dir=tmp_path,
        timestamp="20260509_210000",
        review_ok=True,
    )
    assert report["decision"] == HYP005_SCHEDULER_PACK_READY
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    artifacts = report["artifacts"]
    assert artifacts
    cycle = Path(artifacts["shadow_cycle_ps1"])
    register = Path(artifacts["register_task_ps1"])
    xml = Path(artifacts["task_xml"])
    assert cycle.exists()
    assert register.exists()
    assert xml.exists()
    text = cycle.read_text(encoding="utf-8")
    assert "run_hyp005_shadow_observation_logger_4B436625V.py" in text
    assert "run_hyp005_shadow_collection_orchestrator_4B436625X.py" in text
    assert "run_hyp005_shadow_acceptance_readiness_4B436625W.py" in text
    assert "run_hyp005_shadow_operator_runbook_4B436625Y.py" in text
    assert "send orders" in text


def test_25z_blocks_without_review_ok(tmp_path: Path) -> None:
    report = build_hyp005_shadow_scheduler_pack_report(
        operator_audit=_audit(),
        out_dir=tmp_path,
        timestamp="20260509_210001",
        review_ok=False,
    )
    assert report["decision"] == HYP005_SCHEDULER_PACK_BLOCK
    assert "REVIEW_OK_REQUIRED" in report["reason_codes"]
    assert report["artifacts"] is None


def test_25z_blocks_unsafe_paper_approval() -> None:
    payload = _audit()
    payload["approved_for_paper_candidate"] = True
    reasons, _warnings = validate_25y_audit_for_scheduler_pack(payload)
    assert "UNSAFE_PAPER_APPROVAL_DETECTED" in reasons


def test_25z_task_registration_is_manual_only(tmp_path: Path) -> None:
    report = build_hyp005_shadow_scheduler_pack_report(
        operator_audit=_audit(),
        out_dir=tmp_path,
        timestamp="20260509_210002",
        review_ok=True,
    )
    register_text = Path(report["artifacts"]["register_task_ps1"]).read_text(encoding="utf-8")
    assert "Manual registration helper" in register_text
    assert "Register-ScheduledTask" in register_text
    assert report["windows_task_scheduler_manual_import_only"] is True
    assert report["post_requests_allowed"] is False


def test_tool_writes_report_and_scheduler_pack(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    audit_path = reports / "4B436625Y_hyp005_shadow_operator_daily_audit_20260509_180514.json"
    audit_path.write_text(json.dumps(_audit()), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_hyp005_shadow_collection_scheduler_pack_4B436625Z.py",
            "--input-json",
            str(audit_path),
            "--reports-dir",
            str(reports),
            "--out-dir",
            str(reports),
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "HYP005_SHADOW_SCHEDULER_PACK_READY" in result.stdout
    assert list(reports.glob("4B436625Z_hyp005_shadow_collection_scheduler_pack_*.json"))
    assert list(reports.glob("4B436625Z_hyp005_windows_task_scheduler_pack_*"))
