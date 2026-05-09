from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

RESEARCH_BACKLOG_HYP003_ADVANCEMENT_CONTRACT_VERSION = "4B.4.3.6.6.25N"
REPORT_PREFIX = "4B436625N_research_backlog_after_hyp003_closure"
SNAPSHOT_PREFIX = "4B436625N_proposed_research_registry_snapshot"

CLOSED_STATUSES = {"CLOSED_NO_GO", "RESEARCH_STOP_NO_GO", "BLOCK", "CLOSED"}
SELECTABLE_STATUSES = {"REGISTERED", "READY", "PENDING", "SELECTABLE", "NOT_STARTED"}


@dataclass(frozen=True)
class HypothesisAcceptanceCriteria:
    min_samples: int = 1000
    min_signal_count: int = 40
    min_mean_net_edge_bps: float = 0.0
    min_median_net_edge_bps: float = 0.0
    min_profit_factor: float = 1.20
    min_walk_forward_positive_rate_pct: float = 60.0
    min_oos_mean_net_edge_bps: float = 0.0
    max_top_win_dependency_pct: float = 35.0
    max_dominant_side_pct: float = 80.0
    requires_robustness_gate: bool = True
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
    require_hyp003_closure_confirmed: bool = True
    require_no_training_paper_live_approvals: bool = True
    max_next_candidates_returned: int = 5


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
            rationale="Closed by 25H evidence pack.",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-003",
            title="Regime-specific strategy family",
            branch_name="regime_specific_strategy_family",
            priority=30,
            status="CLOSED_NO_GO",
            rationale="Closed by 25M evidence pack.",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-004",
            title="Cross-symbol relative strength rotation",
            branch_name="cross_symbol_relative_strength_rotation",
            priority=40,
            status="REGISTERED",
            rationale="Test whether capital rotation across BTC/ETH/SOL/BNB creates more stable edge than single-symbol signals.",
            acceptance_criteria=HypothesisAcceptanceCriteria(
                min_samples=1500,
                min_signal_count=50,
                min_profit_factor=1.20,
                min_walk_forward_positive_rate_pct=60.0,
                max_top_win_dependency_pct=32.0,
            ),
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-005",
            title="Liquidity sweep reversal with volatility compression filter",
            branch_name="liquidity_sweep_reversal_vol_compression",
            priority=50,
            status="REGISTERED",
            rationale="Evaluate wick/sweep behaviour only when volatility compression precedes expansion.",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-006",
            title="Session-aware breakout / mean-reversion hybrid",
            branch_name="session_aware_breakout_mean_reversion_hybrid",
            priority=60,
            status="REGISTERED",
            rationale="Segment strategy families by UTC session behaviour instead of global one-size-fits-all logic.",
        ),
    ]


def _safe_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
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


def _criteria_from_mapping(raw: Mapping[str, Any] | None) -> HypothesisAcceptanceCriteria:
    if not isinstance(raw, Mapping):
        return HypothesisAcceptanceCriteria()
    base = asdict(HypothesisAcceptanceCriteria())
    for key in base:
        if key in raw and raw[key] is not None:
            base[key] = raw[key]
    return HypothesisAcceptanceCriteria(**base)


def _hypothesis_from_mapping(raw: Mapping[str, Any], *, source: str = "registry") -> ResearchHypothesisBacklogItem | None:
    hypothesis_id = str(raw.get("hypothesis_id") or raw.get("id") or raw.get("hypothesisId") or "").strip()
    title = str(raw.get("title") or raw.get("name") or "").strip()
    branch_name = str(raw.get("branch_name") or raw.get("branch") or raw.get("slug") or "").strip()
    if not hypothesis_id:
        return None
    if not title:
        title = hypothesis_id
    if not branch_name:
        branch_name = hypothesis_id.lower().replace("-", "_")
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
    if not candidates and any(key.startswith("HYP-") for key in registry):
        candidates = [value for value in registry.values() if isinstance(value, Mapping)]
    parsed = [item for item in (_hypothesis_from_mapping(raw, source="registry") for raw in candidates if isinstance(raw, Mapping)) if item]
    return parsed or default_research_backlog()


