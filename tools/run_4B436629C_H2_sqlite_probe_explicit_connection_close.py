from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from check_4B436629C_H2_sqlite_probe_explicit_connection_close import CONTRACT_VERSION, build_report


def _validate_reports_dir(value: str) -> Path:
    path = Path(value)
    normalized = path.as_posix().replace("\\", "/")
    if "src=" in normalized or "production_hardenin" in normalized and "production_hardening" not in normalized:
        raise SystemExit("Invalid reports-dir; use .\\reports\\production_hardening")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.29C-H2 SQLite probe explicit connection close report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    root = Path.cwd()
    report = build_report(root)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ok": bool(report.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "decision": "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_READY_LIVE_REAL_STILL_BLOCKED" if report.get("ok") else "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "sqlite_probe_explicit_connection_close": True,
        "base_29c_report_ok": bool(report.get("base_29c_report_ok")),
        "h1_report_ok": bool(report.get("h1_report_ok")),
        "approved_for_sqlite_audit_ledger_baseline": bool(report.get("base_29c_report_ok")),
        "approved_for_windows_probe_cleanup_baseline": bool(report.get("h1_report_ok")),
        "approved_for_explicit_connection_close_baseline": bool(report.get("checks", {}).get("direct_explicit_close_probe_ok")),
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
        "checks": report.get("checks", {}),
        "recommendation": "Accept 29C SQLite audit ledger only after explicit SQLite connections are closed on Windows. Keep live-real and order actions blocked.",
    }
    reports_dir = _validate_reports_dir(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436629C_H2_sqlite_probe_explicit_connection_close_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.29C-H2 SQLite Probe Explicit Connection Close Decision Report\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- read_only: `{payload['read_only']}`\n"
        f"- approved_for_sqlite_audit_ledger_baseline: `{payload['approved_for_sqlite_audit_ledger_baseline']}`\n"
        f"- approved_for_windows_probe_cleanup_baseline: `{payload['approved_for_windows_probe_cleanup_baseline']}`\n"
        f"- approved_for_explicit_connection_close_baseline: `{payload['approved_for_explicit_connection_close_baseline']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- trading_action_performed: `{payload['trading_action_performed']}`\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{CONTRACT_VERSION} SQLite Probe Explicit Connection Close {payload['decision']}")
    for key in (
        "read_only",
        "approved_for_sqlite_audit_ledger_baseline",
        "approved_for_windows_probe_cleanup_baseline",
        "approved_for_explicit_connection_close_baseline",
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
