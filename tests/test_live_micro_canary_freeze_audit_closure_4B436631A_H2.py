from __future__ import annotations

import json
from pathlib import Path

from tradebot.config import Settings
from tradebot.live_micro_canary_freeze_audit_closure import (
    FINALIZATION_TOKEN,
    READY_DECISION,
    SOURCE_30Z_REQUIRED_DECISION,
    build_from_latest_30z_risk_review_report,
    build_live_micro_canary_freeze_audit_closure_snapshot,
    cleanup_bad_31a_not_ready_artifacts,
    evaluate_source_30z_risk_review,
    write_report_bundle,
)


def compact_30z_summary() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30Z",
        "decision": "POST_LIVE_MICRO_CANARY_RISK_REVIEW_READY_PNL_FEE_SLIPPAGE_EMERGENCY_STOP_NO_ADDITIONAL_LIVE_ORDER",
        "ok": True,
        "source_30y_h1_reconciliation_verified": True,
        "real_fill_risk_review_verified": True,
        "pnl_evidence_verified": True,
        "fee_evidence_verified": True,
        "slippage_evidence_verified": True,
        "emergency_stop_continuity_verified": True,
        "no_additional_live_order_verified": True,
        "approved_for_additional_exchange_submit": False,
        "approved_for_live_real_continuation": False,
        "patch_exchange_submit_performed": False,
        "patch_network_submit_attempted": False,
    }


def seed_evidence_pack(root: Path, source: dict[str, object]) -> None:
    (root / "4B436630X_first_live_real_micro_canary_1_ready.json").write_text("{}", encoding="utf-8")
    (root / "4B436630Y_live_real_micro_canary_reconciliation_1_ready.json").write_text("{}", encoding="utf-8")
    (root / "4B436630Z_post_live_micro_canary_risk_review_20260622T081654Z_ready.json").write_text(json.dumps(source), encoding="utf-8")


def test_compact_30z_ready_summary_is_accepted() -> None:
    status = evaluate_source_30z_risk_review(compact_30z_summary())
    assert status.ok is True
    assert status.mismatch_count == 0
    assert status.pnl_review_verified is True
    assert status.fee_review_verified is True
    assert status.slippage_review_verified is True


def test_latest_compact_30z_ready_can_close_31a_h2(tmp_path: Path) -> None:
    seed_evidence_pack(tmp_path, compact_30z_summary())
    payload = build_from_latest_30z_risk_review_report(
        Settings(),
        tmp_path,
        operator_id="operator-31a",
        finalization_token=FINALIZATION_TOKEN,
        evidence_pack_id="LIVE_MICRO_CANARY_8114595899_CLOSURE_H2",
        acknowledge_hyp006_report_separation=True,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["source_30z_risk_review_verified"] is True
    assert payload["no_further_live_orders_verified"] is True
    assert payload["approved_for_additional_exchange_submit"] is False
    assert payload["patch_network_submit_attempted"] is False
    json_path, md_path = write_report_bundle(payload, tmp_path)
    assert json_path.name.endswith("_ready.json")
    assert md_path.exists()
    assert len(list(tmp_path.glob("4B436631A_live_micro_canary_freeze_audit_closure_*_evidence_pack_manifest.json"))) == 1


def test_not_ready_does_not_write_manifest(tmp_path: Path) -> None:
    payload = build_live_micro_canary_freeze_audit_closure_snapshot(
        Settings(),
        {},
        reports_dir=tmp_path,
        operator_id="operator-31a",
        finalization_token=FINALIZATION_TOKEN,
        evidence_pack_id="BAD",
        acknowledge_hyp006_report_separation=True,
    )
    assert payload["decision"] == SOURCE_30Z_REQUIRED_DECISION
    write_report_bundle(payload, tmp_path)
    assert len(list(tmp_path.glob("*_not_ready.json"))) == 1
    assert len(list(tmp_path.glob("*_evidence_pack_manifest.json"))) == 0


def test_cleanup_bad_31a_not_ready_artifacts(tmp_path: Path) -> None:
    for suffix in ("not_ready.json", "not_ready.md", "evidence_pack_manifest.json"):
        (tmp_path / f"4B436631A_live_micro_canary_freeze_audit_closure_20260622T000000Z_{suffix}").write_text("x", encoding="utf-8")
    removed = cleanup_bad_31a_not_ready_artifacts(tmp_path)
    assert len(removed) == 3
    assert not list(tmp_path.glob("4B436631A_live_micro_canary_freeze_audit_closure_*"))
