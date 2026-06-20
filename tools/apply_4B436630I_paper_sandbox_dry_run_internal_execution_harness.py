from __future__ import annotations

import json
import py_compile
import shutil
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I"
CONFIG_BLOCK = '''    # 4B.4.3.6.6.30I paper sandbox dry-run internal execution harness controls
    paper_sandbox_dry_run_internal_execution_harness_enabled: bool = True
    paper_sandbox_dry_run_internal_execution_consume_30h_lock_required: bool = True
    paper_sandbox_dry_run_internal_only_harness_required: bool = True
    paper_sandbox_dry_run_simulated_fill_ledger_append_required: bool = True
    paper_sandbox_dry_run_simulated_fill_ledger_path: str = "reports/production_hardening/4B436630I_internal_simulated_fill_ledger.jsonl"
    paper_sandbox_dry_run_internal_no_exchange_submit_required: bool = True
    paper_sandbox_dry_run_internal_paper_candidate_still_blocked_required: bool = True
'''
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_internal_execution_harness_enabled",
    "paper_sandbox_dry_run_internal_execution_consume_30h_lock_required",
    "paper_sandbox_dry_run_internal_only_harness_required",
    "paper_sandbox_dry_run_simulated_fill_ledger_append_required",
    "paper_sandbox_dry_run_simulated_fill_ledger_path",
    "paper_sandbox_dry_run_internal_no_exchange_submit_required",
    "paper_sandbox_dry_run_internal_paper_candidate_still_blocked_required",
]
COMPILE_TARGETS = [
    "src/tradebot/config.py",
    "src/tradebot/paper_sandbox_dry_run_internal_execution_harness.py",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I.py",
    "tools/check_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
    "tools/rollback_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
    "tools/run_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
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
    patched = False
    if before_missing:
        marker = "    live_real_hard_block_required: bool = True\n"
        if marker not in text:
            raise RuntimeError("live_real_hard_block_required marker missing")
        text = text.replace(marker, CONFIG_BLOCK + marker, 1)
        path.write_text(text, encoding="utf-8", newline="\n")
        patched = True
    after = path.read_text(encoding="utf-8")
    return {"patched": patched, "before_missing": before_missing, "after_missing": [field for field in CONFIG_FIELDS if field not in after]}


def remove_payload_dirs(root: Path) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for rel in ("_patch_payload", "tools/_patch_payload"):
        path = root / rel
        if path.exists():
            shutil.rmtree(path)
        result[rel] = not path.exists()
    return result


def compile_targets(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in COMPILE_TARGETS:
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
    namespace: dict[str, Any] = {}
    checker = root / "tools" / "check_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py"
    exec(compile(checker.read_text(encoding="utf-8"), str(checker), "exec"), namespace)
    return namespace["run_check"](root)


def main() -> int:
    root = repo_root()
    config_patch = patch_config(root)
    payload_removed = remove_payload_dirs(root)
    compiled = compile_targets(root)
    report = run_check(root)
    report["config_patch"] = config_patch
    report["payload_removed"] = payload_removed
    report["compiled_after_apply"] = compiled
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} paper sandbox dry-run internal execution harness patch applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - patched_config_30i_missing_fields: {config_patch['patched']}")
    print(f" - root_patch_payload_removed: {payload_removed.get('_patch_payload')}")
    print(f" - tools_patch_payload_removed: {payload_removed.get('tools/_patch_payload')}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
