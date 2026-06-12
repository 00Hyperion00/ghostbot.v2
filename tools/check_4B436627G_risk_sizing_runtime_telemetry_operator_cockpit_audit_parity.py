from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src" / "tradebot"


def _seed_verified_runtime(root: Path) -> None:
    database = root / ".tradebot" / "tradebot.db"
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "CREATE TABLE logs (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, level TEXT NOT NULL, code TEXT NOT NULL, message TEXT NOT NULL, data TEXT NOT NULL)"
        )
        sizing = {
            "contract_version": "4B.4.3.6.6.27F",
            "sizing_mode": "risk_percent_quote_balance",
            "free_quote_balance": 1000.0,
            "usable_quote_balance": 800.0,
            "requested_quote_budget": 20.0,
            "quote_budget": 20.0,
            "reference_price": 2500.0,
            "raw_quantity": 0.008,
            "quantity": 0.008,
            "required_min_notional": 5.5,
            "order_notional": 20.0,
        }
        preflight = {"side": "BUY", "symbol": "ETHUSDT", "reasonCode": "ENTRY_PREFLIGHT_VERIFIED"}
        connection.execute("INSERT INTO logs(ts, level, code, message, data) VALUES(?, ?, ?, ?, ?)", (1000, "INFO", "ENTRY_SIZING_VERIFIED", "verified", json.dumps(sizing)))
        connection.execute("INSERT INTO logs(ts, level, code, message, data) VALUES(?, ?, ?, ?, ?)", (1001, "INFO", "LIVE_PREFLIGHT_OK", "preflight", json.dumps(preflight)))
        connection.commit()
    finally:
        connection.close()


def _contains(path: Path, marker: str) -> bool:
    return path.exists() and marker in path.read_text(encoding="utf-8")


def build_report() -> dict[str, Any]:
    from tradebot.risk_sizing_runtime_telemetry import (
        assert_risk_sizing_evidence_export_ready,
        collect_risk_sizing_runtime_telemetry,
    )

    with tempfile.TemporaryDirectory(prefix="tradebot_27g_check_") as raw:
        root = Path(raw)
        missing = collect_risk_sizing_runtime_telemetry(root)
        db_created_by_missing_probe = (root / ".tradebot" / "tradebot.db").exists()
        _seed_verified_runtime(root)
        ready = collect_risk_sizing_runtime_telemetry(root)
        assert_risk_sizing_evidence_export_ready(ready)

    cockpit = SRC / "operator_cockpit_v2_read_only.py"
    desktop = SRC / "operator_cockpit_v2_desktop_wrapper.py"
    telemetry = SRC / "risk_sizing_runtime_telemetry.py"
    checks = {
        "runtime_sqlite_read_only_mode_present": _contains(telemetry, "?mode=ro"),
        "missing_probe_does_not_create_database": db_created_by_missing_probe is False,
        "missing_runtime_telemetry_fails_closed": missing.get("export_ready") is False and "RUNTIME_TELEMETRY_DB_NOT_FOUND" in missing.get("export_blockers", []),
        "verified_runtime_telemetry_is_export_ready": ready.get("export_ready") is True,
        "verified_runtime_preflight_parity_present": ready.get("audit_parity", {}).get("preflight_event_found") is True,
        "cockpit_snapshot_telemetry_present": _contains(cockpit, '"risk_sizing_runtime_telemetry": risk_sizing_telemetry'),
        "cockpit_fail_closed_export_gate_present": _contains(cockpit, "except RiskSizingEvidenceExportBlocked as error:"),
        "legacy_evidence_pack_route_preserved": _contains(cockpit, 'if path == "/api/operator-cockpit-v2/export/evidence-pack.zip":'),
        "native_desktop_export_bridge_parity_present": _contains(desktop, "DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP"),
    }
    return {
        "ok": all(checks.values()),
        "contract_version": "4B.4.3.6.6.27G",
        "checks": checks,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("4B.4.3.6.6.27G checker")
        for name, value in report["checks"].items():
            print(f" - {name}: {value}")
        print(f" - ok: {report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
