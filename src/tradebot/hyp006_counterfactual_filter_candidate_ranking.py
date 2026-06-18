from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G-H5"
SOURCE_H4_CONTRACT_VERSION = "4B.4.3.6.6.28G-H4"
REPORT_TYPE = "hyp006_r1_counterfactual_filter_candidate_ranking_no_order_gate_combo_review_pack"
REPORT_PREFIX = "4B436628G_H5_hyp006_r1_counterfactual_filter_candidate_ranking"
DEFAULT_REPORTS_DIR = "reports/hyp006_r1_canonical"
DEFAULT_H4_PATTERN = "4B436628G_H4_hyp006_r1_near_miss_outcome_attribution_*.json"

MIN_REVIEW_MATURED_COUNT = 10
MIN_WATCHLIST_MATURED_COUNT = 3
MIN_REVIEW_WIN_RATE_PCT = 60.0
MIN_REVIEW_PROFIT_FACTOR = 1.5
MIN_REVIEW_MEAN_RETURN_BPS = 0.0
MAX_REVIEW_WORST_RETURN_BPS = -500.0
MAX_REVIEW_WORST_MAE_BPS = -500.0
TAIL_RISK_WORST_RETURN_BPS = -400.0
TAIL_RISK_WORST_MAE_BPS = -500.0
DO_NOT_RELAX_WIN_RATE_PCT = 45.0
DO_NOT_RELAX_PROFIT_FACTOR = 1.0

SUMMARY_FIELDS = (
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
    "research_only_counterfactual_candidate",
)

CATEGORY_LABELS = {
    "gate_combo": "Gate combo",
    "symbol": "Symbol",
    "risk_bucket": "Risk bucket",
}


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


