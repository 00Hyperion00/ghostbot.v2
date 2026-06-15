from __future__ import annotations

import json
import math
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28A"
HYPOTHESIS_ID = "HYP-005"
FAILED_BRANCH_NAME = "liquidity_sweep_reversal_vol_compression"
FAILED_STRATEGY_FAMILY = "long_liquidity_sweep_reversal"
REPORT_PREFIX = "4B436628A_new_hypothesis_candidate_discovery"


@dataclass(frozen=True)
class LedgerSummary:
    sample_count: int
    matured_count: int
    win_count: int
    loss_count: int
    win_rate_pct: float
    gross_profit_bps: float
    gross_loss_bps: float
    net_return_bps: float
    mean_return_bps: float | None
    median_return_bps: float | None
    profit_factor: float
    worst_return_bps: float | None
    best_return_bps: float | None
    latest_observation_utc: str | None
    symbols_observed_count: int
    symbol_counts: dict[str, int]
    worst_timestamp_cluster: dict[str, Any]


@dataclass(frozen=True)
class FailedBranchLessons:
    closure_status: str
    negative_expectancy_confirmed: bool
    stagnation_confirmed: bool
    parameter_relaxation_rejected: bool
    sample_target_incomplete: bool
    top_bottleneck_filter: str | None
    best_relaxed_variant_status: str | None
    lesson_codes: list[str]


@dataclass(frozen=True)
class ResearchCandidate:
    candidate_id: str
    branch_name: str
    strategy_family: str
    research_thesis: str
    evidence_basis: list[str]
    score: float
    expected_edge_proxy_bps: float | None
    risk_level: str
    rejection_risks: list[str]
    required_next_gate: str
    selected_for_no_order_research: bool
    approved_for_candidate_spec_drafting: bool
    approved_for_shadow_collection: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool


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


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    selected = payload.get("selected_research_candidate") or {}
    ledger = payload.get("failed_branch_ledger_summary") or {}
    lines = [
        "# 4B.4.3.6.6.28A New Hypothesis Candidate Discovery",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- failed_branch: `{payload.get('failed_branch_name')}`",
        f"- closure_status: `{payload.get('failed_branch_lessons', {}).get('closure_status')}`",
        f"- sample_count: `{ledger.get('sample_count')}`",
        f"- mean_return_bps: `{ledger.get('mean_return_bps')}`",
        f"- profit_factor: `{ledger.get('profit_factor')}`",
        f"- selected_candidate_id: `{selected.get('candidate_id')}`",
        f"- selected_candidate_branch: `{selected.get('branch_name')}`",
        f"- next_gate: `{selected.get('required_next_gate')}`",
        "",
        "## Recommendation",
        "",
        str(payload.get("recommendation", "")),
    ]
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _final_return(row: Mapping[str, Any]) -> float | None:
    value = row.get("forward_return_bps_final")
    if value is None:
        value = row.get("final_return_bps")
    if value is None:
        return None
    return safe_float(value)