def _hypothesis_closed_by_25m(closure_report: Mapping[str, Any], hypothesis_id: str = "HYP-003") -> bool:
    decision = str(closure_report.get("decision") or "").upper()
    report_hypothesis = str(closure_report.get("hypothesis_id") or closure_report.get("closed_hypothesis_id") or "")
    reason_codes = {str(code) for code in _as_list(closure_report.get("reason_codes"))}
    return (
        report_hypothesis == hypothesis_id
        and decision == "HYP003_BRANCH_CLOSURE_CONFIRMED"
        and "HYP003_ROBUSTNESS_BLOCK_CONFIRMED" in reason_codes
        and "NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE_CONFIRMED" in reason_codes
    )


def _no_training_paper_live_approvals(closure_report: Mapping[str, Any]) -> bool:
    approval_keys = [
        "approved_for_training_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "live_real_allowed",
        "reload_performed",
        "order_actions_performed",
        "config_mutation_performed",
    ]
    return not any(_safe_bool(closure_report.get(key)) for key in approval_keys)


def _merge_backlog_with_closure(backlog: Sequence[ResearchHypothesisBacklogItem], *, closed_hypothesis_id: str, closure_report: Mapping[str, Any]) -> list[ResearchHypothesisBacklogItem]:
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
                    rationale="Closed by 4B.4.3.6.6.25M HYP-003 closure evidence pack.",
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
                title="Regime-specific strategy family",
                branch_name=str(closure_report.get("branch_name") or "regime_specific_strategy_family"),
                priority=30,
                status="CLOSED_NO_GO",
                source="closure_25M",
                rationale="Closed by 4B.4.3.6.6.25M HYP-003 closure evidence pack.",
            )
        )
    return sorted(merged, key=lambda item: item.priority)


def _is_selectable(item: ResearchHypothesisBacklogItem) -> bool:
    status = item.status.upper()
    return status in SELECTABLE_STATUSES and status not in CLOSED_STATUSES and not (
        item.approved_for_training_candidate or item.approved_for_paper_candidate or item.approved_for_live_real
    )


def select_next_hypothesis(backlog: Sequence[ResearchHypothesisBacklogItem], *, after_hypothesis_id: str = "HYP-003") -> ResearchHypothesisBacklogItem | None:
    sorted_backlog = sorted(backlog, key=lambda item: item.priority)
    after_priority = next((item.priority for item in sorted_backlog if item.hypothesis_id == after_hypothesis_id), -1)
    forward = [item for item in sorted_backlog if item.priority > after_priority and _is_selectable(item)]
    if forward:
        return forward[0]
    selectable = [item for item in sorted_backlog if _is_selectable(item)]
    return selectable[0] if selectable else None


