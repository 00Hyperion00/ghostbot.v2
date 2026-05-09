from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json

HYP003_REFINEMENT_CONTRACT_VERSION = "4B.4.3.6.6.25L"
REPORT_PREFIX = "4B436625L_hyp003_candidate_refinement_branch_decision"
NEXT_CANDIDATE_PREFIX = "4B436625L_hyp003_next_candidate_for_25K"
DEFAULT_HYPOTHESIS_ID = "HYP-003"

TERMINAL_ROBUSTNESS_BLOCK_CODES = {
    "ROBUST_MEAN_EDGE_LOW",
    "ROBUST_MEDIAN_EDGE_LOW",
    "ROBUST_OOS_EDGE_LOW",
    "ROBUST_PROFIT_FACTOR_LOW",
    "ROBUST_WALK_FORWARD_STABILITY_LOW",
    "ROBUST_WIN_RATE_LOW",
    "ROBUST_TOP_WIN_DEPENDENCY_HIGH",
    "ROBUST_SIDE_IMBALANCE_HIGH",
    "ROBUST_REGIME_PERSISTENCE_LOW",
    "ROBUST_MAX_DRAWDOWN_HIGH",
}


@dataclass(frozen=True)
class Hyp003CandidateKey:
    symbol: str
    interval: str
    strategy_family: str
    regime: str

    def normalized(self) -> tuple[str, str, str, str]:
        return (self.symbol.upper(), self.interval, self.strategy_family, self.regime)


@dataclass(frozen=True)
class Hyp003CandidateEvidence:
    source_phase: str
    source_report: str
    key: Hyp003CandidateKey
    decision: str
    score: float
    signal_count: int
    mean_net_edge_bps: float
    median_net_edge_bps: float
    profit_factor: float
    oos_mean_net_edge_bps: float
    walk_forward_positive_rate_pct: float
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class Hyp003BranchDecisionLimits:
    min_alternate_signal_count: int = 40
    min_alternate_mean_net_edge_bps: float = 0.0
    min_alternate_median_net_edge_bps: float = 0.0
    min_alternate_profit_factor: float = 1.20
    min_alternate_oos_edge_bps: float = 0.0
    require_25j_pass: bool = True
    require_failed_selected_25k_block: bool = True


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    return (str(value),)


def _phase(report: Mapping[str, Any], source_report: str = "") -> str:
    text = " ".join(str(item) for item in (report.get("contract_version"), report.get("phase"), report.get("report_type"), source_report) if item).upper()
    if "25J" in text or "HYP003_REGIME" in text or "EXPLORATION" in text:
        return "25J"
    if "25K" in text or "ROBUSTNESS" in text or "WALKFORWARD" in text or "WALK_FORWARD" in text:
        return "25K"
    return "UNKNOWN"


