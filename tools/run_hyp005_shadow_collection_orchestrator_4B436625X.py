#!/usr/bin/env python3
"""CLI for 4B.4.3.6.6.25X HYP-005 no-order shadow collection orchestrator."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from tradebot.research_hyp005_shadow_collection_orchestrator import (
    DEFAULT_MERGED_LEDGER_PREFIX,
    DEFAULT_PLAN_PREFIX,
    DEFAULT_REPORT_PREFIX,
    HYP005_SHADOW_COLLECTION_ORCHESTRATOR_CONTRACT_VERSION,
    as_serializable_report,
    build_hyp005_shadow_collection_orchestrator_report,
    load_json,
    load_observations_from_json,
    load_observations_from_jsonl,
    merge_observations,
    utc_timestamp,
    write_json,
    write_jsonl,
    write_markdown_report,
)

CLI_HOTFIX_SAFE_VERSION = HYP005_SHADOW_COLLECTION_ORCHESTRATOR_CONTRACT_VERSION
HYP005_R1_STRICT_EXPLICIT_CHAIN_HOTFIX_VERSION = "4B.4.3.6.6.25AE-H3"
HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION = "4B.4.3.6.6.25AE-H4"


def _latest(paths: list[Path]) -> Path | None:
    return max(paths, key=lambda item: item.stat().st_mtime) if paths else None


def _discover_reports(reports_dir: Path, include_all: bool) -> tuple[Path | None, list[Path], list[Path], list[Path], list[Path]]:
    candidate_specs = sorted(reports_dir.glob("4B436625U_hyp005_no_order_shadow_candidate_spec_*.json"))
    logger_reports = sorted(reports_dir.glob("4B436625V_hyp005_shadow_observation_logger_*.json"))
    acceptance_reports = sorted(reports_dir.glob("4B436625W_hyp005_shadow_observation_acceptance_*.json"))
    ledger_jsons = sorted(reports_dir.glob("4B436625V_hyp005_shadow_observation_ledger_*.json"))
    ledger_jsonls = sorted(reports_dir.glob("4B436625V_hyp005_shadow_observation_ledger_*.jsonl"))

    spec = _latest(candidate_specs)
    if include_all:
        return spec, logger_reports, acceptance_reports, ledger_jsons, ledger_jsonls
    return (
        spec,
        [item for item in [_latest(logger_reports)] if item],
        [item for item in [_latest(acceptance_reports)] if item],
        [item for item in [_latest(ledger_jsons)] if item],
        [item for item in [_latest(ledger_jsonls)] if item],
    )


def _load_many_json(paths: list[Path]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for path in paths:
        payload = load_json(path)
        if isinstance(payload, dict):
            values.append(payload)
    return values



def _ensure_scoped_inputs(reports_dir: Path, paths: list[Path], *, label: str) -> None:
    scope = reports_dir.resolve()
    for path in paths:
        resolved = path.resolve()
        try:
            resolved.relative_to(scope)
        except ValueError as exc:
            raise SystemExit(f"{label} must remain inside scoped reports-dir: {resolved}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-spec-json", type=Path)
    parser.add_argument("--logger-report-json", action="append", type=Path, default=[])
    parser.add_argument("--acceptance-report-json", action="append", type=Path, default=[])
    parser.add_argument("--ledger-json", action="append", type=Path, default=[])
    parser.add_argument("--ledger-jsonl", action="append", type=Path, default=[])
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--include-all", action="store_true")
    parser.add_argument("--strict-explicit-chain", action="store_true", help="Require scoped explicit logger/ledger inputs; disable discovery fallback.")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--out-dir", type=Path, default=Path("reports"))
    parser.add_argument("--review-ok", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.review_ok:
        raise SystemExit("--review-ok is required for this no-order scheduler gate")

    candidate_spec_path = args.candidate_spec_json
    logger_paths = list(args.logger_report_json)
    acceptance_paths = list(args.acceptance_report_json)
    ledger_json_paths = list(args.ledger_json)
    ledger_jsonl_paths = list(args.ledger_jsonl)

    if args.strict_explicit_chain:
        if not candidate_spec_path or not logger_paths or not (ledger_json_paths or ledger_jsonl_paths):
            raise SystemExit("--strict-explicit-chain requires --candidate-spec-json, --logger-report-json, and --ledger-json/--ledger-jsonl")
        _ensure_scoped_inputs(
            args.reports_dir,
            logger_paths + acceptance_paths + ledger_json_paths + ledger_jsonl_paths,
            label="25X explicit input",
        )
    elif not candidate_spec_path or not logger_paths or not (ledger_json_paths or ledger_jsonl_paths):
        discovered_spec, discovered_loggers, discovered_acceptance, discovered_ledgers, discovered_jsonls = _discover_reports(
            args.reports_dir, args.include_all
        )
        candidate_spec_path = candidate_spec_path or discovered_spec
        logger_paths = logger_paths or discovered_loggers
        acceptance_paths = acceptance_paths or discovered_acceptance
        ledger_json_paths = ledger_json_paths or discovered_ledgers
        ledger_jsonl_paths = ledger_jsonl_paths or discovered_jsonls

    # 25W acceptance is downstream of 25X. Prior acceptance reports are optional
    # informational metadata only and never a bootstrap prerequisite.
    if not args.strict_explicit_chain and not acceptance_paths:
        acceptance_paths = [item for item in [_latest(sorted(args.reports_dir.glob("4B436625W_hyp005_shadow_observation_acceptance_*.json")))] if item]

    if not candidate_spec_path:
        raise SystemExit("candidate spec not found; pass --candidate-spec-json or use --reports-dir with 25U outputs")

    candidate_spec = load_json(candidate_spec_path)
    if not isinstance(candidate_spec, dict):
        raise SystemExit("candidate spec JSON must contain an object")

    logger_reports = _load_many_json(logger_paths)
    acceptance_reports = _load_many_json(acceptance_paths)
    observation_sets = [load_observations_from_json(path) for path in ledger_json_paths]
    observation_sets.extend(load_observations_from_jsonl(path) for path in ledger_jsonl_paths)
    merged_observations, duplicate_count = merge_observations(observation_sets)

    symbols = [item.strip().upper() for item in str(args.symbols).split(",") if item.strip()]
    report = build_hyp005_shadow_collection_orchestrator_report(
        candidate_spec=candidate_spec,
        candidate_spec_path=str(candidate_spec_path),
        logger_reports=logger_reports,
        acceptance_reports=acceptance_reports,
        observations=merged_observations,
        duplicate_observation_count=duplicate_count,
        ledger_source_count=len(ledger_json_paths) + len(ledger_jsonl_paths),
        symbols=symbols,
        interval=args.interval,
        days=args.days,
        base_url=args.base_url,
        out_dir=str(args.out_dir),
    )
    payload = as_serializable_report(report)

    ts = utc_timestamp()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_json = args.out_dir / f"{DEFAULT_REPORT_PREFIX}_{ts}.json"
    report_md = args.out_dir / f"{DEFAULT_REPORT_PREFIX}_{ts}.md"
    plan_json = args.out_dir / f"{DEFAULT_PLAN_PREFIX}_{ts}.json"
    merged_ledger_json = args.out_dir / f"{DEFAULT_MERGED_LEDGER_PREFIX}_{ts}.json"
    merged_ledger_jsonl = args.out_dir / f"{DEFAULT_MERGED_LEDGER_PREFIX}_{ts}.jsonl"

    write_json(report_json, payload)
    write_markdown_report(report_md, payload)
    write_json(plan_json, payload["plan"])
    write_json(merged_ledger_json, {"observations": merged_observations})
    write_jsonl(merged_ledger_jsonl, merged_observations)

    progress = payload["progress"]
    print(f"4B.4.3.6.6.25X HYP-005 shadow collection orchestrator {payload['decision']}")
    print(f" - source_reports: {payload['source_reports']}")
    print(f" - source_ledgers: {payload['source_ledgers']}")
    print(f" - hypothesis_id: {payload['hypothesis_id']}")
    print(f" - branch_name: {payload['branch_name']}")
    print(f" - selected_strategy_family: {payload['selected_strategy_family']}")
    print(f" - no_order_collection_only: {payload['no_order_collection_only']}")
    print(f" - shadow_collection_ready: {payload['shadow_collection_ready']}")
    print(f" - collection_status: {payload['collection_status']}")
    print(f" - acceptance_report_required_for_collection_ready: {payload['acceptance_report_required_for_collection_ready']}")
    print(f" - shadow_observation_count: {payload['shadow_observation_count']}")
    print(f" - shadow_sample_target: {payload['shadow_sample_target']}")
    print(f" - progress_pct: {payload['progress_pct']}")
    print(f" - duplicate_observation_count: {progress['duplicate_observation_count']}")
    print(f" - approved_for_shadow_collection: {payload['approved_for_shadow_collection']}")
    print(f" - approved_for_paper_transition_candidate: {payload['approved_for_paper_transition_candidate']}")
    print(f" - approved_for_training_candidate: {payload['approved_for_training_candidate']}")
    print(f" - approved_for_paper_candidate: {payload['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {payload['approved_for_live_real']}")
    print(f" - reason_codes: {payload['reason_codes']}")
    print(f" - warnings: {payload['warnings']}")
    print(f" - recommendation: {payload['recommendation']}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    print(f"plan_json: {plan_json}")
    print(f"merged_ledger_json: {merged_ledger_json}")
    print(f"merged_ledger_jsonl: {merged_ledger_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# marker inventory for apply verifier:
# __candidate_spec_json __logger_report_json __acceptance_report_json __strict_explicit_chain method=GET public_market_data_GET_only

# 25AE-H4 marker inventory:
# HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION
# acceptance_report_required_for_collection_ready
# previous acceptance metadata is informational only
