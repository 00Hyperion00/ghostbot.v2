from __future__ import annotations

from pathlib import Path

from tradebot.research_hyp005_shadow_collection_scheduler_pack import (
    HYP005_SCHEDULER_PACK_READY,
    HYP005_SHADOW_SCHEDULER_PACK_HOTFIX_VERSION,
    SchedulerPackRequest,
    build_hyp005_shadow_scheduler_pack_report,
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


def test_25zh1_declares_hotfix_version() -> None:
    assert HYP005_SHADOW_SCHEDULER_PACK_HOTFIX_VERSION == "4B.4.3.6.6.25Z_H1"


def test_25zh1_register_script_avoids_unsupported_battery_parameters(tmp_path: Path) -> None:
    report = build_hyp005_shadow_scheduler_pack_report(
        operator_audit=_audit(),
        request=SchedulerPackRequest(reports_dir=str(tmp_path), run_every_hours=4),
        out_dir=tmp_path,
        timestamp="20260509_220000",
        review_ok=True,
    )
    register_text = Path(report["artifacts"]["register_task_ps1"]).read_text(encoding="utf-8")
    assert "New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable" in register_text
    assert "New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries" not in register_text
    assert "New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -DisallowStartIfOnBatteries" not in register_text
    assert "PSObject.Properties.Name" in register_text
    assert "DisallowStartIfOnBatteries" in register_text


def test_25zh1_cycle_script_resolves_project_root_from_reports_pack_dir(tmp_path: Path) -> None:
    report = build_hyp005_shadow_scheduler_pack_report(
        operator_audit=_audit(),
        request=SchedulerPackRequest(reports_dir=str(tmp_path), run_every_hours=4),
        out_dir=tmp_path,
        timestamp="20260509_220001",
        review_ok=True,
    )
    cycle_text = Path(report["artifacts"]["shadow_cycle_ps1"]).read_text(encoding="utf-8")
    assert "$ReportsDir = Split-Path -Parent $PackDir" in cycle_text
    assert "$ProjectRoot = Split-Path -Parent $ReportsDir" in cycle_text
    assert "Test-Path (Join-Path $ProjectRoot \"tools\")" in cycle_text
    assert "Set-Location $ProjectRoot" in cycle_text


def test_25zh1_scheduler_pack_still_ready_and_no_order(tmp_path: Path) -> None:
    report = build_hyp005_shadow_scheduler_pack_report(
        operator_audit=_audit(),
        request=SchedulerPackRequest(reports_dir=str(tmp_path), run_every_hours=4),
        out_dir=tmp_path,
        timestamp="20260509_220002",
        review_ok=True,
    )
    assert report["decision"] == HYP005_SCHEDULER_PACK_READY
    assert report["approved_for_scheduler_pack"] is True
    assert report["approved_for_paper_transition_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["post_requests_allowed"] is False
    assert report["order_actions_performed"] is False
