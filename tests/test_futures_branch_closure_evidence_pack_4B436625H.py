from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.futures_branch_closure_evidence_pack import build_futures_branch_closure_evidence_pack, summarize_report


def _report_25b() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25B",
        "report_type": "futures_funding_open_interest_edge_exploration",
        "decision": "PASS",
        "selected": "ETHUSDT 4h funding_trend_exhaustion",
        "selected_mean_net_edge_bps": 44.125478,
        "selected_profit_factor": 1.584716,
        "approved_for_research_candidate": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def _report_25g() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25G",
        "report_type": "futures_companion_candidate_audit_runner",
        "decision": "COMPANION_AUDIT_READY",
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reason_codes": ["COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED", "COMPANION_SPEC_READY"],
    }


def _report_25d(symbol: str) -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25D",
        "report_type": "futures_research_candidate_dry_run_signal_simulator",
        "decision": "BLOCK",
        "selected": {
            "symbol": symbol,
            "interval": "4h",
            "strategy": "funding_trend_exhaustion",
            "metrics": {
                "signal_count": 36 if symbol == "ETHUSDT" else 27,
                "mean_net_edge_bps": 69.5964 if symbol == "ETHUSDT" else 16.295166,
                "median_net_edge_bps": 96.251131 if symbol == "ETHUSDT" else -23.26973,
                "profit_factor": 1.907343 if symbol == "ETHUSDT" else 1.184,
            },
        },
        "reason_codes": ["NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED", "DRY_RUN_OOS_EDGE_LOW"],
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def _report_25e(symbol: str) -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25E",
        "report_type": "futures_candidate_refinement_median_edge_recovery",
        "decision": "BLOCK",
        "candidate_spec": {"symbol": symbol, "interval": "4h", "strategy": "funding_trend_exhaustion"},
        "selected": {
            "metrics": {
                "signal_count": 34 if symbol == "ETHUSDT" else 3,
                "mean_net_edge_bps": -14.276254 if symbol == "ETHUSDT" else 65.51966,
                "median_net_edge_bps": -6.063459 if symbol == "ETHUSDT" else 51.934953,
                "profit_factor": 0.637968 if symbol == "ETHUSDT" else 99.0,
            }
        },
        "reason_codes": [
            "NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED",
            "REFINEMENT_MEAN_EDGE_LOW",
            "REFINEMENT_MEDIAN_EDGE_LOW",
            "REFINEMENT_OOS_EDGE_LOW",
            "REFINEMENT_PROFIT_FACTOR_LOW",
            "REFINEMENT_WALK_FORWARD_STABILITY_LOW",
            "REFINEMENT_WIN_RATE_LOW",
        ],
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def _report_25f_final() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25F",
        "report_type": "futures_hypothesis_branch_review",
        "decision": "BRANCH_CLOSED_NO_GO",
        "selected_symbol": "BTCUSDT",
        "selected_interval": "4h",
        "selected_strategy": "funding_trend_exhaustion",
        "reason_codes": [
            "COMBINED_DRY_RUN_CONFIRMATION_MISSING",
            "COMBINED_TERMINAL_AUDIT_BLOCK_PRESENT",
            "FUTURES_BRANCH_NO_ROBUST_DRY_RUN_CANDIDATE",
            "PRIMARY_CANDIDATE_TOO_SPARSE_OR_OUTLIER_DEPENDENT",
        ],
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def test_summarize_25e_candidate_spec_selected_metrics() -> None:
    summary = summarize_report("eth_25e.json", _report_25e("ETHUSDT"))
    assert summary.phase == "25E"
    assert summary.selected_symbol == "ETHUSDT"
    assert summary.signal_count == 34
    assert summary.mean_net_edge_bps == -14.276254
    assert "REFINEMENT_MEDIAN_EDGE_LOW" in summary.reason_codes