def _metrics_from(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    metrics = candidate.get("metrics")
    if isinstance(metrics, Mapping):
        return metrics
    return candidate


def _candidate_key_from(candidate: Mapping[str, Any]) -> Hyp003CandidateKey:
    spec = candidate.get("spec") if isinstance(candidate.get("spec"), Mapping) else {}
    candidate_spec = candidate.get("candidate_spec") if isinstance(candidate.get("candidate_spec"), Mapping) else {}
    return Hyp003CandidateKey(
        symbol=str(candidate.get("symbol") or candidate_spec.get("symbol") or spec.get("symbol") or "").upper(),
        interval=str(candidate.get("interval") or candidate_spec.get("interval") or spec.get("interval") or ""),
        strategy_family=str(
            candidate.get("strategy_family")
            or candidate.get("strategy")
            or candidate_spec.get("strategy")
            or spec.get("name")
            or ""
        ),
        regime=str(candidate.get("regime") or candidate_spec.get("regime") or spec.get("regime") or ""),
    )


def _candidate_from_25j(candidate: Mapping[str, Any], source_report: str) -> Hyp003CandidateEvidence:
    metrics = _metrics_from(candidate)
    key = _candidate_key_from(candidate)
    return Hyp003CandidateEvidence(
        source_phase="25J",
        source_report=source_report,
        key=key,
        decision=str(candidate.get("decision") or "UNKNOWN"),
        score=_safe_float(candidate.get("score"), 0.0),
        signal_count=_safe_int(metrics.get("signal_count"), 0),
        mean_net_edge_bps=_safe_float(metrics.get("mean_net_edge_bps"), 0.0),
        median_net_edge_bps=_safe_float(metrics.get("median_net_edge_bps"), 0.0),
        profit_factor=_safe_float(metrics.get("profit_factor"), 0.0),
        oos_mean_net_edge_bps=_safe_float(metrics.get("oos_mean_net_edge_bps"), 0.0),
        walk_forward_positive_rate_pct=_safe_float(metrics.get("walk_forward_positive_rate_pct"), 0.0),
        reason_codes=_tuple_str(candidate.get("reason_codes")),
        warnings=_tuple_str(candidate.get("warnings")),
        raw=candidate,
    )


def _candidate_from_25k(report: Mapping[str, Any], source_report: str) -> Hyp003CandidateEvidence:
    spec = report.get("candidate_spec") if isinstance(report.get("candidate_spec"), Mapping) else {}
    metrics = report.get("signal_metrics") if isinstance(report.get("signal_metrics"), Mapping) else {}
    oos = report.get("oos_segment") if isinstance(report.get("oos_segment"), Mapping) else {}
    key = Hyp003CandidateKey(
        symbol=str(spec.get("symbol") or "").upper(),
        interval=str(spec.get("interval") or ""),
        strategy_family=str(spec.get("strategy") or ""),
        regime=str(spec.get("regime") or ""),
    )
    return Hyp003CandidateEvidence(
        source_phase="25K",
        source_report=source_report,
        key=key,
        decision=str(report.get("decision") or "UNKNOWN"),
        score=_safe_float(report.get("score"), 0.0),
        signal_count=_safe_int(metrics.get("signal_count"), 0),
        mean_net_edge_bps=_safe_float(metrics.get("mean_net_edge_bps"), 0.0),
        median_net_edge_bps=_safe_float(metrics.get("median_net_edge_bps"), 0.0),
        profit_factor=_safe_float(metrics.get("profit_factor"), 0.0),
        oos_mean_net_edge_bps=_safe_float(oos.get("mean_net_edge_bps"), _safe_float(report.get("oos_mean_net_edge_bps"), 0.0)),
        walk_forward_positive_rate_pct=_safe_float(report.get("walk_forward_positive_rate_pct"), 0.0),
        reason_codes=_tuple_str(report.get("reason_codes")),
        warnings=_tuple_str(report.get("warnings")),
        raw={"candidate_spec": spec, "signal_metrics": metrics},
    )


def extract_hyp003_evidence(reports: Sequence[tuple[str, Mapping[str, Any]]]) -> tuple[list[Hyp003CandidateEvidence], list[Hyp003CandidateEvidence]]:
    exploration: list[Hyp003CandidateEvidence] = []
    robustness: list[Hyp003CandidateEvidence] = []
    for source_report, report in reports:
        phase = _phase(report, source_report)
        if phase == "25J":
            candidates = report.get("candidates")
            if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes)):
                for candidate in candidates:
                    if isinstance(candidate, Mapping):
                        exploration.append(_candidate_from_25j(candidate, source_report))
            selected = report.get("selected_candidate")
            if isinstance(selected, Mapping):
                selected_ev = _candidate_from_25j(selected, source_report)
                if all(item.key.normalized() != selected_ev.key.normalized() for item in exploration):
                    exploration.append(selected_ev)
        elif phase == "25K":
            robustness.append(_candidate_from_25k(report, source_report))
    return exploration, robustness


