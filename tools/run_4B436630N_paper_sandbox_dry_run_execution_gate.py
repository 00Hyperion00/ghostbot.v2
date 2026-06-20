from __future__ import annotations

import argparse
from pathlib import Path
from tradebot.config import Settings
from tradebot.paper_sandbox_dry_run_execution_gate import (
    CONTRACT_VERSION,
    build_from_latest_30m_ready_report,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--authorization-token", default=None)
    parser.add_argument("--issue-execution-authorization", action="store_true")
    parser.add_argument("--append-ledger", action="store_true")
    parser.add_argument("--ttl-sec", type=int, default=None)
    args = parser.parse_args()
    settings = Settings()
    payload = build_from_latest_30m_ready_report(
        settings,
        reports_dir=args.reports_dir,
        operator_id=args.operator_id,
        authorization_token=args.authorization_token,
        issue_execution_authorization=args.issue_execution_authorization,
        append_ledger=args.append_ledger,
        ttl_sec=args.ttl_sec,
    )
    report_json, report_md = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Paper Sandbox Dry-run Execution Gate {payload.get('decision')}")
    for key in (
        "read_only",
        "approved_for_paper_sandbox_dry_run_execution_gate",
        "approved_for_30m_order_envelope_consumption",
        "approved_for_internal_paper_execution_simulation",
        "approved_for_paper_execution_ledger_append",
        "approved_for_paper_sandbox_dry_run_execution",
        "approved_for_exchange_submit",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "paper_sandbox_dry_run_execution_performed_internal_only",
        "paper_order_enablement_still_blocked",
        "exchange_submit_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    print(f"paper_execution_ledger: {payload.get('paper_execution_ledger_path')}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
