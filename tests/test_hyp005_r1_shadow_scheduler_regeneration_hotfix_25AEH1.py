from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_r1_shadow_scheduler_regeneration_pack import (
    HYP005_R1_SHADOW_SCHEDULER_HOTFIX_VERSION,
    HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK,
    HYP005_R1_SHADOW_SCHEDULER_PACK_READY,
    R1_SHADOW_SAMPLE_TARGET_VALIDATION_NORMALIZED,
    build_hyp005_r1_shadow_scheduler_regeneration_pack_report,
)

REFINED = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
PRUNED = ["AVAXUSDT", "DOGEUSDT"]


def _real_25ad_shape(*, nested_target: object = 30) -> dict[str, object]:
    # 25AD writes the canonical target inside refined_candidate_spec, not at root.
    return {
        "contract_version": "4B.4.3.6.6.25AD",
        "decision": "HYP005_R1_REVALIDATION_PLANNING_READY",
        "refined_branch_id": "HYP-005-R1",
        "fresh_ledger_namespace": "HYP005_R1",
        "starting_unique_shadow_observation_count": 0,
        "recommended_pruned_symbols": PRUNED,
        "recommended_refined_symbols": REFINED,
        "recommended_refined_symbols_arg": ",".join(REFINED),
        "approved_for_next_scheduler_pack_patch": True,
        "approved_for_scheduler_regeneration": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "baseline_observations_reused_in_refined_branch": False,
        "limits": {"revalidation_sample_target": 30},
        "refined_candidate_spec": {
            "symbols": REFINED,
            "symbols_arg": ",".join(REFINED),
            "excluded_symbols": PRUNED,
            "fresh_ledger_namespace": "HYP005_R1",
            "starting_unique_shadow_observation_count": 0,
            "shadow_sample_target": nested_target,
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
        "guardrails": {
            "no_order_shadow_only": True,
            "orders_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
        },
    }


def _write_inputs(root: Path, *, nested_target: object = 30) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    ad = root / "4B436625AD_hyp005_baseline_freeze_refined_revalidation_planning_20260602_072834.json"
    u = root / "4B436625U_hyp005_no_order_shadow_candidate_spec_20260509_175722.json"
    ad.write_text(json.dumps(_real_25ad_shape(nested_target=nested_target)), encoding="utf-8")
    u.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    return ad, u


def test_25aeh1_declares_hotfix_version() -> None:
    assert HYP005_R1_SHADOW_SCHEDULER_HOTFIX_VERSION == "4B.4.3.6.6.25AE-H1"


def test_25aeh1_real_25ad_nested_target_generates_pack(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        tmp_path,
        out_dir=tmp_path,
        baseline_task_disabled_confirmed=True,
        review_ok=True,
        timestamp="20260602_090000",
    )
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_READY
    assert report["shadow_sample_target"] == 30
    validation = report["shadow_sample_target_validation"]
    assert validation["resolved_shadow_sample_target"] == 30
    assert validation["selected_source"] == "refined_candidate_spec.shadow_sample_target"
    assert R1_SHADOW_SAMPLE_TARGET_VALIDATION_NORMALIZED in report["reason_codes"]
    assert report["artifacts"] is not None
    assert Path(report["artifacts"]["pack_dir"]).exists()


def test_25aeh1_string_nested_target_30_is_normalized(tmp_path: Path) -> None:
    _write_inputs(tmp_path, nested_target="30")
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        tmp_path, out_dir=tmp_path, baseline_task_disabled_confirmed=True, review_ok=True
    )
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_READY
    assert report["shadow_sample_target_validation"]["resolved_shadow_sample_target"] == 30


def test_25aeh1_invalid_nested_target_still_blocks(tmp_path: Path) -> None:
    _write_inputs(tmp_path, nested_target="29")
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        tmp_path, out_dir=tmp_path, baseline_task_disabled_confirmed=True, review_ok=True
    )
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK
    assert "R1_SHADOW_SAMPLE_TARGET_NOT_30" in report["blockers"]
    assert report["artifacts"] is None


def test_25aeh1_baseline_disabled_guard_remains_enforced(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(tmp_path, out_dir=tmp_path, review_ok=True)
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK
    assert "BASELINE_TASK_DISABLED_CONFIRMATION_REQUIRED" in report["blockers"]
    assert report["artifacts"] is None


def test_25aeh1_cli_generates_pack_from_real_25ad_shape(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    out = tmp_path / "out"
    _write_inputs(reports, nested_target="30")
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
    assert list(out.glob("4B436625AE_hyp005_r1_windows_task_scheduler_pack_*"))


def test_25aeh1_accepts_report_emitted_by_actual_25ad_builder(tmp_path: Path) -> None:
    from tradebot.research_hyp005_baseline_freeze_refined_revalidation_planning import (
        build_hyp005_baseline_freeze_refined_revalidation_planning_report,
        write_hyp005_baseline_freeze_refined_revalidation_planning_artifacts,
    )

    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    ac_payload = {
        "contract_version": "4B.4.3.6.6.25AC",
        "decision": "HYP005_BRANCH_REFINEMENT_REQUIRED",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "baseline_scenario": {"included_symbols": sorted([*REFINED, *PRUNED])},
        "recommended_pruned_symbols": PRUNED,
        "recommended_symbols": REFINED,
        "recommended_symbols_arg": ",".join(REFINED),
        "selected_scenario": {
            "scenario_id": "PRUNE_AVAXUSDT_DOGEUSDT",
            "excluded_symbols": PRUNED,
            "included_symbols": REFINED,
            "passes_continuation_gate": False,
        },
        "approved_for_scheduler_regeneration": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }
    (reports / "4B436625AC_hyp005_symbol_risk_pruning_decision_20260602_071442.json").write_text(
        json.dumps(ac_payload), encoding="utf-8"
    )
    (reports / "4B436625U_hyp005_no_order_shadow_candidate_spec_20260509_175722.json").write_text(
        json.dumps(_candidate_spec()), encoding="utf-8"
    )
    ad_report = build_hyp005_baseline_freeze_refined_revalidation_planning_report(reports, review_ok=True)
    assert "shadow_sample_target" not in ad_report  # regression shape: canonical target is nested
    assert ad_report["refined_candidate_spec"]["shadow_sample_target"] == 30
    write_hyp005_baseline_freeze_refined_revalidation_planning_artifacts(ad_report, reports)
    ae_report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        reports,
        out_dir=tmp_path / "out",
        baseline_task_disabled_confirmed=True,
        review_ok=True,
        timestamp="20260602_093000",
    )
    assert ae_report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_READY
    assert ae_report["artifacts"] is not None
