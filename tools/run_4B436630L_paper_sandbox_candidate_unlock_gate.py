from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = _repo_root()
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.paper_sandbox_candidate_unlock_gate import (
        CONTRACT_VERSION,
        build_from_latest_30k_ready_report,
        write_report_bundle,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--unlock-token", default=None)
    parser.add_argument("--issue-candidate-unlock", action="store_true")
    parser.add_argument("--ttl-sec", type=int, default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    payload = build_from_latest_30k_ready_report(
        reports_dir=args.reports_dir,
        operator_id=args.operator_id,
        unlock_token=args.unlock_token,
        issue_candidate_unlock=args.issue_candidate_unlock,
        ttl_sec=args.ttl_sec,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} Paper Sandbox Candidate Unlock Gate {payload.get('decision')}")
        for key in (
            "read_only",
            "approved_for_paper_sandbox_candidate_unlock_gate",
            "approved_for_explicit_paper_candidate_unlock",
            "approved_for_sandbox_only_order_enablement_preflight",
            "approved_for_paper_sandbox_candidate",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
