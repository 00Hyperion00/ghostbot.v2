from __future__ import annotations

from pathlib import Path

from tradebot.config import Settings


def test_settings_from_yaml_ignores_unknown_keys(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        """
market_type: spot_demo
symbol: SOLUSDT
api_host: 127.0.0.1
api_port: 8787
order_notional_usd: 25
""".strip(),
        encoding='utf-8',
    )

    settings = Settings.from_yaml(path)

    assert settings.market_type == 'spot_demo'
    assert settings.symbol == 'SOLUSDT'
    assert settings.order_notional_usd == 25
    assert 'api_host' not in settings.to_dict()
    assert 'api_port' not in settings.to_dict()
