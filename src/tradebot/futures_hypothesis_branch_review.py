from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json
import math

FUTURES_BRANCH_REVIEW_CONTRACT_VERSION = "4B.4.3.6.6.25F"
REPORT_PREFIX = "4B436625F_futures_hypothesis_branch_review"

TERMINAL_BLOCK_CODES = {
    "NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED",
    "DRY_RUN_SIGNAL_COUNT_LOW",
    "DRY_RUN_MEDIAN_EDGE_LOW",
    "DRY_RUN_WALK_FORWARD_STABILITY_LOW",
    "NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED",
    "REFINEMENT_SIGNAL_COUNT_LOW",
    "REFINEMENT_SIDE_IMBALANCE_HIGH",
    "REFINEMENT_TOP_WIN_DEPENDENCY_HIGH",
    "REFINEMENT_OOS_EDGE_LOW",
}

SPARSE_CODES = {
    "DRY_RUN_SIGNAL_COUNT_LOW",
    "REFINEMENT_SIGNAL_COUNT_LOW",
    "REFINEMENT_TOP_WIN_DEPENDENCY_HIGH",
    "REFINEMENT_SIDE_IMBALANCE_HIGH",
}

PHASE_ORDER = ["25B", "25C", "25D", "25E"]


@dataclass(frozen=True)
class BranchReviewLimits:
    min_combined_signal_count: int = 30
    min_symbol_signal_count: int = 20
    min_mean_net_edge_bps: float = 0.0
    min_median_net_edge_bps: float = 0.0
    min_profit_factor: float = 1.15
    max_drawdown_pct: float = 30.0
    min_oos_edge_bps: float = 0.0
    max_top_win_dependency_pct: float = 35.0


@dataclass(frozen=True)
class NormalizedBranchCandidate:
    source_phase: str
    source_report: str
    symbol: str
    interval: str
    strategy: str
    decision: str
    signal_count: int = 0
    coverage_pct: float = 0.0
    mean_net_edge_bps: float = 0.0
    median_net_edge_bps: float | None = None
    win_rate_pct: float | None = None
    profit_factor: float = 0.0
    max_drawdown_pct: float | None = None
    oos_edge_bps: float | None = None
    walk_forward_positive_rate_pct: float | None = None
    top_win_dependency_pct: float | None = None
    reason_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_pass(self) -> bool:
        return self.decision.upper() == "PASS"

    @property
    def is_block(self) -> bool:
        return self.decision.upper() == "BLOCK"

    @property
    def has_terminal_sparse_block(self) -> bool:
        return bool(set(self.reason_codes).intersection(SPARSE_CODES))


@dataclass(frozen=True)
class SymbolBranchSummary:
    symbol: str
    interval: str
    strategy: str
    exploration_pass: bool = False
    robustness_pass: bool = False
    dry_run_pass: bool = False
    refinement_pass: bool = False
    terminal_block: bool = False
    sparse_or_outlier_block: bool = False
    latest_decision: str = "MISSING"
    best_phase: str | None = None
    best_signal_count: int = 0
    best_mean_net_edge_bps: float = 0.0
    best_median_net_edge_bps: float | None = None
    best_profit_factor: float = 0.0
    reason_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CombinedBranchSummary:
    symbol_count: int
    symbols: tuple[str, ...]
    signal_count: int
    weighted_mean_net_edge_bps: float
    worst_median_net_edge_bps: float | None
    min_profit_factor: float
    all_have_exploration_pass: bool
    any_have_terminal_block: bool
    dry_run_or_refinement_confirmed_count: int


