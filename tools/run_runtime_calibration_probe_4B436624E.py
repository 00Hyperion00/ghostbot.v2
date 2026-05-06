"""4B.4.3.6.6.24E runtime calibration probe + threshold sweep.

GET-only diagnostic tool. It collects /status snapshots, extracts raw model
probabilities, replays the runtime calibration logic across diagnostic threshold
profiles, and reports whether HOLD dominance is caused by raw model collapse or
calibration/threshold suppression.

It never submits orders, never reloads a model, and never mutates config.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.runtime_calibration_probe import (  # noqa: E402
    RUNTIME_CALIBRATION_PROBE_CONTRACT_VERSION,
    build_runtime_calibration_probe,
    build_threshold_sweep,
    extract_runtime_probability_sample,
)

PHASE = "4B.4.3.6.6.24E"
REPORT_PREFIX = "4B436624E_runtime_calibration_probe"
SWEEP_PREFIX = "4B436624E_threshold_sweep"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


class ProbeHttpError(RuntimeError):
    pass


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compact(value: Any, max_len: int = 500) -> str:
    text = str(value)
    return text if len(text) <= max_len else text[:max_len] + "..."


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
        raise ProbeHttpError(f"HTTP {exc.code}: {exc.reason}") from exc
    except Exception as exc:
        raise ProbeHttpError(str(exc)) from exc


def _status_from_sample(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, Mapping):
        return None
    # Native status payload.
    if "ai_snapshot" in item or "last_signal_metrics" in item or "decision_audit_snapshot" in item:
        return dict(item)
    # Possible wrapped report payloads.
    for key in ("status_payload", "raw_status", "status"):
        value = item.get(key)
        if isinstance(value, Mapping):
            if "ai_snapshot" in value or "last_signal_metrics" in value or "decision_audit_snapshot" in value:
                return dict(value)
    return None


def load_status_payloads(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [status for item in payload if (status := _status_from_sample(item)) is not None]
    if isinstance(payload, Mapping):
        direct = _status_from_sample(payload)
        if direct is not None:
            return [direct]
        samples = payload.get("samples")
        if isinstance(samples, list):
            return [status for item in samples if (status := _status_from_sample(item)) is not None]
        statuses = payload.get("statuses")
        if isinstance(statuses, list):
            return [status for item in statuses if (status := _status_from_sample(item)) is not None]
    return []


def collect_status_payloads(
    base_url: str,
    *,
    duration_sec: float,
    interval_sec: float,
    timeout_sec: float,
    max_samples: int,
    fetcher: Callable[[str, str, float], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    fetch = fetcher or http_get_json
    started = time.monotonic()
    statuses: list[dict[str, Any]] = []
    while len(statuses) < max_samples:
        try:
            status = fetch(base_url, "/status", timeout_sec)
            status["_probe_collected_at"] = utc_now()
            statuses.append(status)
        except Exception as exc:
            statuses.append({"_probe_error": compact(exc), "_probe_collected_at": utc_now()})
        if len(statuses) >= max_samples:
            break
        if duration_sec > 0:
            elapsed = time.monotonic() - started
            if elapsed >= duration_sec:
                break
            time.sleep(max(0.0, min(interval_sec, duration_sec - elapsed)))
    return statuses


def extract_probability_samples(statuses: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    samples: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for idx, status in enumerate(statuses):
        sample = extract_runtime_probability_sample(status, sample_index=idx)
        if sample is None:
            rejected.append({
                "sample_index": idx,
                "reason": "PROBABILITY_METRICS_MISSING",
                "error": status.get("_probe_error"),
                "collected_at": status.get("_probe_collected_at"),
            })
        else:
            sample["collected_at"] = status.get("_probe_collected_at")
            samples.append(sample)
    return samples, rejected


def build_markdown(report: Mapping[str, Any]) -> str:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), Mapping) else {}
    lines = [
        f"# 4B.4.3.6.6.24E Runtime Calibration Probe",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- conclusion: `{report.get('conclusion')}`",
        f"- sample_count: `{report.get('sample_count')}`",
        f"- observation_only: `{report.get('observation_only')}`",
        f"- no_post_actions: `{report.get('no_post_actions')}`",
        "",
        "## Metrics",
        "",
        f"- raw_distribution: `{metrics.get('raw_distribution')}`",
        f"- raw_action_pct: `{metrics.get('raw_action_pct')}`",
        f"- current_distribution: `{metrics.get('current_distribution')}`",
        f"- current_action_pct: `{metrics.get('current_action_pct')}`",
        f"- low_margin_rejection_pct: `{metrics.get('low_margin_rejection_pct')}`",
        f"- relaxed_best_action_pct: `{metrics.get('relaxed_best_action_pct')}`",
        f"- relaxed_best_profile: `{metrics.get('relaxed_best_profile')}`",
        "",
        "## Reason Codes",
        "",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- warnings: `{report.get('warnings')}`",
        "",
        "## Recommendation",
        "",
        str(report.get("recommendation") or "-"),
        "",
        "## Threshold Sweep",
        "",
        "| profile | action_pct | hold_pct | calibrated_distribution | reasons |",
        "|---|---:|---:|---|---|",
    ]
    sweep = report.get("threshold_sweep") if isinstance(report.get("threshold_sweep"), Mapping) else {}
    for profile in sweep.get("profiles") or []:
        profile_cfg = profile.get("profile") if isinstance(profile.get("profile"), Mapping) else {}
        lines.append(
            f"| {profile_cfg.get('name')} | {profile.get('action_pct')} | {profile.get('hold_pct')} | `{profile.get('calibrated_distribution')}` | `{profile.get('reason_counts')}` |"
        )
    lines.extend([
        "",
        "## Guardrail",
        "",
        "This report is diagnostic only. It does not reload models, mutate thresholds, submit orders, or arm live trading.",
    ])
    return "\n".join(lines) + "\n"


def build_sweep_markdown(sweep: Mapping[str, Any]) -> str:
    lines = [
        "# 4B.4.3.6.6.24E Threshold Sweep",
        "",
        f"- contract_version: `{sweep.get('contract_version')}`",
        f"- sample_count: `{sweep.get('sample_count')}`",
        "",
        "| profile | buy_th | sell_th | hold_low | hold_high | margin | action_pct | distribution | reasons |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for profile in sweep.get("profiles") or []:
        cfg = profile.get("profile") if isinstance(profile.get("profile"), Mapping) else {}
        lines.append(
            f"| {cfg.get('name')} | {cfg.get('buy_threshold')} | {cfg.get('sell_threshold')} | {cfg.get('hold_band_low')} | {cfg.get('hold_band_high')} | {cfg.get('indecision_margin')} | {profile.get('action_pct')} | `{profile.get('calibrated_distribution')}` | `{profile.get('reason_counts')}` |"
        )
    return "\n".join(lines) + "\n"


def write_reports(out_dir: str | Path, report: dict[str, Any]) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slug = timestamp_slug()
    report_json = out / f"{REPORT_PREFIX}_{slug}.json"
    report_md = out / f"{REPORT_PREFIX}_{slug}.md"
    sweep_json = out / f"{SWEEP_PREFIX}_{slug}.json"
    sweep_md = out / f"{SWEEP_PREFIX}_{slug}.md"

    sweep = report.get("threshold_sweep") if isinstance(report.get("threshold_sweep"), dict) else build_threshold_sweep([])
    report_json.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    report_md.write_text(build_markdown(report), encoding="utf-8")
    sweep_json.write_text(json.dumps(sweep, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    sweep_md.write_text(build_sweep_markdown(sweep), encoding="utf-8")
    return {
        "report_json": report_json.as_posix(),
        "report_md": report_md.as_posix(),
        "sweep_json": sweep_json.as_posix(),
        "sweep_md": sweep_md.as_posix(),
    }


def run_probe(
    *,
    base_url: str = DEFAULT_BASE_URL,
    duration_sec: float = 0.0,
    interval_sec: float = 60.0,
    timeout_sec: float = 5.0,
    max_samples: int = 1,
    min_samples: int = 30,
    input_json: str | None = None,
    fetcher: Callable[[str, str, float], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if input_json:
        statuses = load_status_payloads(input_json)
    else:
        statuses = collect_status_payloads(
            base_url,
            duration_sec=duration_sec,
            interval_sec=interval_sec,
            timeout_sec=timeout_sec,
            max_samples=max_samples,
            fetcher=fetcher,
        )
    samples, rejected = extract_probability_samples(statuses)
    report = build_runtime_calibration_probe(samples, min_samples=min_samples)
    report.update({
        "phase": PHASE,
        "base_url": base_url,
        "status_count": len(statuses),
        "probability_sample_count": len(samples),
        "rejected_samples": rejected,
        "guardrails": {
            "observation_only": True,
            "get_only": True,
            "post_requests_allowed": False,
            "reload_performed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "live_trading_armed": False,
        },
    })
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.24E runtime calibration probe + threshold sweep")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--duration-min", type=float, default=0.0)
    parser.add_argument("--interval-sec", type=float, default=60.0)
    parser.add_argument("--timeout-sec", type=float, default=5.0)
    parser.add_argument("--max-samples", type=int, default=1)
    parser.add_argument("--min-samples", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--input-json")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Compatibility flag; report generation remains diagnostic-only.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    max_samples = 1 if args.once else max(1, int(args.max_samples or 1))
    duration_sec = 0.0 if args.once else max(0.0, float(args.duration_min) * 60.0)
    if not args.once and duration_sec > 0 and max_samples <= 1:
        max_samples = max(1, int(duration_sec // max(1.0, float(args.interval_sec))) + 1)
    report = run_probe(
        base_url=args.base_url,
        duration_sec=duration_sec,
        interval_sec=float(args.interval_sec),
        timeout_sec=float(args.timeout_sec),
        max_samples=max_samples,
        min_samples=int(args.min_samples),
        input_json=args.input_json,
    )
    paths = write_reports(args.out_dir, report)
    print(f"{PHASE} runtime calibration probe {report['decision']}")
    print(f" - samples: {report['sample_count']}")
    print(f" - conclusion: {report['conclusion']}")
    print(f" - reason_codes: {report['reason_codes']}")
    print(f" - warnings: {report['warnings']}")
    metrics = report.get("metrics") or {}
    print(f" - raw_action_pct: {metrics.get('raw_action_pct')}")
    print(f" - current_action_pct: {metrics.get('current_action_pct')}")
    print(f" - relaxed_best_action_pct: {metrics.get('relaxed_best_action_pct')} ({metrics.get('relaxed_best_profile')})")
    print(f"report_json: {paths['report_json']}")
    print(f"report_md: {paths['report_md']}")
    print(f"sweep_json: {paths['sweep_json']}")
    print(f"sweep_md: {paths['sweep_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
