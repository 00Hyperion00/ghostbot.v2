from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

FUTURES_BRANCH_CLOSURE_CONTRACT_VERSION = "4B.4.3.6.6.25H"
REPORT_PREFIX = "4B436625H_futures_branch_closure_evidence_pack"
DEFAULT_PRIMARY_SYMBOL = "BTCUSDT"
DEFAULT_COMPANION_SYMBOLS = ("ETHUSDT",)
DEFAULT_INTERVAL = "4h"
DEFAULT_STRATEGY = "funding_trend_exhaustion"

TERMINAL_BLOCK_REASON_CODES = {
    "NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED",
    "DRY_RUN_OOS_EDGE_LOW",
    "DRY_RUN_EXPECTED_EDGE_LOW",
    "DRY_RUN_PROFIT_FACTOR_LOW",
    "NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED",
    "REFINEMENT_MEAN_EDGE_LOW",
    "REFINEMENT_MEDIAN_EDGE_LOW",
    "REFINEMENT_OOS_EDGE_LOW",
    "REFINEMENT_PROFIT_FACTOR_LOW",
    "REFINEMENT_WALK_FORWARD_STABILITY_LOW",
    "REFINEMENT_WIN_RATE_LOW",
    "REFINEMENT_SIGNAL_COUNT_LOW",
    "REFINEMENT_TOP_WIN_DEPENDENCY_HIGH",
}


@dataclass(frozen=True)
class FuturesBranchClosureLimits:
    require_final_25f_closed_no_go: bool = True
    require_primary_terminal_block: bool = True
    require_companion_terminal_block: bool = True
    require_no_training_paper_live_approvals: bool = True
    primary_symbol: str = DEFAULT_PRIMARY_SYMBOL
    companion_symbols: tuple[str, ...] = DEFAULT_COMPANION_SYMBOLS
    interval: str = DEFAULT_INTERVAL
    strategy: str = DEFAULT_STRATEGY


@dataclass(frozen=True)
class EvidenceReportSummary:
    source_report: str
    phase: str
    report_type: str
    decision: str
    selected_symbol: str | None = None
    selected_interval: str | None = None
    selected_strategy: str | None = None
    signal_count: int | None = None
    mean_net_edge_bps: float | None = None
    median_net_edge_bps: float | None = None
    profit_factor: float | None = None
    reason_codes: list[str] = field(default_factory=list)
    approved_for_research_candidate: bool = False
    approved_for_training_candidate: bool = False
    approved_for_paper_candidate: bool = False
    approved_for_live_real: bool = False
    live_real_allowed: bool = False
    config_mutation_performed: bool = False
    order_actions_performed: bool = False
    reload_performed: bool = False


@dataclass(frozen=True)
class BranchClosureEvidencePack:
    contract_version: str
    phase: str
    report_type: str
    generated_at: str
    decision: str
    ok: bool
    hypothesis_id: str
    branch_name: str
    primary_symbol: str
    companion_symbols: list[str]
    interval: str
    strategy: str
    source_reports: int
    evidence_report_count: int
    final_25f_decision: str | None
    primary_terminal_block_count: int
    companion_terminal_block_count: int
    reason_codes: list[str]
    warnings: list[str]
    recommendation: str
    evidence_chain: list[dict[str, Any]]
    terminal_block_evidence: list[dict[str, Any]]
    next_hypothesis_backlog: list[str]
    guardrails: dict[str, Any]
    approved_for_research_candidate: bool = False
    approved_for_training_candidate: bool = False
    approved_for_paper_candidate: bool = False
    approved_for_live_real: bool = False
    live_real_allowed: bool = False
    post_requests_allowed: bool = False
    config_mutation_performed: bool = False
    order_actions_performed: bool = False
    reload_performed: bool = False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _phase_from_contract(report: Mapping[str, Any]) -> str:
    raw = str(report.get("contract_version") or report.get("phase") or "")
    for suffix in ("25H", "25G", "25F", "25E", "25D", "25C", "25B", "25A", "24N", "24M"):
        if suffix in raw:
            return suffix
    return raw.split(".")[-1] if raw else "UNKNOWN"


