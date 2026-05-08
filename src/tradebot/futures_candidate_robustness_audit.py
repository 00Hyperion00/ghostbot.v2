"""4B.4.3.6.6.25C futures candidate robustness / data coverage audit.

This module audits 25B futures funding/open-interest edge exploration reports.
It never trains models, mutates runtime config, reloads models, or sends orders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json
import math
import statistics

FUTURES_CANDIDATE_ROBUSTNESS_CONTRACT_VERSION = "4B.4.3.6.6.25C"
REPORT_PREFIX = "4B436625C_futures_candidate_robustness_audit"

NO_FUTURES_ROBUSTNESS_CANDIDATE_PASSED = "NO_FUTURES_ROBUSTNESS_CANDIDATE_PASSED"
ROBUSTNESS_CANDIDATE_CONFIRMED = "ROBUSTNESS_CANDIDATE_CONFIRMED"
NEXT_PHASE_RECOMMENDATION = "25D_FUTURES_RESEARCH_CANDIDATE_SPEC_AND_DRY_RUN_SIGNAL_SIMULATOR"


@dataclass(frozen=True)
class FuturesRobustnessLimits:
    min_signal_count: int = 30
    min_signal_coverage_pct: float = 0.5
    max_signal_coverage_pct: float = 15.0
    min_mean_net_edge_bps: float = 5.0
    min_median_net_edge_bps: float = 0.0
    min_win_rate_pct: float = 50.0
    min_profit_factor: float = 1.15
    max_drawdown_pct: float = 25.0
    min_oos_edge_bps: float = 0.0
    min_positive_window_count: int = 1
    min_positive_window_rate_pct: float = 50.0
    min_cross_symbol_pass_count: int = 1
    min_funding_coverage_pct: float = 50.0
    min_open_interest_coverage_pct: float = 40.0
    min_long_short_coverage_pct: float = 40.0
    min_taker_coverage_pct: float = 40.0
    max_top_trade_contribution_pct: float = 55.0
    max_top_3_trade_contribution_pct: float = 80.0


@dataclass
class FuturesCandidateAudit:
    key: str
    symbol: str
    interval: str
    strategy: str
    decision: str
    score: float
    signal_count: int
    coverage_pct: float
    mean_net_edge_bps: float
    median_net_edge_bps: float
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    oos_edge_bps: float
    source_report_count: int
    pass_window_count: int
    positive_edge_window_count: int
    positive_window_rate_pct: float
    cross_symbol_pass_count: int
    edge_window_mean_bps: float
    edge_window_median_bps: float
    funding_data_coverage_pct: float | None
    open_interest_data_coverage_pct: float | None
    long_short_data_coverage_pct: float | None
    taker_data_coverage_pct: float | None
    outlier_top_trade_contribution_pct: float | None
    outlier_top_3_trade_contribution_pct: float | None
    reason_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    approved_for_research_candidate: bool = False
    approved_for_training_candidate: bool = False
    approved_for_paper_candidate: bool = False
    approved_for_live_real: bool = False


@dataclass
class FuturesRobustnessReport:
    contract_version: str
    phase: str
    report_type: str
    decision: str
    ok: bool
    source_reports: int
    candidate_count: int
    selected_key: str | None
    selected_symbol: str | None
    selected_interval: str | None
    selected_strategy: str | None
    selected_mean_net_edge_bps: float | None
    selected_profit_factor: float | None
    selected_signal_count: int | None
    selected_positive_window_rate_pct: float | None
    approved_for_research_candidate: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    live_real_allowed: bool
    observation_only: bool
    get_only_public_futures_data: bool
    post_requests_allowed: bool
    config_mutation_performed: bool
    order_actions_performed: bool
    reload_performed: bool
    reason_codes: list[str]
    warnings: list[str]
    recommendation: str
    selected_candidate: dict[str, Any] | None
    candidates: list[dict[str, Any]]
    limits: dict[str, Any]
    next_phase: str


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _first(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    metrics = mapping.get("metrics")
    if isinstance(metrics, Mapping):
        for key in keys:
            if key in metrics and metrics[key] is not None:
                return metrics[key]
    return default


def _reason_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, Sequence) and not isinstance(raw, (bytes, bytearray, str)):
        return [str(item) for item in raw]
    return [str(raw)]


def _candidate_key(symbol: str, interval: str, strategy: str) -> str:
    return f"{symbol.upper()}::{interval}::{strategy}"


def load_json_reports(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Input report not found: {p}")
        with p.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, Mapping):
            reports.append(dict(payload))
    return reports


def discover_25b_reports(reports_dir: str | Path) -> list[Path]:
    root = Path(reports_dir)
    if not root.exists():
        return []
    return sorted(root.glob("4B436625B_futures_funding_open_interest_edge_exploration_*.json"))


def normalize_candidate(candidate: Mapping[str, Any], source_index: int = 0) -> dict[str, Any]:
    symbol = str(_first(candidate, "symbol", default="")).upper()
    interval = str(_first(candidate, "interval", default=""))
    strategy = str(_first(candidate, "strategy", "strategy_name", default=""))
    if not symbol or not interval or not strategy:
        spec = candidate.get("spec") or candidate.get("candidate_spec") or {}
        if isinstance(spec, Mapping):
            symbol = symbol or str(spec.get("symbol", "")).upper()
            interval = interval or str(spec.get("interval", ""))
            strategy = strategy or str(spec.get("strategy", spec.get("name", "")))
    decision = str(_first(candidate, "decision", default="BLOCK")).upper()
    signals = _safe_int(_first(candidate, "signals", "signal_count", default=0))
    coverage = _safe_float(_first(candidate, "coverage_pct", "signal_coverage_pct", default=0.0))
    mean_edge = _safe_float(_first(candidate, "mean_edge_bps", "mean_net_edge_bps", default=0.0))
    median_edge = _safe_float(_first(candidate, "median_edge_bps", "median_net_edge_bps", default=0.0))
    win_rate = _safe_float(_first(candidate, "win_rate_pct", default=0.0))
    profit_factor = _safe_float(_first(candidate, "profit_factor", default=0.0))
    max_dd = _safe_float(_first(candidate, "max_dd_pct", "max_drawdown_pct", default=0.0))
    oos_edge = _safe_float(_first(candidate, "oos_edge_bps", "oos_mean_net_edge_bps", default=0.0))
    score = _safe_float(_first(candidate, "score", default=0.0))
    normalized = {
        "source_index": source_index,
        "key": _candidate_key(symbol, interval, strategy),
        "symbol": symbol,
        "interval": interval,
        "strategy": strategy,
        "decision": decision,
        "score": score,
        "signal_count": signals,
        "coverage_pct": coverage,
        "mean_net_edge_bps": mean_edge,
        "median_net_edge_bps": median_edge,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_dd,
        "oos_edge_bps": oos_edge,
        "funding_data_coverage_pct": _optional_float(candidate, "funding_data_coverage_pct", "funding_coverage_pct"),
        "open_interest_data_coverage_pct": _optional_float(candidate, "open_interest_data_coverage_pct", "open_interest_coverage_pct", "oi_coverage_pct"),
        "long_short_data_coverage_pct": _optional_float(candidate, "long_short_data_coverage_pct", "long_short_coverage_pct"),
        "taker_data_coverage_pct": _optional_float(candidate, "taker_data_coverage_pct", "taker_coverage_pct"),
        "outlier_top_trade_contribution_pct": _optional_float(candidate, "outlier_top_trade_contribution_pct", "top_trade_contribution_pct"),
        "outlier_top_3_trade_contribution_pct": _optional_float(candidate, "outlier_top_3_trade_contribution_pct", "top_3_trade_contribution_pct"),
        "reason_codes": _reason_list(_first(candidate, "reason_codes", "reasons", default=[])),
        "warnings": _reason_list(_first(candidate, "warnings", default=[])),
        "raw": dict(candidate),
    }
    return normalized


def _optional_float(mapping: Mapping[str, Any], *keys: str) -> float | None:
    value = _first(mapping, *keys, default=None)
    if value is None:
        return None
    return _safe_float(value, default=0.0)


def extract_candidates(reports: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, report in enumerate(reports):
        raw_candidates = report.get("candidates")
        if isinstance(raw_candidates, Sequence) and not isinstance(raw_candidates, (str, bytes, bytearray)):
            for item in raw_candidates:
                if isinstance(item, Mapping):
                    normalized = normalize_candidate(item, source_index=idx)
                    if normalized["symbol"] and normalized["interval"] and normalized["strategy"]:
                        out.append(normalized)
        # Fallback for compact reports without candidates table.
        if not raw_candidates and report.get("selected"):
            selected = report.get("selected")
            if isinstance(selected, Mapping):
                out.append(normalize_candidate(selected, source_index=idx))
    return out


def _mean(values: Sequence[float]) -> float:
    return float(statistics.fmean(values)) if values else 0.0


def _median(values: Sequence[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def audit_candidate_group(key: str, group: Sequence[dict[str, Any]], all_candidates: Sequence[dict[str, Any]], limits: FuturesRobustnessLimits) -> FuturesCandidateAudit:
    # Prefer PASS candidate with highest score, otherwise best score.
    ordered = sorted(group, key=lambda c: (c["decision"] == "PASS", c["score"], c["mean_net_edge_bps"]), reverse=True)
    primary = ordered[0]
    pass_count = sum(1 for c in group if c["decision"] == "PASS")
    positive_edge_count = sum(1 for c in group if c["mean_net_edge_bps"] > 0.0 and c["profit_factor"] > 1.0)
    edge_values = [float(c["mean_net_edge_bps"]) for c in group]
    symbol = primary["symbol"]
    interval = primary["interval"]
    strategy = primary["strategy"]
    cross_symbol_pass = {
        c["symbol"]
        for c in all_candidates
        if c["strategy"] == strategy and c["interval"] == interval and c["decision"] == "PASS"
    }
    warnings = list(primary.get("warnings", []))
    reasons: list[str] = []

    def add_reason(cond: bool, code: str) -> None:
        if cond and code not in reasons:
            reasons.append(code)

    def add_warning(cond: bool, code: str) -> None:
        if cond and code not in warnings:
            warnings.append(code)

    signal_count = int(primary["signal_count"])
    coverage = float(primary["coverage_pct"])
    mean_edge = float(primary["mean_net_edge_bps"])
    median_edge = float(primary["median_net_edge_bps"])
    win_rate = float(primary["win_rate_pct"])
    profit_factor = float(primary["profit_factor"])
    max_dd = float(primary["max_drawdown_pct"])
    oos_edge = float(primary["oos_edge_bps"])
    positive_rate = (positive_edge_count / max(1, len(group))) * 100.0

    add_reason(signal_count < limits.min_signal_count, "ROBUSTNESS_SIGNAL_COUNT_LOW")
    add_reason(coverage < limits.min_signal_coverage_pct, "ROBUSTNESS_COVERAGE_LOW")
    add_reason(coverage > limits.max_signal_coverage_pct, "ROBUSTNESS_COVERAGE_HIGH")
    add_reason(mean_edge < limits.min_mean_net_edge_bps, "ROBUSTNESS_EXPECTED_EDGE_LOW")
    add_reason(median_edge < limits.min_median_net_edge_bps, "ROBUSTNESS_MEDIAN_EDGE_LOW")
    add_reason(win_rate < limits.min_win_rate_pct, "ROBUSTNESS_WIN_RATE_LOW")
    add_reason(profit_factor < limits.min_profit_factor, "ROBUSTNESS_PROFIT_FACTOR_LOW")
    add_reason(max_dd > limits.max_drawdown_pct, "ROBUSTNESS_MAX_DRAWDOWN_HIGH")
    add_reason(oos_edge < limits.min_oos_edge_bps, "ROBUSTNESS_OOS_EDGE_LOW")
    add_reason(positive_edge_count < limits.min_positive_window_count, "ROBUSTNESS_POSITIVE_WINDOW_COUNT_LOW")
    add_reason(positive_rate < limits.min_positive_window_rate_pct, "ROBUSTNESS_POSITIVE_WINDOW_RATE_LOW")
    add_reason(len(cross_symbol_pass) < limits.min_cross_symbol_pass_count, "ROBUSTNESS_CROSS_SYMBOL_CONFIRMATION_LOW")

    funding_cov = primary.get("funding_data_coverage_pct")
    oi_cov = primary.get("open_interest_data_coverage_pct")
    ls_cov = primary.get("long_short_data_coverage_pct")
    taker_cov = primary.get("taker_data_coverage_pct")
    add_warning(funding_cov is None, "FUNDING_COVERAGE_DETAIL_UNAVAILABLE")
    add_warning(oi_cov is None, "OPEN_INTEREST_COVERAGE_DETAIL_UNAVAILABLE")
    add_warning(ls_cov is None, "LONG_SHORT_COVERAGE_DETAIL_UNAVAILABLE")
    add_warning(taker_cov is None, "TAKER_COVERAGE_DETAIL_UNAVAILABLE")
    add_reason(funding_cov is not None and funding_cov < limits.min_funding_coverage_pct, "FUNDING_DATA_COVERAGE_LOW")
    add_reason(oi_cov is not None and oi_cov < limits.min_open_interest_coverage_pct, "OPEN_INTEREST_DATA_COVERAGE_LOW")
    add_reason(ls_cov is not None and ls_cov < limits.min_long_short_coverage_pct, "LONG_SHORT_DATA_COVERAGE_LOW")
    add_reason(taker_cov is not None and taker_cov < limits.min_taker_coverage_pct, "TAKER_DATA_COVERAGE_LOW")

    top_trade = primary.get("outlier_top_trade_contribution_pct")
    top3_trade = primary.get("outlier_top_3_trade_contribution_pct")
    add_warning(top_trade is None, "OUTLIER_DEPENDENCY_DETAIL_UNAVAILABLE")
    add_reason(top_trade is not None and top_trade > limits.max_top_trade_contribution_pct, "OUTLIER_TOP_TRADE_DEPENDENCY_HIGH")
    add_reason(top3_trade is not None and top3_trade > limits.max_top_3_trade_contribution_pct, "OUTLIER_TOP_3_TRADE_DEPENDENCY_HIGH")

    approved = not reasons
    return FuturesCandidateAudit(
        key=key,
        symbol=symbol,
        interval=interval,
        strategy=strategy,
        decision="PASS" if approved else "BLOCK",
        score=float(primary["score"]),
        signal_count=signal_count,
        coverage_pct=round(coverage, 6),
        mean_net_edge_bps=round(mean_edge, 6),
        median_net_edge_bps=round(median_edge, 6),
        win_rate_pct=round(win_rate, 6),
        profit_factor=round(profit_factor, 6),
        max_drawdown_pct=round(max_dd, 6),
        oos_edge_bps=round(oos_edge, 6),
        source_report_count=len(group),
        pass_window_count=pass_count,
        positive_edge_window_count=positive_edge_count,
        positive_window_rate_pct=round(positive_rate, 6),
        cross_symbol_pass_count=len(cross_symbol_pass),
        edge_window_mean_bps=round(_mean(edge_values), 6),
        edge_window_median_bps=round(_median(edge_values), 6),
        funding_data_coverage_pct=funding_cov,
        open_interest_data_coverage_pct=oi_cov,
        long_short_data_coverage_pct=ls_cov,
        taker_data_coverage_pct=taker_cov,
        outlier_top_trade_contribution_pct=top_trade,
        outlier_top_3_trade_contribution_pct=top3_trade,
        reason_codes=reasons,
        warnings=warnings,
        approved_for_research_candidate=approved,
    )


def build_futures_candidate_robustness_audit(reports: Sequence[Mapping[str, Any]], limits: FuturesRobustnessLimits | None = None) -> FuturesRobustnessReport:
    active_limits = limits or FuturesRobustnessLimits()
    candidates = extract_candidates(reports)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate["key"], []).append(candidate)

    audits = [audit_candidate_group(key, group, candidates, active_limits) for key, group in grouped.items()]
    audits.sort(
        key=lambda a: (
            a.approved_for_research_candidate,
            a.mean_net_edge_bps,
            a.profit_factor,
            a.signal_count,
        ),
        reverse=True,
    )
    selected = audits[0] if audits else None
    approved = bool(selected and selected.approved_for_research_candidate)
    reason_codes: list[str] = []
    warnings: list[str] = []
    if not candidates:
        reason_codes.append("NO_25B_CANDIDATES_FOUND")
    if not approved:
        reason_codes.append(NO_FUTURES_ROBUSTNESS_CANDIDATE_PASSED)
    if selected:
        reason_codes.extend(code for code in selected.reason_codes if code not in reason_codes)
        warnings.extend(code for code in selected.warnings if code not in warnings)
    else:
        warnings.append("NO_SELECTED_CANDIDATE")

    decision = "PASS" if approved else "BLOCK"
    recommendation = (
        "Futures research candidate passed robustness audit. Treat it only as a research candidate; do not train, reload, paper trade, or enable live trading yet."
        if approved
        else "No futures candidate passed robustness/data coverage audit. Do not train, reload, paper trade, or enable live trading from this hypothesis."
    )
    return FuturesRobustnessReport(
        contract_version=FUTURES_CANDIDATE_ROBUSTNESS_CONTRACT_VERSION,
        phase=FUTURES_CANDIDATE_ROBUSTNESS_CONTRACT_VERSION,
        report_type="futures_candidate_robustness_data_coverage_audit",
        decision=decision,
        ok=approved,
        source_reports=len(reports),
        candidate_count=len(candidates),
        selected_key=selected.key if selected else None,
        selected_symbol=selected.symbol if selected else None,
        selected_interval=selected.interval if selected else None,
        selected_strategy=selected.strategy if selected else None,
        selected_mean_net_edge_bps=selected.mean_net_edge_bps if selected else None,
        selected_profit_factor=selected.profit_factor if selected else None,
        selected_signal_count=selected.signal_count if selected else None,
        selected_positive_window_rate_pct=selected.positive_window_rate_pct if selected else None,
        approved_for_research_candidate=approved,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        live_real_allowed=False,
        observation_only=True,
        get_only_public_futures_data=True,
        post_requests_allowed=False,
        config_mutation_performed=False,
        order_actions_performed=False,
        reload_performed=False,
        reason_codes=reason_codes,
        warnings=warnings,
        recommendation=recommendation,
        selected_candidate=asdict(selected) if selected else None,
        candidates=[asdict(item) for item in audits],
        limits=asdict(active_limits),
        next_phase=NEXT_PHASE_RECOMMENDATION if approved else "HYP_002_REVIEW_OR_NEXT_HYPOTHESIS",
    )


def report_to_dict(report: FuturesRobustnessReport) -> dict[str, Any]:
    return asdict(report)


def write_report_files(report: FuturesRobustnessReport, out_dir: str | Path, timestamp: str) -> tuple[Path, Path]:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / f"{REPORT_PREFIX}_{timestamp}.json"
    md_path = root / f"{REPORT_PREFIX}_{timestamp}.md"
    json_path.write_text(json.dumps(report_to_dict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def render_markdown_report(report: FuturesRobustnessReport) -> str:
    rows = []
    for idx, c in enumerate(report.candidates, start=1):
        rows.append(
            "| {idx} | {decision} | {symbol} | {interval} | {strategy} | {signals} | {mean:.6f} | {median:.6f} | {pf:.6f} | {dd:.6f} | {pos:.2f} | `{reasons}` | `{warnings}` |".format(
                idx=idx,
                decision=c["decision"],
                symbol=c["symbol"],
                interval=c["interval"],
                strategy=c["strategy"],
                signals=c["signal_count"],
                mean=c["mean_net_edge_bps"],
                median=c["median_net_edge_bps"],
                pf=c["profit_factor"],
                dd=c["max_drawdown_pct"],
                pos=c["positive_window_rate_pct"],
                reasons=c["reason_codes"],
                warnings=c["warnings"],
            )
        )
    selected = report.selected_candidate or {}
    return "\n".join(
        [
            "# 4B.4.3.6.6.25C Futures Candidate Robustness / Data Coverage Audit",
            "",
            f"- contract_version: `{report.contract_version}`",
            f"- decision: **{report.decision}**",
            f"- source_reports: `{report.source_reports}`",
            f"- candidate_count: `{report.candidate_count}`",
            f"- approved_for_research_candidate: `{report.approved_for_research_candidate}`",
            f"- approved_for_training_candidate: `{report.approved_for_training_candidate}`",
            f"- approved_for_paper_candidate: `{report.approved_for_paper_candidate}`",
            f"- approved_for_live_real: `{report.approved_for_live_real}`",
            f"- selected: `{report.selected_symbol}` `{report.selected_interval}` `{report.selected_strategy}`",
            f"- selected_mean_net_edge_bps: `{report.selected_mean_net_edge_bps}`",
            f"- selected_profit_factor: `{report.selected_profit_factor}`",
            f"- selected_signal_count: `{report.selected_signal_count}`",
            f"- selected_positive_window_rate_pct: `{report.selected_positive_window_rate_pct}`",
            f"- reason_codes: `{report.reason_codes}`",
            f"- warnings: `{report.warnings}`",
            f"- recommendation: {report.recommendation}",
            "",
            "## Guardrails",
            "",
            f"- observation_only: `{report.observation_only}`",
            f"- get_only_public_futures_data: `{report.get_only_public_futures_data}`",
            f"- post_requests_allowed: `{report.post_requests_allowed}`",
            f"- config_mutation_performed: `{report.config_mutation_performed}`",
            f"- order_actions_performed: `{report.order_actions_performed}`",
            f"- reload_performed: `{report.reload_performed}`",
            f"- live_real_allowed: `{report.live_real_allowed}`",
            "- backtest_pass_is_not_paper_permission: `True`",
            "- paper_pass_is_not_live_permission: `True`",
            "",
            "## Selected Candidate Metrics",
            "",
            f"- key: `{selected.get('key')}`",
            f"- signal_count: `{selected.get('signal_count')}`",
            f"- coverage_pct: `{selected.get('coverage_pct')}`",
            f"- mean_net_edge_bps: `{selected.get('mean_net_edge_bps')}`",
            f"- median_net_edge_bps: `{selected.get('median_net_edge_bps')}`",
            f"- win_rate_pct: `{selected.get('win_rate_pct')}`",
            f"- profit_factor: `{selected.get('profit_factor')}`",
            f"- max_drawdown_pct: `{selected.get('max_drawdown_pct')}`",
            f"- oos_edge_bps: `{selected.get('oos_edge_bps')}`",
            f"- source_report_count: `{selected.get('source_report_count')}`",
            f"- pass_window_count: `{selected.get('pass_window_count')}`",
            f"- positive_edge_window_count: `{selected.get('positive_edge_window_count')}`",
            f"- cross_symbol_pass_count: `{selected.get('cross_symbol_pass_count')}`",
            f"- funding_data_coverage_pct: `{selected.get('funding_data_coverage_pct')}`",
            f"- open_interest_data_coverage_pct: `{selected.get('open_interest_data_coverage_pct')}`",
            f"- long_short_data_coverage_pct: `{selected.get('long_short_data_coverage_pct')}`",
            f"- taker_data_coverage_pct: `{selected.get('taker_data_coverage_pct')}`",
            "",
            "## Candidates",
            "",
            "| # | decision | symbol | interval | strategy | signals | mean_edge_bps | median_edge_bps | profit_factor | max_dd_pct | positive_window_rate_pct | reasons | warnings |",
            "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|",
            *rows,
            "",
            "## Policy",
            "",
            "This tool audits previous 25B research reports. It never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only confirms a robustness-reviewed research candidate; paper/live trading remains blocked.",
        ]
    )
