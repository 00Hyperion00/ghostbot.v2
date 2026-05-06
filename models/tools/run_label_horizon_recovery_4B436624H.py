"""4B.4.3.6.6.24H label horizon / target engineering recovery tool.

Public-market-data/GET-only diagnostic tool. It does not mutate config, reload
models, submit orders, or approve real-live trading.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
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

from tradebot.label_horizon_recovery import (  # noqa: E402
    LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
    LabelHorizonGateLimits,
    build_label_horizon_recovery,
    default_label_policy_candidates,
)

PHASE = "4B.4.3.6.6.24H"
REPORT_PREFIX = "4B436624H_label_horizon_recovery"
DEFAULT_BASE_URL = "https://api.binance.com"


class LabelHorizonRecoveryToolError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def compact(value: Any, max_len: int = 700) -> str:
    text = str(value)
    return text if len(text) <= max_len else text[:max_len] + "..."


def fetch_klines(symbol: str, interval: str, days: int, *, base_url: str = DEFAULT_BASE_URL, pause_sec: float = 0.15) -> pd.DataFrame:
    candles_per_call = 1000
    total_candles = max(int(days), 1) * 24 * 60
    all_klines: list[list[Any]] = []
    end_time = int(time.time() * 1000)
    base = base_url.rstrip("/")
    while len(all_klines) < total_candles:
        params = urllib.parse.urlencode({
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": candles_per_call,
            "endTime": end_time,
        })
        url = f"{base}/api/v3/klines?{params}"
        req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            raise LabelHorizonRecoveryToolError(f"HTTP {exc.code}: {exc.reason}") from exc
        except Exception as exc:
            raise LabelHorizonRecoveryToolError(str(exc)) from exc
        if not data:
            break
        all_klines = list(data) + all_klines
        end_time = int(data[0][0]) - 1
        if len(data) < candles_per_call:
            break
        time.sleep(max(0.0, float(pause_sec)))
    if not all_klines:
        raise LabelHorizonRecoveryToolError("No klines returned")
    rows = all_klines[-total_candles:]
    df = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_base",
            "taker_quote",
            "ignore",
        ],
    )
    keep = ["open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"]
    out = df[keep].copy()
    for col in keep:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)


def load_ohlcv_from_json(path: str | Path) -> pd.DataFrame:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        for key in ("ohlcv", "klines", "candles", "rows", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                payload = value
                break
    if not isinstance(payload, list):
        raise LabelHorizonRecoveryToolError("Input JSON must be a list or contain ohlcv/klines/candles rows")
    if payload and isinstance(payload[0], list):
        columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume"]
        payload = [dict(zip(columns, row[: len(columns)])) for row in payload]
    return pd.DataFrame(payload)


def load_ohlcv_from_csv(path: str | Path) -> pd.DataFrame:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        return pd.read_csv(handle, dialect=dialect)


def load_ohlcv(args: argparse.Namespace) -> tuple[pd.DataFrame, str]:
    if args.input_json:
        return load_ohlcv_from_json(args.input_json), str(args.input_json)
    if args.input_csv:
        return load_ohlcv_from_csv(args.input_csv), str(args.input_csv)
    return fetch_klines(args.symbol, args.interval, args.days, base_url=args.base_url), f"{args.base_url}|{args.symbol}|{args.interval}|{args.days}d"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def format_pct(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "0.0000"


def render_markdown(report: Mapping[str, Any]) -> str:
    selected = report.get("selected_policy") if isinstance(report.get("selected_policy"), Mapping) else {}
    selected_policy = selected.get("policy") if isinstance(selected.get("policy"), Mapping) else {}
    lines = [
        f"# {PHASE} Label Horizon / Target Engineering Recovery",
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
        "| policy | approvable | decision | score | samples | action_pct | hold_pct | buy/sell/hold | side_pct | entropy | fwd_gap_bps | reasons | warnings |",
        "|---|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|",
    ])
    for item in report.get("policies") or []:
        if not isinstance(item, Mapping):
            continue
        policy = item.get("policy") if isinstance(item.get("policy"), Mapping) else {}
        metrics = item.get("metrics") if isinstance(item.get("metrics"), Mapping) else {}
        dist = metrics.get("target_distribution") if isinstance(metrics.get("target_distribution"), Mapping) else {}
        lines.append(
            "| {name} | {approvable} | {decision} | {score} | {samples} | {action} | {hold} | BUY={buy}, SELL={sell}, HOLD={hold_n} | {side} | {entropy} | {gap} | `{reasons}` | `{warnings}` |".format(
                name=policy.get("name"),
                approvable=item.get("approvable"),
                decision=item.get("decision"),
                score=item.get("score"),
                samples=item.get("sample_count"),
                action=format_pct(metrics.get("target_action_pct")),
                hold=format_pct(metrics.get("target_hold_pct")),
                buy=dist.get("BUY", 0),
                sell=dist.get("SELL", 0),
                hold_n=dist.get("HOLD", 0),
                side=format_pct(metrics.get("target_action_side_pct")),
                entropy=format_pct(metrics.get("directional_entropy")),
                gap=format_pct(metrics.get("forward_return_gap_bps")),
                reasons=item.get("reason_codes") or [],
                warnings=item.get("warnings") or [],
            )
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This tool never changes label settings, retrains, reloads, mutates config, or sends orders. A PASS only identifies a training-candidate label policy; paper/live trading remains blocked.",
        "",
    ])
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    df, source = load_ohlcv(args)
    limits = LabelHorizonGateLimits(
        min_samples=args.min_samples,
        min_action_pct=args.min_action_pct,
        max_action_pct=args.max_action_pct,
        min_hold_pct=args.min_hold_pct,
        max_hold_pct=args.max_hold_pct,
        max_action_side_pct=args.max_action_side_pct,
        min_directional_entropy=args.min_directional_entropy,
        min_forward_return_gap_bps=args.min_forward_return_gap_bps,
        min_buy_direction_consistency_pct=args.min_buy_direction_consistency_pct,
        min_sell_direction_consistency_pct=args.min_sell_direction_consistency_pct,
        min_class_count=args.min_class_count,
        target_action_pct=args.target_action_pct,
    )
    policies = default_label_policy_candidates()
    if args.max_policies and args.max_policies > 0:
        policies = policies[: int(args.max_policies)]
    report = build_label_horizon_recovery(df, policies=policies, limits=limits, feature_lag=args.feature_lag, source=source)
    report["generated_at"] = utc_now()
    report["symbol"] = args.symbol
    report["interval"] = args.interval
    report["days"] = args.days
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{PHASE} label horizon / target engineering recovery")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--input-json")
    parser.add_argument("--input-csv")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--feature-lag", type=int, default=1)
    parser.add_argument("--max-policies", type=int, default=0, help="Limit candidate policies for smoke tests; 0 means all")
    parser.add_argument("--min-samples", type=int, default=1000)
    parser.add_argument("--min-action-pct", type=float, default=3.0)
    parser.add_argument("--max-action-pct", type=float, default=45.0)
    parser.add_argument("--min-hold-pct", type=float, default=35.0)
    parser.add_argument("--max-hold-pct", type=float, default=92.0)
    parser.add_argument("--max-action-side-pct", type=float, default=78.0)
    parser.add_argument("--min-directional-entropy", type=float, default=0.68)
    parser.add_argument("--min-forward-return-gap-bps", type=float, default=8.0)
    parser.add_argument("--min-buy-direction-consistency-pct", type=float, default=55.0)
    parser.add_argument("--min-sell-direction-consistency-pct", type=float, default=55.0)
    parser.add_argument("--min-class-count", type=int, default=20)
    parser.add_argument("--target-action-pct", type=float, default=18.0)
    parser.add_argument("--review-ok", action="store_true", help="Acknowledge that this diagnostic never approves paper/live trading automatically")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: pass --review-ok to acknowledge this is an observation-only label recovery gate", file=sys.stderr)
        return 2
    try:
        report = run(args)
    except Exception as exc:
        report = {
            "contract_version": LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
            "phase": PHASE,
            "report_type": "label_horizon_target_engineering_recovery",
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
            "reason_codes": ["LABEL_HORIZON_RECOVERY_TOOL_FAILED"],
            "error": compact(exc),
            "recommendation": "Fix data collection or input format before changing label policy.",
        }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = timestamp_slug()
    json_path = out_dir / f"{REPORT_PREFIX}_{slug}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{slug}.md"
    write_json(json_path, report)
    md_path.write_text(render_markdown(report), encoding="utf-8")

    selected = report.get("selected_policy") if isinstance(report.get("selected_policy"), Mapping) else {}
    selected_policy = selected.get("policy") if isinstance(selected.get("policy"), Mapping) else {}
    selected_metrics = selected.get("metrics") if isinstance(selected.get("metrics"), Mapping) else {}
    print(f"{PHASE} label horizon recovery {report.get('decision')}")
    print(f" - samples: {report.get('sample_count', 0)}")
    print(f" - policies: {report.get('policy_count', 0)}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - selected_policy: {selected_policy.get('name')}")
    print(f" - selected_action_pct: {selected_metrics.get('target_action_pct', 0.0)}")
    print(f" - selected_side_pct: {selected_metrics.get('target_action_side_pct', 0.0)}")
    print(f" - reason_codes: {report.get('reason_codes', [])}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path.as_posix()}")
    print(f"report_md: {md_path.as_posix()}")
    return 0 if report.get("decision") in {"PASS", "BLOCK"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
