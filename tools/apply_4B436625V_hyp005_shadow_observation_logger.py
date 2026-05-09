from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "HYP005_SHADOW_OBSERVATION_CONTRACT_VERSION"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "Hyp005ShadowRuntimeLimits"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "Hyp005ShadowCandidateRuntimeSpec"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "ShadowObservation"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "build_hyp005_shadow_observation_logger_report"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "HYP005_SHADOW_OBSERVATION_LOGGER_READY"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "NO_ORDER_SHADOW_LEDGER_READY"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "approved_for_live_real"),
    ("src/tradebot/research_hyp005_shadow_observation_logger.py", "post_requests_allowed"),
    ("tools/run_hyp005_shadow_observation_logger_4B436625V.py", "__candidate_spec_json"),
    ("tools/run_hyp005_shadow_observation_logger_4B436625V.py", "__input_csv"),
    ("tools/run_hyp005_shadow_observation_logger_4B436625V.py", "ledger_json"),
    ("tools/run_hyp005_shadow_observation_logger_4B436625V.py", "ledger_jsonl"),
    ("tools/run_hyp005_shadow_observation_logger_4B436625V.py", "method=\"GET\""),
    ("tools/run_hyp005_shadow_observation_logger_4B436625V.py", "public_market_data_GET_only"),
    ("tests/test_hyp005_shadow_observation_logger_4B436625V.py", "test_25v_validates_no_order_candidate_spec"),
    ("tests/test_hyp005_shadow_observation_logger_4B436625V.py", "test_25v_detects_shadow_liquidity_sweep_observation"),
    ("tests/test_hyp005_shadow_observation_logger_4B436625V.py", "test_tool_writes_report_and_ledger_files"),
    ("docs/HYP005_SHADOW_OBSERVATION_LOGGER_RUNBOOK_4B436625V.md", "HYP-005 Shadow Observation Logger"),
    ("docs/HYP005_SHADOW_OBSERVATION_LOGGER_RUNBOOK_4B436625V.md", "No-order runtime probe"),
    ("docs/HYP005_SHADOW_OBSERVATION_LOGGER_RUNBOOK_4B436625V.md", "Paper/live remain blocked"),
]


def main() -> int:
    print("4B.4.3.6.6.25V HYP-005 shadow observation logger / no-order runtime probe patch applied")
    seen: set[str] = set()
    for rel, marker in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        if not exists:
            continue
        if rel.endswith(".py") and rel not in seen:
            try:
                py_compile.compile(str(path), doraise=True)
                print(f" - {rel}_py_compile_ok: True")
            except py_compile.PyCompileError as exc:
                print(f" - {rel}_py_compile_ok: False {exc}")
            seen.add(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        print(f" - {marker.replace(' ', '_')}_present: {marker in text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
