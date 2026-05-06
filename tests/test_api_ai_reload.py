from fastapi.testclient import TestClient

from tradebot.api import create_app


class DummyProvider:
    def __init__(self):
        self.available = False
        self.load_error = 'boom'
        self.calls = []

    def reload(self, *, model_path=None, threshold=None, buy_threshold=None, sell_threshold=None, hold_band_low=None, hold_band_high=None, indecision_margin=None):
        self.calls.append((model_path, threshold, buy_threshold, sell_threshold, hold_band_low, hold_band_high, indecision_margin))
        self.available = True
        self.load_error = None


class DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def warn(self, *args, **kwargs):
        pass


class DummySettings:
    symbol = 'SOLUSDT'
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
    def __init__(self):
        self.settings = DummySettings()
        self.ai_provider = DummyProvider()
        self.logger = DummyLogger()
        self._running = True
        self.runtime = type('Runtime', (), {'state': 'FLAT'})()
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


def test_ai_reload_updates_engine_settings_and_provider():
    engine = DummyEngine()
    client = TestClient(create_app(engine))
    resp = client.post('/ai/reload', json={'model_path': 'models/new.ubj', 'threshold': 0.73})
    payload = resp.json()
    assert payload['ok'] is True
    assert engine.settings.ai_model_path == 'models/new.ubj'
    assert engine.settings.ai_confidence_threshold == 0.73
    assert engine.ai_provider.calls == [('models/new.ubj', 0.73, 0.64, 0.57, 0.45, 0.55, 0.08)]
