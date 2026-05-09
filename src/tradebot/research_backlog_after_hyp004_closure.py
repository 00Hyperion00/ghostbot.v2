from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

RESEARCH_BACKLOG_HYP004_ADVANCEMENT_CONTRACT_VERSION = "4B.4.3.6.6.25R"
REPORT_PREFIX = "4B436625R_research_backlog_after_hyp004_closure"
SNAPSHOT_PREFIX = "4B436625R_proposed_research_registry_snapshot"

CLOSED_STATUSES = {"CLOSED_NO_GO", "RESEARCH_STOP_NO_GO", "BLOCK", "CLOSED"}
SELECTABLE_STATUSES = {"REGISTERED", "READY", "PENDING", "SELECTABLE", "NOT_STARTED"}
TRAINING_PAPER_LIVE_KEYS = (
    "approved_for_training_candidate",
    "approved_for_paper_candidate",
    "approved_for_live_real",
    "live_real_allowed",
    "reload_performed",
    "config_mutation_performed",
    "order_actions_performed",
    "post_requests_allowed",
)


@dataclass(frozen=True)
class HypothesisAcceptanceCriteria:
    min_samples: int = 1500
    min_signal_count: int = 50
    min_mean_net_edge_bps: float = 0.0
    min_median_net_edge_bps: float = 0.0
    min_profit_factor: float = 1.20
    min_walk_forward_positive_rate_pct: float = 60.0
    min_oos_mean_net_edge_bps: float = 0.0
    max_top_win_dependency_pct: float = 32.0
    max_dominant_symbol_pct: float = 72.0
    requires_robustness_gate: bool = True
    requires_refinement_gate: bool = True
    requires_closure_if_blocked: bool = True


@dataclass(frozen=True)
class ResearchHypothesisBacklogItem:
    hypothesis_id: str
    title: str
    branch_name: str
    priority: int
    status: str = "REGISTERED"
    source: str = "builtin"
    rationale: str = ""
    acceptance_criteria: HypothesisAcceptanceCriteria = field(default_factory=HypothesisAcceptanceCriteria)
    approved_for_research_candidate: bool = False
    approved_for_training_candidate: bool = False
    approved_for_paper_candidate: bool = False
    approved_for_live_real: bool = False


@dataclass(frozen=True)
class BacklogAdvancementLimits:
    require_hyp004_closure_confirmed: bool = True
    require_no_training_paper_live_approvals: bool = True
    max_next_candidates_returned: int = 5


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value) if value is not None else False


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]


def load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def default_research_backlog() -> list[ResearchHypothesisBacklogItem]:
    return [
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-001",
            title="Higher timeframe trend following",
            branch_name="higher_timeframe_trend_following",
            priority=10,
            status="CLOSED_NO_GO",
            rationale="Previously explored and blocked before HYP-002.",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-002",
            title="Futures funding / open-interest exhaustion",
            branch_name="futures_funding_trend_exhaustion",
            priority=20,
            status="CLOSED_NO_GO",
            rationale="Closed by 25H futures branch closure evidence pack.",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-003",
            title="Regime-specific strategy family",
            branch_name="regime_specific_strategy_family",
            priority=30,
            status="CLOSED_NO_GO",
            rationale="Closed by 25M HYP-003 closure evidence pack.",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-004",
            title="Cross-symbol relative strength rotation",
            branch_name="cross_symbol_relative_strength_rotation",
            priority=40,
            status="CLOSED_NO_GO",
            rationale="Closed by 25Q HYP-004 closure evidence pack.",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-005",
            title="Liquidity sweep reversal with volatility compression filter",
            branch_name="liquidity_sweep_reversal_vol_compression",
            priority=50,
            status="REGISTERED",
            rationale="Evaluate wick/sweep reversals only when volatility compression precedes expansion.",
            acceptance_criteria=HypothesisAcceptanceCriteria(
                min_samples=1500,
                min_signal_count=45,
                min_profit_factor=1.22,
                min_walk_forward_positive_rate_pct=62.0,
                max_top_win_dependency_pct=30.0,
                max_dominant_symbol_pct=70.0,
            ),
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-006",
            title="Session-aware breakout / mean-reversion hybrid",
            branch_name="session_aware_breakout_mean_reversion_hybrid",
            priority=60,
            status="REGISTERED",
            rationale="Segment strategy families by UTC session behaviour instead of global one-size-fits-all logic.",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-007",
            title="Volatility-of-volatility squeeze expansion",
            branch_name="vol_of_vol_squeeze_expansion",
            priority=70,
            status="REGISTERED",
            rationale="Test whether second-order volatility compression predicts post-squeeze directional expansion.",
        ),
    ]


