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


def _canonical_reports_dir(raw: str) -> Path:
    text = str(raw or "").replace("\\", "/").strip()
    bad_fragments = ("$env:", "src=", "production_hardenin$", "production_hardeninsrc")
    if any(fragment.lower() in text.lower() for fragment in bad_fragments):
        raise SystemExit(f"BAD_REPORTS_DIR: shell-contaminated reports-dir rejected: {raw}")
    path = Path(raw)
    canonical = Path("reports") / "production_hardening"
    if path.as_posix().rstrip("/") != canonical.as_posix():
        raise SystemExit(f"BAD_REPORTS_DIR: expected {canonical.as_posix()}, got {path.as_posix()}")
    return path


def main() -> int:
    root = _repo_root()
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_dry_run_reconciliation_audit_ledger import (
        build_from_latest_30i_evidence,
        write_report_bundle,
    )

    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.30J reconciliation + audit ledger proof")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--sqlite-path", default="")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    reports_dir = _canonical_reports_dir(args.reports_dir)
    settings = Settings()
    sqlite_path = args.sqlite_path.strip() or None
    payload = build_from_latest_30i_evidence(settings=settings, reports_dir=reports_dir, sqlite_path=sqlite_path)
    json_path, md_path = write_report_bundle(payload, reports_dir)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.30J Paper Sandbox Dry-run Reconciliation + Audit Ledger Proof {payload.get('decision')}")
        for key in (
            "read_only",
            "approved_for_paper_sandbox_dry_run_reconciliation_audit_ledger_proof",
            "approved_for_30i_simulated_fill_ledger_consumption",
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
        print(f"report_json: {json_path}")
        print(f"report_md: {md_path}")
    return 0 if payload.get("decision", "").endswith("LIVE_REAL_BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
