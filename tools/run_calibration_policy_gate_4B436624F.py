from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from tradebot.calibration_policy_gate import CALIBRATION_POLICY_GATE_CONTRACT_VERSION, CalibrationPolicyGateLimits, build_calibration_policy_gate, samples_from_24e_report
from tradebot.runtime_calibration_probe import extract_runtime_probability_sample

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
REPORT_PREFIX = "4B436624F_calibration_policy_gate"


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def fetch_json(base_url: str, path: str, timeout_sec: float, *, method: str = "GET") -> dict[str, Any]:
    request = urllib.request.Request(base_url.rstrip("/") + path, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:  # noqa: S310
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object from status endpoint")
    return data


def collect_status_payloads(base_url: str, *, duration_sec: float, interval_sec: float, timeout_sec: float, max_samples: int, fetcher: Callable[[str, str, float], dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    fetcher = fetcher or fetch_json
    statuses: list[dict[str, Any]] = []
    deadline = time.monotonic() + max(0.0, float(duration_sec))
    while len(statuses) < int(max_samples):
        try:
            status = fetcher(base_url, "/status", timeout_sec)
            status["_collected_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            statuses.append(status)
        except Exception as exc:  # noqa: BLE001
            statuses.append({"_collected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "_collection_error": str(exc)})
        if duration_sec <= 0 or time.monotonic() >= deadline:
            break
        time.sleep(max(0.1, float(interval_sec)))
    return statuses


def load_input_payloads(path: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        report_samples = samples_from_24e_report(raw)
        if report_samples:
            return [], report_samples
        statuses = raw.get("statuses") or raw.get("status_payloads")
        if isinstance(statuses, list):
            return [dict(item) for item in statuses if isinstance(item, Mapping)], []
        if "ai_snapshot" in raw:
            return [dict(raw)], []
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, Mapping)], []
    raise ValueError(f"Unsupported input JSON format: {path}")


def build_samples_from_statuses(statuses: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    samples: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for index, status in enumerate(statuses):
        if status.get("_collection_error"):
            rejected.append({"sample_index": index, "reason": "API_STATUS_REQUEST_FAILED", "error": status.get("_collection_error"), "collected_at": status.get("_collected_at")})
            continue
        sample = extract_runtime_probability_sample(status, sample_index=index)
        if sample is None:
            rejected.append({"sample_index": index, "reason": "PROBABILITY_METRICS_MISSING", "collected_at": status.get("_collected_at")})
            continue
        samples.append(sample)
    return samples, rejected


def build_markdown(report: Mapping[str, Any]) -> str:
    selected = report.get("selected_profile") if isinstance(report.get("selected_profile"), Mapping) else {}
    selected_cfg = selected.get("profile") if isinstance(selected.get("profile"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.24F Calibration Policy Candidate Gate", "",
        f"- contract_version: `{report.get('contract_version')}`", f"- decision: **{report.get('decision')}**", f"- sample_count: `{report.get('sample_count')}`", f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`", f"- approved_for_live_real: `{report.get('approved_for_live_real')}`", f"- selected_profile: `{selected_cfg.get('name')}`", f"- recommendation: {report.get('recommendation')}", "",
        "## Guardrails", "", f"- observation_only: `{report.get('observation_only')}`", f"- no_post_actions: `{report.get('no_post_actions')}`", f"- config_mutation_performed: `{report.get('config_mutation_performed')}`", f"- order_actions_performed: `{report.get('order_actions_performed')}`", f"- live_real_allowed: `{report.get('live_real_allowed')}`", "",
        "## Profiles", "", "| profile | approvable | decision | score | action_pct | buy/sell/hold | dominant_action_pct | low_margin_pct | reasons | warnings |", "|---|---:|---|---:|---:|---|---:|---:|---|---|",
    ]
    for item in report.get("profiles") or []:
        cfg = item.get("profile") if isinstance(item.get("profile"), Mapping) else {}
        metrics = item.get("metrics") if isinstance(item.get("metrics"), Mapping) else {}
        dist = metrics.get("calibrated_distribution") if isinstance(metrics.get("calibrated_distribution"), Mapping) else {}
        lines.append(f"| {cfg.get('name')} | {item.get('approvable')} | {item.get('decision')} | {item.get('score')} | {metrics.get('calibrated_action_pct')} | BUY={dist.get('BUY', 0)}, SELL={dist.get('SELL', 0)}, HOLD={dist.get('HOLD', 0)} | {metrics.get('dominant_action_pct')} | {metrics.get('low_margin_rejection_pct')} | `{item.get('reason_codes')}` | `{item.get('warnings')}` |")
    lines.extend(["", "## Policy", "", "This gate never applies thresholds automatically. A PASS result only identifies a paper/demo candidate profile. Real live trading remains blocked."])
    return "\n".join(lines) + "\n"


def write_report(out_dir: str | Path, report: dict[str, Any]) -> dict[str, str]:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True); slug = timestamp_slug()
    report_json = out / f"{REPORT_PREFIX}_{slug}.json"; report_md = out / f"{REPORT_PREFIX}_{slug}.md"
    report_json.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    report_md.write_text(build_markdown(report), encoding="utf-8")
    return {"report_json": report_json.as_posix(), "report_md": report_md.as_posix()}


def run_gate(*, base_url: str = DEFAULT_BASE_URL, duration_sec: float = 0.0, interval_sec: float = 60.0, timeout_sec: float = 5.0, max_samples: int = 1, min_samples: int = 30, min_action_pct: float = 2.0, max_action_pct: float = 45.0, max_action_side_pct: float = 85.0, input_json: str | None = None, fetcher: Callable[[str, str, float], dict[str, Any]] | None = None) -> dict[str, Any]:
    rejected: list[dict[str, Any]] = []
    if input_json:
        statuses, report_samples = load_input_payloads(input_json)
        if report_samples:
            samples = report_samples; status_count = 0
        else:
            samples, rejected = build_samples_from_statuses(statuses); status_count = len(statuses)
    else:
        statuses = collect_status_payloads(base_url, duration_sec=duration_sec, interval_sec=interval_sec, timeout_sec=timeout_sec, max_samples=max_samples, fetcher=fetcher)
        samples, rejected = build_samples_from_statuses(statuses); status_count = len(statuses)
    limits = CalibrationPolicyGateLimits(min_samples=int(min_samples), min_action_pct=float(min_action_pct), max_action_pct=float(max_action_pct), max_action_side_pct=float(max_action_side_pct))
    report = build_calibration_policy_gate(samples, limits=limits)
    report.update({"phase": CALIBRATION_POLICY_GATE_CONTRACT_VERSION, "base_url": base_url, "status_count": status_count, "rejected_samples": rejected, "guardrails": {**dict(report.get("guardrails") or {}), "get_only": True, "post_requests_allowed": False}})
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.24F calibration policy candidate gate")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL); parser.add_argument("--duration-min", type=float, default=0.0); parser.add_argument("--interval-sec", type=float, default=60.0); parser.add_argument("--timeout-sec", type=float, default=5.0); parser.add_argument("--min-samples", type=int, default=30); parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--min-action-pct", type=float, default=2.0); parser.add_argument("--max-action-pct", type=float, default=45.0); parser.add_argument("--max-action-side-pct", type=float, default=85.0)
    parser.add_argument("--input-json", default=None); parser.add_argument("--out-dir", default="reports"); parser.add_argument("--once", action="store_true"); parser.add_argument("--review-ok", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args(); duration_sec = 0.0 if args.once else max(0.0, args.duration_min) * 60.0; max_samples = args.max_samples if args.max_samples > 0 else (1 if args.once else max(1, int(duration_sec // max(float(args.interval_sec), 1.0)) + 1))
    report = run_gate(base_url=args.base_url, duration_sec=duration_sec, interval_sec=args.interval_sec, timeout_sec=args.timeout_sec, max_samples=max_samples, min_samples=args.min_samples, min_action_pct=args.min_action_pct, max_action_pct=args.max_action_pct, max_action_side_pct=args.max_action_side_pct, input_json=args.input_json)
    paths = write_report(args.out_dir, report); selected = report.get("selected_profile") if isinstance(report.get("selected_profile"), Mapping) else {}; selected_cfg = selected.get("profile") if isinstance(selected.get("profile"), Mapping) else {}
    print(f"4B.4.3.6.6.24F calibration policy gate {report['decision']}"); print(f" - samples: {report['sample_count']}"); print(f" - approved_for_paper_candidate: {report['approved_for_paper_candidate']}"); print(f" - selected_profile: {selected_cfg.get('name')}"); print(f" - approved_for_live_real: {report['approved_for_live_real']}"); print(f" - recommendation: {report['recommendation']}"); print(f"report_json: {paths['report_json']}"); print(f"report_md: {paths['report_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