def summarize_ledger(rows: Sequence[Mapping[str, Any]]) -> LedgerSummary:
    returns = [value for row in rows if (value := _final_return(row)) is not None]
    wins = [value for value in returns if value > 0]
    losses = [abs(value) for value in returns if value < 0]
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    profit_factor = gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0)
    timestamps = [str(row.get("timestamp_utc") or "") for row in rows if row.get("timestamp_utc")]
    symbol_counts = dict(Counter(str(row.get("symbol") or "UNKNOWN").upper() for row in rows))
    cluster_returns: dict[str, list[float]] = defaultdict(list)
    cluster_symbols: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        timestamp = str(row.get("timestamp_utc") or "")
        value = _final_return(row)
        if timestamp and value is not None:
            cluster_returns[timestamp].append(value)
            cluster_symbols[timestamp].add(str(row.get("symbol") or "UNKNOWN").upper())
    worst_cluster: dict[str, Any] = {}
    if cluster_returns:
        worst_ts = min(cluster_returns, key=lambda item: sum(cluster_returns[item]))
        worst_values = cluster_returns[worst_ts]
        worst_cluster = {
            "timestamp_utc": worst_ts,
            "sample_count": len(worst_values),
            "symbols": sorted(cluster_symbols[worst_ts]),
            "net_return_bps": round(sum(worst_values), 6),
            "mean_return_bps": round(sum(worst_values) / len(worst_values), 6),
            "gross_loss_bps": round(sum(abs(v) for v in worst_values if v < 0), 6),
        }
    return LedgerSummary(
        sample_count=len(rows),
        matured_count=len(returns),
        win_count=len(wins),
        loss_count=len(losses),
        win_rate_pct=round(len(wins) / len(returns) * 100.0, 6) if returns else 0.0,
        gross_profit_bps=round(gross_profit, 6),
        gross_loss_bps=round(gross_loss, 6),
        net_return_bps=round(sum(returns), 6) if returns else 0.0,
        mean_return_bps=round(sum(returns) / len(returns), 6) if returns else None,
        median_return_bps=None if (median := _median(returns)) is None else round(median, 6),
        profit_factor=round(profit_factor, 6),
        worst_return_bps=None if not returns else round(min(returns), 6),
        best_return_bps=None if not returns else round(max(returns), 6),
        latest_observation_utc=max(timestamps) if timestamps else None,
        symbols_observed_count=len(symbol_counts),
        symbol_counts=symbol_counts,
        worst_timestamp_cluster=worst_cluster,
    )


def extract_failed_branch_lessons(
    *,
    ledger_summary: LedgerSummary,
    h3_diagnostics: Mapping[str, Any] | None,
    h4_sensitivity: Mapping[str, Any] | None,
    h5_closure: Mapping[str, Any] | None,
) -> FailedBranchLessons:
    h3 = h3_diagnostics or {}
    h4 = h4_sensitivity or {}
    h5 = h5_closure or {}
    h3_stag = h3.get("stagnation", {}) if isinstance(h3.get("stagnation"), Mapping) else {}
    h3_diag = h3.get("candidate_diagnostics", {}) if isinstance(h3.get("candidate_diagnostics"), Mapping) else {}
    h4_summary = h4.get("research_summary", {}) if isinstance(h4.get("research_summary"), Mapping) else {}
    closure_criteria = h5.get("closure_criteria", {}) if isinstance(h5.get("closure_criteria"), Mapping) else {}
    negative_expectancy = ledger_summary.mean_return_bps is not None and ledger_summary.mean_return_bps < 0 and ledger_summary.profit_factor < 1.0
    stagnation = bool(h3_stag.get("status") == "STAGNATED" or closure_criteria.get("h3_stagnation_confirmed"))
    relaxation_rejected = bool(
        h4_summary.get("paper_transition_candidate_found") is False
        and h4_summary.get("promising_research_only_variant_count", 0) == 0
        or closure_criteria.get("h4_relaxation_rejected")
    )
    sample_target_incomplete = ledger_summary.sample_count < 30 or bool(closure_criteria.get("sample_target_incomplete"))
    lesson_codes: list[str] = []
    if negative_expectancy:
        lesson_codes.append("FAILED_BRANCH_NEGATIVE_EXPECTANCY")
    if stagnation:
        lesson_codes.append("FAILED_BRANCH_STAGNATED_SAMPLE_STREAM")
    if relaxation_rejected:
        lesson_codes.append("THRESHOLD_RELAXATION_REJECTED")
    if sample_target_incomplete:
        lesson_codes.append("SAMPLE_TARGET_INCOMPLETE")
    if ledger_summary.worst_timestamp_cluster:
        lesson_codes.append("TIMESTAMP_CLUSTER_TAIL_RISK_PRESENT")
    return FailedBranchLessons(
        closure_status=str(h5.get("closure_status") or "CLOSE_NO_PROMOTION_RECOMMENDED"),
        negative_expectancy_confirmed=negative_expectancy,
        stagnation_confirmed=stagnation,
        parameter_relaxation_rejected=relaxation_rejected,
        sample_target_incomplete=sample_target_incomplete,
        top_bottleneck_filter=str(h3_diag.get("top_bottleneck_filter") or h3.get("top_bottleneck_filter") or "") or None,
        best_relaxed_variant_status=str(h4_summary.get("best_research_status") or "") or None,
        lesson_codes=lesson_codes,
    )


