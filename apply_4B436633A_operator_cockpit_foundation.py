from __future__ import annotations

import json
import os
from pathlib import Path
from textwrap import dedent

PATCH_VERSION = "4B.4.3.6.6.33A"
PATCH_NAME = "TradeBot V2 Operator Cockpit Foundation"


def _repo_root() -> Path:
    return Path.cwd()


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8")


def _append_once(path: Path, marker: str, block: str) -> bool:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in text:
        return False
    with path.open("a", encoding="utf-8") as fh:
        if text and not text.endswith("\n"):
            fh.write("\n")
        fh.write("\n" + block.strip() + "\n")
    return True


def _patch_cli(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    if "cockpit_p = sub.add_parser('cockpit')" not in text:
        anchor = """    dashboard_p = sub.add_parser('dashboard')\n    dashboard_p.add_argument('--config', required=True)\n    dashboard_p.add_argument('--host', default='127.0.0.1')\n    dashboard_p.add_argument('--port', default=8787, type=int)\n"""
        insert = anchor + """\n    cockpit_p = sub.add_parser('cockpit')\n    cockpit_p.add_argument('--config', required=True)\n    cockpit_p.add_argument('--host', default='127.0.0.1')\n    cockpit_p.add_argument('--port', default=8787, type=int)\n    cockpit_p.add_argument('--auto-start-engine', action='store_true')\n    cockpit_p.add_argument('--no-open-browser', action='store_true')\n"""
        if anchor not in text:
            raise RuntimeError("cli.py dashboard parser anchor not found")
        text = text.replace(anchor, insert)

    if "if args.cmd == 'cockpit':" not in text:
        anchor = """    args = parser.parse_args()\n    if args.cmd == 'ai-service':\n"""
        insert = """    args = parser.parse_args()\n    if args.cmd == 'cockpit':\n        from .cockpit.app import run_cockpit\n\n        run_cockpit(\n            args.config,\n            host=args.host,\n            port=args.port,\n            auto_start_engine=bool(args.auto_start_engine),\n            open_browser=not bool(args.no_open_browser),\n        )\n        return\n    if args.cmd == 'ai-service':\n"""
        if anchor not in text:
            raise RuntimeError("cli.py args handler anchor not found")
        text = text.replace(anchor, insert)

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


COCKPIT_INIT = '''from __future__ import annotations

OPERATOR_COCKPIT_CONTRACT_VERSION = "4B.4.3.6.6.33A"
OPERATOR_COCKPIT_FOUNDATION_ENABLED = True

__all__ = [
    "OPERATOR_COCKPIT_CONTRACT_VERSION",
    "OPERATOR_COCKPIT_FOUNDATION_ENABLED",
]
'''

COCKPIT_SCHEMAS = '''from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

OPERATOR_COCKPIT_CONTRACT_VERSION = "4B.4.3.6.6.33A"


def utc_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True, slots=True)
class CockpitActionResult:
    ok: bool
    action: str
    message: str
    data: dict[str, Any] | None = None
    contract_version: str = OPERATOR_COCKPIT_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["data"] = self.data or {}
        return payload


@dataclass(frozen=True, slots=True)
class CockpitSystemSnapshot:
    pid: int
    uptime_sec: float
    heartbeat_age_ms: int
    process_started_at_ms: int
    now_ms: int
    contract_version: str = OPERATOR_COCKPIT_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
'''

COCKPIT_ORCHESTRATOR = '''from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from ..config import Settings
from ..engine import TradeBotEngine
from ..persistence import SQLiteStore
from ..production_hardening import RuntimeLockHandle, acquire_runtime_lock, release_runtime_lock
from .schemas import CockpitActionResult, CockpitSystemSnapshot, OPERATOR_COCKPIT_CONTRACT_VERSION, utc_ms


class TradeBotOrchestrator:
    """Single-process control plane for TradeBot V2 Operator Cockpit.

    The orchestrator intentionally keeps the trading engine in the same Python
    process as the FastAPI control-plane. This avoids split-brain runtime state
    and makes shutdown, audit logging, and runtime-lock handling deterministic.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = SQLiteStore(settings.database_path)
        self.engine = TradeBotEngine(settings, self.store)
        self.process_started_at_ms = utc_ms()
        self.last_heartbeat_ms = self.process_started_at_ms
        self._runtime_lock: RuntimeLockHandle | None = None
        self._startup_error: str | None = None
        self._shutdown_lock = asyncio.Lock()

    @property
    def startup_error(self) -> str | None:
        return self._startup_error

    @property
    def runtime_lock_present(self) -> bool:
        return self._runtime_lock is not None

    async def open(self) -> None:
        """Prepare cockpit resources without starting order-producing logic."""
        if not bool(getattr(self.settings, "runtime_lock_enabled", True)):
            return
        if self._runtime_lock is not None:
            return
        identity = f"cockpit:{getattr(self.settings, 'symbol', 'UNKNOWN')}:{os.getpid()}"
        try:
            self._runtime_lock = acquire_runtime_lock(
                getattr(self.settings, "runtime_lock_path", ".tradebot/runtime.lock"),
                identity=identity,
                stale_after_seconds=0,
            )
        except Exception as exc:  # fail-safe: cockpit starts degraded, engine start stays blocked
            self._startup_error = f"RUNTIME_LOCK_BLOCKED: {exc}"

    async def shutdown(self) -> None:
        async with self._shutdown_lock:
            try:
                await self.stop_engine(reason="COCKPIT_SHUTDOWN")
            finally:
                try:
                    await self.engine.close()
                finally:
                    if self._runtime_lock is not None:
                        release_runtime_lock(self._runtime_lock)
                        self._runtime_lock = None
                    close = getattr(self.store, "close", None)
                    if callable(close):
                        close()

    def _result(self, *, ok: bool, action: str, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return CockpitActionResult(ok=ok, action=action, message=message, data=data or {}).to_dict()

    async def start_engine(self) -> dict[str, Any]:
        if self._startup_error:
            return self._result(ok=False, action="engine.start", message="Cockpit runtime lock is not available", data={"startup_error": self._startup_error})
        try:
            started = await self.engine.start()
            return self._result(ok=True, action="engine.start", message="Engine start requested", data={"started": bool(started), "already_running": not bool(started)})
        except Exception as exc:
            return self._result(ok=False, action="engine.start", message="Engine start failed", data={"error": str(exc)})

    async def stop_engine(self, *, reason: str = "OPERATOR_STOP") -> dict[str, Any]:
        try:
            stopped = await self.engine.stop()
            return self._result(ok=True, action="engine.stop", message="Engine stop requested", data={"stopped": bool(stopped), "already_stopped": not bool(stopped), "reason": reason})
        except Exception as exc:
            return self._result(ok=False, action="engine.stop", message="Engine stop failed", data={"error": str(exc), "reason": reason})

    async def restart_engine(self) -> dict[str, Any]:
        stop_result = await self.stop_engine(reason="OPERATOR_RESTART")
        start_result = await self.start_engine()
        return self._result(ok=bool(stop_result.get("ok") and start_result.get("ok")), action="engine.restart", message="Engine restart requested", data={"stop": stop_result, "start": start_result})

    async def force_buy(self) -> dict[str, Any]:
        try:
            await self.engine.force_buy()
            return self._result(ok=True, action="trade.force_buy", message="Force BUY requested")
        except Exception as exc:
            return self._result(ok=False, action="trade.force_buy", message="Force BUY failed", data={"error": str(exc)})

    async def force_sell(self) -> dict[str, Any]:
        try:
            await self.engine.force_sell()
            return self._result(ok=True, action="trade.force_sell", message="Force SELL requested")
        except Exception as exc:
            return self._result(ok=False, action="trade.force_sell", message="Force SELL failed", data={"error": str(exc)})

    async def cancel_pending(self) -> dict[str, Any]:
        try:
            await self.engine.cancel_pending(reason="COCKPIT_OPERATOR_CANCEL")
            return self._result(ok=True, action="trade.cancel_pending", message="Pending cancel requested")
        except Exception as exc:
            return self._result(ok=False, action="trade.cancel_pending", message="Pending cancel failed", data={"error": str(exc)})

    async def risk_reset(self) -> dict[str, Any]:
        try:
            await self.engine.risk_reset()
            return self._result(ok=True, action="risk.reset", message="Risk counters reset")
        except Exception as exc:
            return self._result(ok=False, action="risk.reset", message="Risk reset failed", data={"error": str(exc)})

    async def toggle_safe_mode(self) -> dict[str, Any]:
        try:
            await self.engine.toggle_safe_mode()
            return self._result(ok=True, action="risk.safe_mode.toggle", message="Safe mode toggled")
        except Exception as exc:
            return self._result(ok=False, action="risk.safe_mode.toggle", message="Safe mode toggle failed", data={"error": str(exc)})

    def system_snapshot(self) -> dict[str, Any]:
        now = utc_ms()
        return CockpitSystemSnapshot(
            pid=os.getpid(),
            uptime_sec=max((now - self.process_started_at_ms) / 1000.0, 0.0),
            heartbeat_age_ms=max(now - self.last_heartbeat_ms, 0),
            process_started_at_ms=self.process_started_at_ms,
            now_ms=now,
        ).to_dict()

    async def snapshot(self, *, log_limit: int = 80) -> dict[str, Any]:
        self.last_heartbeat_ms = utc_ms()
        try:
            status = await self.engine.get_status()
        except Exception as exc:
            status = {"ok": False, "degraded": True, "error": str(exc), "state": "UNKNOWN"}
        try:
            logs = self.store.fetch_logs(limit=max(int(log_limit), 0), order="desc")
        except Exception as exc:
            logs = [{"ts": utc_ms(), "level": "ERROR", "code": "COCKPIT_LOG_FETCH_FAILED", "message": str(exc), "data": {}}]
        return {
            "ok": self._startup_error is None,
            "contract_version": OPERATOR_COCKPIT_CONTRACT_VERSION,
            "cockpit": {
                "name": "TradeBot V2 Operator Cockpit",
                "foundation_enabled": True,
                "runtime_lock_present": self.runtime_lock_present,
                "startup_error": self._startup_error,
            },
            "engine_running": bool(getattr(self.engine, "_running", False)),
            "status": status,
            "logs": logs,
            "system": self.system_snapshot(),
        }
'''

COCKPIT_BROADCASTER = '''from __future__ import annotations

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
'''

COCKPIT_APP = '''from __future__ import annotations

import asyncio
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Awaitable, Callable

import uvicorn
from fastapi import FastAPI, Header, HTTPException, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import Settings
from .broadcaster import CockpitBroadcaster
from .orchestrator import TradeBotOrchestrator
from .schemas import OPERATOR_COCKPIT_CONTRACT_VERSION

_CONFIRMATIONS = {
    "trade.force_buy": "CONFIRM_FORCE_BUY",
    "trade.force_sell": "CONFIRM_FORCE_SELL",
    "trade.cancel_pending": "CONFIRM_CANCEL_PENDING",
    "risk.reset": "CONFIRM_RISK_RESET",
    "risk.safe_mode.toggle": "CONFIRM_SAFE_MODE_TOGGLE",
}


def _static_dir() -> Path:
    return Path(__file__).resolve().parent / "static"


def _assert_confirm(action: str, supplied: str | None) -> None:
    expected = _CONFIRMATIONS.get(action)
    if expected and str(supplied or "").strip() != expected:
        raise HTTPException(
            status_code=412,
            detail={
                "ok": False,
                "contract_version": OPERATOR_COCKPIT_CONTRACT_VERSION,
                "reason_code": "COCKPIT_TYPED_CONFIRMATION_REQUIRED",
                "action": action,
                "confirmation_header": "X-TradeBot-Confirm",
                "expected_confirmation": expected,
            },
        )


def create_cockpit_app(settings: Settings, *, auto_start_engine: bool = False) -> FastAPI:
    orchestrator = TradeBotOrchestrator(settings)
    broadcaster = CockpitBroadcaster(orchestrator)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await orchestrator.open()
        task = asyncio.create_task(broadcaster.run())
        if auto_start_engine:
            await orchestrator.start_engine()
        try:
            yield
        finally:
            broadcaster.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await orchestrator.shutdown()

    app = FastAPI(title="TradeBot V2 Operator Cockpit", version=OPERATOR_COCKPIT_CONTRACT_VERSION, lifespan=lifespan)
    app.state.tradebot_cockpit_orchestrator = orchestrator
    app.state.tradebot_cockpit_broadcaster = broadcaster

    static_dir = _static_dir()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/cockpit/snapshot")
    async def cockpit_snapshot() -> dict[str, Any]:
        return await orchestrator.snapshot()

    @app.websocket("/ws/cockpit")
    async def cockpit_ws(websocket: WebSocket) -> None:
        await broadcaster.connect(websocket)
        await broadcaster.keepalive(websocket)

    @app.post("/api/engine/start")
    async def engine_start() -> dict[str, Any]:
        return await orchestrator.start_engine()

    @app.post("/api/engine/stop")
    async def engine_stop() -> dict[str, Any]:
        return await orchestrator.stop_engine()

    @app.post("/api/engine/restart")
    async def engine_restart() -> dict[str, Any]:
        return await orchestrator.restart_engine()

    async def _confirmed(action: str, header: str | None, fn: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
        _assert_confirm(action, header)
        return await fn()

    @app.post("/api/trade/force-buy")
    async def force_buy(x_tradebot_confirm: str | None = Header(default=None, alias="X-TradeBot-Confirm")) -> dict[str, Any]:
        return await _confirmed("trade.force_buy", x_tradebot_confirm, orchestrator.force_buy)

    @app.post("/api/trade/force-sell")
    async def force_sell(x_tradebot_confirm: str | None = Header(default=None, alias="X-TradeBot-Confirm")) -> dict[str, Any]:
        return await _confirmed("trade.force_sell", x_tradebot_confirm, orchestrator.force_sell)

    @app.post("/api/trade/cancel-pending")
    async def cancel_pending(x_tradebot_confirm: str | None = Header(default=None, alias="X-TradeBot-Confirm")) -> dict[str, Any]:
        return await _confirmed("trade.cancel_pending", x_tradebot_confirm, orchestrator.cancel_pending)

    @app.post("/api/risk/reset")
    async def risk_reset(x_tradebot_confirm: str | None = Header(default=None, alias="X-TradeBot-Confirm")) -> dict[str, Any]:
        return await _confirmed("risk.reset", x_tradebot_confirm, orchestrator.risk_reset)

    @app.post("/api/risk/safe-mode/toggle")
    async def safe_mode_toggle(x_tradebot_confirm: str | None = Header(default=None, alias="X-TradeBot-Confirm")) -> dict[str, Any]:
        return await _confirmed("risk.safe_mode.toggle", x_tradebot_confirm, orchestrator.toggle_safe_mode)

    return app


def run_cockpit(
    config_path: str,
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    auto_start_engine: bool = False,
    open_browser: bool = True,
) -> None:
    settings = Settings.from_yaml(config_path)
    app = create_cockpit_app(settings, auto_start_engine=auto_start_engine)
    url = f"http://{host}:{port}"
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, loop="asyncio", log_level="info", lifespan="on")
'''

INDEX_HTML = '''<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>TradeBot V2 Operator Cockpit</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <header class="topbar">
    <div>
      <h1>TradeBot V2 Operator Cockpit</h1>
      <p id="contract">Contract: -</p>
    </div>
    <div class="status-pill" id="connection">DISCONNECTED</div>
  </header>

  <main class="grid">
    <section class="card span-4">
      <h2>Runtime</h2>
      <div class="kpi-row">
        <div><span>State</span><strong id="state">-</strong></div>
        <div><span>WS</span><strong id="ws">-</strong></div>
        <div><span>Symbol</span><strong id="symbol">-</strong></div>
        <div><span>Heartbeat</span><strong id="heartbeat">-</strong></div>
      </div>
    </section>

    <section class="card span-4">
      <h2>Signal & Position</h2>
      <div class="kpi-row">
        <div><span>Signal</span><strong id="signal">-</strong></div>
        <div><span>Position</span><strong id="position">-</strong></div>
        <div><span>Qty</span><strong id="qty">-</strong></div>
        <div><span>PnL</span><strong id="pnl">-</strong></div>
      </div>
      <p class="muted" id="signalReason">-</p>
    </section>

    <section class="card span-4 danger-zone">
      <h2>Operator Controls</h2>
      <div class="button-grid">
        <button onclick="postAction('/api/engine/start')">Start Engine</button>
        <button onclick="postAction('/api/engine/stop')">Stop Engine</button>
        <button onclick="postAction('/api/engine/restart')">Restart</button>
        <button onclick="postDanger('/api/risk/safe-mode/toggle', 'CONFIRM_SAFE_MODE_TOGGLE')">Safe Mode Toggle</button>
        <button onclick="postDanger('/api/trade/force-buy', 'CONFIRM_FORCE_BUY')">Force BUY</button>
        <button onclick="postDanger('/api/trade/force-sell', 'CONFIRM_FORCE_SELL')">Force SELL</button>
        <button onclick="postDanger('/api/trade/cancel-pending', 'CONFIRM_CANCEL_PENDING')">Cancel Pending</button>
        <button onclick="postDanger('/api/risk/reset', 'CONFIRM_RISK_RESET')">Risk Reset</button>
      </div>
      <pre id="actionResult">Ready.</pre>
    </section>

    <section class="card span-6">
      <h2>Risk</h2>
      <div class="kv" id="riskBox"></div>
    </section>

    <section class="card span-6">
      <h2>System</h2>
      <div class="kv" id="systemBox"></div>
    </section>

    <section class="card span-12">
      <h2>Live Logs</h2>
      <div id="logs" class="logs"></div>
    </section>
  </main>

  <script src="/static/app.js"></script>
</body>
</html>
'''

STYLES_CSS = ''':root {
  color-scheme: dark;
  --bg: #0b1020;
  --panel: #111827;
  --panel-2: #162033;
  --text: #e5e7eb;
  --muted: #94a3b8;
  --green: #22c55e;
  --yellow: #eab308;
  --red: #ef4444;
  --blue: #38bdf8;
  --border: #253044;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: radial-gradient(circle at top left, #14213d, var(--bg) 42%);
  color: var(--text);
  font-family: Inter, Segoe UI, Arial, sans-serif;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
  background: rgba(10, 15, 30, 0.92);
  position: sticky;
  top: 0;
  z-index: 5;
}
h1 { margin: 0; font-size: 22px; }
p { margin: 6px 0 0; }
.status-pill {
  padding: 8px 14px;
  border-radius: 999px;
  font-weight: 700;
  background: #2b1b1b;
  color: var(--red);
  border: 1px solid rgba(239, 68, 68, .35);
}
.status-pill.online {
  background: #10261a;
  color: var(--green);
  border-color: rgba(34, 197, 94, .35);
}
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 16px;
  padding: 18px;
}
.card {
  background: linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(13, 19, 32, .98));
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,.25);
}
.card h2 { margin: 0 0 14px; font-size: 16px; color: #f8fafc; }
.span-4 { grid-column: span 4; }
.span-6 { grid-column: span 6; }
.span-12 { grid-column: span 12; }
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.kpi-row div, .kv div {
  background: var(--panel-2);
  border: 1px solid var(--border);
  padding: 10px;
  border-radius: 12px;
}
.kpi-row span, .kv span { display: block; color: var(--muted); font-size: 12px; }
.kpi-row strong { display: block; font-size: 18px; margin-top: 4px; }
.muted { color: var(--muted); font-size: 13px; }
.button-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
button {
  cursor: pointer;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 10px;
  color: var(--text);
  background: #1f2937;
  font-weight: 700;
}
button:hover { background: #263449; }
.danger-zone button:nth-child(n+5) { border-color: rgba(239, 68, 68, .5); }
pre {
  white-space: pre-wrap;
  background: #08111f;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px;
  min-height: 52px;
  max-height: 140px;
  overflow: auto;
}
.kv { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.logs {
  max-height: 360px;
  overflow: auto;
  font-family: Consolas, monospace;
  font-size: 12px;
}
.log-line {
  padding: 6px 8px;
  border-bottom: 1px solid rgba(148, 163, 184, .12);
}
.log-ERROR { color: var(--red); }
.log-WARN { color: var(--yellow); }
.log-INFO { color: var(--blue); }
@media (max-width: 1100px) {
  .span-4, .span-6 { grid-column: span 12; }
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
}
'''

APP_JS = '''let latestSnapshot = null;

function byId(id) { return document.getElementById(id); }
function text(id, value) { const el = byId(id); if (el) el.textContent = value ?? '-'; }
function fmt(value, digits = 4) {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'number') return Number.isFinite(value) ? value.toFixed(digits) : '-';
  return String(value);
}
function setConnection(online) {
  const el = byId('connection');
  el.textContent = online ? 'CONNECTED' : 'DISCONNECTED';
  el.classList.toggle('online', online);
}
function kv(containerId, data) {
  const box = byId(containerId);
  if (!box) return;
  box.innerHTML = '';
  Object.entries(data).forEach(([key, value]) => {
    const row = document.createElement('div');
    row.innerHTML = `<span>${key}</span><strong>${value ?? '-'}</strong>`;
    box.appendChild(row);
  });
}
function renderLogs(logs) {
  const box = byId('logs');
  if (!box) return;
  box.innerHTML = '';
  (logs || []).slice(0, 120).forEach(item => {
    const line = document.createElement('div');
    const level = String(item.level || 'INFO').toUpperCase();
    line.className = `log-line log-${level}`;
    const ts = item.ts ? new Date(item.ts).toLocaleString() : '-';
    line.textContent = `${ts} | ${level.padEnd(5)} | ${(item.code || '-').padEnd(28)} | ${item.message || '-'} | ${JSON.stringify(item.data || {})}`;
    box.appendChild(line);
  });
}
function renderSnapshot(payload) {
  latestSnapshot = payload;
  const status = payload.status || {};
  const position = status.position_snapshot || {};
  const perf = status.performance_snapshot || {};
  const risk = status.risk_snapshot || {};
  const system = payload.system || {};

  text('contract', `Contract: ${payload.contract_version || '-'}`);
  text('state', status.state || '-');
  text('ws', status.ws_status || '-');
  text('symbol', status.symbol || '-');
  text('heartbeat', `${system.heartbeat_age_ms ?? '-'} ms`);
  text('signal', status.last_signal || '-');
  text('position', position.present ? 'OPEN' : 'FLAT');
  text('qty', fmt(position.qty));
  text('pnl', fmt(position.unrealized_pnl ?? perf.realized_pnl));
  text('signalReason', status.signal_reason || '-');

  kv('riskBox', {
    'Safe Mode': status.safe_mode,
    'Kill Switch': status.kill_switch_active,
    'Daily PnL': fmt((status.session || {}).daily_realized_pnl),
    'Trades Today': (status.session || {}).daily_trade_count ?? '-',
    'Pending': (status.pending_snapshot || {}).present ?? '-',
    'Protective Exit': ((position.protective_exit || {}).protective_exit_ready ?? '-')
  });
  kv('systemBox', {
    'PID': system.pid,
    'Uptime Sec': fmt(system.uptime_sec, 1),
    'Engine Running': payload.engine_running,
    'Runtime Lock': (payload.cockpit || {}).runtime_lock_present,
    'Startup Error': (payload.cockpit || {}).startup_error || 'None',
    'Snapshot OK': payload.ok
  });
  renderLogs(payload.logs || []);
}
function connectWs() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws/cockpit`);
  ws.onopen = () => setConnection(true);
  ws.onclose = () => { setConnection(false); setTimeout(connectWs, 1500); };
  ws.onerror = () => setConnection(false);
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'snapshot') renderSnapshot(msg.payload);
  };
}
async function postAction(path, headers = {}) {
  const res = await fetch(path, { method: 'POST', headers });
  const payload = await res.json().catch(() => ({ ok: false, error: 'non-json response' }));
  byId('actionResult').textContent = JSON.stringify(payload, null, 2);
  return payload;
}
async function postDanger(path, expected) {
  const supplied = prompt(`Bu aksiyon için şu metni yaz: ${expected}`);
  if (supplied !== expected) {
    byId('actionResult').textContent = 'Confirmation mismatch. Action cancelled.';
    return;
  }
  return postAction(path, { 'X-TradeBot-Confirm': expected });
}
connectWs();
fetch('/api/cockpit/snapshot').then(r => r.json()).then(renderSnapshot).catch(() => setConnection(false));
'''

DOC = '''# 4B.4.3.6.6.33A — TradeBot V2 Operator Cockpit Foundation

Bu patch, eski `run_dashboard.bat`, `start_dashboard.bat`, `start_tradebot.bat` dağınıklığını azaltmak için tek bir web tabanlı Operator Cockpit foundation ekler.

## Yeni komut

```bash
tradebot cockpit --config config.local.yaml
```

Tarayıcı otomatik açılır. Otomatik açılmasını istemezsen:

```bash
tradebot cockpit --config config.local.yaml --no-open-browser
```

Engine cockpit açılır açılmaz başlasın istersen:

```bash
tradebot cockpit --config config.local.yaml --auto-start-engine
```

## Yeni bileşenler

- `src/tradebot/cockpit/orchestrator.py`
- `src/tradebot/cockpit/app.py`
- `src/tradebot/cockpit/broadcaster.py`
- `src/tradebot/cockpit/static/index.html`
- `src/tradebot/cockpit/static/app.js`
- `src/tradebot/cockpit/static/styles.css`
- `run_cockpit.bat`
- `run_cockpit.ps1`

## Güvenlik notu

Danger-zone aksiyonları typed confirmation ister:

- `CONFIRM_FORCE_BUY`
- `CONFIRM_FORCE_SELL`
- `CONFIRM_CANCEL_PENDING`
- `CONFIRM_RISK_RESET`
- `CONFIRM_SAFE_MODE_TOGGLE`

## Legacy BAT policy

Eski `.bat` dosyaları hemen silinmez. 33A itibarıyla canonical başlatıcı `tradebot cockpit` ve `run_cockpit.*` dosyalarıdır.
'''

RUN_BAT = r'''@echo off
setlocal
cd /d %~dp0
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m tradebot.cli cockpit --config config.local.yaml --host 127.0.0.1 --port 8787
) else (
  python -m tradebot.cli cockpit --config config.local.yaml --host 127.0.0.1 --port 8787
)
pause
'''

RUN_PS1 = r'''$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}
& $python -m tradebot.cli cockpit --config config.local.yaml --host 127.0.0.1 --port 8787
'''

TEST_FILE = '''from __future__ import annotations

from pathlib import Path


def test_operator_cockpit_static_assets_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "src/tradebot/cockpit/app.py").exists()
    assert (root / "src/tradebot/cockpit/orchestrator.py").exists()
    assert (root / "src/tradebot/cockpit/static/index.html").exists()
    assert (root / "src/tradebot/cockpit/static/app.js").exists()
    assert (root / "src/tradebot/cockpit/static/styles.css").exists()


def test_cockpit_contract_version_literal_present() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "4B.4.3.6.6.33A" in text


def test_cli_contains_cockpit_command() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/cli.py").read_text(encoding="utf-8")
    assert "sub.add_parser('cockpit')" in text
    assert "run_cockpit" in text
'''


def apply() -> dict[str, object]:
    root = _repo_root()
    files = {
        "src/tradebot/cockpit/__init__.py": COCKPIT_INIT,
        "src/tradebot/cockpit/schemas.py": COCKPIT_SCHEMAS,
        "src/tradebot/cockpit/orchestrator.py": COCKPIT_ORCHESTRATOR,
        "src/tradebot/cockpit/broadcaster.py": COCKPIT_BROADCASTER,
        "src/tradebot/cockpit/app.py": COCKPIT_APP,
        "src/tradebot/cockpit/static/index.html": INDEX_HTML,
        "src/tradebot/cockpit/static/styles.css": STYLES_CSS,
        "src/tradebot/cockpit/static/app.js": APP_JS,
        "docs/OPERATOR_COCKPIT_4B436633A.md": DOC,
        "run_cockpit.bat": RUN_BAT,
        "run_cockpit.ps1": RUN_PS1,
        "tests/test_operator_cockpit_4B436633A.py": TEST_FILE,
    }
    written: list[str] = []
    for rel, content in files.items():
        _write_text(root / rel, content)
        written.append(rel)

    cli_changed = _patch_cli(root / "src/tradebot/cli.py")
    readme_changed = _append_once(
        root / "README.md",
        "<!-- 4B436633A_OPERATOR_COCKPIT -->",
        '''<!-- 4B436633A_OPERATOR_COCKPIT -->
## TradeBot V2 Operator Cockpit

33A itibarıyla önerilen tek başlatma yolu:

```bash
tradebot cockpit --config config.local.yaml
```

Windows tek tık başlatma için `run_cockpit.bat` veya `run_cockpit.ps1` kullanılabilir. Eski `run_dashboard.bat`, `start_dashboard.bat`, `start_tradebot.bat` dosyaları legacy kabul edilir.
''',
    )

    return {
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written": written,
        "cli_changed": cli_changed,
        "readme_changed": readme_changed,
    }


if __name__ == "__main__":
    result = apply()
    print(json.dumps(result, ensure_ascii=False, indent=2))
