from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_version_comparison_accepts_20_plus() -> None:
    smoke = _load_tool("run_runtime_smoke_4B436621")
    assert smoke.contract_version_at_least("4B.4.3.6.6.20") is True
    assert smoke.contract_version_at_least("4B.4.3.6.6.21") is True
    assert smoke.contract_version_at_least("4B.4.3.6.6.19") is False


def test_runtime_smoke_evaluators_validate_health_and_status() -> None:
    smoke = _load_tool("run_runtime_smoke_4B436621")
    ok, reason, details = smoke.evaluate_health({"ok": True, "running": True, "symbol": "ETHUSDT"})
    assert ok is True
    assert reason is None
    assert details["symbol"] == "ETHUSDT"
    status = {
        "contract_version": "4B.4.3.6.6.20",
        "ai_snapshot": {},
        "risk_snapshot": {},
        "position_snapshot": {},
        "pending_snapshot": {},
        "config_safety_snapshot": {},
        "performance_snapshot": {},
        "model_quality_snapshot": {},
    }
    ok, reason, details = smoke.evaluate_status(status)
    assert ok is True
    assert reason is None
    assert details["missing_snapshots"] == []


def test_dashboard_checker_reports_required_symbols() -> None:
    checker = _load_tool("check_dashboard_contract_4B436621")
    class Dummy:
        pass
    for name in [
        "build_operator_control_state",
        "build_position_management_text",
        "build_audit_query_path",
        "filter_audit_events",
        "format_log_line",
        "build_audit_summary_text",
    ]:
        setattr(Dummy, name, object())
    setattr(Dummy, "DashboardApp", object())
    result = checker.check_imports(Dummy)
    assert result.ok is True


def test_report_writers_create_files(tmp_path: Path) -> None:
    smoke = _load_tool("run_runtime_smoke_4B436621")
    result = smoke.SmokeResult(name="health", ok=True, url="http://127.0.0.1:8000/health", status_code=200, reason=None, details={"ok": True})
    json_path, md_path = smoke.write_reports(tmp_path, [result], stamp="TEST", base_url="http://127.0.0.1:8000")
    assert json_path.exists()
    assert md_path.exists()
    assert "PASS" in md_path.read_text(encoding="utf-8")
