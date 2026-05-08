from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FUTURES_COMPANION_AUDIT_CONTRACT_VERSION = "4B.4.3.6.6.25G"
REPORT_PREFIX = "4B436625G_futures_companion_candidate_audit_runner"
DEFAULT_PRIMARY_SYMBOL = "BTCUSDT"
DEFAULT_COMPANION_SYMBOLS = ("ETHUSDT",)
DEFAULT_INTERVAL = "4h"
DEFAULT_STRATEGY = "funding_trend_exhaustion"

NEXT_REQUIRED_TOOLS = (
    "tools/run_futures_research_candidate_simulator_4B436625D.py",
    "tools/run_futures_candidate_refinement_median_edge_recovery_4B436625E.py",
)


@dataclass(frozen=True)
class FuturesCompanionAuditLimits:
    min_exploration_signal_count: int = 20
    min_combined_signal_count: int = 60
    min_mean_net_edge_bps: float = 0.0
    min_profit_factor: float = 1.15
    require_companion_candidate: bool = True
    require_downstream_audit_before_continue: bool = True


@dataclass(frozen=True)
class CompanionCandidateSummary:
    symbol: str
    interval: str
    strategy: str
    decision: str
    signal_count: int
    mean_net_edge_bps: float
    median_net_edge_bps: float
    profit_factor: float
    source_phase: str
    source_report: str
    role: str
    warnings: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FuturesCompanionCandidateSpec:
    contract_version: str
    generated_at: str
    source_phase: str
    candidate_role: str
    symbol: str
    interval: str
    strategy: str
    source_report: str
    cost_bps: float = 16.0
    slippage_bps: float = 4.0
    holding_bars: int = 1
    days: int = 90
    base_url: str = "https://fapi.binance.com"
    approved_for_training_candidate: bool = False
    approved_for_paper_candidate: bool = False
    approved_for_live_real: bool = False
    live_real_allowed: bool = False
    post_requests_allowed: bool = False
    config_mutation_performed: bool = False
    order_actions_performed: bool = False
    reload_performed: bool = False


@dataclass(frozen=True)
class DownstreamAuditCommand:
    phase: str
    description: str
    command: str


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


def _phase_from_contract(value: str | None) -> str:
    if not value:
        return "UNKNOWN"
    for suffix in ("25B", "25C", "25D", "25E", "25F", "25G"):
        if suffix in value:
            return suffix
    return value.split(".")[-1] if "." in value else value


def _normalise_candidate(raw: Mapping[str, Any], *, report: Mapping[str, Any], report_path: str, role: str) -> CompanionCandidateSummary:
    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), Mapping) else {}
    return CompanionCandidateSummary(
        symbol=str(raw.get("symbol") or raw.get("selected_symbol") or metrics.get("symbol") or report.get("selected_symbol") or ""),
        interval=str(raw.get("interval") or raw.get("selected_interval") or metrics.get("interval") or report.get("selected_interval") or ""),
        strategy=str(raw.get("strategy") or raw.get("selected_strategy") or metrics.get("strategy") or report.get("selected_strategy") or ""),
        decision=str(raw.get("decision") or raw.get("status") or report.get("decision") or "UNKNOWN"),
        signal_count=_safe_int(raw.get("signals", raw.get("signal_count", metrics.get("signal_count", 0))), 0),
        mean_net_edge_bps=_safe_float(raw.get("mean_edge_bps", raw.get("mean_net_edge_bps", metrics.get("mean_net_edge_bps", 0.0))), 0.0),
        median_net_edge_bps=_safe_float(raw.get("median_edge_bps", raw.get("median_net_edge_bps", metrics.get("median_net_edge_bps", 0.0))), 0.0),
        profit_factor=_safe_float(raw.get("profit_factor", metrics.get("profit_factor", 0.0)), 0.0),
        source_phase=_phase_from_contract(str(report.get("contract_version") or report.get("phase") or "")),
        source_report=report_path,
        role=role,
        warnings=[str(item) for item in raw.get("warnings", [])] if isinstance(raw.get("warnings"), list) else [],
        reason_codes=[str(item) for item in raw.get("reasons", raw.get("reason_codes", []))] if isinstance(raw.get("reasons", raw.get("reason_codes", [])), list) else [],
    )