def latest_h4_artifact(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    target = Path(reports_dir)
    matches = sorted(target.glob(DEFAULT_H4_PATTERN), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _copy_summary_row(category: str, row: Mapping[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = {"category": category, "category_label": CATEGORY_LABELS.get(category, category)}
    for field in SUMMARY_FIELDS:
        if field in row:
            copied[field] = row.get(field)
    copied["key"] = str(copied.get("key") or "UNKNOWN")
    copied["event_count"] = safe_int(copied.get("event_count"))
    copied["matured_count"] = safe_int(copied.get("matured_count"))
    copied["win_rate_pct"] = round(float(safe_float(copied.get("win_rate_pct"), 0.0) or 0.0), 6)
    copied["mean_return_bps"] = round(float(safe_float(copied.get("mean_return_bps"), 0.0) or 0.0), 6)
    copied["profit_factor"] = round(float(safe_float(copied.get("profit_factor"), 0.0) or 0.0), 6)
    copied["worst_return_bps"] = round(float(safe_float(copied.get("worst_return_bps"), 0.0) or 0.0), 6)
    copied["worst_mae_bps"] = round(float(safe_float(copied.get("worst_mae_bps"), 0.0) or 0.0), 6)
    copied["review_score"] = review_score(copied)
    copied["tail_risk_flag"] = is_tail_risk(copied)
    copied["tail_risk_reasons"] = tail_risk_reasons(copied)
    copied["ranking_guard_reasons"] = ranking_guard_reasons(copied)
    copied["no_order_review_only"] = True
    copied["parameter_change_allowed"] = False
    copied["paper_live_order_allowed"] = False
    return copied


def review_score(row: Mapping[str, Any]) -> float:
    matured = safe_int(row.get("matured_count"))
    win_rate = safe_float(row.get("win_rate_pct"), 0.0) or 0.0
    mean_return = safe_float(row.get("mean_return_bps"), 0.0) or 0.0
    profit_factor = safe_float(row.get("profit_factor"), 0.0) or 0.0
    worst_return = safe_float(row.get("worst_return_bps"), 0.0) or 0.0
    tail_penalty = max(0.0, abs(min(worst_return, 0.0)) - 300.0) / 10.0
    return round((matured * 0.75) + (win_rate * 0.35) + (mean_return * 0.08) + (profit_factor * 4.0) - tail_penalty, 6)


def is_tail_risk(row: Mapping[str, Any]) -> bool:
    worst_return = safe_float(row.get("worst_return_bps"), 0.0) or 0.0
    worst_mae = safe_float(row.get("worst_mae_bps"), 0.0) or 0.0
    return worst_return <= TAIL_RISK_WORST_RETURN_BPS or worst_mae <= TAIL_RISK_WORST_MAE_BPS


def tail_risk_reasons(row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    worst_return = safe_float(row.get("worst_return_bps"), 0.0) or 0.0
    worst_mae = safe_float(row.get("worst_mae_bps"), 0.0) or 0.0
    if worst_return <= TAIL_RISK_WORST_RETURN_BPS:
        reasons.append("WORST_RETURN_TAIL_RISK")
    if worst_mae <= TAIL_RISK_WORST_MAE_BPS:
        reasons.append("WORST_MAE_TAIL_RISK")
    return reasons


def ranking_guard_reasons(row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if safe_int(row.get("matured_count")) < MIN_REVIEW_MATURED_COUNT:
        reasons.append("MATURED_COUNT_BELOW_REVIEW_MIN")
    if (safe_float(row.get("win_rate_pct"), 0.0) or 0.0) < MIN_REVIEW_WIN_RATE_PCT:
        reasons.append("WIN_RATE_BELOW_REVIEW_MIN")
    if (safe_float(row.get("profit_factor"), 0.0) or 0.0) < MIN_REVIEW_PROFIT_FACTOR:
        reasons.append("PROFIT_FACTOR_BELOW_REVIEW_MIN")
    if (safe_float(row.get("mean_return_bps"), 0.0) or 0.0) <= MIN_REVIEW_MEAN_RETURN_BPS:
        reasons.append("MEAN_RETURN_NOT_POSITIVE")
    if (safe_float(row.get("worst_return_bps"), 0.0) or 0.0) <= MAX_REVIEW_WORST_RETURN_BPS:
        reasons.append("WORST_RETURN_BELOW_REVIEW_TAIL_LIMIT")
    if (safe_float(row.get("worst_mae_bps"), 0.0) or 0.0) <= MAX_REVIEW_WORST_MAE_BPS:
        reasons.append("WORST_MAE_BELOW_REVIEW_TAIL_LIMIT")
    return reasons


def qualifies_for_review(row: Mapping[str, Any]) -> bool:
    return not ranking_guard_reasons(row)


def qualifies_for_watchlist(row: Mapping[str, Any]) -> bool:
    matured = safe_int(row.get("matured_count"))
    if not (MIN_WATCHLIST_MATURED_COUNT <= matured < MIN_REVIEW_MATURED_COUNT):
        return False
    return (
        (safe_float(row.get("win_rate_pct"), 0.0) or 0.0) >= MIN_REVIEW_WIN_RATE_PCT
        and (safe_float(row.get("profit_factor"), 0.0) or 0.0) >= MIN_REVIEW_PROFIT_FACTOR
        and (safe_float(row.get("mean_return_bps"), 0.0) or 0.0) > MIN_REVIEW_MEAN_RETURN_BPS
        and (safe_float(row.get("worst_return_bps"), 0.0) or 0.0) > MAX_REVIEW_WORST_RETURN_BPS
        and (safe_float(row.get("worst_mae_bps"), 0.0) or 0.0) > MAX_REVIEW_WORST_MAE_BPS
    )


def qualifies_for_do_not_relax(row: Mapping[str, Any]) -> bool:
    key = str(row.get("key") or "")
    if row.get("category") != "gate_combo":
        return False
    if not key or key == "UNKNOWN":
        return False
    mean_return = safe_float(row.get("mean_return_bps"), 0.0) or 0.0
    win_rate = safe_float(row.get("win_rate_pct"), 0.0) or 0.0
    profit_factor = safe_float(row.get("profit_factor"), 0.0) or 0.0
    return mean_return <= 0 or win_rate < DO_NOT_RELAX_WIN_RATE_PCT or profit_factor < DO_NOT_RELAX_PROFIT_FACTOR


def _rows_from_h4(h4_artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_specs = (
        ("gate_combo", "gate_combo_outcome_summary"),
        ("symbol", "symbol_outcome_summary"),
        ("risk_bucket", "risk_bucket_outcome_summary"),
    )
    for category, field in source_specs:
        for raw in _sequence(h4_artifact.get(field)):
            mapping = _mapping(raw)
            if mapping:
                rows.append(_copy_summary_row(category, mapping))
    return rows


def _sort_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in sorted(rows, key=lambda item: (safe_float(item.get("review_score"), 0.0) or 0.0), reverse=True)]


def build_counterfactual_filter_candidate_ranking_report(h4_artifact: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if h4_artifact.get("contract_version") != SOURCE_H4_CONTRACT_VERSION:
        blockers.append("SOURCE_H4_CONTRACT_VERSION_MISMATCH")
    if not h4_artifact.get("read_only", False):
        blockers.append("SOURCE_H4_NOT_READ_ONLY")
    if h4_artifact.get("approved_for_paper_candidate") is not False or h4_artifact.get("approved_for_live_real") is not False:
        blockers.append("SOURCE_H4_TRADING_GATE_NOT_CLOSED")

    rows = _rows_from_h4(h4_artifact)
    if not rows:
        blockers.append("SOURCE_H4_NO_OUTCOME_SUMMARY_ROWS")

    accepted = _sort_rows([row for row in rows if qualifies_for_review(row)])
    watchlist = _sort_rows([row for row in rows if qualifies_for_watchlist(row)])
    rejected = _sort_rows([row for row in rows if not qualifies_for_review(row) and not qualifies_for_watchlist(row)])
    tail_flags = _sort_rows([row for row in rows if row.get("tail_risk_flag")])
    do_not_relax = _sort_rows([row for row in rows if qualifies_for_do_not_relax(row)])
    symbol_specific = _sort_rows([row for row in accepted if row.get("category") == "symbol"])
    gate_combo_specific = _sort_rows([row for row in accepted if row.get("category") == "gate_combo"])
    risk_bucket_specific = _sort_rows([row for row in accepted if row.get("category") == "risk_bucket"])

    ok = not blockers
    recommendation = (
        "Review accepted counterfactual candidates as no-order filter research only. Parameter relaxation, paper, live, training, reload, and order gates remain closed."
        if accepted else
        "No accepted counterfactual review candidates. Continue no-order evidence collection and keep all trading gates closed."
    )

    return {
        "ok": ok,
        "contract_version": CONTRACT_VERSION,
        "source_h4_contract_version": h4_artifact.get("contract_version"),
        "report_type": REPORT_TYPE,
        "generated_at_utc": utc_now_iso(),
        "branch_id": h4_artifact.get("branch_id", "HYP-006-R1"),
        "branch_name": h4_artifact.get("branch_name", "failed_downside_sweep_reversal_continuation_short"),
        "hypothesis_id": h4_artifact.get("hypothesis_id", "HYP-006"),
        "strategy_family": h4_artifact.get("strategy_family", "short_failed_liquidity_sweep_continuation"),
        "timeframe": h4_artifact.get("timeframe", "4h"),
        "decision": "HYP006_R1_COUNTERFACTUAL_FILTER_CANDIDATE_RANKING_READY" if ok else "HYP006_R1_COUNTERFACTUAL_FILTER_CANDIDATE_RANKING_BLOCKED",
        "blockers": blockers,
        "read_only": True,
        "no_order_measurement_only": True,
        "counterfactual_research_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "strategy_parameter_mutation_performed": False,
        "approved_for_gate_combo_counterfactual_review_candidate": bool(ok and gate_combo_specific),
        "approved_for_filter_candidate_review": bool(ok and accepted),
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "guard_thresholds": {
            "min_review_matured_count": MIN_REVIEW_MATURED_COUNT,
            "min_watchlist_matured_count": MIN_WATCHLIST_MATURED_COUNT,
            "min_review_win_rate_pct": MIN_REVIEW_WIN_RATE_PCT,
            "min_review_profit_factor": MIN_REVIEW_PROFIT_FACTOR,
            "min_review_mean_return_bps": MIN_REVIEW_MEAN_RETURN_BPS,
            "max_review_worst_return_bps": MAX_REVIEW_WORST_RETURN_BPS,
            "max_review_worst_mae_bps": MAX_REVIEW_WORST_MAE_BPS,
            "tail_risk_worst_return_bps": TAIL_RISK_WORST_RETURN_BPS,
            "tail_risk_worst_mae_bps": TAIL_RISK_WORST_MAE_BPS,
        },
        "source_h4_summary": {
            "attributed_near_miss_event_count": h4_artifact.get("attributed_near_miss_event_count"),
            "matured_near_miss_event_count": h4_artifact.get("matured_near_miss_event_count"),
            "near_miss_outcome_summary": h4_artifact.get("near_miss_outcome_summary", {}),
        },
        "candidate_row_count": len(rows),
        "accepted_review_candidate_count": len(accepted),
        "watchlist_low_sample_candidate_count": len(watchlist),
        "rejected_counterfactual_candidate_count": len(rejected),
        "tail_risk_flag_count": len(tail_flags),
        "do_not_relax_gate_combo_count": len(do_not_relax),
        "accepted_review_candidates": accepted,
        "gate_combo_specific_candidates": gate_combo_specific,
        "symbol_specific_candidates": symbol_specific,
        "risk_bucket_specific_candidates": risk_bucket_specific,
        "watchlist_low_sample_candidates": watchlist,
        "rejected_counterfactual_candidates": rejected,
        "tail_risk_flags": tail_flags,
        "do_not_relax_gate_combos": do_not_relax,
        "recommendation": recommendation,
    }


def render_markdown_report(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {CONTRACT_VERSION} HYP-006 Counterfactual Filter Candidate Ranking")
    lines.append("")
    lines.append("No-order gate-combo review pack. This report ranks counterfactual candidates only; it does not relax parameters or enable trading.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    for key in (
        "decision",
        "read_only",
        "counterfactual_research_only",
        "approved_for_filter_candidate_review",
        "approved_for_gate_combo_counterfactual_review_candidate",
        "approved_for_parameter_relaxation_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
        "order_actions_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Candidate counts")
    lines.append("")
    for key in (
        "candidate_row_count",
        "accepted_review_candidate_count",
        "watchlist_low_sample_candidate_count",
        "rejected_counterfactual_candidate_count",
        "tail_risk_flag_count",
        "do_not_relax_gate_combo_count",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Accepted review candidates")
    lines.append("")
    accepted = _sequence(payload.get("accepted_review_candidates"))
    if not accepted:
        lines.append("No accepted no-order review candidates.")
    else:
        lines.append("| category | key | matured | win % | mean bps | PF | worst bps | score | tail |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in accepted[:20]:
            item = _mapping(row)
            lines.append(
                f"| {item.get('category')} | {item.get('key')} | {item.get('matured_count')} | {item.get('win_rate_pct')} | {item.get('mean_return_bps')} | {item.get('profit_factor')} | {item.get('worst_return_bps')} | {item.get('review_score')} | {item.get('tail_risk_flag')} |"
            )
    lines.append("")
    lines.append("## Do-not-relax gate combos")
    lines.append("")
    blocked = _sequence(payload.get("do_not_relax_gate_combos"))
    if not blocked:
        lines.append("No do-not-relax gate combos were identified by the report guards.")
    else:
        lines.append("| key | matured | win % | mean bps | PF | worst bps | reasons |")
        lines.append("|---|---:|---:|---:|---:|---:|---|")
        for row in blocked[:20]:
            item = _mapping(row)
            reasons = ", ".join(str(reason) for reason in _sequence(item.get("ranking_guard_reasons")))
            lines.append(
                f"| {item.get('key')} | {item.get('matured_count')} | {item.get('win_rate_pct')} | {item.get('mean_return_bps')} | {item.get('profit_factor')} | {item.get('worst_return_bps')} | {reasons} |"
            )
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append(str(payload.get("recommendation") or ""))
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


def build_report_from_path(h4_json: str | os.PathLike[str]) -> dict[str, Any]:
    artifact = load_json(h4_json)
    return build_counterfactual_filter_candidate_ranking_report(_mapping(artifact))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run HYP-006 counterfactual filter candidate ranking no-order review pack")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--h4-json", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    h4_path = Path(args.h4_json) if args.h4_json else latest_h4_artifact(args.reports_dir)
    if h4_path is None:
        payload = build_counterfactual_filter_candidate_ranking_report({})
        payload["decision"] = "HYP006_R1_COUNTERFACTUAL_FILTER_CANDIDATE_RANKING_H4_ARTIFACT_NOT_FOUND"
        payload["ok"] = False
        if "SOURCE_H4_ARTIFACT_NOT_FOUND" not in payload["blockers"]:
            payload["blockers"].append("SOURCE_H4_ARTIFACT_NOT_FOUND")
        print(f"{CONTRACT_VERSION} HYP-006 counterfactual filter candidate ranking {payload['decision']}")
        return 2

    payload = build_report_from_path(h4_path)
    payload["source_h4_artifact_json"] = str(h4_path)
    report_json, report_md = write_report_bundle(payload, args.out_dir or args.reports_dir)
    print(f"{CONTRACT_VERSION} HYP-006 counterfactual filter candidate ranking {payload['decision']}")
    for key in (
        "read_only",
        "counterfactual_research_only",
        "candidate_row_count",
        "accepted_review_candidate_count",
        "watchlist_low_sample_candidate_count",
        "rejected_counterfactual_candidate_count",
        "tail_risk_flag_count",
        "do_not_relax_gate_combo_count",
        "approved_for_filter_candidate_review",
        "approved_for_parameter_relaxation_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
