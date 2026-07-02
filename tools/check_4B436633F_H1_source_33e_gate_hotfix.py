from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.evidence_retention_archive_policy import build_evidence_retention_archive_policy_report, summarize_report


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33F-H1 source 33E gate hotfix check")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_evidence_retention_archive_policy_report(args.repo_root)
    summary = summarize_report(report)
    ok = report.status == "READY" and report.source_33e.complete
    payload = {
        "ok": ok,
        "check_name": "source_33e_completion_gate_hotfix",
        "patch_id": "4B436633F_H1",
        "patch_version": "4B.4.3.6.6.33F-H1",
        "status": "READY" if ok else "NOT_READY",
        "decision": "SOURCE_33E_COMPLETION_GATE_HOTFIX_READY" if ok else "SOURCE_33E_COMPLETION_GATE_HOTFIX_NOT_READY",
        "source_33e_complete": report.source_33e.complete,
        "source_33e_report": report.source_33e.report_path,
        "source_33e_error": report.source_33e.error,
        "source_33f_status_after_hotfix": report.status,
        "source_33f_decision_after_hotfix": report.decision,
        "source_33f_ready_after_hotfix": report.status == "READY",
        "retention_rules_complete": report.retention_rules_complete,
        "report_retention_complete": report.report_retention.complete,
        "backup_payload_archive_manifest_complete": report.backup_payload_archive_manifest.complete,
        "non_destructive_cleanup_plan_complete": report.non_destructive_cleanup_plan.complete,
        "evidence_aging_ledger_complete": report.evidence_aging_ledger.complete,
        "destructive_cleanup_performed": report.safety_snapshot.destructive_cleanup_performed,
        "exchange_submit_performed": report.safety_snapshot.exchange_submit_performed,
        "trading_action_performed": report.safety_snapshot.trading_action_performed,
        "training_performed": report.safety_snapshot.training_performed,
        "reload_performed": report.safety_snapshot.reload_performed,
        "runtime_overlay_activated": report.safety_snapshot.runtime_overlay_activated,
        "approved_for_live_real": report.safety_snapshot.approved_for_live_real,
        "approved_for_paper_transition": report.safety_snapshot.approved_for_paper_transition,
        "approved_for_exchange_submit": report.safety_snapshot.approved_for_exchange_submit,
        "approved_for_runtime_overlay": report.safety_snapshot.approved_for_runtime_overlay,
        "evidence_retention_archive_policy_summary": summary,
    }
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False) if args.once_json else json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