def _selected_from_report(report: Mapping[str, Any], report_path: str, role: str) -> CompanionCandidateSummary | None:
    selected = report.get("selected")
    if isinstance(selected, Mapping):
        return _normalise_candidate(selected, report=report, report_path=report_path, role=role)
    symbol = report.get("selected_symbol")
    interval = report.get("selected_interval")
    strategy = report.get("selected_strategy")
    if not (symbol or interval or strategy):
        selected_text = str(report.get("selected") or "")
        parts = selected_text.split()
        if len(parts) >= 3:
            symbol, interval, strategy = parts[0], parts[1], parts[2]
    if symbol and interval and strategy:
        return CompanionCandidateSummary(
            symbol=str(symbol),
            interval=str(interval),
            strategy=str(strategy),
            decision=str(report.get("decision") or "UNKNOWN"),
            signal_count=_safe_int(report.get("selected_signal_count", report.get("signal_count", 0))),
            mean_net_edge_bps=_safe_float(report.get("selected_mean_net_edge_bps", report.get("mean_net_edge_bps", 0.0))),
            median_net_edge_bps=_safe_float(report.get("selected_median_net_edge_bps", report.get("median_net_edge_bps", 0.0))),
            profit_factor=_safe_float(report.get("selected_profit_factor", report.get("profit_factor", 0.0))),
            source_phase=_phase_from_contract(str(report.get("contract_version") or report.get("phase") or "")),
            source_report=report_path,
            role=role,
            warnings=[str(item) for item in report.get("warnings", [])] if isinstance(report.get("warnings"), list) else [],
            reason_codes=[str(item) for item in report.get("reason_codes", [])] if isinstance(report.get("reason_codes"), list) else [],
        )
    return None


def extract_candidates_from_reports(reports: Sequence[tuple[str, Mapping[str, Any]]], *, strategy: str = DEFAULT_STRATEGY) -> list[CompanionCandidateSummary]:
    candidates: list[CompanionCandidateSummary] = []
    for report_path, report in reports:
        raw_candidates = report.get("candidates")
        if isinstance(raw_candidates, list):
            for raw in raw_candidates:
                if isinstance(raw, Mapping):
                    summary = _normalise_candidate(raw, report=report, report_path=report_path, role="candidate")
                    if summary.strategy == strategy:
                        candidates.append(summary)
        selected = _selected_from_report(report, report_path, role="selected")
        if selected and selected.strategy == strategy:
            candidates.append(selected)
    # Deduplicate same source/symbol/interval/strategy/phase/decision.
    seen: set[tuple[str, str, str, str, str, str]] = set()
    deduped: list[CompanionCandidateSummary] = []
    for candidate in candidates:
        key = (candidate.source_report, candidate.symbol, candidate.interval, candidate.strategy, candidate.source_phase, candidate.decision)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _is_exploration_pass(candidate: CompanionCandidateSummary, limits: FuturesCompanionAuditLimits) -> bool:
    return (
        candidate.decision.upper() == "PASS"
        and candidate.signal_count >= limits.min_exploration_signal_count
        and candidate.mean_net_edge_bps > limits.min_mean_net_edge_bps
        and candidate.profit_factor >= limits.min_profit_factor
    )


def select_primary_and_companion(
    candidates: Sequence[CompanionCandidateSummary],
    *,
    primary_symbol: str = DEFAULT_PRIMARY_SYMBOL,
    companion_symbols: Sequence[str] = DEFAULT_COMPANION_SYMBOLS,
    interval: str = DEFAULT_INTERVAL,
    strategy: str = DEFAULT_STRATEGY,
    limits: FuturesCompanionAuditLimits | None = None,
) -> tuple[CompanionCandidateSummary | None, CompanionCandidateSummary | None, list[CompanionCandidateSummary]]:
    limits = limits or FuturesCompanionAuditLimits()
    eligible = [
        candidate
        for candidate in candidates
        if candidate.interval == interval and candidate.strategy == strategy and _is_exploration_pass(candidate, limits)
    ]
    primary = next((candidate for candidate in eligible if candidate.symbol == primary_symbol), None)
    companions = [candidate for candidate in eligible if candidate.symbol in set(companion_symbols)]
    companions.sort(key=lambda item: (item.mean_net_edge_bps, item.profit_factor, item.signal_count), reverse=True)
    return primary, (companions[0] if companions else None), eligible


