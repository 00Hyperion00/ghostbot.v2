from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33d_contract_markers_present() -> None:
    schemas = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_UX_HEALTH_VERSION" in schemas
    assert "4B.4.3.6.6.33D" in schemas
    assert "cpu_percent" in schemas
    assert "memory_rss_mb" in schemas
    assert "engine_uptime_sec" in schemas


def test_33d_orchestrator_system_metrics_are_optional_and_non_mutating() -> None:
    orch = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "import psutil" in orch
    assert "psutil = None" in orch
    assert "_process_metrics" in orch
    assert "engine_started_at_ms" in orch
    assert "OPERATOR_COCKPIT_UX_HEALTH_VERSION" in orch
    assert "order_path_mutation" not in orch.lower()


def test_33d_ui_has_auth_connection_health_and_disable_cards() -> None:
    html = (_root() / "src/tradebot/cockpit/static/index.html").read_text(encoding="utf-8")
    assert "Auth Status" in html
    assert "Connection State Machine" in html
    assert "Protected Action Disable Reasons" in html
    assert "System Health" in html
    assert "authStatusBox" in html
    assert "connectionStateBox" in html
    assert "protectedActionBox" in html


def test_33d_app_js_state_machine_and_health_rendering() -> None:
    js = (_root() / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    assert "UX_HEALTH_OBSERVABILITY_VERSION" in js
    assert "4B.4.3.6.6.33D" in js
    assert "CONNECTION_STATES" in js
    assert "renderConnectionStateMachine" in js
    assert "renderAuthStatusCard" in js
    assert "renderSystemHealth" in js
    assert "renderProtectedActionDisableReasons" in js
    assert "heartbeat-stale" in js
    assert "cpu_percent" in js
    assert "memory_rss_mb" in js
    assert "engine_uptime_sec" in js


def test_33d_css_observability_styles_present() -> None:
    css = (_root() / "src/tradebot/cockpit/static/styles.css").read_text(encoding="utf-8")
    assert "4B.4.3.6.6.33D" in css
    assert "button:disabled" in css
    assert "heartbeat-ok" in css
    assert "heartbeat-warn" in css
    assert "heartbeat-stale" in css


def test_33d_python_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
