from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from tradebot.release_hygiene_bad_evidence_cleanup import (
    CONTRACT_VERSION,
    FINALIZATION_TOKEN,
    READY_DECISION,
    SOURCE_31A_H3_CONTRACT_VERSION,
    SOURCE_31A_H3_READY_DECISION,
    build_from_explicit_31a_h3_report,
    build_from_latest_31a_h3_report,
    write_report_bundle,
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _sample_31a_h3() -> dict[str, Any]:
    return {
        "contract_version": SOURCE_31A_H3_CONTRACT_VERSION,
        "decision": SOURCE_31A_H3_READY_DECISION,
        "source_30z_risk_review_verified": True,
        "evidence_pack_sealed": True,
        "release_hygiene_verified": True,
        "operator_audit_finalized": True,
        "no_further_live_orders_verified": True,
        "emergency_stop_continuity_verified": True,
        "approved_for_additional_exchange_submit": False,
        "approved_for_live_real_continuation": False,
        "patch_network_submit_attempted": False,
        "patch_exchange_submit_performed": False,
        "patch_live_real_order_performed": False,
        "additional_exchange_submit_performed": False,
        "additional_network_submit_attempted": False,
        "additional_live_real_order_performed": False,
        "evidence_pack_file_count": 15,
    }


def run_probe() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        reports = Path(tmp) / "reports" / "production_hardening"
        reports.mkdir(parents=True, exist_ok=True)
        source = reports / "4B436631A_live_micro_canary_freeze_audit_closure_20260622T094041Z_ready.json"
        _write_json(source, _sample_31a_h3())
        bad_json = reports / "4B436631A_live_micro_canary_freeze_audit_closure_20260622T082318Z_not_ready.json"
        bad_md = reports / "4B436631A_live_micro_canary_freeze_audit_closure_20260622T082318Z_not_ready.md"
        _write_json(bad_json, {"contract_version": "4B.4.3.6.6.31A-H2", "decision": "NOT_READY"})
        bad_md.write_text("# bad not_ready evidence\n", encoding="utf-8")
        payload = build_from_explicit_31a_h3_report(
            reports_dir=reports,
            source_31a_h3_report=source,
            operator_id="checker-31b",
            finalization_token=FINALIZATION_TOKEN,
            audit_comment="checker probe",
            move_bad_evidence_to_quarantine=True,
            quarantine_manifest_id="CHECKER_31B_QUARANTINE",
        )
        json_path, md_path, manifest_path = write_report_bundle(payload, reports_dir=reports)
        remaining_bad = list(reports.glob("4B436631A_live_micro_canary_freeze_audit_closure_*_not_ready.*"))
        return {
            "payload": payload,
            "json_path_exists": json_path.exists(),
            "md_path_exists": md_path.exists(),
            "manifest_path_exists": manifest_path.exists(),
            "remaining_bad_count": len(remaining_bad),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.31B release hygiene cleanup checker")
    parser.add_argument("--once-json", action="store_true")
    _ = parser.parse_args()
    probe = run_probe()
    payload = probe["payload"]
    checks = {
        "contract_version_ok": payload.get("contract_version") == CONTRACT_VERSION,
        "ready_decision_ok": payload.get("decision") == READY_DECISION,
        "source_31a_h3_verified": payload.get("source_31a_h3_freeze_audit_closure_verified") is True,
        "bad_history_explained": payload.get("bad_evidence_history_explained") is True,
        "bad_evidence_quarantined": payload.get("bad_evidence_quarantined") is True,
        "moved_file_count_ok": payload.get("bad_evidence_quarantine_moved_file_count") == 2,
        "remaining_bad_zero": payload.get("bad_evidence_quarantine_remaining_file_count") == 0 and probe["remaining_bad_count"] == 0,
        "final_audit_snapshot_written": payload.get("final_audit_snapshot_written") is True,
        "no_further_live_orders": payload.get("no_further_live_orders_verified") is True,
        "patch_network_submit_false": payload.get("patch_network_submit_attempted") is False,
        "additional_live_order_false": payload.get("additional_live_real_order_performed") is False,
        "report_bundle_written": probe["json_path_exists"] and probe["md_path_exists"] and probe["manifest_path_exists"],
    }
    output = {"ok": all(checks.values()), "contract_version": CONTRACT_VERSION, "checks": checks}
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if output["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
