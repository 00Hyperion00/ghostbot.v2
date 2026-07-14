from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def _checker():
    path = Path(__file__).with_name("check_4B436662F_H6_final_full_repo_contract_closure.py")
    spec = importlib.util.spec_from_file_location("phase62f_h6_checker", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("H6_CHECKER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = _checker().build_report()
    output = Path(args.reports_dir)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "4B436662F_H6_final_full_repo_contract_closure.json"
    report["report_path"] = str(report_path.resolve())
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
