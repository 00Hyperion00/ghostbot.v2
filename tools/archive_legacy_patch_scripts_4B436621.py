"""Archive legacy patch scripts after 4B.4.3.6.6.21c review.

Default mode is dry-run. Use --apply to move high-risk 4B436620 apply scripts into
`tools/legacy_patches_4B436620/`. This tool never deletes files.
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from check_patch_artifact_risk_4B436621 import scan_legacy_patches
except Exception:  # pragma: no cover - import fallback when executed from project root
    import importlib.util
    import sys

    tool_path = Path(__file__).resolve().with_name("check_patch_artifact_risk_4B436621.py")
    spec = importlib.util.spec_from_file_location("check_patch_artifact_risk_4B436621", tool_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    scan_legacy_patches = module.scan_legacy_patches

PHASE = "4B.4.3.6.6.21c"
ARCHIVE_DIR_NAME = "legacy_patches_4B436620"


def archive_plan(root: Path) -> dict[str, Any]:
    report = scan_legacy_patches(root)
    candidates = [
        item for item in report.get("items", [])
        if item.get("risk_level") == "high" and str(item.get("path", "")).startswith("tools/")
    ]
    return {
        "phase": PHASE,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "archive_dir": f"tools/{ARCHIVE_DIR_NAME}",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def execute_archive(root: Path, plan: dict[str, Any], apply: bool = False) -> dict[str, Any]:
    tools_dir = root / "tools"
    archive_dir = tools_dir / ARCHIVE_DIR_NAME
    actions: list[dict[str, Any]] = []
    if apply:
        archive_dir.mkdir(parents=True, exist_ok=True)
    for item in plan.get("candidates", []):
        src = root / item["path"]
        dst = archive_dir / src.name
        action = {
            "source": str(src.relative_to(root)).replace("\\", "/"),
            "destination": str(dst.relative_to(root)).replace("\\", "/"),
            "status": "planned",
        }
        if apply:
            if not src.exists():
                action["status"] = "missing"
            elif dst.exists():
                action["status"] = "already_archived"
            else:
                shutil.move(str(src), str(dst))
                action["status"] = "moved"
        actions.append(action)
    return {
        "phase": PHASE,
        "applied": bool(apply),
        "archive_dir": f"tools/{ARCHIVE_DIR_NAME}",
        "actions": actions,
    }


def write_archive_report(root: Path, result: dict[str, Any]) -> Path:
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = reports_dir / f"4B436621_legacy_patch_archive_{stamp}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run or apply archival of legacy 4B436620 patch scripts.")
    parser.add_argument("--root", default=".", help="Project root. Default: current directory")
    parser.add_argument("--apply", action="store_true", help="Actually move files. Default is dry-run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    plan = archive_plan(root)
    result = execute_archive(root, plan, apply=args.apply)
    report_path = write_archive_report(root, result)
    mode = "APPLIED" if args.apply else "DRY-RUN"
    moved = sum(1 for action in result["actions"] if action.get("status") == "moved")
    print(f"{PHASE} legacy patch archive {mode}")
    print(f" - candidates: {len(result['actions'])}")
    print(f" - moved: {moved}")
    print(f" - archive_dir: {result['archive_dir']}")
    print(f"JSON report: {report_path}")
    if not args.apply:
        print("Dry-run only. Re-run with --apply after backup/review to move files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
