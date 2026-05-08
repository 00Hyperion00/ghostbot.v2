from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

RESEARCH_STOP_CONTRACT_VERSION = "4B.4.3.6.6.24N"
PHASE = "4B.4.3.6.6.24N"
REPORT_TYPE = "research_stop_no_edge_evidence_pack"
REPORT_PREFIX = "4B436624N_research_stop_evidence_pack"

PHASE_ORDER: tuple[str, ...] = (
    "4B.4.3.6.6.24A",
    "4B.4.3.6.6.24B",
    "4B.4.3.6.6.24C",
    "4B.4.3.6.6.24D",
    "4B.4.3.6.6.24E",
    "4B.4.3.6.6.24F",
    "4B.4.3.6.6.24G",
    "4B.4.3.6.6.24H",
    "4B.4.3.6.6.24I",
    "4B.4.3.6.6.24J",
    "4B.4.3.6.6.24K",
    "4B.4.3.6.6.24L",
    "4B.4.3.6.6.24M",
)

PHASE_LABELS: dict[str, str] = {
    "4B.4.3.6.6.24A": "pre-live hygiene / release cleanup",
    "4B.4.3.6.6.24B": "model quality recovery / retrain gate",
    "4B.4.3.6.6.24C": "extended demo soak / readiness",
    "4B.4.3.6.6.24D": "model retrain dataset expansion / candidate quality recovery",
    "4B.4.3.6.6.24E": "runtime calibration probe / threshold sweep",
    "4B.4.3.6.6.24F": "calibration policy candidate gate",
    "4B.4.3.6.6.24G": "probability separation / label calibration recovery",
    "4B.4.3.6.6.24H": "label horizon / target engineering recovery",
    "4B.4.3.6.6.24I": "cost-aware label policy recovery",
    "4B.4.3.6.6.24J": "cost-aware retrain sweep / separation gate",
    "4B.4.3.6.6.24K": "two-stage action/side model recovery",
    "4B.4.3.6.6.24L": "edge-aware meta-label / regime filter recovery",
    "4B.4.3.6.6.24M": "timeframe / symbol / strategy edge exploration",
}

TERMINAL_NO_GO_PHASES: frozenset[str] = frozenset(
    {
        "4B.4.3.6.6.24J",
        "4B.4.3.6.6.24K",
        "4B.4.3.6.6.24L",
        "4B.4.3.6.6.24M",
    }
)

DEFAULT_REPORT_GLOBS: tuple[str, ...] = (
    "4B436624A_*.json",
    "4B436624B_*.json",
    "4B436624C_*.json",
    "4B436624D_*.json",
    "4B436624E_*.json",
    "4B436624F_*.json",
    "4B436624G_*.json",
    "4B436624H_*.json",
    "4B436624I_*.json",
    "4B436624J_*.json",
    "4B436624K_*.json",
    "4B436624L_*.json",
    "4B436624M_*.json",
)

HIGH_VALUE_FIELDS: tuple[str, ...] = (
    "decision",
    "ok",
    "approved_for_training_candidate",
    "approved_for_research_candidate",
    "approved_for_paper_candidate",
    "approved_for_live_real",
    "live_real_allowed",
    "reload_performed",
    "config_mutation_performed",
    "order_actions_performed",
    "reason_codes",
    "recommendation",
    "selected_policy",
    "selected_model",
    "selected_action_model",
    "selected_side_model",
    "selected_filter",
    "selected_mean_edge_bps",
    "selected_good_action_pct",
    "selected_staged_action_pct",
    "selected_action_precision",
    "selected_side_accuracy",
    "selected_score",
)

