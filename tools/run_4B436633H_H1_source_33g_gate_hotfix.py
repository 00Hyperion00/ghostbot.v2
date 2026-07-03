from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_4B436633H_H1_source_33g_gate_hotfix import _bootstrap, build_summary


def _stamp() -> str:
    import time

    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B436633H-H1 source 33G gate hotfix report.")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = _bootstrap()
    summary = build_summary(root)
    out_dir = Path(args.reports_dir) if args.reports_dir else root / "reports" / "recovery"
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if summary.get("ok") is True else "not_ready"
    path = out_dir / f"4B436633H_H1_source_33g_gate_hotfix_{_stamp()}_{suffix}.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    summary["report_path"] = str(path)
    print(json.dumps(summary, sort_keys=True) if args.once_json else json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
