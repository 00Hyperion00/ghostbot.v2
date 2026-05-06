import importlib.util
import json
import sys
from pathlib import Path


def load_tool():
    path = Path(__file__).resolve().parents[1] / "tools" / "run_live_demo_soak_4B436622.py"
    spec = importlib.util.spec_from_file_location("run_live_demo_soak_4B436622", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def good_status() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.21",
        "state": "FLAT",
        "ws_status": "CONNECTED",
        "symbol": "ETHUSDT",
        "config_safety_snapshot": {
            "execution_mode": "live_demo",
            "market_type": "spot_demo",
            "safe_to_trade": True,
            "safe_to_auto_trade": True,
            "live_trading_armed": False,
            "live_real_double_confirm": False,
            "critical_warnings": [],
        },
        "health_snapshot": {
            "account_consistency": "HEALTHY",
            "position_consistency": "HEALTHY",
            "pending_consistency": "HEALTHY",
            "active_anomaly_code": None,
        },
        "model_quality_snapshot": {"severity": "ok", "reason_codes": [], "sample_count": 50},
        "performance_snapshot": {"closed_trade_count": 0, "realized_pnl": 0.0},
        "position_snapshot": {"present": False},
        "pending_snapshot": {"present": False},
    }


def test_good_sample_passes() -> None:
    tool = load_tool()
    health = tool.summarize_health({"ok": True, "running": True, "bootstrap_ok": True, "symbol": "ETHUSDT"})
    status = tool.summarize_status(good_status())
    result = tool.evaluate_sample(health, status)
    assert result["severity"] == "PASS"
    assert result["reason_codes"] == []


def test_real_live_armed_fails_closed() -> None:
    tool = load_tool()
    payload = good_status()
    payload["config_safety_snapshot"]["live_trading_armed"] = True
    health = tool.summarize_health({"ok": True, "running": True, "bootstrap_ok": True})
    status = tool.summarize_status(payload)
    result = tool.evaluate_sample(health, status)
    assert result["severity"] == "FAIL"
    assert "REAL_LIVE_ARMED" in result["reason_codes"]


def test_run_soak_with_fake_fetcher_and_report(tmp_path: Path) -> None:
    tool = load_tool()

    def fake_fetcher(base_url: str, path: str, timeout_sec: float) -> dict:
        if path == "/health":
            return {"ok": True, "running": True, "bootstrap_ok": True, "symbol": "ETHUSDT"}
        if path == "/status":
            return good_status()
        raise AssertionError(path)

    report = tool.run_soak(
        "http://127.0.0.1:8000",
        duration_sec=0.0,
        interval_sec=1.0,
        timeout_sec=1.0,
        max_samples=1,
        min_samples=1,
        fetcher=fake_fetcher,
    )
    assert report["summary"]["decision"] == "PASS"
    json_path, md_path = tool.write_reports(tmp_path, report)
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["decision"] == "PASS"
    assert "Live-demo Supervised Soak" in md_path.read_text(encoding="utf-8")


def test_tool_is_get_only_observation_tool() -> None:
    path = Path(__file__).resolve().parents[1] / "tools" / "run_live_demo_soak_4B436622.py"
    text = path.read_text(encoding="utf-8")
    assert 'method="GET"' in text
    assert 'method="POST"' not in text
    assert "/force" not in text
    assert "/cancel" not in text
    assert "observation_only" in text
