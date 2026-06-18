from __future__ import annotations

from tradebot.hyp006_counterfactual_filter_candidate_ranking import (
    CONTRACT_VERSION,
    build_counterfactual_filter_candidate_ranking_report,
)


def _summary_row(
    key: str,
    *,
    matured_count: int,
    win_rate_pct: float,
    mean_return_bps: float,
    profit_factor: float,
    worst_return_bps: float,
    worst_mae_bps: float,
) -> dict[str, object]:
    return {
        "key": key,
        "event_count": matured_count,
        "matured_count": matured_count,
        "win_rate_pct": win_rate_pct,
        "mean_return_bps": mean_return_bps,
        "median_return_bps": mean_return_bps,
        "profit_factor": profit_factor,
        "worst_return_bps": worst_return_bps,
        "worst_mae_bps": worst_mae_bps,
        "best_return_bps": max(mean_return_bps, 1.0),
        "net_return_bps": mean_return_bps * matured_count,
        "research_only_counterfactual_candidate": True,
    }


def _h4_payload() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.28G-H4",
        "branch_id": "HYP-006-R1",
        "branch_name": "failed_downside_sweep_reversal_continuation_short",
        "hypothesis_id": "HYP-006",
        "strategy_family": "short_failed_liquidity_sweep_continuation",
        "read_only": True,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "attributed_near_miss_event_count": 42,
        "matured_near_miss_event_count": 42,
        "near_miss_outcome_summary": {"mean_return_bps": 50.0, "win_rate_pct": 50.0},
        "gate_combo_outcome_summary": [
            _summary_row(
                "MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS",
                matured_count=17,
                win_rate_pct=70.58,
                mean_return_bps=160.48,
                profit_factor=2.95,
                worst_return_bps=-434.01,
                worst_mae_bps=-447.53,
            ),
            _summary_row(
                "MIN_WICK_PCT_REFERENCE + MAX_COMPRESSION_RATIO_REFERENCE",
                matured_count=9,
                win_rate_pct=77.77,
                mean_return_bps=258.04,
                profit_factor=18.7,
                worst_return_bps=-120.60,
                worst_mae_bps=-300.0,
            ),
            _summary_row(
                "RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE",
                matured_count=38,
                win_rate_pct=34.21,
                mean_return_bps=-15.76,
                profit_factor=0.84,
                worst_return_bps=-455.58,
                worst_mae_bps=-490.0,
            ),
        ],
        "symbol_outcome_summary": [
            _summary_row(
                "BNBUSDT",
                matured_count=12,
                win_rate_pct=75.0,
                mean_return_bps=101.11,
                profit_factor=4.26,
                worst_return_bps=-312.20,
                worst_mae_bps=-426.69,
            )
        ],
        "risk_bucket_outcome_summary": [
            _summary_row(
                "HIGH_COMPRESSION_AND_SLIPPAGE",
                matured_count=17,
                win_rate_pct=70.58,
                mean_return_bps=160.48,
                profit_factor=2.95,
                worst_return_bps=-434.01,
                worst_mae_bps=-447.53,
            )
        ],
    }


def test_build_report_ranks_candidates_and_stays_fail_closed() -> None:
    payload = build_counterfactual_filter_candidate_ranking_report(_h4_payload())
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["decision"] == "HYP006_R1_COUNTERFACTUAL_FILTER_CANDIDATE_RANKING_READY"
    assert payload["read_only"] is True
    assert payload["counterfactual_research_only"] is True
    assert payload["approved_for_filter_candidate_review"] is True
    assert payload["approved_for_parameter_relaxation_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["training_performed"] is False
    assert payload["reload_performed"] is False
    assert payload["trading_action_performed"] is False
    assert payload["order_actions_performed"] is False
    accepted_keys = {row["key"] for row in payload["accepted_review_candidates"]}
    assert "MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS" in accepted_keys
    assert "BNBUSDT" in accepted_keys
    watchlist_keys = {row["key"] for row in payload["watchlist_low_sample_candidates"]}
    assert "MIN_WICK_PCT_REFERENCE + MAX_COMPRESSION_RATIO_REFERENCE" in watchlist_keys
    blocked_keys = {row["key"] for row in payload["do_not_relax_gate_combos"]}
    assert "RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE" in blocked_keys


def test_invalid_source_blocks_report() -> None:
    h4 = _h4_payload()
    h4["contract_version"] = "BAD"
    payload = build_counterfactual_filter_candidate_ranking_report(h4)
    assert payload["ok"] is False
    assert "SOURCE_H4_CONTRACT_VERSION_MISMATCH" in payload["blockers"]
    assert payload["approved_for_parameter_relaxation_candidate"] is False


def test_no_rows_blocks_report() -> None:
    h4 = _h4_payload()
    h4["gate_combo_outcome_summary"] = []
    h4["symbol_outcome_summary"] = []
    h4["risk_bucket_outcome_summary"] = []
    payload = build_counterfactual_filter_candidate_ranking_report(h4)
    assert payload["ok"] is False
    assert "SOURCE_H4_NO_OUTCOME_SUMMARY_ROWS" in payload["blockers"]
    assert payload["approved_for_paper_candidate"] is False
