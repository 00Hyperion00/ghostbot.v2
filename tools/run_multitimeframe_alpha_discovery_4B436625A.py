"""4B.4.3.6.6.25A multi-timeframe alpha discovery / research reset tool.

GET-only public-market-data research tool. It does not mutate config, retrain
production models, reload models, submit orders, or approve paper/live trading.
"""

from __future__ import annotations

import argparse
import csv
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

from tradebot.multitimeframe_alpha_discovery import (  # noqa: E402
    MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION,
    MultiTimeframeAlphaGateLimits,
    build_multitimeframe_alpha_discovery,
    default_multitimeframe_alpha_candidates,
)

PHASE = MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION
REPORT_PREFIX = "4B436625A_multitimeframe_alpha_discovery"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def fetch_klines(symbol: str, interval: str, days: int, *, base_url: str) -> pd.DataFrame:
    rows: list[list[Any]] = []
    limit = 1000
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - int(days * 24 * 60 * 60 * 1000)
    url_base = base_url.rstrip("/") + "/api/v3/klines"
    guard = 0
    while start_ms < end_ms and guard < 1200:
        guard += 1
        params = urllib.parse.urlencode({"symbol": symbol, "interval": interval, "limit": limit, "startTime": start_ms, "endTime": end_ms})
        request = urllib.request.Request(f"{url_base}?{params}", method="GET")
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - operator supplied public market-data endpoint
            payload = json.loads(response.read().decode("utf-8"))
        if not payload:
            break
        rows.extend(payload)
        last_open = int(payload[-1][0])
        next_start = last_open + 1
        if next_start <= start_ms:
            break
        start_ms = next_start
        if len(payload) < limit:
            break
        time.sleep(0.04)
    columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]
    return pd.DataFrame([dict(zip(columns, row[: len(columns)])) for row in rows])


