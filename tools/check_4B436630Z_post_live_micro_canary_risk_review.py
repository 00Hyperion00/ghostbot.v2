from __future__ import annotations

import argparse
import ast
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

TARGETS = [
    "src/tradebot/post_live_micro_canary_risk_review.py",
    "tools/run_4B436630Z_post_live_micro_canary_risk_review.py",
    "tools/check_4B436630Z_post_live_micro_canary_risk_review.py",
    "tools/apply_4B436630Z_post_live_micro_canary_risk_review.py",
    "tools/rollback_4B436630Z_post_live_micro_canary_risk_review.py",
    "tests/test_post_live_micro_canary_risk_review_4B436630Z.py",
    "docs/POST_LIVE_MICRO_CANARY_RISK_REVIEW_4B436630Z.md",
]

REQUIRED_MARKERS = {
    "src/tradebot/post_live_micro_canary_risk_review.py": [
        "CONTRACT_VERSION = \"4B.4.3.6.6.30Z\"",
        "POST_LIVE_MICRO_CANARY_RISK_REVIEW_READY_PNL_FEE_SLIPPAGE_EMERGENCY_STOP_NO_ADDITIONAL_LIVE_ORDER",
        "patch_network_submit_attempted=False",
        "approved_for_additional_live_order=False",
    ],
    "tools/run_4B436630Z_post_live_micro_canary_risk_review.py": [
        "--fee-amount",
        "--emergency-stop-armed",
    ],
}


def inspect() -> dict[str, object]:
    root = Path.cwd().resolve()
    missing: list[str] = []
    compile_failures: list[str] = []
    marker_failures: list[str] = []
    ast_failures: list[str] = []
    for rel in TARGETS:
        path = root / rel
        if not path.exists():
            missing.append(rel)
            continue
        if path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_failures.append(f"{rel}: {exc.msg}")
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                ast_failures.append(f"{rel}: {exc}")
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in REQUIRED_MARKERS.get(rel, []):
            if marker not in text:
                marker_failures.append(f"{rel}: missing {marker}")
    ok = not missing and not compile_failures and not marker_failures and not ast_failures
    return {
        "ok": ok,
        "contract_version": "4B.4.3.6.6.30Z",
        "missing": missing,
        "compile_failures": compile_failures,
        "ast_failures": ast_failures,
        "marker_failures": marker_failures,
        "exchange_submit_blocked": True,
        "network_submit_attempted": False,
        "live_real_order_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    result = inspect()
    if args.once_json:
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.30Z check ok={result['ok']}")
        if not result["ok"]:
            print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
