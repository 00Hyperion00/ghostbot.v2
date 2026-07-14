from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from datetime import datetime, timezone

def _load_build_report():
    path = Path(__file__).with_name("check_4B436662C_phase61_regression_restore_shadow_evidence_collection_fix.py")
    spec = importlib.util.spec_from_file_location("phase62c_check", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("PHASE62C_CHECKER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_report

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    build_report = _load_build_report()
    payload = build_report(Path.cwd())
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ").lower()
    report_path = reports_dir / f"4B436662C_phase61_regression_restore_shadow_evidence_collection_fix_{stamp}_{payload['status'].lower()}.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    payload["report_path"] = str(report_path)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
