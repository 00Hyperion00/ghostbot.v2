from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp004_branch_closure_evidence_pack import build_hyp004_branch_closure_evidence_pack


def _report_25o_block() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25O",
        "phase": "4B.4.3.6.6.25O",
        "report_type": "hyp004_cross_symbol_relative_strength_exploration",
        "decision": "HYP004_EXPLORATION_BLOCK",
        "hypothesis_id": "HYP-004",
        "candidate_count": 4,
        "passed_candidate_count": 0,
        "selected_strategy_family": "laggard_reversion",
        "selected_signal_count": 510,
        "selected_mean_net_edge_bps": 21.936463,
        "selected_median_net_edge_bps": 9.812974,
        "selected_profit_factor": 1.238365,
        "selected_oos_mean_net_edge_bps": 29.363216,
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reason_codes": [
            "DIAGNOSTIC_STRATEGY_NOT_APPROVABLE",
            "NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED",
        ],
    }


def _report_25p_block() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25P",
        "phase": "4B.4.3.6.6.25P",
        "report_type": "hyp004_relative_strength_refinement",
        "decision": "HYP004_REFINEMENT_BLOCK",
        "hypothesis_id": "HYP-004",
        "selected_25o_family": "laggard_reversion",
        "candidate_count": 5,
        "passed_candidate_count": 0,
        "selected_refinement_name": "laggard_reversion_symbol_cooldown_lb24_h8_spread45",
        "selected_signal_count": 163,
        "selected_mean_net_edge_bps": 5.509956,
        "selected_median_net_edge_bps": 20.545359,
        "selected_profit_factor": 1.051558,
        "selected_oos_mean_net_edge_bps": 41.8504,
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reason_codes": [
            "DIAGNOSTIC_REFINEMENT_NOT_APPROVABLE",
            "NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED",
        ],
    }


def test_25q_confirms_hyp004_closure_from_25o_25p_blocks() -> None:
    report = build_hyp004_branch_closure_evidence_pack([
        ("25o.json", _report_25o_block()),
        ("25p.json", _report_25p_block()),
    ])
    assert report.decision == "HYP004_BRANCH_CLOSURE_CONFIRMED"
    assert report.ok is True
    assert report.selected_25o_family == "laggard_reversion"
    assert report.selected_refinement_name == "laggard_reversion_symbol_cooldown_lb24_h8_spread45"
    assert "HYP004_EXPLORATION_BLOCK_CONFIRMED" in report.reason_codes
    assert "HYP004_REFINEMENT_BLOCK_CONFIRMED" in report.reason_codes
    assert "NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED_CONFIRMED" in report.reason_codes
    assert report.registry_snapshot["hypotheses"][0]["status"] == "CLOSED_NO_GO"
    assert report.approved_for_live_real is False


def test_25q_blocks_when_25p_refinement_missing() -> None:
    report = build_hyp004_branch_closure_evidence_pack([("25o.json", _report_25o_block())])
    assert report.decision == "HYP004_BRANCH_CLOSURE_BLOCK"
    assert "HYP004_REFINEMENT_BLOCK_MISSING" in report.reason_codes


def test_25q_blocks_when_any_training_or_live_approval_detected() -> None:
    p = _report_25p_block()
    p["approved_for_paper_candidate"] = True
    report = build_hyp004_branch_closure_evidence_pack([("25o.json", _report_25o_block()), ("25p.json", p)])
    assert report.decision == "HYP004_BRANCH_CLOSURE_BLOCK"
    assert "TRAINING_PAPER_LIVE_APPROVAL_DETECTED" in report.reason_codes
    assert report.approved_for_paper_candidate is False


def test_25q_registry_snapshot_has_guardrails() -> None:
    report = build_hyp004_branch_closure_evidence_pack([("25o.json", _report_25o_block()), ("25p.json", _report_25p_block())])
    guardrails = report.registry_snapshot["guardrails"]
    assert guardrails["training_allowed"] is False
    assert guardrails["paper_allowed"] is False
    assert guardrails["live_real_allowed"] is False
    assert report.registry_snapshot["hypotheses"][0]["approved_for_live_real"] is False


def test_tool_writes_closure_report_and_registry_snapshot(tmp_path: Path) -> None:
    report_25o = tmp_path / "25o.json"
    report_25p = tmp_path / "25p.json"
    out_dir = tmp_path / "reports"
    report_25o.write_text(json.dumps(_report_25o_block()), encoding="utf-8")
    report_25p.write_text(json.dumps(_report_25p_block()), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_hyp004_branch_closure_evidence_pack_4B436625Q.py",
            "--input-json",
            str(report_25o),
            "--input-json",
            str(report_25p),
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "HYP004_BRANCH_CLOSURE_CONFIRMED" in result.stdout
    assert list(out_dir.glob("4B436625Q_hyp004_branch_closure_evidence_pack_*.json"))
    assert list(out_dir.glob("4B436625Q_hyp004_branch_closure_evidence_pack_*.md"))
    assert list(out_dir.glob("4B436625Q_hyp004_branch_closure_registry_snapshot_*.json"))
