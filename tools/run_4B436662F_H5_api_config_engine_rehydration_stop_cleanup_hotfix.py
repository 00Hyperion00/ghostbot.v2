
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path

def _load_checker():
    path = Path(__file__).with_name("check_4B436662F_H5_api_config_engine_rehydration_stop_cleanup_hotfix.py")
    spec = importlib.util.spec_from_file_location("phase62f_h5_checker", path)
    if spec is None or spec.loader is None: raise RuntimeError("CHECKER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--reports-dir", default="reports/recovery"); parser.add_argument("--once-json", action="store_true"); args=parser.parse_args()
    report=_load_checker().build_report(); out_dir=Path(args.reports_dir); out_dir.mkdir(parents=True, exist_ok=True); report_path=out_dir/"4B436662F_H5_api_config_engine_rehydration_stop_cleanup_ready.json"; report["report_path"]=str(report_path.resolve()); report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"); print(json.dumps(report, ensure_ascii=False, sort_keys=True)); return 0 if report.get("ok") else 1
if __name__ == "__main__":
    raise SystemExit(main())