def build_companion_spec(
    companion: CompanionCandidateSummary,
    *,
    days: int = 90,
    base_url: str = "https://fapi.binance.com",
    generated_at: str | None = None,
) -> FuturesCompanionCandidateSpec:
    return FuturesCompanionCandidateSpec(
        contract_version=FUTURES_COMPANION_AUDIT_CONTRACT_VERSION,
        generated_at=generated_at or utc_now_iso(),
        source_phase=companion.source_phase,
        candidate_role="companion",
        symbol=companion.symbol,
        interval=companion.interval,
        strategy=companion.strategy,
        source_report=companion.source_report,
        days=days,
        base_url=base_url,
    )


def build_downstream_commands(spec_path: str, *, out_dir: str = "reports", days: int = 90, base_url: str = "https://fapi.binance.com") -> list[DownstreamAuditCommand]:
    quoted_spec = spec_path.replace("/", "\\")
    return [
        DownstreamAuditCommand(
            phase="25D",
            description="Run companion dry-run signal simulator without orders.",
            command=(
                "python tools/run_futures_research_candidate_simulator_4B436625D.py `\n"
                f"  --spec-json {quoted_spec} `\n"
                f"  --days {days} `\n"
                f"  --base-url {base_url} `\n"
                f"  --out-dir {out_dir} `\n"
                "  --review-ok"
            ),
        ),
        DownstreamAuditCommand(
            phase="25E",
            description="Run companion median-edge refinement without orders.",
            command=(
                "python tools/run_futures_candidate_refinement_median_edge_recovery_4B436625E.py `\n"
                f"  --spec-json {quoted_spec} `\n"
                f"  --days {days} `\n"
                f"  --base-url {base_url} `\n"
                f"  --out-dir {out_dir} `\n"
                "  --review-ok"
            ),
        ),
    ]


def _downstream_confirmed(reports: Sequence[tuple[str, Mapping[str, Any]]], companion: CompanionCandidateSummary | None) -> tuple[int, list[str]]:
    if not companion:
        return 0, []
    confirmed: list[str] = []
    for report_path, report in reports:
        phase = _phase_from_contract(str(report.get("contract_version") or report.get("phase") or ""))
        if phase not in {"25D", "25E"}:
            continue
        selected = _selected_from_report(report, report_path, role="selected")
        if not selected:
            continue
        if selected.symbol == companion.symbol and selected.interval == companion.interval and selected.strategy == companion.strategy:
            if str(report.get("decision") or "").upper() == "PASS" or bool(report.get("approved_for_research_candidate")):
                confirmed.append(f"{phase}:{Path(report_path).name}")
    return len(confirmed), confirmed


