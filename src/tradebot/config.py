from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

import yaml

from .enums import AutoSignalMode, ExecutionMode, MarketType


@dataclass(slots=True)
class Settings:
    market_type: str = MarketType.SPOT_DEMO.value
    api_key: str = ""
    api_secret: str = ""
    base_url: str = "https://demo-api.binance.com"
    symbol: str = "ETHUSDT"
    kline_interval: str = "1m"
    stale_ms: int = 15_000
    enable_verbose_logs: bool = True

    ema_fast_period: int = 20
    ema_slow_period: int = 50
    rsi_period: int = 14
    volume_sma_period: int = 20
    min_meaningful_volume_ratio: float = 0.5
    rsi_buy_threshold: float = 55.0
    rsi_sell_threshold: float = 45.0
    volume_multiplier: float = 1.0

    execution_mode: str = ExecutionMode.DRY_RUN.value
    live_trading_armed: bool = False
    live_real_double_confirm: bool = False
    auto_trade_on_signal: bool = False
    auto_trade_signal_mode: str = AutoSignalMode.NORMAL.value
    auto_trade_cooldown_sec: int = 5
    max_auto_entry_per_signal: int = 1

    order_notional_usd: float = 25.0
    order_timeout_sec: int = 20
    reconciliation_base_backoff_ms: int = 1_000
    reconciliation_max_backoff_ms: int = 15_000
    reconciliation_missing_warning_count: int = 2
    reconciliation_missing_critical_count: int = 3
    reconciliation_max_attempts_before_deferred: int = 8
    reconciliation_late_fill_grace_ms: int = 30_000
    min_notional_buffer_multiplier: float = 1.10
    sizing_mode: str = "fixed_quote"
    risk_percent_quote_balance: float = 2.5
    quote_balance_reserve_usd: float = 0.0
    max_quote_budget_usd: float = 0.0

    force_entry_price_mode: str = "passive"
    force_exit_price_mode: str = "aggressive"

    sl_mode: str = "atr"
    atr_period: int = 14
    atr_multiplier: float = 1.5
    fixed_stop_loss_pct: float = 1.0

    tp_mode: str = "rr"
    risk_reward_ratio: float = 2.0
    fixed_take_profit_pct: float = 2.0

    max_daily_loss_pct: float = 2.0
    max_consecutive_losses: int = 3
    safe_mode_cooldown_min: int = 60
    max_daily_trades: int = 0

    break_even_enabled: bool = True
    break_even_trigger_r: float = 1.0
    break_even_buffer_pct: float = 0.02
    trailing_stop_enabled: bool = True
    trailing_atr_multiplier: float = 1.0
    trailing_only_after_break_even: bool = True
    partial_take_profit_enabled: bool = True
    partial_take_profit_rr: float = 1.0
    partial_take_profit_close_pct: float = 50.0
    position_max_hold_sec: int = 0

    ai_provider_enabled: bool = True
    ai_provider_mode: str = "local_xgboost"
    ai_model_path: str = "models/xgboost_trade_model.json"
    ai_confidence_threshold: float = 0.60
    ai_service_url: str | None = None
    ai_buy_threshold: float = 0.64
    ai_sell_threshold: float = 0.57
    ai_hold_band_low: float = 0.45
    ai_hold_band_high: float = 0.55
    ai_indecision_margin: float = 0.08
    ai_threshold_profile: str = "runtime_settings"

    model_quality_enabled: bool = True
    model_quality_window_size: int = 200
    model_quality_min_samples: int = 30
    model_quality_hold_warning_pct: float = 80.0
    model_quality_hold_critical_pct: float = 90.0
    model_quality_avg_conf_warning: float = 0.50
    model_quality_avg_conf_critical: float = 0.42
    model_quality_low_margin_warning_pct: float = 35.0
    model_quality_low_margin_critical_pct: float = 55.0
    model_quality_stale_warning_days: int = 14
    model_quality_stale_critical_days: int = 30

    model_quality_gate_enabled: bool = True
    model_quality_gate_min_runtime_samples: int = 30
    model_quality_gate_block_runtime_warming_up: bool = True
    model_quality_gate_block_runtime_warning: bool = False
    model_quality_gate_min_clean_samples: int = 1000
    model_quality_gate_min_action_coverage: float = 0.03
    model_quality_gate_max_hold_rate: float = 0.97
    model_quality_gate_max_low_margin_reject_rate: float = 0.75
    model_quality_gate_min_calibrated_accuracy: float = 0.30
    model_quality_gate_block_reload_on_insufficient_evidence: bool = True
    model_quality_gate_min_target_action_rate: float = 0.03
    model_quality_gate_max_target_hold_rate: float = 0.97
    model_quality_gate_min_present_target_classes: int = 2
    model_quality_gate_block_synthetic_class_padding: bool = True

    performance_analytics_enabled: bool = True
    performance_analytics_window_size: int = 200
    performance_breakeven_epsilon: float = 1e-9

    data_dir: str = ".tradebot"
    database_path: str = ".tradebot/tradebot.db"

    # dashboard/api compatibility fields used by local desktop tooling
    api_host: str = "127.0.0.1"
    api_port: int = 8787

    # 4B.4.3.6.6.29A production hardening controls
    strict_config_validation: bool = True
    api_auth_enabled: bool = False
    api_auth_token: str = ""
    api_auth_header: str = "X-TradeBot-Auth"
    api_auth_env_var: str = "TRADEBOT_API_TOKEN"
    destructive_action_confirmation_required: bool = False
    destructive_action_confirmation_header: str = "X-TradeBot-Confirm"
    runtime_lock_enabled: bool = True
    runtime_lock_path: str = ".tradebot/runtime.lock"
    sqlite_wal_enabled: bool = True
    sqlite_busy_timeout_ms: int = 5000
    sqlite_schema_version: int = 2
    sqlite_backup_enabled: bool = True
    fee_slippage_baseline_bps: float = 24.0
    promotion_gate_isolation_enabled: bool = True

    # 4B.4.3.6.6.29D replay/backtest/walk-forward gate controls
    replay_gate_enabled: bool = True
    deterministic_replay_required: bool = True
    model_artifact_hash_required: bool = True
    walk_forward_oos_gate_required: bool = True
    last_known_good_model_registry_path: str = "models/last_known_good_model_registry.json"
    replay_gate_min_oos_samples: int = 30
    replay_gate_min_oos_win_rate_pct: float = 60.0
    replay_gate_min_oos_profit_factor: float = 1.5
    replay_gate_min_oos_mean_return_bps: float = 0.0
    replay_gate_min_oos_worst_return_bps: float = -500.0
    replay_gate_min_oos_worst_mae_bps: float = -500.0
    replay_gate_min_unique_oos_days: int = 3
    replay_gate_min_regime_count: int = 2
    # 4B.4.3.6.6.29C SQLite audit ledger upgrade

    # 4B.4.3.6.6.29B API/operator security hardening controls
    api_auth_token_ttl_sec: int = 900
    api_auth_token_issued_at_ms: int = 0
    api_auth_token_issued_at_env_var: str = "TRADEBOT_API_TOKEN_ISSUED_AT_MS"
    api_operator_id_header: str = "X-TradeBot-Operator"
    api_local_only_required: bool = True
    operator_audit_enabled: bool = True
    live_real_arm_ttl_sec: int = 900
    live_real_armed_at_ms: int = 0
    live_real_arm_expires_at_ms: int = 0
    live_real_arm_confirmation_header: str = "X-TradeBot-Live-Arm"
    live_real_start_confirmation: str = "CONFIRM_LIVE_REAL_START"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Settings":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise TypeError("Settings yaml must decode to a mapping")
        allowed = {field.name for field in fields(cls)}
        unknown_keys = sorted(str(key) for key in payload if key not in allowed)
        strict_value = payload.get("strict_config_validation", True)
        strict_config_validation = bool(strict_value)
        if unknown_keys and strict_config_validation:
            joined = ", ".join(unknown_keys)
            raise ValueError(f"Unknown Settings yaml key(s): {joined}")
        filtered = {key: value for key, value in payload.items() if key in allowed}
        return cls(**filtered)

    def to_dict(self, *, include_secrets: bool = False) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop('api_host', None)
        payload.pop('api_port', None)
        if not include_secrets:
            payload['api_auth_token'] = '[REDACTED]' if payload.get('api_auth_token') else ''
            payload['api_key'] = '[REDACTED]' if self.api_key else ''
            payload['api_secret'] = '[REDACTED]' if self.api_secret else ''
        return payload