def _candidate_passes_alternate_gate(candidate: Hyp003CandidateEvidence, limits: Hyp003BranchDecisionLimits) -> bool:
    if limits.require_25j_pass and candidate.decision.upper() != "PASS":
        return False
    if candidate.signal_count < limits.min_alternate_signal_count:
        return False
    if candidate.mean_net_edge_bps <= limits.min_alternate_mean_net_edge_bps:
        return False
    if candidate.median_net_edge_bps <= limits.min_alternate_median_net_edge_bps:
        return False
    if candidate.profit_factor < limits.min_alternate_profit_factor:
        return False
    if candidate.oos_mean_net_edge_bps <= limits.min_alternate_oos_edge_bps:
        return False
    return True


def _sort_key(candidate: Hyp003CandidateEvidence) -> tuple[float, float, float, int]:
    return (candidate.score, candidate.profit_factor, candidate.median_net_edge_bps, candidate.signal_count)


def _latest_25k(robustness: Sequence[Hyp003CandidateEvidence]) -> Hyp003CandidateEvidence | None:
    return robustness[-1] if robustness else None


def build_next_candidate_25j_report(
    source_25j_report: Mapping[str, Any],
    next_candidate: Hyp003CandidateEvidence,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Create a 25K-compatible synthetic 25J report with selected_candidate replaced.

    25K reads selected_candidate from a 25J-shaped input report. This helper allows
    the next HYP-003 candidate to be audited by the existing 25K runner without
    changing runtime, config, or live trading state.
    """
    generated_at = generated_at or utc_now_iso()
    report = dict(source_25j_report)
    report["contract_version"] = HYP003_REFINEMENT_CONTRACT_VERSION
    report["phase"] = "25L"
    report["report_type"] = "hyp003_next_candidate_for_25k_compat_report"
    report["decision"] = "HYP003_NEXT_CANDIDATE_SELECTED_FOR_ROBUSTNESS"
    report["generated_at"] = generated_at
    report["selected_candidate"] = dict(next_candidate.raw)
    report["selected_candidate_source_phase"] = next_candidate.source_phase
    report["reason_codes"] = ["HYP003_NEXT_CANDIDATE_SELECTED_FOR_ROBUSTNESS"]
    report["recommendation"] = "Run 25K robustness/walk-forward confirmation on this next HYP-003 candidate. Paper/live remain blocked."
    report["approved_for_research_candidate"] = True
    report["approved_for_training_candidate"] = False
    report["approved_for_paper_candidate"] = False
    report["approved_for_live_real"] = False
    report["live_real_allowed"] = False
    report["post_requests_allowed"] = False
    report["config_mutation_performed"] = False
    report["order_actions_performed"] = False
    report["reload_performed"] = False
    return report


def build_hyp003_candidate_refinement_branch_decision(
    reports: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    limits: Hyp003BranchDecisionLimits | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    limits = limits or Hyp003BranchDecisionLimits()
    generated_at = generated_at or utc_now_iso()
    exploration, robustness = extract_hyp003_evidence(reports)
    latest = _latest_25k(robustness)
    reason_codes: list[str] = []
    warnings: list[str] = []
    failed_key: tuple[str, str, str, str] | None = None

    if not exploration:
        reason_codes.append("HYP003_EXPLORATION_EVIDENCE_MISSING")
    if latest is None:
        reason_codes.append("HYP003_ROBUSTNESS_EVIDENCE_MISSING")

    selected_failed_terminal = False
    if latest is not None:
        failed_key = latest.key.normalized()
        if latest.decision == "HYP003_ROBUSTNESS_PASS":
            decision = "HYP003_BRANCH_RESEARCH_CONTINUE"
            recommendation = "HYP-003 candidate passed robustness. Continue only to no-order shadow planning; training/paper/live remain blocked."
            selected_next: Hyp003CandidateEvidence | None = None
            approved_for_research = True
        elif latest.decision == "HYP003_ROBUSTNESS_BLOCK":
            selected_failed_terminal = True
            reason_codes.append("HYP003_SELECTED_CANDIDATE_ROBUSTNESS_BLOCK")
            reason_codes.extend(code for code in latest.reason_codes if code in TERMINAL_ROBUSTNESS_BLOCK_CODES)
            alternates = [
                candidate
                for candidate in exploration
                if candidate.key.normalized() != failed_key and _candidate_passes_alternate_gate(candidate, limits)
            ]
            alternates.sort(key=_sort_key, reverse=True)
            selected_next = alternates[0] if alternates else None
            if selected_next is not None:
                decision = "HYP003_NEXT_CANDIDATE_SELECTED_FOR_ROBUSTNESS"
                approved_for_research = True
                reason_codes.append("HYP003_ALTERNATE_RESEARCH_CANDIDATE_AVAILABLE")
                recommendation = "Selected HYP-003 candidate failed 25K, but another 25J PASS candidate is available. Run 25K on the generated next-candidate report; paper/live remain blocked."
            else:
                decision = "HYP003_BRANCH_CLOSURE_RECOMMENDED"
                approved_for_research = False
                reason_codes.append("NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE")
                recommendation = "HYP-003 selected candidate failed robustness and no alternate 25J PASS candidate meets refinement criteria. Close this branch or return to registry; do not train, reload, paper trade, or enable live trading."
        else:
            decision = "HYP003_BRANCH_DECISION_INCONCLUSIVE"
            selected_next = None
            approved_for_research = False
            reason_codes.append("HYP003_ROBUSTNESS_DECISION_UNKNOWN")
            recommendation = "HYP-003 branch evidence is inconclusive. Provide a valid 25K PASS/BLOCK report."
    else:
        decision = "HYP003_BRANCH_DECISION_PENDING_ROBUSTNESS"
        selected_next = None
        approved_for_research = False
        recommendation = "25K robustness evidence is missing. Run robustness/walk-forward confirmation before branch decision."

    # Build compatible next-candidate report if needed.
    source_25j_report = next((report for _, report in reports if _phase(report) == "25J"), None)
    next_candidate_25k_report = None
    if selected_next is not None and source_25j_report is not None:
        next_candidate_25k_report = build_next_candidate_25j_report(source_25j_report, selected_next, generated_at=generated_at)

    guardrails = {
        "observation_only": True,
        "public_market_data_requests_performed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "training_allowed": False,
        "paper_allowed": False,
        "live_real_allowed": False,
        "backtest_pass_is_not_paper_permission": True,
        "paper_pass_is_not_live_permission": True,
    }

    return {
        "contract_version": HYP003_REFINEMENT_CONTRACT_VERSION,
        "phase": "25L",
        "report_type": "hyp003_candidate_refinement_branch_decision_gate",
        "generated_at": generated_at,
        "decision": decision,
        "ok": decision in {"HYP003_NEXT_CANDIDATE_SELECTED_FOR_ROBUSTNESS", "HYP003_BRANCH_RESEARCH_CONTINUE"},
        "source_reports": len(reports),
        "hypothesis_id": DEFAULT_HYPOTHESIS_ID,
        "selected_failed_terminal": selected_failed_terminal,
        "failed_candidate": asdict(latest) if latest is not None else None,
        "alternate_candidate_count": len([
            candidate for candidate in exploration if failed_key is None or candidate.key.normalized() != failed_key
        ]),
        "selected_next_candidate": asdict(selected_next) if selected_next is not None else None,
        "next_candidate_25k_report": next_candidate_25k_report,
        "exploration_candidates": [asdict(candidate) for candidate in exploration],
        "robustness_candidates": [asdict(candidate) for candidate in robustness],
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(warnings)),
        "recommendation": recommendation,
        "limits": asdict(limits),
        "guardrails": guardrails,
        "approved_for_research_candidate": approved_for_research,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
    }


def load_json_report(path: str | Path) -> tuple[str, dict[str, Any]]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON report must contain object: {path}")
    return str(path), payload


def discover_reports(reports_dir: str | Path, include_all: bool = False) -> list[Path]:
    reports_dir = Path(reports_dir)
    if not reports_dir.exists():
        return []
    patterns = [
        "4B436625J_hyp003_regime_strategy_exploration_*.json",
        "4B436625K_hyp003_robustness_walkforward_confirmation_*.json",
    ]
    found: list[Path] = []
    for pattern in patterns:
        matches = sorted(reports_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
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


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def render_markdown(report: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# 4B.4.3.6.6.25L HYP-003 Candidate Refinement / Branch Decision Gate")
    lines.append("")
    for key in [
        "contract_version",
        "decision",
        "hypothesis_id",
        "source_reports",
        "approved_for_research_candidate",
        "approved_for_training_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "reason_codes",
        "recommendation",
    ]:
        if key in report:
            value = report[key]
            lines.append(f"- {key}: **{value}**" if key == "decision" else f"- {key}: `{value}`")
    failed = report.get("failed_candidate") if isinstance(report.get("failed_candidate"), Mapping) else None
    if failed:
        key = failed.get("key", {}) if isinstance(failed.get("key"), Mapping) else {}
        lines.extend(["", "## Failed 25K Candidate", ""])
        lines.append(f"- symbol: `{key.get('symbol')}`")
        lines.append(f"- interval: `{key.get('interval')}`")
        lines.append(f"- strategy_family: `{key.get('strategy_family')}`")
        lines.append(f"- regime: `{key.get('regime')}`")
        for metric in ["signal_count", "mean_net_edge_bps", "median_net_edge_bps", "profit_factor", "oos_mean_net_edge_bps", "walk_forward_positive_rate_pct"]:
            lines.append(f"- {metric}: `{failed.get(metric)}`")
    selected = report.get("selected_next_candidate") if isinstance(report.get("selected_next_candidate"), Mapping) else None
    if selected:
        key = selected.get("key", {}) if isinstance(selected.get("key"), Mapping) else {}
        lines.extend(["", "## Selected Next Candidate", ""])
        lines.append(f"- symbol: `{key.get('symbol')}`")
        lines.append(f"- interval: `{key.get('interval')}`")
        lines.append(f"- strategy_family: `{key.get('strategy_family')}`")
        lines.append(f"- regime: `{key.get('regime')}`")
        for metric in ["signal_count", "mean_net_edge_bps", "median_net_edge_bps", "profit_factor", "oos_mean_net_edge_bps", "walk_forward_positive_rate_pct"]:
            lines.append(f"- {metric}: `{selected.get(metric)}`")
    lines.extend(["", "## Exploration Candidates", ""])
    lines.append("| # | phase | decision | score | symbol | interval | family | regime | signals | mean | median | pf | oos | reasons |")
    lines.append("|---:|---|---|---:|---|---|---|---|---:|---:|---:|---:|---:|---|")
    for idx, item in enumerate(report.get("exploration_candidates", []), 1):
        key = item.get("key", {}) if isinstance(item, Mapping) and isinstance(item.get("key"), Mapping) else {}
        lines.append(
            f"| {idx} | {item.get('source_phase')} | {item.get('decision')} | {item.get('score')} | {key.get('symbol')} | {key.get('interval')} | {key.get('strategy_family')} | {key.get('regime')} | {item.get('signal_count')} | {item.get('mean_net_edge_bps')} | {item.get('median_net_edge_bps')} | {item.get('profit_factor')} | {item.get('oos_mean_net_edge_bps')} | `{item.get('reason_codes')}` |"
        )
    lines.extend(["", "## Guardrails", ""])
    for key, value in dict(report.get("guardrails", {})).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Policy", "", "This gate never fetches market data, trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders. Any next candidate is research-only and must pass 25K before further planning."])
    return "\n".join(lines) + "\n"
