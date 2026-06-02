from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_baseline_freeze_refined_revalidation_planning import (
    HYP005_R1_REVALIDATION_PLANNING_BLOCK,
    HYP005_R1_REVALIDATION_PLANNING_READY,
    build_hyp005_baseline_freeze_refined_revalidation_planning_report,
    write_hyp005_baseline_freeze_refined_revalidation_planning_artifacts,
)

REFINED = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
BASELINE = [*REFINED, "AVAXUSDT", "DOGEUSDT"]


def _ac_report(*, decision: str = "HYP005_BRANCH_REFINEMENT_REQUIRED", refined: list[str] | None = None) -> dict[str, object]:
    symbols = sorted(refined if refined is not None else REFINED)
    return {
        "contract_version": "4B.4.3.6.6.25AC",
        "report_type": "hyp005_symbol_risk_pruning_candidate_continuation_decision_gate",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "decision": decision,
        "deduplication": {
            "raw_observation_count": 3292,
            "unique_observation_count": 31,
            "duplicate_removed_count": 3261,
        },
        "baseline_scenario": {
            "scenario_id": "BASELINE_ALL_SYMBOLS",
            "included_symbols": sorted(BASELINE),
            "observation_count": 31,
            "matured_forward_return_count": 25,
            "maturity_pending_count": 6,
            "mean_forward_edge_bps": -15.642778,
            "median_forward_edge_bps": 16.225838,
            "profit_factor": 0.783427,
            "win_rate_pct": 56.0,
            "high_slippage_symbols": ["AVAXUSDT", "DOGEUSDT"],
            "tail_loss_count": 3,
            "tail_loss_symbols": ["AVAXUSDT", "DOGEUSDT"],
            "true_missing_required_fields_pct": 0.967742,
        },
        "selected_scenario": {
            "scenario_id": "PRUNE_AVAXUSDT_DOGEUSDT",
            "excluded_symbols": ["AVAXUSDT", "DOGEUSDT"],
            "included_symbols": symbols,
            "passes_continuation_gate": False,
        },
        "recommended_pruned_symbols": ["AVAXUSDT", "DOGEUSDT"],
        "recommended_symbols": symbols,
        "recommended_symbols_arg": ",".join(symbols),
        "approved_for_scheduler_regeneration": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def _write_ac(reports_dir: Path, payload: dict[str, object] | None = None) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "4B436625AC_hyp005_symbol_risk_pruning_decision_20260602_071442.json"
    path.write_text(json.dumps(payload if payload is not None else _ac_report()), encoding="utf-8")
    return path


def test_25ad_valid_refinement_freezes_baseline_and_plans_fresh_r1(tmp_path: Path) -> None:
    _write_ac(tmp_path)
    report = build_hyp005_baseline_freeze_refined_revalidation_planning_report(tmp_path, review_ok=True)
    assert report["decision"] == HYP005_R1_REVALIDATION_PLANNING_READY
    assert report["baseline_evidence_frozen"] is True
    assert report["refined_branch_id"] == "HYP-005-R1"
    assert report["fresh_ledger_namespace"] == "HYP005_R1"
    assert report["starting_unique_shadow_observation_count"] == 0
    assert report["recommended_pruned_symbols"] == ["AVAXUSDT", "DOGEUSDT"]
    assert report["recommended_refined_symbols"] == sorted(REFINED)
    assert report["baseline_observations_reused_in_refined_branch"] is False
    spec = report["refined_candidate_spec"]
    assert spec["legacy_baseline_observations_reused"] is False
    assert spec["starting_unique_shadow_observation_count"] == 0
    assert spec["shadow_sample_target"] == 30


def test_25ad_blocks_without_valid_25ac_refinement_decision(tmp_path: Path) -> None:
    _write_ac(tmp_path, _ac_report(decision="HYP005_CONTINUE_WITH_BASELINE_SYMBOLS"))
    report = build_hyp005_baseline_freeze_refined_revalidation_planning_report(tmp_path, review_ok=True)
    assert report["decision"] == HYP005_R1_REVALIDATION_PLANNING_BLOCK
    assert "SOURCE_25AC_DECISION_NOT_REFINEMENT_REQUIRED" in report["blockers"]
    assert report["baseline_evidence_frozen"] is False


def test_25ad_blocks_if_pruned_symbol_is_still_in_refined_set(tmp_path: Path) -> None:
    payload = _ac_report(refined=[*REFINED, "DOGEUSDT"])
    _write_ac(tmp_path, payload)
    report = build_hyp005_baseline_freeze_refined_revalidation_planning_report(tmp_path, review_ok=True)
    assert report["decision"] == HYP005_R1_REVALIDATION_PLANNING_BLOCK
    assert "PRUNED_SYMBOL_PRESENT_IN_REFINED_SET" in report["blockers"]


def test_25ad_all_transition_guardrails_remain_closed(tmp_path: Path) -> None:
    _write_ac(tmp_path)
    report = build_hyp005_baseline_freeze_refined_revalidation_planning_report(tmp_path, review_ok=True)
    assert report["approved_for_next_scheduler_pack_patch"] is True
    assert report["approved_for_scheduler_regeneration"] is False
    assert report["approved_for_scheduler_registration"] is False
    assert report["scheduler_regeneration_requires_separate_operator_patch"] is True
    assert report["baseline_scheduler_disable_performed"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["order_actions_performed"] is False
    assert report["post_requests_allowed"] is False
    assert report["training_performed"] is False
    assert report["reload_performed"] is False
    assert report["config_mutation_performed"] is False


def test_25ad_write_artifacts_emits_digest_snapshot_and_fresh_plan(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    out = tmp_path / "out"
    _write_ac(reports)
    report = build_hyp005_baseline_freeze_refined_revalidation_planning_report(reports, review_ok=True)
    paths = write_hyp005_baseline_freeze_refined_revalidation_planning_artifacts(report, out)
    assert paths["report_json"] and paths["report_json"].exists()
    assert paths["report_md"] and paths["report_md"].exists()
    assert paths["baseline_evidence_freeze_json"] and paths["baseline_evidence_freeze_json"].exists()
    assert paths["refined_candidate_revalidation_plan_json"] and paths["refined_candidate_revalidation_plan_json"].exists()
    freeze = json.loads(paths["baseline_evidence_freeze_json"].read_text(encoding="utf-8"))
    spec = json.loads(paths["refined_candidate_revalidation_plan_json"].read_text(encoding="utf-8"))
    assert len(freeze["baseline_evidence_digest_sha256"]) == 64
    assert spec["fresh_ledger_namespace"] == "HYP005_R1"
    assert spec["legacy_baseline_observation_reuse_allowed"] is False


def test_25ad_tool_writes_planning_artifacts(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    out = tmp_path / "out"
    _write_ac(reports)
    project_root = Path(__file__).resolve().parents[1]
    tool = project_root / "tools" / "run_hyp005_baseline_freeze_refined_revalidation_planning_4B436625AD.py"
    result = subprocess.run(
        [
            sys.executable,
            str(tool),
            "--reports-dir",
            str(reports),
            "--out-dir",
            str(out),
            "--review-ok",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "4B.4.3.6.6.25AD" in result.stdout
    assert "HYP005_R1_REVALIDATION_PLANNING_READY" in result.stdout
    assert list(out.glob("4B436625AD_hyp005_baseline_freeze_refined_revalidation_planning_*.json"))
    assert list(out.glob("4B436625AD_hyp005_baseline_evidence_freeze_*.json"))
    assert list(out.glob("4B436625AD_hyp005_r1_refined_candidate_revalidation_plan_*.json"))
