from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tradebot.api import create_app
from tradebot.ui.dashboard import DashboardApp


class DummyProvider:
    def __init__(self, *, available: bool = False, fail: bool = False):
        self.available = available
        self.fail = fail
        self.load_error = 'initial' if not available else None
        self.calls = []
        self._schema_info = {
            'schema_validated': available,
            'schema_version': '4B.3.4' if available else None,
            'feature_pack_name': 'core_price_action_regime_vwap_mtf15_v1' if available else None,
            'feature_count': 40 if available else None,
            'feature_lag': 1,
        }

    def reload(self, *, model_path=None, threshold=None, buy_threshold=None, sell_threshold=None, hold_band_low=None, hold_band_high=None, indecision_margin=None):
        self.calls.append((model_path, threshold, buy_threshold, sell_threshold, hold_band_low, hold_band_high, indecision_margin))
        if self.fail:
            self.available = False
            self.load_error = 'reload failed'
            return False
        self.available = True
        self.load_error = None
        self._schema_info.update({'schema_validated': True, 'schema_version': '4B.3.4', 'feature_count': 40})
        return True

    def schema_info(self):
        return dict(self._schema_info, load_error=self.load_error)


class DummySettings:
    symbol = 'ETHUSDT'
    kline_interval = '1m'
    base_url = 'https://demo-api.binance.com'
    ai_provider_enabled = True
    ai_provider_mode = 'local_xgboost'
    ai_model_path = 'models/old.ubj'
    ai_confidence_threshold = 0.6
    ai_buy_threshold = 0.64
    ai_sell_threshold = 0.57
    ai_hold_band_low = 0.45
    ai_hold_band_high = 0.55
    ai_indecision_margin = 0.08

    def to_dict(self):
        return {}


class DummyEngine:
    def __init__(self, provider=None):
        self.settings = DummySettings()
        self.ai_provider = provider if provider is not None else DummyProvider()
        self._running = True
        self.store = type('Store', (), {'fetch_logs': lambda self, limit=200: []})()

    async def get_status(self):
        return {}

    async def start(self):
        return False

    async def stop(self):
        return True

    async def force_buy(self):
        return None

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


def test_ai_reload_is_successful_and_updates_settings():
    engine = DummyEngine(DummyProvider())
    client = TestClient(create_app(engine))
    resp = client.post('/ai/reload', json={'model_path': 'models/new.ubj', 'threshold': 0.72})
    payload = resp.json()
    assert payload['ok'] is True
    assert payload['reload_ok'] is True
    assert payload['available'] is True
    assert engine.settings.ai_model_path == 'models/new.ubj'
    assert engine.settings.ai_confidence_threshold == 0.72
    assert engine.ai_provider.calls[-1][0] == 'models/new.ubj'


def test_ai_reload_failure_does_not_overwrite_active_settings():
    engine = DummyEngine(DummyProvider(available=True, fail=True))
    client = TestClient(create_app(engine))
    resp = client.post('/ai/reload', json={'model_path': 'models/bad.ubj', 'threshold': 0.91})
    payload = resp.json()
    assert payload['ok'] is False
    assert payload['reload_ok'] is False
    assert engine.settings.ai_model_path == 'models/old.ubj'
    assert engine.settings.ai_confidence_threshold == 0.6


def test_ai_train_calls_training_then_reload(monkeypatch, tmp_path: Path):
    engine = DummyEngine(DummyProvider())
    client = TestClient(create_app(engine))
    trained_model = tmp_path / 'ETHUSDT_model.ubj'

    def fake_train(symbol, interval, days, out, base_url, **kwargs):
        assert symbol == 'ETHUSDT'
        assert interval == '1m'
        assert days == 7
        assert Path(out).suffix == '.ubj'
        return {
            'symbol': symbol,
            'interval': interval,
            'days': days,
            'model_path': trained_model.as_posix(),
            'schema_path': trained_model.with_suffix('.schema.json').as_posix(),
            'manifest_path': trained_model.with_suffix('.manifest.json').as_posix(),
            'workflow_version': '4B.4.3.6.6.4',
            'clean_samples': 2400,
            'calibrated_accuracy': 0.44,
            'calibrated_action_report': {'hold_rate': 0.82, 'action_coverage': 0.18, 'non_hold_rate': 0.18},
            'calibrated_reason_counts': {'RAW_TOP_HOLD': 1968, 'RAW_ACTION_FIRST_ACCEPT': 432},
            'calibrated_predicted_class_distribution': {'0': 1968, '1': 216, '2': 216},
        }

    monkeypatch.setattr('tradebot.api.train_xgb_model', fake_train)
    resp = client.post('/ai/train', json={'symbol': 'ETHUSDT', 'days': 7, 'out': str(tmp_path / 'candidate.json')})
    payload = resp.json()
    assert payload['ok'] is True
    assert payload['trained'] is True
    assert payload['reloaded'] is True
    assert engine.settings.ai_model_path == trained_model.as_posix()


