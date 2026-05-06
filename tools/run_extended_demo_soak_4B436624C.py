"""4B.4.3.6.6.24C extended demo soak + model gate reporting.

Observation-only tool. It performs GET requests against the local API, records
/status and /health snapshots, builds a model-gate timeline, and produces three
report families:

- 4B436624C_extended_demo_soak_*.json/.md
- 4B436624C_model_gate_timeline_*.json/.md
- 4B436624C_pre_paper_readiness_*.json/.md

It never submits orders, never toggles settings, and never arms live trading.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:  # keep the tool usable even when imported in minimal test environments
    from tradebot.model_quality_gate import build_runtime_model_quality_gate
except Exception:  # pragma: no cover - defensive fallback for operator tooling
    build_runtime_model_quality_gate = None  # type: ignore[assignment]

PHASE = "4B.4.3.6.6.24C"
CONTRACT_VERSION = "4B.4.3.6.6.24C"
REPORT_PREFIX = "4B436624C_extended_demo_soak"
TIMELINE_PREFIX = "4B436624C_model_gate_timeline"
READINESS_PREFIX = "4B436624C_pre_paper_readiness"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
SAFE_EXECUTION_MODES = {"live_demo", "paper", "dry_run"}
SAFE_MARKET_TYPES = {"spot_demo", "paper", "dry_run", "", None}
PASSABLE_GATE_DECISIONS = {"PASS"}
REVIEW_GATE_DECISIONS = {"WARN", "WARMING_UP"}
FAIL_REASONS = {
    "HEALTH_REQUEST_FAILED",
    "STATUS_REQUEST_FAILED",
    "HEALTH_NOT_OK",
    "API_NOT_RUNNING",
    "BOOTSTRAP_FAILED",
    "DEGRADED_RUNTIME",
    "REAL_LIVE_ARMED",
    "LIVE_REAL_CONFIRM_ENABLED",
    "UNSAFE_EXECUTION_MODE",
    "UNSAFE_MARKET_TYPE",
    "CONFIG_NOT_SAFE_TO_TRADE",
    "CONFIG_CRITICAL_WARNING",
    "ACCOUNT_HEALTH_ANOMALY",
    "MODEL_GATE_BLOCK",
    "MODEL_GATE_MISSING",
    "MODEL_GATE_LIVE_DEMO_NOT_ALLOWED",
    "DIAGNOSTICS_CRITICAL",
}
WARNING_REASONS = {
    "CONFIG_NOT_SAFE_TO_AUTO_TRADE",
    "WS_NOT_CONNECTED",
    "MODEL_GATE_WARN",
    "MODEL_QUALITY_WARNING",
    "LOW_SAMPLE_COUNT",
    "POSITION_PRESENT",
    "PENDING_PRESENT",
    "DIAGNOSTICS_WARNING",
}


class ExtendedSoakHttpError(RuntimeError):
    """Raised when a GET-only observation request fails."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def compact(value: Any, max_len: int = 500) -> str:
    text = str(value)
    return text if len(text) <= max_len else text[:max_len] + "..."


def boolish(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ok", "pass", "passed", "connected"}
    return bool(value)


def get_path(data: Any, path: str, default: Any = None) -> Any:
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part, default)
        else:
            return default
    return cur


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def http_get_json(base_url: str, path: str, timeout_sec: float = 5.0) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return {}
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else {"value": payload}
    except urllib.error.HTTPError as exc:
        raise ExtendedSoakHttpError(f"HTTP {exc.code}: {exc.reason}") from exc
    except Exception as exc:
        raise ExtendedSoakHttpError(str(exc)) from exc


