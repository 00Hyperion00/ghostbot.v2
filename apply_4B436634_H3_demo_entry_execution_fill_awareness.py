from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_VERSION = "4B.4.3.6.6.34-H3"
PATCH_NAME = "Demo Entry Execution Fill Awareness Hotfix"
ROOT = Path.cwd()


def _replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    if old not in text:
        return text, False
    return text.replace(old, new, 1), True


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def patch_orchestrator() -> dict[str, bool]:
    path = ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py"
    text = path.read_text(encoding="utf-8")
    results: dict[str, bool] = {}

    helper_marker = '''def _protective_exit_present_from_status(status: dict[str, Any]) -> bool:
    position = _as_dict(status.get("position_snapshot"))
    protective_exit = _as_dict(position.get("protective_exit"))
    risk_plan = _as_dict(position.get("risk_plan"))
    pending = _as_dict(status.get("pending_snapshot"))
    candidates = [protective_exit, risk_plan, pending]
    for candidate in candidates:
        if bool(candidate.get("present", False)) or bool(candidate.get("stop_loss_order_id")) or bool(candidate.get("take_profit_order_id")) or bool(candidate.get("protective_exit_present", False)):
            return True
    return False


'''
    h3_helpers = '''def _protective_exit_present_from_status(status: dict[str, Any]) -> bool:
    position = _as_dict(status.get("position_snapshot"))
    protective_exit = _as_dict(position.get("protective_exit"))
    risk_plan = _as_dict(position.get("risk_plan"))
    pending = _as_dict(status.get("pending_snapshot"))
    candidates = [protective_exit, risk_plan, pending, _as_dict(status.get("protective_exit")), _as_dict(status.get("risk_plan"))]
    for candidate in candidates:
        if bool(candidate.get("present", False)) or bool(candidate.get("stop_loss_order_id")) or bool(candidate.get("take_profit_order_id")) or bool(candidate.get("protective_exit_present", False)):
            return True
    return False


# --- 4B.4.3.6.6.34-H3 demo entry execution fill-awareness helpers ---
def _object_public_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if value is None:
        return {}
    for method_name in ("model_dump", "to_dict", "dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                candidate = method()
            except TypeError:
                continue
            if isinstance(candidate, dict):
                return dict(candidate)
    data: dict[str, Any] = {}
    for name in (
        "ok", "success", "status", "order_id", "orderId", "id",
        "client_order_id", "clientOrderId", "executed_qty", "executedQty",
        "filled_qty", "filledQty", "cum_quote_qty", "cummulativeQuoteQty",
    ):
        if hasattr(value, name):
            try:
                data[name] = getattr(value, name)
            except Exception:
                pass
    return data


def _nested_order_dicts(value: Any) -> list[dict[str, Any]]:
    root = _object_public_dict(value)
    if not root:
        return []
    candidates: list[dict[str, Any]] = [root]
    for key in ("order", "order_result", "result", "response", "data", "raw"):
        nested = root.get(key)
        nested_dict = _object_public_dict(nested)
        if nested_dict:
            candidates.append(nested_dict)
    return candidates


def _first_text_from_dicts(dicts: list[dict[str, Any]], *keys: str) -> str:
    for item in dicts:
        for key in keys:
            value = item.get(key)
            if value is not None and str(value).strip() != "":
                return str(value).strip()
    return ""


def _first_float_from_dicts(dicts: list[dict[str, Any]], *keys: str) -> float:
    for item in dicts:
        for key in keys:
            value = _float_value(item.get(key), 0.0)
            if value > 0:
                return value
    return 0.0


def _position_present_from_status(status: dict[str, Any]) -> bool:
    status = status if isinstance(status, dict) else {}
    candidates = [
        _as_dict(status.get("position_snapshot")),
        _as_dict(status.get("position")),
        _as_dict(status.get("runtime_position")),
        _as_dict(status.get("current_position")),
    ]
    for position in candidates:
        if bool(position.get("present", False)):
            return True
        qty = max(
            _float_value(position.get("qty"), 0.0),
            _float_value(position.get("quantity"), 0.0),
            _float_value(position.get("amount"), 0.0),
            _float_value(position.get("base_qty"), 0.0),
            _float_value(position.get("position_amt"), 0.0),
            _float_value(position.get("positionAmt"), 0.0),
        )
        if abs(qty) > 0:
            return True
    return False


def _pending_order_present_from_status(status: dict[str, Any]) -> bool:
    pending = _as_dict((status if isinstance(status, dict) else {}).get("pending_snapshot"))
    if bool(pending.get("present", False)):
        return True
    for key in ("order_id", "orderId", "client_order_id", "clientOrderId"):
        if pending.get(key):
            return True
    return False


def _build_force_buy_execution_binding(*, result: Any, status_after: dict[str, Any], demo_gate: dict[str, Any], operator_id: str = "UNKNOWN", error: str | None = None) -> dict[str, Any]:
    status_after = status_after if isinstance(status_after, dict) else {}
    dicts = _nested_order_dicts(result)
    status_text = _first_text_from_dicts(dicts, "status", "order_status", "state").upper()
    order_id = _first_text_from_dicts(dicts, "order_id", "orderId", "id")
    client_order_id = _first_text_from_dicts(dicts, "client_order_id", "clientOrderId", "clientOrderID", "client_id")
    executed_qty = _first_float_from_dicts(dicts, "executed_qty", "executedQty", "filled_qty", "filledQty", "qty", "quantity")
    cumulative_quote_qty = _first_float_from_dicts(dicts, "cum_quote_qty", "cummulativeQuoteQty", "cumulative_quote_qty", "quote_qty", "quoteQty")
    position_present = _position_present_from_status(status_after)
    pending_present = _pending_order_present_from_status(status_after)
    protective_exit_present = _protective_exit_present_from_status(status_after)
    explicit_ok = any(bool(item.get("ok", False) or item.get("success", False)) for item in dicts)
    status_accepted = status_text in {"NEW", "PARTIALLY_FILLED", "FILLED", "ACCEPTED", "SUCCESS", "OK"}
    status_terminal_rejected = status_text in {"REJECTED", "EXPIRED", "CANCELED", "CANCELLED", "FAILED"}
    result_has_identifier = bool(order_id or client_order_id)
    result_has_fill = bool(executed_qty > 0 or cumulative_quote_qty > 0 or status_text in {"PARTIALLY_FILLED", "FILLED"})
    result_bound = bool(result_has_identifier or status_text or result_has_fill or position_present or pending_present)
    order_accepted = bool(result_bound and not status_terminal_rejected and (result_has_identifier or status_accepted or result_has_fill or position_present or pending_present or explicit_ok))
    order_executed = bool(result_has_fill or position_present)
    protected_position = bool(position_present and protective_exit_present)
    reason_codes: list[str] = []
    if error:
        reason_codes.append("FORCE_BUY_ENGINE_EXCEPTION")
    if result is None:
        reason_codes.append("FORCE_BUY_RESULT_MISSING")
    if result_bound:
        reason_codes.append("FORCE_BUY_RESULT_BOUND")
    else:
        reason_codes.append("FORCE_BUY_RESULT_NOT_BOUND")
    if order_accepted:
        reason_codes.append("FORCE_BUY_ORDER_ACCEPTED_OR_DETECTED")
    else:
        reason_codes.append("FORCE_BUY_ORDER_NOT_ACCEPTED_OR_DETECTED")
    if order_executed:
        reason_codes.append("FORCE_BUY_FILL_OR_POSITION_DETECTED")
    else:
        reason_codes.append("FORCE_BUY_FILL_NOT_DETECTED")
    if protected_position:
        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_VERIFIED")
    elif position_present:
        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_MISSING")
    else:
        reason_codes.append("POST_ENTRY_POSITION_NOT_PRESENT")
    if not protected_position:
        reason_codes.append("NO_FILL_NO_PROTECTION_FAIL_CLOSED")
    return {
        "contract_version": "4B.4.3.6.6.34-H3",
        "operator_id": str(operator_id or "UNKNOWN"),
        "bound_at_ms": utc_ms(),
        "force_buy_invoked": True,
        "order_result_bound": result_bound,
        "order_accepted": order_accepted,
        "order_executed": order_executed,
        "order_id": order_id or None,
        "client_order_id": client_order_id or None,
        "order_status": status_text or None,
        "executed_qty": executed_qty,
        "cumulative_quote_qty": cumulative_quote_qty,
        "post_entry_position_detected": position_present,
        "pending_order_detected": pending_present,
        "post_entry_protective_exit_verified": protected_position,
        "protective_exit_present": protective_exit_present,
        "authorization_should_be_consumed": order_accepted,
        "no_fill_no_protection_fail_closed": not protected_position,
        "demo_gate_status_before_execution": demo_gate.get("status"),
        "raw_result_type": type(result).__name__ if result is not None else "NoneType",
        "raw_result": _object_public_dict(result),
        "error": error,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "reason_codes": reason_codes,
    }


def _post_entry_protective_exit_record(*, status: dict[str, Any], operator_id: str = "UNKNOWN", latest_execution: dict[str, Any] | None = None) -> dict[str, Any]:
    latest_execution = latest_execution if isinstance(latest_execution, dict) else {}
    position_present = _position_present_from_status(status) or bool(latest_execution.get("post_entry_position_detected", False))
    protective_exit_present = _protective_exit_present_from_status(status) or bool(latest_execution.get("protective_exit_present", False))
    protective_exit_verified = bool(position_present and protective_exit_present)
    reason_codes = ["POST_ENTRY_PROTECTIVE_EXIT_VERIFIED" if protective_exit_verified else "POST_ENTRY_PROTECTIVE_EXIT_NOT_VERIFIED"]
    if not position_present:
        reason_codes.append("POST_ENTRY_POSITION_NOT_PRESENT")
    if latest_execution and not protective_exit_verified:
        reason_codes.append("NO_FILL_NO_PROTECTION_FAIL_CLOSED")
    return {
        "contract_version": "4B.4.3.6.6.34-H3",
        "operator_id": str(operator_id or "UNKNOWN"),
        "verified_at_ms": utc_ms(),
        "position_present": position_present,
        "protective_exit_present": protective_exit_present,
        "protective_exit_verified": protective_exit_verified,
        "latest_force_buy_execution_present": bool(latest_execution),
        "read_only": True,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "reason_codes": reason_codes,
    }
# --- end 4B.4.3.6.6.34-H3 helpers ---


'''
    if "def _build_force_buy_execution_binding" not in text:
        text, results["fill_awareness_helpers_added"] = _replace_once(text, helper_marker, h3_helpers, "h3_helpers")
    else:
        results["fill_awareness_helpers_added"] = True

    replacements = [
        (
            '    post_entry = _as_dict(state.get("post_entry_protective_exit_verification"))\n    auth_expires = _float_value(authorization.get("expires_at_ms"), 0.0)\n',
            '    post_entry = _as_dict(state.get("post_entry_protective_exit_verification"))\n    latest_execution = _as_dict(state.get("latest_force_buy_execution"))\n    auth_expires = _float_value(authorization.get("expires_at_ms"), 0.0)\n',
            "gate_reads_latest_execution",
        ),
        (
            '    authorization_valid = bool(authorization.get("authorized", False) and auth_expires >= now and not authorization.get("consumed", False))\n    dry_run_ok = bool(latest_dry_run.get("dry_run_passed", False))\n',
            '    authorization_valid = bool(authorization.get("authorized", False) and auth_expires >= now and not authorization.get("consumed", False))\n    force_buy_result_bound = bool(latest_execution.get("order_result_bound", False))\n    force_buy_order_accepted = bool(latest_execution.get("order_accepted", False))\n    force_buy_order_executed = bool(latest_execution.get("order_executed", False))\n    post_entry_position_detected = bool(post_entry.get("position_present", False) or latest_execution.get("post_entry_position_detected", False))\n    post_entry_protective_exit_verified = bool(post_entry.get("protective_exit_verified", False) or latest_execution.get("post_entry_protective_exit_verified", False))\n    execution_attempted = bool(latest_execution)\n    no_fill_no_protection_fail_closed = bool(execution_attempted and not post_entry_protective_exit_verified)\n    dry_run_ok = bool(latest_dry_run.get("dry_run_passed", False))\n',
            "gate_computes_fill_awareness",
        ),
        (
            '    demo_trade_enablement_ready = bool(demo_runtime and entry_guard_ready and cache_ready and fresh_source_verified and dry_run_ok and filters_ok and intent_recorded and authorization_valid)\n',
            '    demo_trade_enablement_ready = bool(demo_runtime and entry_guard_ready and cache_ready and fresh_source_verified and dry_run_ok and filters_ok and intent_recorded and authorization_valid and not no_fill_no_protection_fail_closed)\n',
            "gate_blocks_after_unprotected_execution",
        ),
        (
            '    if bool(post_entry.get("protective_exit_verified", False)):\n        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_VERIFIED")\n    else:\n        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_VERIFICATION_PENDING")\n',
            '    if post_entry_protective_exit_verified:\n        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_VERIFIED")\n    elif no_fill_no_protection_fail_closed:\n        reason_codes.append("NO_FILL_NO_PROTECTION_FAIL_CLOSED")\n    else:\n        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_VERIFICATION_PENDING")\n',
            "gate_reports_no_protection_fail_closed",
        ),
        (
            '        "demo_trade_authorization": authorization,\n        "post_entry_protective_exit_verification": post_entry,\n        "engine_position_state_mutated": False,\n',
            '        "demo_trade_authorization": authorization,\n        "post_entry_protective_exit_verification": post_entry,\n        "force_buy_execution_fill_awareness_version": "4B.4.3.6.6.34-H3",\n        "latest_force_buy_execution": latest_execution,\n        "force_buy_result_bound": force_buy_result_bound,\n        "force_buy_order_accepted": force_buy_order_accepted,\n        "force_buy_order_executed": force_buy_order_executed,\n        "post_entry_position_detected": post_entry_position_detected,\n        "post_entry_protective_exit_verified": post_entry_protective_exit_verified,\n        "no_fill_no_protection_fail_closed": no_fill_no_protection_fail_closed,\n        "engine_position_state_mutated": False,\n',
            "gate_returns_fill_awareness_fields",
        ),
        (
            '        "status": "DEMO_ENTRY_ENABLEMENT_READY" if demo_trade_enablement_ready else "WAITING_FOR_DEMO_ENTRY_EXECUTION_PREFLIGHT",\n',
            '        "status": "DEMO_ENTRY_EXECUTION_PROTECTED" if post_entry_protective_exit_verified else ("DEMO_ENTRY_EXECUTION_FAIL_CLOSED_NO_PROTECTION" if no_fill_no_protection_fail_closed else ("DEMO_ENTRY_ENABLEMENT_READY" if demo_trade_enablement_ready else "WAITING_FOR_DEMO_ENTRY_EXECUTION_PREFLIGHT")),\n',
            "gate_status_fill_awareness",
        ),
    ]
    for old, new, key in replacements:
        text, results[key] = _replace_once(text, old, new, key)

    old_verify = '''    async def verify_post_entry_protective_exit(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        try:
            status = await self.engine.get_status()
        except Exception as exc:
            status = {"ok": False, "error": str(exc)}
        position = _as_dict(status.get("position_snapshot"))
        position_present = bool(position.get("present", False))
        protective_exit_verified = bool(position_present and _protective_exit_present_from_status(status))
        record = {
            "contract_version": OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "verified_at_ms": utc_ms(),
            "position_present": position_present,
            "protective_exit_verified": protective_exit_verified,
            "read_only": True,
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
            "order_path_mutation_performed": False,
            "live_real_enablement_performed": False,
            "reason_codes": ["POST_ENTRY_PROTECTIVE_EXIT_VERIFIED" if protective_exit_verified else "POST_ENTRY_PROTECTIVE_EXIT_NOT_VERIFIED"],
        }
        state = self._demo_entry_execution_state()
        state["post_entry_protective_exit_verification"] = record
        ledger = list(state.get("post_entry_protective_exit_ledger") or [])
        ledger.append(record)
        state["post_entry_protective_exit_ledger"] = ledger[-30:]
        self._set_demo_entry_execution_state(state)
        snapshot_after = await self.snapshot(log_limit=20)
        return self._result(ok=protective_exit_verified, action="demo_entry.verify_post_entry_protective_exit", message="34 post-entry protective exit verified." if protective_exit_verified else "34 post-entry protective exit is not verified; keep demo entry supervision active.", data={"demo_entry_execution_gate": snapshot_after.get("demo_entry_execution_gate"), "post_entry_protective_exit_verification": record})
'''
    new_verify = '''    async def verify_post_entry_protective_exit(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        try:
            status = await self.engine.get_status()
        except Exception as exc:
            status = {"ok": False, "error": str(exc)}
        state = self._demo_entry_execution_state()
        latest_execution = _as_dict(state.get("latest_force_buy_execution"))
        record = _post_entry_protective_exit_record(status=status, operator_id=operator_id, latest_execution=latest_execution)
        protective_exit_verified = bool(record.get("protective_exit_verified", False))
        state["post_entry_protective_exit_verification"] = record
        ledger = list(state.get("post_entry_protective_exit_ledger") or [])
        ledger.append(record)
        state["post_entry_protective_exit_ledger"] = ledger[-30:]
        self._set_demo_entry_execution_state(state)
        snapshot_after = await self.snapshot(log_limit=20)
        return self._result(ok=protective_exit_verified, action="demo_entry.verify_post_entry_protective_exit", message="34-H3 post-entry protective exit verified." if protective_exit_verified else "34-H3 post-entry protective exit is not verified; no-fill/no-protection gate remains fail-closed.", data={"demo_entry_execution_gate": snapshot_after.get("demo_entry_execution_gate"), "post_entry_protective_exit_verification": record})
'''
    text, results["protective_exit_verifier_h3"] = _replace_once(text, old_verify, new_verify, "verify_post_entry")

    old_force_buy = '''    async def force_buy(self) -> dict[str, Any]:
        snapshot = await self.snapshot(log_limit=20)
        guard = _as_dict(snapshot.get("entry_guard"))
        if bool(guard.get("force_buy_disabled", False)):
            reason_code = "ENTRY_BLOCK_UNTIL_RECONCILED" if bool(guard.get("entry_block_until_reconciled", False)) else "RED_RISK_BADGE_ENTRY_GUARD"
            return self._result(ok=False, action="trade.force_buy", message="Force BUY blocked by cockpit entry guard", data={"reason_code": reason_code, "entry_guard": guard})
        demo_gate = await self._demo_entry_execution_gate_snapshot_from_snapshot(snapshot)
        if not bool(demo_gate.get("demo_trade_enablement_ready", False)):
            return self._result(ok=False, action="trade.force_buy", message="Force BUY blocked by 34 demo entry execution gate; run dry-run, filters, intent audit, and demo-only authorization first.", data={"reason_code": "DEMO_ENTRY_EXECUTION_GATE_NOT_READY", "entry_guard": guard, "demo_entry_execution_gate": demo_gate})
        try:
            await self.engine.force_buy()
            state = self._demo_entry_execution_state()
            authorization = _as_dict(state.get("demo_trade_authorization"))
            if authorization:
                authorization["consumed"] = True
                authorization["consumed_at_ms"] = utc_ms()
                state["demo_trade_authorization"] = authorization
                self._set_demo_entry_execution_state(state)
            return self._result(ok=True, action="trade.force_buy", message="Force BUY requested through 34 demo-only controlled entry gate", data={"demo_entry_execution_gate": demo_gate})
        except Exception as exc:
            return self._result(ok=False, action="trade.force_buy", message="Force BUY failed", data={"error": str(exc), "demo_entry_execution_gate": demo_gate})
'''
    new_force_buy = '''    async def force_buy(self) -> dict[str, Any]:
        snapshot = await self.snapshot(log_limit=20)
        guard = _as_dict(snapshot.get("entry_guard"))
        if bool(guard.get("force_buy_disabled", False)):
            reason_code = "ENTRY_BLOCK_UNTIL_RECONCILED" if bool(guard.get("entry_block_until_reconciled", False)) else "RED_RISK_BADGE_ENTRY_GUARD"
            return self._result(ok=False, action="trade.force_buy", message="Force BUY blocked by cockpit entry guard", data={"reason_code": reason_code, "entry_guard": guard})
        demo_gate = await self._demo_entry_execution_gate_snapshot_from_snapshot(snapshot)
        if not bool(demo_gate.get("demo_trade_enablement_ready", False)):
            return self._result(ok=False, action="trade.force_buy", message="Force BUY blocked by 34 demo entry execution gate; run dry-run, filters, intent audit, and demo-only authorization first.", data={"reason_code": "DEMO_ENTRY_EXECUTION_GATE_NOT_READY", "entry_guard": guard, "demo_entry_execution_gate": demo_gate})
        result: Any = None
        error_text: str | None = None
        try:
            result = await self.engine.force_buy()
        except Exception as exc:
            error_text = str(exc)
        try:
            status_after = await self.engine.get_status()
        except Exception as exc:
            status_after = {"ok": False, "error": str(exc)}
        state = self._demo_entry_execution_state()
        binding = _build_force_buy_execution_binding(result=result, status_after=status_after, demo_gate=demo_gate, operator_id=_as_dict(state.get("demo_trade_authorization")).get("operator_id") or "UNKNOWN", error=error_text)
        authorization = _as_dict(state.get("demo_trade_authorization"))
        if authorization and bool(binding.get("authorization_should_be_consumed", False)):
            authorization["consumed"] = True
            authorization["consumed_at_ms"] = utc_ms()
            authorization["consumption_reason"] = "FORCE_BUY_ORDER_ACCEPTED_OR_DETECTED"
            state["demo_trade_authorization"] = authorization
        elif authorization:
            authorization["consumption_blocked_reason"] = "FORCE_BUY_RESULT_NOT_BOUND_OR_NOT_ACCEPTED"
            state["demo_trade_authorization"] = authorization
        state["latest_force_buy_execution"] = binding
        ledger = list(state.get("force_buy_execution_ledger") or [])
        ledger.append(binding)
        state["force_buy_execution_ledger"] = ledger[-30:]
        post_entry_record = _post_entry_protective_exit_record(status=status_after, operator_id=binding.get("operator_id") or "UNKNOWN", latest_execution=binding)
        state["post_entry_protective_exit_verification"] = post_entry_record
        post_ledger = list(state.get("post_entry_protective_exit_ledger") or [])
        post_ledger.append(post_entry_record)
        state["post_entry_protective_exit_ledger"] = post_ledger[-30:]
        self._set_demo_entry_execution_state(state)
        snapshot_after = await self.snapshot(log_limit=20)
        ok = bool(binding.get("order_result_bound", False) and binding.get("order_accepted", False) and binding.get("post_entry_protective_exit_verified", False))
        if error_text:
            message = "34-H3 Force BUY failed in engine execution path."
            reason_code = "FORCE_BUY_ENGINE_EXCEPTION"
        elif ok:
            message = "34-H3 Force BUY bound to accepted order and protected post-entry state."
            reason_code = "FORCE_BUY_ORDER_BOUND_AND_PROTECTED"
        else:
            message = "34-H3 Force BUY is fail-closed: order/fill/protective-exit binding is incomplete."
            reason_code = "FORCE_BUY_NO_FILL_NO_PROTECTION_FAIL_CLOSED"
        return self._result(ok=ok, action="trade.force_buy", message=message, data={"reason_code": reason_code, "entry_guard": guard, "demo_entry_execution_gate": snapshot_after.get("demo_entry_execution_gate"), "force_buy_execution": binding, "post_entry_protective_exit_verification": post_entry_record})
'''
    text, results["force_buy_result_binding_h3"] = _replace_once(text, old_force_buy, new_force_buy, "force_buy")

    if not all(results.values()):
        missing = [key for key, ok in results.items() if not ok]
        raise RuntimeError(f"34-H3 patch anchors not found: {missing}")
    path.write_text(text, encoding="utf-8")
    return results


