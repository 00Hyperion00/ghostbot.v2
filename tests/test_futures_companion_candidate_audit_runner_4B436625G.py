from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.futures_companion_candidate_audit_runner import (
    build_futures_companion_candidate_audit_runner,
    extract_candidates_from_reports,
)


def _report_25b() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25B",
        "decision": "PASS",
        "candidates": [
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
                "warnings": [],
            },
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
                "warnings": [],
            },
        ],
    }


def test_extract_candidates_from_25b_report() -> None:
    candidates = extract_candidates_from_reports([("25b.json", _report_25b())])
    assert {candidate.symbol for candidate in candidates} == {"BTCUSDT", "ETHUSDT"}
    assert all(candidate.strategy == "funding_trend_exhaustion" for candidate in candidates)


def test_companion_audit_runner_generates_eth_spec_and_commands() -> None:
    report = build_futures_companion_candidate_audit_runner([("25b.json", _report_25b())], out_dir="reports")
    assert report["decision"] == "COMPANION_AUDIT_READY"
    assert report["approved_for_research_candidate"] is False
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["primary"]["symbol"] == "BTCUSDT"
    assert report["companion"]["symbol"] == "ETHUSDT"
    assert report["combined_signals"] == 64
    assert report["companion_spec"]["symbol"] == "ETHUSDT"
    assert "COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED" in report["reason_codes"]
    commands = "\n".join(item["command"] for item in report["downstream_commands"])
    assert "run_futures_research_candidate_simulator_4B436625D.py" in commands
    assert "run_futures_candidate_refinement_median_edge_recovery_4B436625E.py" in commands


def test_companion_audit_runner_blocks_when_companion_missing() -> None:
    payload = _report_25b()
    payload["candidates"] = [item for item in payload["candidates"] if item["symbol"] == "BTCUSDT"]
    report = build_futures_companion_candidate_audit_runner([("25b.json", payload)])
    assert report["decision"] == "COMPANION_AUDIT_BLOCKED"
    assert "COMPANION_EXPLORATION_CANDIDATE_MISSING" in report["reason_codes"]


def test_companion_audit_runner_detects_downstream_confirmation() -> None:
    dry_run_pass = {
        "contract_version": "4B.4.3.6.6.25D",
        "decision": "PASS",
        "approved_for_research_candidate": True,
        "selected": "ETHUSDT 4h funding_trend_exhaustion",
        "selected_symbol": "ETHUSDT",
        "selected_interval": "4h",
        "selected_strategy": "funding_trend_exhaustion",
        "selected_signal_count": 35,
        "selected_mean_net_edge_bps": 12.0,
        "selected_profit_factor": 1.3,
    }
    report = build_futures_companion_candidate_audit_runner([("25b.json", _report_25b()), ("25d.json", dry_run_pass)])
    assert report["decision"] == "COMPANION_AUDIT_CONFIRMED"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_paper_candidate"] is False


def test_tool_writes_report_and_spec_from_input_json(tmp_path: Path) -> None:
    input_json = tmp_path / "25b.json"
    out_dir = tmp_path / "reports"
    input_json.write_text(json.dumps(_report_25b()), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_futures_companion_candidate_audit_runner_4B436625G.py",
            "--input-json",
            str(input_json),
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "COMPANION_AUDIT_READY" in result.stdout
    assert list(out_dir.glob("4B436625G_futures_companion_candidate_audit_runner_*.json"))
    specs = list(out_dir.glob("4B436625G_companion_spec_ETHUSDT_4h_funding_trend_exhaustion.json"))
    assert specs
    spec = json.loads(specs[0].read_text(encoding="utf-8"))
    assert spec["symbol"] == "ETHUSDT"
    assert spec["post_requests_allowed"] is False
