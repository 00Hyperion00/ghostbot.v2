from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


def load_tool():
    path = Path(__file__).resolve().parents[1] / "tools" / "run_extended_demo_soak_4B436624C.py"
    spec = importlib.util.spec_from_file_location("run_extended_demo_soak_4B436624C", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def health_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "running": True,
        "engine_running": True,
        "degraded": False,
        "bootstrap_ok": True,
        "bootstrap_error": None,
        "start_error": None,
        "symbol": "ETHUSDT",
    }


def pass_status(signal: str = "HOLD") -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.24B",
        "state": "FLAT",
        "ws_status": "CONNECTED",
        "symbol": "ETHUSDT",
        "last_signal": signal,
        "last_signal_confidence": 0.72,
        "config_safety_snapshot": {
            "profile_mode": "live_demo",
            "execution_mode": "live_demo",
            "market_type": "spot_demo",
            "safe_to_trade": True,
            "safe_to_auto_trade": True,
            "live_trading_armed": False,
            "live_real_double_confirm": False,
            "auto_trade_on_signal": False,
            "critical_warnings": [],
            "warnings": [],
        },
        "health_snapshot": {
            "account_consistency": "HEALTHY",
            "position_consistency": "HEALTHY",
            "pending_consistency": "HEALTHY",
            "active_anomaly_code": None,
        },
        "model_quality_snapshot": {
            "enabled": True,
            "sample_count": 120,
            "severity": "ok",
            "recommendation": "OK",
            "reason_codes": [],
        },
        "model_quality_gate_snapshot": {
            "contract_version": "4B.4.3.6.6.24B",
            "enabled": True,
            "gate_type": "runtime",
            "decision": "PASS",
            "ok": True,
            "reload_allowed": True,
            "live_demo_allowed": True,
            "live_real_allowed": True,
            "reason_codes": [],
            "warnings": [],
            "metrics": {
                "sample_count": 120,
                "hold_pct": 74.0,
                "action_pct": 26.0,
                "avg_confidence": 0.72,
                "low_margin_rejection_pct": 12.0,
            },
        },
        "diagnostics_snapshot": {
            "severity": "ok",
            "ready_to_operate": True,
            "reason_codes": [],
        },
        "performance_snapshot": {"closed_trade_count": 0, "realized_pnl": 0.0, "guard_counts": {}},
        "position_snapshot": {"present": False, "qty": 0.0, "source": None},
        "pending_snapshot": {"present": False, "side": None, "status": None},
    }


def make_fetcher(statuses: list[dict[str, Any]]):
    state = {"status_idx": 0, "paths": []}

    def fetcher(base_url: str, path: str, timeout_sec: float) -> dict[str, Any]:
        state["paths"].append(path)
        if path == "/health":
            return health_payload()
        if path == "/status":
            idx = min(int(state["status_idx"]), len(statuses) - 1)
            state["status_idx"] = idx + 1
            return statuses[idx]
        raise AssertionError(f"unexpected path: {path}")

    fetcher.state = state  # type: ignore[attr-defined]
    return fetcher


def test_extended_soak_passes_and_remains_get_only() -> None:
    tool = load_tool()
    fetcher = make_fetcher([pass_status("HOLD"), pass_status("BUY"), pass_status("SELL")])
    report = tool.run_extended_soak(
        "http://127.0.0.1:8000",
        duration_sec=0,
        interval_sec=1,
        timeout_sec=1,
        max_samples=3,
        min_samples=3,
        fetcher=fetcher,
    )
    assert report["observation_only"] is True
    assert report["no_post_actions"] is True
    assert report["summary"]["decision"] == "PASS"
    assert report["summary"]["severity_counts"] == {"PASS": 3}
    assert fetcher.state["paths"] == ["/health", "/status", "/health", "/status", "/health", "/status"]  # type: ignore[attr-defined]


