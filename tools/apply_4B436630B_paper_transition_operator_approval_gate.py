from __future__ import annotations

import json
import py_compile
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30B"
ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "tools" / "_patch_payload" / CONTRACT_VERSION
CONFIG_FIELDS_BLOCK = """
    # 4B.4.3.6.6.30B paper transition operator approval gate controls
    paper_transition_operator_id: str = ""
    paper_transition_approval_issued_at_ms: int = 0
    paper_transition_approval_ttl_sec: int = 900
    paper_transition_runtime_envelope: str = "sandbox_only"
    paper_transition_dry_run_reconciliation_required: bool = True
    paper_transition_dry_run_reconciliation_probe_passed: bool = True
    paper_transition_dry_run_probe_order_actions_performed: bool = False
    paper_transition_max_open_orders: int = 1
""".strip("\n")
CONFIG_FIELDS = [line.split(":", 1)[0].strip() for line in CONFIG_FIELDS_BLOCK.splitlines() if ":" in line]
EXPECTED_FILES = [
    "src/tradebot/paper_transition_operator_gate.py",
    "tests/test_paper_transition_operator_gate_4B436630B.py",
    "tools/apply_4B436630B_paper_transition_operator_approval_gate.py",
    "tools/check_4B436630B_paper_transition_operator_approval_gate.py",
    "tools/run_4B436630B_paper_transition_operator_approval_gate.py",
    "tools/rollback_4B436630B_paper_transition_operator_approval_gate.py",
    "docs/PAPER_TRANSITION_OPERATOR_APPROVAL_GATE_4B436630B.md",
]


def _copy_with_retry(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(8):
        try:
            shutil.copy2(src, dst)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.25)


def _copy_payload() -> None:
    if not PAYLOAD.exists():
        raise FileNotFoundError(f"Patch payload not found: {PAYLOAD}")
    for src in PAYLOAD.rglob("*"):
        if src.is_file():
            rel = src.relative_to(PAYLOAD)
            _copy_with_retry(src, ROOT / rel)


def _patch_config() -> dict[str, Any]:
    config_path = ROOT / "src/tradebot/config.py"
    text = config_path.read_text(encoding="utf-8")
    before_missing = [field for field in CONFIG_FIELDS if field not in text]
    patched = False
    if before_missing:
        marker = '    live_real_hard_block_required: bool = True\n'
        if marker in text:
            text = text.replace(marker, CONFIG_FIELDS_BLOCK + "\n" + marker, 1)
        else:
            anchor = '    @classmethod\n'
            if anchor not in text:
                raise RuntimeError("Settings class insertion anchor not found")
            text = text.replace(anchor, CONFIG_FIELDS_BLOCK + "\n\n" + anchor, 1)
        config_path.write_text(text, encoding="utf-8", newline="\n")
        patched = True
    after = config_path.read_text(encoding="utf-8")
    return {"before_missing": before_missing, "after_missing": [field for field in CONFIG_FIELDS if field not in after], "patched": patched}


def _ensure_gitignore() -> None:
    path = ROOT / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if "tools/_patch_payload/" not in text:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "tools/_patch_payload/\n"
        path.write_text(text, encoding="utf-8", newline="\n")


def _cleanup_payload_tracking() -> dict[str, Any]:
    _ensure_gitignore()
    tracked: list[str] = []
    try:
        proc = subprocess.run(["git", "ls-files", "tools/_patch_payload"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        tracked = [line for line in proc.stdout.splitlines() if line.strip()]
        if tracked:
            subprocess.run(["git", "rm", "-r", "--cached", "--ignore-unmatch", "tools/_patch_payload"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except Exception:
        tracked = []
    shutil.rmtree(ROOT / "tools/_patch_payload", ignore_errors=True)
    return {"tracked_before_count": len(tracked), "worktree_removed": not (ROOT / "tools/_patch_payload").exists()}


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _run_checker() -> dict[str, Any]:
    proc = subprocess.run([sys.executable, "tools/check_4B436630B_paper_transition_operator_approval_gate.py", "--once-json"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"ok": False, "stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
    return payload


def main() -> int:
    _copy_payload()
    patch_result = _patch_config()
    cleanup = _cleanup_payload_tracking()
    report = _run_checker()
    report["patch_result"] = patch_result
    report["payload_cleanup"] = cleanup
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} paper transition operator approval gate patch applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - patched_config_30b_missing_fields: {not patch_result['after_missing']}")
    print(" - runtime_overlay_activation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    print(" - paper_live_order_enablement_present: False")
    return 0 if report.get("ok") and not patch_result["after_missing"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