def build_research_backlog_after_hyp003_closure(
    closure_report: Mapping[str, Any],
    *,
    registry: Mapping[str, Any] | None = None,
    hypothesis_id: str = "HYP-003",
    generated_at: str | None = None,
    limits: BacklogAdvancementLimits | None = None,
) -> dict[str, Any]:
    limits = limits or BacklogAdvancementLimits()
    generated_at = generated_at or utc_now_iso()
    closure_confirmed = _hypothesis_closed_by_25m(closure_report, hypothesis_id)
    approvals_clear = _no_training_paper_live_approvals(closure_report)

    base_backlog = load_backlog_from_registry(registry)
    proposed_backlog = _merge_backlog_with_closure(base_backlog, closed_hypothesis_id=hypothesis_id, closure_report=closure_report)
    next_hypothesis = select_next_hypothesis(proposed_backlog, after_hypothesis_id=hypothesis_id)

    reason_codes: list[str] = []
    if closure_confirmed:
        reason_codes.append("HYP003_CLOSURE_CONFIRMED")
    else:
        reason_codes.append("HYP003_CLOSURE_NOT_CONFIRMED")
    if approvals_clear:
        reason_codes.append("NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED")
    else:
        reason_codes.append("TRAINING_PAPER_LIVE_APPROVAL_DETECTED")
    if next_hypothesis:
        reason_codes.append("NEXT_HYPOTHESIS_AVAILABLE")
    else:
        reason_codes.append("RESEARCH_BACKLOG_EXHAUSTED")

    if closure_confirmed and approvals_clear and next_hypothesis is not None:
        decision = "NEXT_HYPOTHESIS_SELECTED"
        ok = True
        recommendation = (
            f"HYP-003 is closed no-go. Advance research-only to {next_hypothesis.hypothesis_id} "
            f"({next_hypothesis.title}). Do not train, reload, paper trade, or enable live trading."
        )
        approved_for_research_candidate = True
    elif closure_confirmed and approvals_clear:
        decision = "RESEARCH_BACKLOG_EXHAUSTED"
        ok = False
        recommendation = "HYP-003 is closed no-go, but no selectable next hypothesis exists. Register a new hypothesis before further research."
        approved_for_research_candidate = False
    else:
        decision = "BACKLOG_ADVANCEMENT_BLOCKED"
        ok = False
        recommendation = "Backlog advancement blocked. Confirm 25M closure and absence of training/paper/live approvals first."
        approved_for_research_candidate = False

    proposed_registry_snapshot = {
        "contract_version": RESEARCH_BACKLOG_HYP003_ADVANCEMENT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "closed_hypothesis_id": hypothesis_id if closure_confirmed else None,
        "selected_next_hypothesis_id": next_hypothesis.hypothesis_id if next_hypothesis else None,
        "hypotheses": [asdict(item) for item in proposed_backlog],
    }

    return {
        "contract_version": RESEARCH_BACKLOG_HYP003_ADVANCEMENT_CONTRACT_VERSION,
        "phase": "25N",
        "report_type": "research_backlog_advancement_after_hyp003_closure",
        "generated_at": generated_at,
        "decision": decision,
        "ok": ok,
        "closed_hypothesis_id": hypothesis_id if closure_confirmed else None,
        "closed_branch_name": closure_report.get("branch_name") if closure_confirmed else None,
        "selected_next_hypothesis_id": next_hypothesis.hypothesis_id if next_hypothesis else None,
        "selected_next_hypothesis_title": next_hypothesis.title if next_hypothesis else None,
        "selected_next_branch_name": next_hypothesis.branch_name if next_hypothesis else None,
        "selected_next_acceptance_criteria": asdict(next_hypothesis.acceptance_criteria) if next_hypothesis else None,
        "reason_codes": reason_codes,
        "recommendation": recommendation,
        "approved_for_research_candidate": approved_for_research_candidate,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "source_closure_decision": closure_report.get("decision"),
        "source_closure_reason_codes": _as_list(closure_report.get("reason_codes")),
        "registry_snapshot": proposed_registry_snapshot,
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


def render_markdown(report: Mapping[str, Any]) -> str:
    criteria = report.get("selected_next_acceptance_criteria") or {}
    lines = [
        "# 4B.4.3.6.6.25N Research Backlog Advancement After HYP-003 Closure",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- closed_hypothesis_id: `{report.get('closed_hypothesis_id')}`",
        f"- closed_branch_name: `{report.get('closed_branch_name')}`",
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
    if criteria:
        for key, value in criteria.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- No next hypothesis selected.")
    lines.extend([
        "",
        "## Guardrails",
        "",
    ])
    for key, value in dict(report.get("guardrails") or {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Policy",
        "",
        "This gate only advances the research backlog after a confirmed HYP-003 closure. It never fetches market data, trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.",
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
    write_json(snapshot_json, report.get("registry_snapshot") or {})
    return report_json, report_md, snapshot_json


def discover_latest_hyp003_closure_report(reports_dir: str | Path) -> Path | None:
    reports_dir = Path(reports_dir)
    matches = sorted(reports_dir.glob("4B436625M_hyp003_branch_closure_evidence_pack_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None
