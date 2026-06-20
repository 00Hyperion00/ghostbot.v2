from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradebot.config import Settings
from tradebot.paper_transition_operator_gate import (
    PAPER_TRANSITION_OPERATOR_GATE_CONTRACT_VERSION,
    build_paper_transition_operator_gate_snapshot,
)

REPORT_PREFIX = "4B436630B_paper_transition_operator_approval_gate_decision"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _latest_json(reports_dir: Path, pattern: str) -> Path | None:
    matches = [p for p in reports_dir.glob(pattern) if p.is_file()]
    return sorted(matches, key=lambda p: p.name, reverse=True)[0] if matches else None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON report must be an object: {path}")
    return payload


def _fallback_preflight_snapshot() -> dict[str, Any]:
    return {
        "decision": "PAPER_CANDIDATE_PREFLIGHT_READY_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED",
        "approved_for_no_order_to_paper_transition_preflight": True,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_live_order_blocked": True,
    }


def _load_latest_30a_snapshot(reports_dir: Path) -> dict[str, Any]:
    path = _latest_json(reports_dir, "4B436630A_paper_candidate_preflight_decision_*.json")
    if path is None:
        return _fallback_preflight_snapshot()
    payload = _load_json(path)
    payload["source_report"] = path.as_posix()
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _render_md(payload: dict[str, Any]) -> str:
    keys = (
        "decision",
        "read_only",
        "approved_for_paper_transition_operator_approval_gate",
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "operator_approval_verified",
        "sandbox_runtime_envelope_verified",
        "paper_dry_run_reconciliation_probe_verified",
        "paper_live_order_blocked",
        "trading_action_performed",
    )
    lines = [f"# {PAPER_TRANSITION_OPERATOR_GATE_CONTRACT_VERSION} Paper Transition Operator Approval Gate", ""]
    lines.append("This report is review-only. It does not enable paper orders, live-real, runtime overlays, training, reload, or order actions.")
    lines.append("")
    lines.append("## Decision")
    for key in keys:
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Reason codes")
    lines.append("- `" + ", ".join(str(x) for x in payload.get("reason_codes", [])) + "`")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run 30B paper transition operator approval gate.")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-confirmation", default=None)
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--approval-issued-at-ms", type=int, default=None)
    parser.add_argument("--now-ms", type=int, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    reports_dir = Path(args.reports_dir)
    settings = Settings()
    if args.operator_confirmation or args.operator_id or args.approval_issued_at_ms is not None:
        settings = replace(
            settings,
            paper_transition_operator_approved=True,
            paper_transition_operator_id=args.operator_id or "operator-cli",
            paper_transition_confirmation_token=args.operator_confirmation or "",
            paper_transition_approval_issued_at_ms=int(args.approval_issued_at_ms or 0),
        )
    preflight = _load_latest_30a_snapshot(reports_dir)
    payload = build_paper_transition_operator_gate_snapshot(settings, preflight, supplied_operator_confirmation=args.operator_confirmation, now_ms=args.now_ms)
    stamp = _utc_stamp()
    json_path = reports_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = reports_dir / f"{REPORT_PREFIX}_{stamp}.md"
    _write_json(json_path, payload)
    md_path.write_text(_render_md(payload), encoding="utf-8", newline="\n")
    print(f"{PAPER_TRANSITION_OPERATOR_GATE_CONTRACT_VERSION} Paper Transition Operator Approval Gate {payload['decision']}")
    for key in (
        "read_only",
        "approved_for_paper_transition_operator_approval_gate",
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "operator_approval_verified",
        "sandbox_runtime_envelope_verified",
        "paper_dry_run_reconciliation_probe_verified",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
