from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from .models import Candle

RAW_NUMERIC_COLUMNS = [
    'open_time', 'close_time', 'open', 'high', 'low', 'close', 'volume', 'quote_volume',
]

BASE_FEATURE_COLUMNS = [
    'open', 'high', 'low', 'close', 'volume',
    'EMA_9', 'EMA_21', 'RSI_14', 'MACD', 'MACD_Signal',
    'BB_Mid', 'BB_Upper', 'BB_Lower', 'ATR_14', 'ROC_9',
]
PRICE_ACTION_FEATURE_COLUMNS = [
    'body_pct', 'upper_wick_pct', 'lower_wick_pct', 'close_location_pct',
    'range_atr_ratio', 'bullish_engulfing_flag', 'bearish_engulfing_flag',
]
REGIME_FEATURE_COLUMNS = [
    'bb_width', 'atr_pct', 'ema_spread_pct', 'trend_strength_proxy',
    'volatility_regime_flag', 'range_regime_flag',
]
VWAP_FEATURE_COLUMNS = [
    'vwap_session', 'close_to_vwap_pct', 'high_to_vwap_pct', 'low_to_vwap_pct',
    'vwap_distance_atr_norm',
]
MTF_15M_FEATURE_COLUMNS = [
    'mtf_15m_trend_flag', 'mtf_15m_ema_gap_pct', 'mtf_15m_rsi_14',
    'mtf_15m_close_to_ema21_pct',
]
FEATURE_COLUMNS = [
    *BASE_FEATURE_COLUMNS,
    *PRICE_ACTION_FEATURE_COLUMNS,
    *REGIME_FEATURE_COLUMNS,
    *VWAP_FEATURE_COLUMNS,
    *MTF_15M_FEATURE_COLUMNS,
]


def _safe_div(numerator: Any, denominator: Any, *, default: float = 0.0) -> pd.Series:
    num = pd.Series(numerator, copy=False, dtype='float64')
    den = pd.Series(denominator, copy=False, dtype='float64').replace(0.0, np.nan)
    return (num / den).replace([np.inf, -np.inf], np.nan).fillna(default).astype('float64')


def _bounded(series: pd.Series, lower: float = 0.0, upper: float = 1.0) -> pd.Series:
    return pd.to_numeric(series, errors='coerce').clip(lower=lower, upper=upper)


def candles_to_frame(candles: Iterable[Candle | dict[str, Any]], *, closed_only: bool = True) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in candles:
        if isinstance(item, Candle):
            if closed_only and not bool(getattr(item, 'closed', True)):
                continue
            rows.append({
                'open_time': item.open_time,
                'close_time': item.close_time,
                'open': float(item.open),
                'high': float(item.high),
                'low': float(item.low),
                'close': float(item.close),
                'volume': float(item.volume),
                'quote_volume': float(item.quote_volume),
            })
        else:
            if closed_only and item.get('closed') is False:
                continue
            rows.append({
                'open_time': int(item.get('open_time', item.get('openTime', 0) or 0)),
                'close_time': int(item.get('close_time', item.get('closeTime', 0) or 0)),
                'open': float(item['open']),
                'high': float(item['high']),
                'low': float(item['low']),
                'close': float(item['close']),
                'volume': float(item['volume']),
                'quote_volume': float(item.get('quote_volume', item.get('quoteVolume', 0) or 0.0)),
            })
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values('close_time').reset_index(drop=True)
    return out


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in RAW_NUMERIC_COLUMNS:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors='coerce')
    return out


def _compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window).mean()
    rs = gain / loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(~((loss == 0) & (gain > 0)), 100.0)
    rsi = rsi.where(~((loss == 0) & (gain == 0)), 50.0)
    return rsi.astype('float64')


def _add_core_indicators(out: pd.DataFrame) -> None:
    close = out['close'].astype('float64')
    out['EMA_9'] = close.ewm(span=9, adjust=False).mean()
    out['EMA_21'] = close.ewm(span=21, adjust=False).mean()
    out['RSI_14'] = _compute_rsi(close, window=14)
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    out['MACD'] = ema_12 - ema_26
    out['MACD_Signal'] = out['MACD'].ewm(span=9, adjust=False).mean()
    out['BB_Mid'] = close.rolling(window=20).mean()
    out['BB_Std'] = close.rolling(window=20).std()
    out['BB_Upper'] = out['BB_Mid'] + out['BB_Std'] * 2
    out['BB_Lower'] = out['BB_Mid'] - out['BB_Std'] * 2
    out['tr0'] = (out['high'] - out['low']).abs()
    out['tr1'] = (out['high'] - out['close'].shift()).abs()
    out['tr2'] = (out['low'] - out['close'].shift()).abs()
    out['TR'] = out[['tr0', 'tr1', 'tr2']].max(axis=1)
    out['ATR_14'] = out['TR'].rolling(window=14).mean()
    out['ROC_9'] = close.pct_change(periods=9) * 100


