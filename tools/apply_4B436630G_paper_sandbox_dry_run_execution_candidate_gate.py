from __future__ import annotations

import json
import py_compile
import shutil
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30G"
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_execution_candidate_gate_enabled",
    "paper_sandbox_dry_run_execution_candidate_consume_30f_plan_required",
    "paper_sandbox_dry_run_single_simulated_intent_required",
    "paper_sandbox_dry_run_no_exchange_submit_required",
    "paper_sandbox_dry_run_paper_candidate_still_blocked_required",
]
CONFIG_BLOCK = """
    # 4B.4.3.6.6.30G paper sandbox dry-run execution candidate gate controls
    paper_sandbox_dry_run_execution_candidate_gate_enabled: bool = True
    paper_sandbox_dry_run_execution_candidate_consume_30f_plan_required: bool = True
    paper_sandbox_dry_run_single_simulated_intent_required: bool = True
    paper_sandbox_dry_run_no_exchange_submit_required: bool = True
    paper_sandbox_dry_run_paper_candidate_still_blocked_required: bool = True
"""
PY_TARGETS = [
    "src/tradebot/paper_sandbox_dry_run_execution_candidate_gate.py",
    "tests/test_paper_sandbox_dry_run_execution_candidate_gate_4B436630G.py",
    "tools/check_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/run_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/rollback_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def patch_config(root: Path) -> dict[str, Any]:
    path = root / "src" / "tradebot" / "config.py"
    text = path.read_text(encoding="utf-8")
    before_missing = [field for field in CONFIG_FIELDS if field not in text]
    if before_missing:
        marker = "    live_real_hard_block_required: bool = True"
        if marker not in text:
            raise RuntimeError("live_real_hard_block_required marker not found in config.py")
        text = text.replace(marker, CONFIG_BLOCK + marker, 1)
        path.write_text(text, encoding="utf-8", newline="\n")
    after = path.read_text(encoding="utf-8")
    after_missing = [field for field in CONFIG_FIELDS if field not in after]
    return {"patched": bool(before_missing), "before_missing": before_missing, "after_missing": after_missing}


def remove_patch_payload_dirs(root: Path) -> dict[str, bool]:
    removed: dict[str, bool] = {}
    for rel in ("_patch_payload", "tools/_patch_payload"):
        target = root / rel
        existed = target.exists()
        if existed:
            shutil.rmtree(target)
        removed[rel] = existed or not target.exists()
    return removed


def compile_targets(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in PY_TARGETS:
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_check(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    checker = root / "tools" / "check_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py"
    namespace: dict[str, Any] = {}
    code = checker.read_text(encoding="utf-8")
    exec(compile(code, str(checker), "exec"), namespace)
    return namespace["run_check"](root)


def main() -> int:
    root = repo_root()
    config_patch = patch_config(root)
    payload_removed = remove_patch_payload_dirs(root)
    compiled = compile_targets(root)
    report = run_check(root)
    report["config_patch"] = config_patch
    report["payload_removed"] = payload_removed
    report["compiled_after_apply"] = compiled
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} paper sandbox dry-run execution candidate gate patch applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - patched_config_30g_missing_fields: {config_patch['patched']}")
    print(f" - root_patch_payload_removed: {payload_removed['_patch_payload']}")
    print(f" - tools_patch_payload_removed: {payload_removed['tools/_patch_payload']}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
