from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp003_robustness_walkforward import (  # noqa: E402
    HYP003_ROBUSTNESS_CONTRACT_VERSION,
    REPORT_PREFIX,
    build_hyp003_robustness_walkforward_report,
    parse_hyp003_candidate_from_25j,
    render_markdown,
)


def interval_to_ms(interval: str) -> int:
    unit = interval[-1]
    value = int(interval[:-1])
    if unit == "m":
        return value * 60_000
    if unit == "h":
        return value * 3_600_000
    if unit == "d":
        return value * 86_400_000
    raise ValueError(f"unsupported interval: {interval}")


def utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def http_get_json(base_url: str, path: str, params: dict[str, Any], timeout_sec: float) -> Any:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{query}"
    request = Request(url, headers={"User-Agent": f"tradebot-{HYP003_ROBUSTNESS_CONTRACT_VERSION}"}, method="GET")
    try:
        with urlopen(request, timeout=timeout_sec) as response:  # nosec B310 - public market data GET only
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:240]
        except Exception:
            body = ""
        raise RuntimeError(f"GET request failed for {path}: HTTP {exc.code} {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"GET request failed for {path}: {exc}") from exc


def fetch_klines(base_url: str, symbol: str, interval: str, days: int, timeout_sec: float) -> pd.DataFrame:
    end_ms = utc_now_ms()
    start_ms = end_ms - int(days * 86_400_000)
    step_ms = interval_to_ms(interval)
    rows: list[list[Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        payload = http_get_json(
            base_url,
            "/api/v3/klines",
            {"symbol": symbol, "interval": interval, "startTime": cursor, "endTime": end_ms, "limit": 1000},
            timeout_sec,
        )
        if not payload:
            break
        rows.extend(payload)
        next_cursor = int(payload[-1][0]) + step_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(payload) < 1000:
            break
    if not rows:
        raise RuntimeError(f"No kline data returned for {symbol} {interval}")
    return pd.DataFrame(
        {
            "timestamp": [row[0] for row in rows],
            "open": [row[1] for row in rows],
            "high": [row[2] for row in rows],
            "low": [row[3] for row in rows],
            "close": [row[4] for row in rows],
            "volume": [row[5] for row in rows],
        }
    )


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def write_report_bundle(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25K HYP-003 robustness / walk-forward confirmation gate")
    parser.add_argument("--input-json", required=True, help="25J exploration PASS report JSON")
    parser.add_argument("--input-csv", default=None, help="Optional local OHLCV CSV for deterministic evaluation")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--timeout-sec", type=float, default=20.0)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that PASS is research-only and paper/live remain blocked")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. This gate is research-only and cannot authorize training/paper/live.", file=sys.stderr)
        return 2
    source_report = load_json(args.input_json)
    spec = parse_hyp003_candidate_from_25j(source_report)
    if args.input_csv:
        market = pd.read_csv(args.input_csv)
        source = f"csv:{args.input_csv}:{spec.symbol}:{spec.interval}:{spec.strategy}:{spec.regime}"
    else:
        market = fetch_klines(args.base_url, spec.symbol, spec.interval, args.days, args.timeout_sec)
        source = f"binance-spot:{spec.symbol}:{spec.interval}:{args.days}d:{spec.strategy}:{spec.regime}"
    report = build_hyp003_robustness_walkforward_report(market, spec, source=source)
    json_path, md_path = write_report_bundle(report, Path(args.out_dir))
    metrics = report.get("signal_metrics", {})
    print(f"{HYP003_ROBUSTNESS_CONTRACT_VERSION} HYP-003 robustness/walk-forward {report['decision']}")
    print(f" - selected: {spec.symbol} {spec.interval} {spec.strategy} {spec.regime}")
    print(f" - signal_count: {metrics.get('signal_count')}")
    print(f" - mean_net_edge_bps: {metrics.get('mean_net_edge_bps')}")
    print(f" - median_net_edge_bps: {metrics.get('median_net_edge_bps')}")
    print(f" - profit_factor: {metrics.get('profit_factor')}")
    print(f" - walk_forward_positive_rate_pct: {report.get('walk_forward_positive_rate_pct')}")
    print(f" - oos_mean_net_edge_bps: {report.get('oos_segment', {}).get('mean_net_edge_bps')}")
    print(f" - approved_for_research_candidate: {report.get('approved_for_research_candidate')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
