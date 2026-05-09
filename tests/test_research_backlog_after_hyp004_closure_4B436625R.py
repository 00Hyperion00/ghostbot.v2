from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_backlog_after_hyp004_closure import (
    RESEARCH_BACKLOG_HYP004_ADVANCEMENT_CONTRACT_VERSION,
    build_research_backlog_after_hyp004_closure,
    discover_latest_closure_report,
)


def _closure_25q() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25Q",
        "decision": "HYP004_BRANCH_CLOSURE_CONFIRMED",
        "hypothesis_id": "HYP-004",
        "branch_name": "cross_symbol_relative_strength_rotation",
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
        "reason_codes": [
            "HYP004_BRANCH_CLOSED_NO_GO",
            "HYP004_EXPLORATION_BLOCK_CONFIRMED",
            "HYP004_REFINEMENT_BLOCK_CONFIRMED",
            "NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED_CONFIRMED",
            "NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED_CONFIRMED",
            "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        ],
    }


def test_25r_selects_next_hypothesis_after_hyp004_closure() -> None:
    report = build_research_backlog_after_hyp004_closure(_closure_25q())

    assert RESEARCH_BACKLOG_HYP004_ADVANCEMENT_CONTRACT_VERSION == "4B.4.3.6.6.25R"
    assert report["decision"] == "NEXT_HYPOTHESIS_SELECTED"
    assert report["closed_hypothesis_id"] == "HYP-004"
    assert report["selected_next_hypothesis_id"] == "HYP-005"
    assert report["selected_next_branch_name"] == "liquidity_sweep_reversal_vol_compression"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert "HYP004_CLOSURE_CONFIRMED" in report["reason_codes"]
    assert "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED" in report["reason_codes"]


def test_25r_blocks_when_hyp004_closure_missing() -> None:
    payload = _closure_25q()
    payload["decision"] = "HYP004_REFINEMENT_BLOCK"
    report = build_research_backlog_after_hyp004_closure(payload)

    assert report["decision"] == "BACKLOG_ADVANCEMENT_BLOCK"
    assert report["selected_next_hypothesis_id"] is None
    assert report["approved_for_research_candidate"] is False
    assert "HYP004_CLOSURE_NOT_CONFIRMED" in report["reason_codes"]


def test_25r_blocks_when_approval_detected() -> None:
    payload = _closure_25q()
    payload["approved_for_paper_candidate"] = True
    report = build_research_backlog_after_hyp004_closure(payload)

    assert report["decision"] == "BACKLOG_ADVANCEMENT_BLOCK"
    assert "TRAINING_PAPER_OR_LIVE_APPROVAL_DETECTED" in report["reason_codes"]
    assert report["approved_for_paper_candidate"] is False


def test_25r_registry_can_select_custom_next_hypothesis() -> None:
    registry = {
        "hypotheses": [
            {"id": "HYP-004", "title": "Cross-symbol relative strength rotation", "branch_name": "cross_symbol_relative_strength_rotation", "priority": 40, "status": "REGISTERED"},
            {"id": "HYP-009", "title": "Order-flow imbalance proxy", "branch_name": "order_flow_imbalance_proxy", "priority": 90, "status": "REGISTERED"},
        ]
    }
    report = build_research_backlog_after_hyp004_closure(_closure_25q(), registry=registry)
    assert report["selected_next_hypothesis_id"] == "HYP-009"
    assert report["selected_next_branch_name"] == "order_flow_imbalance_proxy"


def test_tool_writes_report_and_registry_snapshot(tmp_path: Path) -> None:
    closure_path = tmp_path / "4B436625Q_hyp004_branch_closure_evidence_pack_20260509_155354.json"
    closure_path.write_text(json.dumps(_closure_25q()), encoding="utf-8")
    out_dir = tmp_path / "reports"

    result = subprocess.run(
        [
            sys.executable,
            "tools/run_research_backlog_after_hyp004_closure_4B436625R.py",
            "--input-json",
            str(closure_path),
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
    assert "NEXT_HYPOTHESIS_SELECTED" in result.stdout
    assert "selected_next_hypothesis_id: HYP-005" in result.stdout
    assert list(out_dir.glob("4B436625R_research_backlog_after_hyp004_closure_*.json"))
    assert list(out_dir.glob("4B436625R_research_backlog_after_hyp004_closure_*.md"))
    assert list(out_dir.glob("4B436625R_proposed_research_registry_snapshot_*.json"))


def test_discover_latest_closure_report(tmp_path: Path) -> None:
    older = tmp_path / "4B436625Q_hyp004_branch_closure_evidence_pack_20260101_000000.json"
    newer = tmp_path / "4B436625Q_hyp004_branch_closure_evidence_pack_20260102_000000.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")
    assert discover_latest_closure_report(tmp_path) == newer
