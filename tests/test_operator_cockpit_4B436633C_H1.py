from __future__ import annotations

from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33c_h1_app_js_bootstrap_blocks_empty_token_ws_retry() -> None:
    js = (_root() / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    assert "4B.4.3.6.6.33C-H1" in js
    assert "bootstrapCockpit" in js
    assert "securityAllowsProtectedCalls" in js
    assert "AUTH_REQUIRED_BUT_NO_TOKEN_CONFIGURED" in js
    assert "AUTH_TOKEN_REQUIRED_IN_UI" in js
    assert "WEBSOCKET_AUTH_REJECTED" in js
    assert "event.code === 1008" in js
    assert "connectWs();\nfetchSnapshot();" not in js


def test_33c_h1_protected_actions_disabled_until_auth_ready() -> None:
    js = (_root() / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    assert "setProtectedButtonsEnabled(false)" in js
    assert "button.disabled = !enabled" in js
    assert "Cockpit auth bootstrap required" in js
    assert "renderSecurityBlocking" in js


def test_33c_h1_compile_helper_present() -> None:
    tool = _root() / "tools/compile_operator_cockpit_4B436633C_H1.py"
    text = tool.read_text(encoding="utf-8")
    assert "4B.4.3.6.6.33C-H1" in text
    assert "auth_bootstrap_hotfix_compile_contract" in text
    assert "websocket_empty_token_retry_blocked_by_ui" in text


def test_33c_h1_doc_present() -> None:
    doc = _root() / "docs/OPERATOR_COCKPIT_AUTH_BOOTSTRAP_HOTFIX_4B436633C_H1.md"
    text = doc.read_text(encoding="utf-8")
    assert "TRADEBOT_COCKPIT_AUTH_TOKEN" in text
    assert "Order submit policy gevşetilmez" in text