def test_ai_train_blocks_reload_when_quality_gate_fails(monkeypatch, tmp_path: Path):
    engine = DummyEngine(DummyProvider(available=True))
    client = TestClient(create_app(engine))

    def fake_train(symbol, interval, days, out, base_url, **kwargs):
        return {
            'symbol': symbol,
            'interval': interval,
            'days': days,
            'model_path': (tmp_path / 'weak.ubj').as_posix(),
            'workflow_version': '4B.4.3.6.6.4',
            'clean_samples': 2500,
            'calibrated_accuracy': 0.42,
            'calibrated_action_report': {'hold_rate': 0.995, 'action_coverage': 0.005, 'non_hold_rate': 0.005},
            'calibrated_reason_counts': {'RAW_TOP_HOLD': 2488, 'REJECT_LOW_MARGIN': 12},
            'calibrated_predicted_class_distribution': {'0': 2488, '1': 6, '2': 6},
        }

    monkeypatch.setattr('tradebot.api.train_xgb_model', fake_train)
    resp = client.post('/ai/train', json={'symbol': 'ETHUSDT', 'days': 7, 'out': str(tmp_path / 'weak.json')})
    payload = resp.json()

    assert payload['ok'] is False
    assert payload['trained'] is True
    assert payload['reloaded'] is False
    assert payload['reload_blocked'] is True
    assert payload['quality_gate']['decision'] == 'BLOCK'
    assert 'TRAINING_ACTION_COVERAGE_LOW' in payload['quality_gate']['reason_codes']
    assert engine.settings.ai_model_path == 'models/old.ubj'


def test_dashboard_extracts_json_training_output_path():
    app = DashboardApp.__new__(DashboardApp)
    line = '{"symbol":"ETHUSDT","model_path":"models/ETHUSDT_model.ubj","workflow_version":"4B.4.3.6.6.4"}'
    assert app._extract_training_output_path(line) == 'models/ETHUSDT_model.ubj'


def test_dashboard_resolve_training_output_path_forces_ubj(tmp_path: Path):
    app = DashboardApp.__new__(DashboardApp)
    app.project_root = tmp_path

    class Entry:
        def get(self):
            return 'models/ETHUSDT_model.json'

    app.form = {'ai_model_path': Entry()}
    out = app._resolve_training_output_path('ETHUSDT')
    assert out.suffix == '.ubj'
    assert out.as_posix().endswith('/models/ETHUSDT_model.ubj')

class AuditStore:
    def __init__(self):
        self._logs = []

    def fetch_logs(self, limit=200, order='desc'):
        rows = list(self._logs)
        if order == 'desc':
            rows.reverse()
        return rows[:limit] if limit else rows

    def append_log(self, event):
        if isinstance(event, dict):
            self._logs.append(event)
            return
        self._logs.append({
            'ts': getattr(event, 'ts', 0),
            'level': getattr(event, 'level', ''),
            'code': getattr(event, 'code', ''),
            'message': getattr(event, 'message', ''),
            'data': getattr(event, 'data', {}),
        })


def test_ai_train_quality_gate_block_is_audited(monkeypatch, tmp_path: Path):
    engine = DummyEngine(DummyProvider(available=True))
    engine.store = AuditStore()
    client = TestClient(create_app(engine))

    def fake_train(symbol, interval, days, out, base_url, **kwargs):
        return {
            'symbol': symbol,
            'interval': interval,
            'days': days,
            'model_path': (tmp_path / 'blocked.ubj').as_posix(),
            'workflow_version': '4B.4.3.6.6.4',
            'clean_samples': 2500,
            'calibrated_action_report': {'hold_rate': 0.995, 'action_coverage': 0.005, 'non_hold_rate': 0.005},
            'calibrated_reason_counts': {'RAW_TOP_HOLD': 2488, 'REJECT_LOW_MARGIN': 12},
            'calibrated_predicted_class_distribution': {'0': 2488, '1': 6, '2': 6},
        }

    monkeypatch.setattr('tradebot.api.train_xgb_model', fake_train)
    response = client.post('/ai/train', json={'symbol': 'ETHUSDT', 'days': 7, 'out': str(tmp_path / 'blocked.json')})
    audit = client.get('/events/audit', params={'category': 'Model', 'order': 'asc', 'limit': 0}).json()

    assert response.json()['reload_blocked'] is True
    assert [event['code'] for event in audit['events']] == ['AI_TRAIN_QUALITY_GATE_BLOCKED_RELOAD']
    assert audit['events'][0]['data']['reload_allowed'] is False
    assert audit['events'][0]['data']['reason_codes']
