from __future__ import annotations

import json
import math
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.27G-H5"
HYPOTHESIS_ID = "HYP-005"
BRANCH_NAME = "liquidity_sweep_reversal_vol_compression"
STRATEGY_FAMILY = "long_liquidity_sweep_reversal"
REPORT_PREFIX = "4B436627GH5_hyp005_r1_branch_review_closure"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
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


def load_json(path: str | os.PathLike[str] | None) -> Any:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str | os.PathLike[str] | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, Mapping):
            rows.append(dict(payload))
    return rows


def _atomic_write(path: Path, payload: bytes) -> None:
    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{resolved.name}.",
        suffix=".tmp",
        dir=resolved.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp_path.replace(resolved)
    finally:
        temp_path.unlink(missing_ok=True)


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    _atomic_write(Path(path), text.encode("utf-8"))


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _timestamp_token(row: Mapping[str, Any]) -> str:
    value = str(row.get("timestamp_utc") or row.get("timestamp") or "")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def _stable_id(row: Mapping[str, Any]) -> str:
    symbol = str(row.get("symbol") or "UNKNOWN").upper()
    timeframe = str(row.get("timeframe") or row.get("interval") or "4h")
    return str(row.get("observation_id") or f"{HYPOTHESIS_ID}-{symbol}-{timeframe}-{_timestamp_token(row)}")


def summarize_ledger(rows: Sequence[Mapping[str, Any]], *, target: int = 30) -> dict[str, Any]:
    returns = [safe_float(row.get("forward_return_bps_final"), 0.0) for row in rows if row.get("forward_return_bps_final") is not None]
    wins = [value for value in returns if value > 0]
    losses = [abs(value) for value in returns if value < 0]
    profit_factor = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    symbols = Counter(str(row.get("symbol") or "UNKNOWN").upper() for row in rows)
    timestamps: list[str] = []
    for row in rows:
        if row.get("timestamp_utc"):
            timestamps.append(str(row.get("timestamp_utc")))
    latest = max(timestamps) if timestamps else None
    return {
        "shadow_observation_count": len(rows),
        "shadow_sample_target": target,
        "shadow_sample_target_met": len(rows) >= target,
        "matured_count": len(returns),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate_pct": round(len(wins) / len(returns) * 100.0, 6) if returns else 0.0,
        "gross_profit_bps": round(sum(wins), 6),
        "gross_loss_bps": round(sum(losses), 6),
        "net_return_bps": round(sum(returns), 6),
        "mean_return_bps": round(sum(returns) / len(returns), 6) if returns else None,
        "median_return_bps": None if not returns else round(_median(returns) or 0.0, 6),
        "profit_factor": round(profit_factor, 6),
        "worst_return_bps": round(min(returns), 6) if returns else None,
        "best_return_bps": round(max(returns), 6) if returns else None,
        "latest_observation_utc": latest,
        "symbols_observed_count": len(symbols),
        "symbol_counts": dict(sorted(symbols.items())),
        "unique_observation_ids": len({_stable_id(row) for row in rows}),
    }


def _get_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _h3_evidence(h3_report: Mapping[str, Any] | None) -> dict[str, Any]:
    h3 = _get_mapping(h3_report)
    stagnation = _get_mapping(h3.get("stagnation"))
    candidate = _get_mapping(h3.get("candidate_diagnostics"))
    return {
        "available": bool(h3),
        "contract_version": h3.get("contract_version"),
        "decision": h3.get("decision"),
        "stagnation_status": stagnation.get("status"),
        "days_since_latest_observation": stagnation.get("days_since_latest_observation"),
        "new_unique_observation_available": bool(stagnation.get("new_unique_observation_available", False)),
        "duplicate_only_current_candidates": bool(stagnation.get("duplicate_only_current_candidates", False)),
        "exact_candidate_count": safe_int(candidate.get("exact_candidate_count"), 0),
        "new_unique_candidate_count": safe_int(candidate.get("new_unique_candidate_count"), 0),
        "duplicate_candidate_count": safe_int(candidate.get("duplicate_candidate_count"), 0),
        "near_miss_count": safe_int(candidate.get("near_miss_count"), 0),
        "top_bottleneck_filter": candidate.get("top_bottleneck_filter"),
    }