def _add_price_action(out: pd.DataFrame) -> None:
    candle_range = (out['high'] - out['low']).abs()
    body = (out['close'] - out['open']).abs()
    upper_wick = out['high'] - pd.concat([out['open'], out['close']], axis=1).max(axis=1)
    lower_wick = pd.concat([out['open'], out['close']], axis=1).min(axis=1) - out['low']
    out['body_pct'] = _bounded(_safe_div(body, candle_range))
    out['upper_wick_pct'] = _bounded(_safe_div(upper_wick.clip(lower=0), candle_range))
    out['lower_wick_pct'] = _bounded(_safe_div(lower_wick.clip(lower=0), candle_range))
    total = out['body_pct'] + out['upper_wick_pct'] + out['lower_wick_pct']
    out['body_pct'] = _safe_div(out['body_pct'], total, default=0.0)
    out['upper_wick_pct'] = _safe_div(out['upper_wick_pct'], total, default=0.0)
    out['lower_wick_pct'] = _safe_div(out['lower_wick_pct'], total, default=0.0)
    out['close_location_pct'] = _bounded(_safe_div(out['close'] - out['low'], candle_range))
    out['range_atr_ratio'] = _safe_div(candle_range, out['ATR_14']).clip(lower=0.0)
    prev_open = out['open'].shift(1)
    prev_close = out['close'].shift(1)
    out['bullish_engulfing_flag'] = (
        (out['close'] > out['open']) & (prev_close < prev_open) &
        (out['open'] <= prev_close) & (out['close'] >= prev_open)
    ).astype('float64')
    out['bearish_engulfing_flag'] = (
        (out['close'] < out['open']) & (prev_close > prev_open) &
        (out['open'] >= prev_close) & (out['close'] <= prev_open)
    ).astype('float64')


def _add_regime(out: pd.DataFrame) -> None:
    out['bb_width'] = _safe_div(out['BB_Upper'] - out['BB_Lower'], out['close'].abs()) * 100
    out['atr_pct'] = _safe_div(out['ATR_14'], out['close'].abs()) * 100
    out['ema_spread_pct'] = _safe_div((out['EMA_9'] - out['EMA_21']).abs(), out['close'].abs()) * 100
    out['trend_strength_proxy'] = _safe_div(out['ema_spread_pct'], out['atr_pct'].replace(0.0, np.nan)).clip(lower=0.0)
    atr_median = out['atr_pct'].rolling(window=50, min_periods=10).median()
    bb_median = out['bb_width'].rolling(window=50, min_periods=10).median()
    out['volatility_regime_flag'] = (out['atr_pct'] > atr_median).astype('float64')
    out['range_regime_flag'] = (out['bb_width'] < bb_median).astype('float64')


def _add_vwap(out: pd.DataFrame) -> None:
    typical = (out['high'] + out['low'] + out['close']) / 3.0
    volume = out['volume'].clip(lower=0).fillna(0.0)
    ts = pd.to_datetime(out['open_time'], unit='ms', errors='coerce')
    if ts.isna().all():
        session_key = pd.Series(np.zeros(len(out), dtype=int), index=out.index)
    else:
        session_key = ts.dt.floor('D').astype('int64')
    cum_pv = (typical * volume).groupby(session_key).cumsum()
    cum_vol = volume.groupby(session_key).cumsum()
    out['vwap_session'] = _safe_div(cum_pv, cum_vol, default=np.nan)
    out['close_to_vwap_pct'] = _safe_div(out['close'] - out['vwap_session'], out['vwap_session'].abs()) * 100
    out['high_to_vwap_pct'] = _safe_div(out['high'] - out['vwap_session'], out['vwap_session'].abs()) * 100
    out['low_to_vwap_pct'] = _safe_div(out['low'] - out['vwap_session'], out['vwap_session'].abs()) * 100
    out['vwap_distance_atr_norm'] = _safe_div((out['close'] - out['vwap_session']).abs(), out['ATR_14'])


def _add_mtf_15m(out: pd.DataFrame) -> None:
    mtf_close = out['close'].rolling(window=15, min_periods=15).mean()
    mtf_fast = mtf_close.ewm(span=9, adjust=False).mean()
    mtf_slow = mtf_close.ewm(span=21, adjust=False).mean()
    mtf_rsi = _compute_rsi(mtf_close, window=14)
    gap_pct = _safe_div(mtf_fast - mtf_slow, mtf_slow.abs()) * 100
    out['mtf_15m_trend_flag'] = np.select([gap_pct > 0.01, gap_pct < -0.01], [1.0, -1.0], default=0.0)
    out['mtf_15m_ema_gap_pct'] = gap_pct
    out['mtf_15m_rsi_14'] = mtf_rsi.clip(lower=0.0, upper=100.0)
    out['mtf_15m_close_to_ema21_pct'] = _safe_div(out['close'] - mtf_slow, mtf_slow.abs()) * 100


