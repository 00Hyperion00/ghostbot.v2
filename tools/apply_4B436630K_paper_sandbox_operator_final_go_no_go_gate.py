from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30K"
CONFIG_FIELDS = [
    "paper_sandbox_operator_final_go_no_go_gate_enabled",
    "paper_sandbox_operator_final_approval_required",
    "paper_sandbox_operator_final_approval_operator_id",
    "paper_sandbox_operator_final_approval_phrase",
    "paper_sandbox_operator_final_approval_token",
    "paper_sandbox_operator_final_approval_issued",
    "paper_sandbox_operator_final_approval_issued_at_ms",
    "paper_sandbox_operator_final_approval_ttl_sec",
    "paper_sandbox_operator_kill_switch_check_required",
    "paper_sandbox_operator_kill_switch_confirmed",
    "paper_sandbox_operator_caps_check_required",
    "paper_sandbox_operator_caps_confirmed",
    "paper_sandbox_operator_paper_candidate_still_blocked_required",
    "paper_sandbox_operator_no_live_real_required",
]
CONFIG_BLOCK = """
    # 4B.4.3.6.6.30K paper sandbox operator final go/no-go controls
    paper_sandbox_operator_final_go_no_go_gate_enabled: bool = True
    paper_sandbox_operator_final_approval_required: bool = True
    paper_sandbox_operator_final_approval_operator_id: str = ""
    paper_sandbox_operator_final_approval_phrase: str = "APPROVE_PAPER_SANDBOX_GO_NO_GO"
    paper_sandbox_operator_final_approval_token: str = ""
    paper_sandbox_operator_final_approval_issued: bool = False
    paper_sandbox_operator_final_approval_issued_at_ms: int = 0
    paper_sandbox_operator_final_approval_ttl_sec: int = 900
    paper_sandbox_operator_kill_switch_check_required: bool = True
    paper_sandbox_operator_kill_switch_confirmed: bool = False
    paper_sandbox_operator_caps_check_required: bool = True
    paper_sandbox_operator_caps_confirmed: bool = False
    paper_sandbox_operator_paper_candidate_still_blocked_required: bool = True
    paper_sandbox_operator_no_live_real_required: bool = True
"""
EXPECTED_FILES = [
    "README_APPLY_4B436630K.txt",
    "docs/PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_4B436630K.md",
    "src/tradebot/paper_sandbox_operator_final_go_no_go_gate.py",
    "tests/test_paper_sandbox_operator_final_go_no_go_gate_4B436630K.py",
    "tools/apply_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/rollback_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/run_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def patch_config(root: Path) -> dict[str, Any]:
    config = root / "src" / "tradebot" / "config.py"
    text = config.read_text(encoding="utf-8")
    before_missing = [field for field in CONFIG_FIELDS if field not in text]
    if not before_missing:
        return {"patched": False, "before_missing": [], "after_missing": []}
    anchor = "    live_real_hard_block_required: bool = True\n"
    if anchor not in text:
        raise RuntimeError("config.py anchor not found for 30K fields")
    text = text.replace(anchor, CONFIG_BLOCK + anchor, 1)
    config.write_text(text, encoding="utf-8", newline="\n")
    after = config.read_text(encoding="utf-8")
    return {"patched": True, "before_missing": before_missing, "after_missing": [field for field in CONFIG_FIELDS if field not in after]}


def remove_patch_artifacts(root: Path) -> dict[str, bool]:
    removed: dict[str, bool] = {}
    for rel in ("_patch_payload", "tools/_patch_payload", "_patch_backup", "tools/_patch_backup", "tests/_patch_backup", "docs/_patch_backup"):
        path = root / rel
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        removed[rel] = not path.exists()
    return removed


def run_checker(root: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(root / "tools" / "check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py"), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=300,
    )
    payload: dict[str, Any] = {"ok": False, "returncode": proc.returncode, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    try:
        parsed = json.loads(proc.stdout)
        if isinstance(parsed, dict):
            payload.update(parsed)
            payload["returncode"] = proc.returncode
    except json.JSONDecodeError:
        pass
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    copied = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    config_report = patch_config(root)
    removed = remove_patch_artifacts(root)
    checker = run_checker(root)
    report = {
        "ok": bool(checker.get("ok")) and all(copied.values()) and not config_report["after_missing"],
        "contract_version": CONTRACT_VERSION,
        "copied": copied,
        "config_patch": config_report,
        "removed_patch_artifacts": removed,
        "checker_report": checker,
        "read_only": True,
        "exchange_submit_performed": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not args.once_json:
        checks = checker.get("checks", {}) if isinstance(checker.get("checks"), dict) else {}
        print(f"{CONTRACT_VERSION} paper sandbox operator final go/no-go gate applied")
        for key in (
            "base_30j_checker_ok",
            "module_probe_ok",
            "module_probe_operator_approval_ok",
            "module_probe_kill_switch_caps_ok",
            "exchange_submit_still_blocked",
            "paper_execution_still_blocked",
            "paper_candidate_still_blocked",
            "live_real_still_blocked",
        ):
            print(f" - {key}: {checks.get(key)}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
