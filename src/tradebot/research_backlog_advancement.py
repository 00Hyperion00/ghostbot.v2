from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

RESEARCH_BACKLOG_ADVANCEMENT_CONTRACT_VERSION = "4B.4.3.6.6.25I"
REPORT_PREFIX = "4B436625I_research_backlog_advancement"
DEFAULT_CLOSED_HYPOTHESIS_ID = "HYP-002"
DEFAULT_BRANCH_NAME = "futures_funding_trend_exhaustion"

CLOSED_DECISIONS = {
    "FUTURES_BRANCH_CLOSURE_CONFIRMED",
    "BRANCH_CLOSED_NO_GO",
    "RESEARCH_STOP_NO_GO",
    "BLOCK",
}

FINAL_NO_GO_REASON_CODES = {
    "HYPOTHESIS_BRANCH_CLOSED_NO_GO",
    "FINAL_25F_BRANCH_CLOSED_NO_GO",
    "PRIMARY_TERMINAL_AUDIT_BLOCK_CONFIRMED",
    "COMPANION_TERMINAL_AUDIT_BLOCK_CONFIRMED",
    "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
}

SAFE_STATUSES = {"REGISTERED", "READY", "OPEN", "BACKLOG", "PENDING_RESEARCH", "SELECTABLE"}
BLOCKED_STATUSES = {"CLOSED_NO_GO", "BLOCK", "BLOCKED", "REJECTED", "DONE", "COMPLETED"}


@dataclass(frozen=True)
class ResearchHypothesisBacklogItem:
    hypothesis_id: str
    title: str
    status: str = "REGISTERED"
    family: str = "research"
    priority: int = 999
    description: str = ""
    acceptance_metrics: dict[str, Any] = field(default_factory=dict)
    paper_allowed_if_pass: bool = False
    live_allowed_if_pass: bool = False
    training_allowed_if_pass: bool = False
    source: str = "registry"


@dataclass(frozen=True)
class ClosedHypothesisEvidence:
    hypothesis_id: str
    branch_name: str
    source_report: str
    decision: str
    final_25f_decision: str
    primary_terminal_block_count: int
    companion_terminal_block_count: int
    reason_codes: tuple[str, ...]
    approvals_detected: bool


@dataclass(frozen=True)
class ResearchBacklogAdvancementLimits:
    require_final_closure: bool = True
    require_no_training_paper_live_approvals: bool = True
    require_next_hypothesis_acceptance_metrics: bool = True
    max_active_research_hypotheses: int = 1


@dataclass(frozen=True)
class ResearchBacklogAdvancementReport:
    contract_version: str
    phase: str
    report_type: str
    decision: str
    ok: bool
    source_reports: int
    registry_source: str
    closed_hypothesis_id: str
    closed_branch_name: str
    selected_next_hypothesis_id: str | None
    selected_next_hypothesis_title: str | None
    approved_for_research_candidate: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    live_real_allowed: bool
    reload_performed: bool
    config_mutation_performed: bool
    order_actions_performed: bool
    post_requests_allowed: bool
    observation_only: bool
    no_post_actions: bool
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    recommendation: str
    closure_evidence: ClosedHypothesisEvidence | None
    next_hypothesis: ResearchHypothesisBacklogItem | None
    backlog: tuple[ResearchHypothesisBacklogItem, ...]
    proposed_registry_snapshot: dict[str, Any]
    guardrails: Mapping[str, bool]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _as_tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    return (str(value),)


