from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_r1_shadow_scheduler_regeneration_pack import (
    HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK,
    HYP005_R1_SHADOW_SCHEDULER_PACK_READY,
    build_hyp005_r1_shadow_scheduler_regeneration_pack_report,
)

REFINED = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
PRUNED = ["AVAXUSDT", "DOGEUSDT"]


def _plan() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.25AD",
        "decision": "HYP005_R1_REVALIDATION_PLANNING_READY",
        "refined_branch_id": "HYP-005-R1",
        "fresh_ledger_namespace": "HYP005_R1",
        "starting_unique_shadow_observation_count": 0,
        "shadow_sample_target": 30,
        "recommended_pruned_symbols": PRUNED,
        "recommended_refined_symbols": REFINED,
        "approved_for_next_scheduler_pack_patch": True,
        "approved_for_scheduler_regeneration": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "baseline_observations_reused_in_refined_branch": False,
        "refined_candidate_spec": {
            "symbols": REFINED,
            "symbols_arg": ",".join(REFINED),
            "excluded_symbols": PRUNED,
            "legacy_baseline_observation_reuse_allowed": False,
            "legacy_baseline_observations_reused": False,
        },
    }


def _candidate_spec() -> dict[str, object]:
    return {
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "entry_signal_definition": {"timeframe": "4h", "parameters": {"lookback_bars": 24, "hold_bars": 6}},
        "guardrails": {"no_order_shadow_only": True, "orders_allowed": False, "paper_trading_allowed": False, "live_trading_allowed": False},
    }


def _write_inputs(root: Path, plan: dict[str, object] | None = None) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    ad = root / "4B436625AD_hyp005_baseline_freeze_refined_revalidation_planning_20260602_072834.json"
    u = root / "4B436625U_hyp005_no_order_shadow_candidate_spec_20260509_175722.json"
    ad.write_text(json.dumps(plan if plan is not None else _plan()), encoding="utf-8")
    u.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    return ad, u


def test_25ae_valid_plan_builds_isolated_r1_scheduler_pack(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        tmp_path, out_dir=tmp_path, baseline_task_disabled_confirmed=True, review_ok=True, timestamp="20260602_080000"
    )
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_READY
    assert report["refined_symbols"] == sorted(REFINED)
    assert report["fresh_ledger_namespace"] == "HYP005_R1"
    assert report["starting_unique_shadow_observation_count"] == 0
    assert report["approved_for_scheduler_registration"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    artifacts = report["artifacts"]
    assert artifacts
    cycle = Path(artifacts["shadow_cycle_ps1"]).read_text(encoding="utf-8")
    assert 'reports\\hyp005_r1' in cycle
    assert 'ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT' in cycle
    assert '--reports-dir "$R1ReportsDir"' in cycle
    assert '--out-dir "$R1ReportsDir"' in cycle


def test_25ae_blocks_without_baseline_disabled_operator_ack(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(tmp_path, out_dir=tmp_path, review_ok=True)
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK
    assert "BASELINE_TASK_DISABLED_CONFIRMATION_REQUIRED" in report["blockers"]
    assert report["artifacts"] is None


def test_25ae_blocks_legacy_reuse_or_symbol_mismatch(tmp_path: Path) -> None:
    plan = _plan()
    plan["recommended_refined_symbols"] = [*REFINED, "DOGEUSDT"]
    spec = dict(plan["refined_candidate_spec"])
    spec["symbols"] = [*REFINED, "DOGEUSDT"]
    spec["legacy_baseline_observation_reuse_allowed"] = True
    plan["refined_candidate_spec"] = spec
    _write_inputs(tmp_path, plan)
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        tmp_path, out_dir=tmp_path, baseline_task_disabled_confirmed=True, review_ok=True
    )
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK
    assert "LEGACY_BASELINE_OBSERVATION_REUSE_NOT_EXPLICITLY_BLOCKED" in report["blockers"]
    assert "REFINED_EIGHT_SYMBOL_SET_MISMATCH" in report["blockers"]


def test_25ae_generated_register_script_checks_baseline_disabled_and_registers_r1_task(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        tmp_path, out_dir=tmp_path, baseline_task_disabled_confirmed=True, review_ok=True
    )
    script = Path(report["artifacts"]["register_task_ps1"]).read_text(encoding="utf-8")
    assert 'Get-ScheduledTask -TaskName $BaselineTaskName -ErrorAction Stop' in script
    assert '$BaselineTask.State -ne "Disabled"' in script
    assert 'TradeBot_HYP005_R1_NoOrderShadowCollection' in script
    assert 'New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable' in script
    assert 'Register-ScheduledTask' in script


def test_25ae_runtime_candidate_spec_forces_no_order_and_fresh_namespace(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        tmp_path, out_dir=tmp_path, baseline_task_disabled_confirmed=True, review_ok=True
    )
    spec = json.loads(Path(report["artifacts"]["r1_runtime_candidate_spec_json"]).read_text(encoding="utf-8"))
    assert spec["fresh_ledger_namespace"] == "HYP005_R1"
    assert spec["legacy_baseline_observation_reuse_allowed"] is False
    assert spec["starting_unique_shadow_observation_count"] == 0
    assert spec["symbols"] == sorted(REFINED)
    assert spec["guardrails"]["orders_allowed"] is False
    assert spec["guardrails"]["paper_trading_allowed"] is False
    assert spec["guardrails"]["live_trading_allowed"] is False
    assert spec["guardrails"]["post_requests_allowed"] is False


def test_25ae_tool_writes_report_and_pack(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    out = tmp_path / "out"
    _write_inputs(reports)
    project_root = Path(__file__).resolve().parents[1]
    tool = project_root / "tools" / "run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py"
    result = subprocess.run(
        [
            sys.executable,
            str(tool),
            "--reports-dir",
            str(reports),
            "--out-dir",
            str(out),
            "--baseline-task-disabled",
            "--review-ok",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "HYP005_R1_SHADOW_SCHEDULER_PACK_READY" in result.stdout
    assert list(out.glob("4B436625AE_hyp005_r1_shadow_scheduler_regeneration_pack_*.json"))
    assert list(out.glob("4B436625AE_hyp005_r1_windows_task_scheduler_pack_*"))
