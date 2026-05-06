from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from tradebot.engine import TradeBotEngine


class DummyLogger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def info(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.calls.append((code, message, data))

    def warn(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.calls.append((code, message, data))


@pytest.mark.asyncio
async def test_engine_start_is_idempotent():
    engine = object.__new__(TradeBotEngine)
    engine.runtime = SimpleNamespace(state='STOPPED', ws_status='DISCONNECTED', pending=None)
    engine.logger = DummyLogger()
    engine._running = False
    engine._market_task = None
    engine._reconcile_task = None
    engine._save_runtime = lambda: None

    bootstrap_calls = 0

    async def fake_bootstrap() -> None:
        nonlocal bootstrap_calls
        bootstrap_calls += 1

    async def fake_market_loop() -> None:
        await asyncio.sleep(3600)

    async def fake_reconcile_loop() -> None:
        await asyncio.sleep(3600)

    engine.bootstrap = fake_bootstrap
    engine._market_loop = fake_market_loop
    engine._reconcile_loop = fake_reconcile_loop

    started_first = await TradeBotEngine.start(engine)
    started_second = await TradeBotEngine.start(engine)

    assert started_first is True
    assert started_second is False
    assert bootstrap_calls == 1

    await TradeBotEngine.stop(engine)


def test_task_alive_helper_handles_none_and_done_task():
    engine = object.__new__(TradeBotEngine)
    assert TradeBotEngine._task_alive(engine, None) is False

    async def noop() -> None:
        return None

    async def run() -> None:
        task = asyncio.create_task(noop())
        await task
        assert TradeBotEngine._task_alive(engine, task) is False

    asyncio.run(run())