def _as_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _nested_get(mapping: Mapping[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping) or key not in current or current[key] is None:
            return default
        current = current[key]
    return current


def _metric_lookup(report: Mapping[str, Any], selected: Mapping[str, Any] | None, key: str, *aliases: str) -> Any:
    names = (key, *aliases)
    containers: list[Mapping[str, Any]] = []
    if selected:
        containers.append(selected)
        metrics = selected.get("metrics")
        if isinstance(metrics, Mapping):
            containers.append(metrics)
    candidate = report.get("candidate")
    if isinstance(candidate, Mapping):
        containers.append(candidate)
        metrics = candidate.get("metrics")
        if isinstance(metrics, Mapping):
            containers.append(metrics)
    containers.append(report)
    for container in containers:
        for name in names:
            if name in container and container[name] is not None:
                return container[name]
    return None


def _parse_selected_text(value: Any) -> tuple[str | None, str | None, str | None]:
    if not isinstance(value, str):
        return None, None, None
    parts = value.replace("`", "").split()
    if len(parts) >= 3:
        return parts[0].upper(), parts[1], parts[2]
    return None, None, None


def _selected_fields(report: Mapping[str, Any]) -> tuple[str | None, str | None, str | None]:
    selected = report.get("selected")
    text_symbol, text_interval, text_strategy = _parse_selected_text(selected)
    selected_map = selected if isinstance(selected, Mapping) else {}
    spec = report.get("candidate_spec") if isinstance(report.get("candidate_spec"), Mapping) else {}
    if not spec:
        spec = _nested_get(report, "candidate", "candidate_spec", default={})
    if not isinstance(spec, Mapping):
        spec = {}
    symbol = (
        report.get("selected_symbol")
        or report.get("symbol")
        or selected_map.get("symbol")
        or spec.get("symbol")
        or text_symbol
    )
    interval = (
        report.get("selected_interval")
        or report.get("interval")
        or selected_map.get("interval")
        or spec.get("interval")
        or text_interval
    )
    strategy = (
        report.get("selected_strategy")
        or report.get("strategy")
        or selected_map.get("strategy")
        or spec.get("strategy")
        or text_strategy
    )
    return (
        str(symbol).upper() if symbol else None,
        str(interval) if interval else None,
        str(strategy) if strategy else None,
    )


def summarize_report(source_report: str, report: Mapping[str, Any]) -> EvidenceReportSummary:
    selected = report.get("selected") if isinstance(report.get("selected"), Mapping) else None
    symbol, interval, strategy = _selected_fields(report)
    reason_codes = [str(item) for item in report.get("reason_codes", [])] if isinstance(report.get("reason_codes"), list) else []
    return EvidenceReportSummary(
        source_report=source_report,
        phase=_phase_from_contract(report),
        report_type=str(report.get("report_type") or "unknown"),
        decision=str(report.get("decision") or "UNKNOWN"),
        selected_symbol=symbol,
        selected_interval=interval,
        selected_strategy=strategy,
        signal_count=_safe_int(_metric_lookup(report, selected, "signal_count", "signals", "selected_signal_count")),
        mean_net_edge_bps=_safe_float(_metric_lookup(report, selected, "mean_net_edge_bps", "mean_edge_bps", "selected_mean_net_edge_bps")),
        median_net_edge_bps=_safe_float(_metric_lookup(report, selected, "median_net_edge_bps", "median_edge_bps", "selected_median_net_edge_bps")),
        profit_factor=_safe_float(_metric_lookup(report, selected, "profit_factor", "selected_profit_factor")),
        reason_codes=reason_codes,
        approved_for_research_candidate=_as_bool(report.get("approved_for_research_candidate")),
        approved_for_training_candidate=_as_bool(report.get("approved_for_training_candidate")),
        approved_for_paper_candidate=_as_bool(report.get("approved_for_paper_candidate")),
        approved_for_live_real=_as_bool(report.get("approved_for_live_real")),
        live_real_allowed=_as_bool(report.get("live_real_allowed")),
        config_mutation_performed=_as_bool(report.get("config_mutation_performed")),
        order_actions_performed=_as_bool(report.get("order_actions_performed")),
        reload_performed=_as_bool(report.get("reload_performed")),
    )


def _matches_branch(summary: EvidenceReportSummary, *, symbol: str, limits: FuturesBranchClosureLimits) -> bool:
    return (
        summary.selected_symbol == symbol
        and summary.selected_interval == limits.interval
        and summary.selected_strategy == limits.strategy
    )


def _is_terminal_block(summary: EvidenceReportSummary, *, symbol: str, limits: FuturesBranchClosureLimits) -> bool:
    if summary.phase not in {"25D", "25E"}:
        return False
    if summary.decision.upper() != "BLOCK":
        return False
    if not _matches_branch(summary, symbol=symbol, limits=limits):
        return False
    return bool(TERMINAL_BLOCK_REASON_CODES.intersection(set(summary.reason_codes))) or summary.phase in {"25D", "25E"}


def build_futures_branch_closure_evidence_pack(
    reports: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    hypothesis_id: str = "HYP-002",
    branch_name: str = "futures_funding_trend_exhaustion",
    limits: FuturesBranchClosureLimits | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    limits = limits or FuturesBranchClosureLimits()
    generated_at = generated_at or utc_now_iso()
    summaries = [summarize_report(source, report) for source, report in reports]
    final_25f = next(
        (
            summary
            for summary in sorted(summaries, key=lambda item: item.source_report, reverse=True)
            if summary.phase == "25F" and summary.decision == "BRANCH_CLOSED_NO_GO"
        ),
        None,
    )
    primary_blocks = [
        summary
        for summary in summaries
        if _is_terminal_block(summary, symbol=limits.primary_symbol, limits=limits)
    ]
    companion_symbols = set(limits.companion_symbols)
    companion_blocks = [
        summary
        for summary in summaries
        if summary.selected_symbol in companion_symbols
        and _is_terminal_block(summary, symbol=summary.selected_symbol or "", limits=limits)
    ]
    approvals = [
        summary
        for summary in summaries
        if summary.approved_for_training_candidate
        or summary.approved_for_paper_candidate
        or summary.approved_for_live_real
        or summary.live_real_allowed
        or summary.config_mutation_performed
        or summary.order_actions_performed
        or summary.reload_performed
    ]

    reason_codes: list[str] = []
    warnings: list[str] = []
    if final_25f:
        reason_codes.append("FINAL_25F_BRANCH_CLOSED_NO_GO")
    else:
        reason_codes.append("FINAL_25F_BRANCH_CLOSED_NO_GO_MISSING")
    if primary_blocks:
        reason_codes.append("PRIMARY_TERMINAL_AUDIT_BLOCK_CONFIRMED")
    else:
        reason_codes.append("PRIMARY_TERMINAL_AUDIT_BLOCK_MISSING")
    if companion_blocks:
        reason_codes.append("COMPANION_TERMINAL_AUDIT_BLOCK_CONFIRMED")
    else:
        reason_codes.append("COMPANION_TERMINAL_AUDIT_BLOCK_MISSING")
    if approvals:
        reason_codes.append("UNSAFE_APPROVAL_OR_MUTATION_DETECTED")
    else:
        reason_codes.append("NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED")

    closure_confirmed = final_25f is not None and primary_blocks and companion_blocks and not approvals
    closure_ready = final_25f is None and primary_blocks and companion_blocks and not approvals
    if closure_confirmed:
        decision = "FUTURES_BRANCH_CLOSURE_CONFIRMED"
        ok = True
        recommendation = (
            "HYP-002 funding_trend_exhaustion futures branch is closed no-go. "
            "Do not train, reload, start paper trading, or enable live trading. Restart only with a new pre-registered hypothesis."
        )
        reason_codes.insert(0, "HYPOTHESIS_BRANCH_CLOSED_NO_GO")
    elif closure_ready:
        decision = "FUTURES_BRANCH_CLOSURE_EVIDENCE_READY_BUT_FINAL_REVIEW_MISSING"
        ok = False
        recommendation = (
            "Primary and companion terminal blocks exist, but final 25F BRANCH_CLOSED_NO_GO was not found. "
            "Run 25F include-all before declaring closure."
        )
    else:
        decision = "FUTURES_BRANCH_CLOSURE_INCOMPLETE"
        ok = False
        recommendation = (
            "Closure evidence is incomplete. Do not train, reload, start paper trading, or enable live trading. "
            "Complete missing terminal audits or rerun final branch review."
        )

    terminal_evidence = [asdict(item) for item in [*primary_blocks, *companion_blocks]]
    next_backlog = [
        "Do not reuse funding_trend_exhaustion without a new pre-registered edge hypothesis and acceptance metrics.",
        "Prefer hypotheses with explicit OOS edge, median edge, walk-forward stability, and signal-count floors before ML retraining.",
        "Keep futures work observation-only until a future branch passes exploration, robustness, dry-run, refinement, and branch-review gates.",
    ]
    pack = BranchClosureEvidencePack(
        contract_version=FUTURES_BRANCH_CLOSURE_CONTRACT_VERSION,
        phase="25H",
        report_type="futures_branch_closure_evidence_pack",
        generated_at=generated_at,
        decision=decision,
        ok=ok,
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        primary_symbol=limits.primary_symbol,
        companion_symbols=list(limits.companion_symbols),
        interval=limits.interval,
        strategy=limits.strategy,
        source_reports=len(reports),
        evidence_report_count=len(summaries),
        final_25f_decision=final_25f.decision if final_25f else None,
        primary_terminal_block_count=len(primary_blocks),
        companion_terminal_block_count=len(companion_blocks),
        reason_codes=reason_codes,
        warnings=warnings,
        recommendation=recommendation,
        evidence_chain=[asdict(item) for item in summaries],
        terminal_block_evidence=terminal_evidence,
        next_hypothesis_backlog=next_backlog,
        guardrails={
            "observation_only": True,
            "market_data_requests_performed": False,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "training_allowed": False,
            "paper_allowed": False,
            "live_real_allowed": False,
            "backtest_pass_is_not_paper_permission": True,
            "paper_pass_is_not_live_permission": True,
        },
    )
    return asdict(pack)


def load_json_report(path: str | Path) -> tuple[str, dict[str, Any]]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Report JSON must contain an object: {path}")
    return str(path), payload


def discover_reports(reports_dir: str | Path, *, include_all: bool = False) -> list[Path]:
    reports_dir = Path(reports_dir)
    if not reports_dir.exists():
        return []
    patterns = [
        "4B436625B_futures_funding_open_interest_edge_exploration_*.json",
        "4B436625C_futures_candidate_robustness_audit_*.json",
        "4B436625D_futures_research_candidate_simulator_*.json",
        "4B436625E_futures_candidate_refinement_median_edge_recovery_*.json",
        "4B436625F_futures_hypothesis_branch_review_*.json",
        "4B436625G_futures_companion_candidate_audit_runner_*.json",
    ]
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(reports_dir.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
        paths.extend(matches if include_all else matches[:1])
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# 4B.4.3.6.6.25H Futures Branch Closure Evidence Pack",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- primary: `{report.get('primary_symbol')}` `{report.get('interval')}` `{report.get('strategy')}`",
        f"- companions: `{', '.join(report.get('companion_symbols') or [])}`",
        f"- source_reports: `{report.get('source_reports')}`",
        f"- final_25f_decision: `{report.get('final_25f_decision')}`",
        f"- primary_terminal_block_count: `{report.get('primary_terminal_block_count')}`",
        f"- companion_terminal_block_count: `{report.get('companion_terminal_block_count')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Terminal Block Evidence",
        "",
        "| phase | decision | symbol | interval | strategy | signals | mean_net_edge_bps | median_net_edge_bps | profit_factor | reasons | source |",
        "|---|---|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    terminal = report.get("terminal_block_evidence") or []
    if terminal:
        for item in terminal:
            lines.append(
                "| {phase} | {decision} | {symbol} | {interval} | {strategy} | {signals} | {mean} | {median} | {pf} | `{reasons}` | `{source}` |".format(
                    phase=item.get("phase"),
                    decision=item.get("decision"),
                    symbol=item.get("selected_symbol"),
                    interval=item.get("selected_interval"),
                    strategy=item.get("selected_strategy"),
                    signals=item.get("signal_count"),
                    mean=item.get("mean_net_edge_bps"),
                    median=item.get("median_net_edge_bps"),
                    pf=item.get("profit_factor"),
                    reasons=item.get("reason_codes"),
                    source=Path(str(item.get("source_report") or "")).name,
                )
            )
    else:
        lines.append("| - | - | - | - | - | - | - | - | - | - | - |")
    lines.extend([
        "",
        "## Evidence Chain",
        "",
        "| phase | decision | symbol | strategy | training | paper | live | source |",
        "|---|---|---|---|---:|---:|---:|---|",
    ])
    for item in report.get("evidence_chain") or []:
        lines.append(
            "| {phase} | {decision} | {symbol} | {strategy} | {training} | {paper} | {live} | `{source}` |".format(
                phase=item.get("phase"),
                decision=item.get("decision"),
                symbol=item.get("selected_symbol"),
                strategy=item.get("selected_strategy"),
                training=item.get("approved_for_training_candidate"),
                paper=item.get("approved_for_paper_candidate"),
                live=item.get("approved_for_live_real"),
                source=Path(str(item.get("source_report") or "")).name,
            )
        )
    lines.extend([
        "",
        "## Next Hypothesis Backlog",
        "",
    ])
    for item in report.get("next_hypothesis_backlog") or []:
        lines.append(f"- {item}")
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
        "- training_allowed: `False`",
        "- paper_allowed: `False`",
        "- live_real_allowed: `False`",
        "",
        "## Policy",
        "",
        "This evidence pack closes the branch only at the research-record level. It never fetches market data, trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.",
    ])
    return "\n".join(lines) + "\n"


def write_report_bundle(report: Mapping[str, Any], *, out_dir: str | Path) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json(json_path, report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path