def summarize_health(health: dict[str, Any] | None, error: str | None = None) -> dict[str, Any]:
    if error:
        return {"ok": False, "error": error, "degraded": True}
    payload = health or {}
    return {
        "ok": boolish(payload.get("ok")),
        "running": boolish(payload.get("running")),
        "engine_running": boolish(payload.get("engine_running"), default=boolish(payload.get("running"))),
        "degraded": boolish(payload.get("degraded")),
        "bootstrap_ok": boolish(payload.get("bootstrap_ok"), default=True),
        "bootstrap_error": payload.get("bootstrap_error"),
        "start_error": payload.get("start_error"),
        "symbol": payload.get("symbol"),
    }


def synthesize_or_extract_gate(status_payload: dict[str, Any]) -> dict[str, Any]:
    gate = status_payload.get("model_quality_gate_snapshot")
    if isinstance(gate, dict) and gate:
        return dict(gate)
    model_quality = status_payload.get("model_quality_snapshot")
    if isinstance(model_quality, dict) and build_runtime_model_quality_gate is not None:
        try:
            generated = build_runtime_model_quality_gate(model_quality)
            generated["source"] = "synthesized_from_model_quality_snapshot"
            return generated
        except Exception as exc:  # pragma: no cover - defensive operator path
            return {
                "decision": "BLOCK",
                "ok": False,
                "live_demo_allowed": False,
                "live_real_allowed": False,
                "reason_codes": ["MODEL_GATE_SYNTHESIS_FAILED"],
                "error": compact(exc),
            }
    return {
        "decision": "BLOCK",
        "ok": False,
        "live_demo_allowed": False,
        "live_real_allowed": False,
        "reason_codes": ["MODEL_QUALITY_GATE_MISSING"],
        "metrics": {},
    }


def summarize_status(status: dict[str, Any] | None, error: str | None = None) -> dict[str, Any]:
    if error:
        return {"ok": False, "error": error}
    payload = status or {}
    config = payload.get("config_safety_snapshot") if isinstance(payload.get("config_safety_snapshot"), dict) else {}
    health = payload.get("health_snapshot") if isinstance(payload.get("health_snapshot"), dict) else {}
    model_quality = payload.get("model_quality_snapshot") if isinstance(payload.get("model_quality_snapshot"), dict) else {}
    diagnostics = payload.get("diagnostics_snapshot") if isinstance(payload.get("diagnostics_snapshot"), dict) else {}
    performance = payload.get("performance_snapshot") if isinstance(payload.get("performance_snapshot"), dict) else {}
    position = payload.get("position_snapshot") if isinstance(payload.get("position_snapshot"), dict) else {}
    pending = payload.get("pending_snapshot") if isinstance(payload.get("pending_snapshot"), dict) else {}
    gate = synthesize_or_extract_gate(payload)
    return {
        "ok": True,
        "contract_version": payload.get("contract_version"),
        "state": str(payload.get("state") or ""),
        "ws_status": str(payload.get("ws_status") or ""),
        "symbol": payload.get("symbol"),
        "last_signal": payload.get("last_signal"),
        "last_signal_confidence": payload.get("last_signal_confidence"),
        "config": {
            "profile_mode": config.get("profile_mode"),
            "execution_mode": config.get("execution_mode") or payload.get("execution_mode"),
            "market_type": config.get("market_type") or payload.get("market_type"),
            "safe_to_trade": config.get("safe_to_trade"),
            "safe_to_auto_trade": config.get("safe_to_auto_trade"),
            "live_trading_armed": config.get("live_trading_armed"),
            "live_real_double_confirm": config.get("live_real_double_confirm"),
            "auto_trade_on_signal": config.get("auto_trade_on_signal"),
            "critical_warnings": config.get("critical_warnings") or [],
            "warnings": config.get("warnings") or [],
        },
        "health_snapshot": {
            "account_consistency": health.get("account_consistency"),
            "position_consistency": health.get("position_consistency"),
            "pending_consistency": health.get("pending_consistency"),
            "active_anomaly_code": health.get("active_anomaly_code"),
        },
        "model_quality": {
            "enabled": model_quality.get("enabled"),
            "sample_count": model_quality.get("sample_count"),
            "severity": model_quality.get("severity"),
            "recommendation": model_quality.get("recommendation"),
            "reason_codes": model_quality.get("reason_codes") or [],
        },
        "model_quality_gate": gate,
        "diagnostics": {
            "severity": diagnostics.get("severity"),
            "ready_to_operate": diagnostics.get("ready_to_operate"),
            "reason_codes": diagnostics.get("reason_codes") or [],
        },
        "performance": {
            "closed_trade_count": performance.get("closed_trade_count"),
            "realized_pnl": performance.get("realized_pnl"),
            "win_rate_pct": performance.get("win_rate_pct"),
            "profit_factor": performance.get("profit_factor"),
            "guard_counts": performance.get("guard_counts") or {},
        },
        "position": {
            "present": boolish(position.get("present")),
            "qty": position.get("qty"),
            "source": position.get("source"),
        },
        "pending": {
            "present": boolish(pending.get("present")),
            "side": pending.get("side"),
            "status": pending.get("status"),
        },
    }


