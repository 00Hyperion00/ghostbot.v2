"""4B.4.3.6.6.24L regime-aware edge filter recovery.

Evaluates whether two-stage ACTION/SIDE signals have positive expected edge in specific
market regimes. This tool never reloads models, mutates config, starts paper trading,
or sends orders. A PASS only identifies a training-candidate regime filter.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.regime_aware_edge_filter_recovery import (  # noqa: E402
    REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION,
    build_report_from_two_stage_json,
    policy_candidates_from_input,
    train_regime_edge_filter_candidates,
)
from tradebot.two_stage_action_side_recovery import TwoStageActionSideCandidateSpec  # noqa: E402
from tradebot.cost_aware_label_policy_recovery import default_cost_aware_label_policy_candidates  # noqa: E402

PHASE = REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION
REPORT_PREFIX = "4B436624L_regime_aware_edge_filter_recovery"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def fetch_klines(symbol: str, interval: str, days: int, *, base_url: str = "https://api.binance.com") -> pd.DataFrame:
    candles_per_call = 1000
    total_candles = max(1, int(days)) * 24 * 60
    end_time = int(time.time() * 1000)
    all_klines: list[list[Any]] = []
    base = str(base_url).rstrip("/")
    while len(all_klines) < total_candles:
        query = urllib.parse.urlencode({"symbol": symbol.upper(), "interval": interval, "limit": candles_per_call, "endTime": end_time})
        url = f"{base}/api/v3/klines?{query}"
        with urllib.request.urlopen(url, timeout=25) as response:  # noqa: S310 - operator-supplied public market-data URL
            data = json.loads(response.read().decode("utf-8"))
        if not data:
            break
        all_klines = list(data) + all_klines
        end_time = int(data[0][0]) - 1
        time.sleep(0.15)
    if not all_klines:
        raise RuntimeError("No klines returned")
    rows = all_klines[-total_candles:]
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore"])
    return df[["open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"]].astype(float)


def load_ohlcv(args: argparse.Namespace) -> tuple[pd.DataFrame, str]:
    if args.input_csv:
        return pd.read_csv(args.input_csv), f"csv:{args.input_csv}"
    return fetch_klines(args.symbol, args.interval, int(args.days), base_url=args.base_url), f"binance:{args.symbol}:{args.interval}:{args.days}d"


def load_input_payload(path: str | None) -> Mapping[str, Any] | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_specs(args: argparse.Namespace, payload: Mapping[str, Any] | None) -> list[TwoStageActionSideCandidateSpec]:
    if payload:
        policies = policy_candidates_from_input(payload, limit=int(args.policy_limit))
    elif args.policies:
        wanted = {item.strip() for item in str(args.policies).split(",") if item.strip()}
        policies = [p for p in default_cost_aware_label_policy_candidates() if p.name in wanted]
    else:
        preferred = {"h30_cost16_edge30_atr3_0", "h20_cost16_edge25_atr2_5", "h15_cost12_edge20_atr2_0", "h5_cost8_edge10_atr1_5"}
        policies = [p for p in default_cost_aware_label_policy_candidates() if p.name in preferred]
    action_profiles = [item.strip() for item in str(args.action_profiles).split(",") if item.strip()]
    side_profiles = [item.strip() for item in str(args.side_profiles).split(",") if item.strip()]
    action_thresholds = [item.strip() for item in str(args.action_threshold_profiles).split(",") if item.strip()]
    side_margins = [item.strip() for item in str(args.side_margin_profiles).split(",") if item.strip()]
    specs: list[TwoStageActionSideCandidateSpec] = []
    for policy in policies:
        for action_profile in action_profiles:
            for side_profile in side_profiles:
                for action_threshold in action_thresholds:
                    for side_margin in side_margins:
                        specs.append(
                            TwoStageActionSideCandidateSpec(
                                label_policy=policy,
                                action_profile=action_profile,
                                side_profile=side_profile,
                                action_threshold_profile=action_threshold,
                                side_margin_profile=side_margin,
                                n_estimators=int(args.n_estimators),
                                max_depth=int(args.max_depth),
                                learning_rate=float(args.learning_rate),
                            )
                        )
                        if len(specs) >= int(args.max_candidates):
                            return specs
    return specs


def select_best_report(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        raise RuntimeError("No regime reports produced")
    best = max(reports, key=lambda r: float(r.get("selected_score") or -1e9))
    if any(r.get("decision") == "PASS" for r in reports):
        best = max((r for r in reports if r.get("decision") == "PASS"), key=lambda r: float(r.get("selected_score") or -1e9))
    merged = dict(best)
    merged["candidate_run_count"] = len(reports)
    merged["candidate_runs"] = reports
    return merged


def write_reports(report: Mapping[str, Any], *, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    json_path = out / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out / f"{REPORT_PREFIX}_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def render_markdown(report: Mapping[str, Any]) -> str:
    selection = report.get("selection") if isinstance(report.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    best_metrics = best.get("metrics") if isinstance(best.get("metrics"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.24L Regime-Aware Edge Filter Recovery",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- candidate_run_count: `{report.get('candidate_run_count', 1)}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected_filter: `{report.get('selected_filter')}`",
        f"- selected_score: `{_fmt(report.get('selected_score'))}`",
        f"- selected_filtered_action_pct: `{_fmt(report.get('selected_filtered_action_pct'))}`",
        f"- selected_action_precision: `{_fmt(report.get('selected_action_precision'))}`",
        f"- selected_side_accuracy: `{_fmt(report.get('selected_side_accuracy'))}`",
        f"- selected_expected_edge_proxy_bps: `{_fmt(report.get('selected_expected_edge_proxy_bps'))}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Guardrails",
        "",
    ]
    guard = report.get("guardrails") if isinstance(report.get("guardrails"), Mapping) else {}
    for key in ("observation_only", "no_post_actions", "post_requests_allowed", "config_mutation_performed", "order_actions_performed", "reload_performed", "live_real_allowed", "promotion_requires_explicit_flag"):
        lines.append(f"- {key}: `{guard.get(key)}`")
    lines.extend([
        "",
        "## Baseline",
        "",
    ])
    base = report.get("baseline") if isinstance(report.get("baseline"), Mapping) else {}
    for key in ("validation_staged_action_pct", "validation_action_precision", "validation_action_recall", "validation_side_accuracy", "expected_edge_proxy_bps"):
        lines.append(f"- {key}: `{_fmt(base.get(key))}`")
    lines.extend([
        "",
        "## Selected Filter Metrics",
        "",
        f"- reason_codes: `{best.get('reason_codes') or []}`",
        f"- filtered_action_count: `{_fmt(best_metrics.get('filtered_action_count'))}`",
        f"- filtered_action_pct: `{_fmt(best_metrics.get('filtered_action_pct'))}`",
        f"- action_precision: `{_fmt(best_metrics.get('action_precision'))}`",
        f"- action_precision_lift: `{_fmt(best_metrics.get('action_precision_lift'))}`",
        f"- action_recall: `{_fmt(best_metrics.get('action_recall'))}`",
        f"- filtered_side_accuracy: `{_fmt(best_metrics.get('filtered_side_accuracy'))}`",
        f"- filtered_action_side_pct: `{_fmt(best_metrics.get('filtered_action_side_pct'))}`",
        f"- expected_edge_proxy_bps: `{_fmt(best_metrics.get('expected_edge_proxy_bps'))}`",
        "",
        "## Filter Candidates",
        "",
        "| # | decision | score | filter | family | action_pct | precision | precision_lift | side_accuracy | edge_proxy_bps | reasons | warnings |",
        "|---:|---|---:|---|---|---:|---:|---:|---:|---:|---|---|",
    ])
    for idx, item in enumerate(report.get("candidates") or [], start=1):
        if not isinstance(item, Mapping):
            continue
        filt = item.get("filter") if isinstance(item.get("filter"), Mapping) else {}
        metrics = item.get("metrics") if isinstance(item.get("metrics"), Mapping) else {}
        lines.append(
            "| {idx} | {decision} | {score} | {name} | {family} | {action_pct} | {precision} | {lift} | {side_acc} | {edge} | `{reasons}` | `{warnings}` |".format(
                idx=idx,
                decision=item.get("decision"),
                score=_fmt(item.get("score")),
                name=filt.get("name"),
                family=filt.get("family"),
                action_pct=_fmt(metrics.get("filtered_action_pct")),
                precision=_fmt(metrics.get("action_precision")),
                lift=_fmt(metrics.get("action_precision_lift")),
                side_acc=_fmt(metrics.get("filtered_side_accuracy")),
                edge=_fmt(metrics.get("expected_edge_proxy_bps")),
                reasons=item.get("reason_codes") or [],
                warnings=item.get("warnings") or [],
            )
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This tool may train temporary two-stage candidates for validation and regime analysis, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a training-candidate regime filter for manual review; real live trading remains blocked.",
        "",
    ])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.24L regime-aware edge filter recovery")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--input-csv")
    parser.add_argument("--input-json", help="24I cost-aware policy report or 24K aggregate report")
    parser.add_argument("--policies", help="Comma-separated policy names")
    parser.add_argument("--policy-limit", type=int, default=3)
    parser.add_argument("--action-profiles", default="balanced")
    parser.add_argument("--side-profiles", default="balanced")
    parser.add_argument("--action-threshold-profiles", default="recall_light,balanced")
    parser.add_argument("--side-margin-profiles", default="strict,guarded,balanced")
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--n-estimators", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.04)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_input_payload(args.input_json)
    if payload and (str(payload.get("contract_version", "")).endswith("24K") or payload.get("report_type") == "two_stage_action_side_recovery") and not args.input_csv and not args.review_ok:
        report = build_report_from_two_stage_json(payload)
    else:
        ohlcv, source = load_ohlcv(args)
        specs = build_specs(args, payload)
        if not specs:
            raise RuntimeError("No two-stage regime candidate specs built")
        reports = [
            train_regime_edge_filter_candidates(ohlcv, spec, symbol=args.symbol, interval=args.interval, days=int(args.days))
            for spec in specs[: int(args.max_candidates)]
        ]
        report = select_best_report(reports)
        report["source"] = source
    json_path, md_path = write_reports(report, out_dir=args.out_dir)
    print(f"{PHASE} regime-aware edge filter recovery {report.get('decision')}")
    print(f" - candidates: {report.get('candidate_count')}")
    print(f" - candidate_runs: {report.get('candidate_run_count', 1)}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - selected_filter: {report.get('selected_filter')}")
    print(f" - selected_expected_edge_proxy_bps: {report.get('selected_expected_edge_proxy_bps')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path.as_posix()}")
    print(f"report_md: {md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
