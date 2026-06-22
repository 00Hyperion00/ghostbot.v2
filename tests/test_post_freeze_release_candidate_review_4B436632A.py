from __future__ import annotations

import json
from pathlib import Path

from tradebot.post_freeze_release_candidate_review import (
    CAPITAL_CAP_REQUIRED_DECISION,
    FINALIZATION_TOKEN,
    READY_DECISION,
    SOURCE_31B_CONTRACT_VERSION,
    SOURCE_31B_READY_DECISION,
    build_from_explicit_31b_report,
    build_from_latest_31b_report,
    evaluate_capital_cap_plan,
    evaluate_source_31b_release_hygiene,
    write_report_bundle,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _source_31b() -> dict[str, object]:
    return {
        "contract_version": SOURCE_31B_CONTRACT_VERSION,
        "decision": SOURCE_31B_READY_DECISION,
        "source_31a_h3_freeze_audit_closure_verified": True,
        "bad_evidence_history_explained": True,
        "bad_evidence_quarantined": True,
        "final_audit_snapshot_written": True,
        "no_further_live_orders_verified": True,
        "emergency_stop_continuity_verified": True,
        "no_code_path_live_submit_verified": True,
        "approved_for_additional_exchange_submit": False,
        "approved_for_live_real_continuation": False,
        "approved_for_live_real_order": False,
        "patch_network_submit_attempted": False,
        "patch_exchange_submit_performed": False,
        "patch_live_real_order_performed": False,
        "additional_exchange_submit_performed": False,
        "additional_network_submit_attempted": False,
        "additional_live_real_order_performed": False,
    }


def test_source_31b_requires_ready_and_no_submit() -> None:
    status = evaluate_source_31b_release_hygiene(_source_31b())
    assert status.ok is True
    broken = dict(_source_31b())
    broken["patch_network_submit_attempted"] = True
    assert evaluate_source_31b_release_hygiene(broken).ok is False


def test_capital_plan_enforces_second_micro_hard_caps() -> None:
    ok = evaluate_capital_cap_plan(
        capital_cap_usdt=25,
        second_micro_max_notional_usdt=5,
        daily_loss_limit_usdt=5,
        max_slippage_bps=50,
    )
    assert ok.ok is True
    bad = evaluate_capital_cap_plan(
        capital_cap_usdt=25,
        second_micro_max_notional_usdt=20,
        daily_loss_limit_usdt=5,
        max_slippage_bps=50,
    )
    assert bad.ok is False
    assert "SECOND_MICRO_MAX_NOTIONAL_REQUIRED_WITHIN_CAP_AND_HARD_LIMIT" in bad.reason_codes


def test_ready_review_is_candidate_only_no_live_order(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    source = reports / "4B436631B_release_hygiene_bad_evidence_ledger_cleanup_20260622T101501Z_ready.json"
    _write_json(source, _source_31b())
    payload = build_from_explicit_31b_report(
        reports_dir=reports,
        source_31b_report=source,
        operator_id="operator-32a",
        finalization_token=FINALIZATION_TOKEN,
        audit_comment="unit test",
        emergency_stop_armed=True,
        capital_cap_usdt=25,
        second_micro_max_notional_usdt=5,
        daily_loss_limit_usdt=5,
        max_slippage_bps=50,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_live_real_continuation_candidate"] is True
    assert payload["approved_for_second_micro_canary_eligibility_gate"] is True
    assert payload["approved_for_live_real_order"] is False
    assert payload["approved_for_second_micro_canary_order_submit"] is False
    assert payload["patch_network_submit_attempted"] is False


def test_latest_source_discovery_and_report_bundle(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    source = reports / "4B436631B_release_hygiene_bad_evidence_ledger_cleanup_20260622T101501Z_ready.json"
    _write_json(source, _source_31b())
    payload = build_from_latest_31b_report(
        reports_dir=reports,
        operator_id="operator-32a",
        finalization_token=FINALIZATION_TOKEN,
        audit_comment="latest unit test",
        emergency_stop_armed=True,
        capital_cap_usdt=25,
        second_micro_max_notional_usdt=5,
        daily_loss_limit_usdt=5,
        max_slippage_bps=50,
    )
    json_path, md_path = write_report_bundle(payload, reports_dir=reports)
    assert payload["decision"] == READY_DECISION
    assert json_path.exists()
    assert md_path.exists()
    stored = json.loads(json_path.read_text(encoding="utf-8"))
    assert stored["second_micro_canary_eligible_candidate"] is True


def test_missing_capital_blocks_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    source = reports / "4B436631B_release_hygiene_bad_evidence_ledger_cleanup_20260622T101501Z_ready.json"
    _write_json(source, _source_31b())
    payload = build_from_explicit_31b_report(
        reports_dir=reports,
        source_31b_report=source,
        operator_id="operator-32a",
        finalization_token=FINALIZATION_TOKEN,
        emergency_stop_armed=True,
    )
    assert payload["decision"] == CAPITAL_CAP_REQUIRED_DECISION
    assert payload["approved_for_live_real_order"] is False
