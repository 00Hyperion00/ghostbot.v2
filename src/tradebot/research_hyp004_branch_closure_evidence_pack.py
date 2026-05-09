from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json

HYP004_BRANCH_CLOSURE_CONTRACT_VERSION = "4B.4.3.6.6.25Q"
REPORT_PREFIX = "4B436625Q_hyp004_branch_closure_evidence_pack"
REGISTRY_PREFIX = "4B436625Q_hyp004_branch_closure_registry_snapshot"

HYP004_EXPLORATION_BLOCK_DECISIONS = {"HYP004_EXPLORATION_BLOCK", "BLOCK"}
HYP004_REFINEMENT_BLOCK_DECISIONS = {"HYP004_REFINEMENT_BLOCK", "BLOCK"}

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
class Hyp004ClosureLimits:
    require_25o_exploration_block: bool = True
    require_25p_refinement_block: bool = True
    require_no_training_paper_live_approvals: bool = True
    require_no_passed_refinement_candidates: bool = True
    require_no_approvable_exploration_candidates: bool = True


@dataclass(frozen=True)
class Hyp004ClosureEvidence:
    source_report: str
    phase: str
    decision: str
    hypothesis_id: str = "HYP-004"
    report_type: str = ""
    selected_strategy_family: str = "UNKNOWN"
    selected_refinement_name: str = "UNKNOWN"
    candidate_count: int = 0
    passed_candidate_count: int = 0
    signal_count: int = 0
    mean_net_edge_bps: float = 0.0
    median_net_edge_bps: float = 0.0
    profit_factor: float = 0.0
    oos_mean_net_edge_bps: float = 0.0
    approved_for_research_candidate: bool = False
    approved_for_training_candidate: bool = False
    approved_for_paper_candidate: bool = False
    approved_for_live_real: bool = False
    reason_codes: tuple[str, ...] = ()
    recommendation: str = ""


@dataclass(frozen=True)
class Hyp004ClosureReport:
    contract_version: str
    phase: str
    report_type: str
    generated_at: str
    decision: str
    ok: bool
    source_reports: int
    hypothesis_id: str
    branch_name: str
    final_25o_decision: str
    final_25p_decision: str
    selected_25o_family: str
    selected_refinement_name: str
    exploration_candidate_count: int
    exploration_passed_candidate_count: int
    refinement_candidate_count: int
    refinement_passed_candidate_count: int
    no_approvable_exploration_candidate_confirmed: bool
    no_approvable_refinement_candidate_confirmed: bool
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
    reason_codes: tuple[str, ...]
    recommendation: str
    evidence: tuple[Hyp004ClosureEvidence, ...]
    registry_snapshot: Mapping[str, Any]
    guardrails: Mapping[str, bool]
    limits: Hyp004ClosureLimits = field(default_factory=Hyp004ClosureLimits)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    return (str(value),)


def infer_phase(report: Mapping[str, Any], source_report: str = "") -> str:
    text = " ".join(str(item) for item in [report.get("contract_version"), report.get("phase"), report.get("report_type"), source_report] if item).upper()
    if "25O" in text or "436625O" in text or "RELATIVE_STRENGTH_EXPLORATION" in text:
        return "25O"
    if "25P" in text or "436625P" in text or "RELATIVE_STRENGTH_REFINEMENT" in text:
        return "25P"
    return "UNKNOWN"