def _mirror_short_candidate(ledger_summary: LedgerSummary, lessons: FailedBranchLessons) -> ResearchCandidate:
    inverse_mean = None if ledger_summary.mean_return_bps is None else -ledger_summary.mean_return_bps
    inverse_pf = (ledger_summary.gross_loss_bps / ledger_summary.gross_profit_bps) if ledger_summary.gross_profit_bps > 0 else 0.0
    score = 0.0
    if inverse_mean is not None and inverse_mean > 0:
        score += min(35.0, inverse_mean / 4.0)
    if inverse_pf > 1.0:
        score += min(30.0, (inverse_pf - 1.0) * 15.0)
    score += 15.0 if lessons.negative_expectancy_confirmed else 0.0
    score -= 10.0 if lessons.stagnation_confirmed else 0.0
    score = round(max(0.0, min(100.0, score)), 6)
    selected = score >= 45.0
    return ResearchCandidate(
        candidate_id="HYP-006-R1",
        branch_name="failed_downside_sweep_reversal_continuation_short",
        strategy_family="short_failed_liquidity_sweep_continuation",
        research_thesis=(
            "HYP-005-R1 long reversal entries show persistent negative expectancy; test the inverse continuation thesis "
            "as a fresh no-order shadow branch, without reusing the failed branch as a trading approval."
        ),
        evidence_basis=[
            "HYP-005-R1 negative expectancy",
            "mirror-return proxy is positive only as a hypothesis seed",
            "requires independent candidate spec and no-order shadow validation",
        ],
        score=score,
        expected_edge_proxy_bps=None if inverse_mean is None else round(inverse_mean, 6),
        risk_level="HIGH",
        rejection_risks=[
            "mirror evidence is not executable edge",
            "short-side borrow/funding/slippage not modeled",
            "cluster-tail risk may simply invert into gap-risk",
        ],
        required_next_gate="28B_CANDIDATE_SPEC_DRAFT_AND_NO_ORDER_SHADOW_REGISTRATION",
        selected_for_no_order_research=selected,
        approved_for_candidate_spec_drafting=selected,
        approved_for_shadow_collection=False,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
    )


def _tail_filter_candidate(ledger_summary: LedgerSummary, lessons: FailedBranchLessons) -> ResearchCandidate:
    cluster_loss = safe_float(ledger_summary.worst_timestamp_cluster.get("gross_loss_bps") if ledger_summary.worst_timestamp_cluster else None)
    score = min(70.0, cluster_loss / 35.0) if cluster_loss > 0 else 15.0
    if "TIMESTAMP_CLUSTER_TAIL_RISK_PRESENT" in lessons.lesson_codes:
        score += 15.0
    score = round(min(100.0, score), 6)
    return ResearchCandidate(
        candidate_id="HYP-007-R1",
        branch_name="timestamp_cluster_tail_risk_no_trade_filter",
        strategy_family="risk_filter_regime_classifier",
        research_thesis=(
            "The failed branch loss is concentrated in timestamp clusters; research a no-trade regime filter before adding new directional exposure."
        ),
        evidence_basis=[
            "worst timestamp cluster contributes outsized loss",
            "risk-control branch can reduce tail exposure without increasing order frequency",
        ],
        score=score,
        expected_edge_proxy_bps=None,
        risk_level="MEDIUM",
        rejection_risks=[
            "filter may overfit a small 21-sample ledger",
            "does not create standalone alpha",
        ],
        required_next_gate="28B_FILTER_SPEC_DRAFT_AND_NO_ORDER_REPLAY_VALIDATION",
        selected_for_no_order_research=False,
        approved_for_candidate_spec_drafting=score >= 55.0,
        approved_for_shadow_collection=False,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
    )


