from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

PATCH_VERSION = "4B.4.3.6.6.33B"
PATCH_NAME = "Operator Cockpit Runtime Hardening"


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


COCKPIT_INIT = '''from __future__ import annotations

OPERATOR_COCKPIT_CONTRACT_VERSION = "4B.4.3.6.6.33A"
OPERATOR_COCKPIT_FOUNDATION_ENABLED = True
OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION = "4B.4.3.6.6.33B"
OPERATOR_COCKPIT_RUNTIME_HARDENING_ENABLED = True

__all__ = [
    "OPERATOR_COCKPIT_CONTRACT_VERSION",
    "OPERATOR_COCKPIT_FOUNDATION_ENABLED",
    "OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION",
    "OPERATOR_COCKPIT_RUNTIME_HARDENING_ENABLED",
]
'''

COCKPIT_SCHEMAS = '''from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

OPERATOR_COCKPIT_CONTRACT_VERSION = "4B.4.3.6.6.33A"
OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION = "4B.4.3.6.6.33B"
OPERATOR_COCKPIT_RUNTIME_HARDENING_ENABLED = True


def utc_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True, slots=True)
class CockpitActionResult:
    ok: bool
    action: str
    message: str
    data: dict[str, Any] | None = None
    contract_version: str = OPERATOR_COCKPIT_CONTRACT_VERSION
    runtime_hardening_version: str = OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION

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
    runtime_hardening_version: str = OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
'''