def _criteria_from_mapping(raw: Mapping[str, Any] | None) -> HypothesisAcceptanceCriteria:
    base = asdict(HypothesisAcceptanceCriteria())
    if isinstance(raw, Mapping):
        for key in base:
            if key in raw and raw[key] is not None:
                base[key] = raw[key]
    return HypothesisAcceptanceCriteria(**base)


def _hypothesis_from_mapping(raw: Mapping[str, Any], *, source: str = "registry") -> ResearchHypothesisBacklogItem | None:
    hypothesis_id = str(raw.get("hypothesis_id") or raw.get("id") or raw.get("hypothesisId") or "").strip()
    if not hypothesis_id:
        return None
    title = str(raw.get("title") or raw.get("name") or hypothesis_id).strip()
    branch_name = str(raw.get("branch_name") or raw.get("branch") or raw.get("slug") or hypothesis_id.lower().replace("-", "_")).strip()
    return ResearchHypothesisBacklogItem(
        hypothesis_id=hypothesis_id,
        title=title,
        branch_name=branch_name,
        priority=int(raw.get("priority") or raw.get("rank") or 999),
        status=str(raw.get("status") or raw.get("state") or "REGISTERED"),
        source=source,
        rationale=str(raw.get("rationale") or raw.get("description") or ""),
        acceptance_criteria=_criteria_from_mapping(raw.get("acceptance_criteria") if isinstance(raw.get("acceptance_criteria"), Mapping) else raw.get("acceptance")),
        approved_for_research_candidate=_safe_bool(raw.get("approved_for_research_candidate")),
        approved_for_training_candidate=_safe_bool(raw.get("approved_for_training_candidate")),
        approved_for_paper_candidate=_safe_bool(raw.get("approved_for_paper_candidate")),
        approved_for_live_real=_safe_bool(raw.get("approved_for_live_real")),
    )


def load_backlog_from_registry(registry: Mapping[str, Any] | None) -> list[ResearchHypothesisBacklogItem]:
    if not registry:
        return default_research_backlog()
    candidates: list[Any] = []
    for key in ("hypotheses", "backlog", "registry", "items"):
        if isinstance(registry.get(key), list):
            candidates = list(registry[key])
            break
    if not candidates and any(str(key).startswith("HYP-") for key in registry):
        candidates = [value for value in registry.values() if isinstance(value, Mapping)]
    parsed = [item for item in (_hypothesis_from_mapping(raw, source="registry") for raw in candidates if isinstance(raw, Mapping)) if item]
    return parsed or default_research_backlog()


def _hypothesis_closed_by_25q(closure_report: Mapping[str, Any], hypothesis_id: str = "HYP-004") -> bool:
    decision = str(closure_report.get("decision") or "").upper()
    report_hypothesis = str(closure_report.get("hypothesis_id") or closure_report.get("closed_hypothesis_id") or "")
    reason_codes = {str(code) for code in _as_list(closure_report.get("reason_codes"))}
    return (
        report_hypothesis == hypothesis_id
        and decision == "HYP004_BRANCH_CLOSURE_CONFIRMED"
        and "HYP004_BRANCH_CLOSED_NO_GO" in reason_codes
        and "HYP004_EXPLORATION_BLOCK_CONFIRMED" in reason_codes
        and "HYP004_REFINEMENT_BLOCK_CONFIRMED" in reason_codes
    )


def _no_training_paper_live_approvals(closure_report: Mapping[str, Any]) -> bool:
    return not any(_safe_bool(closure_report.get(key)) for key in TRAINING_PAPER_LIVE_KEYS)


