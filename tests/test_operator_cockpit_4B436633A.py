from __future__ import annotations

from pathlib import Path


def test_operator_cockpit_static_assets_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "src/tradebot/cockpit/app.py").exists()
    assert (root / "src/tradebot/cockpit/orchestrator.py").exists()
    assert (root / "src/tradebot/cockpit/static/index.html").exists()
    assert (root / "src/tradebot/cockpit/static/app.js").exists()
    assert (root / "src/tradebot/cockpit/static/styles.css").exists()


def test_cockpit_contract_version_literal_present() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "4B.4.3.6.6.33A" in text


def test_cli_contains_cockpit_command() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/cli.py").read_text(encoding="utf-8")
    assert "sub.add_parser('cockpit')" in text
    assert "run_cockpit" in text