@dataclass(frozen=True)
class FuturesBranchReviewReport:
    contract_version: str
    phase: str
    report_type: str
    decision: str
    ok: bool
    source_reports: int
    primary_symbol: str
    companion_symbols: tuple[str, ...]
    interval: str
    strategy: str
    approved_for_research_candidate: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    live_real_allowed: bool
    reload_performed: bool
    config_mutation_performed: bool
    order_actions_performed: bool
    observation_only: bool
    no_post_actions: bool
    reason_codes: tuple[str, ...]
    recommendation: str
    primary_summary: SymbolBranchSummary | None
    companion_summaries: tuple[SymbolBranchSummary, ...]
    combined_summary: CombinedBranchSummary | None
    candidates: tuple[NormalizedBranchCandidate, ...]
    next_actions: tuple[str, ...]
    guardrails: Mapping[str, bool]


# ----------------------------- generic parsing helpers -----------------------------


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(float(value))
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


def _first_present(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def infer_phase(report: Mapping[str, Any], source_report: str = "") -> str:
    text = " ".join(
        str(x)
        for x in (
            report.get("contract_version"),
            report.get("phase"),
            report.get("report_type"),
            source_report,
        )
        if x
    ).upper()
    for phase in ("25B", "25C", "25D", "25E"):
        compact = phase.replace(".", "")
        if phase in text or compact in text or f"4B4366{phase}" in text:
            return phase
    if "FUTURES_FUNDING" in text or "OPEN_INTEREST_EDGE" in text:
        return "25B"
    if "ROBUSTNESS" in text:
        return "25C"
    if "DRY-RUN" in text or "DRY_RUN" in text or "SIMULATOR" in text:
        return "25D"
    if "REFINEMENT" in text or "MEDIAN" in text:
        return "25E"
    return "UNKNOWN"


def _normalize_candidate(
    raw: Mapping[str, Any],
    *,
    phase: str,
    source_report: str,
    fallback_symbol: str = "",
    fallback_interval: str = "",
    fallback_strategy: str = "",
    fallback_decision: str = "",
) -> NormalizedBranchCandidate:
    decision = str(_first_present(raw, "decision", default=fallback_decision or "UNKNOWN")).upper()
    symbol = str(_first_present(raw, "symbol", default=fallback_symbol or "")).upper()
    interval = str(_first_present(raw, "interval", default=fallback_interval or ""))
    strategy = str(_first_present(raw, "strategy", "strategy_name", default=fallback_strategy or ""))

    if not symbol or not interval or not strategy:
        selected = raw.get("selected")
        if isinstance(selected, str):
            parts = selected.replace("`", "").split()
            if len(parts) >= 3:
                symbol = symbol or parts[0].upper()
                interval = interval or parts[1]
                strategy = strategy or parts[2]

    return NormalizedBranchCandidate(
        source_phase=phase,
        source_report=source_report,
        symbol=symbol,
        interval=interval,
        strategy=strategy,
        decision=decision,
        signal_count=_safe_int(_first_present(raw, "signals", "signal_count", "selected_signal_count", default=0)),
        coverage_pct=_safe_float(_first_present(raw, "coverage_pct", "selected_coverage_pct", default=0.0)),
        mean_net_edge_bps=_safe_float(
            _first_present(raw, "mean_edge_bps", "mean_net_edge_bps", "selected_mean_net_edge_bps", default=0.0)
        ),
        median_net_edge_bps=(
            _safe_float(_first_present(raw, "median_edge_bps", "median_net_edge_bps", default=None))
            if _first_present(raw, "median_edge_bps", "median_net_edge_bps", default=None) is not None
            else None
        ),
        win_rate_pct=(
            _safe_float(_first_present(raw, "win_rate_pct", default=None))
            if _first_present(raw, "win_rate_pct", default=None) is not None
            else None
        ),
        profit_factor=_safe_float(_first_present(raw, "profit_factor", "selected_profit_factor", default=0.0)),
        max_drawdown_pct=(
            _safe_float(_first_present(raw, "max_dd_pct", "max_drawdown_pct", default=None))
            if _first_present(raw, "max_dd_pct", "max_drawdown_pct", default=None) is not None
            else None
        ),
        oos_edge_bps=(
            _safe_float(_first_present(raw, "oos_edge_bps", "oos_mean_net_edge_bps", default=None))
            if _first_present(raw, "oos_edge_bps", "oos_mean_net_edge_bps", default=None) is not None
            else None
        ),
        walk_forward_positive_rate_pct=(
            _safe_float(_first_present(raw, "walk_forward_positive_rate_pct", default=None))
            if _first_present(raw, "walk_forward_positive_rate_pct", default=None) is not None
            else None
        ),
        top_win_dependency_pct=(
            _safe_float(_first_present(raw, "top_win_dependency_pct", default=None))
            if _first_present(raw, "top_win_dependency_pct", default=None) is not None
            else None
        ),
        reason_codes=_as_tuple_str(_first_present(raw, "reason_codes", "reasons", default=())),
        warnings=_as_tuple_str(_first_present(raw, "warnings", default=())),
    )


def _selected_from_top_level(report: Mapping[str, Any], phase: str, source_report: str) -> NormalizedBranchCandidate | None:
    selected = report.get("selected")
    symbol = str(report.get("selected_symbol") or report.get("symbol") or "").upper()
    interval = str(report.get("selected_interval") or report.get("interval") or "")
    strategy = str(report.get("selected_strategy") or report.get("strategy") or "")
    if isinstance(selected, str):
        parts = selected.replace("`", "").split()
        if len(parts) >= 3:
            symbol = symbol or parts[0].upper()
            interval = interval or parts[1]
            strategy = strategy or parts[2]
    if not symbol and not interval and not strategy:
        return None
    synthetic = {
        "symbol": symbol,
        "interval": interval,
        "strategy": strategy,
        "decision": report.get("decision", "UNKNOWN"),
        "signals": report.get("selected_signal_count") or report.get("signal_count"),
        "mean_net_edge_bps": report.get("selected_mean_net_edge_bps") or report.get("mean_net_edge_bps"),
        "median_net_edge_bps": report.get("selected_median_net_edge_bps") or report.get("median_net_edge_bps"),
        "profit_factor": report.get("selected_profit_factor") or report.get("profit_factor"),
        "reason_codes": report.get("reason_codes", ()),
        "warnings": report.get("warnings", ()),
    }
    return _normalize_candidate(synthetic, phase=phase, source_report=source_report)


def normalize_report_candidates(report: Mapping[str, Any], source_report: str) -> tuple[NormalizedBranchCandidate, ...]:
    phase = infer_phase(report, source_report)
    candidates: list[NormalizedBranchCandidate] = []
    raw_candidates = report.get("candidates")
    if isinstance(raw_candidates, Sequence) and not isinstance(raw_candidates, (str, bytes)):
        for raw in raw_candidates:
            if isinstance(raw, Mapping):
                candidates.append(_normalize_candidate(raw, phase=phase, source_report=source_report))

    selected_candidate = _selected_from_top_level(report, phase, source_report)
    if selected_candidate is not None:
        candidates.append(selected_candidate)

    # Some 25C/25D/25E reports may nest the selected candidate under selection/best_candidate.
    selection = report.get("selection")
    if isinstance(selection, Mapping):
        best = selection.get("best_candidate") or selection.get("selected_candidate")
        if isinstance(best, Mapping):
            candidates.append(_normalize_candidate(best, phase=phase, source_report=source_report))

    # Deduplicate while preserving order.
    seen: set[tuple[str, str, str, str, str, int]] = set()
    unique: list[NormalizedBranchCandidate] = []
    for candidate in candidates:
        key = (
            candidate.source_phase,
            candidate.symbol,
            candidate.interval,
            candidate.strategy,
            candidate.decision,
            candidate.signal_count,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return tuple(unique)


def load_json_report(path: str | Path) -> Mapping[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise ValueError(f"Report is not a JSON object: {path}")
    return data


# ----------------------------- branch review -----------------------------


def _candidate_rank(candidate: NormalizedBranchCandidate) -> tuple[int, int, float, float]:
    phase_idx = PHASE_ORDER.index(candidate.source_phase) if candidate.source_phase in PHASE_ORDER else -1
    pass_bonus = 1 if candidate.is_pass else 0
    return (phase_idx, pass_bonus, candidate.profit_factor, candidate.mean_net_edge_bps)


def _summarize_symbol(
    symbol: str,
    interval: str,
    strategy: str,
    candidates: Sequence[NormalizedBranchCandidate],
    limits: BranchReviewLimits,
) -> SymbolBranchSummary:
    scoped = [
        candidate
        for candidate in candidates
        if candidate.symbol.upper() == symbol.upper()
        and candidate.interval == interval
        and candidate.strategy == strategy
    ]
    if not scoped:
        return SymbolBranchSummary(
            symbol=symbol.upper(),
            interval=interval,
            strategy=strategy,
            reason_codes=("BRANCH_SYMBOL_REPORT_MISSING",),
        )

    best = max(scoped, key=_candidate_rank)
    by_phase = {phase: [candidate for candidate in scoped if candidate.source_phase == phase] for phase in PHASE_ORDER}

    exploration_pass = any(candidate.is_pass for candidate in by_phase.get("25B", ()))
    robustness_pass = any(candidate.is_pass for candidate in by_phase.get("25C", ()))
    dry_run_pass = any(candidate.is_pass for candidate in by_phase.get("25D", ()))
    refinement_pass = any(candidate.is_pass for candidate in by_phase.get("25E", ()))
    terminal_blocks = [candidate for candidate in scoped if candidate.source_phase in {"25D", "25E"} and candidate.is_block]
    terminal_block = bool(terminal_blocks)
    sparse_or_outlier_block = any(candidate.has_terminal_sparse_block for candidate in terminal_blocks)

    reason_codes: list[str] = []
    warnings: list[str] = []
    for candidate in scoped:
        reason_codes.extend(candidate.reason_codes)
        warnings.extend(candidate.warnings)

    if not exploration_pass:
        reason_codes.append("BRANCH_EXPLORATION_PASS_MISSING")
    if exploration_pass and not (dry_run_pass or refinement_pass) and not terminal_block:
        reason_codes.append("BRANCH_DRY_RUN_REFINEMENT_AUDIT_MISSING")
    if terminal_block:
        reason_codes.append("BRANCH_TERMINAL_AUDIT_BLOCK")
    if sparse_or_outlier_block:
        reason_codes.append("BRANCH_TOO_SPARSE_OR_OUTLIER_DEPENDENT")
    if best.signal_count < limits.min_symbol_signal_count:
        warnings.append("BRANCH_SYMBOL_SIGNAL_COUNT_LOW")

    return SymbolBranchSummary(
        symbol=symbol.upper(),
        interval=interval,
        strategy=strategy,
        exploration_pass=exploration_pass,
        robustness_pass=robustness_pass,
        dry_run_pass=dry_run_pass,
        refinement_pass=refinement_pass,
        terminal_block=terminal_block,
        sparse_or_outlier_block=sparse_or_outlier_block,
        latest_decision=best.decision,
        best_phase=best.source_phase,
        best_signal_count=best.signal_count,
        best_mean_net_edge_bps=best.mean_net_edge_bps,
        best_median_net_edge_bps=best.median_net_edge_bps,
        best_profit_factor=best.profit_factor,
        reason_codes=tuple(sorted(set(reason_codes))),
        warnings=tuple(sorted(set(warnings))),
    )


def _combined_summary(summaries: Sequence[SymbolBranchSummary]) -> CombinedBranchSummary | None:
    if not summaries:
        return None
    signal_total = sum(summary.best_signal_count for summary in summaries)
    if signal_total > 0:
        weighted_mean = sum(summary.best_mean_net_edge_bps * summary.best_signal_count for summary in summaries) / signal_total
    else:
        weighted_mean = 0.0
    medians = [summary.best_median_net_edge_bps for summary in summaries if summary.best_median_net_edge_bps is not None]
    worst_median = min(medians) if medians else None
    profit_factors = [summary.best_profit_factor for summary in summaries if summary.best_profit_factor > 0]
    min_pf = min(profit_factors) if profit_factors else 0.0
    return CombinedBranchSummary(
        symbol_count=len(summaries),
        symbols=tuple(summary.symbol for summary in summaries),
        signal_count=signal_total,
        weighted_mean_net_edge_bps=round(weighted_mean, 6),
        worst_median_net_edge_bps=round(worst_median, 6) if worst_median is not None else None,
        min_profit_factor=round(min_pf, 6),
        all_have_exploration_pass=all(summary.exploration_pass for summary in summaries),
        any_have_terminal_block=any(summary.terminal_block for summary in summaries),
        dry_run_or_refinement_confirmed_count=sum(1 for summary in summaries if summary.dry_run_pass or summary.refinement_pass),
    )


def build_futures_hypothesis_branch_review(
    reports: Sequence[Mapping[str, Any]],
    *,
    source_names: Sequence[str] | None = None,
    primary_symbol: str = "BTCUSDT",
    companion_symbols: Sequence[str] = ("ETHUSDT",),
    interval: str = "4h",
    strategy: str = "funding_trend_exhaustion",
    limits: BranchReviewLimits | None = None,
) -> FuturesBranchReviewReport:
    limits = limits or BranchReviewLimits()
    names = list(source_names or [f"input_{i}" for i in range(len(reports))])
    candidates: list[NormalizedBranchCandidate] = []
    for report, name in zip(reports, names):
        candidates.extend(normalize_report_candidates(report, source_report=name))

    scoped_candidates = tuple(
        candidate
        for candidate in candidates
        if candidate.interval == interval
        and candidate.strategy == strategy
        and candidate.symbol.upper() in {primary_symbol.upper(), *(symbol.upper() for symbol in companion_symbols)}
    )

    primary_summary = _summarize_symbol(primary_symbol, interval, strategy, scoped_candidates, limits)
    companion_summaries = tuple(
        _summarize_symbol(symbol, interval, strategy, scoped_candidates, limits) for symbol in companion_symbols
    )
    combined = _combined_summary((primary_summary, *companion_summaries))

    reason_codes: list[str] = []
    next_actions: list[str] = []

    if not scoped_candidates:
        reason_codes.append("FUTURES_BRANCH_CANDIDATES_MISSING")

    if primary_summary.terminal_block and primary_summary.sparse_or_outlier_block:
        reason_codes.append("PRIMARY_CANDIDATE_TOO_SPARSE_OR_OUTLIER_DEPENDENT")

    companion_missing_audit = [
        summary.symbol
        for summary in companion_summaries
        if summary.exploration_pass and not summary.terminal_block and not (summary.dry_run_pass or summary.refinement_pass)
    ]
    if companion_missing_audit:
        reason_codes.append("COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED")
        next_actions.append(
            "Run the same 25D/25E dry-run and refinement path for companion futures candidates before closing or continuing HYP-002."
        )

    companion_all_terminal_failed = bool(companion_summaries) and all(
        summary.terminal_block or not summary.exploration_pass for summary in companion_summaries
    )

    if combined is not None:
        if combined.signal_count < limits.min_combined_signal_count:
            reason_codes.append("COMBINED_SIGNAL_COUNT_LOW")
        if combined.all_have_exploration_pass and combined.dry_run_or_refinement_confirmed_count == 0:
            reason_codes.append("COMBINED_DRY_RUN_CONFIRMATION_MISSING")
        if combined.any_have_terminal_block:
            reason_codes.append("COMBINED_TERMINAL_AUDIT_BLOCK_PRESENT")

    any_confirmed_pass = primary_summary.dry_run_pass or primary_summary.refinement_pass or any(
        summary.dry_run_pass or summary.refinement_pass for summary in companion_summaries
    )
    any_terminal_block = primary_summary.terminal_block or any(summary.terminal_block for summary in companion_summaries)

    if any_confirmed_pass:
        decision = "BRANCH_RESEARCH_CONTINUE"
        ok = True
        approved_for_research_candidate = True
        recommendation = (
            "At least one futures branch candidate passed dry-run/refinement review. Keep it research-only; "
            "do not train, reload, start paper trading, or enable live trading."
        )
    elif companion_missing_audit:
        decision = "BRANCH_REVIEW_PENDING_COMPANION_AUDIT"
        ok = False
        approved_for_research_candidate = False
        recommendation = (
            "Primary futures branch is too sparse or terminally blocked, while a companion exploration candidate has not been "
            "dry-run/refinement audited. Run companion audit before final closure; paper/live remain blocked."
        )
    elif any_terminal_block and companion_all_terminal_failed:
        decision = "BRANCH_CLOSED_NO_GO"
        ok = False
        approved_for_research_candidate = False
        reason_codes.append("FUTURES_BRANCH_NO_ROBUST_DRY_RUN_CANDIDATE")
        next_actions.append("Close this HYP-002 funding_trend_exhaustion branch or pre-register a materially different futures hypothesis.")
        recommendation = (
            "Futures funding_trend_exhaustion branch has no robust dry-run/refinement candidate. Close this branch or "
            "restart with a new pre-registered futures hypothesis; do not train, reload, paper trade, or enable live trading."
        )
    else:
        decision = "BRANCH_REVIEW_INCONCLUSIVE"
        ok = False
        approved_for_research_candidate = False
        reason_codes.append("FUTURES_BRANCH_EVIDENCE_INCOMPLETE")
        next_actions.append("Provide 25B/25C/25D/25E reports for the primary and companion symbols to complete closure review.")
        recommendation = (
            "Futures branch evidence is incomplete. Do not continue to training/paper/live until closure or continuation evidence is complete."
        )

    reason_codes = sorted(set(reason_codes))
    guardrails = {
        "observation_only": True,
        "no_post_actions": True,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "live_real_allowed": False,
        "training_allowed": False,
        "paper_allowed": False,
    }

    return FuturesBranchReviewReport(
        contract_version=FUTURES_BRANCH_REVIEW_CONTRACT_VERSION,
        phase=FUTURES_BRANCH_REVIEW_CONTRACT_VERSION,
        report_type="futures_hypothesis_branch_review_candidate_closure_decision",
        decision=decision,
        ok=ok,
        source_reports=len(reports),
        primary_symbol=primary_symbol.upper(),
        companion_symbols=tuple(symbol.upper() for symbol in companion_symbols),
        interval=interval,
        strategy=strategy,
        approved_for_research_candidate=approved_for_research_candidate,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        live_real_allowed=False,
        reload_performed=False,
        config_mutation_performed=False,
        order_actions_performed=False,
        observation_only=True,
        no_post_actions=True,
        reason_codes=tuple(reason_codes),
        recommendation=recommendation,
        primary_summary=primary_summary,
        companion_summaries=companion_summaries,
        combined_summary=combined,
        candidates=scoped_candidates,
        next_actions=tuple(next_actions),
        guardrails=guardrails,
    )


def report_to_dict(report: FuturesBranchReviewReport) -> dict[str, Any]:
    return asdict(report)


def write_report_json(report: FuturesBranchReviewReport, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report_to_dict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def render_markdown(report: FuturesBranchReviewReport) -> str:
    lines: list[str] = []
    lines.append("# 4B.4.3.6.6.25F Futures Hypothesis Branch Review / Candidate Closure Decision")
    lines.append("")
    lines.append(f"- contract_version: `{report.contract_version}`")
    lines.append(f"- decision: **{report.decision}**")
    lines.append(f"- source_reports: `{report.source_reports}`")
    lines.append(f"- primary_symbol: `{report.primary_symbol}`")
    lines.append(f"- companion_symbols: `{', '.join(report.companion_symbols)}`")
    lines.append(f"- interval: `{report.interval}`")
    lines.append(f"- strategy: `{report.strategy}`")
    lines.append(f"- approved_for_research_candidate: `{report.approved_for_research_candidate}`")
    lines.append(f"- approved_for_training_candidate: `{report.approved_for_training_candidate}`")
    lines.append(f"- approved_for_paper_candidate: `{report.approved_for_paper_candidate}`")
    lines.append(f"- approved_for_live_real: `{report.approved_for_live_real}`")
    lines.append(f"- reason_codes: `{list(report.reason_codes)}`")
    lines.append(f"- recommendation: {report.recommendation}")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    for key, value in report.guardrails.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Branch Summaries")
    lines.append("")
    lines.append("| symbol | latest | exploration | robustness | dry_run | refinement | terminal_block | sparse/outlier | best_phase | signals | mean_edge_bps | median_edge_bps | profit_factor | reasons |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|")
    for summary in (report.primary_summary, *report.companion_summaries):
        if summary is None:
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    summary.symbol,
                    summary.latest_decision,
                    str(summary.exploration_pass),
                    str(summary.robustness_pass),
                    str(summary.dry_run_pass),
                    str(summary.refinement_pass),
                    str(summary.terminal_block),
                    str(summary.sparse_or_outlier_block),
                    str(summary.best_phase or ""),
                    str(summary.best_signal_count),
                    f"{summary.best_mean_net_edge_bps:.6f}",
                    "" if summary.best_median_net_edge_bps is None else f"{summary.best_median_net_edge_bps:.6f}",
                    f"{summary.best_profit_factor:.6f}",
                    "`" + str(list(summary.reason_codes)) + "`",
                ]
            )
            + " |"
        )
    lines.append("")
    if report.combined_summary is not None:
        c = report.combined_summary
        lines.append("## Combined Branch Snapshot")
        lines.append("")
        lines.append(f"- symbols: `{', '.join(c.symbols)}`")
        lines.append(f"- signal_count: `{c.signal_count}`")
        lines.append(f"- weighted_mean_net_edge_bps: `{c.weighted_mean_net_edge_bps}`")
        lines.append(f"- worst_median_net_edge_bps: `{c.worst_median_net_edge_bps}`")
        lines.append(f"- min_profit_factor: `{c.min_profit_factor}`")
        lines.append(f"- all_have_exploration_pass: `{c.all_have_exploration_pass}`")
        lines.append(f"- dry_run_or_refinement_confirmed_count: `{c.dry_run_or_refinement_confirmed_count}`")
        lines.append("")
    lines.append("## Candidate Evidence")
    lines.append("")
    lines.append("| phase | symbol | interval | strategy | decision | signals | mean_edge_bps | median_edge_bps | profit_factor | reasons |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---|")
    for candidate in report.candidates:
        lines.append(
            f"| {candidate.source_phase} | {candidate.symbol} | {candidate.interval} | {candidate.strategy} | {candidate.decision} | "
            f"{candidate.signal_count} | {candidate.mean_net_edge_bps:.6f} | "
            f"{'' if candidate.median_net_edge_bps is None else f'{candidate.median_net_edge_bps:.6f}'} | "
            f"{candidate.profit_factor:.6f} | `{list(candidate.reason_codes)}` |"
        )
    lines.append("")
    if report.next_actions:
        lines.append("## Next Actions")
        lines.append("")
        for action in report.next_actions:
            lines.append(f"- {action}")
        lines.append("")
    lines.append("## Policy")
    lines.append("")
    lines.append(
        "This branch review never trains models, reloads models, mutates config, starts paper trading, or sends orders. "
        "A continuation decision is research-only; paper/live trading remains blocked."
    )
    return "\n".join(lines)


def write_report_markdown(report: FuturesBranchReviewReport, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(report), encoding="utf-8")
    return output