def _merge_backlog_with_closure(
    backlog: Sequence[ResearchHypothesisBacklogItem],
    *,
    closed_hypothesis_id: str,
    closure_report: Mapping[str, Any],
) -> list[ResearchHypothesisBacklogItem]:
    found = False
    merged: list[ResearchHypothesisBacklogItem] = []
    for item in backlog:
        if item.hypothesis_id == closed_hypothesis_id:
            found = True
            merged.append(
                ResearchHypothesisBacklogItem(
                    hypothesis_id=item.hypothesis_id,
                    title=item.title,
                    branch_name=str(closure_report.get("branch_name") or item.branch_name),
                    priority=item.priority,
                    status="CLOSED_NO_GO",
                    source=item.source,
                    rationale="Closed by 4B.4.3.6.6.25Q HYP-004 closure evidence pack.",
                    acceptance_criteria=item.acceptance_criteria,
                    approved_for_research_candidate=False,
                    approved_for_training_candidate=False,
                    approved_for_paper_candidate=False,
                    approved_for_live_real=False,
                )
            )
        else:
            merged.append(item)
    if not found:
        merged.append(
            ResearchHypothesisBacklogItem(
                hypothesis_id=closed_hypothesis_id,
                title="Cross-symbol relative strength rotation",
                branch_name=str(closure_report.get("branch_name") or "cross_symbol_relative_strength_rotation"),
                priority=40,
                status="CLOSED_NO_GO",
                source="closure_report",
                rationale="Closed by 4B.4.3.6.6.25Q HYP-004 closure evidence pack.",
            )
        )
    return sorted(merged, key=lambda item: (item.priority, item.hypothesis_id))


def _select_next_hypothesis(backlog: Sequence[ResearchHypothesisBacklogItem], *, after_hypothesis_id: str = "HYP-004") -> ResearchHypothesisBacklogItem | None:
    closed_priority = None
    for item in backlog:
        if item.hypothesis_id == after_hypothesis_id:
            closed_priority = item.priority
            break
    selectable = [
        item
        for item in backlog
        if item.status.upper() in SELECTABLE_STATUSES
        and not item.approved_for_training_candidate
        and not item.approved_for_paper_candidate
        and not item.approved_for_live_real
        and (closed_priority is None or item.priority > closed_priority)
    ]
    selectable.sort(key=lambda item: (item.priority, item.hypothesis_id))
    return selectable[0] if selectable else None


