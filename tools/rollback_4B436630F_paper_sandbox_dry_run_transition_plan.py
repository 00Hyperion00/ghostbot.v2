from __future__ import annotations

from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30F"
FILES = [
    "README_APPLY_4B436630F.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_4B436630F.md",
    "src/tradebot/paper_sandbox_dry_run_transition_plan.py",
    "tests/test_paper_sandbox_dry_run_transition_plan_4B436630F.py",
    "tools/apply_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    "tools/check_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    "tools/run_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    "tools/rollback_4B436630F_paper_sandbox_dry_run_transition_plan.py",
]
CONFIG_FIELDS = [
    "    # 4B.4.3.6.6.30F paper sandbox dry-run transition plan controls\n",
    "    paper_sandbox_dry_run_transition_plan_enabled: bool = True\n",
    "    paper_sandbox_dry_run_transition_plan_consume_30e_ready_required: bool = True\n",
    "    paper_sandbox_dry_run_order_path_simulation_required: bool = True\n",
    "    paper_sandbox_dry_run_operator_go_no_go_required: bool = True\n",
    "    paper_sandbox_dry_run_still_no_order_enablement_required: bool = True\n",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    for rel in FILES:
        (root / rel).unlink(missing_ok=True)
    cfg = root / "src" / "tradebot" / "config.py"
    if cfg.exists():
        text = cfg.read_text(encoding="utf-8")
        for line in CONFIG_FIELDS:
            text = text.replace(line, "")
        cfg.write_text(text, encoding="utf-8", newline="\n")
    print(f"{CONTRACT_VERSION} rollback completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
