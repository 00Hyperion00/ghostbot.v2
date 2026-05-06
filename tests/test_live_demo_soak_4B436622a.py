import importlib.util
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


def good_status(contract_version: str = "4B.4.3.6.6.12") -> dict:
    return {
        "contract_version": contract_version,
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


def test_runtime_engine_contract_12_is_not_release_warning() -> None:
    tool = load_tool()
    health = tool.summarize_health({"ok": True, "running": True, "bootstrap_ok": True, "symbol": "ETHUSDT"})
    status = tool.summarize_status(good_status("4B.4.3.6.6.12"))
    result = tool.evaluate_sample(health, status)
    assert result["severity"] == "PASS"
    assert "STATUS_CONTRACT_BELOW_RELEASE_CANDIDATE" not in result["reason_codes"]
    assert "STATUS_CONTRACT_BELOW_ENGINE_MINIMUM" not in result["reason_codes"]


def test_runtime_engine_contract_below_12_warns() -> None:
    tool = load_tool()
    health = tool.summarize_health({"ok": True, "running": True, "bootstrap_ok": True, "symbol": "ETHUSDT"})
    status = tool.summarize_status(good_status("4B.4.3.6.6.9"))
    result = tool.evaluate_sample(health, status)
    assert result["severity"] == "WARN"
    assert "STATUS_CONTRACT_BELOW_ENGINE_MINIMUM" in result["reason_codes"]


def test_keyboard_interrupt_returns_partial_review_report(monkeypatch) -> None:
    tool = load_tool()

    def fake_fetcher(base_url: str, path: str, timeout_sec: float) -> dict:
        if path == "/health":
            return {"ok": True, "running": True, "bootstrap_ok": True, "symbol": "ETHUSDT"}
        if path == "/status":
            return good_status()
        raise AssertionError(path)

    def interrupted_sleep(seconds: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(tool.time, "sleep", interrupted_sleep)
    report = tool.run_soak(
        "http://127.0.0.1:8000",
        duration_sec=60.0,
        interval_sec=30.0,
        timeout_sec=1.0,
        max_samples=None,
        min_samples=1,
        fetcher=fake_fetcher,
    )
    assert report["interrupted_by_operator"] is True
    assert report["summary"]["decision"] == "REVIEW"
    assert report["summary"]["sample_count"] == 1
    assert report["summary"]["reason_counts"]["INTERRUPTED_BY_OPERATOR"] == 1


def test_markdown_mentions_interruption_flag() -> None:
    tool = load_tool()
    report = {
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "base_url": "http://127.0.0.1:8000",
        "observation_only": True,
        "no_post_actions": True,
        "interrupted_by_operator": True,
        "summary": {
            "decision": "REVIEW",
            "sample_count": 1,
            "first_ts_utc": "x",
            "last_ts_utc": "x",
            "severity_counts": {"PASS": 0, "WARN": 1, "FAIL": 0},
            "state_counts": {"FLAT": 1},
            "reason_counts": {"INTERRUPTED_BY_OPERATOR": 1},
        },
        "samples": [],
    }
    text = tool.render_markdown(report)
    assert "Interrupted by operator: `True`" in text
    assert "INTERRUPTED_BY_OPERATOR" in text
