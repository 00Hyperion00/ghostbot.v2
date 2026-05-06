from __future__ import annotations
import py_compile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CHECKS = ["src/tradebot/calibration_policy_gate.py", "tools/run_calibration_policy_gate_4B436624F.py", "tests/test_calibration_policy_gate_4B436624F.py", "docs/CALIBRATION_POLICY_GATE_RUNBOOK_4B436624F.md"]
MARKERS = {"src/tradebot/calibration_policy_gate.py": ["CALIBRATION_POLICY_GATE_CONTRACT_VERSION", "CalibrationPolicyGateLimits", "build_calibration_policy_gate", "DIAGNOSTIC_PROFILE_NOT_APPROVABLE", "ZERO_MARGIN_PROFILE_NOT_APPROVABLE", "approved_for_live_real"], "tools/run_calibration_policy_gate_4B436624F.py": ["REPORT_PREFIX", "method=\"GET\"", "post_requests_allowed", "--input-json", "approved_for_paper_candidate"]}

def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True); return True
    except py_compile.PyCompileError:
        return False

def main() -> int:
    print("4B.4.3.6.6.24F calibration policy candidate gate patch applied"); ok = True
    for rel in CHECKS:
        path = ROOT / rel; exists = path.exists(); print(f" - {rel}_exists: {exists}"); ok = ok and exists
        if path.suffix == ".py" and exists:
            compiled = compile_ok(path); print(f" - {rel}_py_compile_ok: {compiled}"); ok = ok and compiled
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            present = marker in text; print(f" - {marker}_present: {present}"); ok = ok and present
    return 0 if ok else 1
if __name__ == "__main__":
    raise SystemExit(main())
