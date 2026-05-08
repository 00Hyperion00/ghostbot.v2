from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/edge_meta_label_regime_recovery.py",
    "tools/run_edge_meta_label_regime_recovery_4B436624L.py",
    "tests/test_edge_meta_label_regime_recovery_4B436624L.py",
]
MARKERS = {
    "src/tradebot/edge_meta_label_regime_recovery.py": [
        "EDGE_META_LABEL_REGIME_CONTRACT_VERSION",
        "EdgeRegimeFilterSpec",
        "EdgeMetaLabelGateLimits",
        "evaluate_edge_meta_label_samples",
        "evaluate_two_stage_candidate_with_regime_filters",
        "META_LABEL_EXPECTED_EDGE_LOW",
        "META_LABEL_EDGE_LIFT_LOW",
        "approved_for_live_real",
    ],
    "tools/run_edge_meta_label_regime_recovery_4B436624L.py": [
        "REPORT_PREFIX",
        "--input-json",
        "--candidate-json",
        "--promote",
        "promotion_performed",
        "post_requests_allowed",
        "review-ok",
    ],
    "tests/test_edge_meta_label_regime_recovery_4B436624L.py": [
        "test_edge_meta_label_gate_passes_positive_regime_subset",
        "test_edge_meta_label_gate_blocks_negative_edge_subset",
        "test_tool_writes_report_from_candidate_json",
    ],
}


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception:
        return False
    return True


def main() -> int:
    print("4B.4.3.6.6.24L edge-aware meta-label / regime filter recovery patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        print(f" - {rel}_exists: {path.exists()}")
        print(f" - {rel}_py_compile_ok: {compile_ok(path) if path.exists() and path.suffix == '.py' else False}")
    doc = ROOT / "docs/EDGE_META_LABEL_REGIME_RECOVERY_RUNBOOK_4B436624L.md"
    print(f" - docs/EDGE_META_LABEL_REGIME_RECOVERY_RUNBOOK_4B436624L.md_exists: {doc.exists()}")
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            safe = marker.replace("-", "_").replace("=", "_")
            print(f" - {safe}_present: {marker in text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
