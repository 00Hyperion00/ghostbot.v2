from __future__ import annotations

from tradebot.hyp006_no_order_filter_shadow_overlay_design import (
    CONTRACT_VERSION,
    build_no_order_filter_shadow_overlay_design_report,
)


def _candidate(
    category: str,
    key: str,
    *,
    matured_count: int,
    win_rate_pct: float,
    mean_return_bps: float,
    profit_factor: float,
    worst_return_bps: float,
    worst_mae_bps: float,
    tail_risk_flag: bool = False,
) -> dict[str, object]:
    return {
        "category": category,
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
        "review_score": mean_return_bps,
        "tail_risk_flag": tail_risk_flag,
        "tail_risk_reasons": ["WORST_RETURN_TAIL_RISK"] if tail_risk_flag else [],
        "ranking_guard_reasons": [],
        "research_only_counterfactual_candidate": True,
    }


def _h5_payload() -> dict[str, object]:
    bnb = _candidate(
        "symbol",
        "BNBUSDT",
        matured_count=12,
        win_rate_pct=75.0,
        mean_return_bps=101.11,
        profit_factor=4.26,
        worst_return_bps=-312.20,
        worst_mae_bps=-426.69,
    )
    combo_tail = _candidate(
        "gate_combo",
        "MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS",
        matured_count=17,
        win_rate_pct=70.58,
        mean_return_bps=160.48,
        profit_factor=2.95,
        worst_return_bps=-434.01,
        worst_mae_bps=-447.53,
        tail_risk_flag=True,
    )
    bucket_tail = _candidate(
        "risk_bucket",
        "HIGH_COMPRESSION_AND_SLIPPAGE",
        matured_count=17,
        win_rate_pct=70.58,
        mean_return_bps=160.48,
        profit_factor=2.95,
        worst_return_bps=-434.01,
        worst_mae_bps=-447.53,
        tail_risk_flag=True,
    )
    watchlist = _candidate(
        "gate_combo",
        "MIN_WICK_PCT_REFERENCE + MAX_COMPRESSION_RATIO_REFERENCE",
        matured_count=9,
        win_rate_pct=77.77,
        mean_return_bps=258.04,
        profit_factor=18.7,
        worst_return_bps=-120.6,
        worst_mae_bps=-300.0,
    )
    blocklist = _candidate(
        "gate_combo",
        "RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE",
        matured_count=38,
        win_rate_pct=34.21,
        mean_return_bps=-15.76,
        profit_factor=0.84,
        worst_return_bps=-455.58,
        worst_mae_bps=-490.0,
    )
    return {
        "contract_version": "4B.4.3.6.6.28G-H5",
        "branch_id": "HYP-006-R1",
        "branch_name": "failed_downside_sweep_reversal_continuation_short",
        "hypothesis_id": "HYP-006",
        "strategy_family": "short_failed_liquidity_sweep_continuation",
        "read_only": True,
        "approved_for_filter_candidate_review": True,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "candidate_row_count": 5,
        "accepted_review_candidates": [bnb, combo_tail, bucket_tail],
        "tail_risk_flags": [combo_tail, bucket_tail],
        "watchlist_low_sample_candidates": [watchlist],
        "rejected_counterfactual_candidates": [blocklist],
        "do_not_relax_gate_combos": [blocklist],
    }


def test_build_overlay_design_quarantines_tail_risk_and_keeps_bnb_primary() -> None:
    payload = build_no_order_filter_shadow_overlay_design_report(_h5_payload())
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["decision"] == "HYP006_R1_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_READY"
    assert payload["read_only"] is True
    assert payload["filter_shadow_overlay_design_only"] is True
    assert payload["approved_for_filter_shadow_overlay_candidate"] is True
    assert payload["approved_for_quarantine_review_candidate"] is True
    assert payload["approved_for_parameter_relaxation_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["runtime_overlay_activation_performed"] is False
    assert payload["training_performed"] is False
    assert payload["reload_performed"] is False
    assert payload["trading_action_performed"] is False
    assert payload["order_actions_performed"] is False

    primary_keys = {row["key"] for row in payload["accepted_primary_overlay_candidates"]}
    quarantine_keys = {row["key"] for row in payload["quarantine_review_candidates"]}
    blocklist_keys = {row["key"] for row in payload["do_not_relax_gate_combo_blocklist"]}
    watchlist_keys = {row["key"] for row in payload["watchlist_low_sample_overlay_candidates"]}

    assert primary_keys == {"BNBUSDT"}
    assert "MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS" in quarantine_keys
    assert "HIGH_COMPRESSION_AND_SLIPPAGE" in quarantine_keys
    assert "RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE" in blocklist_keys
    assert "MIN_WICK_PCT_REFERENCE + MAX_COMPRESSION_RATIO_REFERENCE" in watchlist_keys


def test_invalid_source_blocks_overlay_design() -> None:
    h5 = _h5_payload()
    h5["contract_version"] = "BAD"
    payload = build_no_order_filter_shadow_overlay_design_report(h5)
    assert payload["ok"] is False
    assert "SOURCE_H5_CONTRACT_VERSION_MISMATCH" in payload["blockers"]
    assert payload["approved_for_filter_shadow_overlay_candidate"] is False
    assert payload["approved_for_parameter_relaxation_candidate"] is False


def test_no_primary_candidate_stays_closed_but_report_ready() -> None:
    h5 = _h5_payload()
    h5["accepted_review_candidates"] = h5["tail_risk_flags"]
    payload = build_no_order_filter_shadow_overlay_design_report(h5)
    assert payload["ok"] is True
    assert payload["accepted_primary_overlay_candidate_count"] == 0
    assert payload["quarantine_review_candidate_count"] == 2
    assert payload["approved_for_filter_shadow_overlay_candidate"] is False
    assert payload["approved_for_parameter_relaxation_candidate"] is False
