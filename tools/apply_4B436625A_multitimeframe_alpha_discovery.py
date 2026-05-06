from __future__ import annotations

import py_compile
from pathlib import Path

PHASE = "4B.4.3.6.6.25A"
ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/multitimeframe_alpha_discovery.py",
    "tools/run_multitimeframe_alpha_discovery_4B436625A.py",
    "tests/test_multitimeframe_alpha_discovery_4B436625A.py",
    "docs/MULTITIMEFRAME_ALPHA_DISCOVERY_RUNBOOK_4B436625A.md",
]
MARKERS = {
    "src/tradebot/multitimeframe_alpha_discovery.py": [
        "MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION",
        "MultiTimeframeAlphaCandidate",
        "MultiTimeframeAlphaGateLimits",
        "build_multitimeframe_alpha_discovery",
        "MTF_EXPECTED_NET_EDGE_LOW",
        "MTF_FORWARD_RETURN_SEPARATION_LOW",
        "approved_for_live_real",
    ],
    "tools/run_multitimeframe_alpha_discovery_4B436625A.py": [
        "REPORT_PREFIX",
        "--intervals",
        "--input-csv",
        "--input-json",
        "method=\"GET\"",
        "post_requests_allowed",
        "review-ok",
    ],
    "tests/test_multitimeframe_alpha_discovery_4B436625A.py": [
        "test_multitimeframe_alpha_gate_can_pass_directional_research_candidate",
        "test_tool_writes_report_from_input_csv",
    ],
}


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:
        print(f" - {path.as_posix()}_py_compile_error: {exc}")
        return False


def main() -> int:
    ok = True
    print(f"{PHASE} multi-timeframe alpha discovery / research reset patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        ok = ok and exists
        if exists and path.suffix == ".py":
            compiled = compile_ok(path)
            print(f" - {rel}_py_compile_ok: {compiled}")
            ok = ok and compiled
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            present = marker in text
            print(f" - {marker}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
