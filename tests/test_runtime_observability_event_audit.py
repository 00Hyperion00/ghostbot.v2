from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

from tradebot.api import create_app
from tradebot.engine import TradeBotEngine
from tradebot.logger import EventLogger
from tradebot.models import LogEvent, RuntimeState
from tradebot.observability import audit_category, audit_severity, normalize_audit_event, summarize_audit_events
from tradebot.persistence import SQLiteStore


def test_audit_normalization_redacts_secrets_and_sets_operator_fields() -> None:
    event = normalize_audit_event({
        'ts': 1,
        'level': 'INFO',
        'code': 'ORDER_SUBMITTED',
        'message': 'submitted',
        'data': {'clientOrderId': 'CID-1', 'api_secret': 'must-not-leak', 'side': 'BUY'},
    })

    assert event['category'] == 'Orders'
    assert event['severity'] == 'info'
    assert event['correlation_id'] == 'CID-1'
    assert event['data']['api_secret'] == '[REDACTED]'


def test_audit_category_and_severity_cover_guard_and_model_events() -> None:
    assert audit_category('MIN_NOTIONAL_BLOCKED') == 'Guards'
    assert audit_category('AI_RELOAD_SUCCEEDED') == 'Model'
    assert audit_severity('WARN', 'MIN_NOTIONAL_BLOCKED') == 'warning'
    assert audit_severity('ERROR', 'AI_TRAIN_FAILED') == 'error'


def test_store_fetch_audit_events_filters_category_severity_and_code_prefix(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / 'audit.db'))
    store.append_log(LogEvent(ts=10, level='INFO', code='ORDER_SUBMITTED', message='buy', data={'clientOrderId': 'CID-2'}))
    store.append_log(LogEvent(ts=20, level='WARN', code='MIN_NOTIONAL_BLOCKED', message='blocked', data={'symbol': 'ETHUSDT'}))
    store.append_log(LogEvent(ts=30, level='INFO', code='AI_RELOAD_SUCCEEDED', message='reload', data={'model_path': 'm.ubj'}))

    order_events = store.fetch_audit_events(limit=0, order='asc', category='Orders')
    warning_events = store.fetch_audit_events(limit=0, order='asc', severity='warning')
    ai_events = store.fetch_audit_events(limit=0, order='asc', code_prefix='AI_')

    assert [event['code'] for event in order_events] == ['ORDER_SUBMITTED']
    assert [event['code'] for event in warning_events] == ['MIN_NOTIONAL_BLOCKED']
    assert [event['code'] for event in ai_events] == ['AI_RELOAD_SUCCEEDED']


def test_audit_summary_counts_categories_and_recent_events() -> None:
    summary = summarize_audit_events([
        {'ts': 1, 'level': 'INFO', 'code': 'ORDER_SUBMITTED', 'message': 'buy', 'data': {}},
        {'ts': 2, 'level': 'WARN', 'code': 'MIN_NOTIONAL_BLOCKED', 'message': 'blocked', 'data': {}},
    ])

    assert summary['event_count'] == 2
    assert summary['counts_by_category']['Orders'] == 1
    assert summary['counts_by_category']['Guards'] == 1
    assert summary['warning_count'] == 1
    assert summary['last_warning']['code'] == 'MIN_NOTIONAL_BLOCKED'


class _DummyExchange:
    async def fetch_klines(self, *args, **kwargs):
        return []


class _DummyEngine:
    def __init__(self, store: SQLiteStore) -> None:
        self._running = True
        self.store = store
        self.logger = EventLogger(store)
        self.exchange = _DummyExchange()
        self.settings = SimpleNamespace(
            symbol='ETHUSDT',
            kline_interval='1m',
            ai_provider_enabled=True,
            ai_provider_mode='local_xgboost',
            ai_model_path='models/model.ubj',
            ai_confidence_threshold=0.6,
        )
        self.ai_provider = SimpleNamespace(available=True)
        self.force_buy_called = False

    async def get_status(self):
        return {'state': 'FLAT', 'symbol': 'ETHUSDT', 'ws_status': 'CONNECTED'}

    async def start(self):
        return True

    async def stop(self):
        return True

    async def force_buy(self):
        self.force_buy_called = True

    async def force_sell(self):
        return None

    async def cancel_pending(self):
        return None

    async def sync_balances(self):
        return None

    async def risk_reset(self):
        return None

    async def toggle_safe_mode(self):
        return None


def test_api_audit_endpoint_returns_filterable_summary(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / 'api-audit.db'))
    store.append_log(LogEvent(ts=10, level='INFO', code='ORDER_SUBMITTED', message='buy', data={'clientOrderId': 'CID-3'}))
    store.append_log(LogEvent(ts=20, level='WARN', code='MIN_NOTIONAL_BLOCKED', message='blocked', data={'symbol': 'ETHUSDT'}))
    client = TestClient(create_app(_DummyEngine(store)))

    response = client.get('/events/audit', params={'limit': 0, 'order': 'asc', 'severity': 'warning'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['contract_version'] == '4B.4.3.6.6.11'
    assert payload['count'] == 1
    assert payload['events'][0]['code'] == 'MIN_NOTIONAL_BLOCKED'
    assert payload['summary']['warning_count'] == 1


def test_operator_action_is_written_to_audit_trail(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / 'operator.db'))
    engine = _DummyEngine(store)
    client = TestClient(create_app(engine))

    response = client.post('/force-buy')
    audit = client.get('/events/audit', params={'category': 'Operator', 'order': 'asc', 'limit': 0}).json()

    assert response.status_code == 200
    assert engine.force_buy_called is True
    assert [event['code'] for event in audit['events']] == ['OPERATOR_ACTION_REQUESTED', 'OPERATOR_ACTION_COMPLETED']


def test_engine_status_includes_event_audit_snapshot(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / 'engine-audit.db'))
    store.append_log(LogEvent(ts=10, level='INFO', code='ORDER_SUBMITTED', message='buy', data={'side': 'BUY'}))
    engine = TradeBotEngine.__new__(TradeBotEngine)
    engine.store = store
    engine.runtime = RuntimeState()
    engine.runtime.ws_status = 'CONNECTED'
    engine.runtime.state = 'FLAT'
    engine.settings = SimpleNamespace(
        ai_provider_enabled=False,
        ai_provider_mode='disabled',
        ai_model_path='-',
        ai_confidence_threshold=0.6,
    )
    engine.ai_provider = None
    engine.symbol_rules = None
    engine._running = True
    engine._latest_book = {}
    engine._closed_candles = []

    status = asyncio.run(engine.get_status())

    assert status['contract_version'] == '4B.4.3.6.6.20'
    assert status['event_audit_snapshot']['available'] is True
    assert status['event_audit_snapshot']['counts_by_category']['Orders'] == 1
