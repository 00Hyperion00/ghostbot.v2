from __future__ import annotations

import shutil
from pathlib import Path

CONFIG_BLOCK_START = "    # 4B.4.3.6.6.30I paper sandbox dry-run internal execution harness controls\n"
CONFIG_BLOCK_END_FIELD = "    paper_sandbox_dry_run_internal_paper_candidate_still_blocked_required: bool = True\n"
FILES = [
    "README_APPLY_4B436630I.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_4B436630I.md",
    "src/tradebot/paper_sandbox_dry_run_internal_execution_harness.py",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I.py",
    "tools/apply_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
    "tools/check_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
    "tools/run_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    config = root / "src" / "tradebot" / "config.py"
    if config.exists():
        text = config.read_text(encoding="utf-8")
        start = text.find(CONFIG_BLOCK_START)
        if start >= 0:
            end = text.find(CONFIG_BLOCK_END_FIELD, start)
            if end >= 0:
                end += len(CONFIG_BLOCK_END_FIELD)
                config.write_text(text[:start] + text[end:], encoding="utf-8", newline="\n")
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
    for rel in ("_patch_payload", "tools/_patch_payload"):
        path = root / rel
        if path.exists():
            shutil.rmtree(path)
    print("4B.4.3.6.6.30I rollback completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