def normalize_hyp004_evidence(source_report: str, report: Mapping[str, Any]) -> Hyp004ClosureEvidence | None:
    phase = infer_phase(report, source_report)
    if phase not in {"25O", "25P"}:
        return None

    selected_strategy_family = str(report.get("selected_strategy_family") or report.get("selected_25o_family") or report.get("strategy_family") or "UNKNOWN")
    selected_refinement_name = str(report.get("selected_refinement_name") or report.get("refinement_name") or "UNKNOWN")
    selected_signal_count = report.get("selected_signal_count") or report.get("signal_count") or report.get("signals")
    selected_mean = report.get("selected_mean_net_edge_bps") or report.get("mean_net_edge_bps")
    selected_median = report.get("selected_median_net_edge_bps") or report.get("median_net_edge_bps")
    selected_pf = report.get("selected_profit_factor") or report.get("profit_factor")
    selected_oos = report.get("selected_oos_mean_net_edge_bps") or report.get("oos_mean_net_edge_bps")

    return Hyp004ClosureEvidence(
        source_report=source_report,
        phase=phase,
        decision=str(report.get("decision") or "UNKNOWN"),
        hypothesis_id=str(report.get("hypothesis_id") or "HYP-004"),
        report_type=str(report.get("report_type") or ""),
        selected_strategy_family=selected_strategy_family,
        selected_refinement_name=selected_refinement_name,
        candidate_count=_safe_int(report.get("candidate_count"), 0),
        passed_candidate_count=_safe_int(report.get("passed_candidate_count"), 0),
        signal_count=_safe_int(selected_signal_count, 0),
        mean_net_edge_bps=_safe_float(selected_mean, 0.0),
        median_net_edge_bps=_safe_float(selected_median, 0.0),
        profit_factor=_safe_float(selected_pf, 0.0),
        oos_mean_net_edge_bps=_safe_float(selected_oos, 0.0),
        approved_for_research_candidate=_safe_bool(report.get("approved_for_research_candidate", False)),
        approved_for_training_candidate=_safe_bool(report.get("approved_for_training_candidate", False)),
        approved_for_paper_candidate=_safe_bool(report.get("approved_for_paper_candidate", False)),
        approved_for_live_real=_safe_bool(report.get("approved_for_live_real", False)) or _safe_bool(report.get("live_real_allowed", False)),
        reason_codes=_as_tuple_str(report.get("reason_codes", ())),
        recommendation=str(report.get("recommendation") or ""),
    )


def _latest_by_phase(evidence: Sequence[Hyp004ClosureEvidence]) -> dict[str, Hyp004ClosureEvidence]:
    latest: dict[str, Hyp004ClosureEvidence] = {}
    for item in evidence:
        latest[item.phase] = item
    return latest


def _any_training_paper_live_approval(reports: Sequence[Mapping[str, Any]]) -> bool:
    for report in reports:
        for key in TRAINING_PAPER_LIVE_KEYS:
            if _safe_bool(report.get(key, False)):
                return True
    return False


def _build_registry_snapshot(
    *,
    hypothesis_id: str,
    branch_name: str,
    generated_at: str,
    reason_codes: Sequence[str],
    selected_25o_family: str,
    selected_refinement_name: str,
) -> dict[str, Any]:
    return {
        "contract_version": HYP004_BRANCH_CLOSURE_CONTRACT_VERSION,
        "generated_at": generated_at,
        "registry_update_type": "hypothesis_branch_closure",
        "hypotheses": [
            {
                "id": hypothesis_id,
                "branch_name": branch_name,
                "title": "Cross-symbol relative strength rotation",
                "status": "CLOSED_NO_GO",
                "closed_by": HYP004_BRANCH_CLOSURE_CONTRACT_VERSION,
                "closure_reason_codes": list(reason_codes),
                "selected_25o_family": selected_25o_family,
                "selected_refinement_name": selected_refinement_name,
                "approved_for_research_candidate": False,
                "approved_for_training_candidate": False,
                "approved_for_paper_candidate": False,
                "approved_for_live_real": False,
                "live_real_allowed": False,
            }
        ],
        "guardrails": {
            "training_allowed": False,
            "paper_allowed": False,
            "live_real_allowed": False,
            "reload_allowed": False,
            "order_actions_allowed": False,
        },
    }