def write_support_files() -> list[str]:
    written: list[str] = []
    compile_tool = '''from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.34-H3"
ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/tradebot/cockpit/schemas.py",
    "src/tradebot/cockpit/security.py",
    "src/tradebot/cockpit/orchestrator.py",
    "src/tradebot/cockpit/app.py",
    "tools/check_cockpit_runtime_4B436634.py",
    "tools/compile_operator_cockpit_4B436634_H3.py",
]


def main() -> int:
    compiled = []
    errors = []
    for rel in FILES:
        path = ROOT / rel
        try:
            py_compile.compile(str(path), doraise=True)
            compiled.append(rel.replace("/", "\\\\"))
        except Exception as exc:
            errors.append({"file": rel, "error": str(exc)})
    orchestrator_text = (ROOT / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    checks = {
        "force_buy_result_binding_present": "def _build_force_buy_execution_binding" in orchestrator_text,
        "authorization_consumption_safety_present": "authorization_should_be_consumed" in orchestrator_text and "FORCE_BUY_RESULT_NOT_BOUND_OR_NOT_ACCEPTED" in orchestrator_text,
        "post_entry_position_detection_present": "def _position_present_from_status" in orchestrator_text,
        "protective_exit_mandatory_verification_present": "post_entry_protective_exit_verified" in orchestrator_text,
        "no_fill_no_protection_fail_closed_present": "NO_FILL_NO_PROTECTION_FAIL_CLOSED" in orchestrator_text,
        "force_buy_does_not_consume_on_missing_binding": "consumption_blocked_reason" in orchestrator_text,
    }
    payload = {"patch_version": PATCH_VERSION, "ok": not errors and all(checks.values()), "compiled": compiled, "errors": errors, **checks}
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''
    _write(ROOT / "tools" / "compile_operator_cockpit_4B436634_H3.py", compile_tool)
    written.append("tools/compile_operator_cockpit_4B436634_H3.py")

    test_file = '''from __future__ import annotations

