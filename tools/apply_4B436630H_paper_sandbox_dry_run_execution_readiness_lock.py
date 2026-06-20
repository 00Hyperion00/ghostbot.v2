from __future__ import annotations

import json
import py_compile
import shutil
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30H"
CONFIG_BLOCK = "\n".join([
    "    # 4B.4.3.6.6.30H paper sandbox dry-run execution readiness lock controls",
    "    paper_sandbox_dry_run_execution_readiness_lock_enabled: bool = True",
    "    paper_sandbox_dry_run_execution_readiness_lock_consume_30g_required: bool = True",
    "    paper_sandbox_dry_run_operator_explicit_lock_required: bool = True",
    "    paper_sandbox_dry_run_operator_lock_operator_id: str = \"\"",
    "    paper_sandbox_dry_run_operator_lock_phrase: str = \"LOCK_PAPER_SANDBOX_DRY_RUN_READINESS\"",
    "    paper_sandbox_dry_run_operator_lock_token: str = \"\"",
    "    paper_sandbox_dry_run_operator_lock_issued: bool = False",
    "    paper_sandbox_dry_run_operator_lock_issued_at_ms: int = 0",
    "    paper_sandbox_dry_run_operator_lock_ttl_sec: int = 900",
    "    paper_sandbox_dry_run_exchange_submit_hard_block_audit_required: bool = True",
    "    paper_sandbox_dry_run_execution_still_disabled_required: bool = True",
])
MARKER = "    live_real_hard_block_required: bool = True"
EXPECTED_FILES = [
    "README_APPLY_4B436630H.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_4B436630H.md",
    "src/tradebot/paper_sandbox_dry_run_execution_readiness_lock.py",
    "tests/test_paper_sandbox_dry_run_execution_readiness_lock_4B436630H.py",
    "tools/check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
    "tools/rollback_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
    "tools/run_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
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
    before_missing = "paper_sandbox_dry_run_execution_readiness_lock_enabled" not in text
    if before_missing:
        if MARKER not in text:
            raise RuntimeError("live_real_hard_block_required marker not found in config.py")
        block = CONFIG_BLOCK.rstrip() + "\n"
        text = text.replace(MARKER, block + MARKER, 1)
        path.write_text(text, encoding="utf-8", newline="\n")
    after = path.read_text(encoding="utf-8")
    required = [
        "paper_sandbox_dry_run_execution_readiness_lock_enabled",
        "paper_sandbox_dry_run_execution_readiness_lock_consume_30g_required",
        "paper_sandbox_dry_run_operator_explicit_lock_required",
        "paper_sandbox_dry_run_operator_lock_operator_id",
        "paper_sandbox_dry_run_operator_lock_phrase",
        "paper_sandbox_dry_run_operator_lock_token",
        "paper_sandbox_dry_run_operator_lock_issued",
        "paper_sandbox_dry_run_operator_lock_issued_at_ms",
        "paper_sandbox_dry_run_operator_lock_ttl_sec",
        "paper_sandbox_dry_run_exchange_submit_hard_block_audit_required",
        "paper_sandbox_dry_run_execution_still_disabled_required",
    ]
    return {
        "patched": before_missing,
        "before_missing": required if before_missing else [],
        "after_missing": [item for item in required if item not in after],
    }


def cleanup_payload_dirs(root: Path) -> dict[str, bool]:
    removed: dict[str, bool] = {}
    for rel in ("_patch_payload", "tools/_patch_payload"):
        target = root / rel
        existed = target.exists()
        if existed:
            shutil.rmtree(target)
        removed[rel] = not target.exists()
    return removed


def compile_targets(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    targets = [rel for rel in EXPECTED_FILES if rel.endswith(".py")]
    targets.append("src/tradebot/config.py")
    for rel in targets:
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
    checker = root / "tools" / "check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py"
    namespace: dict[str, Any] = {}
    exec(compile(checker.read_text(encoding="utf-8"), str(checker), "exec"), namespace)
    return namespace["run_check"](root)


def main() -> int:
    root = repo_root()
    config_patch = patch_config(root)
    payload_removed = cleanup_payload_dirs(root)
    compiled = compile_targets(root)
    report = run_check(root)
    report["config_patch"] = config_patch
    report["payload_removed"] = payload_removed
    report["compiled_after_apply"] = compiled
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.30H paper sandbox dry-run execution readiness lock patch applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - patched_config_30h_missing_fields: {config_patch['patched']}")
    print(f" - root_patch_payload_removed: {payload_removed.get('_patch_payload')}")
    print(f" - tools_patch_payload_removed: {payload_removed.get('tools/_patch_payload')}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
