"""4B.4.3.6.6.22 live-demo supervised soak test runner.

Observation-only tool. It performs GET requests against the local API, records
runtime/status/config/model/performance snapshots, and produces JSON/Markdown
reports. It never submits orders, never toggles settings, and never arms real live
trading.
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

PHASE = "4B.4.3.6.6.22"
REPORT_PREFIX = "4B436622_live_demo_soak"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
RUNTIME_ENGINE_CONTRACT_MINIMUM = "4B.4.3.6.6.12"
RELEASE_CANDIDATE_TOOLING_CONTRACT = "4B.4.3.6.6.21"
SAFE_EXECUTION_MODES = {"live_demo", "paper", "dry_run"}
SAFE_MARKET_TYPES = {"spot_demo", "paper", "dry_run", None, ""}
FAIL_REASONS = {
    "HEALTH_REQUEST_FAILED",
    "STATUS_REQUEST_FAILED",
    "HEALTH_NOT_OK",
    "API_NOT_RUNNING",
    "BOOTSTRAP_FAILED",
    "REAL_LIVE_ARMED",
    "LIVE_REAL_CONFIRM_ENABLED",
    "UNSAFE_EXECUTION_MODE",
    "UNSAFE_MARKET_TYPE",
    "CONFIG_NOT_SAFE_TO_TRADE",
    "CONFIG_NOT_SAFE_TO_AUTO_TRADE",
    "CONFIG_CRITICAL_WARNING",
    "ACCOUNT_HEALTH_ANOMALY",
    "MODEL_QUALITY_CRITICAL",
}
WARNING_REASONS = {
    "WS_NOT_CONNECTED",
    "STATUS_CONTRACT_BELOW_ENGINE_MINIMUM",
    "INTERRUPTED_BY_OPERATOR",
    "MODEL_QUALITY_WARNING",
    "LOW_SAMPLE_COUNT",
    "POSITION_PRESENT",
    "PENDING_PRESENT",
}


class SoakHttpError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def compact(value: Any, max_len: int = 500) -> str:
    text = str(value)
    return text if len(text) <= max_len else text[:max_len] + "..."


def get_path(data: Any, path: str, default: Any = None) -> Any:
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part, default)
        else:
            return default
    return cur


def boolish(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ok", "pass", "passed"}
    return bool(value)


def normalize_contract(value: Any) -> tuple[int, ...]:
    text = str(value or "")
    parts: list[int] = []
    for token in text.replace("-", ".").split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts)


def contract_at_least(value: Any, minimum: str = "4B.4.3.6.6.21") -> bool:
    current = normalize_contract(value)
    required = normalize_contract(minimum)
    if not current:
        return False
    max_len = max(len(current), len(required))
    return current + (0,) * (max_len - len(current)) >= required + (0,) * (max_len - len(required))


def http_get_json(base_url: str, path: str, timeout_sec: float = 5.0) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return {}
            data = json.loads(raw)
            return data if isinstance(data, dict) else {"value": data}
    except urllib.error.HTTPError as exc:
        raise SoakHttpError(f"HTTP {exc.code}: {exc.reason}") from exc
    except Exception as exc:
        raise SoakHttpError(str(exc)) from exc


def summarize_health(health: dict[str, Any] | None, error: str | None = None) -> dict[str, Any]:
    if error:
        return {"ok": False, "error": error}
    payload = health or {}
    return {
        "ok": boolish(payload.get("ok")),
        "running": boolish(payload.get("running")),
        "bootstrap_ok": boolish(payload.get("bootstrap_ok"), default=True),
        "bootstrap_error": payload.get("bootstrap_error"),
        "symbol": payload.get("symbol"),
    }


def summarize_status(status: dict[str, Any] | None, error: str | None = None) -> dict[str, Any]:
    if error:
        return {"ok": False, "error": error}
    payload = status or {}
    config = payload.get("config_safety_snapshot") or {}
    health = payload.get("health_snapshot") or {}
    model_quality = payload.get("model_quality_snapshot") or {}
    performance = payload.get("performance_snapshot") or {}
    position = payload.get("position_snapshot") or {}
    pending = payload.get("pending_snapshot") or {}
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
    if health.get("bootstrap_ok") is False or health.get("bootstrap_error"):
        reasons.append("BOOTSTRAP_FAILED")
    if status.get("ok"):
        # /status.contract_version is the runtime engine/status contract, not the
        # release tooling phase. The 4B.4.3.6.6.21 release candidate is proven
        # by acceptance reports; live runtime can legitimately report the older
        # engine contract such as 4B.4.3.6.6.12. Do not warn on that.
        if not contract_at_least(status.get("contract_version"), RUNTIME_ENGINE_CONTRACT_MINIMUM):
            reasons.append("STATUS_CONTRACT_BELOW_ENGINE_MINIMUM")
        if str(status.get("ws_status") or "").upper() not in {"CONNECTED", "WS CONNECTED"}:
            reasons.append("WS_NOT_CONNECTED")
        config = status.get("config") or {}
        execution_mode = str(config.get("execution_mode") or "").strip().lower()
        market_type = config.get("market_type")
        market_type_norm = str(market_type or "").strip().lower()
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
        model = status.get("model_quality") or {}
        severity = str(model.get("severity") or "").lower()
        if severity in {"critical", "fail", "failed"}:
            reasons.append("MODEL_QUALITY_CRITICAL")
        elif severity in {"warning", "warn", "degraded"}:
            reasons.append("MODEL_QUALITY_WARNING")
        if get_path(status, "position.present", False):
            reasons.append("POSITION_PRESENT")
        if get_path(status, "pending.present", False):
            reasons.append("PENDING_PRESENT")
    fail = any(reason in FAIL_REASONS for reason in reasons)
    warn = any(reason in WARNING_REASONS for reason in reasons)
    severity = "FAIL" if fail else "WARN" if warn else "PASS"
    return {"severity": severity, "reason_codes": sorted(set(reasons))}


def collect_sample(base_url: str, timeout_sec: float, fetcher: Callable[[str, str, float], dict[str, Any]] = http_get_json) -> dict[str, Any]:
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
    evaluation = evaluate_sample(health, status)
    return {
        "ts_utc": utc_now(),
        "health": health,
        "status": status,
        "evaluation": evaluation,
    }


def aggregate_samples(samples: list[dict[str, Any]], min_samples: int = 1) -> dict[str, Any]:
    severity_counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    reason_counts: dict[str, int] = {}
    states: dict[str, int] = {}
    for sample in samples:
        severity = get_path(sample, "evaluation.severity", "FAIL")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        for reason in get_path(sample, "evaluation.reason_codes", []) or []:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        state = str(get_path(sample, "status.state", "") or "UNKNOWN")
        states[state] = states.get(state, 0) + 1
    if len(samples) < min_samples:
        reason_counts["LOW_SAMPLE_COUNT"] = reason_counts.get("LOW_SAMPLE_COUNT", 0) + 1
        severity_counts["WARN"] = severity_counts.get("WARN", 0) + 1
    decision = "FAIL" if severity_counts.get("FAIL", 0) else "REVIEW" if severity_counts.get("WARN", 0) else "PASS"
    return {
        "decision": decision,
        "sample_count": len(samples),
        "severity_counts": severity_counts,
        "reason_counts": dict(sorted(reason_counts.items())),
        "state_counts": dict(sorted(states.items())),
        "first_ts_utc": samples[0]["ts_utc"] if samples else None,
        "last_ts_utc": samples[-1]["ts_utc"] if samples else None,
    }


def mark_operator_interrupt(summary: dict[str, Any]) -> dict[str, Any]:
    severity_counts = dict(summary.get("severity_counts") or {})
    reason_counts = dict(summary.get("reason_counts") or {})
    reason_counts["INTERRUPTED_BY_OPERATOR"] = reason_counts.get("INTERRUPTED_BY_OPERATOR", 0) + 1
    severity_counts["WARN"] = severity_counts.get("WARN", 0) + 1
    summary["severity_counts"] = severity_counts
    summary["reason_counts"] = dict(sorted(reason_counts.items()))
    if severity_counts.get("FAIL", 0):
        summary["decision"] = "FAIL"
    else:
        summary["decision"] = "REVIEW"
    return summary


def run_soak(
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
            if time.monotonic() >= deadline:
                break
            sleep_for = min(max(interval_sec, 0.0), max(deadline - time.monotonic(), 0.0))
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                break
    except KeyboardInterrupt:
        interrupted_by_operator = True
    summary = aggregate_samples(samples, min_samples=min_samples)
    if interrupted_by_operator:
        summary = mark_operator_interrupt(summary)
    return {
        "phase": PHASE,
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


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        f"# {PHASE} Live-demo Supervised Soak Test Report",
        "",
        f"Generated at UTC: `{report.get('generated_at_utc')}`",
        f"Base URL: `{report.get('base_url')}`",
        f"Decision: **{summary.get('decision')}**",
        f"Observation-only: `{report.get('observation_only')}`",
        f"No POST actions: `{report.get('no_post_actions')}`",
        f"Interrupted by operator: `{report.get('interrupted_by_operator', False)}`",
        "",
        "## Summary",
        "",
        f"- Sample count: `{summary.get('sample_count')}`",
        f"- First sample: `{summary.get('first_ts_utc')}`",
        f"- Last sample: `{summary.get('last_ts_utc')}`",
        f"- Severity counts: `{summary.get('severity_counts')}`",
        f"- State counts: `{summary.get('state_counts')}`",
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
        "| # | Time UTC | Severity | State | WS | Reasons |",
        "|---:|---|---|---|---|---|",
    ])
    for idx, sample in enumerate(report.get("samples") or [], start=1):
        status = sample.get("status") or {}
        eval_ = sample.get("evaluation") or {}
        reasons = ", ".join(eval_.get("reason_codes") or []) or "-"
        lines.append(
            f"| {idx} | {sample.get('ts_utc')} | {eval_.get('severity')} | {status.get('state')} | {status.get('ws_status')} | {reasons} |"
        )
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- This tool must remain GET-only.",
        "- Do not use this phase to arm real live trading.",
        "- If the decision is FAIL, stop the soak and investigate before any new patch.",
        "- REVIEW is acceptable only for known non-critical warnings such as existing open/pending demo state or operator-interrupted partial soak under supervision.",
    ])
    return "\n".join(lines) + "\n"


def write_reports(root: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = timestamp_slug()
    json_path = reports_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = reports_dir / f"{REPORT_PREFIX}_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run observation-only live-demo supervised soak checks.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--duration-min", type=float, default=60.0, help="Observation duration in minutes. Default: 60")
    parser.add_argument("--interval-sec", type=float, default=60.0, help="Seconds between samples. Default: 60")
    parser.add_argument("--timeout-sec", type=float, default=5.0)
    parser.add_argument("--max-samples", type=int, default=None, help="Optional hard cap for samples")
    parser.add_argument("--min-samples", type=int, default=3, help="Minimum expected samples before PASS")
    parser.add_argument("--once", action="store_true", help="Take one sample and exit")
    parser.add_argument("--review-ok", action="store_true", help="Exit 0 for REVIEW decision")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    if args.once:
        duration_sec = 0.0
        max_samples = 1
        min_samples = 1
    else:
        duration_sec = max(args.duration_min, 0.0) * 60.0
        max_samples = args.max_samples
        min_samples = max(args.min_samples, 1)
    report = run_soak(
        args.base_url,
        duration_sec=duration_sec,
        interval_sec=max(args.interval_sec, 1.0),
        timeout_sec=max(args.timeout_sec, 1.0),
        max_samples=max_samples,
        min_samples=min_samples,
    )
    json_path, md_path = write_reports(root, report)
    summary = report["summary"]
    decision = summary["decision"]
    print(f"{PHASE} live-demo supervised soak {decision}")
    print(f" - samples: {summary['sample_count']}")
    print(f" - severity_counts: {summary['severity_counts']}")
    print(f" - reason_counts: {summary['reason_counts']}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    if decision == "PASS":
        return 0
    if decision == "REVIEW" and args.review_ok:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
