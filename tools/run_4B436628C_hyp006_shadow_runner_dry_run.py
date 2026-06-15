from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tradebot.hyp006_shadow_runner_dry_run import (  # noqa: E402
    BRANCH_ID,
    CONTRACT_VERSION,
    build_hyp006_shadow_runner_dry_run_report,
    fetch_public_klines,
    load_json,
    load_jsonl,
    parse_csv_rows,
    write_report_bundle,
)


def parse_symbols(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="4B436628C HYP-006-R1 no-order shadow runner dry-run")
    parser.add_argument("--registration-json", required=True, help="28B registration gate report JSON or candidate spec JSON")
    parser.add_argument("--input-csv", default=None, help="Optional local OHLCV CSV for deterministic dry-run")
    parser.add_argument("--existing-ledger-jsonl", default=None, help="Optional existing HYP-006 JSONL ledger for duplicate guard")
    parser.add_argument("--symbols", default="", help="Comma-separated symbols for public GET mode")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--out-dir", default="reports/hyp006_r1_canonical")
    parser.add_argument("--review-ok", action="store_true", help="Required explicit operator acknowledgement for no-order dry-run")
    args = parser.parse_args(argv)

    if not args.review_ok:
        raise SystemExit("REVIEW_OK_REQUIRED_FOR_28C_NO_ORDER_DRY_RUN")

    registration_path = Path(args.registration_json).resolve()
    registration_payload: dict[str, Any] = load_json(registration_path)
    existing_rows = load_jsonl(args.existing_ledger_jsonl) if args.existing_ledger_jsonl else []
    network_request_performed = False
    candles = []
    requested_symbols = parse_symbols(args.symbols)
    source_paths: dict[str, Any] = {
        "registration_json": str(registration_path),
        "input_csv": None,
        "existing_ledger_jsonl": None if args.existing_ledger_jsonl is None else str(Path(args.existing_ledger_jsonl).resolve()),
    }

    if args.input_csv:
        csv_path = Path(args.input_csv).resolve()
        candles = parse_csv_rows(csv_path)
        if not requested_symbols:
            requested_symbols = sorted({item.symbol for item in candles})
        source_paths["input_csv"] = str(csv_path)
    else:
        if not requested_symbols:
            raise SystemExit("SYMBOLS_REQUIRED_WHEN_INPUT_CSV_IS_NOT_USED")
        for symbol in requested_symbols:
            candles.extend(fetch_public_klines(symbol=symbol, interval=args.interval, days=args.days, base_url=args.base_url))
        network_request_performed = True

    out_dir = Path(args.out_dir)
    report = build_hyp006_shadow_runner_dry_run_report(
        candidate_spec_source=registration_payload,
        candles=candles,
        symbols=requested_symbols,
        existing_ledger_rows=existing_rows,
        source_paths=source_paths,
        network_request_performed=network_request_performed,
        out_dir=out_dir,
    )
    report_json, ledger_jsonl, report_md = write_report_bundle(report, out_dir)

    summary = report.get("dry_run_summary", {})
    preflight = report.get("scheduler_registration_preflight", {})
    print(f"{CONTRACT_VERSION} {BRANCH_ID} no-order shadow runner dry-run {report.get('decision')}")
    print(f" - read_only: {report.get('read_only')}")
    print(f" - no_order_shadow_runner_dry_run_only: {report.get('no_order_shadow_runner_dry_run_only')}")
    print(f" - network_request_performed: {report.get('network_request_performed')}")
    print(f" - dry_run_observation_count: {summary.get('dry_run_observation_count')}")
    print(f" - new_unique_dry_run_observation_count: {summary.get('new_unique_dry_run_observation_count')}")
    print(f" - duplicate_existing_observation_count: {summary.get('duplicate_existing_observation_count')}")
    print(f" - operator_registration_approval_gate_ready: {report.get('operator_registration_approval_gate_ready')}")
    print(f" - proposed_task_name: {preflight.get('proposed_task_name')}")
    print(f" - scheduler_mutation_performed: {report.get('scheduler_mutation_performed')}")
    print(f" - approved_for_shadow_collection: {report.get('approved_for_shadow_collection')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f"report_json: {report_json}")
    print(f"dry_run_ledger_jsonl: {ledger_jsonl}")
    print(f"report_md: {report_md}")
    return 0 if report.get("ok") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
