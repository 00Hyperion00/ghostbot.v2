from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_ID = "4B436637I"
PATCH_VERSION = "4B.4.3.6.6.37I"
PATCH_NAME = "Fee / Slippage Baseline"

WRITTEN_FILES = [
    "README_APPLY_4B436637I.txt",
    "docs/FEE_SLIPPAGE_BASELINE_4B436637I.md",
    "src/tradebot/fee_slippage_baseline.py",
    "tests/test_fee_slippage_baseline_4B436637I.py",
    "tools/check_4B436637I_fee_slippage_baseline.py",
    "tools/run_4B436637I_fee_slippage_baseline.py",
    "tools/rollback_4B436637I_fee_slippage_baseline.py",
]


def compile_files(repo_root: Path) -> dict[str, str]:
    errors: dict[str, str] = {}
    for rel in WRITTEN_FILES:
        if not rel.endswith(".py"):
            continue
        try:
            py_compile.compile(str(repo_root / rel), doraise=True)
        except Exception as exc:  # pragma: no cover - returned to operator
            errors[rel] = f"{type(exc).__name__}: {exc}"
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    missing = [rel for rel in WRITTEN_FILES if not (repo_root / rel).exists()]
    compile_errors = compile_files(repo_root)
    result: dict[str, Any] = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "written_files": WRITTEN_FILES,
        "missing_files": missing,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "py_compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "fee_slippage_baseline_written": (repo_root / "src/tradebot/fee_slippage_baseline.py").exists(),
        "fee_slippage_source_mutation_performed": True,
        "fee_slippage_runtime_binding_performed": False,
        "fee_slippage_config_mutation_performed": False,
        "fee_model_runtime_binding_performed": False,
        "slippage_runtime_binding_performed": False,
        "break_even_runtime_binding_performed": False,
        "exchange_fee_lookup_performed": False,
        "account_fee_tier_lookup_performed": False,
        "market_data_lookup_performed": False,
        "book_depth_lookup_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "runtime_overlay_activated": False,
        "runtime_health_probe_performed": False,
        "runtime_readiness_unlock_performed": False,
        "runtime_start_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_performed": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "evidence_collection_started": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
