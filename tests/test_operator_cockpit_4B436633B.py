from __future__ import annotations

from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33b_contract_literals_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "4B.4.3.6.6.33A" in text
    assert "4B.4.3.6.6.33B" in text
    assert "OPERATOR_COCKPIT_RUNTIME_HARDENING_ENABLED" in text


def test_33b_runtime_awareness_logic_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_runtime_awareness_snapshot" in text
    assert "BASE_BALANCE_PRESENT_POSITION_NOT_TRACKED" in text
    assert "ORPHAN_LOCAL_POSITION_RECOVERY_DETECTED" in text
    assert "auto_entry_risk_attention_required" in text


def test_33b_favicon_route_and_asset_present() -> None:
    root = _root()
    app_text = (root / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert '"/favicon.ico"' in app_text
    assert (root / "src/tradebot/cockpit/static/favicon.svg").exists()


def test_33b_ui_risk_badge_present() -> None:
    root = _root()
    html = (root / "src/tradebot/cockpit/static/index.html").read_text(encoding="utf-8")
    js = (root / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    css = (root / "src/tradebot/cockpit/static/styles.css").read_text(encoding="utf-8")
    assert "runtimeRiskBanner" in html
    assert "runtimeRiskBadge" in html
    assert "renderRuntimeAwareness" in js
    assert "risk-red" in css
    assert "risk-yellow" in css


def test_33b_powershell_compile_helper_present() -> None:
    tool = _root() / "tools/compile_operator_cockpit_4B436633B.py"
    text = tool.read_text(encoding="utf-8")
    assert "powershell_glob_required" in text
    assert "py_compile.compile" in text
