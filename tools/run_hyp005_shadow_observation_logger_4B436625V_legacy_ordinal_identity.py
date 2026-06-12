from __future__ import annotations

# CLI_MARKERS_25V: __candidate_spec_json __input_json __input_csv __symbols __interval __review_ok ledger_json ledger_jsonl no_order_shadow_only method="GET" public_market_data_GET_only
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp005_r1_canonical_epoch_contract import utc_artifact_stamp  # noqa: E402

from tradebot.research_hyp005_shadow_observation_logger import (  # noqa: E402
    HYP005_SHADOW_OBSERVATION_CONTRACT_VERSION,
    LEDGER_PREFIX,
    REPORT_PREFIX,
    build_hyp005_shadow_observation_logger_report,
    fetch_binance_klines,
    load_json,
    parse_csv_rows,
    write_json,
    write_jsonl,
    report_to_markdown,
)


def latest_report(reports_dir: Path, prefix: str) -> Path | None:
    matches = sorted(reports_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def resolve_candidate_spec(candidate_spec_json: str | None, input_jsons: list[str] | None, reports_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    source_paths: list[str] = []
    if candidate_spec_json:
        payload = load_json(candidate_spec_json)
        source_paths.append(candidate_spec_json)
        if isinstance(payload, dict):
            return payload, source_paths
    for item in input_jsons or []:
        payload = load_json(item)
        source_paths.append(item)
        if isinstance(payload, dict):
            if isinstance(payload.get("candidate_spec"), dict):
                return payload["candidate_spec"], source_paths
            if payload.get("status") == "NO_ORDER_SHADOW_PLAN_READY" or payload.get("strategy_family") == "long_liquidity_sweep_reversal":
                return payload, source_paths
    for prefix in (
        "4B436625U_hyp005_no_order_shadow_candidate_spec",
        "4B436625U_hyp005_no_order_shadow_planning",
    ):
        path = latest_report(reports_dir, prefix)
        payload = load_json(path) if path else None
        if path:
            source_paths.append(str(path))
        if isinstance(payload, dict):
            if isinstance(payload.get("candidate_spec"), dict):
                return payload["candidate_spec"], source_paths
            return payload, source_paths
    return None, source_paths


def parse_symbols(text: str | None) -> list[str]:
    if not text:
        return []
    return [item.strip().upper() for item in text.split(",") if item.strip()]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25V HYP-005 shadow observation logger / no-order runtime probe gate")
    parser.add_argument("--candidate-spec-json", default=None, help="25U candidate spec JSON. Preferred explicit input.")
    parser.add_argument("--input-json", action="append", default=None, help="25U report or candidate spec JSON. Can be supplied multiple times for compatibility.")
    parser.add_argument("--reports-dir", default="reports", help="Directory used to discover latest 25U candidate spec/report if explicit inputs are omitted.")
    parser.add_argument("--include-all", action="store_true", help="Compatibility flag; latest 25U candidate spec/report is selected from reports-dir.")
    parser.add_argument("--input-csv", default=None, help="Optional deterministic OHLCV CSV for no-order shadow scan.")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--timeout-sec", type=int, default=15)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this is no-order shadow observation only.")
    return parser.parse_args(argv)


def load_candles(args: argparse.Namespace, symbols: list[str]) -> list[Any]:
    if args.input_csv:
        default_symbol = symbols[0] if symbols else "TESTUSDT"
        return parse_csv_rows(args.input_csv, default_symbol=default_symbol)
    candles: list[Any] = []
    for symbol in symbols:
        try:
            candles.extend(
                fetch_binance_klines(
                    symbol=symbol,
                    interval=args.interval,
                    days=args.days,
                    base_url=args.base_url,
                    timeout_sec=args.timeout_sec,
                )
            )
        except Exception as exc:  # noqa: BLE001 - optional public GET failure should not trigger side effects.
            print(f"warning: optional public market data GET failed for {symbol}: {exc}", file=sys.stderr)
    return candles


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. 25V is no-order shadow observation only and cannot approve paper/live trading.", file=sys.stderr)
        return 2
    symbols = parse_symbols(args.symbols)
    candidate_spec, source_paths = resolve_candidate_spec(args.candidate_spec_json, args.input_json, Path(args.reports_dir))
    candles = load_candles(args, symbols)
    report = build_hyp005_shadow_observation_logger_report(
        candidate_spec=candidate_spec,
        candles=candles,
        symbols=symbols,
        timeframe=args.interval,
    )
    report["source_reports"] = source_paths
    report["market_data_source"] = "input_csv" if args.input_csv else "public_market_data_GET_only"
    out_dir = Path(args.out_dir)
    stamp = utc_artifact_stamp()
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    ledger_json = out_dir / f"{LEDGER_PREFIX}_{stamp}.json"
    ledger_jsonl = out_dir / f"{LEDGER_PREFIX}_{stamp}.jsonl"
    observations = report.get("shadow_observations") if isinstance(report.get("shadow_observations"), list) else []
    write_json(ledger_json, observations)
    write_jsonl(ledger_jsonl, observations)
    report["ledger_json"] = str(ledger_json)
    report["ledger_jsonl"] = str(ledger_jsonl)
    write_json(json_path, report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    summary = report.get("shadow_summary") if isinstance(report.get("shadow_summary"), dict) else {}
    print(f"{HYP005_SHADOW_OBSERVATION_CONTRACT_VERSION} HYP-005 shadow observation logger {report['decision']}")
    print(f" - source_reports: {len(source_paths)}")
    print(f" - hypothesis_id: {report.get('hypothesis_id')}")
    print(f" - branch_name: {report.get('branch_name')}")
    print(f" - selected_strategy_family: {report.get('selected_strategy_family')}")
    print(f" - no_order_shadow_only: {report.get('no_order_shadow_only')}")
    print(f" - runtime_probe_only: {report.get('runtime_probe_only')}")
    print(f" - symbols_requested: {report.get('symbols_requested')}")
    print(f" - shadow_observation_count: {report.get('shadow_observation_count')}")
    print(f" - shadow_sample_target: {report.get('shadow_sample_target')}")
    print(f" - shadow_sample_target_met: {report.get('shadow_sample_target_met')}")
    print(f" - shadow_mean_forward_edge_bps: {summary.get('shadow_mean_forward_edge_bps')}")
    print(f" - shadow_profit_factor: {summary.get('shadow_profit_factor')}")
    print(f" - approved_for_shadow_candidate: {report.get('approved_for_shadow_candidate')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - warnings: {report.get('warnings')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    print(f"ledger_json: {ledger_json}")
    print(f"ledger_jsonl: {ledger_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