import sys
import types

# The patch verification fixture contains only cockpit files. Provide minimal
# import-time stubs for sibling modules; the real project modules are used at runtime.
config_stub = types.ModuleType("tradebot.config")
config_stub.Settings = type("Settings", (), {})
sys.modules.setdefault("tradebot.config", config_stub)
engine_stub = types.ModuleType("tradebot.engine")
engine_stub.TradeBotEngine = type("TradeBotEngine", (), {})
sys.modules.setdefault("tradebot.engine", engine_stub)
persistence_stub = types.ModuleType("tradebot.persistence")
persistence_stub.SQLiteStore = type("SQLiteStore", (), {})
sys.modules.setdefault("tradebot.persistence", persistence_stub)
hardening_stub = types.ModuleType("tradebot.production_hardening")
hardening_stub.RuntimeLockHandle = type("RuntimeLockHandle", (), {})
hardening_stub.acquire_runtime_lock = lambda *args, **kwargs: None
hardening_stub.release_runtime_lock = lambda *args, **kwargs: None
sys.modules.setdefault("tradebot.production_hardening", hardening_stub)

from tradebot.cockpit.orchestrator import (
    _build_force_buy_execution_binding,
    _post_entry_protective_exit_record,
    build_demo_entry_execution_gate_snapshot,
)


