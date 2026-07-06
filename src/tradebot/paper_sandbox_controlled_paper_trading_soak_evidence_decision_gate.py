from __future__ import annotations

from .paper_sandbox_phase50_60_common import evaluate_phase, main_for_patch

PATCH_ID = "4B436653H"
PATCH_VERSION = "4B.4.3.6.6.53H"
PATCH_NAME = "Paper Sandbox Controlled Paper Trading Soak Evidence Decision Gate"


def evaluate(reports_dir: str = "reports/recovery", write_reports: bool = False) -> dict[str, object]:
    return evaluate_phase(PATCH_ID, reports_dir=reports_dir, write_reports=write_reports)


def main() -> int:
    return main_for_patch(PATCH_ID)


if __name__ == "__main__":
    raise SystemExit(main())
