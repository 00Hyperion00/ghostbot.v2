from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .enums import AutoSignalMode, ExecutionMode, MarketType

CONTRACT_VERSION = '4B.4.3.6.6.15'


@dataclass(slots=True)
class ConfigSafetyConfig:
    symbol: str
    kline_interval: str
    execution_mode: str
    market_type: str
    base_url: str
    api_key: str
    api_secret: str
    live_trading_armed: bool
    live_real_double_confirm: bool
    auto_trade_on_signal: bool
    auto_trade_signal_mode: str
    order_notional_usd: float
    sizing_mode: str
    risk_percent_quote_balance: float
    min_notional_buffer_multiplier: float
    max_daily_loss_pct: float
    max_consecutive_losses: int
    max_daily_trades: int
    ai_provider_enabled: bool
    ai_provider_mode: str
    ai_model_path: str
    ai_confidence_threshold: float
    ai_buy_threshold: float
    ai_sell_threshold: float
    ai_hold_band_low: float
    ai_hold_band_high: float
    ai_indecision_margin: float
    sl_mode: str
    tp_mode: str
    atr_period: int
    atr_multiplier: float
    fixed_stop_loss_pct: float
    fixed_take_profit_pct: float
    risk_reward_ratio: float
    break_even_trigger_r: float
    trailing_atr_multiplier: float
    partial_take_profit_close_pct: float
    position_max_hold_sec: int


def config_from_settings(settings: Any) -> ConfigSafetyConfig:
    return ConfigSafetyConfig(
        symbol=str(getattr(settings, 'symbol', 'ETHUSDT') or ''),
        kline_interval=str(getattr(settings, 'kline_interval', '1m') or ''),
        execution_mode=str(getattr(settings, 'execution_mode', ExecutionMode.DRY_RUN.value) or ''),
        market_type=str(getattr(settings, 'market_type', MarketType.SPOT_DEMO.value) or ''),
        base_url=str(getattr(settings, 'base_url', '') or ''),
        api_key=str(getattr(settings, 'api_key', '') or ''),
        api_secret=str(getattr(settings, 'api_secret', '') or ''),
        live_trading_armed=bool(getattr(settings, 'live_trading_armed', False)),
        live_real_double_confirm=bool(getattr(settings, 'live_real_double_confirm', False)),
        auto_trade_on_signal=bool(getattr(settings, 'auto_trade_on_signal', False)),
        auto_trade_signal_mode=str(getattr(settings, 'auto_trade_signal_mode', AutoSignalMode.NORMAL.value) or ''),
        order_notional_usd=float(getattr(settings, 'order_notional_usd', 0.0) or 0.0),
        sizing_mode=str(getattr(settings, 'sizing_mode', 'fixed_quote') or ''),
        risk_percent_quote_balance=float(getattr(settings, 'risk_percent_quote_balance', 0.0) or 0.0),
        min_notional_buffer_multiplier=float(getattr(settings, 'min_notional_buffer_multiplier', 0.0) or 0.0),
        max_daily_loss_pct=float(getattr(settings, 'max_daily_loss_pct', 0.0) or 0.0),
        max_consecutive_losses=int(getattr(settings, 'max_consecutive_losses', 0) or 0),
        max_daily_trades=int(getattr(settings, 'max_daily_trades', 0) or 0),
        ai_provider_enabled=bool(getattr(settings, 'ai_provider_enabled', False)),
        ai_provider_mode=str(getattr(settings, 'ai_provider_mode', 'disabled') or ''),
        ai_model_path=str(getattr(settings, 'ai_model_path', '') or ''),
        ai_confidence_threshold=float(getattr(settings, 'ai_confidence_threshold', 0.0) or 0.0),
        ai_buy_threshold=float(getattr(settings, 'ai_buy_threshold', 0.0) or 0.0),
        ai_sell_threshold=float(getattr(settings, 'ai_sell_threshold', 0.0) or 0.0),
        ai_hold_band_low=float(getattr(settings, 'ai_hold_band_low', 0.0) or 0.0),
        ai_hold_band_high=float(getattr(settings, 'ai_hold_band_high', 0.0) or 0.0),
        ai_indecision_margin=float(getattr(settings, 'ai_indecision_margin', 0.0) or 0.0),
        sl_mode=str(getattr(settings, 'sl_mode', 'atr') or ''),
        tp_mode=str(getattr(settings, 'tp_mode', 'rr') or ''),
        atr_period=int(getattr(settings, 'atr_period', 0) or 0),
        atr_multiplier=float(getattr(settings, 'atr_multiplier', 0.0) or 0.0),
        fixed_stop_loss_pct=float(getattr(settings, 'fixed_stop_loss_pct', 0.0) or 0.0),
        fixed_take_profit_pct=float(getattr(settings, 'fixed_take_profit_pct', 0.0) or 0.0),
        risk_reward_ratio=float(getattr(settings, 'risk_reward_ratio', 0.0) or 0.0),
        break_even_trigger_r=float(getattr(settings, 'break_even_trigger_r', 0.0) or 0.0),
        trailing_atr_multiplier=float(getattr(settings, 'trailing_atr_multiplier', 0.0) or 0.0),
        partial_take_profit_close_pct=float(getattr(settings, 'partial_take_profit_close_pct', 0.0) or 0.0),
        position_max_hold_sec=int(getattr(settings, 'position_max_hold_sec', 0) or 0),
    )