class Settings:
    symbol = "ETHUSDT"
    market_type = "spot_demo"
    execution_mode = "live_demo"
    base_url = "https://demo-api.binance.com"


def _ready_guard() -> dict:
    return {"entry_actions_enabled": True, "force_buy_disabled": False, "entry_block_until_reconciled": False, "risk_badge": "GREEN", "entry_guard_release_authorized": True}


def _cache_ready() -> dict:
    return {"runtime_snapshot_override_active": True, "stale_engine_balance_invalidated": True, "entry_guard_release_stabilized_after_safe_apply": True, "no_mismatch_from_verified_fresh_source": True}


def test_missing_force_buy_result_without_position_fails_closed_and_does_not_consume_authorization() -> None:
    binding = _build_force_buy_execution_binding(result=None, status_after={"position_snapshot": {"present": False}}, demo_gate={"status": "DEMO_ENTRY_ENABLEMENT_READY"}, operator_id="operator-local")
    assert binding["order_result_bound"] is False
    assert binding["order_accepted"] is False
    assert binding["authorization_should_be_consumed"] is False
    assert binding["no_fill_no_protection_fail_closed"] is True
    assert "NO_FILL_NO_PROTECTION_FAIL_CLOSED" in binding["reason_codes"]


def test_order_result_with_identifier_and_protected_position_is_accepted_and_protected() -> None:
    binding = _build_force_buy_execution_binding(
        result={"orderId": 123, "status": "FILLED", "executedQty": "0.004", "cummulativeQuoteQty": "10"},
        status_after={"position_snapshot": {"present": True, "qty": 0.004, "protective_exit": {"present": True, "stop_loss_order_id": "sl-1"}}},
        demo_gate={"status": "DEMO_ENTRY_ENABLEMENT_READY"},
        operator_id="operator-local",
    )
    assert binding["order_result_bound"] is True
    assert binding["order_accepted"] is True
    assert binding["order_executed"] is True
    assert binding["authorization_should_be_consumed"] is True
    assert binding["post_entry_protective_exit_verified"] is True
    assert binding["no_fill_no_protection_fail_closed"] is False


