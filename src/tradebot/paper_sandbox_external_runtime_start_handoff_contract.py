from __future__ import annotations

from .paper_sandbox_phase41_common import evaluate_phase, main_for_patch

PATCH_ID = "4B436641B"
PATCH_VERSION = "4B.4.3.6.6.41B"
PATCH_NAME = "Paper Sandbox External Runtime Start Handoff Contract"


def evaluate(reports_dir: str = "reports/recovery", write_reports: bool = False) -> dict[str, object]:
    return evaluate_phase(PATCH_ID, reports_dir=reports_dir, write_reports=write_reports)


def main() -> int:
    return main_for_patch(PATCH_ID)


if __name__ == "__main__":
    raise SystemExit(main())
