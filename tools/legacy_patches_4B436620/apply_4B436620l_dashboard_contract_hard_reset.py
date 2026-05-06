from __future__ import annotations

from pathlib import Path
import re

START_RE = r"# BEGIN 4B\.4\.3\.6\.6\.20[D-Z][^\n]*\n.*?# END 4B\.4\.3\.6\.6\.20[D-Z][^\n]*"
ENGINE_CONTRACT = "4B.4.3.6.6.20"

COMPAT_BLOCK = r'''
# BEGIN 4B.4.3.6.6.20L DASHBOARD CONTRACT HARD RESET
import ast as _tb20l_ast
import json as _tb20l_json
from urllib.parse import urlencode as _tb20l_urlencode
from typing import Any as _Tb20lAny

AUDIT_VIEWER_CONTRACT_VERSION = "4B.4.3.6.6.20"
DASHBOARD_CONTROL_CONTRACT_VERSION = "4B.4.3.6.6.20"


def _tb20l_safe_getattr(obj: object, name: str, default: _Tb20lAny = None) -> _Tb20lAny:
    try:
        return object.__getattribute__(obj, name)
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return default


def _tb20l_dict(value: _Tb20lAny) -> dict[str, _Tb20lAny]:
    return value if isinstance(value, dict) else {}


def _tb20l_list(value: _Tb20lAny) -> list[_Tb20lAny]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _tb20l_bool(value: _Tb20lAny) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "ready", "normal", "enabled", "ok"}
    return bool(value)


def _tb20l_float(value: _Tb20lAny, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _tb20l_int(value: _Tb20lAny, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _tb20l_fmt(value: _Tb20lAny, digits: int = 4) -> str:
    try:
        if value is None:
            return "-"
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-" if value in (None, "") else str(value)


def _tb20l_is_all(value: _Tb20lAny) -> bool:
    if value is None:
        return True
    return str(value).strip() in {"", "-", "All", "ALL", "all", "Tümü", "TUMU", "Tümü / All"}


def _tb20l_widget_value(obj: _Tb20lAny, default: _Tb20lAny = None) -> _Tb20lAny:
    if obj is None:
        return default
    try:
        if hasattr(obj, "get") and callable(obj.get):
            return obj.get()
    except Exception:
        pass
    return obj if obj is not None else default


def _tb20l_set_widget_text(widget: _Tb20lAny, text: str) -> None:
    if widget is None:
        return
    try:
        widget.text = text
    except Exception:
        pass
    try:
        kwargs = _tb20l_safe_getattr(widget, "kwargs", None)
        if isinstance(kwargs, dict):
            kwargs["text"] = text
    except Exception:
        pass
    try:
        config = _tb20l_safe_getattr(widget, "config", None)
        if isinstance(config, dict):
            config["text"] = text
    except Exception:
        pass
    try:
        if hasattr(widget, "delete") and hasattr(widget, "insert"):
            try:
                widget.delete("1.0", "end")
            except TypeError:
                widget.delete(0, "end")
            widget.insert("end", text)
            return
    except Exception:
        pass
    try:
        widget.configure(text=text)
    except Exception:
        pass


def _tb20l_app_set_text(app: _Tb20lAny, attr_name: str, text: str) -> None:
    widget = _tb20l_safe_getattr(app, attr_name, None)
    setter = _tb20l_safe_getattr(app, "_set_text", None)
    if callable(setter):
        # In tests the widget can be a string key like "status-box".
        try:
            setter(widget, text)
            return
        except Exception:
            pass
        try:
            setter(attr_name.replace("_", "-"), text)
            return
        except Exception:
            pass
    optional = _tb20l_safe_getattr(app, "_optional_set_text", None)
    if callable(optional):
        try:
            optional(attr_name, text)
            return
        except Exception:
            pass
    _tb20l_set_widget_text(widget, text)


def _tb20l_config(widget: _Tb20lAny, **kwargs: _Tb20lAny) -> None:
    if widget is None:
        return
    try:
        widget.configure(**kwargs)
    except Exception:
        pass
    try:
        kw = _tb20l_safe_getattr(widget, "kwargs", None)
        if isinstance(kw, dict):
            kw.update(kwargs)
    except Exception:
        pass
    try:
        cfg = _tb20l_safe_getattr(widget, "config", None)
        if isinstance(cfg, dict):
            cfg.update(kwargs)
    except Exception:
        pass
    for k, v in kwargs.items():
        try:
            setattr(widget, k, v)
        except Exception:
            pass


def _tb20l_status_position(status: dict[str, _Tb20lAny]) -> dict[str, _Tb20lAny]:
    return _tb20l_dict(status.get("position_snapshot") or status.get("position") or {})


def _tb20l_status_pending(status: dict[str, _Tb20lAny]) -> dict[str, _Tb20lAny]:
    return _tb20l_dict(status.get("pending_snapshot") or status.get("pending") or {})


def _tb20l_position_present(status: dict[str, _Tb20lAny]) -> bool:
    pos = _tb20l_status_position(status)
    return _tb20l_bool(pos.get("present")) or _tb20l_float(pos.get("qty")) > 0 or str(status.get("state", "")).upper() == "IN_POSITION"


def _tb20l_pending_present(status: dict[str, _Tb20lAny]) -> bool:
    pending = _tb20l_status_pending(status)
    state = str(status.get("state") or "").upper()
    return _tb20l_bool(pending.get("present")) or state in {"BUY_PENDING", "SELL_PENDING"} or state.endswith("_PENDING")


def _tb20l_contract_ok(version: _Tb20lAny) -> bool:
    if version in (None, ""):
        return True
    raw = str(version)
    if not raw.startswith("4B.4.3.6.6."):
        return False
    try:
        return int(raw.rsplit(".", 1)[-1]) >= 20
    except Exception:
        return False


def _tb20l_health_reason_codes(health: dict[str, _Tb20lAny]) -> tuple[bool, list[str]]:
    health_ok = True
    codes: list[str] = []
    account = str(health.get("account_consistency") or "HEALTHY").upper()
    position = str(health.get("position_consistency") or "HEALTHY").upper()
    pending = str(health.get("pending_consistency") or "HEALTHY").upper()
    anomaly = health.get("active_anomaly_code") or health.get("anomaly_code")
    if account not in {"HEALTHY", "OK", "-", "NONE"}:
        health_ok = False
        codes.append(f"ACCOUNT_CONSISTENCY_{account}")
        codes.append(f"HEALTH_ANOMALY:{account}")
    if position not in {"HEALTHY", "OK", "-", "NONE"}:
        health_ok = False
        codes.append(f"POSITION_CONSISTENCY_{position}")
        if "DRIFT" in position:
            codes.append("HEALTH_ANOMALY:ACCOUNT_POSITION_DRIFT")
        else:
            codes.append(f"HEALTH_ANOMALY:{position}")
    if pending not in {"HEALTHY", "OK", "-", "NONE"}:
        health_ok = False
        codes.append(f"PENDING_CONSISTENCY_{pending}")
        codes.append(f"HEALTH_ANOMALY:{pending}")
    if anomaly:
        health_ok = False
        codes.append(str(anomaly))
        codes.append(f"HEALTH_ANOMALY:{anomaly}")
    return health_ok, list(dict.fromkeys(codes))


def build_operator_control_state(status: dict[str, _Tb20lAny] | None = None, *, connected: bool = True, **_: _Tb20lAny) -> dict[str, _Tb20lAny]:
    status = _tb20l_dict(status)
    state = str(status.get("state") or status.get("runtime_state") or "FLAT")
    state_upper = state.upper()
    health = _tb20l_dict(status.get("health_snapshot"))
    risk = _tb20l_dict(status.get("risk_snapshot") or status)
    position = _tb20l_status_position(status)
    protective = _tb20l_dict(position.get("protective_exit"))
    has_position = _tb20l_position_present(status)
    has_pending = _tb20l_pending_present(status)
    safe_mode = _tb20l_bool(risk.get("safe_mode") or status.get("safe_mode"))
    kill_switch = _tb20l_bool(risk.get("kill_switch_active") or status.get("kill_switch_active"))
    health_ok, reason_codes = _tb20l_health_reason_codes(health)
    contract_ok = _tb20l_contract_ok(status.get("contract_version"))
    protective_exit_ready = protective.get("protective_exit_ready")
    if protective_exit_ready is None:
        protective_exit_ready = not bool(protective.get("block_reason")) if protective else True
    protective_exit_ready = bool(protective_exit_ready)
    block_reason = protective.get("block_reason")
    protective_blocked = bool(has_position and protective and not protective_exit_ready and block_reason not in (None, "", "-", "NONE", "OK"))
    position_is_dust = bool(protective.get("is_dust") or position.get("is_dust"))
    if not connected:
        reason_codes.append("BACKEND_OFFLINE")
    if not contract_ok:
        reason_codes.append("STALE_CONTRACT")
    if kill_switch:
        reason_codes.append("KILL_SWITCH_ACTIVE")
    if has_pending:
        reason_codes.extend(["PENDING_ORDER_ACTIVE", "PENDING_ORDER_EXISTS"])
    if safe_mode:
        reason_codes.append("SAFE_MODE_ACTIVE")
    if protective_blocked:
        reason_codes.append(str(block_reason).upper())
    reason_codes = list(dict.fromkeys(reason_codes))
    force_buy = bool(connected and contract_ok and health_ok and not kill_switch and not safe_mode and not has_pending and not has_position)
    force_sell = bool(connected and contract_ok and health_ok and not kill_switch and has_position and not has_pending and not protective_blocked and not position_is_dust)
    cancel_pending = bool(connected and has_pending)
    running = _tb20l_bool(status.get("running", True))
    start = bool(connected and not running)
    stop = bool(connected and running)
    if not contract_ok or not health_ok or kill_switch:
        severity = "danger"
    elif has_pending:
        severity = "busy"
    elif safe_mode:
        severity = "safe"
    elif has_position:
        severity = "position"
    else:
        severity = "ready"
    if has_pending and "BUY" in state_upper:
        hint = "PENDING giriş emri bekliyor"
    elif has_pending and "SELL" in state_upper:
        hint = "çıkış emri bekliyor"
    elif has_pending:
        hint = "pending emir var"
    elif safe_mode:
        hint = "safe mode aktif"
    elif force_sell:
        hint = "force sell aktif"
    elif force_buy:
        hint = "Force BUY aktif"
    elif reason_codes:
        hint = ", ".join(reason_codes)
    else:
        hint = "ready"
    buttons = {
        "force_buy": force_buy,
        "force_sell": force_sell,
        "cancel_pending": cancel_pending,
        "safe_mode_toggle": bool(connected),
        "balance_sync": bool(connected),
        "ai_reload": bool(connected),
        "start": start,
        "stop": stop,
    }
    warnings: list[str] = []
    if protective_blocked:
        warnings.append(str(block_reason).upper())
    if not health_ok:
        warnings.extend([c for c in reason_codes if "HEALTH_ANOMALY" in c or "CONSISTENCY" in c])
    if has_pending:
        warnings.append("PENDING_ORDER_ACTIVE")
    if safe_mode:
        warnings.append("SAFE_MODE_ACTIVE")
    return {
        "contract_version": DASHBOARD_CONTROL_CONTRACT_VERSION,
        "connected": bool(connected),
        "contract_ok": contract_ok,
        "state": state,
        "health_ok": health_ok,
        "safe_mode": safe_mode,
        "kill_switch_active": kill_switch,
        "has_position": has_position,
        "has_pending": has_pending,
        "protective_exit_ready": protective_exit_ready,
        "position_is_dust": position_is_dust,
        "severity": severity,
        "reason_codes": reason_codes,
        "warnings": list(dict.fromkeys(warnings)),
        "buttons": buttons,
        "force_buy": force_buy,
        "force_sell": force_sell,
        "cancel_pending": cancel_pending,
        "safe_mode_toggle": bool(connected),
        "balance_sync": bool(connected),
        "ai_reload": bool(connected),
        "start": start,
        "stop": stop,
        "hint": hint,
    }


def _tb20l_risk_exec(position: dict[str, _Tb20lAny]) -> dict[str, _Tb20lAny]:
    protective = _tb20l_dict(position.get("protective_exit"))
    return _tb20l_dict(protective.get("risk_execution") or position.get("risk_execution") or {})


def build_position_management_text(status_or_position: dict[str, _Tb20lAny] | None = None) -> str:
    payload = _tb20l_dict(status_or_position)
    position = _tb20l_dict(payload.get("position_snapshot") or payload.get("position") or payload)
    protective = _tb20l_dict(position.get("protective_exit"))
    risk_plan = _tb20l_dict(position.get("risk_plan"))
    risk_exec = _tb20l_risk_exec(position)
    present = _tb20l_bool(position.get("present")) or _tb20l_float(position.get("qty")) > 0
    ready = protective.get("protective_exit_ready")
    if ready is None:
        ready = not bool(protective.get("block_reason")) if protective else False
    ready_text = "READY" if bool(ready) else f"BLOCKED / {protective.get('block_reason') or '-'}"
    risk_plan_text = "READY" if risk_plan else "MISSING"
    effective_sl = risk_exec.get("effective_stop_loss") or risk_exec.get("active_stop_loss") or protective.get("active_stop_loss") or risk_plan.get("active_stop_loss") or risk_plan.get("stop_loss")
    active_stop = risk_exec.get("active_stop_loss") or protective.get("active_stop_loss") or risk_plan.get("active_stop_loss") or effective_sl
    partial_done = risk_plan.get("partial_tp_done", risk_plan.get("partial_tp_hit", protective.get("partial_tp_done", False)))
    risk_status = risk_exec.get("status") or ("READY" if risk_exec.get("should_submit_exit") is not False else "HOLD")
    exit_signal = risk_exec.get("exit_signal") or risk_exec.get("exit_action") or "HOLD"
    lines = [
        f"Position status : {'IN_POSITION' if present else 'FLAT'}",
        f"Position source : {position.get('source') or '-'}",
        f"Qty             : {_tb20l_fmt(position.get('qty'), 8)}",
        f"Entry           : {_tb20l_fmt(position.get('entry_price'), 4)}",
        f"Mark            : {_tb20l_fmt(position.get('mark_price'), 4)}",
        f"Unrealized PnL  : {_tb20l_fmt(position.get('unrealized_pnl'), 6)}",
        f"Unrealized %    : {_tb20l_fmt(position.get('unrealized_pnl_pct'), 4)}",
        f"Protective exit : {ready_text}",
        f"Exit qty        : {_tb20l_fmt(protective.get('tradable_exit_qty'), 8)}",
        f"Exit notional   : {_tb20l_fmt(protective.get('exit_notional'), 4)}",
        f"Dust position   : {bool(protective.get('is_dust') or position.get('is_dust'))}",
        f"Risk plan       : {risk_plan_text}",
        f"Stop loss       : {_tb20l_fmt(risk_plan.get('stop_loss') or protective.get('stop_loss'), 4)}",
        f"Effective SL    : {_tb20l_fmt(effective_sl, 4)}",
        f"Active stop     : {_tb20l_fmt(active_stop, 4)}",
        f"Take profit     : {_tb20l_fmt(risk_plan.get('take_profit') or protective.get('take_profit'), 4)}",
        f"Partial TP      : {_tb20l_fmt(risk_plan.get('partial_tp_price') or protective.get('partial_tp_price'), 4)} / {_tb20l_fmt(risk_plan.get('partial_tp_close_pct') or protective.get('partial_tp_close_pct'), 2)}",
        f"Partial TP done : {bool(partial_done)}",
        f"Risk exec       : {risk_status} / {exit_signal}",
        f"Risk exit       : {risk_exec.get('exit_action') or risk_exec.get('action') or 'NONE'} / {risk_exec.get('exit_reason') or risk_exec.get('reason') or '-'}",
    ]
    return "\n".join(lines)


def _tb20l_event_category(item: dict[str, _Tb20lAny]) -> str:
    category = item.get("category")
    if category and not _tb20l_is_all(category):
        return str(category)
    code = str(item.get("code") or "").upper()
    if code.startswith(("ORDER_", "LIVE_", "FILL_", "ENTRY_ORDER", "EXIT_ORDER")):
        return "Orders"
    if code.startswith(("AUTO_", "ENTRY_GUARD", "EXIT_GUARD")):
        return "Guards"
    if code.startswith(("RISK_", "SAFE_", "KILL_")):
        return "Risk"
    if code.startswith(("AI_", "MODEL_", "STRATEGY_")):
        return "AI"
    return "System"


def _tb20l_level(value: _Tb20lAny) -> str:
    raw = str(value or "INFO").upper()
    return "WARN" if raw == "WARNING" else raw


def _tb20l_severity(item: dict[str, _Tb20lAny]) -> str:
    if item.get("severity"):
        return str(item.get("severity")).lower()
    level = _tb20l_level(item.get("level"))
    if level in {"ERROR", "CRITICAL"}:
        return "error"
    if level == "WARN":
        return "warning"
    return "info"


def _tb20l_corr(item: dict[str, _Tb20lAny]) -> str:
    data = _tb20l_dict(item.get("data"))
    for key in ("correlation_id", "correlationId", "clientOrderId", "client_order_id", "orderId", "order_id", "signalKey", "signal_key"):
        if item.get(key):
            return str(item.get(key))
        if data.get(key):
            return str(data.get(key))
    return "-"


def _tb20l_blob(item: dict[str, _Tb20lAny]) -> str:
    try:
        return " ".join([
            _tb20l_level(item.get("level")),
            str(item.get("code") or ""),
            str(item.get("message") or ""),
            _tb20l_event_category(item),
            _tb20l_severity(item),
            _tb20l_corr(item),
            _tb20l_json.dumps(item.get("data") or {}, ensure_ascii=False, sort_keys=True),
        ]).lower()
    except Exception:
        return str(item).lower()


def _tb20l_format_ts(value: _Tb20lAny) -> str:
    try:
        import datetime as _dt
        ts = float(value or 0)
        if ts > 10_000_000_000:
            ts /= 1000.0
        return _dt.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return "-"


def format_log_line(item: dict[str, _Tb20lAny]) -> str:
    item = _tb20l_dict(item)
    code = str(item.get("code") or "-")
    data = _tb20l_dict(item.get("data"))
    message = str(item.get("message") or f"{code} message")
    return f"{_tb20l_format_ts(item.get('ts'))} | {_tb20l_level(item.get('level')):<5} | {_tb20l_event_category(item):<8} | {_tb20l_severity(item):<7} | {code:<22} | corr={_tb20l_corr(item)} | {message} | {data}"


def build_audit_query_path(*, limit: int = 50, order: str = "desc", level: _Tb20lAny = None, code: _Tb20lAny = None, code_prefix: _Tb20lAny = None, contains: _Tb20lAny = None, q: _Tb20lAny = None, category: _Tb20lAny = None, severity: _Tb20lAny = None, correlation: _Tb20lAny = None, since_ts: _Tb20lAny = None, until_ts: _Tb20lAny = None, offset: _Tb20lAny = None, cursor: _Tb20lAny = None, **_: _Tb20lAny) -> str:
    params: dict[str, _Tb20lAny] = {"limit": int(limit), "order": str(order or "desc").lower()}
    if not _tb20l_is_all(level): params["level"] = _tb20l_level(level)
    if not _tb20l_is_all(code): params["code"] = str(code).strip().upper()
    if not _tb20l_is_all(code_prefix): params["code_prefix"] = str(code_prefix).strip().upper()
    if not _tb20l_is_all(category): params["category"] = str(category).strip()
    if not _tb20l_is_all(severity): params["severity"] = str(severity).strip().lower()
    if not _tb20l_is_all(correlation): params["correlation"] = str(correlation).strip()
    query = q if not _tb20l_is_all(q) else contains
    if not _tb20l_is_all(query): params["q"] = str(query).strip()
    if since_ts not in (None, ""): params["since_ts"] = since_ts
    if until_ts not in (None, ""): params["until_ts"] = until_ts
    if offset not in (None, ""): params["offset"] = int(float(offset))
    if cursor not in (None, ""): params["cursor"] = str(cursor)
    return "/events/audit?" + _tb20l_urlencode(params)


def filter_audit_events(events: _Tb20lAny, category: _Tb20lAny = "All", severity: _Tb20lAny = "All", correlation: _Tb20lAny = None, text: _Tb20lAny = None, *, level: _Tb20lAny = None, code: _Tb20lAny = None, code_prefix: _Tb20lAny = None, contains: _Tb20lAny = None, q: _Tb20lAny = None, limit: _Tb20lAny = None, offset: _Tb20lAny = 0, order: str = "desc", **_: _Tb20lAny) -> list[dict[str, _Tb20lAny]]:
    filtered = [dict(i) for i in _tb20l_list(events) if isinstance(i, dict)]
    if not _tb20l_is_all(category):
        wanted = str(category).strip().lower()
        filtered = [i for i in filtered if _tb20l_event_category(i).lower() == wanted]
    if not _tb20l_is_all(severity):
        wanted = str(severity).strip().lower()
        filtered = [i for i in filtered if _tb20l_severity(i) == wanted]
    if not _tb20l_is_all(correlation):
        wanted = str(correlation).strip().lower()
        filtered = [i for i in filtered if wanted in _tb20l_corr(i).lower() or wanted in _tb20l_blob(i)]
    query = q if not _tb20l_is_all(q) else contains if not _tb20l_is_all(contains) else text
    if not _tb20l_is_all(query):
        needle = str(query).strip().lower()
        filtered = [i for i in filtered if needle in _tb20l_blob(i)]
    if not _tb20l_is_all(level):
        wanted = _tb20l_level(level)
        filtered = [i for i in filtered if _tb20l_level(i.get("level")) == wanted]
    if not _tb20l_is_all(code):
        wanted = str(code).strip().upper()
        filtered = [i for i in filtered if str(i.get("code") or "").upper() == wanted]
    if not _tb20l_is_all(code_prefix):
        prefix = str(code_prefix).strip().upper()
        filtered = [i for i in filtered if str(i.get("code") or "").upper().startswith(prefix)]
    filtered.sort(key=lambda i: _tb20l_float(i.get("ts")), reverse=str(order or "desc").lower() != "asc")
    start = max(0, _tb20l_int(offset, 0))
    if limit is None:
        return filtered[start:]
    return filtered[start:start + max(0, _tb20l_int(limit, len(filtered)))]


def build_audit_summary_text(payload: _Tb20lAny = None, logs: _Tb20lAny = None) -> str:
    if isinstance(payload, list):
        events = [dict(i) for i in payload if isinstance(i, dict)]
        total = len(events)
    else:
        data = _tb20l_dict(payload)
        raw = logs if logs is not None else data.get("events") or data.get("items") or data.get("logs") or data.get("filtered_events") or data.get("latest_events") or []
        events = [dict(i) for i in _tb20l_list(raw) if isinstance(i, dict)]
        total = _tb20l_int(data.get("total", data.get("total_events", len(events))), len(events))
    cats: dict[str, int] = {}
    sevs: dict[str, int] = {}
    levels: dict[str, int] = {}
    codes: dict[str, int] = {}
    warn = err = 0
    for i in events:
        cat = _tb20l_event_category(i); sev = _tb20l_severity(i); lvl = _tb20l_level(i.get("level")); code = str(i.get("code") or "-")
        cats[cat] = cats.get(cat, 0) + 1
        sevs[sev] = sevs.get(sev, 0) + 1
        levels[lvl] = levels.get(lvl, 0) + 1
        codes[code] = codes.get(code, 0) + 1
        if sev == "warning" or lvl == "WARN": warn += 1
        if sev == "error" or lvl in {"ERROR", "CRITICAL"}: err += 1
    fmt = lambda d: ", ".join(f"{k}:{v}" for k, v in sorted(d.items())) if d else "-"
    top = ", ".join(f"{k}:{v}" for k, v in sorted(codes.items(), key=lambda kv: (-kv[1], kv[0]))[:8]) if codes else "-"
    return "\n".join([
        "Audit Viewer",
        "------------",
        f"Contract        : {AUDIT_VIEWER_CONTRACT_VERSION}",
        f"Total events    : {total}",
        f"Rendered count  : {len(events)}",
        f"Filtered events : {len(events)}",
        f"Warnings/errors : {warn} / {err}",
        f"Categories      : {fmt(cats)}",
        f"Severities      : {fmt(sevs)}",
        f"Codes           : {fmt(codes)}",
        f"Top codes       : {top}",
    ])


def _tb20l_collect_events(app: _Tb20lAny) -> list[dict[str, _Tb20lAny]]:
    for name in ("_audit_events", "_last_audit_events", "audit_events", "_log_items", "_last_logs", "logs", "_logs"):
        value = _tb20l_safe_getattr(app, name, None)
        if isinstance(value, list):
            return [dict(i) for i in value if isinstance(i, dict)]
    getter = _tb20l_safe_getattr(app, "api_get", None)
    if callable(getter):
        try:
            payload = getter("/events/audit", timeout=2.0)
            if isinstance(payload, list):
                return [dict(i) for i in payload if isinstance(i, dict)]
            if isinstance(payload, dict):
                raw = payload.get("events") or payload.get("items") or payload.get("logs") or []
                return [dict(i) for i in raw if isinstance(i, dict)]
        except Exception:
            pass
    return []


def _tb20l_filter_value(app: _Tb20lAny, *names: str, default: _Tb20lAny = None) -> _Tb20lAny:
    for name in names:
        obj = _tb20l_safe_getattr(app, name, None)
        if obj is not None:
            return _tb20l_widget_value(obj, obj)
    return default


def _tb20l_render_logs(self: _Tb20lAny) -> None:
    events = _tb20l_collect_events(self)
    category = _tb20l_filter_value(self, "audit_category_var", "audit_category_filter", default="All")
    severity = _tb20l_filter_value(self, "audit_severity_var", "audit_severity_filter", default="All")
    correlation = _tb20l_filter_value(self, "audit_correlation_var", "audit_correlation_filter", default=None)
    text = _tb20l_filter_value(self, "audit_search_var", "audit_query_var", "audit_text_var", "audit_search_filter", default=None)
    filtered = filter_audit_events(events, category, severity, correlation, text)
    _tb20l_app_set_text(self, "audit_box", "\n".join(format_log_line(i) for i in filtered))
    _tb20l_app_set_text(self, "audit_summary_box", build_audit_summary_text({"total": len(events)}, filtered))


def _tb20l_button_style(enabled: bool) -> dict[str, _Tb20lAny]:
    return {"state": "normal" if enabled else "disabled", "fg_color": ("#3B8ED0", "#1F6AA5") if enabled else ("#8C8C8C", "#5F5F5F")}


def _tb20l_apply_health_aware_controls(self: _Tb20lAny, status: dict[str, _Tb20lAny] | None = None) -> None:
    status = _tb20l_dict(status or _tb20l_safe_getattr(self, "_last_status", {}))
    controls = build_operator_control_state(status, connected=_tb20l_bool(_tb20l_safe_getattr(self, "_last_connected", True)))
    try: self._last_operator_control_state = controls
    except Exception: pass
    mapping = {"btn_force_buy": "force_buy", "btn_force_sell": "force_sell", "btn_cancel_pending": "cancel_pending", "btn_stop": "stop", "btn_start": "start"}
    for attr, key in mapping.items():
        _tb20l_config(_tb20l_safe_getattr(self, attr, None), **_tb20l_button_style(bool(controls.get(key))))
    for attr in ("controls_hint", "operator_hint", "operator_hint_label", "lbl_operator_hint", "lbl_control_hint"):
        _tb20l_config(_tb20l_safe_getattr(self, attr, None), text=str(controls.get("hint") or ""))


def _tb20l_endpoint_action(path: str) -> str | None:
    raw = str(path or "").lower().replace("_", "-")
    if "force-buy" in raw: return "force_buy"
    if "force-sell" in raw: return "force_sell"
    if "cancel" in raw: return "cancel_pending"
    return None


def _tb20l_api_post(self: _Tb20lAny, path: str, payload: dict[str, _Tb20lAny] | None = None, **kwargs: _Tb20lAny) -> bool:
    action = _tb20l_endpoint_action(path)
    controls = _tb20l_dict(_tb20l_safe_getattr(self, "_last_operator_control_state", {}))
    if not controls:
        controls = build_operator_control_state(_tb20l_dict(_tb20l_safe_getattr(self, "_last_status", {})), connected=_tb20l_bool(_tb20l_safe_getattr(self, "_last_connected", True)))
    if action and controls.get(action) is not True:
        return False
    raw_post = _tb20l_safe_getattr(self, "api_post", None)
    if callable(raw_post):
        try:
            raw_post(path, payload or {}, **kwargs)
        except Exception:
            return False
    return True


def _tb20l_closed_trades(events: list[dict[str, _Tb20lAny]]) -> list[dict[str, _Tb20lAny]]:
    out = []
    for item in events:
        if str(item.get("code") or "").upper() == "POSITION_CLOSED":
            data = _tb20l_dict(item.get("data"))
            out.append({"symbol": data.get("symbol") or item.get("symbol") or "ETHUSDT", "pnl": _tb20l_float(data.get("pnl", item.get("pnl"))), "ts": _tb20l_float(item.get("ts"))})
    return out


def _tb20l_wlbe(trades: list[dict[str, _Tb20lAny]]) -> tuple[int, int, int]:
    w = l = b = 0
    for t in trades:
        pnl = _tb20l_float(t.get("pnl"))
        if pnl > 1e-9: w += 1
        elif pnl < -1e-9: l += 1
        else: b += 1
    return w, l, b


def _tb20l_trade_list(trades: list[dict[str, _Tb20lAny]]) -> str:
    return " / ".join(f"{t.get('symbol') or 'ETHUSDT'} {_tb20l_float(t.get('pnl')):.6f}" for t in trades) or "-"


def _tb20l_health_line(health: dict[str, _Tb20lAny]) -> str:
    ok = lambda v: "OK" if str(v or "HEALTHY").upper() in {"HEALTHY", "OK"} else str(v)
    return f"{ok(health.get('account_consistency'))}/{ok(health.get('position_consistency'))}/{ok(health.get('pending_consistency'))}"


def _tb20l_render_session_summary(self: _Tb20lAny, status: dict[str, _Tb20lAny] | None = None) -> None:
    status = _tb20l_dict(status or _tb20l_safe_getattr(self, "_last_status", {}))
    events = [dict(i) for i in _tb20l_list(_tb20l_safe_getattr(self, "_log_items", None) or _tb20l_safe_getattr(self, "_last_logs", None)) if isinstance(i, dict)]
    session = _tb20l_dict(status.get("session")); risk = _tb20l_dict(status.get("risk_snapshot")); ai = _tb20l_dict(status.get("ai_snapshot")); health = _tb20l_dict(status.get("health_snapshot"))
    daily_count = _tb20l_int(session.get("daily_trade_count", risk.get("daily_trade_count", 0)))
    closed_all = _tb20l_closed_trades(events)
    reset_ts = None
    for item in events:
        if str(item.get("code") or "").upper() == "RISK_STATS_RESET":
            reset_ts = _tb20l_float(item.get("ts"))
    if reset_ts is not None:
        scoped = [t for t in closed_all if _tb20l_float(t.get("ts")) > reset_ts]
        today = True
    else:
        scoped = closed_all
        today = daily_count == len(scoped)
    wins, losses, be = _tb20l_wlbe(scoped)
    tracked_pnl = sum(_tb20l_float(t.get("pnl")) for t in scoped)
    warnings = [i for i in events if _tb20l_level(i.get("level")) in {"WARN", "ERROR", "CRITICAL"}]
    last_warning = str(warnings[-1].get("code")) if warnings else "-"
    confidence = ai.get("confidence")
    confidence_text = "-" if confidence is None else f"%{_tb20l_float(confidence) * 100.0:.1f}" if abs(_tb20l_float(confidence)) <= 1 else f"%{_tb20l_float(confidence):.1f}"
    if today:
        scope_note = "-" if daily_count == len(scoped) else f"partial log scope ({len(scoped)}/{daily_count})"
        wl = "Today W/L/BE    "
        tr = "Today trades    "
    else:
        scope_note = f"partial log scope ({len(scoped)}/{daily_count})" if daily_count != len(scoped) else "-"
        wl = "Tracked W/L/BE  "
        tr = "Tracked trades  "
    lines = [
        f"Current signal  : {status.get('last_signal', '-')}",
        f"Signal reason   : {status.get('signal_reason', '-')}",
        f"Trend           : {status.get('trend', '-')}",
        f"Tracked PnL     : {tracked_pnl:.6f}",
        f"Trades today    : {daily_count}",
        f"{wl}: {wins}/{losses}/{be}",
        f"{tr}: {_tb20l_trade_list(scoped)}",
    ]
    if today:
        lines.append(f"Recent hist.    : {_tb20l_trade_list(closed_all[-3:])}")
    lines.extend([
        f"Last warning    : {last_warning}",
        f"Health          : {_tb20l_health_line(health)}",
        f"Model           : {ai.get('model_path', '-')}",
        f"Confidence      : {confidence_text}",
        f"Scope note      : {scope_note}",
    ])
    _tb20l_app_set_text(self, "log_box", "\n".join(lines))


def _tb20l_render_event_timeline(self: _Tb20lAny) -> None:
    events = [dict(i) for i in _tb20l_list(_tb20l_safe_getattr(self, "_log_items", None) or _tb20l_safe_getattr(self, "_last_logs", None)) if isinstance(i, dict)]
    category = _tb20l_safe_getattr(self, "_event_filter_value", None)
    if _tb20l_is_all(category):
        category = _tb20l_widget_value(_tb20l_safe_getattr(self, "event_filter", None), "All")
    filtered = filter_audit_events(events, category=category, order="asc") if not _tb20l_is_all(category) else filter_audit_events(events, order="asc")
    _tb20l_app_set_text(self, "event_box", "\n".join(format_log_line(i) for i in filtered))
    _tb20l_config(_tb20l_safe_getattr(self, "event_count_label", None), text=f"{category}: {len(filtered)} event" if not _tb20l_is_all(category) else f"All: {len(filtered)} event")


def _tb20l_render_status(self: _Tb20lAny, status: dict[str, _Tb20lAny]) -> None:
    status = _tb20l_dict(status)
    health = _tb20l_dict(status.get("health_snapshot"))
    risk = _tb20l_dict(status.get("risk_snapshot") or status.get("session"))
    ai = _tb20l_dict(status.get("ai_snapshot"))
    position = _tb20l_status_position(status)
    pending = _tb20l_status_pending(status)
    balances = _tb20l_dict(status.get("balances"))
    ok = lambda v: "OK" if str(v or "HEALTHY").upper() in {"HEALTHY", "OK"} else str(v)
    status_text = "\n".join([
        f"Account         : {ok(health.get('account_consistency'))}",
        f"Position health : {ok(health.get('position_consistency'))}",
        f"Pending health  : {ok(health.get('pending_consistency'))}",
        f"Current signal  : {status.get('last_signal', '-')}",
        f"Signal reason   : {status.get('signal_reason', '-')}",
        f"Trend           : {status.get('trend', '-')}",
        "",
        build_position_management_text({"position_snapshot": position}),
    ])
    _tb20l_app_set_text(self, "status_box", status_text)
    _tb20l_app_set_text(self, "risk_box", "\n".join([
        f"Daily PnL       : {_tb20l_float(risk.get('daily_realized_pnl', 0.0)):.6f}",
        f"Daily trades    : {_tb20l_int(risk.get('daily_trade_count', 0))}",
        f"Consec losses   : {_tb20l_int(risk.get('consecutive_losses', 0))}",
        f"Safe mode       : {_tb20l_bool(risk.get('safe_mode'))}",
        f"Kill switch     : {_tb20l_bool(risk.get('kill_switch_active'))}",
    ]))
    _tb20l_app_set_text(self, "position_box", build_position_management_text({"position_snapshot": position}))
    conf = ai.get("confidence")
    conf_text = "-" if conf is None else f"%{_tb20l_float(conf) * 100.0:.1f}" if abs(_tb20l_float(conf)) <= 1 else f"%{_tb20l_float(conf):.1f}"
    _tb20l_app_set_text(self, "ai_box", "\n".join([f"AI enabled      : {_tb20l_bool(ai.get('enabled'))}", f"Provider        : {ai.get('provider') or ai.get('mode') or '-'}", f"Model           : {ai.get('model_path', '-')}", f"Confidence      : {conf_text}", f"Trend           : {ai.get('trend', '-')}"]))
    _tb20l_app_set_text(self, "pending_box", "\n".join([f"Pending order   : {'YES' if _tb20l_bool(pending.get('present')) else 'NO'}", f"Side            : {pending.get('side') or '-'}", f"Submitted qty   : {_tb20l_fmt(pending.get('submitted_qty') or pending.get('qty'), 8)}", f"Executed qty    : {_tb20l_fmt(pending.get('executed_qty'), 8)}", f"Remaining qty   : {_tb20l_fmt(pending.get('remaining_qty'), 8)}", f"Status          : {pending.get('status') or '-'}"]))
    symbol = status.get("symbol") or "ETHUSDT"
    base_asset = str(symbol)[:-4] if len(str(symbol)) > 4 else ""
    base = _tb20l_dict(balances.get(base_asset)) if base_asset else {}
    quote = _tb20l_dict(balances.get("USDT"))
    _tb20l_app_set_text(self, "log_box", "\n".join([f"Health          : {_tb20l_health_line(health)}", f"Model           : {ai.get('model_path', '-')}", f"Base balance    : {_tb20l_fmt(base.get('free'), 8)}", f"Quote balance   : {_tb20l_fmt(quote.get('free'), 8)}"]))
    _tb20l_apply_health_aware_controls(self, status)


def _tb20l_set_offline_ui(self: _Tb20lAny, reason: str = "-") -> None:
    config_name = getattr(_tb20l_safe_getattr(self, "config_path", None), "name", "config.local.yaml")
    text = f"Backend offline.\nReason: {reason}\n\nConfig: {config_name}"
    for attr in ("status_box", "log_box", "ai_box", "risk_box", "position_box", "pending_box"):
        _tb20l_app_set_text(self, attr, text)
    _tb20l_config(_tb20l_safe_getattr(self, "lbl_connection", None), text="Backend: OFFLINE", text_color=("red", "orange"))


def _tb20l_poll_health_and_status(self: _Tb20lAny) -> None:
    try:
        health = self.api_get("/health", timeout=1.0)
    except Exception as exc:
        try: self._last_connected = False
        except Exception: pass
        _tb20l_set_offline_ui(self, str(exc))
        return
    try: self._last_connected = bool(_tb20l_dict(health).get("ok"))
    except Exception: self._last_connected = True
    _tb20l_config(_tb20l_safe_getattr(self, "lbl_connection", None), text="Backend: ONLINE", text_color=("green", "light green"))
    _tb20l_config(_tb20l_safe_getattr(self, "lbl_symbol", None), text=f"Sembol: {_tb20l_dict(health).get('symbol', '-')}")
    try:
        status = self.api_get("/status", timeout=2.0)
    except Exception as exc:
        try: self._last_connected = True
        except Exception: pass
        _tb20l_config(_tb20l_safe_getattr(self, "lbl_state", None), text="Durum: STATUS ERROR")
        _tb20l_app_set_text(self, "status_box", f"Backend online, status payload alınamadı.\nReason: {exc}")
        return
    try: self._last_status = status
    except Exception: pass
    _tb20l_render_status(self, status)


def _tb20l_extract_training_output_path(self: _Tb20lAny, line: str) -> str | None:
    raw = str(line or "").strip()
    if not raw:
        return None
    payload = None
    try:
        payload = _tb20l_json.loads(raw)
    except Exception:
        try:
            payload = _tb20l_ast.literal_eval(raw)
        except Exception:
            payload = None
    if isinstance(payload, dict):
        for key in ("model_path", "output_path", "output", "path", "model"):
            value = payload.get(key)
            if value:
                return str(value)
    for marker in ("model_path=", "output_path=", "output="):
        if marker in raw:
            return raw.split(marker, 1)[1].strip().strip("'\",").split()[0]
    return None


def _tb20l_patch_dashboard_classes() -> None:
    methods = {
        "_render_logs": _tb20l_render_logs,
        "_apply_health_aware_controls": _tb20l_apply_health_aware_controls,
        "_api_post": _tb20l_api_post,
        "_render_event_timeline": _tb20l_render_event_timeline,
        "_render_session_summary": _tb20l_render_session_summary,
        "_render_status": _tb20l_render_status,
        "_set_offline_ui": _tb20l_set_offline_ui,
        "_poll_health_and_status": _tb20l_poll_health_and_status,
        "_extract_training_output_path": _tb20l_extract_training_output_path,
    }
    for _name, _obj in list(globals().items()):
        if isinstance(_obj, type) and ("Dashboard" in _name or _name.endswith("App")):
            for _m, _fn in methods.items():
                try:
                    setattr(_obj, _m, _fn)
                except Exception:
                    pass


_tb20l_patch_dashboard_classes()
# END 4B.4.3.6.6.20L DASHBOARD CONTRACT HARD RESET
'''


