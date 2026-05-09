from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

HYP003_BRANCH_CLOSURE_CONTRACT_VERSION = "4B.4.3.6.6.25M"
REPORT_PREFIX = "4B436625M_hyp003_branch_closure_evidence_pack"
SNAPSHOT_PREFIX = "4B436625M_hyp003_branch_closure_registry_snapshot"

HYP003_CLOSURE_CONFIRMED = "HYP003_BRANCH_CLOSURE_CONFIRMED"
HYP003_CLOSURE_BLOCK = "HYP003_BRANCH_CLOSURE_BLOCK"

REQUIRED_J_DECISIONS = {"HYP003_EXPLORATION_PASS"}
REQUIRED_K_DECISIONS = {"HYP003_ROBUSTNESS_BLOCK"}
REQUIRED_L_DECISIONS = {"HYP003_BRANCH_CLOSURE_RECOMMENDED"}

TERMINAL_25K_CODES = {
    "ROBUST_MEAN_EDGE_LOW",
    "ROBUST_MEDIAN_EDGE_LOW",
    "ROBUST_OOS_EDGE_LOW",
    "ROBUST_PROFIT_FACTOR_LOW",
    "ROBUST_WALK_FORWARD_STABILITY_LOW",
    "ROBUST_WIN_RATE_LOW",
}

TERMINAL_25L_CODES = {
    "HYP003_SELECTED_CANDIDATE_ROBUSTNESS_BLOCK",
    "NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE",
}


@dataclass(frozen=True)
class Hyp003ClosedCandidate:
    symbol: str = ""
    interval: str = ""
    strategy_family: str = ""
    regime: str = ""
    signal_count: int = 0
    mean_net_edge_bps: float = 0.0
    median_net_edge_bps: float = 0.0
    profit_factor: float = 0.0
    source_phase: str = ""

    @property
    def key(self) -> str:
        parts = [self.symbol, self.interval, self.strategy_family, self.regime]
        return " ".join(part for part in parts if part) or "UNKNOWN"


@dataclass(frozen=True)
class Hyp003ClosureLimits:
    require_25j_exploration_pass: bool = True
    require_25k_robustness_block: bool = True
    require_25l_closure_recommended: bool = True
    require_no_alternate_candidate: bool = True
    require_no_training_paper_live_approvals: bool = True


@dataclass(frozen=True)
class Hyp003EvidenceSummary:
    phase: str
    source_report: str
    decision: str
    reason_codes: tuple[str, ...] = ()
    approved_for_research_candidate: bool = False
    approved_for_training_candidate: bool = False
    approved_for_paper_candidate: bool = False
    approved_for_live_real: bool = False
    selected_candidate: Hyp003ClosedCandidate | None = None


@dataclass(frozen=True)
class Hyp003ClosureEvidencePack:
    contract_version: str
    phase: str
    report_type: str
    decision: str
    ok: bool
    generated_at: str
    source_reports: int
    hypothesis_id: str
    branch_name: str
    selected_candidate: Hyp003ClosedCandidate | None
    final_25j_decision: str | None
    final_25k_decision: str | None
    final_25l_decision: str | None
    exploration_pass_confirmed: bool
    robustness_block_confirmed: bool
    branch_closure_recommended_confirmed: bool
    no_alternate_candidate_confirmed: bool
    no_training_paper_live_approvals_detected: bool
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
    warnings: tuple[str, ...]
    recommendation: str
    evidence: tuple[Hyp003EvidenceSummary, ...]
    registry_snapshot: Mapping[str, Any]
    next_actions: tuple[str, ...]
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    return (str(value),)


def _phase(report: Mapping[str, Any], source_report: str = "") -> str:
    text = " ".join(str(x) for x in [report.get("contract_version"), report.get("phase"), report.get("report_type"), source_report] if x).upper()
    for suffix in ("25J", "25K", "25L", "25M"):
        if suffix in text or f"4B4366{suffix}" in text:
            return suffix
    if "REGIME_STRATEGY_EXPLORATION" in text:
        return "25J"
    if "ROBUSTNESS" in text or "WALKFORWARD" in text or "WALK_FORWARD" in text:
        return "25K"
    if "REFINEMENT" in text or "BRANCH_DECISION" in text:
        return "25L"
    return "UNKNOWN"


def _decision(report: Mapping[str, Any]) -> str:
    return str(report.get("decision") or "UNKNOWN")


