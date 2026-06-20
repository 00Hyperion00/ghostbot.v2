from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30E"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
CONFIG_MARKER = "# 4B.4.3.6.6.30E paper transition review rerun controls"
CONFIG_INSERT_BEFORE = "    live_real_hard_block_required: bool = True"
CONFIG_BLOCK = """    # 4B.4.3.6.6.30E paper transition review rerun controls
    paper_transition_review_rerun_enabled: bool = True
    paper_transition_review_rerun_consume_30d_ready_required: bool = True
    paper_transition_review_rerun_require_30c_ready: bool = True
    paper_transition_review_rerun_still_no_order_enablement_required: bool = True
    paper_transition_review_rerun_evidence_report_required: bool = True
"""
COPY_FILES = (
    "README_APPLY_4B436630E.txt",
    "docs/PAPER_TRANSITION_REVIEW_RERUN_4B436630E.md",
    "src/tradebot/paper_transition_review_rerun.py",
    "tests/test_paper_transition_review_rerun_4B436630E.py",
    "tools/apply_4B436630E_paper_transition_review_rerun.py",
    "tools/check_4B436630E_paper_transition_review_rerun.py",
    "tools/run_4B436630E_paper_transition_review_rerun.py",
    "tools/rollback_4B436630E_paper_transition_review_rerun.py",
)
REQUIRED_CONFIG_FIELDS = (
    "paper_transition_review_rerun_enabled",
    "paper_transition_review_rerun_consume_30d_ready_required",
    "paper_transition_review_rerun_require_30c_ready",
    "paper_transition_review_rerun_still_no_order_enablement_required",
    "paper_transition_review_rerun_evidence_report_required",
)


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _copy_files(root: Path, payload: Path) -> None:
    for rel in COPY_FILES:
        src = payload / rel
        dst = root / rel
        if not src.exists():
            raise FileNotFoundError(f"payload missing: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _patch_config(root: Path) -> dict[str, Any]:
    path = root / "src" / "tradebot" / "config.py"
    text = path.read_text(encoding="utf-8")
    before_missing = [field for field in REQUIRED_CONFIG_FIELDS if field not in text]
    patched = False
    if CONFIG_MARKER not in text:
        if CONFIG_INSERT_BEFORE not in text:
            raise RuntimeError("config insert anchor missing")
        text = text.replace(CONFIG_INSERT_BEFORE, CONFIG_BLOCK + CONFIG_INSERT_BEFORE, 1)
        path.write_text(text, encoding="utf-8", newline="\n")
        patched = True
    after = path.read_text(encoding="utf-8")
    after_missing = [field for field in REQUIRED_CONFIG_FIELDS if field not in after]
    return {"patched": patched, "before_missing": before_missing, "after_missing": after_missing}


def _cleanup_payload(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in ("_patch_payload", "tools/_patch_payload"):
        path = root / rel
        existed = path.exists()
        if existed:
            shutil.rmtree(path)
        out[rel] = existed and not path.exists()
    return out


def _ensure_gitignore(root: Path) -> dict[str, Any]:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    additions: list[str] = []
    for line in ("_patch_payload/", "_patch_payload/**", "tools/_patch_payload/", "tools/_patch_payload/**"):
        if line not in text:
            additions.append(line)
    if additions:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n# 4B.4.3.6.6.30E patch payload exclusion\n" + "\n".join(additions) + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")
    return {"changed": bool(additions), "added": additions}


def _run_check(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630E_paper_transition_review_rerun.py"
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    namespace: dict[str, Any] = {}
    exec(compile(checker.read_text(encoding="utf-8"), str(checker), "exec"), namespace)
    return namespace["build_report"](root)


def main() -> int:
    root = repo_root()
    payload = root / PAYLOAD_DIR
    if not payload.exists():
        raise SystemExit(f"payload directory not found: {payload}")
    _copy_files(root, payload)
    config_patch = _patch_config(root)
    gitignore_patch = _ensure_gitignore(root)
    payload_removed = _cleanup_payload(root)
    report = _run_check(root)
    report["config_patch"] = config_patch
    report["gitignore_patch"] = gitignore_patch
    report["payload_removed"] = payload_removed
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} paper transition review rerun patch applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - patched_config_30e_missing_fields: {bool(config_patch['before_missing']) and not config_patch['after_missing']}")
    print(f" - root_patch_payload_removed: {payload_removed.get('_patch_payload')}")
    print(f" - tools_patch_payload_removed: {payload_removed.get('tools/_patch_payload')}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