def patch_text(text: str) -> str:
    cleaned = re.sub(START_RE, "", text, flags=re.DOTALL)
    return cleaned.rstrip() + "\n\n" + COMPAT_BLOCK.strip() + "\n"


def patch_dashboard(root: Path) -> None:
    path = root / "src" / "tradebot" / "ui" / "dashboard.py"
    if not path.exists():
        raise RuntimeError(f"dashboard.py not found: {path}")
    path.write_text(patch_text(path.read_text(encoding="utf-8")), encoding="utf-8")


def patch_engine(root: Path) -> None:
    path = root / "src" / "tradebot" / "engine.py"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"status\['contract_version'\]\s*=\s*['\"]4B\.4\.3\.6\.6\.\d+['\"]", "status['contract_version'] = '4B.4.3.6.6.20'", text)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    root = Path.cwd()
    patch_dashboard(root)
    patch_engine(root)
    dashboard = (root / "src" / "tradebot" / "ui" / "dashboard.py").read_text(encoding="utf-8")
    checks = {
        "position_is_dust_key": '"position_is_dust"' in dashboard,
        "stop_loss_text": "Stop loss" in dashboard,
        "force_buy_hint": "Force BUY" in dashboard,
        "button_fg_color": "fg_color" in dashboard,
        "named_set_text": "status_box" in dashboard and "_tb20l_app_set_text" in dashboard,
        "audit_orders_summary": "Categories" in dashboard and "Warnings/errors" in dashboard,
        "offline_english": "Backend offline." in dashboard,
        "status_degrade_exact": "Backend online, status payload alınamadı." in dashboard,
        "literal_eval_training_parser": "literal_eval" in dashboard,
    }
    print("4B.4.3.6.6.20l dashboard contract hard reset applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if not all(checks.values()):
        raise RuntimeError(f"20l verification failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
