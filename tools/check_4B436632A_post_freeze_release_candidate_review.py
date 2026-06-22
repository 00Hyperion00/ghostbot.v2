from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from tradebot.post_freeze_release_candidate_review import (
    CONTRACT_VERSION,
    FINALIZATION_TOKEN,
    READY_DECISION,
    SOURCE_31B_CONTRACT_VERSION,
    SOURCE_31B_READY_DECISION,
    build_from_explicit_31b_report,
    build_from_latest_31b_report,
    write_report_bundle,
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _sample_31b() -> dict[str, Any]:
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


def run_probe() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        reports = Path(tmp) / "reports" / "production_hardening"
        source = reports / "4B436631B_release_hygiene_bad_evidence_ledger_cleanup_20260622T101501Z_ready.json"
        _write_json(source, _sample_31b())
        payload = build_from_explicit_31b_report(
            reports_dir=reports,
            source_31b_report=source,
            operator_id="checker-32a",
            finalization_token=FINALIZATION_TOKEN,
            audit_comment="checker probe",
            emergency_stop_armed=True,
            capital_cap_usdt=25,
            second_micro_max_notional_usdt=5,
            daily_loss_limit_usdt=5,
            max_slippage_bps=50,
        )
        latest_payload = build_from_latest_31b_report(
            reports_dir=reports,
            operator_id="checker-32a",
            finalization_token=FINALIZATION_TOKEN,
            audit_comment="latest checker probe",
            emergency_stop_armed=True,
            capital_cap_usdt=25,
            second_micro_max_notional_usdt=5,
            daily_loss_limit_usdt=5,
            max_slippage_bps=50,
        )
        json_path, md_path = write_report_bundle(payload, reports_dir=reports)
        return {
            "payload": payload,
            "latest_payload": latest_payload,
            "json_path_exists": json_path.exists(),
            "md_path_exists": md_path.exists(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.32A post-freeze release candidate review checker")
    parser.add_argument("--once-json", action="store_true")
    _ = parser.parse_args()
    probe = run_probe()
    payload = probe["payload"]
    latest = probe["latest_payload"]
    checks = {
        "contract_version_ok": payload.get("contract_version") == CONTRACT_VERSION,
        "ready_decision_ok": payload.get("decision") == READY_DECISION,
        "latest_discovery_ready": latest.get("decision") == READY_DECISION,
        "source_31b_verified": payload.get("source_31b_release_hygiene_verified") is True,
        "final_audit_snapshot_reviewed": payload.get("final_audit_snapshot_reviewed") is True,
        "capital_cap_confirmed": payload.get("capital_cap_confirmed") is True,
        "second_micro_candidate_only": payload.get("second_micro_canary_eligible_candidate") is True,
        "live_real_order_false": payload.get("approved_for_live_real_order") is False,
        "second_micro_order_submit_false": payload.get("approved_for_second_micro_canary_order_submit") is False,
        "patch_network_submit_false": payload.get("patch_network_submit_attempted") is False,
        "additional_live_order_false": payload.get("additional_live_real_order_performed") is False,
        "report_bundle_written": probe["json_path_exists"] and probe["md_path_exists"],
    }
    output = {"ok": all(checks.values()), "contract_version": CONTRACT_VERSION, "checks": checks}
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if output["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
