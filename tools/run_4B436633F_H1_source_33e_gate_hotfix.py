from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.evidence_retention_archive_policy import build_evidence_retention_archive_policy_report


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33F-H1 source 33E gate hotfix run")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    report = build_evidence_retention_archive_policy_report(root)
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
        "destructive_cleanup_performed": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
    }
    out_dir = (root / args.reports_dir).resolve() if not Path(args.reports_dir).is_absolute() else Path(args.reports_dir).resolve()
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    suffix = "ready" if ok else "not_ready"
    report_path = out_dir / f"4B436633F_H1_source_33e_gate_hotfix_{timestamp}_{suffix}.json"
    _write_json(report_path, payload)
    payload["report_path"] = str(report_path)
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False) if args.once_json else json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
