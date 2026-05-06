import argparse
import importlib
import json
import py_compile
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PHASE = "4B.4.3.6.6.21b"


@dataclass
class ContractCheck:
    name: str
    ok: bool
    reason: str | None = None
    details: dict[str, Any] | None = None


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_src_path(root: Path) -> None:
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _contains(text: str, *needles: str) -> bool:
    return all(needle in text for needle in needles)


def _safe_call(name: str, fn) -> ContractCheck:
    try:
        return fn()
    except Exception as exc:  # pragma: no cover - report path
        return ContractCheck(name=name, ok=False, reason=f"{type(exc).__name__}: {exc}")


def check_imports(module: Any) -> ContractCheck:
    required = [
        "build_operator_control_state",
        "build_position_management_text",
        "build_audit_query_path",
        "filter_audit_events",
        "format_log_line",
        "build_audit_summary_text",
        "DashboardApp",
    ]
    missing = [name for name in required if not hasattr(module, name)]
    return ContractCheck("imports", not missing, None if not missing else "missing: " + ", ".join(missing), {"missing": missing})


def check_operator_control(module: Any) -> ContractCheck:
    status = {
        "contract_version": "4B.4.3.6.6.20",
        "state": "BUY_PENDING",
        "engine_running": True,
        "health_snapshot": {
            "account_consistency": "HEALTHY",
            "position_consistency": "HEALTHY",
            "pending_consistency": "HEALTHY",
        },
        "pending_snapshot": {"present": True, "side": "BUY"},
        "position_snapshot": {"present": False, "qty": 0.0},
        "risk_snapshot": {"safe_mode": False, "kill_switch_active": False},
    }
    controls = module.build_operator_control_state(status, connected=True)
    required_keys = {"state", "health_ok", "buttons", "hint", "force_buy", "force_sell", "cancel_pending"}
    missing = sorted(required_keys - set(controls.keys()))
    ok = not missing and controls.get("force_buy") is False and controls.get("cancel_pending") is True and "PENDING" in str(controls.get("hint", "")).upper()
    return ContractCheck("operator_control", ok, None if ok else f"bad control shape/state; missing={missing}", {"controls": controls, "missing": missing})


def check_position_text(module: Any) -> ContractCheck:
    text = module.build_position_management_text({
        "position_snapshot": {
            "present": True,
            "qty": 0.0123,
            "entry_price": 100.0,
            "mark_price": 101.0,
            "source": "TEST",
            "risk_plan": {
                "stop_loss": 98.0,
                "take_profit": 105.0,
                "active_stop_loss": 99.0,
                "partial_tp_done": True,
            },
            "protective_exit": {
                "protective_exit_ready": True,
                "tradable_exit_qty": 0.0123,
                "exit_notional": 1.24,
                "is_dust": False,
                "risk_execution": {"status": "READY", "exit_signal": "HOLD"},
            },
        }
    })
    ok = _contains(text, "Protective exit", "Take profit", "Effective SL", "Partial TP done", "Risk exec")
    return ContractCheck("position_text", ok, None if ok else "position text missing required operator lines", {"text": text})


def check_audit_helpers(module: Any) -> ContractCheck:
    event = {"ts": 0, "level": "INFO", "code": "ORDER_SUBMITTED", "message": "ok", "data": {"clientOrderId": "CID-1"}}
    formatted = module.format_log_line(event)
    filtered = module.filter_audit_events([event], {"category": "Orders"})
    summary = module.build_audit_summary_text({"total": 1, "events": [event]})
    query_path = module.build_audit_query_path(limit=0, order="asc", code_prefix="order_")
    ok = (
        "Orders" in formatted
        and "CID-1" in formatted
        and len(filtered) == 1
        and "Orders:1" in summary
        and "code_prefix=ORDER_" in query_path
        and "limit=0" in query_path
    )
    return ContractCheck("audit_helpers", ok, None if ok else "audit helper contract mismatch", {"formatted": formatted, "summary": summary, "query_path": query_path, "filtered_count": len(filtered)})


def check_dashboard_class(module: Any) -> ContractCheck:
    klass = module.DashboardApp
    required_methods = [
        "api_post",
        "_api_post",
        "_render_status",
        "_render_logs",
        "_set_offline_ui",
        "_poll_health_and_status",
        "_render_event_timeline",
        "_render_session_summary",
        "_extract_training_output_path",
    ]
    missing = [name for name in required_methods if not hasattr(klass, name)]
    return ContractCheck("dashboard_class", not missing, None if not missing else "missing methods: " + ", ".join(missing), {"missing": missing})


def run_contract_checks(root: Path) -> tuple[bool, list[ContractCheck]]:
    _ensure_src_path(root)
    dashboard_path = root / "src" / "tradebot" / "ui" / "dashboard.py"
    py_compile.compile(str(dashboard_path), doraise=True)
    module = importlib.import_module("tradebot.ui.dashboard")
    checks = [
        _safe_call("imports", lambda: check_imports(module)),
        _safe_call("operator_control", lambda: check_operator_control(module)),
        _safe_call("position_text", lambda: check_position_text(module)),
        _safe_call("audit_helpers", lambda: check_audit_helpers(module)),
        _safe_call("dashboard_class", lambda: check_dashboard_class(module)),
    ]
    return all(check.ok for check in checks), checks


def write_reports(root: Path, checks: list[ContractCheck], *, stamp: str) -> tuple[Path, Path]:
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436621_dashboard_contract_{stamp}.json"
    md_path = reports_dir / f"4B436621_dashboard_contract_{stamp}.md"
    payload = {"phase": PHASE, "ok": all(check.ok for check in checks), "checks": [asdict(check) for check in checks]}
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        f"# {PHASE} Dashboard Contract Report",
        "",
        f"- Result: **{'PASS' if payload['ok'] else 'FAIL'}**",
        "",
        "| Check | Result | Reason |",
        "|---|---:|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {'PASS' if check.ok else 'FAIL'} | {check.reason or '-'} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{PHASE} dashboard contract checker")
    parser.add_argument("--root", default=".")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    ok, checks = run_contract_checks(root)
    json_path, md_path = write_reports(root, checks, stamp=_now_stamp())
    print(f"{PHASE} dashboard contract {'PASSED' if ok else 'FAILED'}")
    for check in checks:
        print(f" - {check.name}: {'PASS' if check.ok else 'FAIL'} ({check.reason or 'OK'})")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
