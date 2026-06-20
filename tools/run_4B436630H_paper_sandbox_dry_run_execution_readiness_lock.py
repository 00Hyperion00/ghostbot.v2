from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir():
            return item
    return start


def main() -> int:
    root = _repo_root()
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.paper_sandbox_dry_run_execution_readiness_lock import (
        build_from_operator_lock_inputs,
        write_report_bundle,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default="")
    parser.add_argument("--lock-token", default="")
    parser.add_argument("--issue-dry-run-lock", action="store_true")
    parser.add_argument("--ttl-sec", type=int, default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    payload = build_from_operator_lock_inputs(
        operator_id=args.operator_id,
        lock_token=args.lock_token,
        issue_lock=args.issue_dry_run_lock,
        reports_dir=args.reports_dir,
        ttl_sec=args.ttl_sec,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.30H Paper Sandbox Dry-run Execution Readiness Lock {payload.get('decision')}")
        for key in (
            "read_only",
            "approved_for_paper_sandbox_dry_run_execution_readiness_lock",
            "approved_for_paper_sandbox_dry_run_execution_readiness_candidate",
            "approved_for_operator_explicit_dry_run_lock",
            "approved_for_exchange_submit_hard_block_audit",
            "approved_for_paper_sandbox_dry_run_execution",
            "approved_for_exchange_submit",
            "approved_for_paper_transition_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "source_30g_candidate_gate_verified",
            "operator_explicit_dry_run_lock_verified",
            "exchange_submit_hard_block_audit_verified",
            "paper_execution_still_disabled_verified",
            "paper_order_enablement_still_blocked",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
            "exchange_submit_performed",
        ):
            print(f" - {key}: {payload.get(key)}")
        print(f"report_json: {json_path}")
        print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
