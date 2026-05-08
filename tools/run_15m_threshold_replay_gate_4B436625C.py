from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.mtf_threshold_replay_gate_25c import (  # noqa: E402
    CONTRACT_VERSION,
    build_threshold_replay_gate,
    evaluate_samples_with_profiles,
    load_25b_report,
    replay_candidate_model_from_25b_report,
    samples_from_json,
    write_reports,
)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _load_json(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25C 15m threshold/calibration replay gate")
    parser.add_argument("--input-json", help="25B retrain sweep JSON or synthetic sample JSON")
    parser.add_argument("--sample-json", help="Synthetic/per-sample replay JSON with samples[]")
    parser.add_argument("--candidate-model", help="Override 25B selected candidate model path")
    parser.add_argument("--candidate-index", type=int, help="1-based candidate index from 25B report")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--threshold-profiles", default="current_report,balanced,action_seek_light,paper_guarded,paper_recall_guarded,edge_guarded_precision,micro_action_probe")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true")
    args = parser.parse_args()

    if not args.review_ok:
        print(f"{CONTRACT_VERSION} requires --review-ok because this is replay-only research.")
        return 2

    try:
        profile_names = _split_csv(args.threshold_profiles)
        source = "unknown"
        candidate_model = args.candidate_model
        evaluations = []
        sample_data = _load_json(args.sample_json) if args.sample_json else None
        if sample_data is None and args.input_json:
            possible = _load_json(args.input_json)
            if isinstance(possible, dict) and isinstance(possible.get("samples"), list):
                sample_data = possible
        if sample_data:
            probs, actual, edges = samples_from_json(sample_data)
            evaluations = evaluate_samples_with_profiles(probs, actual, edges, profile_names)
            source = args.sample_json or args.input_json or "sample-json"
        elif args.input_json:
            report25b = load_25b_report(args.input_json)
            from tradebot.multitimeframe_retrain_sweep_25b import fetch_binance_klines  # type: ignore
            rows = fetch_binance_klines(args.symbol, args.interval, args.days, args.base_url)
            evaluations, candidate_model = replay_candidate_model_from_25b_report(
                report25b,
                rows=rows,
                candidate_index=args.candidate_index,
                model_path=args.candidate_model,
                profile_names=profile_names,
            )
            source = f"25b-replay:{args.symbol}:{args.interval}:{args.days}d"
        else:
            raise RuntimeError("Provide --input-json or --sample-json")
        report = build_threshold_replay_gate(evaluations, source=source, candidate_model=candidate_model)
        json_path, md_path = write_reports(report, args.out_dir)
        selected = (report.get("selection") or {}).get("selected_profile") or {}
        metrics = selected.get("metrics") or {}
        profile = selected.get("profile") or {}
        print(f"{CONTRACT_VERSION} 15m threshold/calibration replay gate {report['decision']}")
        print(f" - profiles: {report.get('profile_count')}")
        print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
        print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
        print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
        print(f" - selected_profile: {profile.get('name')}")
        print(f" - selected_action_pct: {metrics.get('calibrated_action_pct')}")
        print(f" - selected_expected_edge_proxy_bps: {metrics.get('expected_edge_proxy_bps')}")
        print(f" - recommendation: {report.get('recommendation')}")
        print(f"report_json: {json_path.as_posix()}")
        print(f"report_md: {md_path.as_posix()}")
        return 0 if report["decision"] == "PASS" else 1
    except Exception as exc:
        report = {
            "contract_version": CONTRACT_VERSION,
            "phase": CONTRACT_VERSION,
            "report_type": "mtf_15m_threshold_calibration_replay_gate",
            "decision": "BLOCK",
            "ok": False,
            "profile_count": 0,
            "approved_for_training_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "reason_codes": ["MTF_THRESHOLD_REPLAY_TOOL_FAILED"],
            "recommendation": f"Tool failed before producing a valid threshold replay report: {exc}",
            "error": str(exc),
            "selection": {"selected_profile": {}},
            "profiles": [],
            "guardrails": {
                "observation_only": True,
                "no_post_actions": True,
                "post_requests_allowed": False,
                "config_mutation_performed": False,
                "order_actions_performed": False,
                "reload_performed": False,
                "live_real_allowed": False,
            },
        }
        json_path, md_path = write_reports(report, args.out_dir)
        print(f"{CONTRACT_VERSION} 15m threshold/calibration replay gate BLOCK")
        print(" - profiles: 0")
        print(" - approved_for_training_candidate: False")
        print(" - approved_for_paper_candidate: False")
        print(" - approved_for_live_real: False")
        print(f" - recommendation: {report['recommendation']}")
        print(f"report_json: {json_path.as_posix()}")
        print(f"report_md: {md_path.as_posix()}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