def _h4_evidence(h4_report: Mapping[str, Any] | None) -> dict[str, Any]:
    h4 = _get_mapping(h4_report)
    summary = _get_mapping(h4.get("research_summary"))
    top_variants = h4.get("top_variants") if isinstance(h4.get("top_variants"), Sequence) else []
    best_variant = top_variants[0] if top_variants and isinstance(top_variants[0], Mapping) else {}
    performance = _get_mapping(best_variant.get("performance"))
    return {
        "available": bool(h4),
        "contract_version": h4.get("contract_version"),
        "decision": h4.get("decision"),
        "variant_count": safe_int(summary.get("variant_count"), 0),
        "variants_with_new_unique_candidates": safe_int(summary.get("variants_with_new_unique_candidates"), 0),
        "promising_research_only_variant_count": safe_int(summary.get("promising_research_only_variant_count"), 0),
        "paper_transition_candidate_found": bool(summary.get("paper_transition_candidate_found", False)),
        "strategy_parameter_mutation_recommended": bool(summary.get("strategy_parameter_mutation_recommended", False)),
        "best_research_variant_id": summary.get("best_research_variant_id"),
        "best_research_status": summary.get("best_research_status"),
        "best_variant_net_return_bps": performance.get("net_return_bps"),
        "best_variant_mean_return_bps": performance.get("mean_return_bps"),
        "best_variant_profit_factor": performance.get("profit_factor"),
        "best_variant_new_unique_candidate_count": best_variant.get("new_unique_candidate_count"),
    }


