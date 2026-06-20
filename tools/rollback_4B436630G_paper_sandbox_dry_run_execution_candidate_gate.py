from __future__ import annotations

import json
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30G"
FILES = [
    "README_APPLY_4B436630G.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_EXECUTION_CANDIDATE_GATE_4B436630G.md",
    "src/tradebot/paper_sandbox_dry_run_execution_candidate_gate.py",
    "tests/test_paper_sandbox_dry_run_execution_candidate_gate_4B436630G.py",
    "tools/apply_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/check_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/run_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
]
CONFIG_BLOCK = """
    # 4B.4.3.6.6.30G paper sandbox dry-run execution candidate gate controls
    paper_sandbox_dry_run_execution_candidate_gate_enabled: bool = True
    paper_sandbox_dry_run_execution_candidate_consume_30f_plan_required: bool = True
    paper_sandbox_dry_run_single_simulated_intent_required: bool = True
    paper_sandbox_dry_run_no_exchange_submit_required: bool = True
    paper_sandbox_dry_run_paper_candidate_still_blocked_required: bool = True
"""


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    removed: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            removed[rel] = True
        else:
            removed[rel] = False
    cfg = root / "src" / "tradebot" / "config.py"
    config_removed = False
    if cfg.exists():
        text = cfg.read_text(encoding="utf-8")
        if CONFIG_BLOCK in text:
            cfg.write_text(text.replace(CONFIG_BLOCK, "", 1), encoding="utf-8", newline="\n")
            config_removed = True
    report = {"contract_version": CONTRACT_VERSION, "removed": removed, "config_block_removed": config_removed}
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
