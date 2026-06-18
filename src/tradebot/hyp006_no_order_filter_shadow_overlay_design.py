from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G-H6"
SOURCE_H5_CONTRACT_VERSION = "4B.4.3.6.6.28G-H5"
REPORT_TYPE = "hyp006_r1_no_order_filter_shadow_overlay_design_accepted_candidate_quarantine_review_pack"
REPORT_PREFIX = "4B436628G_H6_hyp006_r1_no_order_filter_shadow_overlay_design"
DEFAULT_REPORTS_DIR = "reports/hyp006_r1_canonical"
DEFAULT_H5_PATTERN = "4B436628G_H5_hyp006_r1_counterfactual_filter_candidate_ranking_*.json"

PRIMARY_OVERLAY_STATUS = "ACCEPTED_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_CANDIDATE"
QUARANTINE_STATUS = "QUARANTINE_REVIEW_ONLY_TAIL_RISK"
WATCHLIST_STATUS = "WATCHLIST_LOW_SAMPLE_NOT_PROMOTABLE"
BLOCKLIST_STATUS = "DO_NOT_RELAX_BLOCKLIST"

CORE_BLOCKLIST_GATES = {
    "DOWNSIDE_SWEEP_OCCURRED",
    "MIN_SWEEP_DEPTH_BPS",
    "RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE",
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


def latest_h5_artifact(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    target = Path(reports_dir)
    matches = sorted(target.glob(DEFAULT_H5_PATTERN), key=lambda item: item.stat().st_mtime, reverse=True)
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
    copied["parameter_change_allowed"] = False
    copied["paper_live_order_allowed"] = False
    copied["training_reload_allowed"] = False
    return copied


def _row_identity(row: Mapping[str, Any]) -> str:
    return f"{row.get('category')}::{row.get('key')}"


def _dedupe_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
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


def _tail_risk_identities(h5_artifact: Mapping[str, Any]) -> set[str]:
    identities: set[str] = set()
    for raw in _sequence(h5_artifact.get("tail_risk_flags")):
        row = _copy_row(_mapping(raw))
        identities.add(_row_identity(row))
    return identities


def _overlay_class(row: Mapping[str, Any]) -> str:
    category = str(row.get("category") or "unknown")
    key = str(row.get("key") or "UNKNOWN")
    if category == "symbol":
        return "SYMBOL_FILTER_SHADOW_OVERLAY"
    if category == "gate_combo":
        return "GATE_COMBO_FILTER_SHADOW_OVERLAY"
    if category == "risk_bucket":
        return "RISK_BUCKET_FILTER_SHADOW_OVERLAY"
    if key in CORE_BLOCKLIST_GATES:
        return "CORE_GATE_BLOCKLIST"
    return "COUNTERFACTUAL_FILTER_SHADOW_OVERLAY"


def _overlay_predicate(row: Mapping[str, Any]) -> dict[str, Any]:
    category = str(row.get("category") or "unknown")
    key = str(row.get("key") or "UNKNOWN")
    if category == "symbol":
        return {"type": "symbol_whitelist", "include_symbols": [key]}
    if category == "gate_combo":
        return {"type": "failed_gate_combo_match", "failed_gate_combo": key}
    if category == "risk_bucket":
        return {"type": "risk_bucket_match", "risk_bucket": key}
    return {"type": "candidate_key_match", "key": key}


def _design_row(row: Mapping[str, Any], *, status: str, quarantine: bool = False) -> dict[str, Any]:
    copied = _copy_row(row)
    copied["overlay_class"] = _overlay_class(copied)
    copied["overlay_predicate"] = _overlay_predicate(copied)
    copied["overlay_status"] = status
    copied["quarantine_required"] = bool(quarantine)
    copied["shadow_overlay_measurement_only"] = True
    copied["runtime_activation_allowed"] = False
    copied["parameter_relaxation_allowed"] = False
    copied["paper_live_order_allowed"] = False
    copied["notes"] = _row_notes(copied, status=status, quarantine=quarantine)
    return copied


def _row_notes(row: Mapping[str, Any], *, status: str, quarantine: bool) -> list[str]:
    notes = ["NO_ORDER_SHADOW_OVERLAY_DESIGN_ONLY", "NO_PARAMETER_CHANGE", "NO_PAPER_LIVE_ORDER"]
    if quarantine:
        notes.append("TAIL_RISK_QUARANTINE_REQUIRED")
    if status == BLOCKLIST_STATUS:
        notes.append("EXPLICIT_DO_NOT_RELAX_BLOCKLIST")
    if status == WATCHLIST_STATUS:
        notes.append("LOW_SAMPLE_WATCHLIST_NOT_PROMOTABLE")
    if row.get("category") == "symbol":
        notes.append("SYMBOL_SPECIFIC_FILTER_REVIEW")
    return notes


def build_no_order_filter_shadow_overlay_design_report(h5_artifact: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if h5_artifact.get("contract_version") != SOURCE_H5_CONTRACT_VERSION:
        blockers.append("SOURCE_H5_CONTRACT_VERSION_MISMATCH")
    if not h5_artifact.get("read_only", False):
        blockers.append("SOURCE_H5_NOT_READ_ONLY")
    if h5_artifact.get("approved_for_parameter_relaxation_candidate") is not False:
        blockers.append("SOURCE_H5_PARAMETER_RELAXATION_GATE_NOT_CLOSED")
    if h5_artifact.get("approved_for_paper_candidate") is not False or h5_artifact.get("approved_for_live_real") is not False:
        blockers.append("SOURCE_H5_TRADING_GATE_NOT_CLOSED")

    accepted = _dedupe_rows(_sequence(h5_artifact.get("accepted_review_candidates")))
    watchlist = _dedupe_rows(_sequence(h5_artifact.get("watchlist_low_sample_candidates")))
    rejected = _dedupe_rows(_sequence(h5_artifact.get("rejected_counterfactual_candidates")))
    blocklist = _dedupe_rows(_sequence(h5_artifact.get("do_not_relax_gate_combos")))
    tail_ids = _tail_risk_identities(h5_artifact)

    primary_candidates: list[dict[str, Any]] = []
    quarantine_candidates: list[dict[str, Any]] = []
    for row in accepted:
        identity = _row_identity(row)
        tail_risk = bool(row.get("tail_risk_flag")) or identity in tail_ids
        if tail_risk:
            quarantine_candidates.append(_design_row(row, status=QUARANTINE_STATUS, quarantine=True))
        else:
            primary_candidates.append(_design_row(row, status=PRIMARY_OVERLAY_STATUS, quarantine=False))

    watchlist_designs = [_design_row(row, status=WATCHLIST_STATUS, quarantine=False) for row in watchlist]
    blocklist_designs = [_design_row(row, status=BLOCKLIST_STATUS, quarantine=False) for row in blocklist]

    ok = not blockers
    primary_candidates = _sort_rows(primary_candidates)
    quarantine_candidates = _sort_rows(quarantine_candidates)
    watchlist_designs = _sort_rows(watchlist_designs)
    blocklist_designs = _sort_rows(blocklist_designs)
    rejected_designs = _sort_rows([_design_row(row, status="REJECTED_COUNTERFACTUAL_NOT_PROMOTABLE") for row in rejected])

    recommendation = (
        "Use primary candidates only as no-order shadow overlay designs. Keep quarantine candidates isolated, keep do-not-relax gate combos blocked, and keep all parameter/paper/live/order gates closed."
        if primary_candidates
        else "No primary no-order overlay candidate is available. Keep all candidates in review or rejection state and keep all gates closed."
    )

    return {
        "ok": ok,
        "contract_version": CONTRACT_VERSION,
        "source_h5_contract_version": h5_artifact.get("contract_version"),
        "report_type": REPORT_TYPE,
        "generated_at_utc": utc_now_iso(),
        "branch_id": h5_artifact.get("branch_id", "HYP-006-R1"),
        "branch_name": h5_artifact.get("branch_name", "failed_downside_sweep_reversal_continuation_short"),
        "hypothesis_id": h5_artifact.get("hypothesis_id", "HYP-006"),
        "strategy_family": h5_artifact.get("strategy_family", "short_failed_liquidity_sweep_continuation"),
        "timeframe": h5_artifact.get("timeframe", "4h"),
        "decision": "HYP006_R1_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_READY" if ok else "HYP006_R1_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_BLOCKED",
        "blockers": blockers,
        "read_only": True,
        "no_order_measurement_only": True,
        "counterfactual_research_only": True,
        "filter_shadow_overlay_design_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "strategy_parameter_mutation_performed": False,
        "runtime_overlay_activation_performed": False,
        "approved_for_filter_shadow_overlay_candidate": bool(ok and primary_candidates),
        "approved_for_quarantine_review_candidate": bool(ok and quarantine_candidates),
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "source_h5_summary": {
            "candidate_row_count": h5_artifact.get("candidate_row_count"),
            "accepted_review_candidate_count": h5_artifact.get("accepted_review_candidate_count"),
            "watchlist_low_sample_candidate_count": h5_artifact.get("watchlist_low_sample_candidate_count"),
            "rejected_counterfactual_candidate_count": h5_artifact.get("rejected_counterfactual_candidate_count"),
            "tail_risk_flag_count": h5_artifact.get("tail_risk_flag_count"),
            "do_not_relax_gate_combo_count": h5_artifact.get("do_not_relax_gate_combo_count"),
        },
        "overlay_policy": {
            "primary_candidate_rule": "accepted_review_candidate AND NOT tail_risk_flag",
            "quarantine_rule": "accepted_review_candidate AND tail_risk_flag",
            "watchlist_rule": "low_sample_candidate, not promotable",
            "blocklist_rule": "do_not_relax_gate_combos remain explicit rejects",
            "runtime_activation_allowed": False,
            "parameter_relaxation_allowed": False,
            "paper_live_order_allowed": False,
        },
        "accepted_primary_overlay_candidate_count": len(primary_candidates),
        "quarantine_review_candidate_count": len(quarantine_candidates),
        "watchlist_overlay_candidate_count": len(watchlist_designs),
        "rejected_overlay_candidate_count": len(rejected_designs),
        "do_not_relax_blocklist_count": len(blocklist_designs),
        "accepted_primary_overlay_candidates": primary_candidates,
        "quarantine_review_candidates": quarantine_candidates,
        "watchlist_low_sample_overlay_candidates": watchlist_designs,
        "rejected_overlay_candidates": rejected_designs,
        "do_not_relax_gate_combo_blocklist": blocklist_designs,
        "recommendation": recommendation,
    }


def render_markdown_report(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {CONTRACT_VERSION} HYP-006 No-Order Filter Shadow Overlay Design")
    lines.append("")
    lines.append("Accepted candidate quarantine review pack. This report designs no-order overlay candidates only; it does not change thresholds, activate runtime overlays, or enable trading.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    for key in (
        "decision",
        "read_only",
        "filter_shadow_overlay_design_only",
        "approved_for_filter_shadow_overlay_candidate",
        "approved_for_quarantine_review_candidate",
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
    lines.append("## Counts")
    lines.append("")
    for key in (
        "accepted_primary_overlay_candidate_count",
        "quarantine_review_candidate_count",
        "watchlist_overlay_candidate_count",
        "rejected_overlay_candidate_count",
        "do_not_relax_blocklist_count",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Primary no-order overlay candidates")
    lines.append("")
    primary = _sequence(payload.get("accepted_primary_overlay_candidates"))
    if not primary:
        lines.append("No primary no-order overlay candidates.")
    else:
        lines.append("| category | key | overlay class | matured | win % | mean bps | PF | worst bps | status |")
        lines.append("|---|---|---|---:|---:|---:|---:|---:|---|")
        for row in primary[:20]:
            item = _mapping(row)
            lines.append(
                f"| {item.get('category')} | {item.get('key')} | {item.get('overlay_class')} | {item.get('matured_count')} | {item.get('win_rate_pct')} | {item.get('mean_return_bps')} | {item.get('profit_factor')} | {item.get('worst_return_bps')} | {item.get('overlay_status')} |"
            )
    lines.append("")
    lines.append("## Quarantine candidates")
    lines.append("")
    quarantine = _sequence(payload.get("quarantine_review_candidates"))
    if not quarantine:
        lines.append("No quarantine candidates.")
    else:
        lines.append("| category | key | matured | win % | mean bps | PF | worst bps | tail reasons |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---|")
        for row in quarantine[:20]:
            item = _mapping(row)
            tail_reasons = ", ".join(str(value) for value in _sequence(item.get("tail_risk_reasons")))
            lines.append(
                f"| {item.get('category')} | {item.get('key')} | {item.get('matured_count')} | {item.get('win_rate_pct')} | {item.get('mean_return_bps')} | {item.get('profit_factor')} | {item.get('worst_return_bps')} | {tail_reasons} |"
            )
    lines.append("")
    lines.append("## Do-not-relax blocklist")
    lines.append("")
    blocklist = _sequence(payload.get("do_not_relax_gate_combo_blocklist"))
    if not blocklist:
        lines.append("No explicit do-not-relax blocklist rows.")
    else:
        lines.append("| key | matured | win % | mean bps | PF | worst bps |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for row in blocklist[:20]:
            item = _mapping(row)
            lines.append(
                f"| {item.get('key')} | {item.get('matured_count')} | {item.get('win_rate_pct')} | {item.get('mean_return_bps')} | {item.get('profit_factor')} | {item.get('worst_return_bps')} |"
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


def build_report_from_path(h5_json: str | os.PathLike[str]) -> dict[str, Any]:
    artifact = load_json(h5_json)
    return build_no_order_filter_shadow_overlay_design_report(_mapping(artifact))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run HYP-006 no-order filter shadow overlay design accepted candidate quarantine review pack")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--h5-json", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    h5_path = Path(args.h5_json) if args.h5_json else latest_h5_artifact(args.reports_dir)
    if h5_path is None:
        payload = build_no_order_filter_shadow_overlay_design_report({})
        payload["decision"] = "HYP006_R1_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_H5_ARTIFACT_NOT_FOUND"
        payload["ok"] = False
        if "SOURCE_H5_ARTIFACT_NOT_FOUND" not in payload["blockers"]:
            payload["blockers"].append("SOURCE_H5_ARTIFACT_NOT_FOUND")
        print(f"{CONTRACT_VERSION} HYP-006 no-order filter shadow overlay design {payload['decision']}")
        return 2

    payload = build_report_from_path(h5_path)
    payload["source_h5_artifact_json"] = str(h5_path)
    report_json, report_md = write_report_bundle(payload, args.out_dir or args.reports_dir)
    print(f"{CONTRACT_VERSION} HYP-006 no-order filter shadow overlay design {payload['decision']}")
    for key in (
        "read_only",
        "filter_shadow_overlay_design_only",
        "accepted_primary_overlay_candidate_count",
        "quarantine_review_candidate_count",
        "watchlist_overlay_candidate_count",
        "do_not_relax_blocklist_count",
        "approved_for_filter_shadow_overlay_candidate",
        "approved_for_quarantine_review_candidate",
        "approved_for_parameter_relaxation_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "runtime_overlay_activation_performed",
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
