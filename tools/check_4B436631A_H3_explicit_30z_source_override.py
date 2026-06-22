from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.31A-H3"
CONFIG_FIELDS = [
    "live_micro_canary_freeze_audit_closure_enabled",
    "live_micro_canary_freeze_consume_30z_required",
    "live_micro_canary_freeze_no_further_live_orders_required",
    "live_micro_canary_freeze_evidence_pack_seal_required",
    "live_micro_canary_freeze_operator_audit_required",
    "live_micro_canary_freeze_release_hygiene_required",
    "live_micro_canary_freeze_finalization_token",
]
EXPECTED_FILES = [
    "README_APPLY_4B436631A_H3.txt",
    "docs/LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_4B436631A_H3.md",
    "README_APPLY_4B436631A.txt",
    "docs/LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_4B436631A.md",
    "src/tradebot/live_micro_canary_freeze_audit_closure.py",
    "tests/test_live_micro_canary_freeze_audit_closure_4B436631A.py",
    "tools/apply_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/check_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/rollback_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/run_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/apply_4B436631A_H3_explicit_30z_source_override.py",
    "tools/check_4B436631A_H3_explicit_30z_source_override.py",
    "tools/rollback_4B436631A_H3_explicit_30z_source_override.py",
]
PY_FILES = [
    "src/tradebot/live_micro_canary_freeze_audit_closure.py",
    "tests/test_live_micro_canary_freeze_audit_closure_4B436631A.py",
    "tools/apply_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/check_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/rollback_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/run_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/apply_4B436631A_H3_explicit_30z_source_override.py",
    "tools/check_4B436631A_H3_explicit_30z_source_override.py",
    "tools/rollback_4B436631A_H3_explicit_30z_source_override.py",
    "src/tradebot/config.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _compile(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out


def _run_json_tool(root: Path, rel: str) -> dict[str, Any]:
    if not (root / rel).exists():
        return {"ok": True, "skipped": True, "missing": rel}
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    proc = subprocess.run([sys.executable, str(root / rel), "--once-json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def _module_probe(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    code = '''
from pathlib import Path
import json, tempfile
from tradebot.config import Settings
from tradebot.live_micro_canary_freeze_audit_closure import FINALIZATION_TOKEN, READY_DECISION, build_live_micro_canary_freeze_audit_closure_snapshot
source = {
    "contract_version": "4B.4.3.6.6.30Z",
    "decision": "POST_LIVE_MICRO_CANARY_RISK_REVIEW_READY_PNL_FEE_SLIPPAGE_EMERGENCY_STOP_NO_ADDITIONAL_LIVE_ORDER",
    "ok": True,
    "source_30y_h1_reconciliation_verified": True,
    "real_fill_risk_review_verified": True,
    "pnl_evidence_verified": True,
    "fee_evidence_verified": True,
    "slippage_evidence_verified": True,
    "emergency_stop_continuity_verified": True,
    "no_additional_live_order_verified": True,
    "approved_for_additional_exchange_submit": False,
    "approved_for_live_real_continuation": False,
    "patch_exchange_submit_performed": False,
    "patch_network_submit_attempted": False,
}
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "4B436630X_first_live_real_micro_canary_1_ready.json").write_text("{}", encoding="utf-8")
    (root / "4B436630Y_live_real_micro_canary_reconciliation_1_ready.json").write_text("{}", encoding="utf-8")
    (root / "4B436630Z_post_live_micro_canary_risk_review_1_ready.json").write_text(json.dumps(source), encoding="utf-8")
    payload = build_live_micro_canary_freeze_audit_closure_snapshot(Settings(), source, reports_dir=root, operator_id="operator-31a", finalization_token=FINALIZATION_TOKEN, evidence_pack_id="LIVE_MICRO_CANARY_8114595899_CLOSURE")
print(json.dumps({"ok": payload["decision"] == READY_DECISION, "decision": payload["decision"], "evidence_pack_file_count": payload["evidence_pack_file_count"], "approved_for_additional_exchange_submit": payload["approved_for_additional_exchange_submit"], "patch_network_submit_attempted": payload["patch_network_submit_attempted"]}))
'''
    proc = subprocess.run([sys.executable, "-c", code], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def build_report(root: Path) -> dict[str, Any]:
    files = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8") if (root / "src/tradebot/config.py").exists() else ""
    config_fields = {field: field in config_text for field in CONFIG_FIELDS}
    compiled = _compile(root)
    base_30z = _run_json_tool(root, "tools/check_4B436630Z_post_live_micro_canary_risk_review.py")
    probe = _module_probe(root)
    checks = {
        "expected_files_ok": all(files.values()),
        "config_fields_ok": all(config_fields.values()),
        "py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "base_30z_checker_ok": bool(base_30z.get("ok")) or bool(base_30z.get("skipped")),
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_evidence_pack_file_count_ok": int(probe.get("evidence_pack_file_count") or 0) >= 3,
        "module_probe_no_additional_exchange_submit": probe.get("approved_for_additional_exchange_submit") is False,
        "module_probe_patch_network_submit_false": probe.get("patch_network_submit_attempted") is False,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "files": files,
        "config_fields": config_fields,
        "compiled": compiled,
        "base_30z_checker": base_30z,
        "module_probe": probe,
        "approved_for_additional_exchange_submit": False,
        "approved_for_live_real_continuation": False,
        "patch_exchange_submit_performed": False,
        "patch_network_submit_attempted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(repo_root())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
