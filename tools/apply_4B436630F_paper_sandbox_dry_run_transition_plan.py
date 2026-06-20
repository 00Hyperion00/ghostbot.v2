from __future__ import annotations

import json
import py_compile
import shutil
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30F"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
CONFIG_FIELDS_BLOCK = '''
    # 4B.4.3.6.6.30F paper sandbox dry-run transition plan controls
    paper_sandbox_dry_run_transition_plan_enabled: bool = True
    paper_sandbox_dry_run_transition_plan_consume_30e_ready_required: bool = True
    paper_sandbox_dry_run_order_path_simulation_required: bool = True
    paper_sandbox_dry_run_operator_go_no_go_required: bool = True
    paper_sandbox_dry_run_still_no_order_enablement_required: bool = True
'''.strip("\n") + "\n"
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_transition_plan_enabled",
    "paper_sandbox_dry_run_transition_plan_consume_30e_ready_required",
    "paper_sandbox_dry_run_order_path_simulation_required",
    "paper_sandbox_dry_run_operator_go_no_go_required",
    "paper_sandbox_dry_run_still_no_order_enablement_required",
]
EXPECTED_PAYLOAD_FILES = [
    "README_APPLY_4B436630F.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_4B436630F.md",
    "src/tradebot/paper_sandbox_dry_run_transition_plan.py",
    "tests/test_paper_sandbox_dry_run_transition_plan_4B436630F.py",
    "tools/check_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    "tools/rollback_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    "tools/run_4B436630F_paper_sandbox_dry_run_transition_plan.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def copy_payload(root: Path) -> None:
    payload = root / PAYLOAD_DIR
    if not payload.exists():
        raise FileNotFoundError(f"payload missing: {payload}")
    for src in payload.rglob("*"):
        if src.is_file():
            rel = src.relative_to(payload)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def patch_config(root: Path) -> dict[str, Any]:
    target = root / "src" / "tradebot" / "config.py"
    text = target.read_text(encoding="utf-8")
    before_missing = [field for field in CONFIG_FIELDS if field not in text]
    patched = False
    if before_missing:
        marker = "    live_real_hard_block_required: bool = True"
        if marker not in text:
            raise RuntimeError("live_real_hard_block_required marker not found in config.py")
        text = text.replace(marker, CONFIG_FIELDS_BLOCK + marker, 1)
        target.write_text(text, encoding="utf-8", newline="\n")
        patched = True
    after = target.read_text(encoding="utf-8")
    return {"patched": patched, "before_missing": before_missing, "after_missing": [field for field in CONFIG_FIELDS if field not in after]}


def ensure_gitignore(root: Path) -> dict[str, Any]:
    gitignore = root / ".gitignore"
    text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    additions = []
    for line in ("_patch_payload/", "_patch_payload/**", "tools/_patch_payload/", "tools/_patch_payload/**"):
        if line not in text:
            additions.append(line)
    if additions:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n# 4B.4.3.6.6.30F patch payload exclusion\n" + "\n".join(additions) + "\n"
        gitignore.write_text(text, encoding="utf-8", newline="\n")
    return {"changed": bool(additions), "added": additions}


def remove_payload_dirs(root: Path) -> dict[str, bool]:
    removed: dict[str, bool] = {}
    for rel in ("_patch_payload", "tools/_patch_payload"):
        path = root / rel
        existed = path.exists()
        if existed:
            shutil.rmtree(path)
        removed[rel] = not path.exists()
    return removed


def compile_targets(root: Path) -> dict[str, bool]:
    targets = [
        "src/tradebot/paper_sandbox_dry_run_transition_plan.py",
        "tests/test_paper_sandbox_dry_run_transition_plan_4B436630F.py",
        "tools/apply_4B436630F_paper_sandbox_dry_run_transition_plan.py",
        "tools/check_4B436630F_paper_sandbox_dry_run_transition_plan.py",
        "tools/rollback_4B436630F_paper_sandbox_dry_run_transition_plan.py",
        "tools/run_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    ]
    out: dict[str, bool] = {}
    for rel in targets:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_check(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    namespace: dict[str, Any] = {}
    checker = root / "tools" / "check_4B436630F_paper_sandbox_dry_run_transition_plan.py"
    exec(compile(checker.read_text(encoding="utf-8"), str(checker), "exec"), namespace)
    return namespace["run_check"](root)


def main() -> int:
    root = repo_root()
    copy_payload(root)
    config_patch = patch_config(root)
    gitignore_patch = ensure_gitignore(root)
    payload_removed = remove_payload_dirs(root)
    compiled = compile_targets(root)
    report = run_check(root)
    report["config_patch"] = config_patch
    report["gitignore_patch"] = gitignore_patch
    report["payload_removed"] = payload_removed
    report["compiled_after_apply"] = compiled
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.30F paper sandbox dry-run transition plan patch applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - patched_config_30f_missing_fields: {config_patch['patched']}")
    print(f" - root_patch_payload_removed: {payload_removed['_patch_payload']}")
    print(f" - tools_patch_payload_removed: {payload_removed['tools/_patch_payload']}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
