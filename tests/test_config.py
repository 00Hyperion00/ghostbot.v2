from pathlib import Path

from tradebot.config import Settings


def test_settings_from_yaml_ignores_unknown_keys(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "symbol: SOLUSDT\napi_host: 127.0.0.1\napi_port: 8787\norder_notional_usd: 25\n",
        encoding="utf-8",
    )

    settings = Settings.from_yaml(cfg)

    assert settings.symbol == "SOLUSDT"
    assert settings.order_notional_usd == 25
