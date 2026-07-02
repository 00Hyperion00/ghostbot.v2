from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.status_conflict_resolver import check_status_conflict_resolver


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33E-H1 source 33D gate hotfix check")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--reports-root", default="reports")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    payload = check_status_conflict_resolver(project_root=args.project_root, reports_root=args.reports_root)
    h1 = {
        "patch_id": "4B436633E_H1",
        "patch_version": "4B.4.3.6.6.33E-H1",
        "check_name": "source_33d_completion_gate_hotfix",
        "status": "READY" if payload.get("source_33d_complete") and payload.get("status") == "READY" else "NOT_READY",
        "decision": "SOURCE_33D_COMPLETION_GATE_HOTFIX_READY" if payload.get("source_33d_complete") and payload.get("status") == "READY" else "SOURCE_33D_COMPLETION_GATE_HOTFIX_NOT_READY",
        "ok": bool(payload.get("ok", False)),
        "source_33d_complete": payload.get("source_33d_complete"),
        "source_33d_report": payload.get("source_33d_report"),
        "source_33e_status_after_hotfix": payload.get("status"),
        "source_33e_decision_after_hotfix": payload.get("decision"),
        "source_33e_ready_after_hotfix": payload.get("status") == "READY",
        "status_conflict_resolution_complete": payload.get("status_conflict_resolution_complete"),
        "unknown_evidence_triage_complete": payload.get("unknown_evidence_triage_complete"),
        "malformed_json_triage_complete": payload.get("malformed_json_triage_complete"),
        "unresolved_conflict_count": payload.get("unresolved_conflict_count"),
        "residual_unknown_count": payload.get("residual_unknown_count"),
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "exchange_submit_performed": False,
        "runtime_overlay_activated": False,
        "destructive_cleanup_performed": False,
    }
    print(json.dumps(h1, sort_keys=True))
    return 0 if h1["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
