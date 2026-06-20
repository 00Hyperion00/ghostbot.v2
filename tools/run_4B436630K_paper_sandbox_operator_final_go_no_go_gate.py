from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.paper_sandbox_operator_final_go_no_go_gate import build_from_latest_30j_ready_report, write_report_bundle

    parser = argparse.ArgumentParser(description="Run 4B.4.3.6.6.30K paper sandbox operator final go/no-go gate")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default="")
    parser.add_argument("--approval-token", default="")
    parser.add_argument("--issue-final-approval", action="store_true")
    parser.add_argument("--confirm-kill-switch", action="store_true")
    parser.add_argument("--confirm-caps", action="store_true")
    parser.add_argument("--ttl-sec", type=int, default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    payload = build_from_latest_30j_ready_report(
        reports_dir=args.reports_dir,
        operator_id=args.operator_id,
        approval_token=args.approval_token,
        issue_final_approval=args.issue_final_approval,
        confirm_kill_switch=args.confirm_kill_switch,
        confirm_caps=args.confirm_caps,
        ttl_sec=args.ttl_sec,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.30K Paper Sandbox Operator Final Go/No-Go Gate {payload.get('decision')}")
        for key in (
            "read_only",
            "approved_for_paper_sandbox_operator_final_go_no_go_gate",
            "approved_for_operator_final_paper_sandbox_approval",
            "approved_for_kill_switch_caps_checklist",
            "approved_for_paper_sandbox_go_no_go_candidate",
            "approved_for_paper_sandbox_dry_run_execution",
            "approved_for_exchange_submit",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "paper_order_enablement_still_blocked",
            "exchange_submit_performed",
            "trading_action_performed",
        ):
            print(f" - {key}: {payload.get(key)}")
        print(f"report_json: {json_path}")
        print(f"report_md: {md_path}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
