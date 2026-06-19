from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from check_4B436629D_replay_backtest_walkforward_gate import CONTRACT_VERSION, build_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.29D replay/backtest/walk-forward gate report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ok": bool(report.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "decision": "REPLAY_BACKTEST_WALKFORWARD_GATE_READY_LIVE_REAL_STILL_BLOCKED" if report.get("ok") else "REPLAY_BACKTEST_WALKFORWARD_GATE_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "approved_for_deterministic_replay_baseline": bool(report["checks"].get("deterministic_replay_digest_present")),
        "approved_for_model_artifact_hash_baseline": bool(report["checks"].get("model_artifact_hash_present")),
        "approved_for_last_known_good_registry_baseline": bool(report["checks"].get("last_known_good_registry_present")),
        "approved_for_walk_forward_gate_baseline": bool(report["checks"].get("walk_forward_gate_present")),
        "approved_for_oos_report_gate_baseline": bool(report["checks"].get("oos_report_gate_present")),
        "approved_for_promotion_review_candidate_only": bool(report["checks"].get("promotion_review_only_guard_present")),
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "runtime_overlay_activation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "checks": report["checks"],
        "module_probe": report.get("module_probe", {}),
        "recommendation": "Use this gate only for deterministic replay/OOS promotion review. Do not infer live readiness or enable runtime/paper/live from this report.",
    }
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436629D_replay_backtest_walkforward_gate_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.29D Replay / Backtest / Walk-forward Gate Decision Report\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- read_only: `{payload['read_only']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- trading_action_performed: `{payload['trading_action_performed']}`\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{CONTRACT_VERSION} Replay / Backtest / Walk-forward Gate {payload['decision']}")
    for key in (
        "read_only", "approved_for_deterministic_replay_baseline", "approved_for_model_artifact_hash_baseline",
        "approved_for_last_known_good_registry_baseline", "approved_for_walk_forward_gate_baseline",
        "approved_for_oos_report_gate_baseline", "approved_for_runtime_overlay_activation_candidate",
        "approved_for_parameter_relaxation_candidate", "approved_for_paper_candidate", "approved_for_live_real",
        "training_performed", "reload_performed", "trading_action_performed",
    ):
        print(f" - {key}: {payload[key]}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
