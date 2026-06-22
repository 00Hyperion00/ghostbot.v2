from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.live_micro_canary_freeze_audit_closure import (
    CONTRACT_VERSION,
    build_from_latest_30z_risk_review_report,
    cleanup_bad_31a_not_ready_artifacts,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--finalization-token", default=None)
    parser.add_argument("--audit-comment", default=None)
    parser.add_argument("--evidence-pack-id", default=None)
    parser.add_argument("--acknowledge-hyp006-report-separation", action="store_true")
    parser.add_argument("--cleanup-bad-31a-not-ready-artifacts", action="store_true")
    args = parser.parse_args()
    removed = cleanup_bad_31a_not_ready_artifacts(args.reports_dir) if args.cleanup_bad_31a_not_ready_artifacts else []
    payload = build_from_latest_30z_risk_review_report(
        Settings(),
        args.reports_dir,
        operator_id=args.operator_id,
        finalization_token=args.finalization_token,
        audit_comment=args.audit_comment,
        evidence_pack_id=args.evidence_pack_id,
        acknowledge_hyp006_report_separation=args.acknowledge_hyp006_report_separation,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Live Micro-Canary Freeze & Audit Closure {payload.get('decision')}")
    for key in (
        "approved_for_live_micro_canary_freeze_audit_closure",
        "approved_for_operator_audit_finalization",
        "approved_for_release_evidence_archive",
        "approved_for_additional_exchange_submit",
        "approved_for_live_real_continuation",
        "source_30z_risk_review_verified",
        "evidence_pack_sealed",
        "release_hygiene_verified",
        "operator_audit_finalized",
        "no_further_live_orders_verified",
        "emergency_stop_continuity_verified",
        "evidence_pack_id",
        "evidence_pack_manifest_sha256",
        "evidence_pack_file_count",
        "patch_network_submit_attempted",
        "additional_live_real_order_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    if removed:
        print(f" - cleanup_bad_31a_not_ready_artifacts_removed: {len(removed)}")
    print(f" - json_report: {json_path}")
    print(f" - markdown_report: {md_path}")
    return 0 if payload.get("source_30z_risk_review_verified") and payload.get("patch_network_submit_attempted") is False else 2


if __name__ == "__main__":
    raise SystemExit(main())
