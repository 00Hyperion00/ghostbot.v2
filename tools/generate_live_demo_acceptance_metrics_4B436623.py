"""4B.4.3.6.6.23 live-demo acceptance metrics / performance review.

Observation-only report generator. It reads prior 4B436622 soak reports, optionally
reads runtime API snapshots and an operator/API log file, then produces acceptance
metrics for the supervised live-demo soak phase.

This tool performs GET requests only when --base-url is provided. It never submits
orders, never toggles controls, and never arms live trading.
"""

import argparse
import json
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PHASE = "4B.4.3.6.6.23"
SOAK_PREFIX = "4B436622_live_demo_soak"
REPORT_PREFIX = "4B436623_live_demo_acceptance_metrics"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
SAFE_EXECUTION_MODES = {"live_demo", "paper", "dry_run", ""}
SAFE_MARKET_TYPES = {"spot_demo", "paper", "dry_run", ""}

ORDER_CODES = {
    "ORDER_SUBMITTED",
    "LIVE_ORDER_SUBMITTED",
    "LIVE_ENTRY_ORDER_SUBMITTED",
    "LIVE_EXIT_ORDER_SUBMITTED",
    "LIVE_PARTIAL_FILL_RECORDED",
    "ORDER_FILLED",
    "ORDER_PARTIALLY_FILLED",
}

ERROR_LEVEL_RE = re.compile(r"\|\s*(ERROR|CRITICAL)\s*\|", re.IGNORECASE)
WARNING_LEVEL_RE = re.compile(r"\|\s*(WARN|WARNING)\s*\|", re.IGNORECASE)
CODE_RE = re.compile(r"^.*?\|\s*(?:INFO|WARN|WARNING|ERROR|CRITICAL)\s*\|\s*(?P<code>[A-Z0-9_]+)\s*\|", re.IGNORECASE)
SIGNAL_RE = re.compile(r"'signal'\s*:\s*'(?P<signal>[A-Z_]+)'")
ACTION_RE = re.compile(r"'action'\s*:\s*'(?P<action>[A-Z_]+)'")
SKIP_CODE_RE = re.compile(r"'skipCode'\s*:\s*'(?P<skip>[A-Z0-9_]+)'")
REASON_CODES_RE = re.compile(r"'reasonCodes'\s*:\s*\[(?P<codes>[^\]]*)\]")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"value": data}


