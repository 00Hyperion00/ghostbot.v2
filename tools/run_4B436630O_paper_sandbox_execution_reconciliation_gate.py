from __future__ import annotations

import argparse
from tradebot.config import Settings
from tradebot.paper_sandbox_execution_reconciliation_gate import (
    CONTRACT_VERSION,
    build_from_latest_30n_ready_report,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--sqlite-path", default="")
    args = parser.parse_args()
    payload = build_from_latest_30n_ready_report(
        Settings(),
        reports_dir=args.reports_dir,
        sqlite_path=args.sqlite_path or None,
    )
    report_json, report_md = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Paper Sandbox Execution Reconciliation Gate {payload.get('decision')}")
    for key in (
        "read_only",
        "approved_for_paper_sandbox_execution_reconciliation_gate",
        "approved_for_30n_ledger_consumption",
        "approved_for_order_fill_position_balance_reconciliation",
        "approved_for_mismatch_zero_proof",
        "approved_for_sqlite_audit_mirror",
        "approved_for_paper_sandbox_dry_run_execution",
        "approved_for_exchange_submit",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "mismatch_count",
        "exchange_submit_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    print(f"sqlite_mirror: {payload.get('sqlite_audit_mirror', {}).get('sqlite_path')}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