def evaluate_sample(health: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if health.get("error"):
        reasons.append("HEALTH_REQUEST_FAILED")
    if status.get("error"):
        reasons.append("STATUS_REQUEST_FAILED")
    if not boolish(health.get("ok")):
        reasons.append("HEALTH_NOT_OK")
    if not boolish(health.get("running")):
        reasons.append("API_NOT_RUNNING")
    if health.get("bootstrap_ok") is False or health.get("bootstrap_error") or health.get("start_error"):
        reasons.append("BOOTSTRAP_FAILED")
    if boolish(health.get("degraded")):
        reasons.append("DEGRADED_RUNTIME")
    if status.get("ok"):
        ws_status = str(status.get("ws_status") or "").upper()
        if ws_status not in {"CONNECTED", "WS CONNECTED"}:
            reasons.append("WS_NOT_CONNECTED")
        config = status.get("config") or {}
        execution_mode = str(config.get("execution_mode") or "").strip().lower()
        market_type_norm = str(config.get("market_type") or "").strip().lower()
        if execution_mode not in SAFE_EXECUTION_MODES:
            reasons.append("UNSAFE_EXECUTION_MODE")
        if market_type_norm not in SAFE_MARKET_TYPES:
            reasons.append("UNSAFE_MARKET_TYPE")
        if boolish(config.get("live_trading_armed")):
            reasons.append("REAL_LIVE_ARMED")
        if boolish(config.get("live_real_double_confirm")):
            reasons.append("LIVE_REAL_CONFIRM_ENABLED")
        if config.get("safe_to_trade") is False:
            reasons.append("CONFIG_NOT_SAFE_TO_TRADE")
        if config.get("safe_to_auto_trade") is False:
            reasons.append("CONFIG_NOT_SAFE_TO_AUTO_TRADE")
        if config.get("critical_warnings"):
            reasons.append("CONFIG_CRITICAL_WARNING")
        health_snapshot = status.get("health_snapshot") or {}
        if health_snapshot.get("active_anomaly_code"):
            reasons.append("ACCOUNT_HEALTH_ANOMALY")
        for key in ("account_consistency", "position_consistency", "pending_consistency"):
            value = str(health_snapshot.get(key) or "").upper()
            if value and value not in {"HEALTHY", "OK"}:
                reasons.append("ACCOUNT_HEALTH_ANOMALY")
                break
        gate = status.get("model_quality_gate") or {}
        gate_decision = str(gate.get("decision") or "").upper()
        if not gate_decision:
            reasons.append("MODEL_GATE_MISSING")
        elif gate_decision == "BLOCK":
            reasons.append("MODEL_GATE_BLOCK")
        elif gate_decision in REVIEW_GATE_DECISIONS:
            reasons.append("MODEL_GATE_WARN")
        if gate.get("live_demo_allowed") is False:
            reasons.append("MODEL_GATE_LIVE_DEMO_NOT_ALLOWED")
        model = status.get("model_quality") or {}
        severity = str(model.get("severity") or "").lower()
        if severity in {"warning", "warn", "degraded"}:
            reasons.append("MODEL_QUALITY_WARNING")
        diagnostics = status.get("diagnostics") or {}
        diag_severity = str(diagnostics.get("severity") or "").lower()
        if diag_severity == "critical" or diagnostics.get("ready_to_operate") is False:
            reasons.append("DIAGNOSTICS_CRITICAL")
        elif diag_severity in {"warning", "warn", "degraded"}:
            reasons.append("DIAGNOSTICS_WARNING")
        if get_path(status, "position.present", False):
            reasons.append("POSITION_PRESENT")
        if get_path(status, "pending.present", False):
            reasons.append("PENDING_PRESENT")
    fail = any(reason in FAIL_REASONS for reason in reasons)
    warn = any(reason in WARNING_REASONS for reason in reasons)
    return {
        "severity": "FAIL" if fail else "WARN" if warn else "PASS",
        "reason_codes": sorted(set(reasons)),
    }


def collect_sample(
    base_url: str,
    timeout_sec: float,
    fetcher: Callable[[str, str, float], dict[str, Any]] = http_get_json,
) -> dict[str, Any]:
    health_raw: dict[str, Any] | None = None
    status_raw: dict[str, Any] | None = None
    health_error: str | None = None
    status_error: str | None = None
    try:
        health_raw = fetcher(base_url, "/health", timeout_sec)
    except Exception as exc:
        health_error = compact(exc)
    try:
        status_raw = fetcher(base_url, "/status", timeout_sec)
    except Exception as exc:
        status_error = compact(exc)
    health = summarize_health(health_raw, health_error)
    status = summarize_status(status_raw, status_error)
    return {
        "ts_utc": utc_now(),
        "health": health,
        "status": status,
        "evaluation": evaluate_sample(health, status),
    }


def _counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def build_model_gate_timeline(samples: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    decision_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    signal_counts: Counter[str] = Counter()
    hold_pct_values: list[float] = []
    action_pct_values: list[float] = []
    confidence_values: list[float] = []
    live_demo_allowed_count = 0
    live_real_allowed_count = 0

    for sample in samples:
        status = sample.get("status") or {}
        gate = status.get("model_quality_gate") or {}
        metrics = gate.get("metrics") if isinstance(gate.get("metrics"), dict) else {}
        decision = str(gate.get("decision") or "MISSING").upper()
        decision_counts[decision] += 1
        for reason in gate.get("reason_codes") or []:
            reason_counts[str(reason)] += 1
        signal = str(status.get("last_signal") or "UNKNOWN").upper()
        signal_counts[signal] += 1
        if boolish(gate.get("live_demo_allowed")):
            live_demo_allowed_count += 1
        if boolish(gate.get("live_real_allowed")):
            live_real_allowed_count += 1
        hold_pct = safe_float(metrics.get("hold_pct"))
        action_pct = safe_float(metrics.get("action_pct"))
        avg_conf = safe_float(metrics.get("avg_confidence"))
        if hold_pct is not None:
            hold_pct_values.append(hold_pct)
        if action_pct is not None:
            action_pct_values.append(action_pct)
        if avg_conf is not None:
            confidence_values.append(avg_conf)
        rows.append(
            {
                "ts_utc": sample.get("ts_utc"),
                "decision": decision,
                "live_demo_allowed": boolish(gate.get("live_demo_allowed")),
                "live_real_allowed": boolish(gate.get("live_real_allowed")),
                "reason_codes": gate.get("reason_codes") or [],
                "warnings": gate.get("warnings") or [],
                "last_signal": signal,
                "hold_pct": hold_pct,
                "action_pct": action_pct,
                "avg_confidence": avg_conf,
                "sample_count": metrics.get("sample_count"),
            }
        )

    sample_count = len(rows)
    block_count = decision_counts.get("BLOCK", 0) + decision_counts.get("MISSING", 0)
    warn_count = sum(decision_counts.get(key, 0) for key in REVIEW_GATE_DECISIONS)
    pass_count = decision_counts.get("PASS", 0)
    decision = "FAIL" if block_count else "REVIEW" if warn_count or pass_count < sample_count else "PASS"
    return {
        "contract_version": CONTRACT_VERSION,
        "phase": PHASE,
        "decision": decision,
        "sample_count": sample_count,
        "decision_counts": _counter_to_dict(decision_counts),
        "reason_counts": _counter_to_dict(reason_counts),
        "signal_counts": _counter_to_dict(signal_counts),
        "live_demo_allowed_count": live_demo_allowed_count,
        "live_real_allowed_count": live_real_allowed_count,
        "avg_hold_pct": sum(hold_pct_values) / len(hold_pct_values) if hold_pct_values else None,
        "avg_action_pct": sum(action_pct_values) / len(action_pct_values) if action_pct_values else None,
        "avg_confidence": sum(confidence_values) / len(confidence_values) if confidence_values else None,
        "first_ts_utc": rows[0]["ts_utc"] if rows else None,
        "last_ts_utc": rows[-1]["ts_utc"] if rows else None,
        "rows": rows,
    }


def aggregate_samples(samples: list[dict[str, Any]], *, min_samples: int = 1) -> dict[str, Any]:
    severity_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    ws_counts: Counter[str] = Counter()
    signal_counts: Counter[str] = Counter()
    for sample in samples:
        severity = str(get_path(sample, "evaluation.severity", "FAIL") or "FAIL").upper()
        severity_counts[severity] += 1
        for reason in get_path(sample, "evaluation.reason_codes", []) or []:
            reason_counts[str(reason)] += 1
        state_counts[str(get_path(sample, "status.state", "UNKNOWN") or "UNKNOWN")] += 1
        ws_counts[str(get_path(sample, "status.ws_status", "UNKNOWN") or "UNKNOWN")] += 1
        signal_counts[str(get_path(sample, "status.last_signal", "UNKNOWN") or "UNKNOWN").upper()] += 1
    if len(samples) < min_samples:
        reason_counts["LOW_SAMPLE_COUNT"] += 1
        severity_counts["WARN"] += 1
    decision = "FAIL" if severity_counts.get("FAIL", 0) else "REVIEW" if severity_counts.get("WARN", 0) else "PASS"
    return {
        "decision": decision,
        "sample_count": len(samples),
        "severity_counts": _counter_to_dict(severity_counts),
        "reason_counts": _counter_to_dict(reason_counts),
        "state_counts": _counter_to_dict(state_counts),
        "ws_counts": _counter_to_dict(ws_counts),
        "signal_counts": _counter_to_dict(signal_counts),
        "first_ts_utc": samples[0]["ts_utc"] if samples else None,
        "last_ts_utc": samples[-1]["ts_utc"] if samples else None,
    }


def build_pre_paper_readiness(report: dict[str, Any], timeline: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") or {}
    reason_counts = summary.get("reason_counts") or {}
    checks = {
        "observation_only": bool(report.get("observation_only")),
        "no_post_actions": bool(report.get("no_post_actions")),
        "soak_pass": summary.get("decision") == "PASS",
        "model_gate_timeline_pass": timeline.get("decision") == "PASS",
        "no_model_gate_block": int((timeline.get("decision_counts") or {}).get("BLOCK", 0) or 0) == 0,
        "model_gate_live_demo_allowed_all_samples": timeline.get("sample_count", 0) > 0
        and timeline.get("live_demo_allowed_count") == timeline.get("sample_count"),
        "no_real_live_arming": int(reason_counts.get("REAL_LIVE_ARMED", 0) or 0) == 0
        and int(reason_counts.get("LIVE_REAL_CONFIRM_ENABLED", 0) or 0) == 0,
        "no_bootstrap_or_degraded_runtime": int(reason_counts.get("BOOTSTRAP_FAILED", 0) or 0) == 0
        and int(reason_counts.get("DEGRADED_RUNTIME", 0) or 0) == 0,
        "no_api_or_ws_failure": int(reason_counts.get("HEALTH_REQUEST_FAILED", 0) or 0) == 0
        and int(reason_counts.get("STATUS_REQUEST_FAILED", 0) or 0) == 0
        and int(reason_counts.get("WS_NOT_CONNECTED", 0) or 0) == 0,
        "no_config_or_account_critical": int(reason_counts.get("CONFIG_CRITICAL_WARNING", 0) or 0) == 0
        and int(reason_counts.get("ACCOUNT_HEALTH_ANOMALY", 0) or 0) == 0,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    decision = "PASS" if not blockers else "BLOCK"
    return {
        "contract_version": CONTRACT_VERSION,
        "phase": PHASE,
        "decision": decision,
        "ready_for_paper_phase": decision == "PASS",
        "ready_for_live_real": False,
        "blockers": blockers,
        "checks": checks,
        "soak_decision": summary.get("decision"),
        "model_gate_timeline_decision": timeline.get("decision"),
        "risk_manager_note": (
            "Paper fazına geçilebilir; gerçek canlı işlem için hâlâ ayrı sınırlı canlı onay kapısı gerekir."
            if decision == "PASS"
            else "Paper fazına geçmeden önce blocker maddeleri kapatılmalıdır. Gerçek canlı işlem kesinlikle açılmamalıdır."
        ),
    }


def mark_operator_interrupt(summary: dict[str, Any]) -> dict[str, Any]:
    severity_counts = Counter(summary.get("severity_counts") or {})
    reason_counts = Counter(summary.get("reason_counts") or {})
    reason_counts["INTERRUPTED_BY_OPERATOR"] += 1
    severity_counts["WARN"] += 1
    summary["severity_counts"] = _counter_to_dict(severity_counts)
    summary["reason_counts"] = _counter_to_dict(reason_counts)
    summary["decision"] = "FAIL" if severity_counts.get("FAIL", 0) else "REVIEW"
    return summary


def run_extended_soak(
    base_url: str,
    *,
    duration_sec: float,
    interval_sec: float,
    timeout_sec: float,
    max_samples: int | None = None,
    min_samples: int = 1,
    fetcher: Callable[[str, str, float], dict[str, Any]] = http_get_json,
) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    interrupted_by_operator = False
    started = time.monotonic()
    deadline = started + max(duration_sec, 0.0)
    try:
        while True:
            samples.append(collect_sample(base_url, timeout_sec, fetcher=fetcher))
            if max_samples is not None and len(samples) >= max_samples:
                break
            if max_samples is None and time.monotonic() >= deadline:
                break
            if max_samples is not None and duration_sec <= 0:
                sleep_for = 0.0
            else:
                sleep_for = min(max(interval_sec, 0.0), max(deadline - time.monotonic(), 0.0))
            if sleep_for > 0:
                time.sleep(sleep_for)
            elif max_samples is None:
                break
    except KeyboardInterrupt:
        interrupted_by_operator = True
    summary = aggregate_samples(samples, min_samples=max(min_samples, 1))
    if interrupted_by_operator:
        summary = mark_operator_interrupt(summary)
    return {
        "phase": PHASE,
        "contract_version": CONTRACT_VERSION,
        "generated_at_utc": utc_now(),
        "base_url": base_url,
        "duration_sec_requested": duration_sec,
        "interval_sec": interval_sec,
        "timeout_sec": timeout_sec,
        "observation_only": True,
        "no_post_actions": True,
        "interrupted_by_operator": interrupted_by_operator,
        "summary": summary,
        "samples": samples,
    }


def render_soak_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        f"# {PHASE} Extended Demo Soak Report",
        "",
        f"Generated at UTC: `{report.get('generated_at_utc')}`",
        f"Contract: `{report.get('contract_version')}`",
        f"Base URL: `{report.get('base_url')}`",
        f"Decision: **{summary.get('decision')}**",
        f"Observation-only: `{report.get('observation_only')}`",
        f"No POST actions: `{report.get('no_post_actions')}`",
        "",
        "## Summary",
        "",
        f"- Sample count: `{summary.get('sample_count')}`",
        f"- Severity counts: `{summary.get('severity_counts')}`",
        f"- State counts: `{summary.get('state_counts')}`",
        f"- WS counts: `{summary.get('ws_counts')}`",
        f"- Signal counts: `{summary.get('signal_counts')}`",
        "",
        "## Reason Counts",
        "",
    ]
    reason_counts = summary.get("reason_counts") or {}
    if reason_counts:
        for reason, count in reason_counts.items():
            lines.append(f"- {reason}: `{count}`")
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Samples",
        "",
        "| # | Time UTC | Severity | State | WS | Signal | Gate | Reasons |",
        "|---:|---|---|---|---|---|---|---|",
    ])
    for idx, sample in enumerate(report.get("samples") or [], start=1):
        status = sample.get("status") or {}
        gate = status.get("model_quality_gate") or {}
        eval_ = sample.get("evaluation") or {}
        reasons = ", ".join(eval_.get("reason_codes") or []) or "-"
        lines.append(
            f"| {idx} | {sample.get('ts_utc')} | {eval_.get('severity')} | {status.get('state')} | {status.get('ws_status')} | {status.get('last_signal')} | {gate.get('decision')} | {reasons} |"
        )
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- GET-only observation tool; no order, config, arming, reload, or training calls are made.",
        "- `PASS` means pre-paper evidence improved; it is not permission for real live trading.",
        "- Any `MODEL_GATE_BLOCK` or degraded runtime must block phase transition.",
    ])
    return "\n".join(lines) + "\n"


