from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_sandbox_dry_run_transition_plan import (
    READY_DECISION,
    SOURCE_30E_REQUIRED_DECISION,
    build_from_latest_30e_ready_report,
    build_paper_sandbox_dry_run_transition_plan_snapshot,
    write_report_bundle,
)


def ready_30e_snapshot() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30E",
        "decision": "PAPER_TRANSITION_REVIEW_RERUN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED",
        "approved_for_paper_transition_review_rerun": True,
        "approved_for_paper_transition_candidate_review": True,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "paper_live_order_enablement_present": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "rerun_30c_snapshot": {
            "runtime_envelope_freeze": {
                "runtime_envelope": "sandbox_only",
                "execution_mode": "dry_run",
                "market_type": "spot_demo",
                "base_url": "https://demo-api.binance.com",
                "auto_trade_on_signal": False,
                "live_trading_armed": False,
                "live_real_double_confirm": False,
                "max_open_orders": 1,
            }
        },
    }


def test_missing_30e_ready_evidence_blocks_plan(tmp_path) -> None:
    payload = build_from_latest_30e_ready_report(Settings(), tmp_path)
    assert payload["decision"] == SOURCE_30E_REQUIRED_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_transition_plan"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["paper_order_enablement_still_blocked"] is True


def test_ready_30e_yields_transition_plan_only() -> None:
    payload = build_paper_sandbox_dry_run_transition_plan_snapshot(Settings(), ready_30e_snapshot(), source_report_path="30e-ready.json")
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_transition_plan"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution_plan"] is True
    assert payload["approved_for_order_path_simulation_envelope"] is True
    assert payload["approved_for_operator_final_go_no_go_checklist"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_paper_transition_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["runtime_activation_blocked"] is True
    assert payload["trading_action_performed"] is False


def test_live_real_source_is_rejected() -> None:
    source = ready_30e_snapshot()
    source["approved_for_live_real"] = True
    payload = build_paper_sandbox_dry_run_transition_plan_snapshot(Settings(), source)
    assert payload["decision"] != READY_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_transition_plan"] is False
    assert "SOURCE_30E_LIVE_REAL_UNEXPECTEDLY_APPROVED" in payload["reason_codes"]
    assert payload["approved_for_live_real"] is False


def test_report_collision_guard(tmp_path) -> None:
    payload = build_paper_sandbox_dry_run_transition_plan_snapshot(Settings(), ready_30e_snapshot())
    first_json, first_md = write_report_bundle(payload, tmp_path)
    second_json, second_md = write_report_bundle(payload, tmp_path)
    assert first_json != second_json
    assert first_md != second_md
    assert first_json.exists()
    assert second_json.exists()
