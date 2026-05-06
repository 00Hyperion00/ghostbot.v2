import importlib.util
import json
from pathlib import Path


def load_tool():
    path = Path(__file__).resolve().parents[1] / "tools" / "generate_live_demo_acceptance_metrics_4B436623.py"
    spec = importlib.util.spec_from_file_location("generate_live_demo_acceptance_metrics_4B436623", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_soak(root: Path, name: str = "4B436622_live_demo_soak_20260101_000000.json", *, decision: str = "PASS", samples: int = 31) -> Path:
    path = root / "reports" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {
            "decision": decision,
            "sample_count": samples,
            "severity_counts": {"PASS": samples if decision == "PASS" else 0, "WARN": 0, "FAIL": 0 if decision == "PASS" else samples},
            "reason_counts": {},
            "state_counts": {"FLAT": samples},
            "first_ts_utc": "2026-05-03T22:00:00Z",
            "last_ts_utc": "2026-05-03T22:15:00Z",
        },
        "observation_only": True,
        "no_post_actions": True,
        "interrupted_by_operator": False,
        "samples": [
            {"ts_utc": "2026-05-03T22:00:00Z", "status": {"state": "FLAT", "ws_status": "CONNECTED", "last_signal": "HOLD"}, "evaluation": {"severity": "PASS", "reason_codes": []}}
            for _ in range(samples)
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_acceptance_metrics_passes_clean_soak(tmp_path: Path) -> None:
    tool = load_tool()
    write_soak(tmp_path, samples=31)
    report = tool.build_report(
        tmp_path,
        latest_only=False,
        log_file=None,
        status_payload=None,
        min_samples=10,
        min_pass_rate_pct=100.0,
        max_ws_disconnects=2,
        max_log_errors=0,
    )
    assert report["decision"] == "PASS"
    assert report["selected_soak_report"]["sample_count"] == 31
    assert report["blockers"] == []


def test_acceptance_metrics_blocks_failed_soak(tmp_path: Path) -> None:
    tool = load_tool()
    write_soak(tmp_path, decision="FAIL", samples=12)
    report = tool.build_report(
        tmp_path,
        latest_only=True,
        log_file=None,
        status_payload=None,
        min_samples=10,
        min_pass_rate_pct=100.0,
        max_ws_disconnects=2,
        max_log_errors=0,
    )
    assert report["decision"] == "FAIL"
    assert "SOAK_DECISION_FAIL" in report["blockers"]


def test_log_parser_counts_strategy_skip_and_ws_disconnect() -> None:
    tool = load_tool()
    text = """
2026-05-03 22:00:03,855 | INFO | STRATEGY_EVAL | Strateji değerlendirildi | {'signal': 'HOLD'}
2026-05-03 22:00:03,860 | INFO | STRATEGY_DECISION_AUDIT | snapshot | {'action': 'AUTO_TRADE_SKIP', 'reasonCodes': ['RAW_SIGNAL_HOLD', 'NO_ACTION_SIGNAL_HOLD']}
2026-05-03 22:00:03,864 | INFO | AUTO_TRADE_SKIP | Otomatik işlem atlandı | {'skipCode': 'NO_ACTION_SIGNAL_HOLD'}
2026-05-03 22:08:39,186 | WARNING | WS_DISCONNECTED | WebSocket bağlantısı kapatıldı | {'reason': 'RECONNECT_PREP'}
"""
    result = tool.analyze_log_text(text)
    assert result["strategy_eval_count"] == 1
    assert result["auto_trade_skip_count"] == 1
    assert result["ws_disconnect_count"] == 1
    assert result["reason_code_counts"]["RAW_SIGNAL_HOLD"] == 1


def test_status_snapshot_blocks_real_live_arming(tmp_path: Path) -> None:
    tool = load_tool()
    write_soak(tmp_path, samples=31)
    status = {
        "config_safety_snapshot": {
            "execution_mode": "live_demo",
            "market_type": "spot_demo",
            "live_trading_armed": True,
            "live_real_double_confirm": False,
            "critical_warnings": [],
        },
        "health_snapshot": {},
        "model_quality_snapshot": {},
        "performance_snapshot": {},
    }
    report = tool.build_report(
        tmp_path,
        latest_only=False,
        log_file=None,
        status_payload=status,
        min_samples=10,
        min_pass_rate_pct=100.0,
        max_ws_disconnects=2,
        max_log_errors=0,
    )
    assert report["decision"] == "FAIL"
    assert "REAL_LIVE_ARMED" in report["blockers"]


def test_report_writer_outputs_json_and_markdown(tmp_path: Path) -> None:
    tool = load_tool()
    write_soak(tmp_path, samples=31)
    report = tool.build_report(
        tmp_path,
        latest_only=False,
        log_file=None,
        status_payload=None,
        min_samples=10,
        min_pass_rate_pct=100.0,
        max_ws_disconnects=2,
        max_log_errors=0,
    )
    json_path, md_path = tool.write_reports(tmp_path, report)
    assert json_path.exists()
    assert md_path.exists()
    assert "Decision: **PASS**" in md_path.read_text(encoding="utf-8")
