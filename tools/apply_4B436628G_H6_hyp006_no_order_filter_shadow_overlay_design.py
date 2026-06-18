from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from check_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design import CONTRACT_VERSION, build_report  # noqa: E402


def main() -> int:
    report = build_report(ROOT)
    print(f"{CONTRACT_VERSION} HYP-006 no-order filter shadow overlay design patch applied")
    for key, value in report["checks"].items():
        print(f" - {key}: {value}")
    for key in (
        "config_mutation_performed",
        "scheduler_mutation_performed",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
        "runtime_overlay_activation_performed",
        "paper_live_order_enablement_present",
    ):
        print(f" - {key}: {report.get(key)}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
