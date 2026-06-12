from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H1-H1"
TARGETS = (
    "tools/apply_4B436627GH1_repository_hygiene_cleanup.py",
    "tools/check_4B436627GH1_repository_hygiene_cleanup.py",
    "tools/rollback_4B436627GH1_repository_hygiene_cleanup.py",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    contents = {relative: (root / relative).read_text(encoding="utf-8") for relative in TARGETS}
    regression_test = (root / "tests/test_repository_hygiene_cleanup_4B436627GH1.py").read_text(encoding="utf-8")
    checks = {
        "gh1_apply_explicit_utf8_present": 'encoding="utf-8"' in contents[TARGETS[0]] and 'errors="strict"' in contents[TARGETS[0]],
        "gh1_checker_explicit_utf8_present": 'encoding="utf-8"' in contents[TARGETS[1]] and 'errors="strict"' in contents[TARGETS[1]],
        "gh1_rollback_explicit_utf8_present": 'encoding="utf-8"' in contents[TARGETS[2]] and 'errors="strict"' in contents[TARGETS[2]],
        "unicode_path_regression_test_present": "Masaüstü ALKILIÇ" in regression_test,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
