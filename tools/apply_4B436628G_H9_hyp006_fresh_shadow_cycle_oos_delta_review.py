from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tools.check_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review import build_report  # noqa: E402


def main() -> int:
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    print("4B.4.3.6.6.28G-H9 HYP-006 fresh shadow cycle OOS delta review patch applied")
    for key, value in report["checks"].items():
        print(f" - {key}: {value}")
    for key in (
        "runtime_overlay_activation_performed",
        "scheduler_mutation_performed",
        "strategy_parameter_mutation_performed",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
        "paper_live_order_enablement_present",
    ):
        print(f" - {key}: {report.get(key)}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
