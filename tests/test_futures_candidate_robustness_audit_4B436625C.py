from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.futures_candidate_robustness_audit import build_futures_candidate_robustness_audit


def _report(decision: str = "PASS") -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25B",
        "decision": decision,
        "candidates": [
            {
                "decision": decision,
                "score": 704.0,
                "symbol": "ETHUSDT",
                "interval": "4h",
                "strategy": "funding_trend_exhaustion",
                "signals": 31,
                "coverage_pct": 5.74,
                "mean_edge_bps": 44.12,
                "median_edge_bps": 139.2,
                "win_rate_pct": 70.96,
                "profit_factor": 1.58,
                "max_dd_pct": 16.13,
                "oos_edge_bps": 175.6,
                "reasons": [],
                "warnings": [],
            },
            {
                "decision": "PASS",
                "score": 330.0,
                "symbol": "BTCUSDT",
                "interval": "4h",
                "strategy": "funding_trend_exhaustion",
                "signals": 33,
                "coverage_pct": 6.11,
                "mean_edge_bps": 53.70,
                "median_edge_bps": 56.66,
                "win_rate_pct": 63.63,
                "profit_factor": 2.15,
                "max_dd_pct": 4.05,
                "oos_edge_bps": 18.23,
                "reasons": [],
                "warnings": [],
            },
        ],
    }


def test_robustness_audit_passes_confirmed_futures_candidate() -> None:
    result = build_futures_candidate_robustness_audit([_report()])
    assert result.decision == "PASS"
    assert result.approved_for_research_candidate is True
    assert result.approved_for_training_candidate is False
    assert result.approved_for_paper_candidate is False
    assert result.approved_for_live_real is False
    assert result.post_requests_allowed is False
    assert result.selected_symbol == "BTCUSDT" or result.selected_symbol == "ETHUSDT"
    assert "NO_FUTURES_ROBUSTNESS_CANDIDATE_PASSED" not in result.reason_codes


def test_robustness_audit_blocks_negative_candidate() -> None:
    bad = _report("BLOCK")
    bad["candidates"] = [
        {
            "decision": "BLOCK",
            "score": -1,
            "symbol": "ETHUSDT",
            "interval": "4h",
            "strategy": "funding_trend_exhaustion",
            "signals": 8,
            "coverage_pct": 0.3,
            "mean_edge_bps": -12,
            "median_edge_bps": -20,
            "win_rate_pct": 35,
            "profit_factor": 0.5,
            "max_dd_pct": 40,
            "oos_edge_bps": -30,
            "reasons": ["EDGE_EXPECTED_EDGE_LOW"],
        }
    ]
    result = build_futures_candidate_robustness_audit([bad])
    assert result.decision == "BLOCK"
    assert result.approved_for_research_candidate is False
    assert "NO_FUTURES_ROBUSTNESS_CANDIDATE_PASSED" in result.reason_codes
    assert "ROBUSTNESS_SIGNAL_COUNT_LOW" in result.reason_codes


def test_robustness_audit_adds_coverage_warnings_when_details_absent() -> None:
    result = build_futures_candidate_robustness_audit([_report()])
    assert "FUNDING_COVERAGE_DETAIL_UNAVAILABLE" in result.warnings
    assert "OUTLIER_DEPENDENCY_DETAIL_UNAVAILABLE" in result.warnings


def test_tool_writes_report_from_input_json(tmp_path: Path) -> None:
    report_path = tmp_path / "25b.json"
    report_path.write_text(json.dumps(_report()), encoding="utf-8")
    out_dir = tmp_path / "reports"
    script = Path(__file__).resolve().parents[1] / "tools" / "run_futures_candidate_robustness_audit_4B436625C.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-json",
            str(report_path),
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "futures candidate robustness audit PASS" in proc.stdout
    assert list(out_dir.glob("4B436625C_futures_candidate_robustness_audit_*.json"))
    assert list(out_dir.glob("4B436625C_futures_candidate_robustness_audit_*.md"))


def test_tool_requires_review_ok(tmp_path: Path) -> None:
    report_path = tmp_path / "25b.json"
    report_path.write_text(json.dumps(_report()), encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "tools" / "run_futures_candidate_robustness_audit_4B436625C.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--input-json", str(report_path)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "--review-ok" in proc.stderr + proc.stdout
