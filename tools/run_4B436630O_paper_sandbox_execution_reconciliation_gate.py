from __future__ import annotations

import argparse
from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_sandbox_execution_reconciliation_gate import (
    build_from_latest_30n_ready_report,
    persist_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B.4.3.6.6.30O paper sandbox execution reconciliation gate.")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--write-sqlite-mirror", action="store_true")
    parser.add_argument("--sqlite-path", default=None)
    args = parser.parse_args()
    settings = Settings()
    snapshot = build_from_latest_30n_ready_report(
        settings,
        reports_dir=args.reports_dir,
        write_sqlite_mirror=args.write_sqlite_mirror,
        sqlite_path=args.sqlite_path,
    )
    report_json, report_md = persist_report(snapshot, reports_dir=args.reports_dir)
    print(f"4B.4.3.6.6.30O Paper Sandbox Execution Reconciliation Gate {snapshot['decision']}")
    for key in (
        "read_only",
        "approved_for_paper_sandbox_execution_reconciliation_gate",
        "approved_for_30n_paper_execution_ledger_consumption",
        "approved_for_order_fill_position_balance_reconciliation",
        "approved_for_mismatch_zero_proof",
        "approved_for_sqlite_audit_mirror",
        "approved_for_paper_sandbox_dry_run_execution",
        "approved_for_exchange_submit",
        "approved_for_live_real",
        "mismatch_count",
        "sqlite_audit_mirror_verified",
        "paper_order_enablement_still_blocked",
        "exchange_submit_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {snapshot.get(key)}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    print(f"sqlite_path: {snapshot.get('sqlite_path')}")
    return 0 if snapshot.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
