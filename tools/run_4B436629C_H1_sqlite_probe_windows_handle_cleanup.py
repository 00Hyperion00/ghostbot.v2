from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from check_4B436629C_H1_sqlite_probe_windows_handle_cleanup import CONTRACT_VERSION, build_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.29C-H1 SQLite probe Windows handle cleanup decision report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    root = Path.cwd()
    report = build_report(root)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ok": bool(report.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "base_contract_version": report.get("base_contract_version"),
        "decision": "SQLITE_PROBE_WINDOWS_HANDLE_CLEANUP_READY_LIVE_REAL_STILL_BLOCKED" if report.get("ok") else "SQLITE_PROBE_WINDOWS_HANDLE_CLEANUP_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "sqlite_probe_windows_handle_cleanup": True,
        "approved_for_windows_probe_cleanup_baseline": bool(report["checks"].get("sqlite_close_release_probe_ok")),
        "approved_for_sqlite_audit_ledger_upgrade_baseline": bool(report["checks"].get("base_29c_checker_ok")),
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "runtime_overlay_activation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "checks": report["checks"],
        "recommendation": "Accept 29C-H1 before committing 29C. This hotfix closes SQLite probe handles so Windows temp cleanup can complete.",
    }
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436629C_H1_sqlite_probe_windows_handle_cleanup_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.29C-H1 SQLite Probe Windows Handle Cleanup Decision Report\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- read_only: `{payload['read_only']}`\n"
        f"- approved_for_sqlite_audit_ledger_upgrade_baseline: `{payload['approved_for_sqlite_audit_ledger_upgrade_baseline']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- approved_for_paper_candidate: `{payload['approved_for_paper_candidate']}`\n"
        f"- approved_for_runtime_overlay_activation_candidate: `{payload['approved_for_runtime_overlay_activation_candidate']}`\n"
        f"- trading_action_performed: `{payload['trading_action_performed']}`\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{CONTRACT_VERSION} SQLite probe Windows handle cleanup {payload['decision']}")
    for key in (
        "read_only",
        "approved_for_windows_probe_cleanup_baseline",
        "approved_for_sqlite_audit_ledger_upgrade_baseline",
        "approved_for_runtime_overlay_activation_candidate",
        "approved_for_parameter_relaxation_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload[key]}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
