from __future__ import annotations

import argparse
import json
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30J"
FILES = [
    "README_APPLY_4B436630J.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_4B436630J.md",
    "src/tradebot/paper_sandbox_dry_run_reconciliation_audit_ledger.py",
    "tests/test_paper_sandbox_dry_run_reconciliation_audit_ledger_4B436630J.py",
    "tools/apply_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py",
    "tools/check_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py",
    "tools/run_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py",
]
CONFIG_START = "    # 4B.4.3.6.6.30J paper sandbox dry-run reconciliation + audit ledger proof controls\n"
CONFIG_END = "    live_real_hard_block_required: bool = True\n"


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def strip_config(root: Path) -> bool:
    config = root / "src" / "tradebot" / "config.py"
    if not config.exists():
        return False
    text = config.read_text(encoding="utf-8")
    start = text.find(CONFIG_START)
    if start < 0:
        return False
    end = text.find(CONFIG_END, start)
    if end < 0:
        return False
    text = text[:start] + text[end:]
    config.write_text(text, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    removed: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
        removed[rel] = not path.exists()
    config_stripped = strip_config(root)
    report = {
        "ok": all(removed.values()),
        "contract_version": CONTRACT_VERSION,
        "removed": removed,
        "config_stripped": config_stripped,
        "read_only": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