COCKPIT_ORCHESTRATOR = '''from __future__ import annotations

import asyncio
import os
from typing import Any

from ..config import Settings
from ..engine import TradeBotEngine
from ..persistence import SQLiteStore
from ..production_hardening import RuntimeLockHandle, acquire_runtime_lock, release_runtime_lock
from .schemas import (
    CockpitActionResult,
    CockpitSystemSnapshot,
    OPERATOR_COCKPIT_CONTRACT_VERSION,
    OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION,
    utc_ms,
)

_KNOWN_QUOTE_ASSETS = (
    "FDUSD",
    "USDT",
    "USDC",
    "BUSD",
    "TUSD",
    "TRY",
    "BTC",
    "ETH",
    "BNB",
)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            result = to_dict()
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}
    return {}


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _infer_assets(symbol: str, balances: dict[str, Any]) -> tuple[str, str]:
    normalized = str(symbol or "").strip().upper()
    for quote in sorted(_KNOWN_QUOTE_ASSETS, key=len, reverse=True):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)], quote
    for asset, raw in balances.items():
        asset_text = str(asset or "").strip().upper()
        if asset_text and asset_text not in _KNOWN_QUOTE_ASSETS:
            data = _as_dict(raw)
            if _float_value(data.get("free")) + _float_value(data.get("locked")) > 0:
                return asset_text, "UNKNOWN"
    return "UNKNOWN", "UNKNOWN"


def _find_recent_orphan_recovery(logs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in logs:
        code = str(item.get("code") or "").upper()
        data = _as_dict(item.get("data"))
        if code == "RECOVERY_RECONCILE_COMPLETED" and str(data.get("position_action") or "").upper() == "CLEARED_ORPHAN_LOCAL_POSITION":
            return item
    return None


def build_runtime_awareness_snapshot(status: dict[str, Any], logs: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive cockpit-only balance/position awareness without mutating engine state.

    33B intentionally does not block orders inside the engine. It exposes operator
    risk visibility when a tradable base balance exists while runtime position is
    not tracked, or when restart recovery cleared an orphan local position.
    """

    status = status if isinstance(status, dict) else {}
    balances = _as_dict(status.get("balances"))
    symbol = str(status.get("symbol") or status.get("config_safety_snapshot", {}).get("symbol") or "").upper()
    base_asset, quote_asset = _infer_assets(symbol, balances)
    base_balance = _as_dict(balances.get(base_asset, {})) if base_asset != "UNKNOWN" else {}
    base_free = _float_value(base_balance.get("free"))
    base_locked = _float_value(base_balance.get("locked"))
    base_dust = _float_value(base_balance.get("dust"))
    tradable_base = max(base_free - base_dust, 0.0)

    position = _as_dict(status.get("position_snapshot"))
    pending = _as_dict(status.get("pending_snapshot"))
    position_present = bool(position.get("present", False))
    pending_present = bool(pending.get("present", False))
    base_balance_present = tradable_base > 0
    not_tracked = base_balance_present and not position_present
    orphan_log = _find_recent_orphan_recovery(logs)
    orphan_detected = orphan_log is not None
    active_anomaly_code = str(status.get("active_anomaly_code") or "").strip()

    reason_codes: list[str] = []
    if not_tracked:
        reason_codes.append("BASE_BALANCE_PRESENT_POSITION_NOT_TRACKED")
    if orphan_detected:
        reason_codes.append("ORPHAN_LOCAL_POSITION_RECOVERY_DETECTED")
    if active_anomaly_code:
        reason_codes.append(f"ACTIVE_ANOMALY_{active_anomaly_code}")

    if active_anomaly_code or (orphan_detected and not_tracked):
        risk_badge = "RED"
        banner_title = "Runtime position mismatch requires operator review"
        banner_message = "Tradable base balance exists while runtime position is not tracked after orphan recovery. Do not authorize new entry until reconciliation is reviewed."
        recommended_action = "REVIEW_RECOVERY_LOGS_AND_BALANCE_SYNC_BEFORE_ENTRY"
    elif not_tracked or orphan_detected:
        risk_badge = "YELLOW"
        banner_title = "Base balance awareness warning"
        banner_message = "Base asset balance is present while runtime position may not be tracked. Confirm whether this is intentional inventory or leftover exposure."
        recommended_action = "BALANCE_SYNC_AND_OPERATOR_REVIEW"
    else:
        risk_badge = "GREEN"
        banner_title = "Runtime inventory tracking normal"
        banner_message = "No base-balance / position-tracking mismatch detected in the current cockpit snapshot."
        recommended_action = "NONE"

    return {
        "contract_version": OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION,
        "runtime_hardening_enabled": True,
        "risk_badge": risk_badge,
        "banner_title": banner_title,
        "banner_message": banner_message,
        "recommended_action": recommended_action,
        "reason_codes": reason_codes,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "base_free": base_free,
        "base_locked": base_locked,
        "base_dust": base_dust,
        "tradable_base": tradable_base,
        "base_balance_present": bool(base_balance_present),
        "position_present": bool(position_present),
        "pending_present": bool(pending_present),
        "base_balance_present_position_not_tracked": bool(not_tracked),
        "orphan_local_position_recovery_detected": bool(orphan_detected),
        "active_anomaly_code": active_anomaly_code or None,
        "auto_entry_risk_attention_required": risk_badge != "GREEN",
        "orphan_recovery_log_ts": orphan_log.get("ts") if orphan_log else None,
    }


class TradeBotOrchestrator:
    """Single-process control plane for TradeBot V2 Operator Cockpit."""

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
        runtime_awareness = build_runtime_awareness_snapshot(status, logs)
        return {
            "ok": self._startup_error is None,
            "contract_version": OPERATOR_COCKPIT_CONTRACT_VERSION,
            "runtime_hardening_version": OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION,
            "cockpit": {
                "name": "TradeBot V2 Operator Cockpit",
                "foundation_enabled": True,
                "runtime_hardening_enabled": True,
                "runtime_lock_present": self.runtime_lock_present,
                "startup_error": self._startup_error,
            },
            "runtime_awareness": runtime_awareness,
            "engine_running": bool(getattr(self.engine, "_running", False)),
            "status": status,
            "logs": logs,
            "system": self.system_snapshot(),
        }
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
from .schemas import OPERATOR_COCKPIT_CONTRACT_VERSION, OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION

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
                "runtime_hardening_version": OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION,
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

    app = FastAPI(title="TradeBot V2 Operator Cockpit", version=OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION, lifespan=lifespan)
    app.state.tradebot_cockpit_orchestrator = orchestrator
    app.state.tradebot_cockpit_broadcaster = broadcaster

    static_dir = _static_dir()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> FileResponse:
        return FileResponse(static_dir / "favicon.svg", media_type="image/svg+xml")

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
  <link rel="icon" href="/static/favicon.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <header class="topbar">
    <div>
      <h1>TradeBot V2 Operator Cockpit</h1>
      <p id="contract">Contract: -</p>
    </div>
    <div class="top-status">
      <div class="risk-badge risk-unknown" id="runtimeRiskBadge">RISK: -</div>
      <div class="status-pill" id="connection">DISCONNECTED</div>
    </div>
  </header>

  <main class="grid">
    <section class="card span-12 risk-banner" id="runtimeRiskBanner">
      <div>
        <h2 id="runtimeRiskTitle">Runtime inventory tracking</h2>
        <p id="runtimeRiskMessage">Waiting for cockpit snapshot...</p>
      </div>
      <div class="risk-meta">
        <span id="runtimeRiskReason">-</span>
        <strong id="runtimeRiskAction">-</strong>
      </div>
    </section>

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
      <h2>Runtime Awareness</h2>
      <div class="kv" id="awarenessBox"></div>
    </section>

    <section class="card span-6">
      <h2>System</h2>
      <div class="kv" id="systemBox"></div>
    </section>

    <section class="card span-6">
      <h2>Contract</h2>
      <div class="kv" id="contractBox"></div>
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
  gap: 14px;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
  background: rgba(10, 15, 30, 0.92);
  position: sticky;
  top: 0;
  z-index: 5;
}
.top-status { display: flex; align-items: center; gap: 10px; }
h1 { margin: 0; font-size: 22px; }
p { margin: 6px 0 0; }
.status-pill, .risk-badge {
  padding: 8px 14px;
  border-radius: 999px;
  font-weight: 800;
  letter-spacing: .02em;
}
.status-pill {
  background: #2b1b1b;
  color: var(--red);
  border: 1px solid rgba(239, 68, 68, .35);
}
.status-pill.online {
  background: #10261a;
  color: var(--green);
  border-color: rgba(34, 197, 94, .35);
}
.risk-green { color: var(--green); background: rgba(34, 197, 94, .10); border: 1px solid rgba(34, 197, 94, .45); }
.risk-yellow { color: var(--yellow); background: rgba(234, 179, 8, .12); border: 1px solid rgba(234, 179, 8, .45); }
.risk-red { color: var(--red); background: rgba(239, 68, 68, .14); border: 1px solid rgba(239, 68, 68, .55); }
.risk-unknown { color: var(--muted); background: rgba(148, 163, 184, .10); border: 1px solid rgba(148, 163, 184, .30); }
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
.risk-banner {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}
.risk-banner.green { border-color: rgba(34, 197, 94, .45); }
.risk-banner.yellow { border-color: rgba(234, 179, 8, .55); box-shadow: 0 0 0 1px rgba(234, 179, 8, .12), 0 10px 30px rgba(0,0,0,.25); }
.risk-banner.red { border-color: rgba(239, 68, 68, .65); box-shadow: 0 0 0 1px rgba(239, 68, 68, .20), 0 10px 30px rgba(0,0,0,.25); }
.risk-meta { text-align: right; color: var(--muted); max-width: 480px; }
.risk-meta span { display: block; font-size: 12px; margin-bottom: 6px; }
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.kpi-row div, .kv div {
  background: var(--panel-2);
  border: 1px solid var(--border);
  padding: 10px;
  border-radius: 12px;
}
.kpi-row span, .kv span { display: block; color: var(--muted); font-size: 12px; }
.kpi-row strong, .kv strong { display: block; font-size: 16px; margin-top: 4px; word-break: break-word; }
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
  .risk-banner { flex-direction: column; align-items: flex-start; }
  .risk-meta { text-align: left; }
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
function setRiskClass(el, badge, prefix) {
  if (!el) return;
  el.classList.remove(`${prefix}-green`, `${prefix}-yellow`, `${prefix}-red`, `${prefix}-unknown`, 'green', 'yellow', 'red');
  const normalized = String(badge || 'UNKNOWN').toLowerCase();
  if (['green', 'yellow', 'red'].includes(normalized)) {
    el.classList.add(`${prefix}-${normalized}`);
    if (prefix === 'risk-banner') el.classList.add(normalized);
  } else {
    el.classList.add(`${prefix}-unknown`);
  }
}
function renderRuntimeAwareness(awareness) {
  awareness = awareness || {};
  const badge = String(awareness.risk_badge || 'UNKNOWN').toUpperCase();
  const badgeEl = byId('runtimeRiskBadge');
  if (badgeEl) badgeEl.textContent = `RISK: ${badge}`;
  setRiskClass(badgeEl, badge, 'risk');
  const banner = byId('runtimeRiskBanner');
  setRiskClass(banner, badge, 'risk-banner');
  text('runtimeRiskTitle', awareness.banner_title || 'Runtime inventory tracking');
  text('runtimeRiskMessage', awareness.banner_message || '-');
  text('runtimeRiskReason', (awareness.reason_codes || []).join(', ') || '-');
  text('runtimeRiskAction', awareness.recommended_action || '-');
  kv('awarenessBox', {
    'Risk Badge': badge,
    'Base Asset': awareness.base_asset || '-',
    'Tradable Base': fmt(awareness.tradable_base),
    'Position Present': awareness.position_present,
    'Pending Present': awareness.pending_present,
    'Base Not Tracked': awareness.base_balance_present_position_not_tracked,
    'Orphan Recovery': awareness.orphan_local_position_recovery_detected,
    'Action Required': awareness.auto_entry_risk_attention_required
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
  const awareness = payload.runtime_awareness || {};

  text('contract', `Contract: ${payload.contract_version || '-'} / Hardening: ${payload.runtime_hardening_version || '-'}`);
  text('state', status.state || '-');
  text('ws', status.ws_status || '-');
  text('symbol', status.symbol || '-');
  text('heartbeat', `${system.heartbeat_age_ms ?? '-'} ms`);
  text('signal', status.last_signal || '-');
  text('position', position.present ? 'OPEN' : 'FLAT');
  text('qty', fmt(position.qty));
  text('pnl', fmt(position.unrealized_pnl ?? perf.realized_pnl));
  text('signalReason', status.signal_reason || '-');

  renderRuntimeAwareness(awareness);
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
  kv('contractBox', {
    'Foundation': payload.contract_version || '-',
    'Runtime Hardening': payload.runtime_hardening_version || '-',
    'Awareness Contract': awareness.contract_version || '-',
    'Favicon Noise Cleanup': 'ON',
    'PowerShell Compile Contract': 'tools/compile_operator_cockpit_4B436633B.py',
    'Order Path Mutation': 'NONE'
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

FAVICON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#0b1020"/>
  <path d="M12 42h40" stroke="#38bdf8" stroke-width="4" stroke-linecap="round"/>
  <path d="M16 38l10-12 8 8 14-18" fill="none" stroke="#22c55e" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="48" cy="16" r="4" fill="#eab308"/>
</svg>
'''