def build_feature_frame(df: pd.DataFrame, *, feature_lag: int = 1) -> pd.DataFrame:
    out = _normalize_ohlcv(df)
    if out.empty:
        for col in FEATURE_COLUMNS:
            out[col] = pd.Series(dtype='float32')
        return out
    _add_core_indicators(out)
    _add_price_action(out)
    _add_regime(out)
    _add_vwap(out)
    _add_mtf_15m(out)
    lag = max(int(feature_lag or 0), 0)
    if lag > 0:
        shifted = out.loc[:, FEATURE_COLUMNS].astype('float64').shift(lag)
        for col in FEATURE_COLUMNS:
            out[col] = shifted[col]
    for col in FEATURE_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors='coerce').replace([np.inf, -np.inf], np.nan)
    return out


def clean_feature_frame(df: pd.DataFrame, *, require_target: bool = False, feature_columns: Sequence[str] | None = None) -> pd.DataFrame:
    out = df.copy()
    cols = list(feature_columns or FEATURE_COLUMNS)
    missing = [col for col in cols if col not in out.columns]
    if missing:
        raise KeyError(f'Missing feature columns: {missing}')
    for col in cols:
        out[col] = pd.to_numeric(out[col], errors='coerce').replace([np.inf, -np.inf], np.nan).astype('float32')
    required = list(cols)
    if require_target:
        if 'target' not in out.columns:
            raise KeyError('Missing target column: target')
        out['target'] = pd.to_numeric(out['target'], errors='coerce')
        required.append('target')
    out = out.dropna(subset=required).reset_index(drop=True)
    if require_target:
        out['target'] = out['target'].astype('int64')
    return out


def get_default_feature_schema():
    from .training.feature_schema import make_default_schema
    return make_default_schema(FEATURE_COLUMNS, RAW_NUMERIC_COLUMNS)


def latest_feature_row(df: pd.DataFrame, *, feature_lag: int = 1, feature_columns: Sequence[str] | None = None) -> pd.DataFrame | None:
    cols = list(feature_columns or FEATURE_COLUMNS)
    featured = clean_feature_frame(build_feature_frame(df, feature_lag=feature_lag), feature_columns=cols)
    if featured.empty:
        return None
    return featured.iloc[-1:][cols].astype('float32')


def _target_for_window(ref: pd.DataFrame, idx: int, *, lookahead: int, atr_multiplier: float, min_profit_bps: float, use_high_low_barriers: bool, ambiguous_barrier_policy: str) -> int:
    current_close = float(ref.iloc[idx]['close'])
    current_atr = float(ref.iloc[idx]['ATR_14'])
    if not np.isfinite(current_close) or not np.isfinite(current_atr) or current_atr <= 0:
        return 0
    move = (current_atr * float(atr_multiplier)) + (current_close * max(float(min_profit_bps or 0.0), 0.0) / 10_000.0)
    upper = current_close + move
    lower = current_close - move
    future = ref.iloc[idx + 1: idx + lookahead + 1]
    if use_high_low_barriers:
        policy = str(ambiguous_barrier_policy or 'hold').lower()
        for _, bar in future.iterrows():
            hit_up = float(bar['high']) > upper
            hit_down = float(bar['low']) < lower
            if hit_up and hit_down:
                return 1 if policy == 'buy' else 2 if policy == 'sell' else 0
            if hit_up:
                return 1
            if hit_down:
                return 2
        return 0
    if float(future['close'].max()) >= upper:
        return 1
    if float(future['close'].min()) <= lower:
        return 2
    return 0


def build_atr_targets(df: pd.DataFrame, lookahead: int = 10, atr_multiplier: float = 1.5, *, feature_lag: int = 1, min_profit_bps: float = 0.0, use_high_low_barriers: bool = False, ambiguous_barrier_policy: str = 'hold') -> pd.DataFrame:
    feature_frame = build_feature_frame(df, feature_lag=feature_lag).copy()
    ref = build_feature_frame(df, feature_lag=0)
    if feature_frame.empty or len(feature_frame) <= lookahead:
        labeled = feature_frame.iloc[0:0].copy()
        labeled['target'] = pd.Series(dtype='int64')
        return labeled
    targets = [np.nan] * len(feature_frame)
    for idx in range(len(feature_frame) - int(lookahead)):
        targets[idx] = _target_for_window(
            ref,
            idx,
            lookahead=int(lookahead),
            atr_multiplier=float(atr_multiplier),
            min_profit_bps=float(min_profit_bps or 0.0),
            use_high_low_barriers=bool(use_high_low_barriers),
            ambiguous_barrier_policy=ambiguous_barrier_policy,
        )
    labeled = feature_frame.copy()
    labeled['target'] = pd.Series(targets, index=labeled.index)
    clean = clean_feature_frame(labeled, require_target=True)
    clean.attrs['feature_lag'] = int(feature_lag or 0)
    clean.attrs['label_config'] = {
        'lookahead': int(lookahead),
        'atr_multiplier': float(atr_multiplier),
        'feature_lag': int(feature_lag or 0),
        'min_profit_bps': float(min_profit_bps or 0.0),
        'use_high_low_barriers': bool(use_high_low_barriers),
        'ambiguous_barrier_policy': str(ambiguous_barrier_policy or 'hold'),
    }
    return clean
