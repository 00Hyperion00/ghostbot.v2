from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path

from tradebot.runtime_safety_lockdown import PATCH_ID, PATCH_VERSION, build_runtime_safety_lockdown, summarize

REQUIRED_FILES = (
    "src/tradebot/runtime_safety_lockdown.py",
    "tools/run_4B436633D_runtime_safety_lockdown.py",
    "tools/check_4B436633D_runtime_safety_lockdown.py",
    "tests/test_runtime_safety_lockdown_4B436633D.py",
    "docs/RUNTIME_SAFETY_LOCKDOWN_4B436633D.md",
    "README_APPLY_4B436633D.txt",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33D runtime safety lockdown checker")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    missing = [rel for rel in REQUIRED_FILES if not (repo_root / rel).exists()]
    compile_errors: dict[str, str] = {}
    for rel in REQUIRED_FILES:
        if rel.endswith(".py") and (repo_root / rel).exists():
            try:
                py_compile.compile(str(repo_root / rel), doraise=True)
            except Exception as exc:  # noqa: BLE001
                compile_errors[rel] = f"{type(exc).__name__}: {exc}"

    report = build_runtime_safety_lockdown(repo_root)
    payload = summarize(report)
    payload.update(
        {
            "patch_id": PATCH_ID,
            "patch_version": PATCH_VERSION,
            "required_files_present": not missing,
            "missing_files": missing,
            "py_compile_ok": not compile_errors,
            "compile_errors": compile_errors,
            "ok": not missing and not compile_errors,
        }
    )
    print(json.dumps(payload if args.once_json else payload, indent=None if args.once_json else 2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
