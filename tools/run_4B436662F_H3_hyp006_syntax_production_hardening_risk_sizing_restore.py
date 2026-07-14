from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools.check_4B436662F_H3_hyp006_syntax_production_hardening_risk_sizing_restore import build_report

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report()
    out_dir = Path(args.reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "4B436662F_H3_hyp006_syntax_production_hardening_risk_sizing_restore_ready.json"
    path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    report["report_path"] = str(path.resolve())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
