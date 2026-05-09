from __future__ import annotations

import argparse
from pathlib import Path

from tradebot.research_hyp005_shadow_collection_scheduler_pack import (
    SchedulerPackRequest,
    build_hyp005_shadow_scheduler_pack_report,
    discover_latest_operator_audit,
    load_json,
    utc_timestamp,
    write_scheduler_pack_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25Z HYP-005 no-order Windows Task Scheduler pack")
    parser.add_argument("--input-json", dest="input_json", default=None, help="Explicit 25Y operator audit JSON")
    parser.add_argument("--reports-dir", default="reports", help="Reports directory for discovery")
    parser.add_argument("--include-all", action="store_true", help="Discover latest 25Y audit from reports-dir")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--task-name", default="TradeBot_HYP005_NoOrderShadowCollection")
    parser.add_argument("--run-every-hours", type=int, default=4)
    parser.add_argument("--python-executable", default="python")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.input_json:
        source_path = Path(args.input_json)
    else:
        source_path = discover_latest_operator_audit(args.reports_dir)
        if source_path is None:
            raise SystemExit("No 25Y operator audit report found. Provide --input-json or run 25Y first.")

    audit = load_json(source_path)
    symbols = tuple(part.strip().upper() for part in args.symbols.split(",") if part.strip())
    request = SchedulerPackRequest(
        reports_dir=args.reports_dir,
        symbols=symbols,
        interval=args.interval,
        days=args.days,
        base_url=args.base_url,
        task_name=args.task_name,
        run_every_hours=args.run_every_hours,
        python_executable=args.python_executable,
    )
    ts = utc_timestamp()
    report = build_hyp005_shadow_scheduler_pack_report(
        operator_audit=audit,
        request=request,
        out_dir=args.out_dir,
        timestamp=ts,
        review_ok=args.review_ok,
    )
    report["source_operator_audit"] = str(source_path)
    report_json, report_md = write_scheduler_pack_report(report, args.out_dir, ts)

    print(f"4B.4.3.6.6.25Z HYP-005 shadow scheduler pack {report['decision']}")
    print(f" - source_operator_audit: {source_path}")
    print(f" - hypothesis_id: {report['hypothesis_id']}")
    print(f" - selected_strategy_family: {report['selected_strategy_family']}")
    print(f" - no_order_scheduler_pack_only: {report['no_order_scheduler_pack_only']}")
    print(f" - task_name: {report['task_name']}")
    print(f" - run_every_hours: {report['run_every_hours']}")
    print(f" - shadow_observation_count: {report['shadow_observation_count']}")
    print(f" - shadow_sample_target: {report['shadow_sample_target']}")
    print(f" - progress_pct: {report['progress_pct']}")
    print(f" - approved_for_scheduler_pack: {report['approved_for_scheduler_pack']}")
    print(f" - approved_for_paper_transition_candidate: {report['approved_for_paper_transition_candidate']}")
    print(f" - approved_for_paper_candidate: {report['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {report['approved_for_live_real']}")
    print(f" - reason_codes: {report['reason_codes']}")
    print(f" - warnings: {report['warnings']}")
    print(f" - recommendation: {report['recommendation']}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    artifacts = report.get("artifacts") or {}
    if artifacts:
        print(f"pack_dir: {artifacts.get('pack_dir')}")
        print(f"shadow_cycle_ps1: {artifacts.get('shadow_cycle_ps1')}")
        print(f"register_task_ps1: {artifacts.get('register_task_ps1')}")
        print(f"task_xml: {artifacts.get('task_xml')}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
