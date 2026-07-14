from __future__ import annotations

from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_clean_dashboard_static_bundle_exists_and_is_read_first() -> None:
    root = _root()
    html = (root / "src/tradebot/cockpit/clean_static/index.html").read_text(encoding="utf-8")
    js = (root / "src/tradebot/cockpit/clean_static/app.js").read_text(encoding="utf-8")
    css = (root / "src/tradebot/cockpit/clean_static/styles.css").read_text(encoding="utf-8")

    assert "TradeBot Clean Dashboard" in html
    assert "/api/cockpit/health" in js
    assert "/api/cockpit/snapshot" in js
    assert "X-TradeBot-Auth" in js
    assert "X-TradeBot-Operator" in js
    assert "state.snapshot.logs || state.snapshot.operator_actions || []" in js
    assert "/events/audit" not in js
    assert "postDanger" not in js
    assert "innerHTML" not in js
    assert "textContent" in js
    assert "force-buy" not in html.lower()
    assert "dashboard-grid" in css


def test_clean_dashboard_route_is_mounted_without_replacing_legacy_cockpit() -> None:
    app_text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")

    assert 'app.mount("/static"' in app_text
    assert 'app.mount("/clean-static"' in app_text
    assert '@app.get("/")' in app_text
    assert '@app.get("/dashboard")' in app_text


def test_clean_dashboard_is_served_by_cockpit_app(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from tradebot.config import Settings
    from tradebot.cockpit.app import create_cockpit_app

    settings = Settings(database_path=str(tmp_path / "clean-dashboard.db"))
    client = TestClient(create_cockpit_app(settings))

    dashboard = client.get("/dashboard")
    script = client.get("/clean-static/app.js")

    assert dashboard.status_code == 200
    assert "TradeBot Clean Dashboard" in dashboard.text
    assert "operatorInput" in dashboard.text
    assert "tokenInput" in dashboard.text
    assert script.status_code == 200
    assert "/api/cockpit/snapshot" in script.text
