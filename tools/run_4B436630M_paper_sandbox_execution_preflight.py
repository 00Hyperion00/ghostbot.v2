
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
    from tradebot.config import Settings
    from tradebot.paper_sandbox_execution_preflight import build_from_latest_30l_ready_report, write_report_bundle

    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.30M paper sandbox execution preflight report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default="")
    parser.add_argument("--authorization-token", default="")
    parser.add_argument("--issue-dry-run-authorization", action="store_true")
    parser.add_argument("--ttl-sec", type=int, default=None)
    parser.add_argument("--write-envelope", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    settings = Settings()
    envelope_path = Path(args.reports_dir) / "4B436630M_order_envelope_preflight.json"
    payload = build_from_latest_30l_ready_report(
        settings,
        reports_dir=args.reports_dir,
        operator_id=args.operator_id or None,
        authorization_token=args.authorization_token or None,
        issue_dry_run_authorization=args.issue_dry_run_authorization,
        ttl_sec=args.ttl_sec,
        envelope_path=envelope_path,
        write_envelope=args.write_envelope,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.30M Paper Sandbox Execution Preflight {payload.get('decision')}")
        for key in (
            "read_only",
            "approved_for_paper_sandbox_execution_preflight",
            "approved_for_30l_candidate_unlock_consumption",
            "approved_for_paper_sandbox_dry_run_authorization",
            "approved_for_order_envelope_build",
            "approved_for_paper_sandbox_dry_run_execution",
            "approved_for_exchange_submit",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "order_envelope_built",
            "order_envelope_written",
            "paper_order_enablement_still_blocked",
            "exchange_submit_performed",
            "trading_action_performed",
        ):
            print(f" - {key}: {payload.get(key)}")
        print(f"report_json: {json_path}")
        print(f"report_md: {md_path}")
        if payload.get("order_envelope", {}).get("envelope_path"):
            print(f"order_envelope: {payload['order_envelope']['envelope_path']}")
    return 0 if bool(payload.get("ok")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