def _mean_reversion_quality_candidate(ledger_summary: LedgerSummary, lessons: FailedBranchLessons) -> ResearchCandidate:
    score = 25.0
    if lessons.parameter_relaxation_rejected:
        score += 10.0
    if ledger_summary.win_rate_pct >= 45.0:
        score += 10.0
    if ledger_summary.profit_factor < 0.6:
        score -= 15.0
    score = round(max(0.0, min(100.0, score)), 6)
    return ResearchCandidate(
        candidate_id="HYP-008-R1",
        branch_name="liquidity_sweep_reversal_quality_gate_v2",
        strategy_family="long_liquidity_sweep_reversal_quality_filtered",
        research_thesis=(
            "Retain the reversal family only if a new quality gate can eliminate low-MFE/high-MAE and high-slippage cases."
        ),
        evidence_basis=[
            "raw threshold relaxation was rejected",
            "some winners exist but branch-level PF remains below one",
        ],
        score=score,
        expected_edge_proxy_bps=ledger_summary.mean_return_bps,
        risk_level="HIGH",
        rejection_risks=[
            "likely curve-fit on small failed branch sample",
            "same signal family already failed promotion evidence",
        ],
        required_next_gate="RESEARCH_ONLY_OFFLINE_REPLAY_BEFORE_ANY_SHADOW_REGISTRATION",
        selected_for_no_order_research=False,
        approved_for_candidate_spec_drafting=False,
        approved_for_shadow_collection=False,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
    )


def generate_research_candidates(ledger_summary: LedgerSummary, lessons: FailedBranchLessons) -> list[ResearchCandidate]:
    candidates = [
        _mirror_short_candidate(ledger_summary, lessons),
        _tail_filter_candidate(ledger_summary, lessons),
        _mean_reversion_quality_candidate(ledger_summary, lessons),
    ]
    candidates.sort(key=lambda item: item.score, reverse=True)
    selected_seen = False
    normalized: list[ResearchCandidate] = []
    for item in candidates:
        selected = bool(item.selected_for_no_order_research and not selected_seen)
        selected_seen = selected_seen or selected
        normalized.append(
            ResearchCandidate(
                candidate_id=item.candidate_id,
                branch_name=item.branch_name,
                strategy_family=item.strategy_family,
                research_thesis=item.research_thesis,
                evidence_basis=item.evidence_basis,
                score=item.score,
                expected_edge_proxy_bps=item.expected_edge_proxy_bps,
                risk_level=item.risk_level,
                rejection_risks=item.rejection_risks,
                required_next_gate=item.required_next_gate,
                selected_for_no_order_research=selected,
                approved_for_candidate_spec_drafting=item.approved_for_candidate_spec_drafting,
                approved_for_shadow_collection=False,
                approved_for_training_candidate=False,
                approved_for_paper_candidate=False,
                approved_for_live_real=False,
            )
        )
    return normalized