def _selected_candidate_from_report(report: Mapping[str, Any], phase: str) -> Hyp003ClosedCandidate | None:
    selected = report.get("selected_candidate") or report.get("selected") or report.get("failed_candidate")
    if isinstance(selected, Mapping):
        return Hyp003ClosedCandidate(
            symbol=str(selected.get("symbol") or ""),
            interval=str(selected.get("interval") or ""),
            strategy_family=str(selected.get("strategy_family") or selected.get("strategy") or selected.get("family") or ""),
            regime=str(selected.get("regime") or ""),
            signal_count=_safe_int(selected.get("signal_count") or selected.get("signals"), 0),
            mean_net_edge_bps=_safe_float(selected.get("mean_net_edge_bps") or selected.get("mean_edge_bps"), 0.0),
            median_net_edge_bps=_safe_float(selected.get("median_net_edge_bps") or selected.get("median_edge_bps"), 0.0),
            profit_factor=_safe_float(selected.get("profit_factor"), 0.0),
            source_phase=phase,
        )
    if isinstance(selected, str) and selected.strip():
        parts = selected.split()
        return Hyp003ClosedCandidate(
            symbol=parts[0] if len(parts) > 0 else "",
            interval=parts[1] if len(parts) > 1 else "",
            strategy_family=parts[2] if len(parts) > 2 else "",
            regime=parts[3] if len(parts) > 3 else "",
            source_phase=phase,
        )

    # 25K report style from CLI output/top-level fields.
    symbol = str(report.get("selected_symbol") or report.get("symbol") or "")
    interval = str(report.get("selected_interval") or report.get("interval") or "")
    strategy = str(report.get("selected_strategy_family") or report.get("strategy_family") or report.get("strategy") or "")
    regime = str(report.get("selected_regime") or report.get("regime") or "")
    selected_text = str(report.get("selected") or "")
    if selected_text and not (symbol and interval and strategy and regime):
        parts = selected_text.split()
        symbol = symbol or (parts[0] if len(parts) > 0 else "")
        interval = interval or (parts[1] if len(parts) > 1 else "")
        strategy = strategy or (parts[2] if len(parts) > 2 else "")
        regime = regime or (parts[3] if len(parts) > 3 else "")
    if symbol or interval or strategy or regime:
        return Hyp003ClosedCandidate(
            symbol=symbol,
            interval=interval,
            strategy_family=strategy,
            regime=regime,
            signal_count=_safe_int(report.get("selected_signal_count") or report.get("signal_count"), 0),
            mean_net_edge_bps=_safe_float(report.get("selected_mean_net_edge_bps") or report.get("mean_net_edge_bps"), 0.0),
            median_net_edge_bps=_safe_float(report.get("selected_median_net_edge_bps") or report.get("median_net_edge_bps"), 0.0),
            profit_factor=_safe_float(report.get("selected_profit_factor") or report.get("profit_factor"), 0.0),
            source_phase=phase,
        )
    return None


def summarize_report(report: Mapping[str, Any], source_report: str) -> Hyp003EvidenceSummary:
    phase = _phase(report, source_report)
    return Hyp003EvidenceSummary(
        phase=phase,
        source_report=source_report,
        decision=_decision(report),
        reason_codes=_as_tuple(report.get("reason_codes")),
        approved_for_research_candidate=bool(report.get("approved_for_research_candidate", False)),
        approved_for_training_candidate=bool(report.get("approved_for_training_candidate", False)),
        approved_for_paper_candidate=bool(report.get("approved_for_paper_candidate", False)),
        approved_for_live_real=bool(report.get("approved_for_live_real", False)),
        selected_candidate=_selected_candidate_from_report(report, phase),
    )


def _latest_by_phase(evidence: Sequence[Hyp003EvidenceSummary], phase: str) -> Hyp003EvidenceSummary | None:
    scoped = [item for item in evidence if item.phase == phase]
    return scoped[-1] if scoped else None


def _candidate_key(candidate: Hyp003ClosedCandidate | None) -> str:
    return candidate.key if candidate is not None else "UNKNOWN"


def _candidate_keys_match(a: Hyp003ClosedCandidate | None, b: Hyp003ClosedCandidate | None) -> bool:
    if a is None or b is None:
        return True
    if a.key == "UNKNOWN" or b.key == "UNKNOWN":
        return True
    return a.key == b.key


def build_registry_snapshot(
    *,
    hypothesis_id: str,
    branch_name: str,
    selected_candidate: Hyp003ClosedCandidate | None,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "contract_version": HYP003_BRANCH_CLOSURE_CONTRACT_VERSION,
        "generated_at": generated_at,
        "hypothesis_id": hypothesis_id,
        "branch_name": branch_name,
        "status": "CLOSED_NO_GO",
        "closure_reason": "HYP003_SELECTED_CANDIDATE_FAILED_ROBUSTNESS_AND_NO_ALTERNATE_CANDIDATE_AVAILABLE",
        "selected_candidate": asdict(selected_candidate) if selected_candidate else None,
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "next_registry_action": "RETURN_TO_BACKLOG_FOR_NEXT_HYPOTHESIS_SELECTION",
    }