NO_GO_REASONS_BY_PHASE: dict[str, str] = {
    "4B.4.3.6.6.24C": "extended demo/paper readiness gate did not clear",
    "4B.4.3.6.6.24F": "no safe calibration profile passed",
    "4B.4.3.6.6.24G": "probability separation remained weak",
    "4B.4.3.6.6.24H": "non-cost-aware label horizon policies over-produced action labels",
    "4B.4.3.6.6.24J": "cost-aware retrain candidates failed separation/action-hold gate",
    "4B.4.3.6.6.24K": "two-stage action/side candidates failed edge gate",
    "4B.4.3.6.6.24L": "regime/meta-label filters did not turn edge positive",
    "4B.4.3.6.6.24M": "symbol/timeframe/strategy exploration found no positive net edge",
}

NEXT_HYPOTHESIS_BACKLOG: tuple[dict[str, Any], ...] = (
    {
        "id": "HYP-001",
        "theme": "Higher timeframe regime-first research",
        "priority": "HIGH",
        "hypothesis": "15m/1h regime classification may be required before 1m execution signals are useful.",
        "minimum_evidence_required": [
            "positive mean and median net edge after costs",
            "coverage not narrower than the configured research floor",
            "walk-forward consistency across at least two market windows",
        ],
    },
    {
        "id": "HYP-002",
        "theme": "Order-flow / liquidity features",
        "priority": "HIGH",
        "hypothesis": "OHLCV-only features may be insufficient; taker imbalance, depth, spread, and liquidity shift features may be needed.",
        "minimum_evidence_required": [
            "feature availability contract",
            "edge lift versus OHLCV baseline",
            "latency and data-quality risk assessment",
        ],
    },
    {
        "id": "HYP-003",
        "theme": "Portfolio-level signal selection",
        "priority": "MEDIUM",
        "hypothesis": "Single-symbol edge may be too unstable; cross-symbol ranking may improve selectivity.",
        "minimum_evidence_required": [
            "cross-sectional rank stability",
            "turnover-adjusted edge",
            "symbol concentration guardrails",
        ],
    },
    {
        "id": "HYP-004",
        "theme": "Futures-specific signals",
        "priority": "MEDIUM",
        "hypothesis": "Funding, open interest, liquidations, and basis may provide edge unavailable in spot OHLCV.",
        "minimum_evidence_required": [
            "futures data connector safety review",
            "funding/open-interest edge attribution",
            "separate leverage and liquidation-risk policy",
        ],
    },
    {
        "id": "HYP-005",
        "theme": "Strategy family reset",
        "priority": "MEDIUM",
        "hypothesis": "Trend/reversion/breakout baselines tested so far may not fit the selected market; new hypotheses should be researched before more ML sweeps.",
        "minimum_evidence_required": [
            "clear economic rationale",
            "pre-registered acceptance metrics",
            "baseline edge before model training",
        ],
    },
)


@dataclass(frozen=True)
class PhaseEvidence:
    phase: str
    label: str
    source_path: str
    decision: str
    ok: bool | None
    approved_for_training_candidate: bool | None
    approved_for_research_candidate: bool | None
    approved_for_paper_candidate: bool | None
    approved_for_live_real: bool | None
    live_real_allowed: bool | None
    guardrails_ok: bool
    reason_codes: list[str] = field(default_factory=list)
    recommendation: str = ""
    selected_summary: dict[str, Any] = field(default_factory=dict)
    no_go_reason: str = ""


@dataclass(frozen=True)
class ResearchStopDecision:
    decision: str
    ok: bool
    approved_for_training_candidate: bool
    approved_for_research_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    live_real_allowed: bool
    reason_codes: list[str]
    recommendation: str


def _as_bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _as_list_of_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _stringify_json_scalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_stringify_json_scalar(item) for item in value[:20]]
    if isinstance(value, dict):
        return {str(k): _stringify_json_scalar(v) for k, v in list(value.items())[:40]}
    return str(value)


def normalize_phase(raw_phase: Any, path: Path | None = None) -> str:
    text = str(raw_phase or "")
    match = re.search(r"4B\.4\.3\.6\.6\.24[A-Z]", text)
    if match:
        return match.group(0)
    if path is not None:
        path_match = re.search(r"4B436624([A-Z])", path.name)
        if path_match:
            return f"4B.4.3.6.6.24{path_match.group(1)}"
    return "UNKNOWN"


