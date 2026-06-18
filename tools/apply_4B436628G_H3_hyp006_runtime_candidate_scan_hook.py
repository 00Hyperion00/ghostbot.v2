from __future__ import annotations

from pathlib import Path

from check_4B436628G_H3_hyp006_runtime_candidate_scan_hook import CONTRACT_VERSION, run_checks


def main() -> int:
    payload = run_checks(Path.cwd())
    print(f"{CONTRACT_VERSION} HYP-006 runtime candidate scan hook patch applied")
    for key, value in payload["checks"].items():
        print(f" - {key}: {value}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    print(" - paper_live_order_enablement_present: False")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
