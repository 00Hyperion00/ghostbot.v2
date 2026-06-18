from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp006_near_miss_outcome_attribution import (  # noqa: E402
    CONTRACT_VERSION,
    DEFAULT_REPORTS_DIR,
    build_near_miss_outcome_attribution_report,
    latest_h3_artifact,
    load_json,
    write_report_bundle,
)


def parse_symbols(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.28G-H4 HYP-006 near-miss outcome attribution no-order research report")
    parser.add_argument("--h3-json", help="Latest 28G-H3 runtime candidate scan artifact JSON")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--out-dir", help="Output directory. Defaults to --reports-dir")
    parser.add_argument("--input-csv", help="Optional OHLCV CSV to avoid public market-data fetch")
    parser.add_argument("--symbols", help="Comma-separated symbols. Defaults to H3 symbol counters")
    parser.add_argument("--interval", help="Kline interval. Defaults to H3 timeframe")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--sample-limit", type=int, default=250)
    args = parser.parse_args()

    h3_path = Path(args.h3_json) if args.h3_json else latest_h3_artifact(args.reports_dir)
    if h3_path is None or not h3_path.exists():
        raise SystemExit("FAIL_CLOSED_H3_RUNTIME_CANDIDATE_SCAN_ARTIFACT_NOT_FOUND")
    h3_payload = load_json(h3_path)
    if isinstance(h3_payload, dict):
        h3_payload["_source_path"] = str(h3_path)
    payload = build_near_miss_outcome_attribution_report(
        h3_artifact=h3_payload,
        reports_dir=args.reports_dir,
        input_csv=args.input_csv,
        symbols=parse_symbols(args.symbols),
        interval=args.interval,
        days=args.days,
        base_url=args.base_url,
        sample_limit=max(1, args.sample_limit),
    )
    report_json, report_md = write_report_bundle(payload, args.out_dir or args.reports_dir)
    print(f"{CONTRACT_VERSION} HYP-006 near-miss outcome attribution {payload.get('decision')}")
    for key in (
        "read_only",
        "counterfactual_research_only",
        "network_request_performed",
        "attributed_near_miss_event_count",
        "matured_near_miss_event_count",
        "approved_for_gate_combo_counterfactual_review_candidate",
        "approved_for_parameter_relaxation_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    summary = payload.get("near_miss_outcome_summary", {}) if isinstance(payload.get("near_miss_outcome_summary"), dict) else {}
    for key in ("mean_return_bps", "win_rate_pct", "profit_factor", "worst_return_bps", "best_return_bps"):
        print(f" - near_miss_{key}: {summary.get(key)}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
