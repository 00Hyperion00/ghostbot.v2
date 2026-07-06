from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_actual_no_order_soak_acceptance_review import evaluate


def _seed_phase44_ready(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "4B436644_phase44_no_order_soak_evidence_acceptance_bundle_seed_ready.json"
    path.write_text(json.dumps({
        "ok": True,
        "status": "READY",
        "patch_id": "4B436644",
        "patch_version": "4B.4.3.6.6.44",
        "decision": "PHASE44_NO_ORDER_SOAK_EVIDENCE_ACCEPTANCE_BUNDLE_READY_ACCEPTANCE_REVIEW_ONLY_SOAK_EVIDENCE_NOT_ACCEPTED_BY_PATCH_NO_PAPER_ORDER_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED",
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "network_order_submit_performed": False,
        "paper_order_submit_performed": False,
        "final_safety_violation_count": 0,
    }), encoding="utf-8")
    return path


def test_paper_sandbox_actual_no_order_soak_acceptance_review_ready_and_locked(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _seed_phase44_ready(reports_dir)
    payload = evaluate(reports_dir=str(reports_dir), write_reports=True)
    assert payload["ok"] is True
    assert payload["status"] == "READY"
    assert payload["patch_id"] == "4B436646A"
    assert payload["patch_version"] == "4B.4.3.6.6.46A"
    assert payload["final_safety_violation_count"] == 0
    assert payload["actual_evidence_ingested_by_patch"] is False
    assert payload["actual_evidence_accepted_by_patch"] is False
    assert payload["paper_order_path_opened_by_patch"] is False
    assert payload["paper_submit_enabled_by_patch"] is False
    assert payload["paper_submit_performed"] is False
    assert payload["paper_order_submit_performed"] is False
    assert payload["network_order_submit_performed"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["exchange_submit_performed"] is False
    assert payload["next_phase_unlock_allowed"] is False
