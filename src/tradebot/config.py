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

    # 4B.4.3.6.6.29E production readiness consolidation gate controls
    production_readiness_consolidation_enabled: bool = True
    production_readiness_evidence_dir: str = "reports/production_hardening"
    production_readiness_require_29a: bool = True
    production_readiness_require_29b: bool = True
    production_readiness_require_29c: bool = True
    production_readiness_require_29d: bool = True
    paper_candidate_preflight_enabled: bool = True

    # 4B.4.3.6.6.30A-H1 paper candidate preflight missing fields repair
    paper_transition_operator_approval_required: bool = True
    paper_transition_operator_approved: bool = False
    paper_transition_confirmation_phrase: str = "CONFIRM_PAPER_TRANSITION_CANDIDATE"
    paper_transition_confirmation_token: str = ""
    paper_exchange_sandbox_required: bool = True
    paper_sandbox_allowed_market_types: str = "spot_demo,spot_testnet"
    paper_transition_capital_cap_usd: float = 100.0
    paper_order_notional_cap_usd: float = 25.0
    paper_max_daily_loss_usd: float = 5.0
    paper_max_daily_trades_cap: int = 5
    paper_kill_switch_required: bool = True
    paper_kill_switch_enabled: bool = True
    # 4B.4.3.6.6.30B paper transition operator approval gate controls
    paper_transition_operator_id: str = ""
    paper_transition_approval_issued_at_ms: int = 0
    paper_transition_approval_ttl_sec: int = 900
    paper_transition_runtime_envelope: str = "sandbox_only"
    paper_transition_dry_run_reconciliation_required: bool = True
    paper_transition_dry_run_reconciliation_probe_passed: bool = True
    paper_transition_dry_run_probe_order_actions_performed: bool = False
    paper_transition_max_open_orders: int = 1
    # 4B.4.3.6.6.30C paper transition candidate review controls
    paper_transition_candidate_review_enabled: bool = True
    paper_transition_operator_evidence_required: bool = True
    paper_transition_runtime_envelope_freeze_required: bool = True
    paper_transition_runtime_envelope_frozen: bool = False
    paper_transition_runtime_envelope_freeze_phrase: str = "FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE"
    paper_transition_runtime_envelope_freeze_token: str = ""
    paper_transition_final_risk_cap_verification_required: bool = True
    paper_transition_final_risk_cap_verified: bool = False
    paper_transition_still_no_order_enablement_required: bool = True

    # 4B.4.3.6.6.30D operator approval evidence capture controls
    paper_transition_approval_evidence_capture_enabled: bool = True
    paper_transition_approval_evidence_operator_id_required: bool = True
    paper_transition_approval_evidence_ttl_bound_required: bool = True
    paper_transition_approval_evidence_snapshot_required: bool = True
    paper_transition_approval_evidence_capture_report_required: bool = True
    paper_transition_approval_evidence_require_30b_ready: bool = True
    paper_transition_approval_evidence_require_30c_ready: bool = True
    paper_transition_approval_evidence_still_no_order_enablement_required: bool = True
    # 4B.4.3.6.6.30E paper transition review rerun controls
    paper_transition_review_rerun_enabled: bool = True
    paper_transition_review_rerun_consume_30d_ready_required: bool = True
    paper_transition_review_rerun_require_30c_ready: bool = True
    paper_transition_review_rerun_still_no_order_enablement_required: bool = True
    paper_transition_review_rerun_evidence_report_required: bool = True
    # 4B.4.3.6.6.30F paper sandbox dry-run transition plan controls
    paper_sandbox_dry_run_transition_plan_enabled: bool = True
    paper_sandbox_dry_run_transition_plan_consume_30e_ready_required: bool = True
    paper_sandbox_dry_run_order_path_simulation_required: bool = True
    paper_sandbox_dry_run_operator_go_no_go_required: bool = True
    paper_sandbox_dry_run_still_no_order_enablement_required: bool = True

    # 4B.4.3.6.6.30G paper sandbox dry-run execution candidate gate controls
    paper_sandbox_dry_run_execution_candidate_gate_enabled: bool = True
    paper_sandbox_dry_run_execution_candidate_consume_30f_plan_required: bool = True
    paper_sandbox_dry_run_single_simulated_intent_required: bool = True
    paper_sandbox_dry_run_no_exchange_submit_required: bool = True
    paper_sandbox_dry_run_paper_candidate_still_blocked_required: bool = True
    # 4B.4.3.6.6.30H paper sandbox dry-run execution readiness lock controls
    paper_sandbox_dry_run_execution_readiness_lock_enabled: bool = True
    paper_sandbox_dry_run_execution_readiness_lock_consume_30g_required: bool = True
    paper_sandbox_dry_run_operator_explicit_lock_required: bool = True
    paper_sandbox_dry_run_operator_lock_operator_id: str = ""
    paper_sandbox_dry_run_operator_lock_phrase: str = "LOCK_PAPER_SANDBOX_DRY_RUN_READINESS"
    paper_sandbox_dry_run_operator_lock_token: str = ""
    paper_sandbox_dry_run_operator_lock_issued: bool = False
    paper_sandbox_dry_run_operator_lock_issued_at_ms: int = 0
    paper_sandbox_dry_run_operator_lock_ttl_sec: int = 900
    paper_sandbox_dry_run_exchange_submit_hard_block_audit_required: bool = True
    paper_sandbox_dry_run_execution_still_disabled_required: bool = True
    # 4B.4.3.6.6.30I paper sandbox dry-run internal execution harness controls
    paper_sandbox_dry_run_internal_execution_harness_enabled: bool = True
    paper_sandbox_dry_run_internal_execution_consume_30h_lock_required: bool = True
    paper_sandbox_dry_run_internal_only_harness_required: bool = True
    paper_sandbox_dry_run_simulated_fill_ledger_append_required: bool = True
    paper_sandbox_dry_run_simulated_fill_ledger_path: str = "reports/production_hardening/4B436630I_internal_simulated_fill_ledger.jsonl"
    paper_sandbox_dry_run_internal_no_exchange_submit_required: bool = True
    paper_sandbox_dry_run_internal_paper_candidate_still_blocked_required: bool = True

    # 4B.4.3.6.6.30J paper sandbox dry-run reconciliation + audit ledger proof controls
    paper_sandbox_dry_run_reconciliation_audit_proof_enabled: bool = True
    paper_sandbox_dry_run_reconciliation_consume_30i_ledger_required: bool = True
    paper_sandbox_dry_run_reconciliation_mismatch_zero_required: bool = True
    paper_sandbox_dry_run_reconciliation_sqlite_mirror_required: bool = True
    paper_sandbox_dry_run_reconciliation_no_exchange_submit_required: bool = True
    paper_sandbox_dry_run_reconciliation_paper_candidate_still_blocked_required: bool = True
    paper_sandbox_dry_run_reconciliation_tolerance: float = 1e-9
    paper_sandbox_dry_run_reconciliation_sqlite_path: str = "reports/production_hardening/4B436630J_reconciliation_audit_mirror.db"

    # 4B.4.3.6.6.30K paper sandbox operator final go/no-go controls
    paper_sandbox_operator_final_go_no_go_gate_enabled: bool = True
    paper_sandbox_operator_final_approval_required: bool = True
    paper_sandbox_operator_final_approval_operator_id: str = ""
    paper_sandbox_operator_final_approval_phrase: str = "APPROVE_PAPER_SANDBOX_GO_NO_GO"
    paper_sandbox_operator_final_approval_token: str = ""
    paper_sandbox_operator_final_approval_issued: bool = False
    paper_sandbox_operator_final_approval_issued_at_ms: int = 0
    paper_sandbox_operator_final_approval_ttl_sec: int = 900
    paper_sandbox_operator_kill_switch_check_required: bool = True
    paper_sandbox_operator_kill_switch_confirmed: bool = False
    paper_sandbox_operator_caps_check_required: bool = True
    paper_sandbox_operator_caps_confirmed: bool = False
    paper_sandbox_operator_paper_candidate_still_blocked_required: bool = True
    paper_sandbox_operator_no_live_real_required: bool = True

    # 4B.4.3.6.6.30L paper sandbox candidate unlock controls
    paper_sandbox_candidate_unlock_gate_enabled: bool = True
    paper_sandbox_candidate_unlock_consume_30k_required: bool = True
    paper_sandbox_candidate_unlock_explicit_unlock_required: bool = True
    paper_sandbox_candidate_unlock_operator_id: str = ""
    paper_sandbox_candidate_unlock_phrase: str = "UNLOCK_PAPER_SANDBOX_CANDIDATE"
    paper_sandbox_candidate_unlock_token: str = ""
    paper_sandbox_candidate_unlock_issued: bool = False
    paper_sandbox_candidate_unlock_issued_at_ms: int = 0
    paper_sandbox_candidate_unlock_ttl_sec: int = 900
    paper_sandbox_candidate_unlock_sandbox_only_preflight_required: bool = True
    paper_sandbox_candidate_unlock_no_exchange_submit_required: bool = True
    paper_sandbox_candidate_unlock_no_live_real_required: bool = True
    paper_sandbox_candidate_unlock_order_enablement_still_blocked_required: bool = True

    # 4B.4.3.6.6.30M paper sandbox execution preflight controls
    paper_sandbox_execution_preflight_enabled: bool = True
    paper_sandbox_execution_preflight_consume_30l_required: bool = True
    paper_sandbox_execution_preflight_authorization_required: bool = True
    paper_sandbox_execution_preflight_operator_id: str = ""
    paper_sandbox_execution_preflight_authorization_phrase: str = "AUTHORIZE_PAPER_SANDBOX_EXECUTION_PREFLIGHT"
    paper_sandbox_execution_preflight_authorization_token: str = ""
    paper_sandbox_execution_preflight_authorization_issued: bool = False
    paper_sandbox_execution_preflight_authorization_issued_at_ms: int = 0
    paper_sandbox_execution_preflight_authorization_ttl_sec: int = 900
    paper_sandbox_execution_preflight_order_envelope_required: bool = True
    paper_sandbox_execution_preflight_no_exchange_submit_required: bool = True
    paper_sandbox_execution_preflight_no_live_real_required: bool = True
    paper_sandbox_execution_preflight_order_envelope_path: str = "reports/production_hardening/4B436630M_order_envelope_preflight.json"

    # 4B.4.3.6.6.30N paper sandbox dry-run execution gate controls
    paper_sandbox_dry_run_execution_gate_enabled: bool = True
    paper_sandbox_dry_run_execution_consume_30m_required: bool = True
    paper_sandbox_dry_run_execution_authorization_required: bool = True
    paper_sandbox_dry_run_execution_operator_id: str = ""
    paper_sandbox_dry_run_execution_authorization_phrase: str = "AUTHORIZE_INTERNAL_PAPER_SANDBOX_DRY_RUN_EXECUTION"
    paper_sandbox_dry_run_execution_authorization_token: str = ""
    paper_sandbox_dry_run_execution_authorization_issued: bool = False
    paper_sandbox_dry_run_execution_authorization_issued_at_ms: int = 0
    paper_sandbox_dry_run_execution_authorization_ttl_sec: int = 900
    paper_sandbox_dry_run_execution_ledger_append_required: bool = True
    paper_sandbox_dry_run_execution_ledger_path: str = "reports/production_hardening/4B436630N_internal_paper_execution_ledger.jsonl"
    paper_sandbox_dry_run_execution_no_exchange_submit_required: bool = True
    paper_sandbox_dry_run_execution_no_live_real_required: bool = True
    paper_sandbox_dry_run_execution_simulated_fill_price_usd: float = 2500.0
    paper_sandbox_dry_run_execution_simulated_fee_bps: float = 10.0


    # 4B.4.3.6.6.30O paper sandbox execution reconciliation controls
    paper_sandbox_execution_reconciliation_gate_enabled: bool = True
    paper_sandbox_execution_reconciliation_consume_30n_required: bool = True
    paper_sandbox_execution_reconciliation_mismatch_zero_required: bool = True
    paper_sandbox_execution_reconciliation_sqlite_mirror_required: bool = True
    paper_sandbox_execution_reconciliation_sqlite_path: str = "reports/production_hardening/4B436630O_reconciliation_audit_mirror.sqlite"
    paper_sandbox_execution_reconciliation_no_exchange_submit_required: bool = True
    paper_sandbox_execution_reconciliation_no_live_real_required: bool = True
    paper_sandbox_execution_reconciliation_tolerance: float = 1e-09

    # 4B.4.3.6.6.30P paper sandbox submit-arm preflight controls
    paper_sandbox_submit_arm_preflight_enabled: bool = True
    paper_sandbox_submit_arm_consume_30o_required: bool = True
    paper_sandbox_submit_arm_api_mode: str = "testnet"
    paper_sandbox_submit_arm_base_url: str = "https://testnet.binance.vision"
    paper_sandbox_submit_arm_min_notional_usd: float = 5.0
    paper_sandbox_submit_arm_lot_size_step_qty: float = 0.0001
    paper_sandbox_submit_arm_min_qty: float = 0.0001
    paper_sandbox_submit_arm_simulated_price_usd: float = 2500.0
    paper_sandbox_submit_arm_api_mode_required: bool = True
    paper_sandbox_submit_arm_endpoint_required: bool = True
    paper_sandbox_submit_arm_min_notional_check_required: bool = True
    paper_sandbox_submit_arm_lot_size_check_required: bool = True
    paper_sandbox_submit_arm_risk_caps_check_required: bool = True
    paper_sandbox_submit_arm_kill_switch_check_required: bool = True
    paper_sandbox_submit_arm_no_exchange_submit_required: bool = True
    paper_sandbox_submit_arm_no_live_real_required: bool = True

    # 4B.4.3.6.6.30Q first paper sandbox canary submit gate controls
    first_paper_sandbox_canary_submit_gate_enabled: bool = True
    first_paper_sandbox_canary_consume_30p_required: bool = True
    first_paper_sandbox_canary_operator_approval_required: bool = True
    first_paper_sandbox_canary_operator_id: str = ""
    first_paper_sandbox_canary_operator_approval_phrase: str = "APPROVE_FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE"
    first_paper_sandbox_canary_operator_approval_token: str = ""
    first_paper_sandbox_canary_operator_approval_issued: bool = False
    first_paper_sandbox_canary_operator_approval_issued_at_ms: int = 0
    first_paper_sandbox_canary_operator_approval_ttl_sec: int = 900
    first_paper_sandbox_canary_order_intent_required: bool = True
    first_paper_sandbox_canary_submit_guard_required: bool = True
    first_paper_sandbox_canary_no_live_real_required: bool = True
    first_paper_sandbox_canary_quote_notional_usd: float = 10.0
    first_paper_sandbox_canary_notional_cap_usd: float = 10.0
    first_paper_sandbox_canary_min_notional_usd: float = 5.0
    first_paper_sandbox_canary_min_qty: float = 0.0001
    first_paper_sandbox_canary_step_size: float = 0.0001
    first_paper_sandbox_canary_estimated_price_usd: float = 2500.0
    first_paper_sandbox_canary_order_intent_path: str = "reports/production_hardening/4B436630Q_single_canary_order_intent.json"

    # 4B.4.3.6.6.30R paper sandbox canary reconciliation controls
    paper_sandbox_canary_reconciliation_enabled: bool = True
    paper_sandbox_canary_reconciliation_consume_30q_required: bool = True
    paper_sandbox_canary_reconciliation_order_intent_required: bool = True
    paper_sandbox_canary_reconciliation_submit_guard_required: bool = True
    paper_sandbox_canary_reconciliation_mismatch_zero_required: bool = True
    paper_sandbox_canary_reconciliation_no_live_real_required: bool = True
    paper_sandbox_canary_reconciliation_order_intent_path: str = "reports/production_hardening/4B436630Q_single_canary_order_intent.json"
    paper_sandbox_canary_reconciliation_expected_fill_count: int = 0
    paper_sandbox_canary_reconciliation_expected_account_delta_usd: float = 0.0
    paper_sandbox_canary_reconciliation_expected_position_delta_qty: float = 0.0
    paper_sandbox_canary_reconciliation_expected_fee_usd: float = 0.0

    # 4B.4.3.6.6.30S paper mode runtime guardrail controls
    paper_mode_runtime_guardrail_enabled: bool = True
    paper_mode_runtime_guardrail_consume_30r_required: bool = True
    paper_mode_runtime_guardrail_loop_required: bool = True
    paper_mode_runtime_guardrail_strict_caps_required: bool = True
    paper_mode_runtime_guardrail_kill_switch_required: bool = True
    paper_mode_runtime_guardrail_kill_switch_enabled: bool = True
    paper_mode_runtime_guardrail_no_exchange_submit_required: bool = True
    paper_mode_runtime_guardrail_no_live_real_required: bool = True
    paper_mode_runtime_guardrail_max_ticks: int = 3
    paper_mode_runtime_guardrail_tick_cap: int = 5
    paper_mode_runtime_guardrail_order_action_cap: int = 0
    paper_mode_runtime_guardrail_exchange_submit_cap: int = 0
    paper_mode_runtime_guardrail_network_submit_cap: int = 0
    paper_mode_runtime_guardrail_max_notional_usd: float = 0.0
    paper_mode_runtime_guardrail_runtime_seconds_cap: int = 30

    # 4B.4.3.6.6.30T paper soak / evidence window controls
    paper_soak_evidence_window_enabled: bool = True
    paper_soak_evidence_window_consume_30s_required: bool = True
    paper_soak_evidence_window_min_cycles_required: int = 3
    paper_soak_evidence_window_cycle_count: int = 5
    paper_soak_evidence_window_cycle_cap: int = 10
    paper_soak_evidence_window_cap_continuity_required: bool = True
    paper_soak_evidence_window_kill_switch_required: bool = True
    paper_soak_evidence_window_kill_switch_enabled: bool = True
    paper_soak_evidence_window_no_exchange_submit_required: bool = True
    paper_soak_evidence_window_no_live_real_required: bool = True
    paper_soak_evidence_window_order_action_cap: int = 0
    paper_soak_evidence_window_exchange_submit_cap: int = 0
    paper_soak_evidence_window_network_submit_cap: int = 0
    paper_soak_evidence_window_max_notional_usd: float = 0.0
    paper_soak_evidence_window_runtime_seconds_cap: int = 90

    # 4B.4.3.6.6.30U paper promotion review controls
    paper_promotion_review_enabled: bool = True
    paper_promotion_review_consume_30t_required: bool = True
    paper_promotion_review_risk_acceptance_required: bool = True
    paper_promotion_review_min_soak_cycles_required: int = 3
    paper_promotion_review_zero_action_counts_required: bool = True
    paper_promotion_review_no_exchange_submit_required: bool = True
    paper_promotion_review_no_live_real_required: bool = True
    paper_promotion_review_cap_continuity_required: bool = True
    paper_promotion_review_kill_switch_required: bool = True
    paper_promotion_review_max_total_notional_usd: float = 0.0
    paper_promotion_review_runtime_seconds_cap: int = 120
    live_real_hard_block_required: bool = True

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
