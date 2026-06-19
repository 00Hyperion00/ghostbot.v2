from __future__ import annotations

from tradebot.hyp006_bnbusdt_overlay_oos_evaluation import (
    CONTRACT_VERSION,
    build_bnbusdt_overlay_oos_evaluation_report,
)


def _h7_payload(
    *,
    matured_count: int,
    event_count: int,
    win_rate_pct: float,
    mean_return_bps: float,
    median_return_bps: float,
    profit_factor: float,
    worst_return_bps: float,
    worst_mae_bps: float,
    guard_pass: bool = True,
) -> dict[str, object]:
    summary = {
        "symbol": "BNBUSDT",
        "measurement_candidate_present": True,
        "measurement_guard_pass": guard_pass,
        "measurement_guard_reasons": [] if guard_pass else ["WIN_RATE_BELOW_MEASUREMENT_MIN"],
        "event_count": event_count,
        "matured_count": matured_count,
        "win_rate_pct": win_rate_pct,
        "mean_return_bps": mean_return_bps,
        "median_return_bps": median_return_bps,
        "profit_factor": profit_factor,
        "worst_return_bps": worst_return_bps,
        "worst_mae_bps": worst_mae_bps,
        "net_return_bps": mean_return_bps * matured_count,
    }
    return {
        "contract_version": "4B.4.3.6.6.28G-H7",
        "branch_id": "HYP-006-R1",
        "branch_name": "failed_downside_sweep_reversal_continuation_short",
        "hypothesis_id": "HYP-006",
        "strategy_family": "short_failed_liquidity_sweep_continuation",
        "timeframe": "4h",
        "decision": "NO_ORDER_BNBUSDT_PRIMARY_OVERLAY_SHADOW_MEASUREMENT_READY",
        "read_only": True,
        "overlay_simulation_measurement_only": True,
        "approved_for_overlay_shadow_measurement": guard_pass,
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "primary_measurement_summary": summary,
        "primary_measurement_candidate": {
            "key": "BNBUSDT",
            "category": "symbol",
            "measurement_symbol": "BNBUSDT",
            "measurement_guard_pass": guard_pass,
            **summary,
        },
    }


def test_h8_passes_oos_delta_but_blocks_runtime_activation() -> None:
    previous = _h7_payload(
        matured_count=12,
        event_count=12,
        win_rate_pct=75.0,
        mean_return_bps=101.112266,
        median_return_bps=117.270557,
        profit_factor=4.267537,
        worst_return_bps=-312.205541,
        worst_mae_bps=-426.691375,
    )
    latest = _h7_payload(
        matured_count=13,
        event_count=13,
        win_rate_pct=76.923077,
        mean_return_bps=126.61364,
        median_return_bps=142.929363,
        profit_factor=5.432608,
        worst_return_bps=-312.205541,
        worst_mae_bps=-426.691375,
    )
    report = build_bnbusdt_overlay_oos_evaluation_report(latest, previous)
    assert report["contract_version"] == CONTRACT_VERSION
    assert report["decision"] == "HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_READY_RUNTIME_ACTIVATION_BLOCKED"
    assert report["approved_for_bnbusdt_oos_evaluation"] is True
    assert report["approved_for_oos_monitoring_continuation"] is True
    assert report["approved_for_runtime_overlay_activation_candidate"] is False
    assert report["approved_for_runtime_overlay_activation"] is False
    assert report["approved_for_parameter_relaxation_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["runtime_overlay_activation_performed"] is False
    assert report["training_performed"] is False
    assert report["reload_performed"] is False
    assert report["trading_action_performed"] is False
    assert report["order_actions_performed"] is False
    assert report["oos_guard_pass"] is True
    assert report["oos_delta_summary"]["matured_count_delta"] == 1
    assert report["oos_delta_summary"]["event_count_delta"] == 1


def test_h8_blocks_when_no_new_matured_sample() -> None:
    previous = _h7_payload(
        matured_count=13,
        event_count=13,
        win_rate_pct=76.923077,
        mean_return_bps=126.61364,
        median_return_bps=142.929363,
        profit_factor=5.432608,
        worst_return_bps=-312.205541,
        worst_mae_bps=-426.691375,
    )
    latest = _h7_payload(
        matured_count=13,
        event_count=13,
        win_rate_pct=76.923077,
        mean_return_bps=126.61364,
        median_return_bps=142.929363,
        profit_factor=5.432608,
        worst_return_bps=-312.205541,
        worst_mae_bps=-426.691375,
    )
    report = build_bnbusdt_overlay_oos_evaluation_report(latest, previous)
    assert report["ok"] is True
    assert report["oos_guard_pass"] is False
    assert "MATURED_COUNT_DELTA_BELOW_OOS_MIN" in report["oos_guard_reasons"]
    assert report["approved_for_bnbusdt_oos_evaluation"] is False
    assert report["approved_for_runtime_overlay_activation_candidate"] is False


def test_h8_blocks_bad_source_contract_and_keeps_all_gates_closed() -> None:
    previous = _h7_payload(
        matured_count=12,
        event_count=12,
        win_rate_pct=75.0,
        mean_return_bps=101.112266,
        median_return_bps=117.270557,
        profit_factor=4.267537,
        worst_return_bps=-312.205541,
        worst_mae_bps=-426.691375,
    )
    latest = _h7_payload(
        matured_count=13,
        event_count=13,
        win_rate_pct=76.923077,
        mean_return_bps=126.61364,
        median_return_bps=142.929363,
        profit_factor=5.432608,
        worst_return_bps=-312.205541,
        worst_mae_bps=-426.691375,
    )
    latest["contract_version"] = "BAD"
    report = build_bnbusdt_overlay_oos_evaluation_report(latest, previous)
    assert report["ok"] is False
    assert "LATEST_SOURCE_H7_CONTRACT_VERSION_MISMATCH" in report["blockers"]
    assert report["approved_for_bnbusdt_oos_evaluation"] is False
    assert report["approved_for_runtime_overlay_activation_candidate"] is False
    assert report["approved_for_parameter_relaxation_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
