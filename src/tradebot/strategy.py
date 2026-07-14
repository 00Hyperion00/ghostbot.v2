from __future__ import annotations

from typing import Protocol

from .config import Settings
from .indicators import atr, ema, rsi
from .models import Candle, SignalDecision
from .utils import ratio, stable_hash


def evaluate_technical_strategy(closed_candles: list[Candle], settings: Settings) -> SignalDecision:
    candles = list(closed_candles)
    candles.sort(key=lambda c: c.close_time)
    lookback_need = max(settings.ema_slow_period, settings.rsi_period + 1, settings.volume_sma_period) + 2
    if len(candles) < lookback_need:
        return SignalDecision(signal='HOLD', trend='UNKNOWN', reason=f'Yetersiz kapanmış mum ({len(candles)}/{lookback_need})')

    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    quote_volumes = [c.quote_volume for c in candles]

    fast_arr = ema(closes, settings.ema_fast_period)
    slow_arr = ema(closes, settings.ema_slow_period)
    rsi_arr = rsi(closes, settings.rsi_period)
    qv_avg_arr = ema(quote_volumes, settings.volume_sma_period)
    atr_arr = atr(highs, lows, closes, settings.atr_period)

    i = len(candles) - 1
    p = len(candles) - 2
    ema_fast = fast_arr[i]
    ema_slow = slow_arr[i]
    prev_ema_fast = fast_arr[p]
    prev_ema_slow = slow_arr[p]
    rsi_now = rsi_arr[i]
    signal_quote_volume = quote_volumes[i]
    quote_volume_avg = qv_avg_arr[i]
    volume_ratio = ratio(signal_quote_volume, quote_volume_avg)
    taker_buy_pressure = ratio(candles[i].taker_buy_quote_volume, signal_quote_volume)
    trend = 'FLAT'
    if ema_fast is not None and ema_slow is not None:
        trend = 'UP' if ema_fast > ema_slow else ('DOWN' if ema_fast < ema_slow else 'FLAT')

    bullish_cross = None not in (prev_ema_fast, prev_ema_slow, ema_fast, ema_slow) and prev_ema_fast <= prev_ema_slow and ema_fast > ema_slow
    bearish_cross = None not in (prev_ema_fast, prev_ema_slow, ema_fast, ema_slow) and prev_ema_fast >= prev_ema_slow and ema_fast < ema_slow
    volume_ok = volume_ratio is not None and volume_ratio >= settings.volume_multiplier
    meaningful_volume = volume_ratio is not None and volume_ratio >= settings.min_meaningful_volume_ratio
    rsi_buy_ok = rsi_now is not None and rsi_now >= settings.rsi_buy_threshold
    rsi_sell_ok = rsi_now is not None and rsi_now <= settings.rsi_sell_threshold

    reasons: list[str] = []
    signal = 'HOLD'
    if bullish_cross and rsi_buy_ok and volume_ok:
        signal = 'BUY'
        reasons += ['EMA bullish cross', f'RSI {rsi_now:.2f} >= {settings.rsi_buy_threshold}', f'QuoteVol x{volume_ratio:.3f} >= {settings.volume_multiplier}']
    elif bearish_cross and rsi_sell_ok and volume_ok:
        signal = 'SELL'
        reasons += ['EMA bearish cross', f'RSI {rsi_now:.2f} <= {settings.rsi_sell_threshold}', f'QuoteVol x{volume_ratio:.3f} >= {settings.volume_multiplier}']
    else:
        reasons += [f'Trend {trend}', 'Yeni cross yok' if not (bullish_cross or bearish_cross) else ('Bullish cross var' if bullish_cross else 'Bearish cross var')]
        reasons.append('RSI yok' if rsi_now is None else f'RSI {rsi_now:.2f}')
        reasons.append('QuoteVol oranı yok' if volume_ratio is None else f'QuoteVol x{volume_ratio:.3f}')
        if taker_buy_pressure is not None:
            reasons.append(f"TakerBuy {(taker_buy_pressure * 100):.1f}%{' (bilgi)' if not meaningful_volume else ''}")

    return SignalDecision(
        signal=signal,
        trend=trend,
        reason=' | '.join(reasons),
        provider='technical',
        last_evaluated_close_time=candles[i].close_time,
        metrics={
            'emaFast': ema_fast,
            'emaSlow': ema_slow,
            'prevEmaFast': prev_ema_fast,
            'prevEmaSlow': prev_ema_slow,
            'rsi': rsi_now,
            'signalQuoteVolume': signal_quote_volume,
            'quoteVolumeAvg': quote_volume_avg,
            'volumeRatio': volume_ratio,
            'takerBuyPressure': taker_buy_pressure,
            'atr': atr_arr[i],
        },
    )