COMPILE_TOOL = '''from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33B"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    files = sorted((root / "src" / "tradebot" / "cockpit").glob("*.py"))
    files.append(root / "src" / "tradebot" / "cli.py")
    compiled: list[str] = []
    errors: list[dict[str, str]] = []
    for file_path in files:
        try:
            py_compile.compile(str(file_path), doraise=True)
            compiled.append(file_path.relative_to(root).as_posix())
        except py_compile.PyCompileError as exc:
            errors.append({"path": file_path.relative_to(root).as_posix(), "error": str(exc)})
    payload = {
        "patch_version": PATCH_VERSION,
        "ok": not errors,
        "compiled": compiled,
        "errors": errors,
        "powershell_glob_required": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
'''

DOC = '''# 4B.4.3.6.6.33B — Operator Cockpit Runtime Hardening

33B, 33A Operator Cockpit Foundation üzerine gelen runtime görünürlük hotfix'idir.

## Kapsam

- PowerShell glob kaynaklı compile komut hatasını kaldıran compile helper.
- `/favicon.ico` route + SVG favicon ile tarayıcı 404 gürültüsü temizliği.
- Base-balance awareness banner.
- Orphan local position recovery warning.
- Cockpit UI risk badge: GREEN / YELLOW / RED.

## Değişmeyenler

- Live-real açılmaz.
- Paper/live gate gevşetilmez.
- Exchange submit policy değişmez.
- Strategy threshold değişmez.
- Auto entry davranışı engine içinde değiştirilmez.

## Doğru Windows compile kontrolü

PowerShell `*.py` glob'unu `python -m py_compile` için güvenilir biçimde expand etmediği için şu komut kullanılmalıdır:

```powershell
python tools/compile_operator_cockpit_4B436633B.py
```

Alternatif:

```powershell
python -m compileall -q src\\tradebot\\cockpit src\\tradebot\\cli.py
```

## Risk badge anlamı

```text
GREEN  : Base balance / runtime position mismatch yok.
YELLOW : Base asset var ama position takip edilmiyor veya orphan recovery sinyali görüldü.
RED    : Orphan local position recovery sonrası tradable base balance position'sız duruyor veya aktif anomaly var.
```

## Operatör aksiyonu

YELLOW/RED görünürse yeni entry onayı vermeden önce:

1. Balance sync yap.
2. Recovery loglarını incele.
3. Cüzdandaki base asset'in bilinçli inventory mi yoksa artık exposure mı olduğunu doğrula.
4. Gerekirse manuel force-sell / reconcile kararı ver; typed confirmation olmadan danger-zone aksiyonları çalışmaz.
'''

