"""4B.4.3.6.6.24G probability separation / label calibration recovery tool.

GET-only diagnostic tool. It does not reload models, mutate config, submit orders,
or approve real-live trading.
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
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.probability_separation_gate import (  # noqa: E402
    PROBABILITY_SEPARATION_GATE_CONTRACT_VERSION,
    ProbabilitySeparationGateConfig,
    build_probability_separation_recovery,
    extract_probability_samples_from_payload,
)
from tradebot.runtime_calibration_probe import extract_runtime_probability_sample  # noqa: E402

PHASE = "4B.4.3.6.6.24G"
REPORT_PREFIX = "4B436624G_probability_separation_recovery"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


class ProbabilitySeparationToolError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def compact(value: Any, max_len: int = 700) -> str:
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
        raise ProbabilitySeparationToolError(f"HTTP {exc.code}: {exc.reason}") from exc
    except Exception as exc:
        raise ProbabilitySeparationToolError(str(exc)) from exc


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
        if duration_sec <= 0:
            break
        elapsed = time.monotonic() - started
        if elapsed >= duration_sec:
            break
        time.sleep(max(0.0, min(interval_sec, duration_sec - elapsed)))
    return statuses


def extract_samples_from_statuses(statuses: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    samples: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for idx, status in enumerate(statuses):
        sample = extract_runtime_probability_sample(status, sample_index=idx)
        if sample is None:
            rejected.append({
                "sample_index": idx,
                "reason": "STATUS_PROBABILITY_METRICS_MISSING",
                "error": status.get("_probe_error"),
                "collected_at": status.get("_probe_collected_at"),
            })
        else:
            sample["collected_at"] = status.get("_probe_collected_at")
            samples.append(sample)
    return samples, rejected


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _training_from_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None
    if isinstance(payload.get("training"), Mapping):
        return dict(payload["training"])
    if payload.get("report_type") in {"training_result", "retrain_candidate_quality"} and (
        "calibrated_action_report" in payload or "target_distribution" in payload
    ):
        return dict(payload)
    candidates = payload.get("candidates")
    if isinstance(candidates, list):
        selected = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else {}
        selected_model_path = None
        best = selected.get("best_candidate") if isinstance(selected.get("best_candidate"), Mapping) else None
        if best is not None:
            selected_model_path = best.get("model_path")
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            training = candidate.get("training") if isinstance(candidate.get("training"), Mapping) else None
            if training is None:
                continue
            if selected_model_path and candidate.get("model_path") == selected_model_path:
                return dict(training)
        for candidate in candidates:
            if isinstance(candidate, Mapping) and candidate.get("decision") == "PASS" and isinstance(candidate.get("training"), Mapping):
                return dict(candidate["training"])
    return None


def load_input_bundle(input_json: str | None, training_json: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None, str | None]:
    if not input_json:
        training = load_json(training_json) if training_json else None
        return [], [], training if isinstance(training, dict) else None, None
    payload = load_json(input_json)
    samples, rejected = extract_probability_samples_from_payload(payload)
    training = _training_from_payload(payload)
    if training_json:
        loaded_training = load_json(training_json)
        if isinstance(loaded_training, dict):
            training = loaded_training
    return samples, rejected, training, input_json


def build_markdown(report: Mapping[str, Any]) -> str:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), Mapping) else {}
    label = report.get("label_calibration") if isinstance(report.get("label_calibration"), Mapping) else {}
    label_metrics = label.get("metrics") if isinstance(label.get("metrics"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.24G Probability Separation / Label Calibration Recovery",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- sample_count: `{report.get('sample_count')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Probability Separation",
        "",
        f"- raw_distribution: `{metrics.get('raw_distribution')}`",
        f"- raw_action_pct: `{metrics.get('raw_action_pct')}`",
        f"- current_distribution: `{metrics.get('current_distribution')}`",
        f"- current_action_pct: `{metrics.get('current_action_pct')}`",
        f"- low_margin_rejection_pct: `{metrics.get('low_margin_rejection_pct')}`",
        f"- raw_action_side_pct: `{metrics.get('raw_action_side_pct')}`",
        f"- directional_entropy: `{metrics.get('directional_entropy')}`",
        f"- buy_sell_margin: `{metrics.get('buy_sell_margin')}`",
        f"- action_vs_hold_margin: `{metrics.get('action_vs_hold_margin')}`",
        "",
        "## Label Calibration",
        "",
        f"- label_decision: `{label.get('decision')}`",
        f"- target_distribution: `{label_metrics.get('target_distribution')}`",
        f"- target_action_rate: `{label_metrics.get('target_action_rate')}`",
        f"- predicted_action_rate: `{label_metrics.get('predicted_action_rate')}`",
        f"- calibrated_action_rate: `{label_metrics.get('calibrated_action_rate')}`",
        f"- synthetic_class_padding_applied: `{label_metrics.get('synthetic_class_padding_applied')}`",
        "",
        "## Reason Codes",
        "",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- warnings: `{report.get('warnings')}`",
        "",
        "## Guardrails",
        "",
        f"- observation_only: `{report.get('guardrails', {}).get('observation_only')}`",
        f"- no_post_actions: `{report.get('guardrails', {}).get('no_post_actions')}`",
        f"- config_mutation_performed: `{report.get('guardrails', {}).get('config_mutation_performed')}`",
        f"- reload_performed: `{report.get('guardrails', {}).get('reload_performed')}`",
        f"- order_actions_performed: `{report.get('guardrails', {}).get('order_actions_performed')}`",
        f"- live_real_allowed: `{report.get('guardrails', {}).get('live_real_allowed')}`",
        "",
        "## Policy",
        "",
        "This report never applies thresholds, reloads models, submits orders, or arms live trading. A PASS result is paper/demo evidence only.",
    ]
    return "\n".join(lines) + "\n"


def write_report(out_dir: str | Path, report: dict[str, Any]) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slug = timestamp_slug()
    json_path = out / f"{REPORT_PREFIX}_{slug}.json"
    md_path = out / f"{REPORT_PREFIX}_{slug}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True, default=str), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    return {"report_json": json_path.as_posix(), "report_md": md_path.as_posix()}


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_json or args.training_json:
        samples, rejected, training, source_path = load_input_bundle(args.input_json, args.training_json)
        status_count = 0
    else:
        statuses = collect_status_payloads(
            args.base_url,
            duration_sec=float(args.duration_min) * 60.0,
            interval_sec=float(args.interval_sec),
            timeout_sec=float(args.timeout_sec),
            max_samples=int(args.max_samples),
        )
        samples, rejected = extract_samples_from_statuses(statuses)
        training = None
        source_path = None
        status_count = len(statuses)

    config = ProbabilitySeparationGateConfig(
        min_samples=int(args.min_samples),
        min_buy_sell_margin_mean=float(args.min_buy_sell_margin_mean),
        min_buy_sell_margin_median=float(args.min_buy_sell_margin_median),
        min_action_hold_margin_mean=float(args.min_action_hold_margin_mean),
        max_raw_action_pct=float(args.max_raw_action_pct),
        min_raw_action_pct=float(args.min_raw_action_pct),
        max_action_side_pct=float(args.max_action_side_pct),
        min_directional_entropy=float(args.min_directional_entropy),
        max_low_margin_reject_pct=float(args.max_low_margin_reject_pct),
        max_current_action_pct=float(args.max_current_action_pct),
        min_current_action_pct_for_ready=float(args.min_current_action_pct_for_ready),
    )
    report = build_probability_separation_recovery(
        samples=samples,
        training_result=training,
        rejected_samples=rejected,
        config=config,
    )
    report.update({
        "base_url": args.base_url,
        "source_input_json": source_path,
        "status_count": status_count,
        "no_post_actions": True,
        "observation_only": True,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
    })
    paths = write_report(args.out_dir, report)
    report.update(paths)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.24G probability separation / label calibration recovery")
    parser.add_argument("--input-json", default=None, help="24E runtime probe report, status payload list, or training report JSON")
    parser.add_argument("--training-json", default=None, help="Optional training result JSON to add label calibration context")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--duration-min", type=float, default=0.0)
    parser.add_argument("--interval-sec", type=float, default=60.0)
    parser.add_argument("--timeout-sec", type=float, default=5.0)
    parser.add_argument("--max-samples", type=int, default=10_000)
    parser.add_argument("--min-samples", type=int, default=30)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Acknowledge that this is an observation-only diagnostic run")
    parser.add_argument("--min-buy-sell-margin-mean", type=float, default=0.015)
    parser.add_argument("--min-buy-sell-margin-median", type=float, default=0.010)
    parser.add_argument("--min-action-hold-margin-mean", type=float, default=0.060)
    parser.add_argument("--max-raw-action-pct", type=float, default=85.0)
    parser.add_argument("--min-raw-action-pct", type=float, default=2.0)
    parser.add_argument("--max-action-side-pct", type=float, default=80.0)
    parser.add_argument("--min-directional-entropy", type=float, default=0.55)
    parser.add_argument("--max-low-margin-reject-pct", type=float, default=60.0)
    parser.add_argument("--max-current-action-pct", type=float, default=45.0)
    parser.add_argument("--min-current-action-pct-for-ready", type=float, default=2.0)
    args = parser.parse_args()

    if not args.review_ok:
        print("Refusing to run without --review-ok. This diagnostic is observation-only and does not change thresholds.", file=sys.stderr)
        raise SystemExit(2)

    report = run(args)
    print(f"4B.4.3.6.6.24G probability separation recovery {report.get('decision')}")
    print(f" - samples: {report.get('sample_count')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    metrics = report.get("metrics") if isinstance(report.get("metrics"), Mapping) else {}
    print(f" - buy_sell_margin_mean: {metrics.get('buy_sell_margin', {}).get('mean') if isinstance(metrics.get('buy_sell_margin'), Mapping) else None}")
    print(f" - buy_sell_margin_median: {metrics.get('buy_sell_margin', {}).get('median') if isinstance(metrics.get('buy_sell_margin'), Mapping) else None}")
    print(f" - raw_action_pct: {metrics.get('raw_action_pct')}")
    print(f" - current_action_pct: {metrics.get('current_action_pct')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {report.get('report_json')}")
    print(f"report_md: {report.get('report_md')}")
    raise SystemExit(0 if report.get("decision") != "BLOCK" else 1)


if __name__ == "__main__":
    main()