def test_model_gate_timeline_counts_decisions_and_signals() -> None:
    tool = load_tool()
    fetcher = make_fetcher([pass_status("HOLD"), pass_status("BUY"), pass_status("SELL")])
    report = tool.run_extended_soak(
        "http://127.0.0.1:8000",
        duration_sec=0,
        interval_sec=1,
        timeout_sec=1,
        max_samples=3,
        min_samples=3,
        fetcher=fetcher,
    )
    timeline = tool.build_model_gate_timeline(report["samples"])
    assert timeline["decision"] == "PASS"
    assert timeline["decision_counts"] == {"PASS": 3}
    assert timeline["signal_counts"] == {"BUY": 1, "HOLD": 1, "SELL": 1}
    assert timeline["live_demo_allowed_count"] == 3
    assert timeline["avg_action_pct"] == 26.0


def test_blocking_model_gate_blocks_soak_and_pre_paper_readiness() -> None:
    tool = load_tool()
    status = pass_status()
    status["model_quality_gate_snapshot"] = {
        "decision": "BLOCK",
        "ok": False,
        "live_demo_allowed": False,
        "live_real_allowed": False,
        "reason_codes": ["RETRAIN_RECOMMENDED", "RUNTIME_ACTION_COVERAGE_LOW"],
        "warnings": [],
        "metrics": {"sample_count": 67, "hold_pct": 100.0, "action_pct": 0.0, "avg_confidence": 0.44},
    }
    fetcher = make_fetcher([status, status])
    report = tool.run_extended_soak(
        "http://127.0.0.1:8000",
        duration_sec=0,
        interval_sec=1,
        timeout_sec=1,
        max_samples=2,
        min_samples=2,
        fetcher=fetcher,
    )
    timeline = tool.build_model_gate_timeline(report["samples"])
    readiness = tool.build_pre_paper_readiness(report, timeline)
    assert report["summary"]["decision"] == "FAIL"
    assert report["summary"]["reason_counts"]["MODEL_GATE_BLOCK"] == 2
    assert timeline["decision"] == "FAIL"
    assert readiness["decision"] == "BLOCK"
    assert "soak_pass" in readiness["blockers"]
    assert "model_gate_timeline_pass" in readiness["blockers"]


def test_missing_gate_is_synthesized_from_runtime_model_quality_snapshot() -> None:
    tool = load_tool()
    status = pass_status()
    status.pop("model_quality_gate_snapshot")
    status["model_quality_snapshot"] = {
        "enabled": True,
        "sample_count": 67,
        "severity": "critical",
        "recommendation": "RETRAIN_RECOMMENDED",
        "prediction_distribution_pct": {"HOLD": 100.0},
        "confidence": {"avg": 0.44},
        "calibration": {"reject_low_margin_pct": 92.0},
        "reason_codes": ["HOLD_DOMINANCE_CRITICAL"],
    }
    sample = tool.collect_sample("http://127.0.0.1:8000", 1.0, fetcher=make_fetcher([status]))
    gate = sample["status"]["model_quality_gate"]
    assert gate["decision"] == "BLOCK"
    assert "RETRAIN_RECOMMENDED" in gate["reason_codes"]
    assert sample["evaluation"]["severity"] == "FAIL"


def test_write_reports_creates_soak_timeline_and_readiness_files(tmp_path: Path, monkeypatch) -> None:
    tool = load_tool()
    report = tool.run_extended_soak(
        "http://127.0.0.1:8000",
        duration_sec=0,
        interval_sec=1,
        timeout_sec=1,
        max_samples=2,
        min_samples=2,
        fetcher=make_fetcher([pass_status("BUY"), pass_status("SELL")]),
    )
    monkeypatch.chdir(tmp_path)
    paths = tool.write_reports(tmp_path, report)
    assert set(paths) == {
        "soak_json",
        "soak_md",
        "timeline_json",
        "timeline_md",
        "readiness_json",
        "readiness_md",
    }
    for path in paths.values():
        assert Path(path).exists()
    readiness = json.loads(Path(paths["readiness_json"]).read_text(encoding="utf-8"))
    assert readiness["decision"] == "PASS"
    assert readiness["ready_for_paper_phase"] is True
    assert readiness["ready_for_live_real"] is False


def test_source_contract_has_no_post_method() -> None:
    source = (Path(__file__).resolve().parents[1] / "tools" / "run_extended_demo_soak_4B436624C.py").read_text(encoding="utf-8")
    assert "method=\"GET\"" in source
    assert "method=\"POST\"" not in source
    assert "no_post_actions" in source
