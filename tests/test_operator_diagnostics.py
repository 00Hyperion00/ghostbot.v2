from __future__ import annotations

import asyncio
import json
import zipfile
from types import SimpleNamespace

from tradebot.config import Settings
from tradebot.diagnostics import build_diagnostics_snapshot, redact_payload, write_support_bundle
from tradebot.engine import TradeBotEngine
from tradebot.models import LogEvent, RuntimeState
from tradebot.persistence import SQLiteStore


def test_redact_payload_masks_credentials_recursively() -> None:
    payload = {
        'api_key': 'A' * 64,
        'nested': {
            'api_secret': 'B' * 64,
            'token': 'abcd1234efgh',
            'safe': 'value',
        },
    }

    redacted = redact_payload(payload)

    assert redacted['api_key'] == 'AAAA...AAAA'
    assert redacted['nested']['api_secret'] == 'BBBB...BBBB'
    assert redacted['nested']['token'] == 'abcd...efgh'
    assert redacted['nested']['safe'] == 'value'


def test_diagnostics_snapshot_ok_when_runtime_is_healthy() -> None:
    snapshot = build_diagnostics_snapshot(
        status={
            'contract_version': '4B.4.3.6.6.17',
            'engine_running': True,
            'ws_status': 'CONNECTED',
            'state': 'FLAT',
            'symbol': 'ETHUSDT',
            'health_snapshot': {
                'ws_connected': True,
                'account_consistency': 'HEALTHY',
                'position_consistency': 'HEALTHY',
                'pending_consistency': 'HEALTHY',
            },
            'risk_snapshot': {'safe_mode': False, 'kill_switch_active': False},
            'config_safety_snapshot': {'safe_to_trade': True},
            'pending_snapshot': {'present': False},
            'position_snapshot': {'present': False},
        },
        logs=[],
        generated_at=100,
    )

    assert snapshot['contract_version'] == '4B.4.3.6.6.17'
    assert snapshot['severity'] == 'ok'
    assert snapshot['ready_to_operate'] is True
    assert snapshot['reason_codes'] == []
    assert snapshot['health_checklist']['engine_running'] is True


def test_diagnostics_snapshot_flags_warning_events_and_safe_mode() -> None:
    snapshot = build_diagnostics_snapshot(
        status={
            'contract_version': '4B.4.3.6.6.17',
            'engine_running': True,
            'ws_status': 'CONNECTED',
            'state': 'FLAT',
            'symbol': 'ETHUSDT',
            'health_snapshot': {'ws_connected': True, 'account_consistency': 'HEALTHY', 'position_consistency': 'HEALTHY', 'pending_consistency': 'HEALTHY'},
            'risk_snapshot': {'safe_mode': True, 'kill_switch_active': False},
            'config_safety_snapshot': {'safe_to_trade': True},
        },
        logs=[{'ts': 20, 'level': 'WARN', 'code': 'ORDER_REJECTED', 'message': 'rejected', 'data': {'api_secret': 'S' * 64}}],
        generated_at=120,
    )

    assert snapshot['severity'] == 'critical'
    assert 'SAFE_MODE_OR_KILL_SWITCH_ACTIVE' in snapshot['reason_codes']
    assert 'RECENT_WARNING_EVENTS_PRESENT' in snapshot['reason_codes']
    assert snapshot['latest_critical_events'][0]['data']['api_secret'] == 'SSSS...SSSS'


def test_write_support_bundle_exports_redacted_zip(tmp_path) -> None:
    output = tmp_path / 'support.zip'

    bundle = write_support_bundle(
        output,
        status={'contract_version': '4B.4.3.6.6.17', 'api_key': 'K' * 64},
        logs=[{'ts': 1, 'level': 'ERROR', 'code': 'X', 'message': 'x', 'data': {'api_secret': 'Z' * 64}}],
        config={'api_secret': 'C' * 64, 'symbol': 'ETHUSDT'},
    )

    assert bundle.exists()
    with zipfile.ZipFile(bundle) as zf:
        names = set(zf.namelist())
        assert {'status.redacted.json', 'logs.redacted.json', 'config.redacted.json', 'bundle_manifest.json'} <= names
        status = json.loads(zf.read('status.redacted.json'))
        config = json.loads(zf.read('config.redacted.json'))
        logs = json.loads(zf.read('logs.redacted.json'))
    assert status['api_key'] == 'KKKK...KKKK'
    assert config['api_secret'] == 'CCCC...CCCC'
    assert logs[0]['data']['api_secret'] == 'ZZZZ...ZZZZ'


def test_engine_status_includes_diagnostics_snapshot(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / 'diag.db'))
    store.append_log(LogEvent(ts=10, level='WARN', code='AUTO_ENTRY_BLOCKED', message='blocked', data={'reason': 'x'}))
    engine = TradeBotEngine.__new__(TradeBotEngine)
    engine.store = store
    engine.runtime = RuntimeState()
    engine.runtime.ws_status = 'CONNECTED'
    engine.runtime.state = 'FLAT'
    engine.settings = Settings(ai_provider_enabled=False)
    engine.ai_provider = None
    engine.symbol_rules = None
    engine._running = True
    engine._latest_book = {}
    engine._closed_candles = []
    engine._expire_safe_mode = lambda: None
    engine._model_quality_snapshot = lambda: {}
    engine._performance_snapshot = lambda: {}
    engine._config_safety_snapshot = lambda: {'safe_to_trade': True, 'contract_version': '4B.4.3.6.6.15'}

    status = asyncio.run(TradeBotEngine.get_status(engine))

    assert status['contract_version'] == '4B.4.3.6.6.20'
    assert status['diagnostics_snapshot']['contract_version'] == '4B.4.3.6.6.17'
    assert status['diagnostics_snapshot']['event_summary']['warning_event_count'] == 1
    assert status['diagnostics_snapshot']['snapshots_available']['config_safety'] is True