def _snapshot_evidence(snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    snap = _get_mapping(snapshot)
    audit = _get_mapping(snap.get("audit"))
    performance = _get_mapping(snap.get("performance"))
    return {
        "available": bool(snap),
        "contract_version": snap.get("contract_version"),
        "mode": snap.get("mode"),
        "system_status": snap.get("system_status"),
        "dashboard_status": audit.get("dashboard_status"),
        "paper_transition_ready": bool(audit.get("paper_transition_ready", False)),
        "approved_for_paper_candidate": bool(audit.get("approved_for_paper_candidate", False)),
        "approved_for_live_real": bool(audit.get("approved_for_live_real", False)),
        "sample_count": performance.get("sample_count"),
        "profit_factor": performance.get("profit_factor"),
        "mean_return_bps": performance.get("mean_return_bps"),
    }


def build_branch_review_closure_report(
    *,
    ledger_rows: Sequence[Mapping[str, Any]],
    h3_report: Mapping[str, Any] | None,
    h4_report: Mapping[str, Any] | None,
    operator_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ledger_summary = summarize_ledger(ledger_rows)
    h3 = _h3_evidence(h3_report)
    h4 = _h4_evidence(h4_report)
    snapshot = _snapshot_evidence(operator_snapshot)

    sample_incomplete = not bool(ledger_summary["shadow_sample_target_met"])
    negative_expectancy = (
        safe_float(ledger_summary.get("mean_return_bps"), 0.0) < 0.0
        and safe_float(ledger_summary.get("net_return_bps"), 0.0) < 0.0
        and safe_float(ledger_summary.get("profit_factor"), 0.0) < 1.0
    )
    h3_stagnated = h3["available"] and h3.get("stagnation_status") == "STAGNATED" and not h3.get("new_unique_observation_available")
    h4_rejected = (
        h4["available"]
        and not h4.get("paper_transition_candidate_found")
        and not h4.get("strategy_parameter_mutation_recommended")
        and safe_int(h4.get("promising_research_only_variant_count"), 0) == 0
        and str(h4.get("best_research_status")) == "REJECTED_NEGATIVE_EXPECTANCY"
    )
    cockpit_blocked = (not snapshot["available"]) or (
        not snapshot.get("paper_transition_ready")
        and not snapshot.get("approved_for_paper_candidate")
        and not snapshot.get("approved_for_live_real")
    )

    closure_recommended = bool(sample_incomplete and negative_expectancy and h3_stagnated and h4_rejected and cockpit_blocked)
    closure_status = "CLOSE_NO_PROMOTION_RECOMMENDED" if closure_recommended else "KEEP_RESEARCH_WATCHLIST_PENDING_MORE_EVIDENCE"
    decision = "HYP005_R1_BRANCH_REVIEW_NO_PROMOTION_CLOSURE_READY" if closure_recommended else "HYP005_R1_BRANCH_REVIEW_NO_PROMOTION_REVIEW_PENDING"

    closure_criteria = {
        "sample_target_incomplete": sample_incomplete,
        "negative_expectancy_confirmed": negative_expectancy,
        "h3_stagnation_confirmed": h3_stagnated,
        "h4_relaxation_rejected": h4_rejected,
        "cockpit_paper_live_blocked": cockpit_blocked,
    }
    risk_items: list[dict[str, str]] = []
    if sample_incomplete:
        risk_items.append({"level": "warning", "code": "SAMPLE_TARGET_INCOMPLETE", "detail": f"{ledger_summary['shadow_observation_count']} / {ledger_summary['shadow_sample_target']} unique observations."})
    if negative_expectancy:
        risk_items.append({"level": "critical", "code": "NEGATIVE_EXPECTANCY", "detail": f"mean={ledger_summary['mean_return_bps']} bps, PF={ledger_summary['profit_factor']}"})
    if h3_stagnated:
        risk_items.append({"level": "warning", "code": "OBSERVATION_STREAM_STAGNATED", "detail": f"latest={ledger_summary.get('latest_observation_utc')}, bottleneck={h3.get('top_bottleneck_filter')}"})
    if h4_rejected:
        risk_items.append({"level": "critical", "code": "PARAMETER_RELAXATION_REJECTED", "detail": f"best={h4.get('best_research_variant_id')} status={h4.get('best_research_status')}"})

    recommendation = (
        "Close HYP-005-R1 as no-promotion research branch. Do not mutate parameters, train, reload, paper trade, live trade, or send orders."
        if closure_recommended
        else "Do not promote. Keep branch under research review until missing closure evidence is supplied."
    )

    return {
        "contract_version": CONTRACT_VERSION,
        "report_type": "hyp005_r1_branch_review_negative_expectancy_closure_no_promotion_decision_pack",
        "generated_at_utc": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "selected_strategy_family": STRATEGY_FAMILY,
        "decision": decision,
        "closure_status": closure_status,
        "ok": True,
        "read_only": True,
        "no_order_branch_review_only": True,
        "branch_state_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_transition_candidate_found": False,
        "branch_closure_recommended": closure_recommended,
        "operator_review_required_for_closure": True,
        "closure_criteria": closure_criteria,
        "ledger_summary": ledger_summary,
        "h3_stagnation_evidence": h3,
        "h4_sensitivity_evidence": h4,
        "operator_snapshot_evidence": snapshot,
        "risk_items": risk_items,
        "reason_codes": [
            "NO_ORDER_BRANCH_REVIEW_ONLY",
            "NO_PROMOTION_DECISION_PACK",
            "PAPER_LIVE_GATES_REMAIN_CLOSED",
            "BRANCH_STATE_MUTATION_NOT_PERFORMED",
        ],
        "warnings": ["BRANCH_CLOSURE_REQUIRES_OPERATOR_ACCEPTANCE"],
        "recommendation": recommendation,
    }


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    ledger = _get_mapping(payload.get("ledger_summary"))
    h3 = _get_mapping(payload.get("h3_stagnation_evidence"))
    h4 = _get_mapping(payload.get("h4_sensitivity_evidence"))
    criteria = _get_mapping(payload.get("closure_criteria"))
    lines = [
        "# 4B.4.3.6.6.27G-H5 HYP-005-R1 Branch Review Closure Evidence",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- closure_status: `{payload.get('closure_status')}`",
        f"- branch_closure_recommended: `{payload.get('branch_closure_recommended')}`",
        f"- operator_review_required_for_closure: `{payload.get('operator_review_required_for_closure')}`",
        "",
        "## Ledger Evidence",
        f"- observations: `{ledger.get('shadow_observation_count')} / {ledger.get('shadow_sample_target')}`",
        f"- mean_return_bps: `{ledger.get('mean_return_bps')}`",
        f"- net_return_bps: `{ledger.get('net_return_bps')}`",
        f"- profit_factor: `{ledger.get('profit_factor')}`",
        "",
        "## H3 Evidence",
        f"- stagnation_status: `{h3.get('stagnation_status')}`",
        f"- top_bottleneck_filter: `{h3.get('top_bottleneck_filter')}`",
        "",
        "## H4 Evidence",
        f"- best_research_variant_id: `{h4.get('best_research_variant_id')}`",
        f"- best_research_status: `{h4.get('best_research_status')}`",
        f"- promising_research_only_variant_count: `{h4.get('promising_research_only_variant_count')}`",
        "",
        "## Closure Criteria",
    ]
    for key, value in sorted(criteria.items()):
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Recommendation", "", str(payload.get("recommendation", ""))])
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")
