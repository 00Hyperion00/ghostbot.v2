from tradebot.models import Candle, SignalDecision
from tradebot.strategy import normalize_signal_with_ai


class DummySettings:
    ai_provider_enabled = True
    ai_provider_mode = 'local_xgboost'
    ai_buy_threshold = 0.64
    ai_sell_threshold = 0.57


class DummyProvider:
    def __init__(self, decision: SignalDecision):
        self._decision = decision

    def predict(self, candles):
        return self._decision


def test_normalize_signal_with_ai_preserves_ai_metrics_for_hold():
    base = SignalDecision(
        signal='HOLD',
        trend='UP',
        reason='tech hold',
        provider='technical',
        confidence=None,
        last_evaluated_close_time=123,
        metrics={'emaFast': 1.0},
    )
    ai = SignalDecision(
        signal='HOLD',
        trend='DOWN',
        reason='AI Kararı | Güven Skoru: %71.0',
        provider='ai',
        confidence=0.71,
        last_evaluated_close_time=123,
        metrics={
            'rawPredictedClass': 2,
            'calibratedClass': 0,
            'calibrationReason': 'REJECT_HOLD_DOMINANCE',
            'buyProbability': 0.12,
            'sellProbability': 0.47,
            'holdProbability': 0.41,
        },
    )
    out = normalize_signal_with_ai(base, DummySettings(), closed_candles=[Candle(0, 1, 1, 1, 1, 1, 1, 1)], ai_provider=DummyProvider(ai))
    assert out.signal == 'HOLD'
    assert out.metrics['technicalSignal'] == 'HOLD'
    assert out.metrics['rawPredictedClass'] == 2
    assert out.metrics['calibrationReason'] == 'REJECT_HOLD_DOMINANCE'


def test_normalize_signal_with_ai_preserves_metrics_for_buy():
    base = SignalDecision(signal='HOLD', trend='UP', reason='tech hold', provider='technical', metrics={'emaFast': 1.0})
    ai = SignalDecision(
        signal='BUY',
        trend='UP',
        reason='AI Kararı | Güven Skoru: %80.0',
        provider='ai',
        confidence=0.80,
        last_evaluated_close_time=456,
        metrics={'rawPredictedClass': 1, 'calibratedClass': 1, 'calibrationReason': 'RAW_ACTION_FIRST_ACCEPT'},
    )
    out = normalize_signal_with_ai(base, DummySettings(), closed_candles=[Candle(0, 1, 1, 1, 1, 1, 1, 1)], ai_provider=DummyProvider(ai))
    assert out.signal == 'BUY'
    assert out.metrics['technicalSignal'] == 'HOLD'
    assert out.metrics['calibratedClass'] == 1


class FailingProvider:
    def predict(self, candles):
        raise RuntimeError('model unavailable')


class CapturingLogger:
    def __init__(self):
        self.events = []

    def warn(self, code, message, data=None, *, dedupe_ms=None):
        self.events.append((code, message, data, dedupe_ms))


def test_normalize_signal_with_ai_logs_provider_failure_and_falls_back():
    base = SignalDecision(
        signal='HOLD',
        trend='UP',
        reason='tech hold',
        provider='technical',
        confidence=None,
        last_evaluated_close_time=789,
        metrics={'rsi': 55.0, 'volumeRatio': 1.0, 'takerBuyPressure': 0.5},
    )
    logger = CapturingLogger()

    out = normalize_signal_with_ai(
        base,
        DummySettings(),
        closed_candles=[Candle(0, 1, 1, 1, 1, 1, 1, 1)],
        ai_provider=FailingProvider(),
        event_logger=logger,
    )

    assert out.provider in {'ai', 'hybrid'}
    assert out.last_evaluated_close_time == 789
    assert logger.events
    code, _message, data, dedupe_ms = logger.events[0]
    assert code == 'AI_PROVIDER_PREDICT_FAILED'
    assert data['errorType'] == 'RuntimeError'
    assert data['technicalSignal'] == 'HOLD'
    assert dedupe_ms == 60_000


