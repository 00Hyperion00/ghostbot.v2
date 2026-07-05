from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.paper_sandbox_runtime_activation_preflight import build_report


def main() -> int:
    report = build_report(repo_root=ROOT, write_reports=False)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
