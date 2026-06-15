from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp006_shadow_registration_operator_approval import (  # noqa: E402
    CONTRACT_VERSION,
    build_registration_approval_report,
    load_json,
    write_registration_bundle,
)


def parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.28D HYP-006-R1 registration approval pack")
    parser.add_argument("--dry-run-report-json", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--symbols", default="ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-runtime-reports-retained", type=int, default=100)
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--operator-approval", action="store_true")
    parser.add_argument("--emit-registration-script", action="store_true")
    parser.add_argument("--review-ok", action="store_true")
    args = parser.parse_args()
    if not args.review_ok:
        raise SystemExit("FAIL_CLOSED_REQUIRES_REVIEW_OK")
    dry_run_report = load_json(args.dry_run_report_json)
    symbols = parse_symbols(args.symbols)
    payload = build_registration_approval_report(
        dry_run_report=dry_run_report,
        operator_approval=bool(args.operator_approval),
        source_paths={"dry_run_report_json": str(Path(args.dry_run_report_json).resolve())},
        reports_dir=args.out_dir,
        symbols=symbols,
        max_runtime_reports_retained=args.max_runtime_reports_retained,
    )
    report_json, retention_json, report_md, script_path = write_registration_bundle(
        payload,
        args.out_dir,
        project_root=args.project_root,
        symbols=symbols,
        interval=args.interval,
        days=args.days,
        emit_registration_script=bool(args.emit_registration_script),
    )
    print(f"{CONTRACT_VERSION} HYP-006-R1 canonical no-order shadow registration approval {payload['decision']}")
    for key in (
        "read_only",
        "no_order_shadow_collection_registration_only",
        "approved_for_canonical_no_order_shadow_registration",
        "approved_for_shadow_collection",
        "scheduler_mutation_performed",
        "scheduler_task_created",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "next_required_gate",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f"report_json: {report_json}")
    print(f"retention_policy_json: {retention_json}")
    print(f"report_md: {report_md}")
    if script_path is not None:
        print(f"registration_script_ps1: {script_path}")
    if not payload.get("ok"):
        print(json.dumps({"blockers": payload.get("blockers", [])}, ensure_ascii=False, indent=2))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