def _redact_secret(value: str) -> dict[str, Any]:
    value = str(value or '')
    if not value:
        return {'present': False, 'redacted': '', 'length': 0}
    if len(value) <= 8:
        redacted = '*' * len(value)
    else:
        redacted = f'{value[:4]}...{value[-4:]}'
    return {'present': True, 'redacted': redacted, 'length': len(value)}


def _model_exists(path_text: str, *, base_dir: Path | None = None) -> bool | None:
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    try:
        return path.exists()
    except OSError:
        return False


def build_config_safety_snapshot(settings: Any, *, base_dir: Path | None = None) -> dict[str, Any]:
    cfg = config_from_settings(settings)
    reason_codes: list[str] = []
    warnings: list[str] = []
    criticals: list[str] = []

    allowed_execution = {item.value for item in ExecutionMode}
    allowed_market = {item.value for item in MarketType}
    allowed_signal_modes = {item.value for item in AutoSignalMode}
    allowed_intervals = {'1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d'}

    if not cfg.symbol or len(cfg.symbol) < 5:
        criticals.append('Symbol boş veya şüpheli')
        reason_codes.append('SYMBOL_INVALID')
    if cfg.execution_mode not in allowed_execution:
        criticals.append('Execution mode tanınmıyor')
        reason_codes.append('EXECUTION_MODE_INVALID')
    if cfg.market_type not in allowed_market:
        criticals.append('Market type tanınmıyor')
        reason_codes.append('MARKET_TYPE_INVALID')
    if cfg.kline_interval not in allowed_intervals:
        warnings.append('Kline interval standart listede değil')
        reason_codes.append('INTERVAL_NONSTANDARD')
    if cfg.auto_trade_signal_mode not in allowed_signal_modes:
        warnings.append('Auto signal mode tanınmıyor')
        reason_codes.append('AUTO_SIGNAL_MODE_INVALID')

    api_key = _redact_secret(cfg.api_key)
    api_secret = _redact_secret(cfg.api_secret)
    is_live_mode = cfg.execution_mode in {ExecutionMode.LIVE_DEMO.value, ExecutionMode.LIVE_REAL.value}
    is_real = cfg.execution_mode == ExecutionMode.LIVE_REAL.value or cfg.market_type == MarketType.SPOT_MAINNET.value
    is_demo_or_test = cfg.market_type in {MarketType.SPOT_DEMO.value, MarketType.SPOT_TESTNET.value}
    base_url_lower = cfg.base_url.lower()

    if is_live_mode and (not api_key['present'] or not api_secret['present']):
        criticals.append('Live/demo execution için API key/secret eksik')
        reason_codes.append('API_CREDENTIALS_MISSING')
    if is_real and not cfg.live_trading_armed:
        criticals.append('Live-real profil live_trading_armed olmadan seçilmiş')
        reason_codes.append('LIVE_REAL_NOT_ARMED')
    if is_real and not cfg.live_real_double_confirm:
        criticals.append('Live-real profil double confirm olmadan seçilmiş')
        reason_codes.append('LIVE_REAL_DOUBLE_CONFIRM_MISSING')
    if is_real and ('demo-api' in base_url_lower or 'testnet' in base_url_lower):
        criticals.append('Live-real profil demo/testnet endpoint ile çelişiyor')
        reason_codes.append('LIVE_REAL_ENDPOINT_MISMATCH')
    if is_demo_or_test and ('api.binance.com' in base_url_lower and 'demo-api' not in base_url_lower and 'testnet' not in base_url_lower):
        warnings.append('Demo/test profile mainnet benzeri endpoint kullanıyor')
        reason_codes.append('DEMO_PROFILE_MAINNET_ENDPOINT')

    if cfg.order_notional_usd <= 0:
        criticals.append('order_notional_usd pozitif değil')
        reason_codes.append('ORDER_NOTIONAL_INVALID')
    if cfg.sizing_mode == 'risk_percent' and not (0 < cfg.risk_percent_quote_balance <= 100):
        criticals.append('risk_percent_quote_balance 0-100 aralığında değil')
        reason_codes.append('RISK_PERCENT_INVALID')
    if cfg.min_notional_buffer_multiplier < 1.0:
        warnings.append('min_notional_buffer_multiplier 1.0 altında')
        reason_codes.append('MIN_NOTIONAL_BUFFER_LOW')
    if cfg.max_daily_loss_pct <= 0:
        warnings.append('max_daily_loss_pct pozitif değil')
        reason_codes.append('MAX_DAILY_LOSS_DISABLED_OR_INVALID')
    if cfg.max_consecutive_losses <= 0:
        warnings.append('max_consecutive_losses pozitif değil')
        reason_codes.append('MAX_CONSECUTIVE_LOSSES_DISABLED_OR_INVALID')
    if cfg.partial_take_profit_close_pct < 0 or cfg.partial_take_profit_close_pct > 100:
        warnings.append('partial_take_profit_close_pct 0-100 aralığında değil')
        reason_codes.append('PARTIAL_TP_CLOSE_PCT_INVALID')
    if cfg.position_max_hold_sec < 0:
        warnings.append('position_max_hold_sec negatif')
        reason_codes.append('POSITION_MAX_HOLD_INVALID')

    if cfg.sl_mode == 'atr' and (cfg.atr_period <= 0 or cfg.atr_multiplier <= 0):
        warnings.append('ATR stop konfigürasyonu geçersiz')
        reason_codes.append('ATR_STOP_CONFIG_INVALID')
    if cfg.sl_mode == 'fixed_pct' and cfg.fixed_stop_loss_pct <= 0:
        warnings.append('Fixed stop-loss yüzdesi geçersiz')
        reason_codes.append('FIXED_SL_CONFIG_INVALID')
    if cfg.tp_mode == 'rr' and cfg.risk_reward_ratio <= 0:
        warnings.append('Risk/reward oranı geçersiz')
        reason_codes.append('RR_CONFIG_INVALID')
    if cfg.tp_mode == 'fixed_pct' and cfg.fixed_take_profit_pct <= 0:
        warnings.append('Fixed take-profit yüzdesi geçersiz')
        reason_codes.append('FIXED_TP_CONFIG_INVALID')
    if cfg.break_even_trigger_r < 0:
        warnings.append('break_even_trigger_r negatif')
        reason_codes.append('BREAK_EVEN_TRIGGER_INVALID')
    if cfg.trailing_atr_multiplier <= 0:
        warnings.append('trailing_atr_multiplier pozitif değil')
        reason_codes.append('TRAILING_ATR_MULTIPLIER_INVALID')

    model_exists = _model_exists(cfg.ai_model_path, base_dir=base_dir)
    if cfg.ai_provider_enabled and cfg.ai_provider_mode == 'local_xgboost':
        if not cfg.ai_model_path:
            warnings.append('AI enabled fakat model path boş')
            reason_codes.append('AI_MODEL_PATH_MISSING')
        elif model_exists is False:
            warnings.append('AI model path bulunamadı')
            reason_codes.append('AI_MODEL_PATH_NOT_FOUND')
        if not (0 <= cfg.ai_confidence_threshold <= 1):
            warnings.append('AI confidence threshold 0-1 aralığında değil')
            reason_codes.append('AI_CONFIDENCE_THRESHOLD_INVALID')
        if not (0 <= cfg.ai_sell_threshold <= 1 and 0 <= cfg.ai_buy_threshold <= 1):
            warnings.append('AI buy/sell threshold 0-1 aralığında değil')
            reason_codes.append('AI_BUY_SELL_THRESHOLD_INVALID')
        if cfg.ai_hold_band_low > cfg.ai_hold_band_high:
            warnings.append('AI hold band low/high ters')
            reason_codes.append('AI_HOLD_BAND_INVALID')
        if cfg.ai_indecision_margin < 0:
            warnings.append('AI indecision margin negatif')
            reason_codes.append('AI_INDECISION_MARGIN_INVALID')

    if is_real:
        profile_mode = 'live_real'
    elif cfg.execution_mode == ExecutionMode.LIVE_DEMO.value:
        profile_mode = 'live_demo'
    else:
        profile_mode = 'dry_run'

    severity = 'critical' if criticals else ('warning' if warnings else 'ok')
    safe_to_trade = not criticals and not (is_real and (not cfg.live_trading_armed or not cfg.live_real_double_confirm))
    safe_to_auto_trade = safe_to_trade and (not is_real or cfg.auto_trade_on_signal)

    return {
        'contract_version': CONTRACT_VERSION,
        'profile_mode': profile_mode,
        'severity': severity,
        'safe_to_trade': bool(safe_to_trade),
        'safe_to_auto_trade': bool(safe_to_auto_trade),
        'reason_codes': reason_codes,
        'warnings': warnings,
        'critical_warnings': criticals,
        'symbol': cfg.symbol,
        'kline_interval': cfg.kline_interval,
        'execution_mode': cfg.execution_mode,
        'market_type': cfg.market_type,
        'base_url': cfg.base_url,
        'base_url_redacted': cfg.base_url,
        'api_key': api_key,
        'api_secret': {'present': api_secret['present'], 'redacted': '***' if api_secret['present'] else '', 'length': api_secret['length']},
        'live_trading_armed': cfg.live_trading_armed,
        'live_real_double_confirm': cfg.live_real_double_confirm,
        'auto_trade_on_signal': cfg.auto_trade_on_signal,
        'auto_trade_signal_mode': cfg.auto_trade_signal_mode,
        'order_notional_usd': cfg.order_notional_usd,
        'sizing_mode': cfg.sizing_mode,
        'risk_percent_quote_balance': cfg.risk_percent_quote_balance,
        'risk_controls': {
            'max_daily_loss_pct': cfg.max_daily_loss_pct,
            'max_consecutive_losses': cfg.max_consecutive_losses,
            'max_daily_trades': cfg.max_daily_trades,
            'position_max_hold_sec': cfg.position_max_hold_sec,
        },
        'ai': {
            'enabled': cfg.ai_provider_enabled,
            'mode': cfg.ai_provider_mode,
            'model_path': cfg.ai_model_path,
            'model_path_exists': model_exists,
            'confidence_threshold': cfg.ai_confidence_threshold,
            'buy_threshold': cfg.ai_buy_threshold,
            'sell_threshold': cfg.ai_sell_threshold,
            'hold_band_low': cfg.ai_hold_band_low,
            'hold_band_high': cfg.ai_hold_band_high,
        },
    }