def build_hyp003_branch_closure_evidence_pack(
    reports: Sequence[Mapping[str, Any]],
    *,
    source_names: Sequence[str] | None = None,
    hypothesis_id: str = "HYP-003",
    branch_name: str = "regime_specific_strategy_family",
    limits: Hyp003ClosureLimits | None = None,
    generated_at: str | None = None,
) -> Hyp003ClosureEvidencePack:
    limits = limits or Hyp003ClosureLimits()
    generated_at = generated_at or utc_now_iso()
    names = list(source_names or [f"input_{idx}" for idx, _ in enumerate(reports)])
    evidence = tuple(summarize_report(report, name) for report, name in zip(reports, names))

    e25j = _latest_by_phase(evidence, "25J")
    e25k = _latest_by_phase(evidence, "25K")
    e25l = _latest_by_phase(evidence, "25L")

    final_25j_decision = e25j.decision if e25j else None
    final_25k_decision = e25k.decision if e25k else None
    final_25l_decision = e25l.decision if e25l else None

    selected_candidate = (e25l.selected_candidate if e25l and e25l.selected_candidate else None) or (e25k.selected_candidate if e25k else None) or (e25j.selected_candidate if e25j else None)

    exploration_pass = bool(e25j and e25j.decision in REQUIRED_J_DECISIONS)
    robustness_block = bool(e25k and e25k.decision in REQUIRED_K_DECISIONS)
    branch_closure_recommended = bool(e25l and e25l.decision in REQUIRED_L_DECISIONS)
    no_alternate = bool(e25l and "NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE" in set(e25l.reason_codes))
    terminal_k_codes = set(e25k.reason_codes if e25k else ())
    robustness_terminal_codes_confirmed = bool(terminal_k_codes.intersection(TERMINAL_25K_CODES))
    terminal_l_codes = set(e25l.reason_codes if e25l else ())
    closure_terminal_codes_confirmed = TERMINAL_25L_CODES.issubset(terminal_l_codes) or bool(terminal_l_codes.intersection(TERMINAL_25L_CODES))
    candidate_consistency = _candidate_keys_match(e25k.selected_candidate if e25k else None, e25l.selected_candidate if e25l else None)

    approvals_detected = any(
        item.approved_for_training_candidate or item.approved_for_paper_candidate or item.approved_for_live_real
        for item in evidence
    )
    no_training_paper_live_approvals = not approvals_detected

    reason_codes: list[str] = []
    warnings: list[str] = []

    if exploration_pass:
        reason_codes.append("HYP003_EXPLORATION_PASS_CONFIRMED")
    else:
        reason_codes.append("HYP003_EXPLORATION_PASS_MISSING")

    if robustness_block:
        reason_codes.append("HYP003_ROBUSTNESS_BLOCK_CONFIRMED")
    else:
        reason_codes.append("HYP003_ROBUSTNESS_BLOCK_MISSING")

    if robustness_terminal_codes_confirmed:
        reason_codes.append("HYP003_ROBUSTNESS_TERMINAL_CODES_CONFIRMED")
    else:
        reason_codes.append("HYP003_ROBUSTNESS_TERMINAL_CODES_MISSING")

    if branch_closure_recommended:
        reason_codes.append("HYP003_BRANCH_CLOSURE_RECOMMENDED_CONFIRMED")
    else:
        reason_codes.append("HYP003_BRANCH_CLOSURE_RECOMMENDED_MISSING")

    if no_alternate:
        reason_codes.append("NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE_CONFIRMED")
    else:
        reason_codes.append("NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE_MISSING")

    if closure_terminal_codes_confirmed:
        reason_codes.append("HYP003_25L_TERMINAL_CODES_CONFIRMED")
    else:
        warnings.append("HYP003_25L_TERMINAL_CODES_NOT_FULLY_CONFIRMED")

    if candidate_consistency:
        reason_codes.append("HYP003_SELECTED_CANDIDATE_CONSISTENT")
    else:
        reason_codes.append("HYP003_SELECTED_CANDIDATE_MISMATCH")

    if no_training_paper_live_approvals:
        reason_codes.append("NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED")
    else:
        reason_codes.append("TRAINING_PAPER_OR_LIVE_APPROVAL_DETECTED")

    closure_requirements = [
        exploration_pass or not limits.require_25j_exploration_pass,
        robustness_block or not limits.require_25k_robustness_block,
        robustness_terminal_codes_confirmed,
        branch_closure_recommended or not limits.require_25l_closure_recommended,
        no_alternate or not limits.require_no_alternate_candidate,
        candidate_consistency,
        no_training_paper_live_approvals or not limits.require_no_training_paper_live_approvals,
    ]
    ok = all(closure_requirements)
    decision = HYP003_CLOSURE_CONFIRMED if ok else HYP003_CLOSURE_BLOCK

    registry_snapshot = build_registry_snapshot(
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        selected_candidate=selected_candidate,
        generated_at=generated_at,
    )

    recommendation = (
        "HYP-003 branch is closed no-go. Do not train, reload, start paper trading, or enable live trading. Return to the research backlog for the next pre-registered hypothesis."
        if ok
        else "HYP-003 branch closure evidence is incomplete. Do not train, reload, paper trade, or enable live trading; provide missing 25J/25K/25L evidence first."
    )

    next_actions = (
        "Write the registry snapshot as CLOSED_NO_GO for HYP-003.",
        "Return to backlog advancement for next hypothesis selection.",
        "Keep training, reload, paper, and live permissions disabled.",
    )

    guardrails = {
        "observation_only": True,
        "market_data_requests_performed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "training_allowed": False,
        "paper_allowed": False,
        "live_real_allowed": False,
    }

    return Hyp003ClosureEvidencePack(
        contract_version=HYP003_BRANCH_CLOSURE_CONTRACT_VERSION,
        phase=HYP003_BRANCH_CLOSURE_CONTRACT_VERSION,
        report_type="hyp003_branch_closure_evidence_pack",
        decision=decision,
        ok=ok,
        generated_at=generated_at,
        source_reports=len(reports),
        hypothesis_id=hypothesis_id,
        branch_name=branch_name,
        selected_candidate=selected_candidate,
        final_25j_decision=final_25j_decision,
        final_25k_decision=final_25k_decision,
        final_25l_decision=final_25l_decision,
        exploration_pass_confirmed=exploration_pass,
        robustness_block_confirmed=robustness_block,
        branch_closure_recommended_confirmed=branch_closure_recommended,
        no_alternate_candidate_confirmed=no_alternate,
        no_training_paper_live_approvals_detected=no_training_paper_live_approvals,
        approved_for_research_candidate=False,
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
        warnings=tuple(warnings),
        recommendation=recommendation,
        evidence=evidence,
        registry_snapshot=registry_snapshot,
        next_actions=next_actions,
        guardrails=guardrails,
    )


