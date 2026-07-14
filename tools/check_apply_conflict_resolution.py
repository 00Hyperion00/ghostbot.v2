from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CONFLICT_FILES: dict[str, tuple[str, ...]] = {
    "README.md": (
        "docs/ARCHITECTURE.md",
        "docs/FINALIZATION_ROADMAP.md",
        "docs/ARCHITECTURE_CONFLICT_RESOLUTION.md",
        "PYTHONPATH=src",
    ),
    "docs/ARCHITECTURE.md": (
        "Current production intent",
        "Canonical runtime flow",
        "Canonical control plane",
        "Safety boundaries",
        "AI decision path",
        "Persistence contract",
        "Current high-value test slices",
    ),
    "src/tradebot/strategy.py": (
        "_StrategyEventLogger",
        "AI_PROVIDER_PREDICT_FAILED",
        "_build_ai_provider_failure_metrics",
        "aiProviderError",
        "aiFallbackMode",
        "event_logger",
    ),
    "tests/test_strategy_ai_merge.py": (
        "FailingProvider",
        "CapturingLogger",
        "ExplodingLogger",
        "AI_PROVIDER_PREDICT_FAILED",
        "aiProviderError",
        "aiFallbackMode",
    ),
}

CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")


def inspect_file(root: Path, relative: str, required_tokens: tuple[str, ...]) -> dict[str, Any]:
    path = root / relative
    if not path.exists():
        return {
            "path": relative,
            "exists": False,
            "conflict_markers_present": False,
            "missing_tokens": list(required_tokens),
            "ready": False,
        }
    text = path.read_text(encoding="utf-8", errors="ignore")
    missing = [token for token in required_tokens if token not in text]
    marker_present = any(marker in text for marker in CONFLICT_MARKERS)
    return {
        "path": relative,
        "exists": True,
        "line_count": len(text.splitlines()),
        "conflict_markers_present": marker_present,
        "missing_tokens": missing,
        "ready": not marker_present and not missing,
    }


def build_report(root: Path) -> dict[str, Any]:
    files = [inspect_file(root, path, tokens) for path, tokens in CONFLICT_FILES.items()]
    ready = all(item["ready"] for item in files)
    return {
        "check_name": "apply_conflict_resolution_status",
        "ready": ready,
        "status": "READY" if ready else "CONFLICT_RESOLUTION_REQUIRED",
        "conflict_file_count": len(files),
        "ready_file_count": sum(1 for item in files if item["ready"]),
        "files": files,
        "validation_commands": [
            "PYTHONPATH=src pytest -q tests/test_strategy_ai_merge.py tests/test_api_logs_compat.py tests/test_api_ai_reload.py tests/test_model_retrain_reload_workflow.py",
            "python -m compileall -q src/tradebot tests",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check apply conflict resolution status for high-churn production-readiness files.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path(args.repo_root).resolve())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