def build_hypothesis_candidate_discovery_report(
    *,
    ledger_rows: Sequence[Mapping[str, Any]],
    h3_diagnostics: Mapping[str, Any] | None = None,
    h4_sensitivity: Mapping[str, Any] | None = None,
    h5_closure: Mapping[str, Any] | None = None,
    operator_snapshot: Mapping[str, Any] | None = None,
    source_paths: Mapping[str, str | None] | None = None,
) -> dict[str, Any]:
    ledger_summary = summarize_ledger(ledger_rows)
    lessons = extract_failed_branch_lessons(
        ledger_summary=ledger_summary,
        h3_diagnostics=h3_diagnostics,
        h4_sensitivity=h4_sensitivity,
        h5_closure=h5_closure,
    )
    candidates = generate_research_candidates(ledger_summary, lessons)
    selected = next((item for item in candidates if item.selected_for_no_order_research), None)
    operator_snapshot = operator_snapshot or {}
    operator_paper_blocked = operator_snapshot.get("audit", {}).get("paper_transition_ready") is False if isinstance(operator_snapshot.get("audit"), Mapping) else True
    decision = "HYP005_FAILED_BRANCH_LESSONS_CANDIDATE_DISCOVERY_READY"
    reason_codes = [
        "NO_ORDER_RESEARCH_BRANCH_SELECTION_ONLY",
        "FAILED_BRANCH_LESSONS_INTEGRATED",
        "PAPER_LIVE_GATES_REMAIN_CLOSED",
        "NO_STRATEGY_PARAMETER_MUTATION_PERFORMED",
    ]
    if selected:
        reason_codes.append("NEXT_RESEARCH_CANDIDATE_SELECTED_FOR_SPEC_DRAFTING")
    else:
        reason_codes.append("NO_RESEARCH_CANDIDATE_SELECTED")
    risk_items: list[dict[str, Any]] = []
    if lessons.negative_expectancy_confirmed:
        risk_items.append({"level": "critical", "code": "FAILED_BRANCH_NEGATIVE_EXPECTANCY", "detail": f"mean={ledger_summary.mean_return_bps} bps, PF={ledger_summary.profit_factor}"})
    if lessons.parameter_relaxation_rejected:
        risk_items.append({"level": "critical", "code": "RELAXATION_REJECTED", "detail": str(lessons.best_relaxed_variant_status or "rejected")})
    if selected:
        risk_items.append({"level": "warning", "code": "SELECTED_CANDIDATE_REQUIRES_28B", "detail": selected.required_next_gate})
    return {
        "contract_version": CONTRACT_VERSION,
        "report_type": "new_hypothesis_candidate_discovery_failed_branch_lessons_no_order_research_selection_pack",
        "generated_at_utc": utc_now_iso(),
        "decision": decision,
        "ok": True,
        "hypothesis_id": HYPOTHESIS_ID,
        "failed_branch_name": FAILED_BRANCH_NAME,
        "failed_strategy_family": FAILED_STRATEGY_FAMILY,
        "read_only": True,
        "no_order_research_branch_selection_only": True,
        "branch_state_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
        "approved_for_shadow_collection": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_transition_candidate_found": False,
        "operator_review_required_for_selection": True,
        "candidate_spec_generation_required_next": bool(selected),
        "selected_research_candidate": None if selected is None else asdict(selected),
        "research_candidates": [asdict(item) for item in candidates],
        "failed_branch_ledger_summary": asdict(ledger_summary),
        "failed_branch_lessons": asdict(lessons),
        "operator_snapshot_evidence": {
            "available": bool(operator_snapshot),
            "paper_transition_ready": not operator_paper_blocked if operator_snapshot else False,
            "approved_for_live_real": bool(operator_snapshot.get("audit", {}).get("approved_for_live_real")) if isinstance(operator_snapshot.get("audit"), Mapping) else False,
        },
        "risk_items": risk_items,
        "reason_codes": reason_codes,
        "warnings": ["NEXT_BRANCH_REQUIRES_SEPARATE_28B_SPEC_AND_NO_ORDER_SHADOW_GATE"],
        "source_paths": dict(source_paths or {}),
        "recommendation": (
            "Draft a separate 28B candidate spec for the selected no-order research hypothesis; do not train, reload, paper trade, live trade, or mutate branch state."
            if selected
            else "Do not create a new branch yet; failed branch lessons did not produce a sufficient research candidate."
        ),
    }


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str]) -> tuple[Path, Path]:
    stamp = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")
    target_dir = Path(out_dir)
    json_path = target_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = target_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(json_path, payload)
    write_markdown(md_path, payload)
    return json_path, md_path