def _snapshot_items(backlog: Sequence[ResearchHypothesisBacklogItem], selected: ResearchHypothesisBacklogItem | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in backlog:
        row = asdict(item)
        row["selected_next"] = bool(selected and item.hypothesis_id == selected.hypothesis_id)
        if selected and item.hypothesis_id == selected.hypothesis_id:
            row["status"] = "SELECTED_RESEARCH_ONLY"
            row["approved_for_research_candidate"] = True
            row["approved_for_training_candidate"] = False
            row["approved_for_paper_candidate"] = False
            row["approved_for_live_real"] = False
        rows.append(row)
    return rows


def build_research_backlog_after_hyp004_closure(
    closure_report: Mapping[str, Any],
    *,
    registry: Mapping[str, Any] | None = None,
    hypothesis_id: str = "HYP-004",
    generated_at: str | None = None,
    limits: BacklogAdvancementLimits | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or utc_now_iso()
    limits = limits or BacklogAdvancementLimits()
    reason_codes: list[str] = []

    closure_confirmed = _hypothesis_closed_by_25q(closure_report, hypothesis_id)
    no_approvals = _no_training_paper_live_approvals(closure_report)

    if closure_confirmed:
        reason_codes.append("HYP004_CLOSURE_CONFIRMED")
    else:
        reason_codes.append("HYP004_CLOSURE_NOT_CONFIRMED")
    if no_approvals:
        reason_codes.append("NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED")
    else:
        reason_codes.append("TRAINING_PAPER_OR_LIVE_APPROVAL_DETECTED")

    backlog = _merge_backlog_with_closure(load_backlog_from_registry(registry), closed_hypothesis_id=hypothesis_id, closure_report=closure_report)
    selected = _select_next_hypothesis(backlog, after_hypothesis_id=hypothesis_id) if closure_confirmed and no_approvals else None
    if selected:
        reason_codes.append("NEXT_HYPOTHESIS_AVAILABLE")
        decision = "NEXT_HYPOTHESIS_SELECTED"
        ok = True
        recommendation = (
            f"HYP-004 is closed no-go. Advance research-only to {selected.hypothesis_id} "
            f"({selected.title}). Do not train, reload, paper trade, or enable live trading."
        )
    else:
        if closure_confirmed and no_approvals:
            reason_codes.append("NO_NEXT_HYPOTHESIS_AVAILABLE")
        decision = "BACKLOG_ADVANCEMENT_BLOCK"
        ok = False
        recommendation = "Do not advance research. Confirm HYP-004 closure/no-approval evidence or register a valid next hypothesis."

    snapshot = {
        "contract_version": RESEARCH_BACKLOG_HYP004_ADVANCEMENT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "registry_update_type": "research_backlog_advancement_after_hyp004_closure",
        "closed_hypothesis_id": hypothesis_id,
        "closed_branch_name": str(closure_report.get("branch_name") or "cross_symbol_relative_strength_rotation"),
        "selected_next_hypothesis_id": selected.hypothesis_id if selected else None,
        "hypotheses": _snapshot_items(backlog, selected),
        "guardrails": {
            "training_allowed": False,
            "paper_allowed": False,
            "live_real_allowed": False,
            "reload_allowed": False,
            "orders_allowed": False,
        },
    }

    return {
        "contract_version": RESEARCH_BACKLOG_HYP004_ADVANCEMENT_CONTRACT_VERSION,
        "phase": "25R",
        "report_type": "research_backlog_advancement_after_hyp004_closure",
        "generated_at": generated_at,
        "decision": decision,
        "ok": ok,
        "closed_hypothesis_id": hypothesis_id,
        "closed_branch_name": str(closure_report.get("branch_name") or "cross_symbol_relative_strength_rotation"),
        "closure_decision": str(closure_report.get("decision") or "UNKNOWN"),
        "hyp004_closure_confirmed": closure_confirmed,
        "selected_next_hypothesis_id": selected.hypothesis_id if selected else None,
        "selected_next_hypothesis_title": selected.title if selected else None,
        "selected_next_branch_name": selected.branch_name if selected else None,
        "selected_next_acceptance_criteria": asdict(selected.acceptance_criteria) if selected else None,
        "approved_for_research_candidate": bool(selected),
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
        "observation_only": True,
        "market_data_requests_performed": False,
        "reason_codes": reason_codes,
        "recommendation": recommendation,
        "registry_snapshot": snapshot,
        "guardrails": {
            "observation_only": True,
            "market_data_requests_performed": False,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
            "training_allowed": False,
            "paper_allowed": False,
            "backtest_pass_is_not_paper_permission": True,
            "paper_pass_is_not_live_permission": True,
        },
        "limits": asdict(limits),
    }


def discover_latest_closure_report(reports_dir: str | Path) -> Path | None:
    reports_dir = Path(reports_dir)
    if not reports_dir.exists():
        return None
    matches = sorted(reports_dir.glob("4B436625Q_hyp004_branch_closure_evidence_pack_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def render_markdown(report: Mapping[str, Any]) -> str:
    criteria = report.get("selected_next_acceptance_criteria") or {}
    lines = [
        "# 4B.4.3.6.6.25R Research Backlog Advancement After HYP-004 Closure",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- closed_hypothesis_id: `{report.get('closed_hypothesis_id')}`",
        f"- closed_branch_name: `{report.get('closed_branch_name')}`",
        f"- closure_decision: `{report.get('closure_decision')}`",
        f"- selected_next_hypothesis_id: `{report.get('selected_next_hypothesis_id')}`",
        f"- selected_next_hypothesis_title: `{report.get('selected_next_hypothesis_title')}`",
        f"- selected_next_branch_name: `{report.get('selected_next_branch_name')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Acceptance Criteria for Next Hypothesis",
        "",
    ]
    if isinstance(criteria, Mapping):
        for key, value in criteria.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- observation_only: `True`",
        "- market_data_requests_performed: `False`",
        "- post_requests_allowed: `False`",
        "- config_mutation_performed: `False`",
        "- order_actions_performed: `False`",
        "- reload_performed: `False`",
        "- live_real_allowed: `False`",
        "- Training remains blocked.",
        "- Paper/live remain blocked.",
        "",
        "## Policy",
        "",
        "This gate advances the research backlog only after HYP-004 closure evidence. It never fetches market data, trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.",
    ])
    return "\n".join(lines) + "\n"


def write_report_bundle(report: Mapping[str, Any], *, out_dir: str | Path) -> tuple[Path, Path, Path]:
    out_dir = Path(out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_json = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    snapshot_json = out_dir / f"{SNAPSHOT_PREFIX}_{stamp}.json"
    write_json(report_json, report)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(render_markdown(report), encoding="utf-8")
    write_json(snapshot_json, report.get("registry_snapshot", {}))
    return report_json, report_md, snapshot_json