def read_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def discover_report_paths(reports_dir: Path, globs: Sequence[str] = DEFAULT_REPORT_GLOBS) -> list[Path]:
    paths: list[Path] = []
    for pattern in globs:
        paths.extend(reports_dir.glob(pattern))
    return sorted(set(paths), key=lambda item: (item.name, item.stat().st_mtime if item.exists() else 0.0))


def select_latest_report_per_phase(paths: Iterable[Path]) -> dict[str, Path]:
    selected: dict[str, Path] = {}
    for path in paths:
        phase = normalize_phase(None, path)
        if phase == "UNKNOWN":
            continue
        current = selected.get(phase)
        if current is None or path.stat().st_mtime >= current.stat().st_mtime:
            selected[phase] = path
    return selected


def extract_phase_evidence(report: Mapping[str, Any], source_path: Path) -> PhaseEvidence:
    phase = normalize_phase(report.get("contract_version") or report.get("phase"), source_path)
    reason_codes = _as_list_of_str(report.get("reason_codes"))
    guardrails = report.get("guardrails") if isinstance(report.get("guardrails"), dict) else {}

    no_post = report.get("no_post_actions", guardrails.get("no_post_actions"))
    reload_performed = report.get("reload_performed", guardrails.get("reload_performed"))
    config_mutation = report.get("config_mutation_performed", guardrails.get("config_mutation_performed"))
    order_actions = report.get("order_actions_performed", guardrails.get("order_actions_performed"))
    live_real_allowed = _as_bool_or_none(report.get("live_real_allowed", guardrails.get("live_real_allowed")))

    guardrails_ok = (
        bool(no_post) is True
        and bool(reload_performed) is False
        and bool(config_mutation) is False
        and bool(order_actions) is False
        and live_real_allowed is False
    )

    selected_summary: dict[str, Any] = {}
    for key in HIGH_VALUE_FIELDS:
        if key in report:
            selected_summary[key] = _stringify_json_scalar(report[key])

    selection = report.get("selection")
    if isinstance(selection, dict) and isinstance(selection.get("best_candidate"), dict):
        best = selection["best_candidate"]
        for key in (
            "decision",
            "score",
            "reason_codes",
            "model_path",
            "action_model_path",
            "side_model_path",
            "metrics",
            "candidate_spec",
        ):
            if key in best:
                selected_summary[f"best_candidate.{key}"] = _stringify_json_scalar(best[key])

    decision = str(report.get("decision", "UNKNOWN")).upper()
    no_go_reason = NO_GO_REASONS_BY_PHASE.get(phase, "") if decision == "BLOCK" else ""

    return PhaseEvidence(
        phase=phase,
        label=PHASE_LABELS.get(phase, "unknown phase"),
        source_path=str(source_path.as_posix()),
        decision=decision,
        ok=_as_bool_or_none(report.get("ok")),
        approved_for_training_candidate=_as_bool_or_none(report.get("approved_for_training_candidate")),
        approved_for_research_candidate=_as_bool_or_none(report.get("approved_for_research_candidate")),
        approved_for_paper_candidate=_as_bool_or_none(report.get("approved_for_paper_candidate")),
        approved_for_live_real=_as_bool_or_none(report.get("approved_for_live_real")),
        live_real_allowed=live_real_allowed,
        guardrails_ok=guardrails_ok,
        reason_codes=reason_codes,
        recommendation=str(report.get("recommendation", "")),
        selected_summary=selected_summary,
        no_go_reason=no_go_reason,
    )


