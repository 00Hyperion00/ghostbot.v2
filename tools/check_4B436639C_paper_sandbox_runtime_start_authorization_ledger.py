from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_runtime_start_authorization_ledger import build_report


def main() -> int:
    report = build_report(Path("reports/recovery"), write_artifacts=False)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("status") == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