def load_ohlcv_from_json(path: str | Path) -> pd.DataFrame:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        for key in ("ohlcv", "klines", "candles", "rows", "data"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise ValueError("input-json must be a list or contain ohlcv/klines/candles rows")
    if payload and isinstance(payload[0], list):
        columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume"]
        payload = [dict(zip(columns, row[: len(columns)])) for row in payload]
    return pd.DataFrame(payload)


def load_ohlcv_from_csv(path: str | Path) -> pd.DataFrame:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
            return pd.read_csv(handle, dialect=dialect)
        except csv.Error:
            handle.seek(0)
            return pd.read_csv(handle)


def load_frames(args: argparse.Namespace) -> tuple[dict[str, pd.DataFrame], str]:
    if args.input_json:
        interval = str(args.input_interval or args.interval or "5m")
        return {interval: load_ohlcv_from_json(args.input_json)}, str(args.input_json)
    if args.input_csv:
        interval = str(args.input_interval or args.interval or "5m")
        return {interval: load_ohlcv_from_csv(args.input_csv)}, str(args.input_csv)
    intervals = [part.strip() for part in str(args.intervals).split(",") if part.strip()]
    frames: dict[str, pd.DataFrame] = {}
    for interval in intervals:
        frames[interval] = fetch_klines(args.symbol, interval, int(args.days), base_url=args.base_url)
    return frames, f"{args.base_url}|{args.symbol}|{','.join(intervals)}|{args.days}d"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def fmt(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "0.0000"


def render_markdown(report: Mapping[str, Any]) -> str:
    selected = report.get("selected_candidate") if isinstance(report.get("selected_candidate"), Mapping) else {}
    selected_policy = selected.get("candidate") if isinstance(selected.get("candidate"), Mapping) else {}
    selected_metrics = selected.get("metrics") if isinstance(selected.get("metrics"), Mapping) else {}
    lines = [
        f"# {PHASE} Multi-Timeframe Alpha Discovery / Research Reset",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected_policy: `{selected_policy.get('name')}`",
        f"- selected_interval: `{selected_policy.get('interval')}`",
        f"- selected_score: `{selected.get('score')}`",
        f"- selected_action_pct: `{fmt(selected_metrics.get('target_action_pct'))}`",
        f"- selected_min_expected_net_edge_bps: `{fmt(selected_metrics.get('min_expected_net_edge_bps'))}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Guardrails",
        "",
    ]
    guardrails = report.get("guardrails") if isinstance(report.get("guardrails"), Mapping) else {}
    for key in ("observation_only", "get_only_public_market_data", "post_requests_allowed", "config_mutation_performed", "order_actions_performed", "reload_performed", "live_real_allowed"):
        lines.append(f"- {key}: `{guardrails.get(key)}`")
    lines.extend([
        "",
        "## Candidates",
        "",
        "| candidate | interval | decision | score | samples | action_pct | hold_pct | buy/sell/hold | side_pct | min_edge_bps | fwd_gap_bps | trend_align_pct | reasons | warnings |",
        "|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|",
    ])
    for item in report.get("candidates") or []:
        if not isinstance(item, Mapping):
            continue
        cand = item.get("candidate") if isinstance(item.get("candidate"), Mapping) else {}
        metrics = item.get("metrics") if isinstance(item.get("metrics"), Mapping) else {}
        dist = metrics.get("target_distribution") if isinstance(metrics.get("target_distribution"), Mapping) else {}
        lines.append(
            "| {name} | {interval} | {decision} | {score} | {samples} | {action} | {hold} | BUY={buy}, SELL={sell}, HOLD={hold_n} | {side} | {edge} | {gap} | {trend} | `{reasons}` | `{warnings}` |".format(
                name=cand.get("name"),
                interval=cand.get("interval"),
                decision=item.get("decision"),
                score=item.get("score"),
                samples=item.get("sample_count"),
                action=fmt(metrics.get("target_action_pct")),
                hold=fmt(metrics.get("target_hold_pct")),
                buy=dist.get("BUY", 0),
                sell=dist.get("SELL", 0),
                hold_n=dist.get("HOLD", 0),
                side=fmt(metrics.get("target_action_side_pct")),
                edge=fmt(metrics.get("min_expected_net_edge_bps")),
                gap=fmt(metrics.get("forward_return_gap_bps")),
                trend=fmt(metrics.get("trend_alignment_pct")),
                reasons=item.get("reason_codes") or [],
                warnings=item.get("warnings") or [],
            )
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This tool is observation-only. A PASS only identifies an offline research/training candidate. It never mutates config, reloads models, starts paper trading, or sends orders; real live trading remains blocked.",
        "",
    ])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4B436625A multi-timeframe alpha discovery / research reset")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="5m", help="interval used for input CSV/JSON")
    parser.add_argument("--input-interval", default=None, help="explicit interval for input CSV/JSON")
    parser.add_argument("--intervals", default="5m,15m,1h", help="comma-separated Binance intervals for public data fetch")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--input-json")
    parser.add_argument("--input-csv")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--min-samples", type=int, default=None)
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--review-ok", action="store_true", help="required acknowledgement that this is observation-only")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required; this is an observation-only research gate.", file=sys.stderr)
        return 2
    try:
        frames, source = load_frames(args)
        limits = MultiTimeframeAlphaGateLimits(min_samples=int(args.min_samples)) if args.min_samples else MultiTimeframeAlphaGateLimits()
        candidates = default_multitimeframe_alpha_candidates()
        if args.max_candidates is not None:
            candidates = candidates[: max(1, int(args.max_candidates))]
        report = build_multitimeframe_alpha_discovery(frames, candidates=candidates, limits=limits, source=source)
    except Exception as exc:
        report = {
            "contract_version": PHASE,
            "phase": PHASE,
            "report_type": "multitimeframe_alpha_discovery_research_reset",
            "decision": "BLOCK",
            "ok": False,
            "approved_for_training_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "live_real_allowed": False,
            "observation_only": True,
            "get_only_public_market_data": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "reason_codes": ["MULTITIMEFRAME_ALPHA_DISCOVERY_TOOL_FAILED"],
            "recommendation": f"Tool failed before producing a valid research report: {exc}",
            "candidates": [],
            "guardrails": {
                "observation_only": True,
                "get_only_public_market_data": True,
                "post_requests_allowed": False,
                "config_mutation_performed": False,
                "order_actions_performed": False,
                "reload_performed": False,
                "live_real_allowed": False,
            },
        }
    stamp = utc_stamp()
    out_dir = Path(args.out_dir)
    report_json = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json(report_json, report)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(render_markdown(report), encoding="utf-8")
    selected = report.get("selected_candidate") if isinstance(report.get("selected_candidate"), Mapping) else {}
    selected_candidate = selected.get("candidate") if isinstance(selected.get("candidate"), Mapping) else {}
    selected_metrics = selected.get("metrics") if isinstance(selected.get("metrics"), Mapping) else {}
    print(f"{PHASE} multi-timeframe alpha discovery {report.get('decision')}")
    print(f" - candidates: {report.get('candidate_count')}")
    print(f" - intervals: {report.get('intervals')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - selected_policy: {selected_candidate.get('name')}")
    print(f" - selected_interval: {selected_candidate.get('interval')}")
    print(f" - selected_min_expected_net_edge_bps: {fmt(selected_metrics.get('min_expected_net_edge_bps'))}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {report_json.as_posix()}")
    print(f"report_md: {report_md.as_posix()}")
    return 0 if bool(report.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
