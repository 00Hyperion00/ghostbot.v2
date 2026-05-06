"""4B.4.3.6.6.24I cost-aware label policy recovery tool.

GET-only/public-market-data diagnostic tool. It does not mutate config, reload
models, train models, submit orders, or approve real-live trading.
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

from tradebot.cost_aware_label_policy_recovery import (  # noqa: E402
    COST_AWARE_LABEL_POLICY_CONTRACT_VERSION,
    CostAwareLabelPolicyGateLimits,
    build_cost_aware_label_policy_recovery,
)

PHASE = COST_AWARE_LABEL_POLICY_CONTRACT_VERSION
REPORT_PREFIX = "4B436624I_cost_aware_label_policy_recovery"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def fetch_klines(symbol: str, interval: str, days: int, *, base_url: str) -> pd.DataFrame:
    rows: list[list[Any]] = []
    limit = 1000
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - int(days * 24 * 60 * 60 * 1000)
    url_base = base_url.rstrip("/") + "/api/v3/klines"
    while start_ms < end_ms and len(rows) < days * 24 * 60 + limit:
        params = urllib.parse.urlencode({"symbol": symbol, "interval": interval, "limit": limit, "startTime": start_ms, "endTime": end_ms})
        request = urllib.request.Request(f"{url_base}?{params}", method="GET")
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - user-supplied market data endpoint
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


def load_ohlcv(args: argparse.Namespace) -> tuple[pd.DataFrame, str]:
    if args.input_json:
        return load_ohlcv_from_json(args.input_json), str(args.input_json)
    if args.input_csv:
        return load_ohlcv_from_csv(args.input_csv), str(args.input_csv)
    return fetch_klines(args.symbol, args.interval, args.days, base_url=args.base_url), f"{args.base_url}|{args.symbol}|{args.interval}|{args.days}d"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def fmt(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "0.0000"


def render_markdown(report: Mapping[str, Any]) -> str:
    selected = report.get("selected_policy") if isinstance(report.get("selected_policy"), Mapping) else {}
    selected_policy = selected.get("policy") if isinstance(selected.get("policy"), Mapping) else {}
    lines = [
        f"# {PHASE} Cost-Aware Label Policy Recovery",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- sample_count: `{report.get('sample_count')}`",
        f"- policy_count: `{report.get('policy_count')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected_policy: `{selected_policy.get('name')}`",
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
        "## Policies",
        "",
        "| policy | approvable | decision | score | samples | action_pct | hold_pct | buy/sell/hold | side_pct | fwd_gap_bps | min_net_edge_bps | effective_floor_bps | reasons | warnings |",
        "|---|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|",
    ])
    for item in report.get("policies") or []:
        if not isinstance(item, Mapping):
            continue
        policy = item.get("policy") if isinstance(item.get("policy"), Mapping) else {}
        metrics = item.get("metrics") if isinstance(item.get("metrics"), Mapping) else {}
        dist = metrics.get("target_distribution") if isinstance(metrics.get("target_distribution"), Mapping) else {}
        lines.append(
            "| {name} | {approvable} | {decision} | {score} | {samples} | {action} | {hold} | BUY={buy}, SELL={sell}, HOLD={hold_n} | {side} | {gap} | {edge} | {floor} | `{reasons}` | `{warnings}` |".format(
                name=policy.get("name"),
                approvable=item.get("approvable"),
                decision=item.get("decision"),
                score=item.get("score"),
                samples=item.get("sample_count"),
                action=fmt(metrics.get("target_action_pct")),
                hold=fmt(metrics.get("target_hold_pct")),
                buy=dist.get("BUY", 0),
                sell=dist.get("SELL", 0),
                hold_n=dist.get("HOLD", 0),
                side=fmt(metrics.get("target_action_side_pct")),
                gap=fmt(metrics.get("forward_return_gap_bps")),
                edge=fmt(metrics.get("min_expected_net_edge_bps")),
                floor=fmt(metrics.get("effective_min_profit_bps")),
                reasons=item.get("reason_codes") or [],
                warnings=item.get("warnings") or [],
            )
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This tool never changes label settings, retrains, reloads, mutates config, starts paper trading, or sends orders. A PASS only identifies a training-candidate cost-aware label policy; paper/live trading remains blocked.",
        "",
    ])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4B436624I cost-aware label policy recovery")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--input-json")
    parser.add_argument("--input-csv")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--min-samples", type=int, default=None)
    parser.add_argument("--max-policies", type=int, default=None)
    parser.add_argument("--review-ok", action="store_true", help="required acknowledgement that this is observation-only")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required; this is a diagnostic-only gate and must be reviewed by the operator.", file=sys.stderr)
        return 2
    try:
        df, source = load_ohlcv(args)
        limits = CostAwareLabelPolicyGateLimits(min_samples=int(args.min_samples)) if args.min_samples else CostAwareLabelPolicyGateLimits()
        from tradebot.cost_aware_label_policy_recovery import default_cost_aware_label_policy_candidates

        policies = default_cost_aware_label_policy_candidates()
        if args.max_policies is not None:
            policies = policies[: max(1, int(args.max_policies))]
        report = build_cost_aware_label_policy_recovery(df, policies=policies, limits=limits, source=source)
    except Exception as exc:
        report = {
            "contract_version": PHASE,
            "phase": PHASE,
            "report_type": "cost_aware_label_policy_recovery",
            "decision": "BLOCK",
            "ok": False,
            "approved_for_training_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "live_real_allowed": False,
            "observation_only": True,
            "no_post_actions": True,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "sample_count": 0,
            "policy_count": 0,
            "selected_policy_name": None,
            "selected_policy": None,
            "policies": [],
            "reason_codes": ["COST_AWARE_LABEL_POLICY_TOOL_FAILED"],
            "warnings": [str(exc)[:500]],
            "recommendation": "Tool failed before a valid diagnostic report could be produced.",
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
    out_dir = Path(args.out_dir)
    stamp = utc_stamp()
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json(json_path, report)
    md_path.write_text(render_markdown(report), encoding="utf-8")

    selected = report.get("selected_policy") if isinstance(report.get("selected_policy"), Mapping) else {}
    selected_policy = selected.get("policy") if isinstance(selected.get("policy"), Mapping) else {}
    selected_metrics = selected.get("metrics") if isinstance(selected.get("metrics"), Mapping) else {}
    print(f"{PHASE} cost-aware label policy recovery {report.get('decision')}")
    print(f" - samples: {report.get('sample_count')}")
    print(f" - policies: {report.get('policy_count')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - selected_policy: {selected_policy.get('name')}")
    print(f" - selected_action_pct: {selected_metrics.get('target_action_pct')}")
    print(f" - selected_hold_pct: {selected_metrics.get('target_hold_pct')}")
    print(f" - selected_min_net_edge_bps: {selected_metrics.get('min_expected_net_edge_bps')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path.as_posix()}")
    print(f"report_md: {md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