def test_gate_becomes_fail_closed_after_unprotected_execution_attempt() -> None:
    state = {
        "latest_dry_run": {"dry_run_passed": True, "filter_review": {"filters_ok": True}},
        "latest_filter_review": {"filters_ok": True},
        "latest_intent": {"intent_recorded": True},
        "demo_trade_authorization": {"authorized": True, "expires_at_ms": 9999999999999999999, "consumed": False},
        "latest_force_buy_execution": {"order_result_bound": False, "order_accepted": False, "no_fill_no_protection_fail_closed": True},
    }
    gate = build_demo_entry_execution_gate_snapshot(settings=Settings(), status={"symbol": "ETHUSDT", "risk_badge": "GREEN"}, entry_guard=_ready_guard(), source_gate={"no_mismatch_from_verified_fresh_source": True}, cache_reconciliation=_cache_ready(), state=state)
    assert gate["demo_trade_enablement_ready"] is False
    assert gate["no_fill_no_protection_fail_closed"] is True
    assert gate["status"] == "DEMO_ENTRY_EXECUTION_FAIL_CLOSED_NO_PROTECTION"


def test_post_entry_record_reports_missing_position_after_execution() -> None:
    record = _post_entry_protective_exit_record(status={"position_snapshot": {"present": False}}, operator_id="operator-local", latest_execution={"force_buy_invoked": True})
    assert record["protective_exit_verified"] is False
    assert "POST_ENTRY_POSITION_NOT_PRESENT" in record["reason_codes"]
    assert "NO_FILL_NO_PROTECTION_FAIL_CLOSED" in record["reason_codes"]
