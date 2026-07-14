from __future__ import annotations

import asyncio
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace


def test_62f_h6_config_and_30o_contracts(tmp_path: Path) -> None:
    from tradebot.config_safety import build_config_safety_snapshot
    from tradebot.paper_sandbox_execution_reconciliation_gate import (
        READY_DECISION,
        build_paper_sandbox_execution_reconciliation_snapshot,
    )

    settings = SimpleNamespace(
        execution_mode="live_real",
        market_type="spot_mainnet",
        base_url="https://api.binance.com",
        api_key="ABCD1234SECRET",
        api_secret="VERYSECRET",
        live_trading_armed=False,
        live_real_double_confirm=False,
        ai_provider_enabled=False,
    )
    safety = build_config_safety_snapshot(settings)
    assert safety["safe_to_trade"] is False
    assert safety["api_key"]["redacted"].startswith("ABCD")
    assert safety["api_secret"]["redacted"] == "***"
    ready = build_paper_sandbox_execution_reconciliation_snapshot(
        settings,
        {"ok": True},
        {"submitted_to_exchange": False, "quote_balance_delta_usd": 0.0},
        sqlite_path=tmp_path / "ready.sqlite",
    )
    assert ready["decision"] == READY_DECISION
    mismatch = build_paper_sandbox_execution_reconciliation_snapshot(
        settings,
        {"ok": True},
        {"submitted_to_exchange": False, "quote_balance_delta_usd": -1.0},
        sqlite_path=tmp_path / "mismatch.sqlite",
    )
    assert mismatch["approved_for_mismatch_zero_proof"] is False


def test_62f_h6_operator_health_and_read_only_405(tmp_path: Path) -> None:
    from tradebot.operator_cockpit_v2_read_only import make_operator_cockpit_server

    server = make_operator_cockpit_server(tmp_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/operator-cockpit-v2/health", timeout=3) as response:
            assert json.loads(response.read().decode("utf-8"))["ok"] is True
        request = urllib.request.Request(
            f"http://{host}:{port}/api/operator-cockpit-v2/snapshot",
            data=b"{}",
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 405
            assert json.loads(error.read().decode("utf-8"))["error"] == "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"
        else:
            raise AssertionError("POST unexpectedly succeeded")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_62f_h6_engine_stop_sets_stopped() -> None:
    from tradebot.engine import TradeBotEngine

    async def scenario() -> None:
        engine = object.__new__(TradeBotEngine)
        engine.runtime = SimpleNamespace(state="FLAT", ws_status="CONNECTED")
        engine.logger = SimpleNamespace(warning=lambda *args, **kwargs: None)
        engine._running = True
        engine._market_task = None
        engine._reconcile_task = None
        engine._save_runtime = lambda: None
        assert await TradeBotEngine.stop(engine) is True
        assert engine.runtime.state == "STOPPED"

    asyncio.run(scenario())
