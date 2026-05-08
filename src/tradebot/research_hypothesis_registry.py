from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

RESEARCH_HYPOTHESIS_REGISTRY_CONTRACT_VERSION = "4B.4.3.6.6.24O"
REPORT_PREFIX = "4B436624O_research_hypothesis_registry"

NEXT_HYPOTHESIS_BACKLOG: tuple[str, ...] = (
    "higher_timeframe_trend_following",
    "futures_funding_open_interest_edge",
    "regime_specific_strategy_family",
    "portfolio_relative_strength_rotation",
    "order_flow_volume_imbalance_research",
)

DEFAULT_ACCEPTANCE_METRICS: dict[str, Any] = {
    "min_net_edge_bps": 3.0,
    "min_profit_factor": 1.15,
    "min_trade_count": 100,
    "max_drawdown_pct": 8.0,
    "oos_required": True,
    "walk_forward_required": True,
    "fee_slippage_included": True,
    "lookahead_leakage_tolerance": "zero",
}

DEFAULT_GUARDRAILS: dict[str, Any] = {
    "observation_only": True,
    "post_requests_allowed": False,
    "config_mutation_performed": False,
    "model_reload_allowed": False,
    "model_reload_performed": False,
    "order_actions_allowed": False,
    "order_actions_performed": False,
    "paper_allowed_if_pass": False,
    "live_allowed_if_pass": False,
    "approved_for_paper_candidate": False,
    "approved_for_live_real": False,
}


@dataclass(frozen=True)
class HypothesisAcceptanceMetrics:
    min_net_edge_bps: float
    min_profit_factor: float
    min_trade_count: int
    max_drawdown_pct: float
    oos_required: bool = True
    walk_forward_required: bool = True
    fee_slippage_included: bool = True
    lookahead_leakage_tolerance: str = "zero"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "HypothesisAcceptanceMetrics":
        data = {**DEFAULT_ACCEPTANCE_METRICS, **dict(value or {})}
        return cls(
            min_net_edge_bps=float(data["min_net_edge_bps"]),
            min_profit_factor=float(data["min_profit_factor"]),
            min_trade_count=int(data["min_trade_count"]),
            max_drawdown_pct=float(data["max_drawdown_pct"]),
            oos_required=bool(data.get("oos_required", True)),
            walk_forward_required=bool(data.get("walk_forward_required", True)),
            fee_slippage_included=bool(data.get("fee_slippage_included", True)),
            lookahead_leakage_tolerance=str(data.get("lookahead_leakage_tolerance", "zero")),
        )


