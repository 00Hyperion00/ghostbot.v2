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

from tradebot.multitimeframe_retrain_sweep_25b import (  # noqa: E402
    CONTRACT_VERSION,
    MultiTimeframeRetrainCandidateSpec,
    build_mtf_15m_retrain_sweep,
    fetch_binance_klines,
    policies_from_25a_report,
    promote_best,
    read_ohlcv_csv,
    train_mtf_15m_candidate,
    write_reports,
)


def _load_json(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25B 15m multi-timeframe retrain sweep + gate")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--input-json", help="25A multi-timeframe alpha discovery report JSON")
    parser.add_argument("--input-csv", help="Optional local 15m OHLCV CSV")
    parser.add_argument("--candidate-json", help="Evaluate already-built candidate JSON instead of training")
    parser.add_argument("--class-weight-profiles", default="balanced,buy_sell_boost_light,buy_sell_boost_medium")
    parser.add_argument("--threshold-profiles", default="balanced,action_seek_light,paper_guarded")
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--candidate-dir", default="models/4B436625B_candidates")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--promote-to", default="models/ETHUSDT_model_4b436625B.ubj")
    parser.add_argument("--review-ok", action="store_true", help="Acknowledge that this is research-only and never reloads/orders")
    args = parser.parse_args()

    if not args.review_ok:
        print(f"{CONTRACT_VERSION} requires --review-ok because this is a gated research operation.")
        return 2

    try:
        candidate_results: list[dict[str, Any]] = []
        source = "candidate-json"
        if args.candidate_json:
            loaded = _load_json(args.candidate_json)
            if isinstance(loaded, dict) and isinstance(loaded.get("candidates"), list):
                candidate_results = [dict(c) for c in loaded["candidates"]]
            elif isinstance(loaded, dict):
                candidate_results = [loaded]
        else:
            report_25a = _load_json(args.input_json)
            policies = policies_from_25a_report(report_25a)
            class_profiles = _split_csv(args.class_weight_profiles)
            threshold_profiles = _split_csv(args.threshold_profiles)
            specs: list[MultiTimeframeRetrainCandidateSpec] = []
            for policy in policies:
                for cw in class_profiles:
                    for th in threshold_profiles:
                        specs.append(MultiTimeframeRetrainCandidateSpec(policy=policy, class_weight_profile=cw, threshold_profile=th))
            specs = specs[: max(1, args.max_candidates)]
            if args.input_csv:
                rows = read_ohlcv_csv(args.input_csv)
                source = f"csv:{args.input_csv}"
            else:
                rows = fetch_binance_klines(args.symbol, args.interval, args.days, args.base_url)
                source = f"binance:{args.symbol}:{args.interval}:{args.days}d"
            for spec in specs:
                candidate_results.append(
                    train_mtf_15m_candidate(
                        rows=rows,
                        spec=spec,
                        symbol=args.symbol.upper(),
                        days=args.days,
                        output_dir=args.candidate_dir,
                    )
                )
        report = build_mtf_15m_retrain_sweep(candidate_results, source=source)
        if args.promote:
            promoted_to = promote_best(report, args.promote_to)
            report = build_mtf_15m_retrain_sweep(candidate_results, source=source, promoted_to=promoted_to, promotion_performed=bool(promoted_to))
        json_path, md_path = write_reports(report, args.out_dir)
        best = (report.get("selection") or {}).get("best_candidate") or {}
        metrics = best.get("metrics") or {}
        print(f"{CONTRACT_VERSION} 15m multi-timeframe retrain sweep {report['decision']}")
        print(f" - candidates: {report.get('candidate_count')}")
        print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
        print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
        print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
        print(f" - selected_model: {best.get('model_path')}")
        print(f" - selected_score: {best.get('score')}")
        print(f" - selected_calibrated_action_pct: {metrics.get('validation_calibrated_action_pct')}")
        print(f" - selected_expected_edge_proxy_bps: {metrics.get('expected_edge_proxy_bps')}")
        print(f" - recommendation: {report.get('recommendation')}")
        print(f"report_json: {json_path.as_posix()}")
        print(f"report_md: {md_path.as_posix()}")
        return 0 if report["decision"] == "PASS" else 1
    except Exception as exc:
        report = {
            "contract_version": CONTRACT_VERSION,
            "phase": CONTRACT_VERSION,
            "report_type": "mtf_15m_retrain_sweep_gate",
            "decision": "BLOCK",
            "ok": False,
            "candidate_count": 0,
            "approved_for_training_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "reason_codes": ["MTF_15M_RETRAIN_TOOL_FAILED"],
            "recommendation": f"Tool failed before producing a valid retrain sweep report: {exc}",
            "error": str(exc),
            "guardrails": {
                "observation_only": True,
                "no_post_actions": True,
                "post_requests_allowed": False,
                "config_mutation_performed": False,
                "order_actions_performed": False,
                "reload_performed": False,
                "live_real_allowed": False,
            },
            "selection": {"best_candidate": {}},
            "candidates": [],
        }
        json_path, md_path = write_reports(report, args.out_dir)
        print(f"{CONTRACT_VERSION} 15m multi-timeframe retrain sweep BLOCK")
        print(f" - candidates: 0")
        print(f" - approved_for_training_candidate: False")
        print(f" - approved_for_paper_candidate: False")
        print(f" - approved_for_live_real: False")
        print(f" - recommendation: {report['recommendation']}")
        print(f"report_json: {json_path.as_posix()}")
        print(f"report_md: {md_path.as_posix()}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
