from __future__ import annotations

import asyncio
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Awaitable, Callable

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import Settings
from .broadcaster import CockpitBroadcaster
from .orchestrator import TradeBotOrchestrator
from .schemas import (
    OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION,
    OPERATOR_COCKPIT_CONTRACT_VERSION,
    OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION,
    OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
    OPERATOR_COCKPIT_UX_HEALTH_VERSION,
    OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
    OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
    OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
    OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_VERSION,
    OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION,
    OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
    OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
    OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION,
    OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
)
from .security import (
    CONFIRM_HEADER,
    DANGER_ACTION_CONFIRMATIONS,
    OPERATOR_ID_HEADER,
    authenticate_http_request,
    authenticate_websocket,
    build_security_snapshot,
    confirmation_required_exception,
    require_operator_identity,
    resolve_auth_header,
)


def _static_dir() -> Path:
    return Path(__file__).resolve().parent / "static"


def create_cockpit_app(settings: Settings, *, auto_start_engine: bool = False) -> FastAPI:
    orchestrator = TradeBotOrchestrator(settings)
    broadcaster = CockpitBroadcaster(orchestrator)
    auth_header = resolve_auth_header(settings)

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

    app = FastAPI(title="TradeBot V2 Operator Cockpit", version=OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION, lifespan=lifespan)
    app.state.tradebot_cockpit_orchestrator = orchestrator
    app.state.tradebot_cockpit_broadcaster = broadcaster

    static_dir = _static_dir()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    def _auth_context(request: Request) -> dict[str, Any]:
        return authenticate_http_request(
            settings,
            path=request.url.path,
            supplied_token=request.headers.get(auth_header),
            operator_id=request.headers.get(OPERATOR_ID_HEADER),
        )

    def _audit_operator_action(*, action: str, actor: str | None, confirmation: str | None, outcome: str, data: dict[str, Any] | None = None) -> None:
        try:
            orchestrator.store.append_operator_action(
                action=action,
                actor=actor or "UNKNOWN",
                confirmation=confirmation or "",
                outcome=outcome,
                data={
                    "security_gate_version": OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
                    **(data or {}),
                },
            )
        except Exception:
            # Audit failure must not create a second exception path inside HTTP handling.
            return

    async def _execute_operator_action(
        *,
        request: Request,
        action: str,
        fn: Callable[[], Awaitable[dict[str, Any]]],
        confirmation_expected: str | None = None,
    ) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action=action)
        confirmation = request.headers.get(CONFIRM_HEADER)
        if confirmation_expected and str(confirmation or "").strip() != confirmation_expected:
            _audit_operator_action(
                action=action,
                actor=operator_id,
                confirmation=confirmation or "",
                outcome="BLOCKED_CONFIRMATION_REQUIRED",
                data={"expected_confirmation": confirmation_expected},
            )
            raise confirmation_required_exception(action=action, expected=confirmation_expected)
        _audit_operator_action(
            action=action,
            actor=operator_id,
            confirmation=confirmation or "",
            outcome="REQUESTED",
            data={"path": request.url.path},
        )
        try:
            result = await fn()
        except Exception as exc:
            _audit_operator_action(
                action=action,
                actor=operator_id,
                confirmation=confirmation or "",
                outcome="FAILED_EXCEPTION",
                data={"error": str(exc)},
            )
            raise
        result_data = result.get("data") if isinstance(result.get("data"), dict) else {}
        reason_code = str(result_data.get("reason_code") or "")
        if reason_code == "RED_RISK_BADGE_ENTRY_GUARD":
            outcome = "BLOCKED_ENTRY_GUARD"
        elif reason_code == "ENTRY_BLOCK_UNTIL_RECONCILED":
            outcome = "BLOCKED_RECONCILIATION_REQUIRED"
        else:
            outcome = "ALLOWED_OK" if bool(result.get("ok", False)) else "ALLOWED_FAILED"
        _audit_operator_action(
            action=action,
            actor=operator_id,
            confirmation=confirmation or "",
            outcome=outcome,
            data={"result_ok": bool(result.get("ok", False)), "result_action": result.get("action")},
        )
        result.setdefault("operator_id", operator_id)
        result.setdefault("security_gate_version", OPERATOR_COCKPIT_SECURITY_GATE_VERSION)
        return result

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> FileResponse:
        return FileResponse(static_dir / "favicon.svg", media_type="image/svg+xml")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "tradebot-cockpit",
            "read_only_health_exception": True,
            "contract_version": OPERATOR_COCKPIT_CONTRACT_VERSION,
            "runtime_hardening_version": OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION,
            "security_gate_version": OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
            "ux_health_version": OPERATOR_COCKPIT_UX_HEALTH_VERSION,
            "action_audit_runtime_lock_version": OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION,
            "risk_reconciliation_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
            "reconciliation_execution_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
            "reconciliation_decision_apply_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
            "external_recovery_evidence_gate_version": OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
            "exchange_environment_source_gate_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
            "engine_status_balance_cache_reconciliation_version": OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION,
            "demo_entry_execution_control_version": OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
        }

    @app.get("/api/cockpit/health")
    async def cockpit_health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "tradebot-cockpit",
            "read_only_health_exception": True,
            "security_gate_version": OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
            "ux_health_version": OPERATOR_COCKPIT_UX_HEALTH_VERSION,
            "action_audit_runtime_lock_version": OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION,
            "risk_reconciliation_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
            "reconciliation_execution_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
            "reconciliation_decision_apply_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
            "external_recovery_evidence_gate_version": OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
            "exchange_environment_source_gate_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
            "engine_status_balance_cache_reconciliation_version": OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION,
            "demo_entry_execution_control_version": OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
            "security": build_security_snapshot(settings),
        }

    @app.get("/api/cockpit/security")
    async def cockpit_security(request: Request) -> dict[str, Any]:
        _auth_context(request)
        return {"ok": True, "security": build_security_snapshot(settings)}

    @app.get("/api/cockpit/snapshot")
    async def cockpit_snapshot(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        snapshot = await orchestrator.snapshot()
        snapshot["request_security"] = {
            "authenticated": bool(context.get("authenticated", False)),
            "operator_id": context.get("operator_id"),
            "auth_header": auth_header,
            "operator_header": OPERATOR_ID_HEADER,
        }
        return snapshot



    @app.get("/api/cockpit/engine-position-recovery-gate")
    async def cockpit_engine_position_recovery_gate(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        snapshot = await orchestrator.snapshot(log_limit=20)
        return {"ok": True, "engine_position_recovery_gate": snapshot.get("engine_position_recovery_gate"), "request_security": context}

    @app.post("/api/cockpit/engine-position-recovery/create-plan")
    async def engine_position_recovery_create_plan(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="engine_position_recovery.create_plan")
        return await _execute_operator_action(request=request, action="engine_position_recovery.create_plan", fn=lambda: orchestrator.create_engine_position_recovery_plan(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["engine_position_recovery.create_plan"])

    @app.post("/api/cockpit/engine-position-recovery/confirm-plan")
    async def engine_position_recovery_confirm_plan(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="engine_position_recovery.confirm_plan")
        return await _execute_operator_action(request=request, action="engine_position_recovery.confirm_plan", fn=lambda: orchestrator.confirm_engine_position_recovery_plan(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["engine_position_recovery.confirm_plan"])

    @app.post("/api/cockpit/engine-position-recovery/verify-completion")
    async def engine_position_recovery_verify_completion(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="engine_position_recovery.verify_completion")
        return await _execute_operator_action(request=request, action="engine_position_recovery.verify_completion", fn=lambda: orchestrator.verify_engine_position_recovery_completion(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["engine_position_recovery.verify_completion"])

    @app.post("/api/cockpit/engine-position-recovery/clear-plan")
    async def engine_position_recovery_clear_plan(request: Request) -> dict[str, Any]:
        _auth_context(request)
        return await _execute_operator_action(request=request, action="engine_position_recovery.clear_plan", fn=orchestrator.clear_engine_position_recovery_plan, confirmation_expected=DANGER_ACTION_CONFIRMATIONS["engine_position_recovery.clear_plan"])



    @app.get("/api/cockpit/recovery-plan-apply-verification-gate")
    async def cockpit_recovery_plan_apply_verification_gate(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        snapshot = await orchestrator.snapshot(log_limit=20)
        return {
            "ok": True,
            "recovery_plan_apply_verification_gate": snapshot.get("recovery_plan_apply_verification_gate"),
            "engine_position_recovery_gate": snapshot.get("engine_position_recovery_gate"),
            "request_security": context,
        }

    @app.post("/api/cockpit/recovery-plan-apply/create-from-reviewed-candidate")
    async def recovery_plan_apply_create_from_reviewed_candidate(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.create_from_reviewed_candidate")
        return await _execute_operator_action(request=request, action="recovery_plan_apply.create_from_reviewed_candidate", fn=lambda: orchestrator.create_recovery_plan_from_reviewed_candidate(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["recovery_plan_apply.create_from_reviewed_candidate"])

    @app.post("/api/cockpit/recovery-plan-apply/confirm-manual-external-recovery")
    async def recovery_plan_apply_confirm_manual_external_recovery(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.confirm_manual_external_recovery")
        return await _execute_operator_action(request=request, action="recovery_plan_apply.confirm_manual_external_recovery", fn=lambda: orchestrator.confirm_manual_external_recovery_plan(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["recovery_plan_apply.confirm_manual_external_recovery"])

    @app.post("/api/cockpit/recovery-plan-apply/verify-no-mismatch")
    async def recovery_plan_apply_verify_no_mismatch(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.verify_no_mismatch")
        return await _execute_operator_action(request=request, action="recovery_plan_apply.verify_no_mismatch", fn=lambda: orchestrator.verify_recovery_no_mismatch(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["recovery_plan_apply.verify_no_mismatch"])

    @app.post("/api/cockpit/recovery-plan-apply/clear")
    async def recovery_plan_apply_clear(request: Request) -> dict[str, Any]:
        _auth_context(request)
        return await _execute_operator_action(request=request, action="recovery_plan_apply.clear", fn=orchestrator.clear_recovery_plan_apply, confirmation_expected=DANGER_ACTION_CONFIRMATIONS["recovery_plan_apply.clear"])



    @app.get("/api/cockpit/external-recovery-evidence-gate")
    async def cockpit_external_recovery_evidence_gate(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        snapshot = await orchestrator.snapshot(log_limit=20)
        return {"ok": True, "external_recovery_evidence_gate": snapshot.get("external_recovery_evidence_gate"), "engine_position_recovery_gate": snapshot.get("engine_position_recovery_gate"), "request_security": context}

    async def _safe_json_body(request: Request) -> dict[str, Any]:
        try:
            body = await request.json()
            return body if isinstance(body, dict) else {}
        except Exception:
            return {}

    @app.post("/api/cockpit/external-recovery-evidence/capture")
    async def external_recovery_evidence_capture(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="external_recovery_evidence.capture")
        evidence = await _safe_json_body(request)
        return await _execute_operator_action(request=request, action="external_recovery_evidence.capture", fn=lambda: orchestrator.capture_external_recovery_evidence(operator_id=operator_id, evidence=evidence), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["external_recovery_evidence.capture"])

    @app.post("/api/cockpit/external-recovery-evidence/capture-post-recovery-snapshot")
    async def external_recovery_evidence_capture_post_recovery_snapshot(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="external_recovery_evidence.capture_post_recovery_snapshot")
        return await _execute_operator_action(request=request, action="external_recovery_evidence.capture_post_recovery_snapshot", fn=lambda: orchestrator.capture_post_recovery_balance_snapshot(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["external_recovery_evidence.capture_post_recovery_snapshot"])

    @app.post("/api/cockpit/external-recovery-evidence/no-mismatch-preflight")
    async def external_recovery_evidence_no_mismatch_preflight(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="external_recovery_evidence.no_mismatch_preflight")
        return await _execute_operator_action(request=request, action="external_recovery_evidence.no_mismatch_preflight", fn=lambda: orchestrator.run_external_recovery_no_mismatch_preflight(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["external_recovery_evidence.no_mismatch_preflight"])

    @app.post("/api/cockpit/external-recovery-evidence/verify-no-mismatch-safe-apply")
    async def external_recovery_evidence_verify_no_mismatch_safe_apply(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="external_recovery_evidence.verify_no_mismatch_safe_apply")
        return await _execute_operator_action(request=request, action="external_recovery_evidence.verify_no_mismatch_safe_apply", fn=lambda: orchestrator.verify_no_mismatch_safe_apply_with_evidence(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["external_recovery_evidence.verify_no_mismatch_safe_apply"])

    @app.post("/api/cockpit/external-recovery-evidence/clear")
    async def external_recovery_evidence_clear(request: Request) -> dict[str, Any]:
        _auth_context(request)
        return await _execute_operator_action(request=request, action="external_recovery_evidence.clear", fn=orchestrator.clear_external_recovery_evidence, confirmation_expected=DANGER_ACTION_CONFIRMATIONS["external_recovery_evidence.clear"])

    @app.get("/api/cockpit/exchange-environment-source-gate")
    async def cockpit_exchange_environment_source_gate(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        snapshot = await orchestrator.snapshot(log_limit=20)
        return {"ok": True, "exchange_environment_source_gate_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION, "exchange_environment_source_gate": snapshot.get("exchange_environment_source_gate"), "external_recovery_evidence_gate": snapshot.get("external_recovery_evidence_gate"), "request_security": context}

    @app.post("/api/cockpit/exchange-environment-source-gate/verify-consistency")
    async def exchange_environment_verify_consistency(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="exchange_environment.verify_consistency")
        return await _execute_operator_action(request=request, action="exchange_environment.verify_consistency", fn=lambda: orchestrator.verify_exchange_environment_consistency(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["exchange_environment.verify_consistency"])

    @app.post("/api/cockpit/exchange-environment-source-gate/capture-fresh-balance")
    async def exchange_environment_capture_fresh_balance(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="exchange_environment.capture_fresh_balance")
        return await _execute_operator_action(request=request, action="exchange_environment.capture_fresh_balance", fn=lambda: orchestrator.capture_fresh_exchange_balance_source(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["exchange_environment.capture_fresh_balance"])

    @app.post("/api/cockpit/exchange-environment-source-gate/clear")
    async def exchange_environment_clear(request: Request) -> dict[str, Any]:
        _auth_context(request)
        return await _execute_operator_action(request=request, action="exchange_environment.clear", fn=orchestrator.clear_exchange_environment_source_gate, confirmation_expected=DANGER_ACTION_CONFIRMATIONS["exchange_environment.clear"])



    @app.get("/api/cockpit/demo-entry-execution-gate")
    async def cockpit_demo_entry_execution_gate(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        snapshot = await orchestrator.snapshot(log_limit=20)
        return {"ok": True, "demo_entry_execution_gate": snapshot.get("demo_entry_execution_gate"), "entry_guard": snapshot.get("entry_guard"), "request_security": context}

    @app.post("/api/cockpit/demo-entry/dry-run")
    async def demo_entry_dry_run(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="demo_entry.dry_run")
        spec = await _safe_json_body(request)
        return await _execute_operator_action(request=request, action="demo_entry.dry_run", fn=lambda: orchestrator.demo_entry_dry_run(operator_id=operator_id, spec=spec), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["demo_entry.dry_run"])

    @app.post("/api/cockpit/demo-entry/verify-filters")
    async def demo_entry_verify_filters(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="demo_entry.verify_filters")
        spec = await _safe_json_body(request)
        return await _execute_operator_action(request=request, action="demo_entry.verify_filters", fn=lambda: orchestrator.verify_demo_entry_filters(operator_id=operator_id, spec=spec), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["demo_entry.verify_filters"])

    @app.post("/api/cockpit/demo-entry/record-intent")
    async def demo_entry_record_intent(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="demo_entry.record_intent")
        intent = await _safe_json_body(request)
        return await _execute_operator_action(request=request, action="demo_entry.record_intent", fn=lambda: orchestrator.record_demo_entry_intent(operator_id=operator_id, intent=intent), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["demo_entry.record_intent"])

    @app.post("/api/cockpit/demo-entry/authorize-demo-only-entry")
    async def demo_entry_authorize_demo_only_entry(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="demo_entry.authorize_demo_only_entry")
        body = await _safe_json_body(request)
        ttl_seconds = int(body.get("ttl_seconds", 120)) if isinstance(body, dict) else 120
        return await _execute_operator_action(request=request, action="demo_entry.authorize_demo_only_entry", fn=lambda: orchestrator.authorize_demo_only_entry(operator_id=operator_id, ttl_seconds=ttl_seconds), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["demo_entry.authorize_demo_only_entry"])

    @app.post("/api/cockpit/demo-entry/verify-post-entry-protective-exit")
    async def demo_entry_verify_post_entry_protective_exit(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="demo_entry.verify_post_entry_protective_exit")
        return await _execute_operator_action(request=request, action="demo_entry.verify_post_entry_protective_exit", fn=lambda: orchestrator.verify_post_entry_protective_exit(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["demo_entry.verify_post_entry_protective_exit"])

    @app.post("/api/cockpit/demo-entry/clear")
    async def demo_entry_clear(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(request=request, action="demo_entry.clear", fn=orchestrator.clear_demo_entry_execution_gate, confirmation_expected=DANGER_ACTION_CONFIRMATIONS["demo_entry.clear"])

    @app.websocket("/ws/cockpit")
    async def cockpit_ws(websocket: WebSocket) -> None:
        auth_result = authenticate_websocket(
            settings,
            supplied_token=websocket.query_params.get("token"),
            operator_id=websocket.query_params.get("operator"),
        )
        if not auth_result.get("ok", False):
            await websocket.close(code=1008, reason=str(auth_result.get("reason_code") or "AUTH_REQUIRED"))
            return
        await broadcaster.connect(websocket)
        await broadcaster.keepalive(websocket)

    @app.post("/api/engine/start")
    async def engine_start(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(request=request, action="engine.start", fn=orchestrator.start_engine)

    @app.post("/api/engine/stop")
    async def engine_stop(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(request=request, action="engine.stop", fn=orchestrator.stop_engine)

    @app.post("/api/engine/restart")
    async def engine_restart(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(request=request, action="engine.restart", fn=orchestrator.restart_engine)

    @app.post("/api/trade/force-buy")
    async def force_buy(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(
            request=request,
            action="trade.force_buy",
            fn=orchestrator.force_buy,
            confirmation_expected=DANGER_ACTION_CONFIRMATIONS["trade.force_buy"],
        )

    @app.post("/api/trade/force-sell")
    async def force_sell(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(
            request=request,
            action="trade.force_sell",
            fn=orchestrator.force_sell,
            confirmation_expected=DANGER_ACTION_CONFIRMATIONS["trade.force_sell"],
        )

    @app.post("/api/trade/cancel-pending")
    async def cancel_pending(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(
            request=request,
            action="trade.cancel_pending",
            fn=orchestrator.cancel_pending,
            confirmation_expected=DANGER_ACTION_CONFIRMATIONS["trade.cancel_pending"],
        )

    @app.post("/api/risk/reset")
    async def risk_reset(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(
            request=request,
            action="risk.reset",
            fn=orchestrator.risk_reset,
            confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk.reset"],
        )

    @app.post("/api/risk/safe-mode/toggle")
    async def safe_mode_toggle(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(
            request=request,
            action="risk.safe_mode.toggle",
            fn=orchestrator.toggle_safe_mode,
            confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk.safe_mode.toggle"],
        )


    @app.get("/api/cockpit/operator-actions")
    async def cockpit_operator_actions(request: Request) -> dict[str, Any]:
        _auth_context(request)
        snapshot = await orchestrator.snapshot(log_limit=20)
        return {
            "ok": True,
            "action_audit_runtime_lock_version": OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION,
            "risk_reconciliation_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
            "reconciliation_execution_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
            "reconciliation_decision_apply_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
            "operator_actions": snapshot.get("operator_actions", []),
            "operator_action_ledger": snapshot.get("operator_action_ledger", {}),
        }

    @app.post("/api/cockpit/runtime-lock/clear-stale")
    async def runtime_lock_clear_stale(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(
            request=request,
            action="runtime_lock.clear_stale",
            fn=orchestrator.clear_stale_runtime_lock,
            confirmation_expected=DANGER_ACTION_CONFIRMATIONS["runtime_lock.clear_stale"],
        )

    @app.get("/api/cockpit/risk-reconciliation")
    async def cockpit_risk_reconciliation(request: Request) -> dict[str, Any]:
        _auth_context(request)
        snapshot = await orchestrator.snapshot(log_limit=40)
        return {"ok": True, "risk_reconciliation_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION, "reconciliation_execution_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION, "risk_reconciliation": snapshot.get("risk_reconciliation", {}), "reconciliation_execution": snapshot.get("reconciliation_execution", {}), "tracked_position_adoption_candidate": snapshot.get("tracked_position_adoption_candidate", {}), "balance_review": snapshot.get("balance_review", {}), "entry_guard": snapshot.get("entry_guard", {})}

    @app.post("/api/cockpit/risk-reconciliation/acknowledge")
    async def risk_reconciliation_acknowledge(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="risk_reconciliation.acknowledge")
        return await _execute_operator_action(request=request, action="risk_reconciliation.acknowledge", fn=lambda: orchestrator.acknowledge_risk_reconciliation(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk_reconciliation.acknowledge"])

    @app.post("/api/cockpit/risk-reconciliation/clear-acknowledgement")
    async def risk_reconciliation_clear_acknowledgement(request: Request) -> dict[str, Any]:
        return await _execute_operator_action(request=request, action="risk_reconciliation.clear_acknowledgement", fn=orchestrator.clear_risk_reconciliation_acknowledgement, confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk_reconciliation.clear_acknowledgement"])

    @app.get("/api/cockpit/reconciliation-execution")
    async def cockpit_reconciliation_execution(request: Request) -> dict[str, Any]:
        _auth_context(request)
        snapshot = await orchestrator.snapshot(log_limit=40)
        return {
            "ok": True,
            "reconciliation_execution_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
            "reconciliation_decision_apply_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
            "balance_review": snapshot.get("balance_review", {}),
            "risk_reconciliation": snapshot.get("risk_reconciliation", {}),
            "reconciliation_execution": snapshot.get("reconciliation_execution", {}),
            "reconciliation_decision_apply": snapshot.get("reconciliation_decision_apply", {}),
            "tracked_position_adoption_candidate": snapshot.get("tracked_position_adoption_candidate", {}),
            "runtime_lock_owner_mismatch_resolver": snapshot.get("runtime_lock_owner_mismatch_resolver", {}),
            "entry_guard": snapshot.get("entry_guard", {}),
        }

    @app.post("/api/cockpit/risk-reconciliation/confirm-balance-snapshot")
    async def risk_reconciliation_confirm_balance_snapshot(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="risk_reconciliation.confirm_balance_snapshot")
        return await _execute_operator_action(request=request, action="risk_reconciliation.confirm_balance_snapshot", fn=lambda: orchestrator.confirm_balance_snapshot(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk_reconciliation.confirm_balance_snapshot"])

    @app.post("/api/cockpit/risk-reconciliation/resolve-dust-safe-base-balance")
    async def risk_reconciliation_resolve_dust_safe_base_balance(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="risk_reconciliation.resolve_dust_safe")
        return await _execute_operator_action(request=request, action="risk_reconciliation.resolve_dust_safe", fn=lambda: orchestrator.resolve_dust_safe_base_balance(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk_reconciliation.resolve_dust_safe"])

    @app.post("/api/cockpit/risk-reconciliation/adopt-position-candidate")
    async def risk_reconciliation_adopt_position_candidate(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="risk_reconciliation.adopt_position_candidate")
        return await _execute_operator_action(request=request, action="risk_reconciliation.adopt_position_candidate", fn=lambda: orchestrator.create_tracked_position_adoption_candidate(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk_reconciliation.adopt_position_candidate"])

    @app.get("/api/cockpit/reconciliation-decision-apply")
    async def cockpit_reconciliation_decision_apply(request: Request) -> dict[str, Any]:
        _auth_context(request)
        snapshot = await orchestrator.snapshot(log_limit=40)
        return {
            "ok": True,
            "reconciliation_decision_apply_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
            "reconciliation_decision_apply": snapshot.get("reconciliation_decision_apply", {}),
            "reconciliation_execution": snapshot.get("reconciliation_execution", {}),
            "tracked_position_adoption_candidate": snapshot.get("tracked_position_adoption_candidate", {}),
            "runtime_lock_owner_mismatch_resolver": snapshot.get("runtime_lock_owner_mismatch_resolver", {}),
            "entry_guard": snapshot.get("entry_guard", {}),
        }

    @app.post("/api/cockpit/risk-reconciliation/apply-tracked-position-candidate-review")
    async def risk_reconciliation_apply_tracked_position_candidate_review(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="risk_reconciliation.apply_tracked_position_candidate_review")
        return await _execute_operator_action(request=request, action="risk_reconciliation.apply_tracked_position_candidate_review", fn=lambda: orchestrator.apply_tracked_position_candidate_review(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk_reconciliation.apply_tracked_position_candidate_review"])

    @app.post("/api/cockpit/risk-reconciliation/apply-dust-safe-clear")
    async def risk_reconciliation_apply_dust_safe_clear(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="risk_reconciliation.apply_dust_safe_clear")
        return await _execute_operator_action(request=request, action="risk_reconciliation.apply_dust_safe_clear", fn=lambda: orchestrator.apply_dust_safe_clear(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk_reconciliation.apply_dust_safe_clear"])

    @app.post("/api/cockpit/risk-reconciliation/clear-manual-decision")
    async def risk_reconciliation_clear_manual_decision(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        require_operator_identity(context.get("operator_id"), action="risk_reconciliation.clear_manual_decision")
        return await _execute_operator_action(request=request, action="risk_reconciliation.clear_manual_decision", fn=orchestrator.clear_manual_reconciliation_decision, confirmation_expected=DANGER_ACTION_CONFIRMATIONS["risk_reconciliation.clear_manual_decision"])

    @app.post("/api/cockpit/runtime-lock/resolve-owner-mismatch")
    async def runtime_lock_resolve_owner_mismatch(request: Request) -> dict[str, Any]:
        context = _auth_context(request)
        operator_id = require_operator_identity(context.get("operator_id"), action="runtime_lock.resolve_owner_mismatch")
        return await _execute_operator_action(request=request, action="runtime_lock.resolve_owner_mismatch", fn=lambda: orchestrator.resolve_runtime_lock_owner_mismatch(operator_id=operator_id), confirmation_expected=DANGER_ACTION_CONFIRMATIONS["runtime_lock.resolve_owner_mismatch"])

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