def build_hyp004_branch_closure_evidence_pack(
    reports: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    hypothesis_id: str = "HYP-004",
    branch_name: str = "cross_symbol_relative_strength_rotation",
    generated_at: str | None = None,
    limits: Hyp004ClosureLimits | None = None,
) -> Hyp004ClosureReport:
    generated_at = generated_at or utc_now_iso()
    limits = limits or Hyp004ClosureLimits()
    evidence_items = tuple(
        item
        for item in (normalize_hyp004_evidence(source, report) for source, report in reports)
        if item is not None
    )
    by_phase = _latest_by_phase(evidence_items)
    exploration = by_phase.get("25O")
    refinement = by_phase.get("25P")

    reason_codes: list[str] = []

    if exploration and exploration.decision in HYP004_EXPLORATION_BLOCK_DECISIONS:
        reason_codes.append("HYP004_EXPLORATION_BLOCK_CONFIRMED")
    else:
        reason_codes.append("HYP004_EXPLORATION_BLOCK_MISSING")

    if refinement and refinement.decision in HYP004_REFINEMENT_BLOCK_DECISIONS:
        reason_codes.append("HYP004_REFINEMENT_BLOCK_CONFIRMED")
    else:
        reason_codes.append("HYP004_REFINEMENT_BLOCK_MISSING")

    if exploration and exploration.passed_candidate_count <= 0:
        reason_codes.append("NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED_CONFIRMED")
    else:
        reason_codes.append("HYP004_EXPLORATION_PASS_CANDIDATE_PRESENT")

    if refinement and refinement.passed_candidate_count <= 0:
        reason_codes.append("NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED_CONFIRMED")
    else:
        reason_codes.append("HYP004_REFINEMENT_PASS_CANDIDATE_PRESENT")

    all_raw_reports = [report for _, report in reports]
    no_approval = not _any_training_paper_live_approval(all_raw_reports)
    if no_approval:
        reason_codes.append("NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED")
    else:
        reason_codes.append("TRAINING_PAPER_LIVE_APPROVAL_DETECTED")

    if exploration:
        for code in exploration.reason_codes:
            if code in {"NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED", "DIAGNOSTIC_STRATEGY_NOT_APPROVABLE"}:
                reason_codes.append(f"25O_{code}")
    if refinement:
        for code in refinement.reason_codes:
            if code in {"NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED", "DIAGNOSTIC_REFINEMENT_NOT_APPROVABLE"}:
                reason_codes.append(f"25P_{code}")

    closure_ok = (
        exploration is not None
        and refinement is not None
        and exploration.decision in HYP004_EXPLORATION_BLOCK_DECISIONS
        and refinement.decision in HYP004_REFINEMENT_BLOCK_DECISIONS
        and exploration.passed_candidate_count <= 0
        and refinement.passed_candidate_count <= 0
        and no_approval
    )

    if closure_ok:
        decision = "HYP004_BRANCH_CLOSURE_CONFIRMED"
        ok = True
        reason_codes.append("HYP004_BRANCH_CLOSED_NO_GO")
        recommendation = (
            "HYP-004 cross-symbol relative strength branch is closed no-go. Do not train, reload, "
            "start paper trading, or enable live trading. Return to the research backlog for the next pre-registered hypothesis."
        )
    else:
        decision = "HYP004_BRANCH_CLOSURE_BLOCK"
        ok = False
        recommendation = (
            "HYP-004 branch closure evidence is incomplete or unsafe. Do not train, reload, paper trade, "
            "or enable live trading until the missing closure evidence is resolved."
        )

    reason_codes = tuple(sorted(set(reason_codes)))
    selected_25o_family = exploration.selected_strategy_family if exploration else "UNKNOWN"
    selected_refinement_name = refinement.selected_refinement_name if refinement else "UNKNOWN"
    registry_snapshot = _build_registry_snapshot(
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        generated_at=generated_at,
        reason_codes=reason_codes,
        selected_25o_family=selected_25o_family,
        selected_refinement_name=selected_refinement_name,
    )
    guardrails = {
        "observation_only": True,
        "public_market_data_get_only": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "training_allowed": False,
        "paper_allowed": False,
        "live_real_allowed": False,
    }

    return Hyp004ClosureReport(
        contract_version=HYP004_BRANCH_CLOSURE_CONTRACT_VERSION,
        phase=HYP004_BRANCH_CLOSURE_CONTRACT_VERSION,
        report_type="hyp004_branch_closure_evidence_pack",
        generated_at=generated_at,
        decision=decision,
        ok=ok,
        source_reports=len(reports),
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        final_25o_decision=exploration.decision if exploration else "MISSING",
        final_25p_decision=refinement.decision if refinement else "MISSING",
        selected_25o_family=selected_25o_family,
        selected_refinement_name=selected_refinement_name,
        exploration_candidate_count=exploration.candidate_count if exploration else 0,
        exploration_passed_candidate_count=exploration.passed_candidate_count if exploration else 0,
        refinement_candidate_count=refinement.candidate_count if refinement else 0,
        refinement_passed_candidate_count=refinement.passed_candidate_count if refinement else 0,
        no_approvable_exploration_candidate_confirmed=bool(exploration and exploration.passed_candidate_count <= 0),
        no_approvable_refinement_candidate_confirmed=bool(refinement and refinement.passed_candidate_count <= 0),
        approved_for_research_candidate=False,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        live_real_allowed=False,
        reload_performed=False,
        config_mutation_performed=False,
        order_actions_performed=False,
        post_requests_allowed=False,
        observation_only=True,
        reason_codes=reason_codes,
        recommendation=recommendation,
        evidence=evidence_items,
        registry_snapshot=registry_snapshot,
        guardrails=guardrails,
        limits=limits,
    )