def build_research_stop_decision(evidence: Sequence[PhaseEvidence]) -> ResearchStopDecision:
    reason_codes: list[str] = []
    by_phase = {item.phase: item for item in evidence}

    no_terminal_pass = True
    for phase in TERMINAL_NO_GO_PHASES:
        item = by_phase.get(phase)
        if item is None:
            reason_codes.append(f"{phase.replace('.', '')}_EVIDENCE_MISSING")
            continue
        if item.decision != "BLOCK":
            no_terminal_pass = False
        else:
            reason_codes.append(f"{phase.replace('.', '')}_BLOCK")

    if any(item.approved_for_paper_candidate is True for item in evidence):
        reason_codes.append("PAPER_CANDIDATE_APPROVED_IN_SOURCE_REPORT")
    if any(item.approved_for_live_real is True or item.live_real_allowed is True for item in evidence):
        reason_codes.append("LIVE_REAL_APPROVAL_DETECTED_IN_SOURCE_REPORT")
    if any(not item.guardrails_ok for item in evidence if item.phase in PHASE_ORDER):
        reason_codes.append("SOURCE_REPORT_GUARDRAIL_GAP_DETECTED")

    critical_blocks = [item for item in evidence if item.phase in TERMINAL_NO_GO_PHASES and item.decision == "BLOCK"]
    if critical_blocks and no_terminal_pass:
        reason_codes.append("NO_EDGE_EVIDENCE_CONFIRMED")

    # Keep ordering stable while removing duplicates.
    seen: set[str] = set()
    stable_reasons = []
    for code in reason_codes:
        if code not in seen:
            seen.add(code)
            stable_reasons.append(code)

    hard_stop = "NO_EDGE_EVIDENCE_CONFIRMED" in stable_reasons or any(
        code.endswith("_BLOCK") for code in stable_reasons
    )
    if any(code in stable_reasons for code in ("PAPER_CANDIDATE_APPROVED_IN_SOURCE_REPORT", "LIVE_REAL_APPROVAL_DETECTED_IN_SOURCE_REPORT")):
        hard_stop = True

    recommendation = (
        "Research stop / no-go remains active. Do not promote, reload, start paper trading, or enable live trading. "
        "Open the next cycle only with a new pre-registered edge hypothesis and acceptance metrics."
        if hard_stop
        else "Evidence is incomplete; collect missing phase reports before changing trading readiness."
    )

    return ResearchStopDecision(
        decision="RESEARCH_STOP_NO_GO" if hard_stop else "EVIDENCE_INCOMPLETE",
        ok=not hard_stop,
        approved_for_training_candidate=False,
        approved_for_research_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        live_real_allowed=False,
        reason_codes=stable_reasons,
        recommendation=recommendation,
    )


