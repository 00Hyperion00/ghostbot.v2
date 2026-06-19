from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from check_4B436629C_sqlite_audit_ledger_upgrade import CONTRACT_VERSION, build_report


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
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.29C SQLite audit ledger upgrade decision report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    root = Path.cwd()
    reports_dir = _canonical_reports_dir(args.reports_dir)
    report = build_report(root)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ok": bool(report.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "decision": "SQLITE_AUDIT_LEDGER_UPGRADE_READY_LIVE_REAL_STILL_BLOCKED" if report.get("ok") else "SQLITE_AUDIT_LEDGER_UPGRADE_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "sqlite_audit_ledger_upgrade": True,
        "approved_for_orders_ledger_baseline": bool(report["checks"].get("orders_table_present")),
        "approved_for_fills_ledger_baseline": bool(report["checks"].get("fills_table_present")),
        "approved_for_positions_ledger_baseline": bool(report["checks"].get("positions_table_present")),
        "approved_for_risk_events_ledger_baseline": bool(report["checks"].get("risk_events_table_present")),
        "approved_for_model_decisions_ledger_baseline": bool(report["checks"].get("model_decisions_table_present")),
        "approved_for_balance_snapshots_ledger_baseline": bool(report["checks"].get("balance_snapshots_table_present")),
        "approved_for_operator_actions_ledger_baseline": bool(report["checks"].get("operator_actions_table_present")),
        "approved_for_schema_migration_baseline": bool(report["checks"].get("schema_migrations_table_present")),
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
        "sqlite_probe": report.get("sqlite_probe", {}),
        "recommendation": "Use ledger as audit baseline only. Keep HYP-006 no-order OOS monitoring separate. Do not enable paper/live/live-real until later production gates pass.",
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436629C_sqlite_audit_ledger_upgrade_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.29C SQLite Audit Ledger Upgrade Decision Report\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- read_only: `{payload['read_only']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- approved_for_paper_candidate: `{payload['approved_for_paper_candidate']}`\n"
        f"- trading_action_performed: `{payload['trading_action_performed']}`\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{CONTRACT_VERSION} SQLite Audit Ledger Upgrade {payload['decision']}")
    for key in (
        "read_only",
        "approved_for_orders_ledger_baseline",
        "approved_for_fills_ledger_baseline",
        "approved_for_positions_ledger_baseline",
        "approved_for_risk_events_ledger_baseline",
        "approved_for_model_decisions_ledger_baseline",
        "approved_for_balance_snapshots_ledger_baseline",
        "approved_for_operator_actions_ledger_baseline",
        "approved_for_schema_migration_baseline",
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
