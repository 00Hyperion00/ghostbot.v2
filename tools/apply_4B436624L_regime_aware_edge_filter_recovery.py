from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/regime_aware_edge_filter_recovery.py",
    "tools/run_regime_aware_edge_filter_recovery_4B436624L.py",
    "tests/test_regime_aware_edge_filter_recovery_4B436624L.py",
    "docs/REGIME_AWARE_EDGE_FILTER_RECOVERY_RUNBOOK_4B436624L.md",
]
MARKERS = {
    "REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION": "src/tradebot/regime_aware_edge_filter_recovery.py",
    "RegimeEdgeFilterLimits": "src/tradebot/regime_aware_edge_filter_recovery.py",
    "evaluate_regime_filter_candidate": "src/tradebot/regime_aware_edge_filter_recovery.py",
    "train_regime_edge_filter_candidates": "src/tradebot/regime_aware_edge_filter_recovery.py",
    "REGIME_FILTER_EXPECTED_EDGE_LOW": "src/tradebot/regime_aware_edge_filter_recovery.py",
    "REGIME_FILTER_PRECISION_LIFT_LOW": "src/tradebot/regime_aware_edge_filter_recovery.py",
    "approved_for_live_real": "src/tradebot/regime_aware_edge_filter_recovery.py",
    "REPORT_PREFIX": "tools/run_regime_aware_edge_filter_recovery_4B436624L.py",
    "--input-json": "tools/run_regime_aware_edge_filter_recovery_4B436624L.py",
    "method=\"GET\"": "docs/REGIME_AWARE_EDGE_FILTER_RECOVERY_RUNBOOK_4B436624L.md",
    "post_requests_allowed": "src/tradebot/regime_aware_edge_filter_recovery.py",
    "review-ok": "tools/run_regime_aware_edge_filter_recovery_4B436624L.py",
    "test_regime_filter_gate_passes_positive_edge_filter": "tests/test_regime_aware_edge_filter_recovery_4B436624L.py",
}


def main() -> int:
    print("4B.4.3.6.6.24L regime-aware edge filter recovery patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        if exists and path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
                print(f" - {rel}_py_compile_ok: True")
            except Exception as exc:
                print(f" - {rel}_py_compile_ok: False ({exc})")
                return 1
    for marker, rel in MARKERS.items():
        path = ROOT / rel
        present = path.exists() and marker in path.read_text(encoding="utf-8", errors="ignore")
        print(f" - {marker}_present: {present}")
        if not present:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
