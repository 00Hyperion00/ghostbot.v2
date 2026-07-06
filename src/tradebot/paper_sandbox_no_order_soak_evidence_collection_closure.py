from __future__ import annotations

from typing import Any

from tradebot.paper_sandbox_phase43_common import evaluate_phase, main_for_patch

PATCH_ID = "4B436643I"
PATCH_VERSION = "4B.4.3.6.6.43I"
PATCH_NAME = "Paper Sandbox No-Order Soak Evidence Collection Closure"


def evaluate(reports_dir: str = "reports/recovery", write_reports: bool = False) -> dict[str, Any]:
    return evaluate_phase(PATCH_ID, reports_dir=reports_dir, write_reports=write_reports)


def main() -> int:
    return main_for_patch(PATCH_ID)


if __name__ == "__main__":
    raise SystemExit(main())
