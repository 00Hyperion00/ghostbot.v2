from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G-H7"
SOURCE_H6_CONTRACT_VERSION = "4B.4.3.6.6.28G-H6"
REPORT_TYPE = "hyp006_r1_no_order_overlay_simulation_bnbusdt_primary_filter_shadow_measurement_pack"
REPORT_PREFIX = "4B436628G_H7_hyp006_r1_no_order_overlay_simulation_bnbusdt_primary_filter_shadow_measurement"
DEFAULT_REPORTS_DIR = "reports/hyp006_r1_canonical"
DEFAULT_H6_PATTERN = "4B436628G_H6_hyp006_r1_no_order_filter_shadow_overlay_design_*.json"
PRIMARY_SYMBOL = "BNBUSDT"
MEASUREMENT_STATUS = "NO_ORDER_BNBUSDT_PRIMARY_OVERLAY_SHADOW_MEASUREMENT_READY"
BLOCKED_STATUS = "NO_ORDER_BNBUSDT_PRIMARY_OVERLAY_SHADOW_MEASUREMENT_BLOCKED"

QUALITY_GUARDS = {
    "min_matured_count": 10,
    "min_win_rate_pct": 60.0,
    "min_profit_factor": 1.5,
    "min_mean_return_bps": 0.0,
    "min_worst_return_bps": -500.0,
    "min_worst_mae_bps": -500.0,
}

