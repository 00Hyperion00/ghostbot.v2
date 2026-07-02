from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from .orchestrator import TradeBotOrchestrator
from .schemas import OPERATOR_COCKPIT_CONTRACT_VERSION


class CockpitBroadcaster:
    def __init__(self, orchestrator: TradeBotOrchestrator, *, interval_sec: float = 1.0) -> None:
        self.orchestrator = orchestrator
        self.interval_sec = max(float(interval_sec), 0.25)
        self.clients: set[WebSocket] = set()
        self._running = False

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.add(websocket)
        await websocket.send_json({"type": "hello", "contract_version": OPERATOR_COCKPIT_CONTRACT_VERSION})
        await websocket.send_json({"type": "snapshot", "payload": await self.orchestrator.snapshot()})

    def disconnect(self, websocket: WebSocket) -> None:
        self.clients.discard(websocket)

    async def keepalive(self, websocket: WebSocket) -> None:
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for client in list(self.clients):
            try:
                await client.send_json(message)
            except Exception:
                dead.append(client)
        for client in dead:
            self.disconnect(client)

    async def run(self) -> None:
        self._running = True
        while self._running:
            await self.broadcast({"type": "snapshot", "payload": await self.orchestrator.snapshot()})
            await asyncio.sleep(self.interval_sec)

    def stop(self) -> None:
        self._running = False