def latest_files(directory: Path, pattern: str) -> list[Path]:
    return sorted([p for p in directory.glob(pattern) if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)


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


def normalize_decision(value: Any) -> str:
    return str(value or "").strip().upper()


def parse_iso_seconds(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def seconds_between(first: Any, last: Any) -> float | None:
    a = parse_iso_seconds(first)
    b = parse_iso_seconds(last)
    if a is None or b is None:
        return None
    return max((b - a).total_seconds(), 0.0)


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


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
        return {"_request_error": f"HTTP {exc.code}: {exc.reason}"}
    except Exception as exc:
        return {"_request_error": str(exc)}


def summarize_soak_report(report: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    summary = report.get("summary") or {}
    severity_counts = summary.get("severity_counts") or {}
    sample_count = int(summary.get("sample_count") or len(report.get("samples") or []) or 0)
    pass_count = int(severity_counts.get("PASS") or 0)
    warn_count = int(severity_counts.get("WARN") or 0)
    fail_count = int(severity_counts.get("FAIL") or 0)
    pass_rate_pct = round((pass_count / sample_count) * 100.0, 4) if sample_count else 0.0
    duration_sec = seconds_between(summary.get("first_ts_utc"), summary.get("last_ts_utc"))
    samples = report.get("samples") or []
    ws_not_connected_samples = 0
    last_signal_counts: dict[str, int] = {}
    state_counts: dict[str, int] = dict(summary.get("state_counts") or {})
    for sample in samples:
        status = sample.get("status") or {}
        ws = str(status.get("ws_status") or "").upper()
        if ws and ws not in {"CONNECTED", "WS CONNECTED"}:
            ws_not_connected_samples += 1
        signal = str(status.get("last_signal") or "UNKNOWN").upper()
        last_signal_counts[signal] = last_signal_counts.get(signal, 0) + 1
    return {
        "path": str(path) if path else None,
        "decision": normalize_decision(summary.get("decision")),
        "sample_count": sample_count,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "pass_rate_pct": pass_rate_pct,
        "duration_sec": duration_sec,
        "first_ts_utc": summary.get("first_ts_utc"),
        "last_ts_utc": summary.get("last_ts_utc"),
        "reason_counts": dict(summary.get("reason_counts") or {}),
        "state_counts": state_counts,
        "last_signal_counts": dict(sorted(last_signal_counts.items())),
        "ws_not_connected_samples": ws_not_connected_samples,
        "interrupted_by_operator": boolish(report.get("interrupted_by_operator")),
        "observation_only": boolish(report.get("observation_only")),
        "no_post_actions": boolish(report.get("no_post_actions")),
    }


def discover_soak_reports(root: Path, latest_only: bool = False) -> list[dict[str, Any]]:
    paths = latest_files(root / "reports", f"{SOAK_PREFIX}_*.json")
    if latest_only and paths:
        paths = paths[:1]
    reports: list[dict[str, Any]] = []
    for path in paths:
        try:
            reports.append(summarize_soak_report(load_json(path), path.relative_to(root)))
        except Exception as exc:
            reports.append({"path": str(path.relative_to(root)), "decision": "LOAD_ERROR", "error": str(exc)})
    return reports


def select_best_soak_report(reports: list[dict[str, Any]], min_samples: int) -> dict[str, Any] | None:
    passing = [r for r in reports if r.get("decision") == "PASS" and int(r.get("sample_count") or 0) >= min_samples]
    if passing:
        return max(passing, key=lambda r: (int(r.get("sample_count") or 0), safe_float(r.get("pass_rate_pct"), 0.0) or 0.0))
    if reports:
        return reports[0]
    return None


def parse_reason_codes_blob(line: str) -> list[str]:
    match = REASON_CODES_RE.search(line)
    if not match:
        return []
    raw = match.group("codes")
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip().strip("'\"")]


def analyze_log_text(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    code_counts: dict[str, int] = {}
    signal_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    skip_code_counts: dict[str, int] = {}
    reason_code_counts: dict[str, int] = {}
    warning_count = 0
    error_count = 0
    ws_disconnect_count = 0
    order_event_count = 0
    strategy_eval_count = 0
    auto_trade_skip_count = 0
    for line in lines:
        if WARNING_LEVEL_RE.search(line):
            warning_count += 1
        if ERROR_LEVEL_RE.search(line):
            error_count += 1
        code_match = CODE_RE.search(line)
        if code_match:
            code = code_match.group("code")
            code_counts[code] = code_counts.get(code, 0) + 1
            if code == "WS_DISCONNECTED":
                ws_disconnect_count += 1
            if code == "STRATEGY_EVAL":
                strategy_eval_count += 1
            if code == "AUTO_TRADE_SKIP":
                auto_trade_skip_count += 1
            if code in ORDER_CODES:
                order_event_count += 1
        signal_match = SIGNAL_RE.search(line)
        if signal_match:
            signal = signal_match.group("signal")
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        action_match = ACTION_RE.search(line)
        if action_match:
            action = action_match.group("action")
            action_counts[action] = action_counts.get(action, 0) + 1
        skip_match = SKIP_CODE_RE.search(line)
        if skip_match:
            skip = skip_match.group("skip")
            skip_code_counts[skip] = skip_code_counts.get(skip, 0) + 1
        for reason in parse_reason_codes_blob(line):
            reason_code_counts[reason] = reason_code_counts.get(reason, 0) + 1
    return {
        "line_count": len(lines),
        "warning_count": warning_count,
        "error_count": error_count,
        "ws_disconnect_count": ws_disconnect_count,
        "order_event_count": order_event_count,
        "strategy_eval_count": strategy_eval_count,
        "auto_trade_skip_count": auto_trade_skip_count,
        "code_counts": dict(sorted(code_counts.items())),
        "signal_counts": dict(sorted(signal_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "skip_code_counts": dict(sorted(skip_code_counts.items())),
        "reason_code_counts": dict(sorted(reason_code_counts.items())),
    }


def analyze_log_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"provided": False}
    if not path.exists():
        return {"provided": True, "exists": False, "error": f"log file not found: {path}"}
    text = path.read_text(encoding="utf-8", errors="replace")
    result = analyze_log_text(text)
    result.update({"provided": True, "exists": True, "path": str(path)})
    return result


def summarize_status_payload(status: dict[str, Any] | None) -> dict[str, Any]:
    if not status:
        return {"provided": False}
    if status.get("_request_error"):
        return {"provided": True, "request_error": status.get("_request_error")}
    config = status.get("config_safety_snapshot") or {}
    model_quality = status.get("model_quality_snapshot") or {}
    performance = status.get("performance_snapshot") or {}
    health = status.get("health_snapshot") or {}
    return {
        "provided": True,
        "contract_version": status.get("contract_version"),
        "state": status.get("state"),
        "ws_status": status.get("ws_status"),
        "last_signal": status.get("last_signal"),
        "last_signal_confidence": status.get("last_signal_confidence"),
        "config": {
            "profile_mode": config.get("profile_mode"),
            "execution_mode": config.get("execution_mode"),
            "market_type": config.get("market_type"),
            "safe_to_trade": config.get("safe_to_trade"),
            "safe_to_auto_trade": config.get("safe_to_auto_trade"),
            "live_trading_armed": config.get("live_trading_armed"),
            "live_real_double_confirm": config.get("live_real_double_confirm"),
            "critical_warnings": config.get("critical_warnings") or [],
        },
        "health": {
            "account_consistency": health.get("account_consistency"),
            "position_consistency": health.get("position_consistency"),
            "pending_consistency": health.get("pending_consistency"),
            "active_anomaly_code": health.get("active_anomaly_code"),
        },
        "model_quality": {
            "enabled": model_quality.get("enabled"),
            "severity": model_quality.get("severity"),
            "sample_count": model_quality.get("sample_count"),
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
    }


def evaluate_acceptance(
    best_soak: dict[str, Any] | None,
    status_summary: dict[str, Any],
    log_summary: dict[str, Any],
    *,
    min_samples: int,
    min_pass_rate_pct: float,
    max_ws_disconnects: int,
    max_log_errors: int,
) -> tuple[str, list[str], list[str]]:
    blockers: list[str] = []
    observations: list[str] = []
    if not best_soak:
        blockers.append("NO_SOAK_REPORT_FOUND")
    else:
        if best_soak.get("decision") != "PASS":
            blockers.append(f"SOAK_DECISION_{best_soak.get('decision', 'UNKNOWN')}")
        if int(best_soak.get("sample_count") or 0) < min_samples:
            blockers.append("SOAK_SAMPLE_COUNT_BELOW_MINIMUM")
        if safe_float(best_soak.get("pass_rate_pct"), 0.0) < min_pass_rate_pct:
            blockers.append("SOAK_PASS_RATE_BELOW_MINIMUM")
        if int(best_soak.get("fail_count") or 0) > 0:
            blockers.append("SOAK_HAS_FAILURES")
        if int(best_soak.get("warn_count") or 0) > 0:
            observations.append("SOAK_HAS_WARNINGS")
        if best_soak.get("interrupted_by_operator"):
            blockers.append("SOAK_INTERRUPTED_BY_OPERATOR")
        if not best_soak.get("observation_only") or not best_soak.get("no_post_actions"):
            blockers.append("SOAK_OBSERVATION_ONLY_CONTRACT_MISSING")
    if status_summary.get("provided"):
        if status_summary.get("request_error"):
            observations.append("STATUS_SNAPSHOT_UNAVAILABLE")
        config = status_summary.get("config") or {}
        if boolish(config.get("live_trading_armed")):
            blockers.append("REAL_LIVE_ARMED")
        if boolish(config.get("live_real_double_confirm")):
            blockers.append("LIVE_REAL_CONFIRM_ENABLED")
        if str(config.get("execution_mode") or "").lower() not in SAFE_EXECUTION_MODES:
            blockers.append("UNSAFE_EXECUTION_MODE")
        if str(config.get("market_type") or "").lower() not in SAFE_MARKET_TYPES:
            blockers.append("UNSAFE_MARKET_TYPE")
        if config.get("critical_warnings"):
            blockers.append("CONFIG_CRITICAL_WARNINGS_PRESENT")
        health = status_summary.get("health") or {}
        if health.get("active_anomaly_code"):
            blockers.append("ACTIVE_HEALTH_ANOMALY")
        model = status_summary.get("model_quality") or {}
        if str(model.get("severity") or "").lower() in {"critical", "fail", "failed"}:
            blockers.append("MODEL_QUALITY_CRITICAL")
    if log_summary.get("provided") and log_summary.get("exists", True):
        if int(log_summary.get("error_count") or 0) > max_log_errors:
            blockers.append("LOG_ERROR_COUNT_ABOVE_LIMIT")
        ws_disconnects = int(log_summary.get("ws_disconnect_count") or 0)
        if ws_disconnects > max_ws_disconnects:
            blockers.append("WS_DISCONNECT_COUNT_ABOVE_LIMIT")
        elif ws_disconnects > 0:
            observations.append("WS_RECONNECT_OBSERVED")
        if int(log_summary.get("order_event_count") or 0) > 0:
            observations.append("ORDER_EVENTS_OBSERVED_IN_LOG")
        if int(log_summary.get("auto_trade_skip_count") or 0) > 0:
            observations.append("AUTO_TRADE_SKIP_CONFIRMED")
    elif log_summary.get("provided") and not log_summary.get("exists"):
        observations.append("LOG_FILE_NOT_FOUND")
    decision = "PASS" if not blockers else "FAIL"
    return decision, sorted(set(blockers)), sorted(set(observations))


def build_report(
    root: Path,
    *,
    latest_only: bool,
    log_file: Path | None,
    status_payload: dict[str, Any] | None,
    min_samples: int,
    min_pass_rate_pct: float,
    max_ws_disconnects: int,
    max_log_errors: int,
) -> dict[str, Any]:
    soak_reports = discover_soak_reports(root, latest_only=latest_only)
    best_soak = select_best_soak_report(soak_reports, min_samples=min_samples)
    status_summary = summarize_status_payload(status_payload)
    log_summary = analyze_log_file(log_file)
    decision, blockers, observations = evaluate_acceptance(
        best_soak,
        status_summary,
        log_summary,
        min_samples=min_samples,
        min_pass_rate_pct=min_pass_rate_pct,
        max_ws_disconnects=max_ws_disconnects,
        max_log_errors=max_log_errors,
    )
    return {
        "phase": PHASE,
        "generated_at_utc": utc_now(),
        "decision": decision,
        "blockers": blockers,
        "observations": observations,
        "criteria": {
            "min_samples": min_samples,
            "min_pass_rate_pct": min_pass_rate_pct,
            "max_ws_disconnects": max_ws_disconnects,
            "max_log_errors": max_log_errors,
        },
        "selected_soak_report": best_soak,
        "soak_reports_reviewed": soak_reports,
        "status_snapshot": status_summary,
        "log_summary": log_summary,
        "observation_only": True,
        "no_post_actions": True,
    }


def render_markdown(report: dict[str, Any]) -> str:
    selected = report.get("selected_soak_report") or {}
    log = report.get("log_summary") or {}
    status = report.get("status_snapshot") or {}
    lines = [
        f"# {PHASE} Live-demo Acceptance Metrics / Performance Review",
        "",
        f"Generated at UTC: `{report.get('generated_at_utc')}`",
        f"Decision: **{report.get('decision')}**",
        f"Observation-only: `{report.get('observation_only')}`",
        f"No POST actions: `{report.get('no_post_actions')}`",
        "",
        "## Acceptance Criteria",
        "",
        f"- Minimum samples: `{get_path(report, 'criteria.min_samples')}`",
        f"- Minimum pass rate: `{get_path(report, 'criteria.min_pass_rate_pct')}`%",
        f"- Max WS disconnects: `{get_path(report, 'criteria.max_ws_disconnects')}`",
        f"- Max log errors: `{get_path(report, 'criteria.max_log_errors')}`",
        "",
        "## Blockers",
        "",
    ]
    blockers = report.get("blockers") or []
    lines.extend([f"- {item}" for item in blockers] if blockers else ["- None"])
    lines.extend(["", "## Observations", ""])
    observations = report.get("observations") or []
    lines.extend([f"- {item}" for item in observations] if observations else ["- None"])
    lines.extend([
        "",
        "## Selected Soak Report",
        "",
        f"- Path: `{selected.get('path')}`",
        f"- Decision: `{selected.get('decision')}`",
        f"- Samples: `{selected.get('sample_count')}`",
        f"- Pass rate: `{selected.get('pass_rate_pct')}`%",
        f"- Warnings: `{selected.get('warn_count')}`",
        f"- Failures: `{selected.get('fail_count')}`",
        f"- State counts: `{selected.get('state_counts')}`",
        f"- Signal counts: `{selected.get('last_signal_counts')}`",
        f"- Reason counts: `{selected.get('reason_counts')}`",
        "",
        "## Runtime Status Snapshot",
        "",
        f"- Provided: `{status.get('provided')}`",
        f"- State: `{status.get('state')}`",
        f"- WS: `{status.get('ws_status')}`",
        f"- Last signal: `{status.get('last_signal')}`",
        f"- Last signal confidence: `{status.get('last_signal_confidence')}`",
        f"- Config: `{status.get('config')}`",
        f"- Model quality: `{status.get('model_quality')}`",
        f"- Performance: `{status.get('performance')}`",
        "",
        "## Log Metrics",
        "",
        f"- Provided: `{log.get('provided')}`",
        f"- Lines: `{log.get('line_count')}`",
        f"- Warnings: `{log.get('warning_count')}`",
        f"- Errors: `{log.get('error_count')}`",
        f"- WS disconnects: `{log.get('ws_disconnect_count')}`",
        f"- Strategy eval count: `{log.get('strategy_eval_count')}`",
        f"- Auto-trade skip count: `{log.get('auto_trade_skip_count')}`",
        f"- Order event count: `{log.get('order_event_count')}`",
        f"- Signals: `{log.get('signal_counts')}`",
        f"- Actions: `{log.get('action_counts')}`",
        f"- Skip codes: `{log.get('skip_code_counts')}`",
        f"- Reason codes: `{log.get('reason_code_counts')}`",
        "",
        "## Risk Manager Notes",
        "",
        "- PASS means the supervised live-demo soak evidence is acceptable for metrics review; it is not permission to arm real live trading.",
        "- HOLD / AUTO_TRADE_SKIP with low-confidence reason codes is acceptable and preferred when decision margin is weak.",
        "- WS reconnect observations are acceptable within the configured threshold only if health/status samples remain PASS.",
        "",
        "## Next Phase",
        "",
        "4B.4.3.6.6.24 — Pre-live risk gate / real trading arming checklist.",
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
    parser = argparse.ArgumentParser(description="Generate live-demo acceptance metrics/performance review from 4B436622 soak reports.")
    parser.add_argument("--root", default=".", help="Project root. Default: current directory")
    parser.add_argument("--base-url", default=None, help="Optional local API base URL for GET /status snapshot")
    parser.add_argument("--timeout-sec", type=float, default=5.0)
    parser.add_argument("--log-file", default=None, help="Optional API/operator log text file to parse")
    parser.add_argument("--latest-only", action="store_true", help="Review only the latest soak report instead of all soak reports")
    parser.add_argument("--min-samples", type=int, default=10)
    parser.add_argument("--min-pass-rate-pct", type=float, default=100.0)
    parser.add_argument("--max-ws-disconnects", type=int, default=2)
    parser.add_argument("--max-log-errors", type=int, default=0)
    parser.add_argument("--review-ok", action="store_true", help="Exit 0 for FAIL/REVIEW-like output; useful during investigation")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    status_payload = http_get_json(args.base_url, "/status", args.timeout_sec) if args.base_url else None
    log_file = Path(args.log_file).resolve() if args.log_file else None
    report = build_report(
        root,
        latest_only=args.latest_only,
        log_file=log_file,
        status_payload=status_payload,
        min_samples=max(args.min_samples, 1),
        min_pass_rate_pct=max(args.min_pass_rate_pct, 0.0),
        max_ws_disconnects=max(args.max_ws_disconnects, 0),
        max_log_errors=max(args.max_log_errors, 0),
    )
    json_path, md_path = write_reports(root, report)
    selected = report.get("selected_soak_report") or {}
    print(f"{PHASE} live-demo acceptance metrics {report['decision']}")
    print(f" - selected_soak: {selected.get('path')}")
    print(f" - samples: {selected.get('sample_count')}")
    print(f" - pass_rate_pct: {selected.get('pass_rate_pct')}")
    print(f" - blockers: {report.get('blockers')}")
    print(f" - observations: {report.get('observations')}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    if report["decision"] == "PASS":
        return 0
    return 0 if args.review_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
