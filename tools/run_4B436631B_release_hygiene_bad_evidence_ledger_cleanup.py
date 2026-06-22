from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tradebot.release_hygiene_bad_evidence_cleanup import (
    DEFAULT_REPORTS_DIR,
    FINALIZATION_TOKEN,
    READY_DECISION,
    build_from_explicit_31a_h3_report,
    build_from_latest_31a_h3_report,
    write_report_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.31B release hygiene bad evidence ledger cleanup runner")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--source-31a-h3-report", default=None, help="Explicit accepted 31A-H3 READY JSON report path")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--finalization-token", default=None)
    parser.add_argument("--audit-comment", default=None)
    parser.add_argument("--quarantine-manifest-id", default=None)
    parser.add_argument("--move-bad-evidence-to-quarantine", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.source_31a_h3_report:
        payload = build_from_explicit_31a_h3_report(
            reports_dir=args.reports_dir,
            source_31a_h3_report=args.source_31a_h3_report,
            operator_id=args.operator_id,
            finalization_token=args.finalization_token,
            audit_comment=args.audit_comment,
            move_bad_evidence_to_quarantine=args.move_bad_evidence_to_quarantine,
            quarantine_manifest_id=args.quarantine_manifest_id,
        )
    else:
        payload = build_from_latest_31a_h3_report(
            reports_dir=args.reports_dir,
            operator_id=args.operator_id,
            finalization_token=args.finalization_token,
            audit_comment=args.audit_comment,
            move_bad_evidence_to_quarantine=args.move_bad_evidence_to_quarantine,
            quarantine_manifest_id=args.quarantine_manifest_id,
        )
    json_path, md_path, manifest_path = write_report_bundle(payload, reports_dir=args.reports_dir)
    output: dict[str, Any] = {
        "ok": payload.get("decision") == READY_DECISION,
        "decision": payload.get("decision"),
        "contract_version": payload.get("contract_version"),
        "report_path": str(json_path),
        "markdown_path": str(md_path),
        "quarantine_manifest_path": str(manifest_path),
        "source_31a_h3_freeze_audit_closure_verified": payload.get("source_31a_h3_freeze_audit_closure_verified"),
        "bad_evidence_history_explained": payload.get("bad_evidence_history_explained"),
        "bad_evidence_quarantined": payload.get("bad_evidence_quarantined"),
        "bad_evidence_quarantine_moved_file_count": payload.get("bad_evidence_quarantine_moved_file_count"),
        "bad_evidence_quarantine_remaining_file_count": payload.get("bad_evidence_quarantine_remaining_file_count"),
        "final_audit_snapshot_written": payload.get("final_audit_snapshot_written"),
        "no_further_live_orders_verified": payload.get("no_further_live_orders_verified"),
        "patch_network_submit_attempted": payload.get("patch_network_submit_attempted"),
        "additional_live_real_order_performed": payload.get("additional_live_real_order_performed"),
        "reason_codes": payload.get("reason_codes", []),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if output["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
