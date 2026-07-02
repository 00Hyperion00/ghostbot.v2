from __future__ import annotations

from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33c_security_gate_contract_literals_present() -> None:
    text = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert "4B.4.3.6.6.33C" in text
    assert "OPERATOR_COCKPIT_SECURITY_GATE_ENABLED" in text
    assert "X-TradeBot-Auth" in text
    assert "X-TradeBot-Operator" in text
    assert "X-TradeBot-Confirm" in text


def test_33c_read_only_health_exception_present() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert '@app.get("/health")' in text
    assert '@app.get("/api/cockpit/health")' in text
    assert "read_only_health_exception" in text
    assert "authenticate_http_request" in text


def test_33c_typed_confirmation_and_operator_audit_present() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "DANGER_ACTION_CONFIRMATIONS" in text
    assert "require_operator_identity" in text
    assert "append_operator_action" in text
    assert "BLOCKED_CONFIRMATION_REQUIRED" in text
    assert "ALLOWED_OK" in text


def test_33c_snapshot_exposes_security_and_operator_actions() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_security_snapshot" in text
    assert "fetch_recent_operator_actions" in text
    assert '"security"' in text
    assert '"operator_actions"' in text
    assert "OPERATOR_COCKPIT_SECURITY_GATE_VERSION" in text


def test_33c_ui_modal_and_headers_present() -> None:
    root = _root()
    html = (root / "src/tradebot/cockpit/static/index.html").read_text(encoding="utf-8")
    js = (root / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    css = (root / "src/tradebot/cockpit/static/styles.css").read_text(encoding="utf-8")
    assert "confirmModal" in html
    assert "operatorInput" in html
    assert "authTokenInput" in html
    assert "requestConfirmModal" in js
    assert "X-TradeBot-Auth" in js
    assert "X-TradeBot-Operator" in js
    assert "X-TradeBot-Confirm" in js
    assert ".modal-backdrop" in css


def test_33c_compile_helper_present() -> None:
    tool = _root() / "tools/compile_operator_cockpit_4B436633C.py"
    text = tool.read_text(encoding="utf-8")
    assert "security_gate_compile_contract" in text
    assert "py_compile.compile" in text
