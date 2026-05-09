from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp003_branch_closure_evidence_pack import (
    HYP003_CLOSURE_CONFIRMED,
    HYP003_CLOSURE_BLOCK,
    build_hyp003_branch_closure_evidence_pack,
)


def _report_25j() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25J",
        "decision": "HYP003_EXPLORATION_PASS",
        "approved_for_research_candidate": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "selected_candidate": {
            "symbol": "ETHUSDT",
            "interval": "4h",
            "strategy_family": "range_mean_reversion",
            "regime": "range",
            "signal_count": 67,
            "mean_net_edge_bps": 23.979025,
            "median_net_edge_bps": 31.590359,
            "profit_factor": 1.581891,
        },
        "reason_codes": ["HYP003_RESEARCH_CANDIDATE_IDENTIFIED"],
    }


def _report_25k() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25K",
        "decision": "HYP003_ROBUSTNESS_BLOCK",
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "selected": "ETHUSDT 4h range_mean_reversion range",
        "selected_signal_count": 66,
        "selected_mean_net_edge_bps": -11.606522,
        "selected_median_net_edge_bps": -24.400868,
        "selected_profit_factor": 0.74203,
        "reason_codes": [
            "ROBUST_MEAN_EDGE_LOW",
            "ROBUST_MEDIAN_EDGE_LOW",
            "ROBUST_OOS_EDGE_LOW",
            "ROBUST_PROFIT_FACTOR_LOW",
            "ROBUST_WALK_FORWARD_STABILITY_LOW",
            "ROBUST_WIN_RATE_LOW",
        ],
    }


def _report_25l() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25L",
        "decision": "HYP003_BRANCH_CLOSURE_RECOMMENDED",
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "failed_candidate": {
            "symbol": "ETHUSDT",
            "interval": "4h",
            "strategy_family": "range_mean_reversion",
            "regime": "range",
        },
        "selected_next_candidate": None,
        "reason_codes": [
            "HYP003_SELECTED_CANDIDATE_ROBUSTNESS_BLOCK",
            "NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE",
            "ROBUST_MEAN_EDGE_LOW",
            "ROBUST_MEDIAN_EDGE_LOW",
            "ROBUST_OOS_EDGE_LOW",
            "ROBUST_PROFIT_FACTOR_LOW",
            "ROBUST_WALK_FORWARD_STABILITY_LOW",
            "ROBUST_WIN_RATE_LOW",
        ],
    }


def test_25m_confirms_hyp003_branch_closure_from_25j_25k_25l() -> None:
    report = build_hyp003_branch_closure_evidence_pack([_report_25j(), _report_25k(), _report_25l()])
    assert report.decision == HYP003_CLOSURE_CONFIRMED
    assert report.final_25j_decision == "HYP003_EXPLORATION_PASS"
    assert report.final_25k_decision == "HYP003_ROBUSTNESS_BLOCK"
    assert report.final_25l_decision == "HYP003_BRANCH_CLOSURE_RECOMMENDED"
    assert report.no_alternate_candidate_confirmed is True
    assert report.approved_for_training_candidate is False
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False
    assert "HYP003_BRANCH_CLOSURE_RECOMMENDED_CONFIRMED" in report.reason_codes
    assert "NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE_CONFIRMED" in report.reason_codes


def test_25m_blocks_when_25l_closure_missing() -> None:
    report = build_hyp003_branch_closure_evidence_pack([_report_25j(), _report_25k()])
    assert report.decision == HYP003_CLOSURE_BLOCK
    assert "HYP003_BRANCH_CLOSURE_RECOMMENDED_MISSING" in report.reason_codes
    assert report.approved_for_live_real is False


def test_25m_blocks_if_any_training_paper_live_approval_detected() -> None:
    bad = _report_25l()
    bad["approved_for_paper_candidate"] = True
    report = build_hyp003_branch_closure_evidence_pack([_report_25j(), _report_25k(), bad])
    assert report.decision == HYP003_CLOSURE_BLOCK
    assert "TRAINING_PAPER_OR_LIVE_APPROVAL_DETECTED" in report.reason_codes


def test_25m_registry_snapshot_marks_closed_no_go() -> None:
    report = build_hyp003_branch_closure_evidence_pack([_report_25j(), _report_25k(), _report_25l()])
    assert report.registry_snapshot["status"] == "CLOSED_NO_GO"
    assert report.registry_snapshot["hypothesis_id"] == "HYP-003"
    assert report.registry_snapshot["approved_for_live_real"] is False


def test_tool_writes_closure_report_and_registry_snapshot(tmp_path: Path) -> None:
    input_paths = []
    for idx, payload in enumerate([_report_25j(), _report_25k(), _report_25l()]):
        path = tmp_path / f"input_{idx}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        input_paths.append(path)
    out_dir = tmp_path / "reports"
    cmd = [
        sys.executable,
        "tools/run_hyp003_branch_closure_evidence_pack_4B436625M.py",
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    for path in input_paths:
        cmd.extend(["--input-json", str(path)])
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "HYP003_BRANCH_CLOSURE_CONFIRMED" in result.stdout
    assert list(out_dir.glob("4B436625M_hyp003_branch_closure_evidence_pack_*.json"))
    assert list(out_dir.glob("4B436625M_hyp003_branch_closure_evidence_pack_*.md"))
    assert list(out_dir.glob("4B436625M_hyp003_branch_closure_registry_snapshot_*.json"))