TEST_FILE = '''from __future__ import annotations

from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33b_contract_literals_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "4B.4.3.6.6.33A" in text
    assert "4B.4.3.6.6.33B" in text
    assert "OPERATOR_COCKPIT_RUNTIME_HARDENING_ENABLED" in text


def test_33b_runtime_awareness_logic_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_runtime_awareness_snapshot" in text
    assert "BASE_BALANCE_PRESENT_POSITION_NOT_TRACKED" in text
    assert "ORPHAN_LOCAL_POSITION_RECOVERY_DETECTED" in text
    assert "auto_entry_risk_attention_required" in text


def test_33b_favicon_route_and_asset_present() -> None:
    root = _root()
    app_text = (root / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert '"/favicon.ico"' in app_text
    assert (root / "src/tradebot/cockpit/static/favicon.svg").exists()


def test_33b_ui_risk_badge_present() -> None:
    root = _root()
    html = (root / "src/tradebot/cockpit/static/index.html").read_text(encoding="utf-8")
    js = (root / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    css = (root / "src/tradebot/cockpit/static/styles.css").read_text(encoding="utf-8")
    assert "runtimeRiskBanner" in html
    assert "runtimeRiskBadge" in html
    assert "renderRuntimeAwareness" in js
    assert "risk-red" in css
    assert "risk-yellow" in css


def test_33b_powershell_compile_helper_present() -> None:
    tool = _root() / "tools/compile_operator_cockpit_4B436633B.py"
    text = tool.read_text(encoding="utf-8")
    assert "powershell_glob_required" in text
    assert "py_compile.compile" in text
'''


