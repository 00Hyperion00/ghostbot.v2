from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H1"
IGNORE_LINES = (
    "reports/hyp005_r1_canonical/",
    "tools/_patch_backup_*/",
    "tools/_patch_payload_*/",
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def _is_hygiene_target(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        normalized.startswith("reports/hyp005_r1_canonical/")
        or normalized.startswith("tools/_patch_backup_")
        or normalized.startswith("tools/_patch_payload_")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    gitignore_path = root / ".gitignore"
    gitignore = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    tracked = [path for path in _git(root, "ls-files", "-z").split("\0") if path]
    hygiene_targets = sorted(path for path in tracked if _is_hygiene_target(path))

    checks = {
        "gitignore_policy_present": all(line in gitignore for line in IGNORE_LINES),
        "canonical_runtime_reports_untracked": not any(path.startswith("reports/hyp005_r1_canonical/") for path in hygiene_targets),
        "patch_backup_payload_untracked": not any(path.startswith("tools/_patch_backup_") or path.startswith("tools/_patch_payload_") for path in hygiene_targets),
        "accepted_baseline_source_mutation_performed": False,
    }
    payload = {
        "ok": (
            checks["gitignore_policy_present"]
            and checks["canonical_runtime_reports_untracked"]
            and checks["patch_backup_payload_untracked"]
            and not checks["accepted_baseline_source_mutation_performed"]
        ),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "tracked_hygiene_paths_remaining": hygiene_targets,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }
    if args.once_json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