def report_to_dict(report: Hyp004ClosureReport) -> dict[str, Any]:
    return asdict(report)


def load_json_report(path: str | Path) -> tuple[str, Mapping[str, Any]]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"JSON report must be an object: {p}")
    return str(p), data


def discover_reports(reports_dir: str | Path, *, include_all: bool = False) -> list[Path]:
    directory = Path(reports_dir)
    if not directory.exists():
        return []
    patterns = [
        "4B436625O_hyp004_cross_symbol_relative_strength_exploration_*.json",
        "4B436625P_hyp004_relative_strength_refinement_*.json",
    ]
    found: list[Path] = []
    for pattern in patterns:
        matches = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        found.extend(matches if include_all else matches[:1])
    return found


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def render_markdown(report: Hyp004ClosureReport) -> str:
    lines = [
        "# 4B.4.3.6.6.25Q HYP-004 Branch Closure Evidence Pack",
        "",
        f"- contract_version: `{report.contract_version}`",
        f"- decision: **{report.decision}**",
        f"- source_reports: `{report.source_reports}`",
        f"- hypothesis_id: `{report.hypothesis_id}`",
        f"- branch_name: `{report.branch_name}`",
        f"- final_25o_decision: `{report.final_25o_decision}`",
        f"- final_25p_decision: `{report.final_25p_decision}`",
        f"- selected_25o_family: `{report.selected_25o_family}`",
        f"- selected_refinement_name: `{report.selected_refinement_name}`",
        f"- no_approvable_exploration_candidate_confirmed: `{report.no_approvable_exploration_candidate_confirmed}`",
        f"- no_approvable_refinement_candidate_confirmed: `{report.no_approvable_refinement_candidate_confirmed}`",
        f"- approved_for_research_candidate: `{report.approved_for_research_candidate}`",
        f"- approved_for_training_candidate: `{report.approved_for_training_candidate}`",
        f"- approved_for_paper_candidate: `{report.approved_for_paper_candidate}`",
        f"- approved_for_live_real: `{report.approved_for_live_real}`",
        f"- reason_codes: `{list(report.reason_codes)}`",
        f"- recommendation: {report.recommendation}",
        "",
        "## Guardrails",
        "",
    ]
    for key, value in report.guardrails.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Evidence",
        "",
        "| phase | decision | selected | candidates | passed | signals | mean bps | median bps | pf | oos bps | reasons |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for item in report.evidence:
        selected = item.selected_refinement_name if item.phase == "25P" else item.selected_strategy_family
        lines.append(
            f"| {item.phase} | {item.decision} | {selected} | {item.candidate_count} | {item.passed_candidate_count} | "
            f"{item.signal_count} | {item.mean_net_edge_bps:.6f} | {item.median_net_edge_bps:.6f} | "
            f"{item.profit_factor:.6f} | {item.oos_mean_net_edge_bps:.6f} | `{list(item.reason_codes)}` |"
        )
    lines.extend([
        "",
        "## Registry Snapshot",
        "",
        f"- HYP-004 status: `{report.registry_snapshot['hypotheses'][0]['status']}`",
        "- Training remains blocked.",
        "- Paper/live remain blocked.",
        "",
        "## Policy",
        "",
        "This closure pack never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.",
    ])
    return "\n".join(lines) + "\n"


def write_report_bundle(report: Hyp004ClosureReport, *, out_dir: str | Path) -> tuple[Path, Path, Path]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = Path(out_dir)
    report_json = directory / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = directory / f"{REPORT_PREFIX}_{stamp}.md"
    registry_json = directory / f"{REGISTRY_PREFIX}_{stamp}.json"
    payload = report_to_dict(report)
    write_json(report_json, payload)
    write_json(registry_json, report.registry_snapshot)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(render_markdown(report), encoding="utf-8")
    return report_json, report_md, registry_json