SUMMARY_FIELDS = (
    "category",
    "category_label",
    "key",
    "event_count",
    "matured_count",
    "win_rate_pct",
    "mean_return_bps",
    "median_return_bps",
    "profit_factor",
    "worst_return_bps",
    "worst_mae_bps",
    "best_return_bps",
    "avg_mae_bps",
    "avg_mfe_bps",
    "net_return_bps",
    "review_score",
    "tail_risk_flag",
    "tail_risk_reasons",
    "ranking_guard_reasons",
    "research_only_counterfactual_candidate",
    "overlay_class",
    "overlay_predicate",
    "overlay_status",
    "quarantine_required",
    "shadow_overlay_measurement_only",
    "runtime_activation_allowed",
    "parameter_relaxation_allowed",
    "paper_live_order_allowed",
    "training_reload_allowed",
    "no_order_review_only",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []


def load_json(path: str | os.PathLike[str]) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{resolved.name}.",
        suffix=".tmp",
        dir=resolved.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp_path.replace(resolved)
    finally:
        temp_path.unlink(missing_ok=True)


def latest_h6_artifact(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    target = Path(reports_dir)
    matches = sorted(target.glob(DEFAULT_H6_PATTERN), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _copy_row(row: Mapping[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = {}
    for field in SUMMARY_FIELDS:
        if field in row:
            copied[field] = row.get(field)
    copied["category"] = str(copied.get("category") or "unknown")
    copied["key"] = str(copied.get("key") or "UNKNOWN")
    copied["event_count"] = safe_int(copied.get("event_count"))
    copied["matured_count"] = safe_int(copied.get("matured_count"))
    for numeric in (
        "win_rate_pct",
        "mean_return_bps",
        "median_return_bps",
        "profit_factor",
        "worst_return_bps",
        "worst_mae_bps",
        "best_return_bps",
        "avg_mae_bps",
        "avg_mfe_bps",
        "net_return_bps",
        "review_score",
    ):
        if numeric in copied:
            copied[numeric] = round(float(safe_float(copied.get(numeric), 0.0) or 0.0), 6)
    copied["no_order_review_only"] = True
    copied["shadow_overlay_measurement_only"] = True
    copied["runtime_activation_allowed"] = False
    copied["parameter_relaxation_allowed"] = False
    copied["paper_live_order_allowed"] = False
    copied["training_reload_allowed"] = False
    return copied


def _row_identity(row: Mapping[str, Any]) -> str:
    return f"{row.get('category')}::{row.get('key')}"


def _dedupe_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for raw in rows:
        mapping = _mapping(raw)
        if not mapping:
            continue
        copied = _copy_row(mapping)
        deduped[_row_identity(copied)] = copied
    return list(deduped.values())


def _sort_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in sorted(
            rows,
            key=lambda item: (
                safe_float(item.get("review_score"), 0.0) or 0.0,
                safe_float(item.get("mean_return_bps"), 0.0) or 0.0,
            ),
            reverse=True,
        )
    ]


def _predicate_symbols(row: Mapping[str, Any]) -> set[str]:
    predicate = _mapping(row.get("overlay_predicate"))
    return {str(value).upper() for value in _sequence(predicate.get("include_symbols"))}


def _is_primary_symbol_candidate(row: Mapping[str, Any], symbol: str = PRIMARY_SYMBOL) -> bool:
    key = str(row.get("key") or "").upper()
    category = str(row.get("category") or "").lower()
    predicate_symbols = _predicate_symbols(row)
    return category == "symbol" and (key == symbol or symbol in predicate_symbols)


def _find_primary_symbol_candidate(h6_artifact: Mapping[str, Any], symbol: str = PRIMARY_SYMBOL) -> dict[str, Any] | None:
    for raw in _sequence(h6_artifact.get("accepted_primary_overlay_candidates")):
        row = _copy_row(_mapping(raw))
        if _is_primary_symbol_candidate(row, symbol=symbol):
            return row
    return None


def _quality_guard_reasons(row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if safe_int(row.get("matured_count")) < int(QUALITY_GUARDS["min_matured_count"]):
        reasons.append("MATURED_COUNT_BELOW_MEASUREMENT_MIN")
    if (safe_float(row.get("win_rate_pct"), 0.0) or 0.0) < QUALITY_GUARDS["min_win_rate_pct"]:
        reasons.append("WIN_RATE_BELOW_MEASUREMENT_MIN")
    if (safe_float(row.get("profit_factor"), 0.0) or 0.0) < QUALITY_GUARDS["min_profit_factor"]:
        reasons.append("PROFIT_FACTOR_BELOW_MEASUREMENT_MIN")
    if (safe_float(row.get("mean_return_bps"), 0.0) or 0.0) <= QUALITY_GUARDS["min_mean_return_bps"]:
        reasons.append("MEAN_RETURN_NOT_POSITIVE")
    if (safe_float(row.get("worst_return_bps"), 0.0) or 0.0) <= QUALITY_GUARDS["min_worst_return_bps"]:
        reasons.append("WORST_RETURN_BELOW_MEASUREMENT_TAIL_LIMIT")
    if (safe_float(row.get("worst_mae_bps"), 0.0) or 0.0) <= QUALITY_GUARDS["min_worst_mae_bps"]:
        reasons.append("WORST_MAE_BELOW_MEASUREMENT_TAIL_LIMIT")
    if bool(row.get("tail_risk_flag")):
        reasons.append("TAIL_RISK_FLAG_PRESENT")
    return reasons


def _build_measurement_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    copied = _copy_row(row)
    guard_reasons = _quality_guard_reasons(copied)
    passed = not guard_reasons
    copied.update(
        {
            "measurement_symbol": PRIMARY_SYMBOL,
            "measurement_class": "BNBUSDT_PRIMARY_SYMBOL_FILTER_SHADOW_MEASUREMENT",
            "measurement_status": "MEASUREMENT_GUARD_PASS" if passed else "MEASUREMENT_GUARD_FAIL",
            "measurement_guard_pass": passed,
            "measurement_guard_reasons": guard_reasons,
            "measurement_policy": "NO_ORDER_MEASUREMENT_ONLY_NOT_RUNTIME_ACTIVATION",
            "overlay_simulation_scope": "BNBUSDT_ONLY_PRIMARY_SYMBOL_FILTER",
            "runtime_overlay_activation_allowed": False,
            "parameter_change_allowed": False,
            "parameter_relaxation_allowed": False,
            "paper_live_order_allowed": False,
            "training_reload_allowed": False,
            "order_actions_allowed": False,
            "shadow_overlay_measurement_only": True,
        }
    )
    return copied


def _excluded_summary(rows: Sequence[Mapping[str, Any]], *, reason: str) -> list[dict[str, Any]]:
    excluded: list[dict[str, Any]] = []
    for row in rows:
        copied = _copy_row(row)
        copied["excluded_from_h7_primary_measurement"] = True
        copied["exclusion_reason"] = reason
        copied["runtime_overlay_activation_allowed"] = False
        copied["parameter_relaxation_allowed"] = False
        copied["paper_live_order_allowed"] = False
        excluded.append(copied)
    return _sort_rows(excluded)


def build_no_order_overlay_simulation_bnbusdt_report(h6_artifact: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if h6_artifact.get("contract_version") != SOURCE_H6_CONTRACT_VERSION:
        blockers.append("SOURCE_H6_CONTRACT_VERSION_MISMATCH")
    if not h6_artifact.get("read_only", False):
        blockers.append("SOURCE_H6_NOT_READ_ONLY")
    if not h6_artifact.get("filter_shadow_overlay_design_only", False):
        blockers.append("SOURCE_H6_NOT_OVERLAY_DESIGN_ONLY")
    if h6_artifact.get("approved_for_parameter_relaxation_candidate") is not False:
        blockers.append("SOURCE_H6_PARAMETER_RELAXATION_GATE_NOT_CLOSED")
    if h6_artifact.get("approved_for_paper_candidate") is not False or h6_artifact.get("approved_for_live_real") is not False:
        blockers.append("SOURCE_H6_TRADING_GATE_NOT_CLOSED")
    if h6_artifact.get("runtime_overlay_activation_performed") is not False:
        blockers.append("SOURCE_H6_RUNTIME_OVERLAY_ACTIVATION_ALREADY_PERFORMED")

    primary_candidate = _find_primary_symbol_candidate(h6_artifact)
    if primary_candidate is None:
        blockers.append("BNBUSDT_PRIMARY_OVERLAY_CANDIDATE_NOT_FOUND")

    quarantine = _dedupe_rows(_sequence(h6_artifact.get("quarantine_review_candidates")))
    watchlist = _dedupe_rows(_sequence(h6_artifact.get("watchlist_low_sample_overlay_candidates")))
    blocklist = _dedupe_rows(_sequence(h6_artifact.get("do_not_relax_gate_combo_blocklist")))
    rejected = _dedupe_rows(_sequence(h6_artifact.get("rejected_overlay_candidates")))

    measurement_candidate = _build_measurement_candidate(primary_candidate) if primary_candidate is not None else None
    guard_pass = bool(measurement_candidate and measurement_candidate.get("measurement_guard_pass"))
    ok = not blockers
    approved_for_measurement = bool(ok and guard_pass)

    measurement_summary = {
        "symbol": PRIMARY_SYMBOL,
        "measurement_candidate_present": primary_candidate is not None,
        "measurement_guard_pass": guard_pass,
        "measurement_guard_reasons": measurement_candidate.get("measurement_guard_reasons") if measurement_candidate else ["BNBUSDT_PRIMARY_OVERLAY_CANDIDATE_NOT_FOUND"],
        "matured_count": measurement_candidate.get("matured_count") if measurement_candidate else 0,
        "event_count": measurement_candidate.get("event_count") if measurement_candidate else 0,
        "win_rate_pct": measurement_candidate.get("win_rate_pct") if measurement_candidate else None,
        "mean_return_bps": measurement_candidate.get("mean_return_bps") if measurement_candidate else None,
        "median_return_bps": measurement_candidate.get("median_return_bps") if measurement_candidate else None,
        "profit_factor": measurement_candidate.get("profit_factor") if measurement_candidate else None,
        "worst_return_bps": measurement_candidate.get("worst_return_bps") if measurement_candidate else None,
        "worst_mae_bps": measurement_candidate.get("worst_mae_bps") if measurement_candidate else None,
        "net_return_bps": measurement_candidate.get("net_return_bps") if measurement_candidate else None,
    }

    return {
        "ok": ok,
        "contract_version": CONTRACT_VERSION,
        "source_h6_contract_version": h6_artifact.get("contract_version"),
        "report_type": REPORT_TYPE,
        "generated_at_utc": utc_now_iso(),
        "branch_id": h6_artifact.get("branch_id", "HYP-006-R1"),
        "branch_name": h6_artifact.get("branch_name", "failed_downside_sweep_reversal_continuation_short"),
        "hypothesis_id": h6_artifact.get("hypothesis_id", "HYP-006"),
        "strategy_family": h6_artifact.get("strategy_family", "short_failed_liquidity_sweep_continuation"),
        "timeframe": h6_artifact.get("timeframe", "4h"),
        "decision": MEASUREMENT_STATUS if ok else BLOCKED_STATUS,
        "blockers": blockers,
        "read_only": True,
        "no_order_measurement_only": True,
        "counterfactual_research_only": True,
        "overlay_simulation_measurement_only": True,
        "filter_shadow_overlay_design_only": False,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "strategy_parameter_mutation_performed": False,
        "runtime_overlay_activation_performed": False,
        "approved_for_overlay_shadow_measurement": approved_for_measurement,
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_filter_shadow_overlay_candidate": False,
        "approved_for_quarantine_review_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "source_h6_summary": {
            "accepted_primary_overlay_candidate_count": h6_artifact.get("accepted_primary_overlay_candidate_count"),
            "quarantine_review_candidate_count": h6_artifact.get("quarantine_review_candidate_count"),
            "watchlist_overlay_candidate_count": h6_artifact.get("watchlist_overlay_candidate_count"),
            "do_not_relax_blocklist_count": h6_artifact.get("do_not_relax_blocklist_count"),
            "rejected_overlay_candidate_count": h6_artifact.get("rejected_overlay_candidate_count"),
        },
        "measurement_quality_guards": QUALITY_GUARDS,
        "measurement_policy": {
            "primary_symbol": PRIMARY_SYMBOL,
            "source_candidate_rule": "accepted_primary_overlay_candidates where category=symbol and key=BNBUSDT",
            "quarantine_candidates_used": False,
            "watchlist_candidates_used": False,
            "do_not_relax_blocklist_enforced": True,
            "runtime_activation_allowed": False,
            "parameter_relaxation_allowed": False,
            "paper_live_order_allowed": False,
        },
        "primary_measurement_candidate_count": 1 if measurement_candidate else 0,
        "primary_measurement_candidate": measurement_candidate,
        "primary_measurement_summary": measurement_summary,
        "excluded_quarantine_candidates": _excluded_summary(quarantine, reason="TAIL_RISK_QUARANTINE_NOT_USED_IN_H7_BNBUSDT_MEASUREMENT"),
        "excluded_watchlist_candidates": _excluded_summary(watchlist, reason="LOW_SAMPLE_WATCHLIST_NOT_USED_IN_H7_BNBUSDT_MEASUREMENT"),
        "enforced_do_not_relax_blocklist": _excluded_summary(blocklist, reason="EXPLICIT_DO_NOT_RELAX_BLOCKLIST_ENFORCED"),
        "excluded_rejected_candidates": _excluded_summary(rejected, reason="REJECTED_COUNTERFACTUAL_NOT_USED_IN_H7_BNBUSDT_MEASUREMENT"),
        "recommendation": "Keep BNBUSDT overlay in no-order shadow measurement only. Do not activate runtime overlay, do not relax parameters, and keep paper/live/order gates closed." if approved_for_measurement else "Do not promote BNBUSDT overlay measurement. Keep all runtime, parameter, paper/live, and order gates closed.",
    }


def render_markdown_report(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {CONTRACT_VERSION} HYP-006 No-Order Overlay Simulation: BNBUSDT Primary Filter Shadow Measurement")
    lines.append("")
    lines.append("This pack measures the H6 BNBUSDT primary overlay candidate in no-order research mode only. It does not activate runtime filtering, change parameters, train, reload, or enable paper/live trading.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    for key in (
        "decision",
        "read_only",
        "overlay_simulation_measurement_only",
        "approved_for_overlay_shadow_measurement",
        "approved_for_runtime_overlay_activation_candidate",
        "approved_for_parameter_relaxation_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "runtime_overlay_activation_performed",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
        "order_actions_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Primary measurement summary")
    lines.append("")
    summary = _mapping(payload.get("primary_measurement_summary"))
    for key in (
        "symbol",
        "measurement_candidate_present",
        "measurement_guard_pass",
        "matured_count",
        "win_rate_pct",
        "mean_return_bps",
        "profit_factor",
        "worst_return_bps",
        "worst_mae_bps",
        "net_return_bps",
    ):
        lines.append(f"- `{key}`: `{summary.get(key)}`")
    guard_reasons = _sequence(summary.get("measurement_guard_reasons"))
    lines.append(f"- `measurement_guard_reasons`: `{', '.join(str(item) for item in guard_reasons) if guard_reasons else '[]'}`")
    lines.append("")
    lines.append("## Primary measurement candidate")
    lines.append("")
    candidate = _mapping(payload.get("primary_measurement_candidate"))
    if not candidate:
        lines.append("No BNBUSDT primary measurement candidate was found.")
    else:
        lines.append("| key | matured | win % | mean bps | PF | worst bps | worst MAE | status |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---|")
        lines.append(
            f"| {candidate.get('key')} | {candidate.get('matured_count')} | {candidate.get('win_rate_pct')} | {candidate.get('mean_return_bps')} | {candidate.get('profit_factor')} | {candidate.get('worst_return_bps')} | {candidate.get('worst_mae_bps')} | {candidate.get('measurement_status')} |"
        )
    lines.append("")
    lines.append("## Exclusions")
    lines.append("")
    for title, field in (
        ("Quarantine candidates", "excluded_quarantine_candidates"),
        ("Watchlist candidates", "excluded_watchlist_candidates"),
        ("Do-not-relax blocklist", "enforced_do_not_relax_blocklist"),
    ):
        lines.append(f"### {title}")
        rows = _sequence(payload.get(field))
        if not rows:
            lines.append("No rows.")
        else:
            lines.append("| category | key | matured | mean bps | PF | reason |")
            lines.append("|---|---|---:|---:|---:|---|")
            for row in rows[:20]:
                item = _mapping(row)
                lines.append(
                    f"| {item.get('category')} | {item.get('key')} | {item.get('matured_count')} | {item.get('mean_return_bps')} | {item.get('profit_factor')} | {item.get('exclusion_reason')} |"
                )
        lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append(str(payload.get("recommendation", "")))
    lines.append("")
    return "\n".join(lines)


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(json_path, payload)
    md_path.write_text(render_markdown_report(payload), encoding="utf-8", newline="\n")
    return json_path, md_path


def build_and_write_latest_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[dict[str, Any], Path | None, Path | None]:
    h6_path = latest_h6_artifact(reports_dir)
    if h6_path is None:
        payload = build_no_order_overlay_simulation_bnbusdt_report({})
        payload["blockers"] = [*payload.get("blockers", []), "SOURCE_H6_ARTIFACT_NOT_FOUND"]
        payload["ok"] = False
        payload["decision"] = BLOCKED_STATUS
        json_path, md_path = write_report_bundle(payload, reports_dir)
        return payload, json_path, md_path
    h6_payload = _mapping(load_json(h6_path))
    report = build_no_order_overlay_simulation_bnbusdt_report(h6_payload)
    report["source_h6_artifact_json"] = str(h6_path)
    json_path, md_path = write_report_bundle(report, reports_dir)
    return report, json_path, md_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build HYP-006 BNBUSDT no-order overlay shadow measurement pack")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report, json_path, md_path = build_and_write_latest_report(args.reports_dir)
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(f"{CONTRACT_VERSION} HYP-006 no-order overlay simulation {report.get('decision')}")
        for key in (
            "read_only",
            "overlay_simulation_measurement_only",
            "primary_measurement_candidate_count",
            "approved_for_overlay_shadow_measurement",
            "approved_for_runtime_overlay_activation_candidate",
            "approved_for_parameter_relaxation_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "runtime_overlay_activation_performed",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
        ):
            print(f" - {key}: {report.get(key)}")
        if json_path is not None:
            print(f"report_json: {json_path}")
        if md_path is not None:
            print(f"report_md: {md_path}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
