from __future__ import annotations

import py_compile
from pathlib import Path

PHASE = "4B.4.3.6.6.24I"
ROOT = Path(__file__).resolve().parents[1]

FILES = [
    "src/tradebot/cost_aware_label_policy_recovery.py",
    "tools/run_cost_aware_label_policy_recovery_4B436624I.py",
    "tests/test_cost_aware_label_policy_recovery_4B436624I.py",
    "docs/COST_AWARE_LABEL_POLICY_RECOVERY_RUNBOOK_4B436624I.md",
]

MARKERS = {
    "src/tradebot/cost_aware_label_policy_recovery.py": [
        "COST_AWARE_LABEL_POLICY_CONTRACT_VERSION",
        "CostAwareLabelPolicyCandidate",
        "CostAwareLabelPolicyGateLimits",
        "build_cost_aware_label_policy_recovery",
        "EXPECTED_NET_EDGE_LOW",
        "EFFECTIVE_MIN_PROFIT_BELOW_COST_FLOOR",
        "approved_for_live_real",
    ],
    "tools/run_cost_aware_label_policy_recovery_4B436624I.py": [
        "REPORT_PREFIX",
        "--input-csv",
        "--input-json",
        "method=\"GET\"",
        "post_requests_allowed",
        "review-ok",
    ],
    "tests/test_cost_aware_label_policy_recovery_4B436624I.py": [
        "test_cost_aware_gate_passes_directional_policy",
        "test_tool_writes_report_from_input_csv",
    ],
}


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception:
        return False
    return True


def main() -> int:
    print(f"{PHASE} cost-aware label policy recovery patch applied")
    ok = True
    for rel in FILES:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        ok = ok and exists
        if rel.endswith(".py") and exists:
            py_ok = compile_ok(path)
            print(f" - {rel}_py_compile_ok: {py_ok}")
            ok = ok and py_ok
    for rel, markers in MARKERS.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for marker in markers:
            present = marker in text
            print(f" - {marker}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