@dataclass(frozen=True)
class ResearchHypothesis:
    hypothesis_id: str
    name: str
    status: str
    market: str
    symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    strategy_family: str
    data_requirements: tuple[str, ...]
    rationale: str
    acceptance_metrics: HypothesisAcceptanceMetrics
    guardrails: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_GUARDRAILS))
    priority: int = 100
    owner: str = "research"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ResearchHypothesis":
        required = ["hypothesis_id", "name", "status", "market", "symbols", "timeframes", "strategy_family"]
        missing = [key for key in required if key not in value or value[key] in (None, "")]
        if missing:
            raise ValueError(f"hypothesis is missing required fields: {', '.join(missing)}")
        guardrails = {**DEFAULT_GUARDRAILS, **dict(value.get("guardrails") or {})}
        return cls(
            hypothesis_id=str(value["hypothesis_id"]),
            name=str(value["name"]),
            status=str(value["status"]),
            market=str(value["market"]),
            symbols=tuple(str(item) for item in value.get("symbols", [])),
            timeframes=tuple(str(item) for item in value.get("timeframes", [])),
            strategy_family=str(value["strategy_family"]),
            data_requirements=tuple(str(item) for item in value.get("data_requirements", [])),
            rationale=str(value.get("rationale", "")),
            acceptance_metrics=HypothesisAcceptanceMetrics.from_mapping(value.get("acceptance_metrics")),
            guardrails=guardrails,
            priority=int(value.get("priority", 100)),
            owner=str(value.get("owner", "research")),
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_research_hypotheses() -> list[ResearchHypothesis]:
    raw: list[dict[str, Any]] = [
        {
            "hypothesis_id": "HYP-001",
            "name": "Higher timeframe trend following",
            "status": "PROPOSED",
            "market": "spot",
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
            "timeframes": ["30m", "1h", "4h"],
            "strategy_family": "trend_following_volatility_regime",
            "data_requirements": ["public_ohlcv", "volume", "atr", "vwap", "mtf_trend"],
            "rationale": "Prior 1m/3m/5m/15m spot research did not show positive edge; slower trend regimes may reduce noise and costs.",
            "priority": 1,
        },
        {
            "hypothesis_id": "HYP-002",
            "name": "Futures funding and open-interest edge",
            "status": "BACKLOG",
            "market": "futures",
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "timeframes": ["15m", "1h", "4h"],
            "strategy_family": "funding_open_interest_sentiment",
            "data_requirements": ["public_ohlcv", "funding_rate", "open_interest", "long_short_ratio"],
            "rationale": "Spot OHLCV alone was insufficient; futures positioning data may add behavioral information.",
            "priority": 2,
        },
        {
            "hypothesis_id": "HYP-003",
            "name": "Regime-specific strategy family",
            "status": "BACKLOG",
            "market": "spot",
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
            "timeframes": ["15m", "30m", "1h"],
            "strategy_family": "trend_range_volatility_router",
            "data_requirements": ["public_ohlcv", "atr", "vwap", "bb_width", "trend_strength"],
            "rationale": "A single strategy/model may be too blunt; route trend, range and volatility regimes separately.",
            "priority": 3,
        },
        {
            "hypothesis_id": "HYP-004",
            "name": "Portfolio relative-strength rotation",
            "status": "BACKLOG",
            "market": "spot",
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"],
            "timeframes": ["1h", "4h"],
            "strategy_family": "multi_symbol_relative_strength_rotation",
            "data_requirements": ["public_ohlcv", "cross_symbol_returns", "volatility_normalization"],
            "rationale": "Single-symbol edge failed; cross-sectional selection may offer more stable edge.",
            "priority": 4,
        },
        {
            "hypothesis_id": "HYP-005",
            "name": "Order-flow and volume imbalance research",
            "status": "BACKLOG",
            "market": "spot_or_futures",
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "timeframes": ["1m", "3m", "5m", "15m"],
            "strategy_family": "order_flow_volume_imbalance",
            "data_requirements": ["agg_trades", "book_ticker", "depth_imbalance", "taker_buy_sell_volume"],
            "rationale": "OHLCV baseline did not produce edge; microstructure data may be required for shorter horizons.",
            "priority": 5,
        },
    ]
    return [ResearchHypothesis.from_mapping(item) for item in raw]


def load_hypotheses_json(path: str | Path) -> list[ResearchHypothesis]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        items = payload.get("hypotheses", [])
    else:
        items = payload
    if not isinstance(items, list):
        raise ValueError("hypotheses json must contain a list or {'hypotheses': [...]} payload")
    return [ResearchHypothesis.from_mapping(item) for item in items]


def validate_hypothesis(hypothesis: ResearchHypothesis) -> dict[str, Any]:
    reason_codes: list[str] = []
    warnings: list[str] = []
    metrics = hypothesis.acceptance_metrics
    guardrails = hypothesis.guardrails

    if not hypothesis.symbols:
        reason_codes.append("HYPOTHESIS_SYMBOLS_MISSING")
    if not hypothesis.timeframes:
        reason_codes.append("HYPOTHESIS_TIMEFRAMES_MISSING")
    if metrics.min_net_edge_bps <= 0:
        reason_codes.append("ACCEPTANCE_MIN_NET_EDGE_NOT_POSITIVE")
    if metrics.min_profit_factor <= 1.0:
        reason_codes.append("ACCEPTANCE_PROFIT_FACTOR_NOT_ABOVE_ONE")
    if metrics.min_trade_count < 30:
        reason_codes.append("ACCEPTANCE_MIN_TRADE_COUNT_LOW")
    if metrics.max_drawdown_pct <= 0 or metrics.max_drawdown_pct > 25:
        reason_codes.append("ACCEPTANCE_MAX_DRAWDOWN_INVALID")
    if not metrics.oos_required:
        reason_codes.append("OOS_VALIDATION_REQUIRED")
    if not metrics.walk_forward_required:
        warnings.append("WALK_FORWARD_NOT_REQUIRED")
    if not metrics.fee_slippage_included:
        reason_codes.append("FEE_SLIPPAGE_MUST_BE_INCLUDED")
    if metrics.lookahead_leakage_tolerance.lower() != "zero":
        reason_codes.append("LOOKAHEAD_LEAKAGE_ZERO_TOLERANCE_REQUIRED")

    if guardrails.get("post_requests_allowed") is not False:
        reason_codes.append("POST_REQUESTS_MUST_REMAIN_DISABLED")
    if guardrails.get("paper_allowed_if_pass") is not False:
        reason_codes.append("PAPER_AUTO_APPROVAL_FORBIDDEN")
    if guardrails.get("live_allowed_if_pass") is not False:
        reason_codes.append("LIVE_AUTO_APPROVAL_FORBIDDEN")
    if guardrails.get("order_actions_allowed") is not False:
        reason_codes.append("ORDER_ACTIONS_MUST_REMAIN_DISABLED")
    if guardrails.get("model_reload_allowed") is not False:
        reason_codes.append("MODEL_RELOAD_MUST_REMAIN_DISABLED")

    return {
        "hypothesis_id": hypothesis.hypothesis_id,
        "name": hypothesis.name,
        "status": hypothesis.status,
        "priority": hypothesis.priority,
        "market": hypothesis.market,
        "strategy_family": hypothesis.strategy_family,
        "symbols": list(hypothesis.symbols),
        "timeframes": list(hypothesis.timeframes),
        "decision": "READY_FOR_RESEARCH_DESIGN" if not reason_codes else "BLOCK",
        "ok": not reason_codes,
        "reason_codes": reason_codes,
        "warnings": warnings,
        "acceptance_metrics": asdict(metrics),
        "guardrails": guardrails,
        "rationale": hypothesis.rationale,
    }


def build_research_hypothesis_registry(
    hypotheses: Sequence[ResearchHypothesis],
    *,
    source: str = "default_registry",
    previous_decision: str = "RESEARCH_STOP_NO_GO",
) -> dict[str, Any]:
    items = [validate_hypothesis(item) for item in sorted(hypotheses, key=lambda hyp: hyp.priority)]
    valid_count = sum(1 for item in items if item["ok"])
    block_count = len(items) - valid_count
    reason_codes: list[str] = []
    if not items:
        reason_codes.append("HYPOTHESIS_REGISTRY_EMPTY")
    if valid_count == 0:
        reason_codes.append("NO_VALID_RESEARCH_HYPOTHESIS_REGISTERED")
    if previous_decision != "RESEARCH_STOP_NO_GO":
        reason_codes.append("PREVIOUS_RESEARCH_STOP_DECISION_NOT_CONFIRMED")

    if not reason_codes:
        decision = "REGISTRY_READY"
        recommendation = (
            "Research restart registry is ready. Select exactly one pre-registered hypothesis for the next exploration phase; "
            "paper/live remain blocked until future acceptance gates pass."
        )
    else:
        decision = "BLOCK"
        recommendation = (
            "Research restart registry is not ready. Fix hypothesis acceptance metrics and guardrails before opening a new exploration cycle."
        )

    selected = next((item for item in items if item["ok"]), None)
    return {
        "contract_version": RESEARCH_HYPOTHESIS_REGISTRY_CONTRACT_VERSION,
        "phase": RESEARCH_HYPOTHESIS_REGISTRY_CONTRACT_VERSION,
        "report_type": "research_restart_charter_hypothesis_registry",
        "generated_at": _now_iso(),
        "source": source,
        "previous_decision": previous_decision,
        "decision": decision,
        "ok": decision == "REGISTRY_READY",
        "hypothesis_count": len(items),
        "valid_hypothesis_count": valid_count,
        "blocked_hypothesis_count": block_count,
        "selected_next_hypothesis_id": selected["hypothesis_id"] if selected else None,
        "selected_next_hypothesis_name": selected["name"] if selected else None,
        "approved_for_research_candidate": decision == "REGISTRY_READY",
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "paper_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
        "reason_codes": reason_codes,
        "recommendation": recommendation,
        "next_hypothesis_backlog": list(NEXT_HYPOTHESIS_BACKLOG),
        "hypotheses": items,
        "guardrails": {
            "observation_only": True,
            "no_post_actions": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "paper_allowed": False,
            "live_real_allowed": False,
        },
    }


def write_default_registry_files(config_dir: str | Path) -> dict[str, str]:
    path = Path(config_dir)
    path.mkdir(parents=True, exist_ok=True)
    hypotheses = [
        {
            **asdict(hyp),
            "symbols": list(hyp.symbols),
            "timeframes": list(hyp.timeframes),
            "data_requirements": list(hyp.data_requirements),
            "acceptance_metrics": asdict(hyp.acceptance_metrics),
        }
        for hyp in default_research_hypotheses()
    ]
    json_path = path / "research_hypotheses_4B436624O.json"
    yaml_path = path / "research_hypotheses_4B436624O.yaml"
    json_path.write_text(json.dumps({"hypotheses": hypotheses}, indent=2, ensure_ascii=False), encoding="utf-8")
    yaml_lines = ["# 4B.4.3.6.6.24O research hypothesis registry", "hypotheses:"]
    for hyp in hypotheses:
        yaml_lines.append(f"  - hypothesis_id: {hyp['hypothesis_id']}")
        yaml_lines.append(f"    name: {hyp['name']}")
        yaml_lines.append(f"    status: {hyp['status']}")
        yaml_lines.append(f"    market: {hyp['market']}")
        yaml_lines.append(f"    strategy_family: {hyp['strategy_family']}")
        yaml_lines.append("    symbols: [" + ", ".join(hyp["symbols"]) + "]")
        yaml_lines.append("    timeframes: [" + ", ".join(hyp["timeframes"]) + "]")
        yaml_lines.append("    acceptance_metrics:")
        for key, value in hyp["acceptance_metrics"].items():
            yaml_lines.append(f"      {key}: {str(value).lower() if isinstance(value, bool) else value}")
        yaml_lines.append("    guardrails:")
        for key, value in hyp["guardrails"].items():
            yaml_lines.append(f"      {key}: {str(value).lower() if isinstance(value, bool) else value}")
    yaml_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "yaml": str(yaml_path)}