def build_futures_companion_candidate_audit_runner(
    reports: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    primary_symbol: str = DEFAULT_PRIMARY_SYMBOL,
    companion_symbols: Sequence[str] = DEFAULT_COMPANION_SYMBOLS,
    interval: str = DEFAULT_INTERVAL,
    strategy: str = DEFAULT_STRATEGY,
    days: int = 90,
    base_url: str = "https://fapi.binance.com",
    out_dir: str = "reports",
    spec_path: str | None = None,
    generated_at: str | None = None,
    limits: FuturesCompanionAuditLimits | None = None,
) -> dict[str, Any]:
    limits = limits or FuturesCompanionAuditLimits()
    generated_at = generated_at or utc_now_iso()
    candidates = extract_candidates_from_reports(reports, strategy=strategy)
    primary, companion, eligible = select_primary_and_companion(
        candidates,
        primary_symbol=primary_symbol,
        companion_symbols=companion_symbols,
        interval=interval,
        strategy=strategy,
        limits=limits,
    )

    reason_codes: list[str] = []
    warnings: list[str] = []
    companion_spec: FuturesCompanionCandidateSpec | None = None
    downstream_commands: list[DownstreamAuditCommand] = []
    confirmed_count, confirmed_reports = _downstream_confirmed(reports, companion)

    if primary is None:
        reason_codes.append("PRIMARY_EXPLORATION_CANDIDATE_MISSING")
    if companion is None:
        reason_codes.append("COMPANION_EXPLORATION_CANDIDATE_MISSING")
    if primary and companion and primary.signal_count + companion.signal_count < limits.min_combined_signal_count:
        reason_codes.append("COMBINED_SIGNAL_COUNT_LOW")
    if companion is not None:
        companion_spec = build_companion_spec(companion, days=days, base_url=base_url, generated_at=generated_at)
        spec_path = spec_path or str(Path(out_dir) / f"4B436625G_companion_spec_{companion.symbol}_{companion.interval}_{companion.strategy}.json")
        downstream_commands = build_downstream_commands(spec_path, out_dir=out_dir, days=days, base_url=base_url)
    if companion is not None and confirmed_count <= 0:
        reason_codes.append("COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED")
        reason_codes.append("COMPANION_SPEC_READY")

    if companion is None:
        decision = "COMPANION_AUDIT_BLOCKED"
        ok = False
        recommendation = "No companion exploration candidate was found. Keep branch blocked; do not train, paper trade, or enable live trading."
    elif confirmed_count > 0:
        decision = "COMPANION_AUDIT_CONFIRMED"
        ok = True
        recommendation = "Companion downstream audit evidence exists. Continue only with the next explicit research gate; paper/live remain blocked."
    else:
        decision = "COMPANION_AUDIT_READY"
        ok = True
        recommendation = "Companion exploration candidate is ready for 25D/25E audit. Run the generated commands; paper/live remain blocked."

    approved_for_research_candidate = decision == "COMPANION_AUDIT_CONFIRMED"
    report: dict[str, Any] = {
        "contract_version": FUTURES_COMPANION_AUDIT_CONTRACT_VERSION,
        "phase": "25G",
        "report_type": "futures_companion_candidate_audit_runner",
        "generated_at": generated_at,
        "decision": decision,
        "ok": ok,
        "source_reports": len(reports),
        "candidate_count": len(candidates),
        "eligible_exploration_candidates": [asdict(item) for item in eligible],
        "primary": asdict(primary) if primary else None,
        "companion": asdict(companion) if companion else None,
        "combined_signals": (primary.signal_count if primary else 0) + (companion.signal_count if companion else 0),
        "downstream_confirmed_count": confirmed_count,
        "downstream_confirmed_reports": confirmed_reports,
        "companion_spec": asdict(companion_spec) if companion_spec else None,
        "companion_spec_path": spec_path if companion_spec else None,
        "downstream_commands": [asdict(item) for item in downstream_commands],
        "reason_codes": reason_codes,
        "warnings": warnings,
        "recommendation": recommendation,
        "limits": asdict(limits),
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
        "approved_for_research_candidate": approved_for_research_candidate,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
    }
    return report


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
    ]
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(reports_dir.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
        paths.extend(matches if include_all else matches[:1])
    # Stable de-dup while preserving order.
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
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")
    return path


def render_markdown(report: Mapping[str, Any]) -> str:
    primary = report.get("primary") or {}
    companion = report.get("companion") or {}
    commands = report.get("downstream_commands") or []
    lines = [
        "# 4B.4.3.6.6.25G Futures Companion Candidate Audit Runner",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- source_reports: `{report.get('source_reports')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- combined_signals: `{report.get('combined_signals')}`",
        f"- downstream_confirmed_count: `{report.get('downstream_confirmed_count')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Primary",
        "",
        f"- symbol: `{primary.get('symbol')}`",
        f"- interval: `{primary.get('interval')}`",
        f"- strategy: `{primary.get('strategy')}`",
        f"- signal_count: `{primary.get('signal_count')}`",
        f"- mean_net_edge_bps: `{primary.get('mean_net_edge_bps')}`",
        f"- profit_factor: `{primary.get('profit_factor')}`",
        "",
        "## Companion",
        "",
        f"- symbol: `{companion.get('symbol')}`",
        f"- interval: `{companion.get('interval')}`",
        f"- strategy: `{companion.get('strategy')}`",
        f"- signal_count: `{companion.get('signal_count')}`",
        f"- mean_net_edge_bps: `{companion.get('mean_net_edge_bps')}`",
        f"- profit_factor: `{companion.get('profit_factor')}`",
        f"- companion_spec_path: `{report.get('companion_spec_path')}`",
        "",
        "## Next Commands",
        "",
    ]
    if commands:
        for command in commands:
            lines.append(f"### {command.get('phase')} — {command.get('description')}")
            lines.append("")
            lines.append("```powershell")
            lines.append(str(command.get("command") or ""))
            lines.append("```")
            lines.append("")
    else:
        lines.append("No downstream commands generated.")
        lines.append("")
    lines.extend([
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
        "This runner only prepares companion audit specs and downstream no-order commands. It never fetches market data, trains models, reloads models, mutates config, starts paper trading, or sends orders.",
    ])
    return "\n".join(lines) + "\n"


def write_report_bundle(report: Mapping[str, Any], *, out_dir: str | Path, generated_at: str | None = None) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S") if generated_at is None else generated_at.replace(":", "").replace("-", "").replace("T", "_").replace("+0000", "")
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json(json_path, report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path