def render_timeline_markdown(timeline: dict[str, Any]) -> str:
    lines = [
        f"# {PHASE} Model Gate Timeline",
        "",
        f"Contract: `{timeline.get('contract_version')}`",
        f"Decision: **{timeline.get('decision')}**",
        f"Sample count: `{timeline.get('sample_count')}`",
        f"Decision counts: `{timeline.get('decision_counts')}`",
        f"Reason counts: `{timeline.get('reason_counts')}`",
        f"Signal counts: `{timeline.get('signal_counts')}`",
        f"Live-demo allowed samples: `{timeline.get('live_demo_allowed_count')}`",
        f"Average HOLD pct: `{timeline.get('avg_hold_pct')}`",
        f"Average action pct: `{timeline.get('avg_action_pct')}`",
        f"Average confidence: `{timeline.get('avg_confidence')}`",
        "",
        "## Timeline",
        "",
        "| # | Time UTC | Decision | Demo allowed | Signal | HOLD % | Action % | Reasons |",
        "|---:|---|---|---|---|---:|---:|---|",
    ]
    for idx, row in enumerate(timeline.get("rows") or [], start=1):
        reasons = ", ".join(row.get("reason_codes") or []) or "-"
        lines.append(
            f"| {idx} | {row.get('ts_utc')} | {row.get('decision')} | {row.get('live_demo_allowed')} | {row.get('last_signal')} | {row.get('hold_pct')} | {row.get('action_pct')} | {reasons} |"
        )
    return "\n".join(lines) + "\n"


