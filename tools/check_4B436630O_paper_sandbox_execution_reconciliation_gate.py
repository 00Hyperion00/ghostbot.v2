from __future__ import annotations
import argparse
import json
import tempfile
from pathlib import Path
from tradebot.paper_sandbox_execution_reconciliation_gate import build_paper_sandbox_execution_reconciliation_snapshot


def build_report() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = build_paper_sandbox_execution_reconciliation_snapshot(
            None,
            {"ok": True},
            {"submitted_to_exchange": False, "quote_balance_delta_usd": 0.0},
            sqlite_path=Path(tmp) / "audit.sqlite",
        )
    checks = {
        "module_probe_ok": snapshot["ok"] is True,
        "module_probe_mismatch_zero": snapshot["mismatch_count"] == 0,
        "target_30o_checker_ok": snapshot["ok"] is True,
        "target_mismatch_zero": snapshot["mismatch_count"] == 0,
        "target_sqlite_mirror_ok": snapshot["sqlite_audit_mirror_verified"] is True,
        "target_exchange_submit_blocked": snapshot["exchange_submit_performed"] is False,
        "target_live_real_blocked": snapshot["approved_for_live_real"] is False,
        "exchange_submit_still_blocked": snapshot["exchange_submit_performed"] is False,
        "order_actions_blocked": snapshot["trading_action_performed"] is False,
    }
    ok = all(checks.values())
    return {
        "ok": ok,
        "status": "READY" if ok else "BLOCKED",
        "patch_id": "4B436630O",
        "patch_version": "4B.4.3.6.6.30O",
        "decision": "PAPER_SANDBOX_EXECUTION_RECONCILIATION_CHECKER_READY" if ok else "PAPER_SANDBOX_EXECUTION_RECONCILIATION_CHECKER_BLOCKED",
        "checks": checks,
        "read_only": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "paper_submit_performed": False,
        "paper_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
    }


def main() -> int:
    argparse.ArgumentParser().parse_known_args()
    payload = build_report()
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["ok"] else 1


run_checker = build_report

if __name__ == "__main__":
    raise SystemExit(main())
