from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from tradebot.config import Settings
from tradebot.config_safety import build_config_safety_snapshot
from tradebot.engine import TradeBotEngine
from tradebot.models import RuntimeState


def test_config_safety_redacts_api_credentials() -> None:
    settings = Settings(api_key='ABCD1234SECRET', api_secret='VERYSECRET123456')

    snapshot = build_config_safety_snapshot(settings)

    assert snapshot['api_key']['present'] is True
    assert snapshot['api_key']['redacted'].startswith('ABCD')
    assert 'SECRET' not in snapshot['api_key']['redacted']
    assert snapshot['api_secret']['present'] is True
    assert snapshot['api_secret']['redacted'] == '***'
    assert 'VERYSECRET123456' not in str(snapshot)


def test_config_safety_flags_unarmed_live_real_profile() -> None:
    settings = Settings(
        execution_mode='live_real',
        market_type='spot_mainnet',
        base_url='https://api.binance.com',
        api_key='key',
        api_secret='secret',
        live_trading_armed=False,
        live_real_double_confirm=False,
    )

    snapshot = build_config_safety_snapshot(settings)

    assert snapshot['severity'] == 'critical'
    assert snapshot['safe_to_trade'] is False
    assert 'LIVE_REAL_NOT_ARMED' in snapshot['reason_codes']
    assert 'LIVE_REAL_DOUBLE_CONFIRM_MISSING' in snapshot['reason_codes']


def test_config_safety_allows_armed_live_demo_profile() -> None:
    settings = Settings(
        execution_mode='live_demo',
        market_type='spot_demo',
        base_url='https://demo-api.binance.com',
        api_key='demo-key',
        api_secret='demo-secret',
        live_trading_armed=False,
        live_real_double_confirm=False,
        order_notional_usd=25.0,
    )

    snapshot = build_config_safety_snapshot(settings)

    assert snapshot['profile_mode'] == 'live_demo'
    assert snapshot['safe_to_trade'] is True
    assert 'LIVE_REAL_NOT_ARMED' not in snapshot['reason_codes']


def test_config_safety_flags_missing_local_model_path(tmp_path: Path) -> None:
    settings = Settings(ai_provider_enabled=True, ai_provider_mode='local_xgboost', ai_model_path='models/missing.ubj')

    snapshot = build_config_safety_snapshot(settings, base_dir=tmp_path)

    assert snapshot['ai']['model_path_exists'] is False
    assert snapshot['severity'] == 'warning'
    assert 'AI_MODEL_PATH_NOT_FOUND' in snapshot['reason_codes']


def test_config_safety_status_snapshot_contract_is_non_blocking() -> None:
    engine = TradeBotEngine.__new__(TradeBotEngine)
    engine.settings = Settings(ai_provider_enabled=False)
    engine.runtime = RuntimeState()
    engine._running = True
    engine._expire_safe_mode = lambda: None
    engine._health_snapshot = lambda: {
        'account_consistency': 'HEALTHY',
        'position_consistency': 'HEALTHY',
        'pending_consistency': 'HEALTHY',
    }
    engine._risk_snapshot = lambda: {}
    engine._ai_snapshot = lambda: {}
    engine._pending_snapshot = lambda: {}
    engine._position_snapshot = lambda runtime_payload: {}
    engine._event_audit_snapshot = lambda: {}
    engine._model_quality_snapshot = lambda: {}
    engine._performance_snapshot = lambda: {}

    status = asyncio.run(TradeBotEngine.get_status(engine))

    assert status['contract_version'] == '4B.4.3.6.6.20'
    assert status['config_safety_snapshot']['contract_version'] == '4B.4.3.6.6.15'
    assert status['config_safety_snapshot']['severity'] in {'ok', 'warning', 'critical'}
