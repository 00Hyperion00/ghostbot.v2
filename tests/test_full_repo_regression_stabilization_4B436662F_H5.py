
from __future__ import annotations
import py_compile

def test_62f_h5_contract_markers_compile_and_lock_safety() -> None:
    for path in ("src/tradebot/api.py", "src/tradebot/config_safety.py", "src/tradebot/engine.py", "src/tradebot/ui/dashboard.py"):
        py_compile.compile(path, doraise=True)
    from tradebot.config_safety import build_config_safety_snapshot
    class S:
        execution_mode = "live_real"; market_type = "spot_mainnet"; base_url = "https://api.binance.com"; api_key = "key"; api_secret = "secret"; live_trading_armed = False; live_real_double_confirm = False; ai_provider_enabled = False
    snapshot = build_config_safety_snapshot(S())
    assert snapshot["safe_to_trade"] is False
    assert "LIVE_REAL_DOUBLE_CONFIRM_MISSING" in snapshot["reason_codes"]
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["exchange_submit_performed"] is False