def _merge_ai_metrics(base_decision: SignalDecision, ai_decision: SignalDecision) -> dict:
    merged_metrics = dict(base_decision.metrics or {})
    merged_metrics['technicalSignal'] = base_decision.signal
    merged_metrics['technicalTrend'] = base_decision.trend
    merged_metrics['technicalReason'] = base_decision.reason
    merged_metrics.update(ai_decision.metrics or {})
    return merged_metrics


class _StrategyEventLogger(Protocol):
    def warn(self, code: str, message: str, data: dict | None = None, *, dedupe_ms: int | None = None) -> None:
        ...
def normalize_signal_with_ai(
    base_decision: SignalDecision,
    settings: Settings,
    *,
    closed_candles: list[Candle] | None = None,
    ai_provider: object | None = None,
    event_logger: _StrategyEventLogger | None = None,
) -> SignalDecision:
    if not settings.ai_provider_enabled:
        return base_decision
    if settings.ai_provider_mode == 'local_xgboost' and ai_provider is not None and closed_candles:
        try:
            ai_decision = ai_provider.predict(closed_candles)
            merged_metrics = _merge_ai_metrics(base_decision, ai_decision)
            if ai_decision.signal in {'BUY', 'SELL'}:
                return SignalDecision(
                    signal=ai_decision.signal,
                    trend=ai_decision.trend,
                    reason=ai_decision.reason,
                    provider='ai',
                    confidence=ai_decision.confidence,
                    last_evaluated_close_time=ai_decision.last_evaluated_close_time,
                    metrics=merged_metrics,
                )
            if ai_decision.reason:
                return SignalDecision(
                    signal='HOLD',
                    trend=ai_decision.trend,
                    reason=ai_decision.reason,
                    provider='ai',
                    confidence=ai_decision.confidence,
                    last_evaluated_close_time=ai_decision.last_evaluated_close_time,
                    metrics=merged_metrics,
                )
        except Exception as exc:
    confidence = 0.5
    trend = base_decision.trend
    rsi_now = metrics.get('rsi')
    volume_ratio = metrics.get('volumeRatio') or 0.0
    taker = metrics.get('takerBuyPressure') or 0.5
    if trend == 'UP':
        confidence += 0.08
    elif trend == 'DOWN':
        confidence -= 0.08
    if rsi_now is not None:
        confidence += max(min((rsi_now - 50) / 100, 0.15), -0.15)
    confidence += max(min((volume_ratio - 1) * 0.1, 0.15), -0.15)
    confidence += max(min((taker - 0.5) * 0.25, 0.12), -0.12)
    confidence = max(0.0, min(1.0, confidence))

    signal = 'HOLD'
    if confidence >= settings.ai_buy_threshold:
        signal = 'BUY'
    elif confidence <= (1 - settings.ai_sell_threshold):
        signal = 'SELL'

    if base_decision.signal in {'BUY', 'SELL'}:
        signal = base_decision.signal

    merged_metrics = dict(metrics or {})
    merged_metrics.setdefault('technicalSignal', base_decision.signal)
    return SignalDecision(
        signal=signal,
        trend=base_decision.trend,
        reason=f'AI Kararı | Güven Skoru: %{confidence * 100:.1f}',
        provider='ai' if signal != base_decision.signal else 'hybrid',
        confidence=confidence,
        last_evaluated_close_time=base_decision.last_evaluated_close_time,
        metrics=merged_metrics,
    )


def effective_auto_signal(decision: SignalDecision, mode: str) -> SignalDecision:
    if mode == 'test_buy_once':
        return SignalDecision(signal='BUY', trend=decision.trend, reason=f'TEST BUY | {decision.reason}', provider='test', confidence=decision.confidence, metrics=decision.metrics, last_evaluated_close_time=decision.last_evaluated_close_time)
    if mode == 'test_sell_once':
        return SignalDecision(signal='SELL', trend=decision.trend, reason=f'TEST SELL | {decision.reason}', provider='test', confidence=decision.confidence, metrics=decision.metrics, last_evaluated_close_time=decision.last_evaluated_close_time)
    if mode == 'relaxed' and decision.signal == 'HOLD':
        if decision.trend == 'UP':
            return SignalDecision(signal='BUY', trend=decision.trend, reason=f'RELAXED BUY | {decision.reason}', provider='relaxed', confidence=decision.confidence, metrics=decision.metrics, last_evaluated_close_time=decision.last_evaluated_close_time)
        if decision.trend == 'DOWN':
            return SignalDecision(signal='SELL', trend=decision.trend, reason=f'RELAXED SELL | {decision.reason}', provider='relaxed', confidence=decision.confidence, metrics=decision.metrics, last_evaluated_close_time=decision.last_evaluated_close_time)
    return decision


def build_signal_key(symbol: str, interval: str, decision: SignalDecision) -> str:
    bucket = decision.last_evaluated_close_time or 0
    return f'{symbol}|{interval}|{decision.signal}|{bucket}|{stable_hash(decision.reason)}'