def report_to_dict(report: Hyp003ClosureEvidencePack) -> dict[str, Any]:
    return asdict(report)


def load_json_report(path: str | Path) -> Mapping[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Report JSON must be an object: {path}")
    return payload


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def render_markdown(report: Hyp003ClosureEvidencePack) -> str:
    selected = report.selected_candidate
    selected_text = selected.key if selected else "UNKNOWN"
    lines = [
        "# 4B.4.3.6.6.25M HYP-003 Branch Closure Evidence Pack",
        "",
        f"- contract_version: `{report.contract_version}`",
        f"- decision: **{report.decision}**",
        f"- hypothesis_id: `{report.hypothesis_id}`",
        f"- branch_name: `{report.branch_name}`",
        f"- selected_candidate: `{selected_text}`",
        f"- source_reports: `{report.source_reports}`",
        f"- final_25j_decision: `{report.final_25j_decision}`",
        f"- final_25k_decision: `{report.final_25k_decision}`",
        f"- final_25l_decision: `{report.final_25l_decision}`",
        f"- exploration_pass_confirmed: `{report.exploration_pass_confirmed}`",
        f"- robustness_block_confirmed: `{report.robustness_block_confirmed}`",
        f"- branch_closure_recommended_confirmed: `{report.branch_closure_recommended_confirmed}`",
        f"- no_alternate_candidate_confirmed: `{report.no_alternate_candidate_confirmed}`",
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
        "## Evidence Chain",
        "",
        "| phase | decision | source | research | training | paper | live | reasons | selected |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ])
    for item in report.evidence:
        lines.append(
            f"| {item.phase} | {item.decision} | {Path(item.source_report).name} | {item.approved_for_research_candidate} | "
            f"{item.approved_for_training_candidate} | {item.approved_for_paper_candidate} | {item.approved_for_live_real} | "
            f"`{list(item.reason_codes)}` | `{_candidate_key(item.selected_candidate)}` |"
        )
    lines.extend([
        "",
        "## Registry Snapshot",
        "",
        f"- status: `{report.registry_snapshot.get('status')}`",
        f"- next_registry_action: `{report.registry_snapshot.get('next_registry_action')}`",
        "",
        "## Policy",
        "",
        "This evidence pack never fetches market data, trains models, reloads models, mutates config, starts paper trading, or sends orders. Paper/live remain blocked.",
    ])
    return "\n".join(lines) + "\n"


def write_report_bundle(report: Hyp003ClosureEvidencePack, out_dir: str | Path) -> tuple[Path, Path, Path]:
    out_dir = Path(out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_json = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    snapshot_json = out_dir / f"{SNAPSHOT_PREFIX}_{stamp}.json"
    write_json(report_json, report_to_dict(report))
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(render_markdown(report), encoding="utf-8")
    write_json(snapshot_json, report.registry_snapshot)
    return report_json, report_md, snapshot_json