'''
    _write(ROOT / "tests" / "test_operator_cockpit_4B436634_H3.py", test_file)
    written.append("tests/test_operator_cockpit_4B436634_H3.py")

    docs = '''# 4B.4.3.6.6.34-H3 — Demo Entry Execution Fill Awareness

This hotfix hardens 34 demo-only entry execution after successful dry-run/filter/intent/authorization.

## Scope

- Binds `force-buy` to a concrete engine/exchange order result when available.
- Detects order id, client order id, status, executed quantity, pending order, position and protective exit.
- Consumes demo authorization only if an accepted order or position/pending order is detected.
- Records `latest_force_buy_execution` and execution ledger.
- Records post-entry protective-exit verification immediately after force-buy and on explicit verification.
- Keeps no-fill/no-protection states fail-closed.

## Non-goals

- No live-real enablement.
- No auth policy relaxation.
- No engine position mutation.
- No automatic retry.
- No bypass when the engine returns no order/fill/position evidence.
'''
    _write(ROOT / "docs" / "OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_FILL_AWARENESS_4B436634_H3.md", docs)
    written.append("docs/OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_FILL_AWARENESS_4B436634_H3.md")
    return written


def main() -> int:
    results = patch_orchestrator()
    written = write_support_files()
    compiled = []
    errors = []
    for rel in ["src/tradebot/cockpit/orchestrator.py", "src/tradebot/cockpit/app.py", "src/tradebot/cockpit/schemas.py", "tools/compile_operator_cockpit_4B436634_H3.py", "tests/test_operator_cockpit_4B436634_H3.py"]:
        try:
            py_compile.compile(str(ROOT / rel), doraise=True)
            compiled.append(rel)
        except Exception as exc:
            errors.append({"file": rel, "error": str(exc)})
    payload = {"patch_version": PATCH_VERSION, "patch_name": PATCH_NAME, "written": ["src/tradebot/cockpit/orchestrator.py", *written], "compiled": compiled, "compile_errors": errors, **results, "force_buy_result_binding_added": True, "authorization_consumption_safety_added": True, "post_entry_position_detection_added": True, "protective_exit_mandatory_verification_added": True, "no_fill_no_protection_fail_closed_added": True, "runtime_mutation_performed": False, "order_path_mutation_performed": False, "live_real_enablement_performed": False, "auth_policy_relaxation_performed": False, "auto_position_mutation_performed": False}
    print(json.dumps(payload, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
