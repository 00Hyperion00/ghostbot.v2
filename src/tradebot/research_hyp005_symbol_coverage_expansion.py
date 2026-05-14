from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

HYP005_SYMBOL_COVERAGE_CONTRACT_VERSION = "4B.4.3.6.6.25AA"
HYP005_SYMBOL_COVERAGE_READY = "HYP005_SYMBOL_COVERAGE_EXPANSION_READY"
HYP005_SYMBOL_COVERAGE_BLOCK = "HYP005_SYMBOL_COVERAGE_EXPANSION_BLOCK"

DEFAULT_HYP005_SYMBOLS_10: tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "LTCUSDT",
)

BASELINE_HYP005_SYMBOLS: tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
)

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


@dataclass(frozen=True)
class Hyp005SymbolCoverageLimits:
    min_symbols: int = 10
    max_symbols: int = 10
    required_quote_asset: str = "USDT"
    min_baseline_overlap: int = 4
    max_single_symbol_sample_share_pct: float = 35.0
    max_non_baseline_symbols: int = 6


@dataclass(frozen=True)
class Hyp005SymbolProfile:
    symbol: str
    quote_asset: str
    baseline_symbol: bool
    expansion_symbol: bool
    accepted: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Hyp005SymbolCoverageReport:
    ok: bool
    contract_version: str
    phase: str
    decision: str
    generated_at_utc: str
    hypothesis_id: str
    branch_name: str
    selected_strategy_family: str
    no_order_symbol_coverage_gate_only: bool
    requested_symbols: tuple[str, ...]
    approved_symbols: tuple[str, ...]
    symbol_count: int
    baseline_symbol_count: int
    expansion_symbol_count: int
    limits: Hyp005SymbolCoverageLimits
    symbol_profiles: tuple[Hyp005SymbolProfile, ...]
    source_operator_audit: str | None
    source_shadow_observation_count: int
    source_shadow_sample_target: int
    source_paper_transition_ready: bool
    source_latest_acceptance_decision: str | None
    approved_for_shadow_collection: bool
    approved_for_scheduler_regeneration: bool
    approved_for_paper_transition_candidate: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    post_requests_allowed: bool
    order_actions_performed: bool
    paper_trading_started: bool
    training_performed: bool
    reload_performed: bool
    config_mutation_performed: bool
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    recommendation: str
    next_scheduler_symbols_arg: str

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def normalize_symbols(symbols: str | Iterable[str] | None) -> tuple[str, ...]:
    if symbols is None:
        raw_items: list[str] = list(DEFAULT_HYP005_SYMBOLS_10)
    elif isinstance(symbols, str):
        raw_items = [part.strip() for part in symbols.replace("\n", ",").split(",")]
    else:
        raw_items = [str(item).strip() for item in symbols]

    cleaned: list[str] = []
    for item in raw_items:
        if not item:
            continue
        cleaned.append(item.upper())
    return tuple(cleaned)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def find_latest_operator_audit(reports_dir: Path) -> Path | None:
    candidates = list(reports_dir.glob("4B436625Y_hyp005_shadow_operator_daily_audit_*.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_operator_audit(input_json: Path | None, reports_dir: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if input_json is not None:
        return load_json(input_json), str(input_json)
    if reports_dir is not None:
        latest = find_latest_operator_audit(reports_dir)
        if latest is not None:
            return load_json(latest), str(latest)
    return None, None


def build_symbol_profiles(
    symbols: Sequence[str],
    *,
    limits: Hyp005SymbolCoverageLimits,
) -> tuple[Hyp005SymbolProfile, ...]:
    seen: set[str] = set()
    profiles: list[Hyp005SymbolProfile] = []
    for symbol in symbols:
        reason_codes: list[str] = []
        if symbol in seen:
            reason_codes.append("DUPLICATE_SYMBOL")
        seen.add(symbol)

        if not _SYMBOL_RE.match(symbol):
            reason_codes.append("INVALID_SYMBOL_FORMAT")
        quote_asset = limits.required_quote_asset if symbol.endswith(limits.required_quote_asset) else "UNKNOWN"
        if not symbol.endswith(limits.required_quote_asset):
            reason_codes.append("NON_USDT_SYMBOL_BLOCKED")
        baseline = symbol in BASELINE_HYP005_SYMBOLS
        profiles.append(
            Hyp005SymbolProfile(
                symbol=symbol,
                quote_asset=quote_asset,
                baseline_symbol=baseline,
                expansion_symbol=not baseline,
                accepted=not reason_codes,
                reason_codes=tuple(reason_codes),
            )
        )
    return tuple(profiles)


def build_hyp005_symbol_coverage_report(
    *,
    symbols: str | Iterable[str] | None = None,
    input_json: Path | None = None,
    reports_dir: Path | None = None,
    review_ok: bool = False,
    limits: Hyp005SymbolCoverageLimits | None = None,
) -> Hyp005SymbolCoverageReport:
    active_limits = limits or Hyp005SymbolCoverageLimits()
    normalized_symbols = normalize_symbols(symbols)
    profiles = build_symbol_profiles(normalized_symbols, limits=active_limits)
    approved_symbols = tuple(profile.symbol for profile in profiles if profile.accepted)
    baseline_count = sum(1 for symbol in approved_symbols if symbol in BASELINE_HYP005_SYMBOLS)
    expansion_count = len(approved_symbols) - baseline_count

    audit, audit_path = load_operator_audit(input_json, reports_dir)
    source_shadow_count = _safe_int((audit or {}).get("shadow_observation_count"), 0)
    source_shadow_target = _safe_int((audit or {}).get("shadow_sample_target"), 30)
    source_paper_ready = _safe_bool((audit or {}).get("paper_transition_ready"), False)
    source_acceptance_decision = (audit or {}).get("latest_acceptance_decision")
    if source_acceptance_decision is not None:
        source_acceptance_decision = str(source_acceptance_decision)

    reason_codes: list[str] = []
    warnings: list[str] = []

    if not review_ok:
        reason_codes.append("REVIEW_OK_REQUIRED")
    if len(normalized_symbols) != len(set(normalized_symbols)):
        reason_codes.append("DUPLICATE_SYMBOLS_PRESENT")
    if len(approved_symbols) < active_limits.min_symbols:
        reason_codes.append("SYMBOL_COUNT_BELOW_REQUIRED_10")
    if len(approved_symbols) > active_limits.max_symbols:
        reason_codes.append("SYMBOL_COUNT_ABOVE_ALLOWED_10")
    if len(normalized_symbols) != active_limits.max_symbols:
        reason_codes.append("EXACTLY_10_SYMBOLS_REQUIRED")
    if baseline_count < active_limits.min_baseline_overlap:
        reason_codes.append("BASELINE_SYMBOL_OVERLAP_LOW")
    if expansion_count > active_limits.max_non_baseline_symbols:
        reason_codes.append("EXPANSION_SYMBOL_COUNT_TOO_HIGH")
    if any(profile.reason_codes for profile in profiles):
        reason_codes.append("ONE_OR_MORE_SYMBOLS_FAILED_VALIDATION")

    if audit is None:
        warnings.append("SOURCE_25Y_OPERATOR_AUDIT_MISSING")
    else:
        if _safe_bool(audit.get("approved_for_live_real"), False):
            reason_codes.append("SOURCE_AUDIT_LIVE_APPROVAL_DETECTED")
        if _safe_bool(audit.get("approved_for_paper_candidate"), False):
            reason_codes.append("SOURCE_AUDIT_PAPER_APPROVAL_DETECTED")
        if _safe_bool(audit.get("approved_for_training_candidate"), False):
            reason_codes.append("SOURCE_AUDIT_TRAINING_APPROVAL_DETECTED")
        if _safe_bool(audit.get("order_actions_performed"), False):
            reason_codes.append("SOURCE_AUDIT_ORDER_ACTION_DETECTED")
        if not _safe_bool(audit.get("no_order_operator_audit_only"), False):
            warnings.append("SOURCE_AUDIT_NO_ORDER_FLAG_NOT_CONFIRMED")

    if source_shadow_count == 0:
        warnings.append("SHADOW_SAMPLE_COUNT_STILL_ZERO")
    if source_paper_ready:
        warnings.append("SOURCE_PAPER_READY_TRUE_BUT_25AA_DOES_NOT_ENABLE_PAPER")

    ok = not reason_codes
    decision = HYP005_SYMBOL_COVERAGE_READY if ok else HYP005_SYMBOL_COVERAGE_BLOCK
    if ok:
        reason_codes.append("HYP005_10_SYMBOL_COVERAGE_APPROVED_FOR_SHADOW_COLLECTION_ONLY")
        reason_codes.append("NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED")
        recommendation = (
            "HYP-005 controlled 10-symbol coverage expansion is ready for no-order shadow collection. "
            "Regenerate the 25Z scheduler pack with the emitted symbol list; do not train, reload, "
            "paper trade, live trade, or send orders."
        )
    else:
        recommendation = (
            "HYP-005 controlled symbol coverage expansion is blocked. Fix validation findings before "
            "regenerating the scheduler; do not train, reload, paper trade, live trade, or send orders."
        )

    return Hyp005SymbolCoverageReport(
        ok=ok,
        contract_version=HYP005_SYMBOL_COVERAGE_CONTRACT_VERSION,
        phase=HYP005_SYMBOL_COVERAGE_CONTRACT_VERSION,
        decision=decision,
        generated_at_utc=_utc_now_iso(),
        hypothesis_id="HYP-005",
        branch_name="liquidity_sweep_reversal_vol_compression",
        selected_strategy_family="long_liquidity_sweep_reversal",
        no_order_symbol_coverage_gate_only=True,
        requested_symbols=tuple(normalized_symbols),
        approved_symbols=approved_symbols if ok else tuple(),
        symbol_count=len(approved_symbols) if ok else 0,
        baseline_symbol_count=baseline_count,
        expansion_symbol_count=expansion_count,
        limits=active_limits,
        symbol_profiles=profiles,
        source_operator_audit=audit_path,
        source_shadow_observation_count=source_shadow_count,
        source_shadow_sample_target=source_shadow_target,
        source_paper_transition_ready=source_paper_ready,
        source_latest_acceptance_decision=source_acceptance_decision,
        approved_for_shadow_collection=ok,
        approved_for_scheduler_regeneration=ok,
        approved_for_paper_transition_candidate=False,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        post_requests_allowed=False,
        order_actions_performed=False,
        paper_trading_started=False,
        training_performed=False,
        reload_performed=False,
        config_mutation_performed=False,
        reason_codes=tuple(reason_codes),
        warnings=tuple(warnings),
        recommendation=recommendation,
        next_scheduler_symbols_arg=",".join(approved_symbols if ok else normalized_symbols),
    )


def write_symbol_coverage_outputs(
    report: Hyp005SymbolCoverageReport,
    *,
    out_dir: Path,
    config_dir: Path | None = None,
    write_config: bool = False,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_json = out_dir / f"4B436625AA_hyp005_symbol_coverage_expansion_{timestamp}.json"
    report_md = out_dir / f"4B436625AA_hyp005_symbol_coverage_expansion_{timestamp}.md"
    report_json.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    report_md.write_text(render_markdown_report(report), encoding="utf-8")

    outputs = {"report_json": report_json, "report_md": report_md}
    if write_config:
        target_config_dir = config_dir or Path("config")
        target_config_dir.mkdir(parents=True, exist_ok=True)
        config_json = target_config_dir / "hyp005_shadow_symbols_4B436625AA.json"
        config_yaml = target_config_dir / "hyp005_shadow_symbols_4B436625AA.yaml"
        payload = {
            "contract_version": report.contract_version,
            "hypothesis_id": report.hypothesis_id,
            "branch_name": report.branch_name,
            "selected_strategy_family": report.selected_strategy_family,
            "symbols": list(report.approved_symbols),
            "symbols_arg": report.next_scheduler_symbols_arg,
            "interval": "4h",
            "days": 30,
            "no_order_shadow_collection_only": True,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "post_requests_allowed": False,
        }
        config_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        config_yaml.write_text(render_yaml_config(payload), encoding="utf-8")
        outputs["config_json"] = config_json
        outputs["config_yaml"] = config_yaml
    return outputs


def render_yaml_config(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    for key, value in payload.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def render_markdown_report(report: Hyp005SymbolCoverageReport) -> str:
    lines = [
        f"# HYP-005 Controlled Symbol Coverage Expansion Gate — {report.contract_version}",
        "",
        f"- decision: `{report.decision}`",
        f"- ok: `{report.ok}`",
        f"- hypothesis_id: `{report.hypothesis_id}`",
        f"- selected_strategy_family: `{report.selected_strategy_family}`",
        f"- symbol_count: `{report.symbol_count}`",
        f"- baseline_symbol_count: `{report.baseline_symbol_count}`",
        f"- expansion_symbol_count: `{report.expansion_symbol_count}`",
        f"- source_shadow_observation_count: `{report.source_shadow_observation_count}`",
        f"- source_shadow_sample_target: `{report.source_shadow_sample_target}`",
        f"- paper_transition_ready: `{report.source_paper_transition_ready}`",
        "",
        "## Approved Symbols",
        "",
    ]
    if report.approved_symbols:
        lines.extend(f"- `{symbol}`" for symbol in report.approved_symbols)
    else:
        lines.append("- NONE")
    lines.extend(
        [
            "",
            "## Risk Permissions",
            "",
            f"- approved_for_shadow_collection: `{report.approved_for_shadow_collection}`",
            f"- approved_for_scheduler_regeneration: `{report.approved_for_scheduler_regeneration}`",
            f"- approved_for_paper_candidate: `{report.approved_for_paper_candidate}`",
            f"- approved_for_live_real: `{report.approved_for_live_real}`",
            f"- post_requests_allowed: `{report.post_requests_allowed}`",
            "",
            "## Reason Codes",
            "",
        ]
    )
    lines.extend(f"- `{code}`" for code in report.reason_codes)
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- `{warning}`" for warning in report.warnings) if report.warnings else lines.append("- NONE")
    lines.extend(
        [
            "",
            "## Next Scheduler Symbols Arg",
            "",
            f"```text\n{report.next_scheduler_symbols_arg}\n```",
            "",
            "## Recommendation",
            "",
            report.recommendation,
            "",
            "Paper/live/order permissions remain closed.",
        ]
    )
    return "\n".join(lines) + "\n"