def test_closure_pack_confirms_closed_no_go_from_final_25f_and_terminal_blocks() -> None:
    reports = [
        ("25b.json", _report_25b()),
        ("25g.json", _report_25g()),
        ("btc_25d.json", _report_25d("BTCUSDT")),
        ("btc_25e.json", _report_25e("BTCUSDT")),
        ("eth_25d.json", _report_25d("ETHUSDT")),
        ("eth_25e.json", _report_25e("ETHUSDT")),
        ("25f.json", _report_25f_final()),
    ]
    pack = build_futures_branch_closure_evidence_pack(reports)
    assert pack["decision"] == "FUTURES_BRANCH_CLOSURE_CONFIRMED"
    assert pack["ok"] is True
    assert pack["final_25f_decision"] == "BRANCH_CLOSED_NO_GO"
    assert pack["primary_terminal_block_count"] == 2
    assert pack["companion_terminal_block_count"] == 2
    assert "HYPOTHESIS_BRANCH_CLOSED_NO_GO" in pack["reason_codes"]
    assert "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED" in pack["reason_codes"]
    assert pack["approved_for_training_candidate"] is False
    assert pack["approved_for_paper_candidate"] is False
    assert pack["approved_for_live_real"] is False
    assert pack["guardrails"]["post_requests_allowed"] is False


def test_closure_pack_blocks_when_final_25f_missing() -> None:
    reports = [
        ("btc_25d.json", _report_25d("BTCUSDT")),
        ("btc_25e.json", _report_25e("BTCUSDT")),
        ("eth_25d.json", _report_25d("ETHUSDT")),
        ("eth_25e.json", _report_25e("ETHUSDT")),
    ]
    pack = build_futures_branch_closure_evidence_pack(reports)
    assert pack["decision"] == "FUTURES_BRANCH_CLOSURE_EVIDENCE_READY_BUT_FINAL_REVIEW_MISSING"
    assert pack["ok"] is False
    assert "FINAL_25F_BRANCH_CLOSED_NO_GO_MISSING" in pack["reason_codes"]


def test_closure_pack_detects_unsafe_approval_or_mutation() -> None:
    unsafe = _report_25f_final()
    unsafe["approved_for_paper_candidate"] = True
    pack = build_futures_branch_closure_evidence_pack([
        ("btc_25d.json", _report_25d("BTCUSDT")),
        ("btc_25e.json", _report_25e("BTCUSDT")),
        ("eth_25d.json", _report_25d("ETHUSDT")),
        ("eth_25e.json", _report_25e("ETHUSDT")),
        ("unsafe_25f.json", unsafe),
    ])
    assert pack["decision"] == "FUTURES_BRANCH_CLOSURE_INCOMPLETE"
    assert "UNSAFE_APPROVAL_OR_MUTATION_DETECTED" in pack["reason_codes"]


def test_tool_writes_closure_report_from_input_json(tmp_path: Path) -> None:
    inputs: list[Path] = []
    for idx, payload in enumerate([
        _report_25b(),
        _report_25g(),
        _report_25d("BTCUSDT"),
        _report_25e("BTCUSDT"),
        _report_25d("ETHUSDT"),
        _report_25e("ETHUSDT"),
        _report_25f_final(),
    ]):
        path = tmp_path / f"report_{idx}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        inputs.append(path)
    cmd = [
        sys.executable,
        "tools/run_futures_branch_closure_evidence_pack_4B436625H.py",
        "--out-dir",
        str(tmp_path / "reports"),
        "--review-ok",
    ]
    for path in inputs:
        cmd.extend(["--input-json", str(path)])
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "FUTURES_BRANCH_CLOSURE_CONFIRMED" in result.stdout
    json_reports = list((tmp_path / "reports").glob("4B436625H_futures_branch_closure_evidence_pack_*.json"))
    md_reports = list((tmp_path / "reports").glob("4B436625H_futures_branch_closure_evidence_pack_*.md"))
    assert json_reports
    assert md_reports
    pack = json.loads(json_reports[0].read_text(encoding="utf-8"))
    assert pack["approved_for_live_real"] is False
