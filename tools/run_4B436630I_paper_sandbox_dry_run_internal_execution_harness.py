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
    from tradebot.config import Settings
    from tradebot.paper_sandbox_dry_run_internal_execution_harness import (
        build_from_latest_30h_ready_report,
        default_ledger_path,
        write_report_bundle,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--ledger-path", default="")
    parser.add_argument("--no-append-ledger", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    reports_dir = args.reports_dir
    ledger_path = args.ledger_path or default_ledger_path(reports_dir)
    payload = build_from_latest_30h_ready_report(
        Settings(),
        reports_dir,
        ledger_path=ledger_path,
        append_ledger=not args.no_append_ledger,
    )
    json_path, md_path = write_report_bundle(payload, reports_dir)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.30I Paper Sandbox Dry-run Internal Execution Harness {payload.get('decision')}")
        for key in (
            "read_only",
            "approved_for_paper_sandbox_dry_run_internal_execution_harness",
            "approved_for_internal_only_execution_harness",
            "approved_for_simulated_fill_ledger_append",
            "approved_for_no_exchange_submit_verification",
            "approved_for_paper_sandbox_dry_run_execution",
            "approved_for_exchange_submit",
            "approved_for_paper_transition_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "source_30h_readiness_lock_verified",
            "internal_only_execution_harness_verified",
            "simulated_fill_ledger_append_verified",
            "no_exchange_submit_verified",
            "paper_candidate_still_blocked_verified",
            "paper_order_enablement_still_blocked",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
            "exchange_submit_performed",
            "simulated_fill_ledger_append_performed",
        ):
            print(f" - {key}: {payload.get(key)}")
        print(f"ledger_path: {payload.get('simulated_fill_ledger_append', {}).get('ledger_path')}")
        print(f"report_json: {json_path}")
        print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