def load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def default_backlog() -> list[ResearchHypothesisBacklogItem]:
    return [
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-001",
            title="Higher timeframe trend following",
            status="BLOCKED",
            family="spot_or_futures_trend",
            priority=10,
            description="Previously explored higher-timeframe trend-following hypothesis; not selected after failed edge checks.",
            acceptance_metrics={"status": "historical_block"},
            source="builtin_default",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-002",
            title="Futures funding/open-interest trend exhaustion",
            status="CLOSED_NO_GO",
            family="futures_funding",
            priority=20,
            description="Closed by 25H evidence pack after BTC primary and ETH companion terminal audits failed.",
            acceptance_metrics={"required_decision": "FUTURES_BRANCH_CLOSURE_CONFIRMED"},
            source="builtin_default",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-003",
            title="Regime-filtered volatility expansion breakout",
            status="REGISTERED",
            family="volatility_breakout",
            priority=30,
            description="Test whether volatility expansion plus regime filter creates positive OOS edge before any ML work.",
            acceptance_metrics={
                "min_sample_count": 250,
                "min_signal_count": 35,
                "min_mean_net_edge_bps": 0.0,
                "min_median_net_edge_bps": 0.0,
                "min_profit_factor": 1.20,
                "min_walk_forward_positive_rate_pct": 60.0,
                "max_top_win_dependency_pct": 35.0,
                "max_drawdown_pct": 25.0,
            },
            source="builtin_default",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-004",
            title="Session-aware VWAP reversion with volatility guard",
            status="REGISTERED",
            family="vwap_reversion",
            priority=40,
            description="Test whether session/VWAP distance with volatility guard can create robust reversion edge.",
            acceptance_metrics={
                "min_signal_count": 40,
                "min_mean_net_edge_bps": 0.0,
                "min_median_net_edge_bps": 0.0,
                "min_profit_factor": 1.18,
                "min_oos_edge_bps": 0.0,
                "max_side_imbalance_pct": 75.0,
            },
            source="builtin_default",
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-005",
            title="Cross-symbol liquidity rotation edge",
            status="REGISTERED",
            family="cross_symbol_relative_strength",
            priority=50,
            description="Test whether liquidity rotation between BTC/ETH/SOL/BNB predicts short-horizon relative edge.",
            acceptance_metrics={
                "min_symbols": 4,
                "min_signal_count": 50,
                "min_mean_net_edge_bps": 0.0,
                "min_median_net_edge_bps": 0.0,
                "min_profit_factor": 1.15,
                "min_walk_forward_positive_rate_pct": 60.0,
            },
            source="builtin_default",
        ),
    ]


def _normalise_hypothesis(raw: Mapping[str, Any], *, source: str) -> ResearchHypothesisBacklogItem | None:
    hypothesis_id = str(raw.get("hypothesis_id") or raw.get("id") or raw.get("hypothesisId") or "").strip()
    if not hypothesis_id:
        return None
    title = str(raw.get("title") or raw.get("name") or raw.get("hypothesis") or hypothesis_id)
    acceptance_metrics = raw.get("acceptance_metrics") or raw.get("metrics") or raw.get("acceptance") or {}
    if not isinstance(acceptance_metrics, dict):
        acceptance_metrics = {}
    return ResearchHypothesisBacklogItem(
        hypothesis_id=hypothesis_id,
        title=title,
        status=str(raw.get("status") or raw.get("state") or "REGISTERED").upper(),
        family=str(raw.get("family") or raw.get("category") or "research"),
        priority=_safe_int(raw.get("priority"), 999),
        description=str(raw.get("description") or raw.get("summary") or ""),
        acceptance_metrics=acceptance_metrics,
        paper_allowed_if_pass=_as_bool(raw.get("paper_allowed_if_pass", False)),
        live_allowed_if_pass=_as_bool(raw.get("live_allowed_if_pass", False)),
        training_allowed_if_pass=_as_bool(raw.get("training_allowed_if_pass", False)),
        source=source,
    )


def load_backlog_from_registry(path: str | Path | None) -> tuple[list[ResearchHypothesisBacklogItem], str]:
    if path is None:
        return default_backlog(), "builtin_default"
    registry_path = Path(path)
    if not registry_path.exists():
        return default_backlog(), f"missing:{registry_path}:builtin_default"
    data = load_json(registry_path)
    raw_items: Any = data.get("hypotheses") or data.get("items") or data.get("backlog") or []
    if isinstance(raw_items, Mapping):
        raw_items = list(raw_items.values())
    items: list[ResearchHypothesisBacklogItem] = []
    if isinstance(raw_items, Sequence) and not isinstance(raw_items, (str, bytes)):
        for raw in raw_items:
            if isinstance(raw, Mapping):
                item = _normalise_hypothesis(raw, source=str(registry_path))
                if item is not None:
                    items.append(item)
    if not items:
        return default_backlog(), f"empty:{registry_path}:builtin_default"
    return items, str(registry_path)


