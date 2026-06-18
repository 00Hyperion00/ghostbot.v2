from __future__ import annotations

from tradebot.hyp006_no_order_overlay_simulation_bnbusdt import (
    CONTRACT_VERSION,
    build_no_order_overlay_simulation_bnbusdt_report,
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
    status: str = "ACCEPTED_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_CANDIDATE",
) -> dict[str, object]:
    predicate: dict[str, object]
    if category == "symbol":
        predicate = {"type": "symbol_whitelist", "include_symbols": [key]}
    elif category == "gate_combo":
        predicate = {"type": "failed_gate_combo_match", "failed_gate_combo": key}
    else:
        predicate = {"type": "risk_bucket_match", "risk_bucket": key}
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
        "net_return_bps": mean_return_bps * matured_count,
        "review_score": mean_return_bps,
        "tail_risk_flag": tail_risk_flag,
        "tail_risk_reasons": ["WORST_RETURN_TAIL_RISK"] if tail_risk_flag else [],
        "ranking_guard_reasons": [],
        "research_only_counterfactual_candidate": True,
        "overlay_class": "SYMBOL_FILTER_SHADOW_OVERLAY" if category == "symbol" else "GATE_COMBO_FILTER_SHADOW_OVERLAY",
        "overlay_predicate": predicate,
        "overlay_status": status,
        "runtime_activation_allowed": False,
        "parameter_relaxation_allowed": False,
        "paper_live_order_allowed": False,
    }


def _h6_payload() -> dict[str, object]:
    primary = _candidate(
        "symbol",
        "BNBUSDT",
        matured_count=12,
        win_rate_pct=75.0,
        mean_return_bps=101.112266,
        profit_factor=4.267537,
        worst_return_bps=-312.205541,
        worst_mae_bps=-426.691375,
    )
    quarantine = _candidate(
        "gate_combo",
        "MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS",
        matured_count=17,
        win_rate_pct=70.58,
        mean_return_bps=160.48,
        profit_factor=2.95,
        worst_return_bps=-434.01,
        worst_mae_bps=-447.53,
        tail_risk_flag=True,
        status="QUARANTINE_REVIEW_ONLY_TAIL_RISK",
    )
    watchlist = _candidate(
        "gate_combo",
        "MIN_WICK_PCT_REFERENCE + MAX_COMPRESSION_RATIO_REFERENCE",
        matured_count=9,
        win_rate_pct=77.77,
        mean_return_bps=258.04,
        profit_factor=18.7,
        worst_return_bps=-120.6,
        worst_mae_bps=-209.0,
        status="WATCHLIST_LOW_SAMPLE_NOT_PROMOTABLE",
    )
    blocklist = _candidate(
        "gate_combo",
        "RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE",
        matured_count=38,
        win_rate_pct=34.21,
        mean_return_bps=-15.76,
        profit_factor=0.84,
        worst_return_bps=-455.58,
        worst_mae_bps=-598.24,
        tail_risk_flag=True,
        status="DO_NOT_RELAX_BLOCKLIST",
    )
    return {
        "contract_version": "4B.4.3.6.6.28G-H6",
        "branch_id": "HYP-006-R1",
        "branch_name": "failed_downside_sweep_reversal_continuation_short",
        "hypothesis_id": "HYP-006",
        "strategy_family": "short_failed_liquidity_sweep_continuation",
        "timeframe": "4h",
        "read_only": True,
        "filter_shadow_overlay_design_only": True,
        "approved_for_filter_shadow_overlay_candidate": True,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "accepted_primary_overlay_candidate_count": 1,
        "quarantine_review_candidate_count": 1,
        "watchlist_overlay_candidate_count": 1,
        "do_not_relax_blocklist_count": 1,
        "accepted_primary_overlay_candidates": [primary],
        "quarantine_review_candidates": [quarantine],
        "watchlist_low_sample_overlay_candidates": [watchlist],
        "do_not_relax_gate_combo_blocklist": [blocklist],
        "rejected_overlay_candidates": [],
    }


def test_h7_builds_bnbusdt_measurement_and_keeps_all_runtime_gates_closed() -> None:
    payload = build_no_order_overlay_simulation_bnbusdt_report(_h6_payload())
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["decision"] == "NO_ORDER_BNBUSDT_PRIMARY_OVERLAY_SHADOW_MEASUREMENT_READY"
    assert payload["read_only"] is True
    assert payload["approved_for_overlay_shadow_measurement"] is True
    assert payload["approved_for_runtime_overlay_activation_candidate"] is False
    assert payload["approved_for_parameter_relaxation_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["runtime_overlay_activation_performed"] is False
    assert payload["training_performed"] is False
    assert payload["reload_performed"] is False
    assert payload["trading_action_performed"] is False
    assert payload["order_actions_performed"] is False

    candidate = payload["primary_measurement_candidate"]
    assert candidate["key"] == "BNBUSDT"
    assert candidate["measurement_guard_pass"] is True
    assert candidate["runtime_overlay_activation_allowed"] is False
    assert candidate["parameter_relaxation_allowed"] is False
    assert payload["excluded_quarantine_candidates"][0]["key"] == "MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS"
    assert payload["excluded_watchlist_candidates"][0]["key"] == "MIN_WICK_PCT_REFERENCE + MAX_COMPRESSION_RATIO_REFERENCE"
    assert payload["enforced_do_not_relax_blocklist"][0]["key"] == "RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE"


def test_invalid_h6_source_blocks_measurement() -> None:
    h6 = _h6_payload()
    h6["contract_version"] = "BAD"
    payload = build_no_order_overlay_simulation_bnbusdt_report(h6)
    assert payload["ok"] is False
    assert "SOURCE_H6_CONTRACT_VERSION_MISMATCH" in payload["blockers"]
    assert payload["approved_for_overlay_shadow_measurement"] is False
    assert payload["approved_for_parameter_relaxation_candidate"] is False


def test_missing_bnbusdt_primary_candidate_blocks_measurement() -> None:
    h6 = _h6_payload()
    h6["accepted_primary_overlay_candidates"] = []
    payload = build_no_order_overlay_simulation_bnbusdt_report(h6)
    assert payload["ok"] is False
    assert "BNBUSDT_PRIMARY_OVERLAY_CANDIDATE_NOT_FOUND" in payload["blockers"]
    assert payload["primary_measurement_candidate_count"] == 0
    assert payload["approved_for_overlay_shadow_measurement"] is False
    assert payload["approved_for_runtime_overlay_activation_candidate"] is False