def render_research_hypothesis_registry_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        f"# {report['contract_version']} Research Restart Charter + Hypothesis Registry",
        "",
        f"- contract_version: `{report['contract_version']}`",
        f"- decision: **{report['decision']}**",
        f"- previous_decision: `{report['previous_decision']}`",
        f"- hypothesis_count: `{report['hypothesis_count']}`",
        f"- valid_hypothesis_count: `{report['valid_hypothesis_count']}`",
        f"- selected_next_hypothesis_id: `{report.get('selected_next_hypothesis_id')}`",
        f"- approved_for_research_candidate: `{report['approved_for_research_candidate']}`",
        f"- approved_for_training_candidate: `{report['approved_for_training_candidate']}`",
        f"- approved_for_paper_candidate: `{report['approved_for_paper_candidate']}`",
        f"- approved_for_live_real: `{report['approved_for_live_real']}`",
        f"- recommendation: {report['recommendation']}",
        "",
        "## Guardrails",
        "",
    ]
    for key, value in report["guardrails"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Hypotheses", "", "| id | decision | priority | name | market | timeframes | strategy_family | reasons |", "|---|---|---:|---|---|---|---|---|"])
    for item in report["hypotheses"]:
        timeframes = ", ".join(item["timeframes"])
        reasons = "`" + ", ".join(item["reason_codes"]) + "`" if item["reason_codes"] else ""
        lines.append(
            f"| {item['hypothesis_id']} | {item['decision']} | {item['priority']} | {item['name']} | {item['market']} | {timeframes} | {item['strategy_family']} | {reasons} |"
        )
    lines.extend([
        "",
        "## Next Hypothesis Backlog",
        "",
    ])
    for item in report["next_hypothesis_backlog"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Policy",
        "",
        "This registry does not start paper trading, enable live trading, reload models, mutate config, or send orders. A REGISTRY_READY decision only permits selecting one pre-registered research hypothesis for the next exploration phase.",
    ])
    return "\n".join(lines) + "\n"


def write_report(report: Mapping[str, Any], out_dir: str | Path) -> dict[str, str]:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = path / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = path / f"{REPORT_PREFIX}_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_research_hypothesis_registry_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}
