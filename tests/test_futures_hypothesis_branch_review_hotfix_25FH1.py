from __future__ import annotations

from tradebot.futures_hypothesis_branch_review import (
    FUTURES_BRANCH_REVIEW_HOTFIX_VERSION,
    build_futures_hypothesis_branch_review,
    normalize_report_candidates,
)


def _report_25b() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25B",
        "decision": "PASS",
        "candidates": [
            {"decision": "PASS", "symbol": "BTCUSDT", "interval": "4h", "strategy": "funding_trend_exhaustion", "signals": 33, "mean_edge_bps": 53.704409, "median_edge_bps": 56.665439, "profit_factor": 2.154669, "reasons": []},
            {"decision": "PASS", "symbol": "ETHUSDT", "interval": "4h", "strategy": "funding_trend_exhaustion", "signals": 31, "mean_edge_bps": 44.125478, "median_edge_bps": 139.2081, "profit_factor": 1.584716, "reasons": []},
        ],
    }


def _actual_25d_report(symbol: str) -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25D",
        "phase": "4B.4.3.6.6.25D",
        "report_type": "futures_research_candidate_dry_run_signal_simulator",
        "decision": "BLOCK",
        "selected": {
            "symbol": symbol,
            "interval": "4h",
            "strategy": "funding_trend_exhaustion",
            "mean_net_edge_bps": 69.5964,
            "profit_factor": 1.907343,
            "signal_count": 36,
        },
        "reason_codes": ["NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED", "DRY_RUN_OOS_EDGE_LOW"],
        "candidate": {
            "metrics": {
                "signal_count": 36,
                "mean_net_edge_bps": 69.5964,
                "median_net_edge_bps": 96.251131,
                "profit_factor": 1.907343,
                "oos_mean_net_edge_bps": -12.0,
            }
        },
    }


def _actual_25e_report(symbol: str) -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25E",
        "phase": "4B.4.3.6.6.25E",
        "report_type": "futures_candidate_refinement_median_edge_recovery",
        "decision": "BLOCK",
        "candidate_spec": {"symbol": symbol, "interval": "4h", "strategy": "funding_trend_exhaustion"},
        "selected_filter": "funding_extreme_strict",
        "selected_mean_net_edge_bps": -14.276254,
        "selected_median_net_edge_bps": -6.063459,
        "selected_profit_factor": 0.637968,
        "selected_signal_count": 34,
        "selected": {
            "filter": {"name": "funding_extreme_strict"},
            "metrics": {
                "signal_count": 34,
                "mean_net_edge_bps": -14.276254,
                "median_net_edge_bps": -6.063459,
                "profit_factor": 0.637968,
            },
        },
        "reason_codes": [
            "NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED",
            "REFINEMENT_MEAN_EDGE_LOW",
            "REFINEMENT_MEDIAN_EDGE_LOW",
            "REFINEMENT_OOS_EDGE_LOW",
            "REFINEMENT_PROFIT_FACTOR_LOW",
            "REFINEMENT_WALK_FORWARD_STABILITY_LOW",
        ],
    }


def test_25fh1_normalizes_actual_25d_selected_mapping() -> None:
    candidates = normalize_report_candidates(_actual_25d_report("ETHUSDT"), "25d_eth.json")
    assert FUTURES_BRANCH_REVIEW_HOTFIX_VERSION == "4B.4.3.6.6.25F-H1"
    assert any(c.symbol == "ETHUSDT" and c.source_phase == "25D" and c.signal_count == 36 for c in candidates)
    eth = next(c for c in candidates if c.symbol == "ETHUSDT")
    assert eth.median_net_edge_bps == 96.251131
    assert "DRY_RUN_OOS_EDGE_LOW" in eth.reason_codes


def test_25fh1_normalizes_actual_25e_candidate_spec_selected_metrics() -> None:
    candidates = normalize_report_candidates(_actual_25e_report("ETHUSDT"), "25e_eth.json")
    eth = next(c for c in candidates if c.symbol == "ETHUSDT" and c.source_phase == "25E")
    assert eth.signal_count == 34
    assert eth.mean_net_edge_bps == -14.276254
    assert eth.median_net_edge_bps == -6.063459
    assert "REFINEMENT_MEDIAN_EDGE_LOW" in eth.reason_codes


def test_25fh1_closes_branch_when_primary_and_actual_companion_terminal_audits_block() -> None:
    report = build_futures_hypothesis_branch_review([
        _report_25b(),
        _actual_25d_report("BTCUSDT"),
        _actual_25e_report("BTCUSDT"),
        _actual_25d_report("ETHUSDT"),
        _actual_25e_report("ETHUSDT"),
    ])
    assert report.decision == "BRANCH_CLOSED_NO_GO"
    assert "COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED" not in report.reason_codes
    assert "FUTURES_BRANCH_NO_ROBUST_DRY_RUN_CANDIDATE" in report.reason_codes
    assert report.approved_for_research_candidate is False
    assert report.approved_for_training_candidate is False
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False
