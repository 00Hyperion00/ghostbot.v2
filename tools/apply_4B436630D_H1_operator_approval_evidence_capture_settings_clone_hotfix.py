from __future__ import annotations

import json
import py_compile
import shutil
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30D-H1"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
BAD_SETTINGS_KWARG_LINE = '            "paper_live_order_enablement_present": False,\n'
EXPECTED_PAYLOAD_FILES = [
    "docs/OPERATOR_APPROVAL_EVIDENCE_CAPTURE_4B436630D_H1.md",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D_H1.py",
    "tools/check_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py",
    "tools/rollback_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py",
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


def patch_30d_settings_clone(root: Path) -> dict[str, Any]:
    target = root / "src" / "tradebot" / "paper_transition_approval_evidence_capture.py"
    if not target.exists():
        raise FileNotFoundError("30D module missing; apply 30D before 30D-H1")
    text = target.read_text(encoding="utf-8")
    before_present = BAD_SETTINGS_KWARG_LINE in text
    if before_present:
        text = text.replace(BAD_SETTINGS_KWARG_LINE, "", 1)
        target.write_text(text, encoding="utf-8", newline="\n")
    after = target.read_text(encoding="utf-8")
    return {
        "patched": before_present,
        "unsupported_kwarg_before_present": before_present,
        "unsupported_kwarg_after_present": BAD_SETTINGS_KWARG_LINE in after,
    }


def compile_targets(root: Path) -> dict[str, bool]:
    targets = [
        "src/tradebot/paper_transition_approval_evidence_capture.py",
        "tests/test_paper_transition_approval_evidence_capture_4B436630D.py",
        "tests/test_paper_transition_approval_evidence_capture_4B436630D_H1.py",
        "tools/check_4B436630D_operator_approval_evidence_capture.py",
        "tools/check_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py",
        "tools/run_4B436630D_operator_approval_evidence_capture.py",
        "tools/rollback_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py",
    ]
    out: dict[str, bool] = {}
    for rel in targets:
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_h1_check(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py"
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    namespace: dict[str, Any] = {}
    code = checker.read_text(encoding="utf-8")
    exec(compile(code, str(checker), "exec"), namespace)
    return namespace["run_check"](root)


def main() -> int:
    root = repo_root()
    copy_payload(root)
    patch_result = patch_30d_settings_clone(root)
    compiled = compile_targets(root)
    report = run_h1_check(root)
    report["patch_result"] = patch_result
    report["compiled_after_apply"] = compiled
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.30D-H1 operator approval evidence capture settings clone hotfix applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - patched_settings_clone_unsupported_kwarg: {patch_result['patched']}")
    return 0 if report.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
