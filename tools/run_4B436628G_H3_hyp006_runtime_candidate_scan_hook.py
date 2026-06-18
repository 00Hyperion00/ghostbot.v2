from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_4B436628G_H3_hyp006_runtime_candidate_scan_hook import CONTRACT_VERSION

ARTIFACT_PREFIX = "4B436628G_H3_hyp006_r1_runtime_candidate_scan_gate_level_near_miss"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read latest 28G-H3 HYP-006 runtime candidate scan hook artifact.")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports/hyp006_r1_canonical"))
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    files = sorted(args.reports_dir.glob(f"{ARTIFACT_PREFIX}_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not files:
        payload = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "decision": "HYP006_R1_RUNTIME_CANDIDATE_SCAN_HOOK_ARTIFACT_NOT_FOUND",
            "read_only": True,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "training_performed": False,
            "reload_performed": False,
            "trading_action_performed": False,
        }
    else:
        payload = json.loads(files[0].read_text(encoding="utf-8-sig"))
        payload["latest_artifact_json"] = str(files[0])
        payload["decision"] = "HYP006_R1_RUNTIME_CANDIDATE_SCAN_HOOK_ARTIFACT_READY"
        payload["ok"] = True
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} HYP-006 runtime candidate scan hook {payload.get('decision')}")
        for key in (
            "read_only",
            "scanned_candle_count",
            "candidate_count",
            "near_miss_count",
            "trigger_count",
            "approved_for_parameter_relaxation_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
        ):
            print(f" - {key}: {payload.get(key)}")
        if payload.get("latest_artifact_json"):
            print(f"latest_artifact_json: {payload['latest_artifact_json']}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
