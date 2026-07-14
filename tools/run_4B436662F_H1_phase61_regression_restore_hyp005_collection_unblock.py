from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=Path("reports/recovery"))
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    sys.path.insert(0, str(Path.cwd() / "src"))
    from tradebot.full_repo_regression_stabilization_62F_H1 import build_phase62f_h1_snapshot
    payload = build_phase62f_h1_snapshot()
    payload["decision"] = "PHASE61_REGRESSION_RESTORE_HYP005_COLLECTION_UNBLOCK_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED" if payload["ok"] else "PHASE61_REGRESSION_RESTORE_HYP005_COLLECTION_UNBLOCK_BLOCKED"
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.reports_dir / "4B436662F_H1_phase61_regression_restore_hyp005_collection_unblock_ready.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    payload["report_path"] = str(report_path.resolve())
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