def apply() -> dict[str, object]:
    root = _repo_root()
    required = [
        root / "src/tradebot/cockpit/app.py",
        root / "src/tradebot/cockpit/orchestrator.py",
        root / "src/tradebot/cockpit/static/index.html",
    ]
    missing = [path.relative_to(root).as_posix() for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"33A cockpit foundation not found; missing: {', '.join(missing)}")

    files = {
        "src/tradebot/cockpit/__init__.py": COCKPIT_INIT,
        "src/tradebot/cockpit/schemas.py": COCKPIT_SCHEMAS,
        "src/tradebot/cockpit/orchestrator.py": COCKPIT_ORCHESTRATOR,
        "src/tradebot/cockpit/app.py": COCKPIT_APP,
        "src/tradebot/cockpit/static/index.html": INDEX_HTML,
        "src/tradebot/cockpit/static/styles.css": STYLES_CSS,
        "src/tradebot/cockpit/static/app.js": APP_JS,
        "src/tradebot/cockpit/static/favicon.svg": FAVICON_SVG,
        "tools/compile_operator_cockpit_4B436633B.py": COMPILE_TOOL,
        "docs/OPERATOR_COCKPIT_RUNTIME_HARDENING_4B436633B.md": DOC,
        "tests/test_operator_cockpit_4B436633B.py": TEST_FILE,
    }
    written: list[str] = []
    for rel, content in files.items():
        _write_text(root / rel, content)
        written.append(rel)

    readme_changed = _append_once(
        root / "README.md",
        "<!-- 4B436633B_OPERATOR_COCKPIT_RUNTIME_HARDENING -->",
        '''<!-- 4B436633B_OPERATOR_COCKPIT_RUNTIME_HARDENING -->
## 33B Operator Cockpit Runtime Hardening

33B ile cockpit'e base-balance awareness banner, orphan local position recovery warning, runtime risk badge ve favicon cleanup eklendi.

Windows compile kontrolü için glob kullanma. Doğru komut:

```powershell
python tools/compile_operator_cockpit_4B436633B.py
```
''',
    )

    return {
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written": written,
        "readme_changed": readme_changed,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
    }


if __name__ == "__main__":
    result = apply()
    print(json.dumps(result, ensure_ascii=False, indent=2))
