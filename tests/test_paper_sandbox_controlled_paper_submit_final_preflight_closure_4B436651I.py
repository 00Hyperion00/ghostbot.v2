from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_controlled_paper_submit_final_preflight_closure import evaluate


def _seed_phase45_49_ready(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "4B436645_49_phase45_to_phase49_paper_sandbox_transition_bundle_seed_ready.json"
    path.write_text(json.dumps({
        "ok": True,
        "status": "READY",
        "patch_id": "4B436645_49",
        "patch_version": "4B.4.3.6.6.45-49",
        "decision": "PHASE45_TO_PHASE49_PAPER_SANDBOX_TRANSITION_BUNDLE_READY_REVIEW_AND_CONTRACT_ONLY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED",
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "network_order_submit_performed": False,
        "paper_order_submit_performed": False,
        "paper_submit_enabled_by_patch": False,
        "final_safety_violation_count": 0,
    }), encoding="utf-8")
    return path


def test_paper_sandbox_controlled_paper_submit_final_preflight_closure_ready_and_locked(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _seed_phase45_49_ready(reports_dir)
    payload = evaluate(reports_dir=str(reports_dir), write_reports=True)
    assert payload["ok"] is True
    assert payload["status"] == "READY"
    assert payload["patch_id"] == "4B436651I"
    assert payload["patch_version"] == "4B.4.3.6.6.51I"
    assert payload["final_safety_violation_count"] == 0
    assert payload["paper_submit_enabled_by_patch"] is False
    assert payload["paper_submit_performed"] is False
    assert payload["paper_order_submit_performed"] is False
    assert payload["network_order_submit_performed"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["exchange_submit_performed"] is False
    assert payload["private_api_access_allowed"] is False
    assert payload["next_phase_unlock_allowed"] is False
