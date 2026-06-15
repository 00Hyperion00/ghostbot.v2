from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp006_shadow_registration_operator_approval import (  # noqa: E402
    CONTRACT_VERSION,
    build_canonical_shadow_cycle_report,
    load_candles_for_symbols,
    load_json,
    load_jsonl,
    write_cycle_bundle,
)


def parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.28D HYP-006-R1 canonical no-order shadow cycle")
    parser.add_argument("--registration-approval-json", required=True)
    parser.add_argument("--candidate-spec-json")
    parser.add_argument("--registration-json")
    parser.add_argument("--existing-ledger-jsonl")
    parser.add_argument("--input-csv")
    parser.add_argument("--symbols", default="ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--review-ok", action="store_true")
    args = parser.parse_args()
    if not args.review_ok:
        raise SystemExit("FAIL_CLOSED_REQUIRES_REVIEW_OK")
    approval = load_json(args.registration_approval_json)
    candidate_source_path = args.candidate_spec_json or args.registration_json
    if not candidate_source_path:
        raise SystemExit("FAIL_CLOSED_REQUIRES_CANDIDATE_SPEC_OR_28B_REGISTRATION_JSON")
    candidate_source = load_json(candidate_source_path)
    existing_rows = load_jsonl(args.existing_ledger_jsonl) if args.existing_ledger_jsonl else []
    symbols = parse_symbols(args.symbols)
    candles, network, rows_by_symbol = load_candles_for_symbols(
        symbols=symbols,
        interval=args.interval,
        days=args.days,
        input_csv=args.input_csv,
        base_url=args.base_url,
    )
    payload = build_canonical_shadow_cycle_report(
        registration_approval_report=approval,
        candidate_spec_source=candidate_source,
        candles=candles,
        existing_ledger_rows=existing_rows,
        source_paths={
            "registration_approval_json": str(Path(args.registration_approval_json).resolve()),
            "candidate_source_json": str(Path(candidate_source_path).resolve()),
            "existing_ledger_jsonl": None if not args.existing_ledger_jsonl else str(Path(args.existing_ledger_jsonl).resolve()),
            "input_csv": None if not args.input_csv else str(Path(args.input_csv).resolve()),
        },
        rows_by_symbol=rows_by_symbol,
        network_request_performed=network,
    )
    report_json, ledger_jsonl, report_md = write_cycle_bundle(payload, args.out_dir)
    print(f"{CONTRACT_VERSION} HYP-006-R1 canonical no-order shadow collection cycle {payload['decision']}")
    summary = payload.get("shadow_summary", {})
    for key in (
        "read_only",
        "canonical_no_order_shadow_collection_cycle",
        "network_request_performed",
        "approved_for_shadow_collection",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "scheduler_mutation_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    for key in (
        "shadow_observation_count",
        "new_unique_shadow_observation_count",
        "duplicate_existing_observation_count",
        "mean_return_bps",
        "profit_factor",
    ):
        print(f" - {key}: {summary.get(key)}")
    print(f"report_json: {report_json}")
    print(f"ledger_jsonl: {ledger_jsonl}")
    print(f"report_md: {report_md}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
