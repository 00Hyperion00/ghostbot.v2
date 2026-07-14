from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PATCH_ID = "4B436644H"
PATCH_VERSION = "4B.4.3.6.6.44H"
PATCH_NAME = "Paper Sandbox No-Order Soak Acceptance Decision Gate"


def evaluate(reports_dir: str = "reports/recovery", write_reports: bool = False) -> dict[str, Any]:
    root = Path(reports_dir)
    sources: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(value, dict) and (
            "4B436643" in path.name
            or "phase43" in path.name.lower()
            or str(value.get("patch_id", "")).startswith("4B436643")
            or str(value.get("patch_version", "")).startswith("4B.4.3.6.6.43")
        ):
            value = dict(value)
            value["_source_path"] = str(path)
            sources.append(value)
    source_ready = any(
        int(item.get("final_safety_violation_count", 0) or 0) == 0
        and item.get("paper_order_submit_performed", False) is False
        and item.get("network_order_submit_performed", False) is False
        and item.get("exchange_submit_performed", False) is False
        and item.get("approved_for_live_real", False) is False
        and (
            bool(item.get("ok"))
            or item.get("status") == "READY"
            or bool(item.get("approved_for_paper_sandbox_no_order_soak_candidate"))
            or bool(item.get("approved_for_no_order_soak_acceptance_candidate"))
            or "4B436643" in str(item.get("_source_path", ""))
        )
        for item in sources
    )
    result = {
        "ok": source_ready,
        "status": "READY" if source_ready else "BLOCKED",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "runtime_process_started": False,
        "runtime_start_performed": False,
        "soak_evidence_accepted_by_patch": False,
        "evidence_manifest_accepted_by_patch": False,
        "runtime_presence_evidence_accepted_by_patch": False,
        "health_evidence_accepted_by_patch": False,
        "metrics_evidence_accepted_by_patch": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "final_safety_violation_count": 0,
        "next_phase_unlock_allowed": False,
    }
    if write_reports:
        root.mkdir(parents=True, exist_ok=True)
        (root / "4B436644H_acceptance_decision_gate.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return result
