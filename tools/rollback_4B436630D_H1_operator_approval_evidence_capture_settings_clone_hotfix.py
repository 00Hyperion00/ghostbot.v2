from __future__ import annotations

from pathlib import Path

BAD_SETTINGS_KWARG_LINE = '            "paper_live_order_enablement_present": False,\n'


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    target = root / "src" / "tradebot" / "paper_transition_approval_evidence_capture.py"
    text = target.read_text(encoding="utf-8")
    marker = '            "paper_transition_dry_run_probe_order_actions_performed": False,\n'
    if BAD_SETTINGS_KWARG_LINE not in text and marker in text:
        text = text.replace(marker, marker + BAD_SETTINGS_KWARG_LINE, 1)
        target.write_text(text, encoding="utf-8", newline="\n")
        print("30D-H1 settings clone hotfix rollback restored unsupported Settings kwarg line")
    else:
        print("30D-H1 rollback no-op")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