def discover_reports(reports_dir: str | Path, *, include_all: bool = False) -> list[Path]:
    reports_dir = Path(reports_dir)
    if not reports_dir.exists():
        return []
    patterns = [
        "4B436625H_futures_branch_closure_evidence_pack_*.json",
        "4B436625F_futures_hypothesis_branch_review_*.json",
        "4B436625G_futures_companion_candidate_audit_runner_*.json",
        "4B436625D_futures_research_candidate_simulator_*.json",
        "4B436625E_futures_candidate_refinement_median_edge_recovery_*.json",
    ]
    found: list[Path] = []
    for pattern in patterns:
        matches = sorted(reports_dir.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
        found.extend(matches if include_all else matches[:1])
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in found:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def extract_closure_evidence(
    reports: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    hypothesis_id: str = DEFAULT_CLOSED_HYPOTHESIS_ID,
    branch_name: str = DEFAULT_BRANCH_NAME,
) -> ClosedHypothesisEvidence | None:
    candidates: list[ClosedHypothesisEvidence] = []
    for source_report, report in reports:
        report_hypothesis_id = str(report.get("hypothesis_id") or report.get("closed_hypothesis_id") or hypothesis_id)
        report_branch = str(report.get("branch_name") or report.get("closed_branch_name") or branch_name)
        if report_hypothesis_id != hypothesis_id:
            continue
        decision = str(report.get("decision") or "")
        final_25f_decision = str(report.get("final_25f_decision") or report.get("final_decision") or "")
        reason_codes = _as_tuple_str(report.get("reason_codes"))
        primary_count = _safe_int(report.get("primary_terminal_block_count"), 0)
        companion_count = _safe_int(report.get("companion_terminal_block_count"), 0)
        approvals_detected = any(
            _as_bool(report.get(key))
            for key in (
                "approved_for_training_candidate",
                "approved_for_paper_candidate",
                "approved_for_live_real",
                "live_real_allowed",
                "reload_performed",
                "order_actions_performed",
                "config_mutation_performed",
            )
        )
        looks_like_closure_pack = (
            decision == "FUTURES_BRANCH_CLOSURE_CONFIRMED"
            or final_25f_decision == "BRANCH_CLOSED_NO_GO"
            or bool(set(reason_codes).intersection(FINAL_NO_GO_REASON_CODES))
        )
        if not looks_like_closure_pack:
            continue
        candidates.append(
            ClosedHypothesisEvidence(
                hypothesis_id=report_hypothesis_id,
                branch_name=report_branch,
                source_report=source_report,
                decision=decision,
                final_25f_decision=final_25f_decision,
                primary_terminal_block_count=primary_count,
                companion_terminal_block_count=companion_count,
                reason_codes=reason_codes,
                approvals_detected=approvals_detected,
            )
        )
    if not candidates:
        return None
    candidates.sort(key=lambda item: (
        item.decision == "FUTURES_BRANCH_CLOSURE_CONFIRMED",
        item.final_25f_decision == "BRANCH_CLOSED_NO_GO",
        item.primary_terminal_block_count + item.companion_terminal_block_count,
    ), reverse=True)
    return candidates[0]


def _item_with_status(item: ResearchHypothesisBacklogItem, status: str) -> ResearchHypothesisBacklogItem:
    return ResearchHypothesisBacklogItem(
        hypothesis_id=item.hypothesis_id,
        title=item.title,
        status=status,
        family=item.family,
        priority=item.priority,
        description=item.description,
        acceptance_metrics=item.acceptance_metrics,
        paper_allowed_if_pass=item.paper_allowed_if_pass,
        live_allowed_if_pass=item.live_allowed_if_pass,
        training_allowed_if_pass=item.training_allowed_if_pass,
        source=item.source,
    )


def advance_backlog_statuses(
    backlog: Sequence[ResearchHypothesisBacklogItem],
    *,
    closed_hypothesis_id: str,
) -> tuple[ResearchHypothesisBacklogItem, ...]:
    updated: list[ResearchHypothesisBacklogItem] = []
    seen_closed = False
    for item in backlog:
        if item.hypothesis_id == closed_hypothesis_id:
            updated.append(_item_with_status(item, "CLOSED_NO_GO"))
            seen_closed = True
        else:
            updated.append(item)
    if not seen_closed:
        updated.append(
            ResearchHypothesisBacklogItem(
                hypothesis_id=closed_hypothesis_id,
                title="Futures funding/open-interest trend exhaustion",
                status="CLOSED_NO_GO",
                family="futures_funding",
                priority=20,
                description="Inserted by 25I from closure evidence pack.",
                acceptance_metrics={"closure_source": "25H"},
                source="25I_inserted_closure",
            )
        )
    return tuple(sorted(updated, key=lambda item: (item.priority, item.hypothesis_id)))


def select_next_hypothesis(
    backlog: Sequence[ResearchHypothesisBacklogItem],
    *,
    closed_hypothesis_id: str,
) -> ResearchHypothesisBacklogItem | None:
    eligible: list[ResearchHypothesisBacklogItem] = []
    for item in backlog:
        status = item.status.upper()
        if item.hypothesis_id == closed_hypothesis_id:
            continue
        if status in BLOCKED_STATUSES or status.startswith("CLOSED"):
            continue
        if status not in SAFE_STATUSES:
            continue
        if item.paper_allowed_if_pass or item.live_allowed_if_pass or item.training_allowed_if_pass:
            continue
        eligible.append(item)
    if not eligible:
        return None
    eligible.sort(key=lambda item: (item.priority, item.hypothesis_id))
    return eligible[0]


def build_proposed_registry_snapshot(
    backlog: Sequence[ResearchHypothesisBacklogItem],
    *,
    next_hypothesis: ResearchHypothesisBacklogItem | None,
    closed_evidence: ClosedHypothesisEvidence | None,
) -> dict[str, Any]:
    return {
        "contract_version": RESEARCH_BACKLOG_ADVANCEMENT_CONTRACT_VERSION,
        "generated_at": utc_now_iso(),
        "selected_next_hypothesis_id": next_hypothesis.hypothesis_id if next_hypothesis else None,
        "closed_hypothesis_id": closed_evidence.hypothesis_id if closed_evidence else None,
        "closed_branch_name": closed_evidence.branch_name if closed_evidence else None,
        "policy": {
            "training_allowed": False,
            "paper_allowed": False,
            "live_allowed": False,
            "reload_allowed": False,
            "orders_allowed": False,
            "new_hypothesis_requires_future_acceptance_gate": True,
        },
        "hypotheses": [asdict(item) for item in backlog],
    }


def build_research_backlog_advancement_gate(
    reports: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    backlog: Sequence[ResearchHypothesisBacklogItem] | None = None,
    registry_source: str = "builtin_default",
    hypothesis_id: str = DEFAULT_CLOSED_HYPOTHESIS_ID,
    branch_name: str = DEFAULT_BRANCH_NAME,
    limits: ResearchBacklogAdvancementLimits | None = None,
) -> ResearchBacklogAdvancementReport:
    limits = limits or ResearchBacklogAdvancementLimits()
    backlog = tuple(backlog or default_backlog())
    closure = extract_closure_evidence(reports, hypothesis_id=hypothesis_id, branch_name=branch_name)
    reason_codes: list[str] = []
    warnings: list[str] = []

    if closure is None:
        reason_codes.append("CLOSURE_EVIDENCE_PACK_MISSING")
    else:
        reason_codes.append("HYPOTHESIS_CLOSURE_EVIDENCE_CONFIRMED")
        if closure.decision != "FUTURES_BRANCH_CLOSURE_CONFIRMED":
            reason_codes.append("CLOSURE_DECISION_NOT_CONFIRMED")
        if closure.final_25f_decision != "BRANCH_CLOSED_NO_GO":
            reason_codes.append("FINAL_25F_CLOSED_NO_GO_MISSING")
        if closure.approvals_detected:
            reason_codes.append("TRAINING_PAPER_LIVE_APPROVAL_DETECTED")

    updated_backlog = advance_backlog_statuses(backlog, closed_hypothesis_id=hypothesis_id)
    next_hypothesis = select_next_hypothesis(updated_backlog, closed_hypothesis_id=hypothesis_id)

    if next_hypothesis is None:
        reason_codes.append("NO_SELECTABLE_NEXT_HYPOTHESIS")
    else:
        reason_codes.append("NEXT_HYPOTHESIS_SELECTED")
        if limits.require_next_hypothesis_acceptance_metrics and not next_hypothesis.acceptance_metrics:
            reason_codes.append("NEXT_HYPOTHESIS_ACCEPTANCE_METRICS_MISSING")
        if next_hypothesis.paper_allowed_if_pass or next_hypothesis.live_allowed_if_pass or next_hypothesis.training_allowed_if_pass:
            reason_codes.append("NEXT_HYPOTHESIS_UNSAFE_APPROVAL_FLAGS")

    active_research_count = sum(1 for item in updated_backlog if item.status.upper() == "ACTIVE_RESEARCH")
    if active_research_count > limits.max_active_research_hypotheses:
        reason_codes.append("TOO_MANY_ACTIVE_RESEARCH_HYPOTHESES")

    unsafe_codes = {
        "CLOSURE_EVIDENCE_PACK_MISSING",
        "CLOSURE_DECISION_NOT_CONFIRMED",
        "FINAL_25F_CLOSED_NO_GO_MISSING",
        "TRAINING_PAPER_LIVE_APPROVAL_DETECTED",
        "NO_SELECTABLE_NEXT_HYPOTHESIS",
        "NEXT_HYPOTHESIS_ACCEPTANCE_METRICS_MISSING",
        "NEXT_HYPOTHESIS_UNSAFE_APPROVAL_FLAGS",
        "TOO_MANY_ACTIVE_RESEARCH_HYPOTHESES",
    }
    blocking = sorted(set(reason_codes).intersection(unsafe_codes))
    decision = "NEXT_HYPOTHESIS_SELECTED" if not blocking else "BACKLOG_ADVANCEMENT_BLOCK"
    ok = decision == "NEXT_HYPOTHESIS_SELECTED"
    approved_for_research_candidate = ok
    recommendation = (
        f"Advance to {next_hypothesis.hypothesis_id} as research-only. Do not train, reload, start paper trading, or enable live trading; run its dedicated exploration gate first."
        if ok and next_hypothesis
        else "Do not advance backlog. Resolve closure evidence or registry safety issues before selecting a new research hypothesis."
    )
    snapshot = build_proposed_registry_snapshot(updated_backlog, next_hypothesis=next_hypothesis, closed_evidence=closure)
    return ResearchBacklogAdvancementReport(
        contract_version=RESEARCH_BACKLOG_ADVANCEMENT_CONTRACT_VERSION,
        phase=RESEARCH_BACKLOG_ADVANCEMENT_CONTRACT_VERSION,
        report_type="research_backlog_advancement_next_hypothesis_selection_gate",
        decision=decision,
        ok=ok,
        source_reports=len(reports),
        registry_source=registry_source,
        closed_hypothesis_id=hypothesis_id,
        closed_branch_name=branch_name,
        selected_next_hypothesis_id=next_hypothesis.hypothesis_id if next_hypothesis else None,
        selected_next_hypothesis_title=next_hypothesis.title if next_hypothesis else None,
        approved_for_research_candidate=approved_for_research_candidate,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        live_real_allowed=False,
        reload_performed=False,
        config_mutation_performed=False,
        order_actions_performed=False,
        post_requests_allowed=False,
        observation_only=True,
        no_post_actions=True,
        reason_codes=tuple(sorted(set(reason_codes))),
        warnings=tuple(sorted(set(warnings))),
        recommendation=recommendation,
        closure_evidence=closure,
        next_hypothesis=next_hypothesis,
        backlog=tuple(updated_backlog),
        proposed_registry_snapshot=snapshot,
        guardrails={
            "observation_only": True,
            "no_post_actions": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "training_allowed": False,
            "paper_allowed": False,
            "live_real_allowed": False,
            "new_hypothesis_requires_future_acceptance_gate": True,
        },
    )


def report_to_dict(report: ResearchBacklogAdvancementReport) -> dict[str, Any]:
    return asdict(report)


def render_markdown(report: ResearchBacklogAdvancementReport) -> str:
    lines = [
        "# 4B.4.3.6.6.25I Research Backlog Advancement / Next Hypothesis Selection Gate",
        "",
        f"- contract_version: `{report.contract_version}`",
        f"- decision: **{report.decision}**",
        f"- source_reports: `{report.source_reports}`",
        f"- registry_source: `{report.registry_source}`",
        f"- closed_hypothesis_id: `{report.closed_hypothesis_id}`",
        f"- closed_branch_name: `{report.closed_branch_name}`",
        f"- selected_next_hypothesis_id: `{report.selected_next_hypothesis_id}`",
        f"- selected_next_hypothesis_title: `{report.selected_next_hypothesis_title}`",
        f"- approved_for_research_candidate: `{report.approved_for_research_candidate}`",
        f"- approved_for_training_candidate: `{report.approved_for_training_candidate}`",
        f"- approved_for_paper_candidate: `{report.approved_for_paper_candidate}`",
        f"- approved_for_live_real: `{report.approved_for_live_real}`",
        f"- reason_codes: `{list(report.reason_codes)}`",
        f"- recommendation: {report.recommendation}",
        "",
        "## Closure Evidence",
        "",
    ]
    if report.closure_evidence:
        closure = report.closure_evidence
        lines.extend([
            f"- source_report: `{closure.source_report}`",
            f"- decision: `{closure.decision}`",
            f"- final_25f_decision: `{closure.final_25f_decision}`",
            f"- primary_terminal_block_count: `{closure.primary_terminal_block_count}`",
            f"- companion_terminal_block_count: `{closure.companion_terminal_block_count}`",
            f"- approvals_detected: `{closure.approvals_detected}`",
        ])
    else:
        lines.append("- closure evidence: `MISSING`")
    lines.extend(["", "## Next Hypothesis", ""])
    if report.next_hypothesis:
        item = report.next_hypothesis
        lines.extend([
            f"- hypothesis_id: `{item.hypothesis_id}`",
            f"- title: `{item.title}`",
            f"- family: `{item.family}`",
            f"- priority: `{item.priority}`",
            f"- status: `{item.status}`",
            f"- training_allowed_if_pass: `{item.training_allowed_if_pass}`",
            f"- paper_allowed_if_pass: `{item.paper_allowed_if_pass}`",
            f"- live_allowed_if_pass: `{item.live_allowed_if_pass}`",
            f"- acceptance_metrics: `{item.acceptance_metrics}`",
        ])
    else:
        lines.append("- next hypothesis: `NONE`")
    lines.extend([
        "",
        "## Backlog Snapshot",
        "",
        "| hypothesis_id | status | priority | family | title |",
        "|---|---|---:|---|---|",
    ])
    for item in report.backlog:
        lines.append(f"| {item.hypothesis_id} | {item.status} | {item.priority} | {item.family} | {item.title} |")
    lines.extend([
        "",
        "## Guardrails",
        "",
    ])
    for key, value in report.guardrails.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Policy",
        "",
        "This gate only advances the research backlog. It never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders. A selected next hypothesis must still pass a future dedicated exploration gate.",
    ])
    return "\n".join(lines) + "\n"


def write_report_bundle(report: ResearchBacklogAdvancementReport, out_dir: str | Path, *, timestamp: str | None = None) -> tuple[Path, Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    report_json = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    registry_json = out_dir / f"4B436625I_proposed_research_registry_snapshot_{stamp}.json"
    write_json(report_json, report_to_dict(report))
    report_md.write_text(render_markdown(report), encoding="utf-8")
    write_json(registry_json, report.proposed_registry_snapshot)
    return report_json, report_md, registry_json
