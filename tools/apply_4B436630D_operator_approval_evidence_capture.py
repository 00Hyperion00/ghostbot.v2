from __future__ import annotations

import argparse
import json
import py_compile
import shutil
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30D"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
EXPECTED_FILES = [
    "docs/OPERATOR_APPROVAL_EVIDENCE_CAPTURE_4B436630D.md",
    "src/tradebot/paper_transition_approval_evidence_capture.py",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D.py",
    "tools/apply_4B436630D_operator_approval_evidence_capture.py",
    "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "tools/run_4B436630D_operator_approval_evidence_capture.py",
    "tools/rollback_4B436630D_operator_approval_evidence_capture.py",
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith(".py")]
CONFIG_FIELDS = [
    "paper_transition_approval_evidence_capture_enabled",
    "paper_transition_approval_evidence_operator_id_required",
    "paper_transition_approval_evidence_ttl_bound_required",
    "paper_transition_approval_evidence_snapshot_required",
    "paper_transition_approval_evidence_capture_report_required",
    "paper_transition_approval_evidence_require_30b_ready",
    "paper_transition_approval_evidence_require_30c_ready",
    "paper_transition_approval_evidence_still_no_order_enablement_required",
]
CONFIG_BLOCK = """
    # 4B.4.3.6.6.30D operator approval evidence capture controls
    paper_transition_approval_evidence_capture_enabled: bool = True
    paper_transition_approval_evidence_operator_id_required: bool = True
    paper_transition_approval_evidence_ttl_bound_required: bool = True
    paper_transition_approval_evidence_snapshot_required: bool = True
    paper_transition_approval_evidence_capture_report_required: bool = True
    paper_transition_approval_evidence_require_30b_ready: bool = True
    paper_transition_approval_evidence_require_30c_ready: bool = True
    paper_transition_approval_evidence_still_no_order_enablement_required: bool = True
"""


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def patch_config(root: Path) -> dict[str, Any]:
    config = root / "src" / "tradebot" / "config.py"
    text = config.read_text(encoding="utf-8")
    before_missing = [field for field in CONFIG_FIELDS if field not in text]
    if not before_missing:
        return {"patched": False, "before_missing": [], "after_missing": []}
    anchor = "    live_real_hard_block_required: bool = True\n"
    if anchor not in text:
        raise RuntimeError("config.py anchor not found for 30D fields")
    text = text.replace(anchor, CONFIG_BLOCK + anchor, 1)
    config.write_text(text, encoding="utf-8", newline="\n")
    after = config.read_text(encoding="utf-8")
    return {"patched": True, "before_missing": before_missing, "after_missing": [field for field in CONFIG_FIELDS if field not in after]}


def copy_payload(root: Path) -> None:
    payload = root / PAYLOAD_DIR
    if not payload.exists():
        raise FileNotFoundError(f"payload missing: {payload}")
    for src in payload.rglob("*"):
        if src.is_file():
            rel = src.relative_to(payload)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def compile_py(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in PY_FILES:
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_check(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    compiled = compile_py(root)
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    checks: dict[str, bool] = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": True,
        "config_30d_fields_present": False,
        "typed_approval_issuance_gate_present": False,
        "ttl_bound_approval_snapshot_gate_present": False,
        "runtime_envelope_freeze_token_gate_present": False,
        "final_risk_cap_evidence_gate_present": False,
        "paper_order_enablement_still_blocked": False,
        "live_real_blocked": False,
        "runtime_activation_blocked": False,
        "training_reload_blocked": False,
        "module_probe_ok": False,
    }
    config_text = (root / "src" / "tradebot" / "config.py").read_text(encoding="utf-8")
    checks["config_30d_fields_present"] = all(field in config_text for field in CONFIG_FIELDS)
    probe: dict[str, Any] = {"ok": False}
    try:
        from tradebot.paper_transition_approval_evidence_capture import (
            CONTRACT_VERSION as module_contract,
            READY_DECISION,
            INPUT_REQUIRED_DECISION,
            build_from_operator_inputs,
        )
        now = 1_800_000_000_000
        default_payload = build_from_operator_inputs(now_ms=now)
        approved_payload = build_from_operator_inputs(
            operator_id="operator-30d",
            confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
            freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
            issue_approval=True,
            freeze_runtime_envelope=True,
            verify_final_risk_cap=True,
            now_ms=now,
        )
        checks["contract_version_ok"] = module_contract == CONTRACT_VERSION
        checks["typed_approval_issuance_gate_present"] = bool(default_payload.get("operator_approval_evidence_capture_gate"))
        checks["ttl_bound_approval_snapshot_gate_present"] = bool(default_payload.get("ttl_bound_approval_snapshot_gate"))
        checks["runtime_envelope_freeze_token_gate_present"] = bool(default_payload.get("runtime_envelope_freeze_token_gate"))
        checks["final_risk_cap_evidence_gate_present"] = bool(default_payload.get("final_risk_cap_verification_evidence_gate"))
        checks["paper_order_enablement_still_blocked"] = bool(default_payload.get("paper_order_enablement_still_blocked")) and bool(approved_payload.get("paper_order_enablement_still_blocked")) and not bool(approved_payload.get("approved_for_paper_candidate"))
        checks["live_real_blocked"] = not bool(approved_payload.get("approved_for_live_real"))
        checks["runtime_activation_blocked"] = bool(approved_payload.get("runtime_activation_blocked"))
        checks["training_reload_blocked"] = bool(approved_payload.get("training_reload_blocked"))
        checks["module_probe_ok"] = (
            default_payload.get("decision") == INPUT_REQUIRED_DECISION
            and approved_payload.get("decision") == READY_DECISION
            and bool(approved_payload.get("approved_for_operator_approval_evidence_capture"))
            and bool(approved_payload.get("approved_for_paper_transition_candidate_review"))
            and not bool(approved_payload.get("approved_for_paper_transition_candidate"))
            and not bool(approved_payload.get("approved_for_paper_candidate"))
            and not bool(approved_payload.get("approved_for_live_real"))
            and not bool(approved_payload.get("trading_action_performed"))
        )
        probe = {
            "ok": checks["module_probe_ok"],
            "default_decision": default_payload.get("decision"),
            "approved_decision": approved_payload.get("decision"),
            "approved_capture": approved_payload.get("approved_for_operator_approval_evidence_capture"),
            "approved_review_only": approved_payload.get("approved_for_paper_transition_candidate_review"),
            "paper_candidate_still_blocked": not bool(approved_payload.get("approved_for_paper_candidate")),
            "live_real_still_blocked": not bool(approved_payload.get("approved_for_live_real")),
        }
    except Exception as exc:
        probe = {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}
    report = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "config_fields": {field: field in config_text for field in CONFIG_FIELDS},
        "module_probe": probe,
        "read_only": True,
        "paper_transition_approval_evidence_capture": True,
        "paper_live_order_enablement_present": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    return report


def main() -> int:
    root = repo_root()
    copy_payload(root)
    patch_result = patch_config(root)
    payload_dir = root / PAYLOAD_DIR
    shutil.rmtree(payload_dir.parent, ignore_errors=True)
    report = run_check(root)
    report["patch_result"] = patch_result
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    for key, value in report["checks"].items():
        print(f" - {key}: {value}")
    print(f" - patched_config_30d_missing_fields: {bool(patch_result.get('patched'))}")
    if not report.get("ok"):
        return 1
    print("4B.4.3.6.6.30D operator approval evidence capture patch applied")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
