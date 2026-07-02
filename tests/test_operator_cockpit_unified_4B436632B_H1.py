from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradebot.operator_cockpit_unified import build_cockpit_snapshot, write_snapshot_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_snapshot_reads_31b_32a_32b_and_keeps_live_submit_locked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    shadow = tmp_path / "reports" / "hyp006_r1_canonical"
    _write_json(
        reports / "4B436631B_release_hygiene_bad_evidence_ledger_cleanup_20260622T000000Z_ready.json",
        {"decision": "RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_READY_FINAL_AUDIT_SNAPSHOT_NO_FURTHER_LIVE_ORDER"},
    )
    _write_json(
        reports / "4B436632A_post_freeze_release_candidate_review_20260622T000001Z_ready.json",
        {
            "decision": "POST_FREEZE_RELEASE_CANDIDATE_REVIEW_READY_SECOND_MICRO_CANARY_ELIGIBILITY_GATE_NO_LIVE_ORDER_SUBMIT",
            "capital_cap_usdt": 25,
            "second_micro_max_notional_usdt": 5,
            "daily_loss_limit_usdt": 5,
            "max_slippage_bps": 50,
            "emergency_stop_armed_verified": True,
        },
    )
    _write_json(
        reports / "4B436632B_second_micro_canary_submit_gate_20260622T000002Z_ready.json",
        {
            "decision": "SECOND_MICRO_CANARY_SUBMIT_GATE_READY_SUBMIT_REQUEST_EVIDENCE_NO_LIVE_ORDER_SUBMIT",
            "symbol": "ETHUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "candidate_qty": 0.0029,
            "candidate_notional_usdt": 4.968744,
            "reference_price": 1713.36,
            "exchange_submit_allowed": False,
            "network_submit_allowed": False,
            "approved_for_live_real_order": False,
            "approved_for_second_micro_order": False,
        },
    )
    shadow.mkdir(parents=True)
    (shadow / "hyp006_scheduler_stdout.log").write_text(
        " - read_only: True\n - approved_for_live_real: False\n - approved_for_paper_candidate: False\n - shadow_observation_count: 20\n - new_unique_shadow_observation_count: 20\n - mean_return_bps: 108.911085\n - profit_factor: 2.776782\n",
        encoding="utf-8",
    )
    (shadow / "4B436628D_hyp006_r1_shadow_observation_logger_20260622T000003Z.json").write_text("{}", encoding="utf-8")
    snapshot = build_cockpit_snapshot(tmp_path, include_status_endpoint=False)
    assert snapshot.latest_accepted_phase == "4B.4.3.6.6.32B"
    assert snapshot.live_micro_canary_state == "SECOND_MICRO_CANDIDATE_ONLY"
    assert snapshot.no_live_order_lock is True
    assert snapshot.approved_for_live_real_order is False
    assert snapshot.approved_for_second_micro_order is False
    assert snapshot.second_micro_candidate.candidate_qty == 0.0029
    assert snapshot.second_micro_candidate.candidate_notional_usdt == 4.968744
    assert snapshot.shadow_health.active is True


def test_not_ready_pattern_is_excluded(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    _write_json(
        reports / "4B436632B_second_micro_canary_submit_gate_20260622T000000Z_not_ready.json",
        {"decision": "NOT_READY_BAD"},
    )
    snapshot = build_cockpit_snapshot(tmp_path, include_status_endpoint=False)
    assert snapshot.phase_32b.verified is False
    assert snapshot.latest_accepted_phase == "UNKNOWN"


def test_write_snapshot_report(tmp_path: Path) -> None:
    out = write_snapshot_report(tmp_path)
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["contract_version"] == "4B.4.3.6.6.32B-H1"
    assert payload["approved_for_live_real_order"] is False