def render_readiness_markdown(readiness: dict[str, Any]) -> str:
    lines = [
        f"# {PHASE} Pre-paper Readiness",
        "",
        f"Decision: **{readiness.get('decision')}**",
        f"Ready for paper phase: `{readiness.get('ready_for_paper_phase')}`",
        f"Ready for live real: `{readiness.get('ready_for_live_real')}`",
        f"Soak decision: `{readiness.get('soak_decision')}`",
        f"Model gate timeline decision: `{readiness.get('model_gate_timeline_decision')}`",
        f"Risk manager note: {readiness.get('risk_manager_note')}",
        "",
        "## Checks",
        "",
    ]
    for name, ok in (readiness.get("checks") or {}).items():
        lines.append(f"- {name}: `{ok}`")
    lines.extend(["", "## Blockers", ""])
    blockers = readiness.get("blockers") or []
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def write_reports(root: Path, report: dict[str, Any]) -> dict[str, str]:
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = timestamp_slug()
    timeline = build_model_gate_timeline(report.get("samples") or [])
    readiness = build_pre_paper_readiness(report, timeline)

    outputs = {
        "soak_json": reports_dir / f"{REPORT_PREFIX}_{stamp}.json",
        "soak_md": reports_dir / f"{REPORT_PREFIX}_{stamp}.md",
        "timeline_json": reports_dir / f"{TIMELINE_PREFIX}_{stamp}.json",
        "timeline_md": reports_dir / f"{TIMELINE_PREFIX}_{stamp}.md",
        "readiness_json": reports_dir / f"{READINESS_PREFIX}_{stamp}.json",
        "readiness_md": reports_dir / f"{READINESS_PREFIX}_{stamp}.md",
    }
    outputs["soak_json"].write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    outputs["soak_md"].write_text(render_soak_markdown(report), encoding="utf-8")
    outputs["timeline_json"].write_text(json.dumps(timeline, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    outputs["timeline_md"].write_text(render_timeline_markdown(timeline), encoding="utf-8")
    outputs["readiness_json"].write_text(json.dumps(readiness, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    outputs["readiness_md"].write_text(render_readiness_markdown(readiness), encoding="utf-8")
    return {key: value.as_posix() for key, value in outputs.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 4B.4.3.6.6.24C observation-only extended demo soak checks.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--duration-min", type=float, default=240.0, help="Observation duration in minutes. Default: 240")
    parser.add_argument("--interval-sec", type=float, default=60.0, help="Seconds between samples. Default: 60")
    parser.add_argument("--timeout-sec", type=float, default=5.0)
    parser.add_argument("--max-samples", type=int, default=None, help="Optional hard cap for samples")
    parser.add_argument("--min-samples", type=int, default=30, help="Minimum expected samples before PASS")
    parser.add_argument("--once", action="store_true", help="Take one sample and exit")
    parser.add_argument("--review-ok", action="store_true", help="Exit 0 for REVIEW decision")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.once:
        duration_sec = 0.0
        max_samples = 1
        min_samples = 1
    else:
        duration_sec = max(args.duration_min, 0.0) * 60.0
        max_samples = args.max_samples
        min_samples = max(args.min_samples, 1)
    report = run_extended_soak(
        args.base_url,
        duration_sec=duration_sec,
        interval_sec=max(args.interval_sec, 1.0),
        timeout_sec=max(args.timeout_sec, 1.0),
        max_samples=max_samples,
        min_samples=min_samples,
    )
    paths = write_reports(Path.cwd(), report)
    timeline = json.loads(Path(paths["timeline_json"]).read_text(encoding="utf-8"))
    readiness = json.loads(Path(paths["readiness_json"]).read_text(encoding="utf-8"))
    summary = report["summary"]
    decision = summary["decision"]
    print(f"{PHASE} extended demo soak {decision}")
    print(f" - samples: {summary['sample_count']}")
    print(f" - severity_counts: {summary['severity_counts']}")
    print(f" - reason_counts: {summary['reason_counts']}")
    print(f" - model_gate_timeline: {timeline['decision']} {timeline['decision_counts']}")
    print(f" - pre_paper_readiness: {readiness['decision']} blockers={readiness['blockers']}")
    for key, path in paths.items():
        print(f"{key}: {path}")
    if decision == "PASS" and readiness.get("decision") == "PASS":
        return 0
    if args.review_ok and decision in {"PASS", "REVIEW"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
