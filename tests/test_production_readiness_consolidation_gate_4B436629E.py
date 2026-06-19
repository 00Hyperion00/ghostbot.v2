from __future__ import annotations

import json
from pathlib import Path

from tradebot.production_readiness_gate import (
    PRODUCTION_READINESS_CONSOLIDATION_CONTRACT_VERSION,
    REQUIRED_EVIDENCE,
    build_consolidated_readiness_snapshot,
    evaluate_production_readiness_consolidation,
    load_production_hardening_evidence,
)


def _write_report(base: Path, key: str, stamp: str = "20260619T000000Z") -> Path:
    spec = REQUIRED_EVIDENCE[key]
    path = base / spec["pattern"].replace("*", stamp)
    payload = {
        "contract_version": spec["contract_version"],
        "decision": spec["decision"],
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
        "approved_for_runtime_overlay_activation_candidate": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8", newline="\n")
    return path


def test_evidence_merge_ready_but_live_real_and_paper_stay_blocked(tmp_path: Path) -> None:
    for key in REQUIRED_EVIDENCE:
        _write_report(tmp_path, key)
    snapshot = build_consolidated_readiness_snapshot(tmp_path)
    assert snapshot["contract_version"] == PRODUCTION_READINESS_CONSOLIDATION_CONTRACT_VERSION
    assert snapshot["decision"] == "PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED"
    assert snapshot["approved_for_evidence_merge_baseline"] is True
    assert snapshot["approved_for_paper_candidate_preflight"] is True
    assert snapshot["approved_for_paper_candidate"] is False
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["live_real_hard_block_verified"] is True
    assert snapshot["trading_action_performed"] is False


def test_missing_evidence_blocks_preflight(tmp_path: Path) -> None:
    _write_report(tmp_path, "29A")
    decision = evaluate_production_readiness_consolidation(load_production_hardening_evidence(tmp_path))
    assert decision.decision == "PRODUCTION_READINESS_CONSOLIDATION_NOT_READY"
    assert decision.approved_for_paper_candidate_preflight is False
    assert decision.approved_for_live_real is False
    assert any("EVIDENCE_MISSING" in reason for reason in decision.reason_codes)


def test_unexpected_live_real_approval_invalidates_evidence(tmp_path: Path) -> None:
    for key in REQUIRED_EVIDENCE:
        _write_report(tmp_path, key)
    report_path = next(tmp_path.glob(REQUIRED_EVIDENCE["29B"]["pattern"]))
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["approved_for_live_real"] = True
    report_path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    snapshot = build_consolidated_readiness_snapshot(tmp_path)
    assert snapshot["decision"] == "PRODUCTION_READINESS_CONSOLIDATION_NOT_READY"
    assert snapshot["approved_for_paper_candidate_preflight"] is False
    assert snapshot["approved_for_live_real"] is False
    assert "29B_LIVE_REAL_UNEXPECTEDLY_APPROVED" in snapshot["reason_codes"]


def test_latest_matching_report_is_used(tmp_path: Path) -> None:
    for key in REQUIRED_EVIDENCE:
        _write_report(tmp_path, key, "20260619T000000Z")
    bad_old = tmp_path / REQUIRED_EVIDENCE["29D"]["pattern"].replace("*", "20000101T000000Z")
    bad_old.write_text(json.dumps({"contract_version": "bad", "decision": "bad"}), encoding="utf-8", newline="\n")
    snapshot = build_consolidated_readiness_snapshot(tmp_path)
    assert snapshot["evidence"]["29D"]["ok"] is True


def test_required_runtime_mutation_flags_are_fail_closed(tmp_path: Path) -> None:
    for key in REQUIRED_EVIDENCE:
        _write_report(tmp_path, key)
    snapshot = build_consolidated_readiness_snapshot(tmp_path)
    assert snapshot["runtime_overlay_activation_performed"] is False
    assert snapshot["scheduler_mutation_performed"] is False
    assert snapshot["strategy_parameter_mutation_performed"] is False
    assert snapshot["training_performed"] is False
    assert snapshot["reload_performed"] is False
    assert snapshot["paper_live_order_enablement_present"] is False
