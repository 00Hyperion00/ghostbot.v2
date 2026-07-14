from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
CHECK_PATH = ROOT / "tools/check_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py"


def _load_build_report() -> Any:
    spec = importlib.util.spec_from_file_location("phase62f_h4_check", CHECK_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"CHECK_SCRIPT_NOT_LOADABLE:{CHECK_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=Path("reports/recovery"))
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    build_report = _load_build_report()
    report: dict[str, Any] = build_report()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    path = args.reports_dir / "4B436662F_H4_hyp006_syntax_repair_runner_import_ready.json"
    report["report_path"] = str(path.resolve())
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
