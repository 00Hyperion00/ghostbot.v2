from __future__ import annotations

import shutil
from pathlib import Path

FILES = (
    "README_APPLY_4B436630E.txt",
    "docs/PAPER_TRANSITION_REVIEW_RERUN_4B436630E.md",
    "src/tradebot/paper_transition_review_rerun.py",
    "tests/test_paper_transition_review_rerun_4B436630E.py",
    "tools/apply_4B436630E_paper_transition_review_rerun.py",
    "tools/check_4B436630E_paper_transition_review_rerun.py",
    "tools/run_4B436630E_paper_transition_review_rerun.py",
    "tools/rollback_4B436630E_paper_transition_review_rerun.py",
)
CONFIG_MARKER = "    # 4B.4.3.6.6.30E paper transition review rerun controls\n"
CONFIG_INSERT_BEFORE = "    live_real_hard_block_required: bool = True"


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
    for rel in ("_patch_payload", "tools/_patch_payload"):
        path = root / rel
        if path.exists():
            shutil.rmtree(path)
    cfg = root / "src" / "tradebot" / "config.py"
    if cfg.exists():
        text = cfg.read_text(encoding="utf-8")
        start = text.find(CONFIG_MARKER)
        end = text.find(CONFIG_INSERT_BEFORE, start)
        if start >= 0 and end >= 0:
            text = text[:start] + text[end:]
            cfg.write_text(text, encoding="utf-8", newline="\n")
    print("4B.4.3.6.6.30E rollback complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
