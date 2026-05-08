from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.futures_hypothesis_branch_review import build_futures_hypothesis_branch_review


def _report_25b() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25B",
        "decision": "PASS",
        "candidates": [
            {
                "decision": "PASS",
                "symbol": "BTCUSDT",
                "interval": "4h",
                "strategy": "funding_trend_exhaustion",
                "signals": 33,
                "mean_edge_bps": 53.704409,
                "median_edge_bps": 56.665439,
                "profit_factor": 2.154669,
                "reasons": [],
            },
            {
                "decision": "PASS",
                "symbol": "ETHUSDT",
                "interval": "4h",
                "strategy": "funding_trend_exhaustion",
                "signals": 31,
                "mean_edge_bps": 44.125478,
                "median_edge_bps": 139.2081,
                "profit_factor": 1.584716,
                "reasons": [],
            },
        ],
    }


def _report_25d_btc_block() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25D",
        "decision": "BLOCK",
        "selected": "BTCUSDT 4h funding_trend_exhaustion",
        "signal_count": 27,
        "mean_net_edge_bps": 16.295166,
        "median_net_edge_bps": -23.26973,
        "profit_factor": 1.18424,
        "reason_codes": [
            "NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED",
            "DRY_RUN_SIGNAL_COUNT_LOW",
            "DRY_RUN_MEDIAN_EDGE_LOW",
            "DRY_RUN_WALK_FORWARD_STABILITY_LOW",
        ],
    }


def _report_25e_btc_block() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25E",
        "decision": "BLOCK",
        "selected": "BTCUSDT 4h funding_trend_exhaustion",
        "signal_count": 4,
        "mean_net_edge_bps": 26.399247,
        "median_net_edge_bps": 50.012313,
        "profit_factor": 2.151512,
        "reason_codes": [
            "NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED",
            "REFINEMENT_OOS_EDGE_LOW",
            "REFINEMENT_SIDE_IMBALANCE_HIGH",
            "REFINEMENT_SIGNAL_COUNT_LOW",
            "REFINEMENT_TOP_WIN_DEPENDENCY_HIGH",
        ],
    }


def _report_25e_eth_block() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25E",
        "decision": "BLOCK",
        "selected": "ETHUSDT 4h funding_trend_exhaustion",
        "signal_count": 6,
        "mean_net_edge_bps": -4.2,
        "median_net_edge_bps": -12.0,
        "profit_factor": 0.82,
        "reason_codes": [
            "NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED",
            "REFINEMENT_SIGNAL_COUNT_LOW",
            "REFINEMENT_TOP_WIN_DEPENDENCY_HIGH",
        ],
    }


def test_branch_review_pending_when_companion_needs_audit() -> None:
    report = build_futures_hypothesis_branch_review([
        _report_25b(),
        _report_25d_btc_block(),
        _report_25e_btc_block(),
    ])

    assert report.decision == "BRANCH_REVIEW_PENDING_COMPANION_AUDIT"
    assert not report.approved_for_training_candidate
    assert not report.approved_for_paper_candidate
    assert not report.approved_for_live_real
    assert "PRIMARY_CANDIDATE_TOO_SPARSE_OR_OUTLIER_DEPENDENT" in report.reason_codes
    assert "COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED" in report.reason_codes
    assert report.combined_summary is not None
    assert report.combined_summary.signal_count >= 30


def test_branch_review_closes_when_primary_and_companion_fail_terminal_audit() -> None:
    report = build_futures_hypothesis_branch_review([
        _report_25b(),
        _report_25d_btc_block(),
        _report_25e_btc_block(),
        _report_25e_eth_block(),
    ])

    assert report.decision == "BRANCH_CLOSED_NO_GO"
    assert not report.approved_for_research_candidate
    assert "FUTURES_BRANCH_NO_ROBUST_DRY_RUN_CANDIDATE" in report.reason_codes
    assert report.order_actions_performed is False
    assert report.reload_performed is False


def test_branch_review_continues_only_research_when_refinement_passes() -> None:
    eth_pass = {
        "contract_version": "4B.4.3.6.6.25E",
        "decision": "PASS",
        "selected": "ETHUSDT 4h funding_trend_exhaustion",
        "signal_count": 42,
        "mean_net_edge_bps": 18.0,
        "median_net_edge_bps": 9.0,
        "profit_factor": 1.31,
        "reason_codes": [],
    }
    report = build_futures_hypothesis_branch_review([_report_25b(), _report_25d_btc_block(), eth_pass])

    assert report.decision == "BRANCH_RESEARCH_CONTINUE"
    assert report.approved_for_research_candidate is True
    assert report.approved_for_training_candidate is False
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False


def test_tool_writes_report_from_input_json(tmp_path: Path) -> None:
    report_paths: list[Path] = []
    for idx, payload in enumerate([_report_25b(), _report_25d_btc_block(), _report_25e_btc_block()]):
        path = tmp_path / f"input_{idx}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        report_paths.append(path)

    out_dir = tmp_path / "reports"
    cmd = [
        sys.executable,
        "tools/run_futures_hypothesis_branch_review_4B436625F.py",
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    for path in report_paths:
        cmd.extend(["--input-json", str(path)])

    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "BRANCH_REVIEW_PENDING_COMPANION_AUDIT" in result.stdout
    assert list(out_dir.glob("4B436625F_futures_hypothesis_branch_review_*.json"))
    assert list(out_dir.glob("4B436625F_futures_hypothesis_branch_review_*.md"))


def test_review_ok_is_required() -> None:
    result = subprocess.run(
        [sys.executable, "tools/run_futures_hypothesis_branch_review_4B436625F.py"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "--review-ok is required" in result.stderr
