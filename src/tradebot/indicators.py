from __future__ import annotations


def ema(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError('period must be positive')
    result: list[float | None] = [None] * len(values)
    if not values:
        return result
    multiplier = 2 / (period + 1)
    seed = None
    for idx, value in enumerate(values):
        if seed is None:
            seed = value
        else:
            seed = (value - seed) * multiplier + seed
        if idx >= period - 1:
            result[idx] = seed
    return result


def rsi(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period + 1:
        return result
    gains = []
    losses = []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100 - (100 / (1 + rs))
    for i in range(period + 1, len(values)):
        gain = gains[i - 1]
        loss = losses[i - 1]
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100 - (100 / (1 + rs))
    return result


def atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float | None]:
    size = min(len(highs), len(lows), len(closes))
    result: list[float | None] = [None] * size
    if size < period + 1:
        return result
    trs: list[float] = []
    for i in range(size):
        prev_close = closes[i - 1] if i > 0 else closes[i]
        tr = max(highs[i] - lows[i], abs(highs[i] - prev_close), abs(lows[i] - prev_close))
        trs.append(tr)
    current = sum(trs[1:period + 1]) / period
    result[period] = current
    for i in range(period + 1, size):
        current = ((current * (period - 1)) + trs[i]) / period
        result[i] = current
    return result