def build_research_stop_evidence_pack(
    reports: Sequence[tuple[Path, Mapping[str, Any]]],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    evidence = [extract_phase_evidence(report, path) for path, report in reports]
    evidence = sorted(evidence, key=lambda item: PHASE_ORDER.index(item.phase) if item.phase in PHASE_ORDER else 999)
    decision = build_research_stop_decision(evidence)

    phase_coverage = {
        phase: phase in {item.phase for item in evidence}
        for phase in PHASE_ORDER
    }
    terminal_evidence = [item for item in evidence if item.phase in TERMINAL_NO_GO_PHASES]
    blocked_terminal_count = sum(1 for item in terminal_evidence if item.decision == "BLOCK")

    guardrails = {
        "observation_only": True,
        "no_post_actions": True,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "live_real_allowed": False,
        "promotion_performed": False,
    }

    return {
        "contract_version": RESEARCH_STOP_CONTRACT_VERSION,
        "phase": PHASE,
        "report_type": REPORT_TYPE,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "decision": decision.decision,
        "ok": decision.ok,
        "approved_for_training_candidate": decision.approved_for_training_candidate,
        "approved_for_research_candidate": decision.approved_for_research_candidate,
        "approved_for_paper_candidate": decision.approved_for_paper_candidate,
        "approved_for_live_real": decision.approved_for_live_real,
        "live_real_allowed": decision.live_real_allowed,
        "reason_codes": decision.reason_codes,
        "recommendation": decision.recommendation,
        "summary": {
            "source_report_count": len(evidence),
            "phase_coverage": phase_coverage,
            "terminal_no_go_phase_count": len(TERMINAL_NO_GO_PHASES),
            "terminal_no_go_block_count": blocked_terminal_count,
            "no_edge_evidence_confirmed": "NO_EDGE_EVIDENCE_CONFIRMED" in decision.reason_codes,
            "paper_live_blocked": True,
        },
        "evidence": [asdict(item) for item in evidence],
        "guardrails": guardrails,
        "next_hypothesis_backlog": list(NEXT_HYPOTHESIS_BACKLOG),
        "policy": (
            "This report is an evidence pack only. It never mutates config, reloads models, starts paper trading, "
            "or sends orders. A research stop/no-go decision requires new pre-registered edge hypotheses before "
            "further training or readiness work."
        ),
    }


def build_markdown_report(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    evidence = report.get("evidence") if isinstance(report.get("evidence"), list) else []
    backlog = report.get("next_hypothesis_backlog") if isinstance(report.get("next_hypothesis_backlog"), list) else []
    guardrails = report.get("guardrails") if isinstance(report.get("guardrails"), dict) else {}

    lines: list[str] = [
        f"# {RESEARCH_STOP_CONTRACT_VERSION} Research Stop / No-Edge Evidence Pack",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- ok: `{report.get('ok')}`",
        f"- source_report_count: `{summary.get('source_report_count')}`",
        f"- terminal_no_go_block_count: `{summary.get('terminal_no_go_block_count')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- live_real_allowed: `{report.get('live_real_allowed')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Guardrails",
        "",
    ]

    for key in (
        "observation_only",
        "no_post_actions",
        "post_requests_allowed",
        "config_mutation_performed",
        "order_actions_performed",
        "reload_performed",
        "live_real_allowed",
        "promotion_performed",
    ):
        lines.append(f"- {key}: `{guardrails.get(key)}`")

    lines.extend([
        "",
        "## Phase Evidence",
        "",
        "| phase | label | decision | guardrails_ok | paper | live | reasons | no_go_reason |",
        "|---|---|---|---:|---:|---:|---|---|",
    ])
    for item in evidence:
        if not isinstance(item, dict):
            continue
        reasons = item.get("reason_codes") or []
        lines.append(
            "| {phase} | {label} | {decision} | {guardrails_ok} | {paper} | {live} | `{reasons}` | {no_go} |".format(
                phase=item.get("phase", ""),
                label=str(item.get("label", "")).replace("|", "/"),
                decision=item.get("decision", ""),
                guardrails_ok=item.get("guardrails_ok"),
                paper=item.get("approved_for_paper_candidate"),
                live=item.get("approved_for_live_real"),
                reasons=reasons,
                no_go=str(item.get("no_go_reason", "")).replace("|", "/"),
            )
        )

    lines.extend([
        "",
        "## Next Hypothesis Backlog",
        "",
        "| id | priority | theme | hypothesis |",
        "|---|---|---|---|",
    ])
    for item in backlog:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| {id} | {priority} | {theme} | {hypothesis} |".format(
                id=item.get("id", ""),
                priority=item.get("priority", ""),
                theme=str(item.get("theme", "")).replace("|", "/"),
                hypothesis=str(item.get("hypothesis", "")).replace("|", "/"),
            )
        )

    lines.extend([
        "",
        "## Policy",
        "",
        str(report.get("policy", "")),
        "",
    ])
    return "\n".join(lines)


def write_report_files(report: Mapping[str, Any], out_dir: Path, *, timestamp: str | None = None) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(build_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def load_reports_from_paths(paths: Sequence[Path]) -> list[tuple[Path, dict[str, Any]]]:
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        loaded.append((path, read_json_file(path)))
    return loaded
