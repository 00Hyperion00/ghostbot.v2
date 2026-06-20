from __future__ import annotations

import json
import py_compile
import shutil
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30D-H2"
MODULE_PATH = Path("src") / "tradebot" / "paper_transition_approval_evidence_capture.py"
OLD_WRITE_REPORT_BUNDLE = '''def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(json_path, payload)
    md_path.write_text(render_markdown_report(payload), encoding="utf-8", newline="\\n")
    return json_path, md_path
'''
NEW_WRITE_REPORT_BUNDLE = '''def _report_decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "unknown").strip().lower()
    if decision == READY_DECISION.lower():
        return "ready"
    if decision == INPUT_REQUIRED_DECISION.lower():
        return "input_required"
    if decision == NOT_READY_DECISION.lower():
        return "not_ready"
    slug = "".join(char if char.isalnum() else "_" for char in decision).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return (slug or "unknown")[:96]


def _unique_report_paths(target: Path, payload: Mapping[str, Any]) -> tuple[Path, Path]:
    stem = f"{REPORT_PREFIX}_{utc_stamp()}_{_report_decision_suffix(payload)}"
    for index in range(1000):
        suffix = "" if index == 0 else f"_{index:03d}"
        json_path = target / f"{stem}{suffix}.json"
        md_path = target / f"{stem}{suffix}.md"
        if not json_path.exists() and not md_path.exists():
            return json_path, md_path
    raise RuntimeError(f"could not allocate unique report path for {stem}")


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path, md_path = _unique_report_paths(target, payload)
    write_json_atomic(json_path, payload)
    md_path.write_text(render_markdown_report(payload), encoding="utf-8", newline="\\n")
    return json_path, md_path
'''
EXPECTED_FILES = [
    "README_APPLY_4B436630D_H2.txt",
    "docs/OPERATOR_APPROVAL_EVIDENCE_CAPTURE_4B436630D_H2.md",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D_H2.py",
    "tools/apply_4B436630D_H2_operator_approval_evidence_repo_hygiene.py",
    "tools/check_4B436630D_H2_operator_approval_evidence_repo_hygiene.py",
    "tools/rollback_4B436630D_H2_operator_approval_evidence_repo_hygiene.py",
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith(".py")] + [
    "src/tradebot/paper_transition_approval_evidence_capture.py",
    "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "tools/run_4B436630D_operator_approval_evidence_capture.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def remove_payload_dirs(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in ("_patch_payload", "tools/_patch_payload"):
        path = root / rel
        existed = path.exists()
        if existed:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        out[rel] = existed
    return out


def patch_gitignore(root: Path) -> dict[str, Any]:
    path = root / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = ["_patch_payload/", "tools/_patch_payload/"]
    lines = existing.splitlines()
    changed = False
    for item in additions:
        if item not in lines:
            lines.append(item)
            changed = True
    if changed:
        text = "\n".join(lines).rstrip() + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")
    return {"path": str(path), "changed": changed, "contains_root_payload_ignore": "_patch_payload/" in lines, "contains_tools_payload_ignore": "tools/_patch_payload/" in lines}


def patch_report_collision_guard(root: Path) -> dict[str, Any]:
    target = root / MODULE_PATH
    if not target.exists():
        raise FileNotFoundError(f"missing 30D module: {target}")
    text = target.read_text(encoding="utf-8")
    if "def _unique_report_paths(" in text and "_report_decision_suffix" in text:
        return {"patched": False, "already_present": True, "old_block_found": OLD_WRITE_REPORT_BUNDLE in text}
    if OLD_WRITE_REPORT_BUNDLE not in text:
        raise RuntimeError("30D write_report_bundle block not found; refusing partial patch")
    target.write_text(text.replace(OLD_WRITE_REPORT_BUNDLE, NEW_WRITE_REPORT_BUNDLE, 1), encoding="utf-8", newline="\n")
    after = target.read_text(encoding="utf-8")
    return {"patched": True, "already_present": False, "collision_guard_present": "def _unique_report_paths(" in after, "old_block_remaining": OLD_WRITE_REPORT_BUNDLE in after}


def compile_targets(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in PY_FILES:
        path = root / rel
        if not path.exists():
            out[rel] = False
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_check(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630D_H2_operator_approval_evidence_repo_hygiene.py"
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    namespace: dict[str, Any] = {}
    exec(compile(checker.read_text(encoding="utf-8"), str(checker), "exec"), namespace)
    return namespace["run_check"](root)


def main() -> int:
    root = repo_root()
    payload_removed = remove_payload_dirs(root)
    gitignore = patch_gitignore(root)
    module_patch = patch_report_collision_guard(root)
    compiled = compile_targets(root)
    report = run_check(root)
    report["payload_removed"] = payload_removed
    report["gitignore_patch"] = gitignore
    report["module_patch"] = module_patch
    report["compiled_after_apply"] = compiled
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.30D-H2 operator approval evidence repo hygiene hotfix applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - root_patch_payload_removed: {not (root / '_patch_payload').exists()}")
    print(f" - report_collision_guard_patched: {module_patch.get('patched') or module_patch.get('already_present')}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
