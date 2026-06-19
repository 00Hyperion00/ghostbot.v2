from __future__ import annotations

import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.29E-H2"
OLD = '"decision": "PRODUCTION_REPORT_PATH_HYGIENE_READY_LIVE_REAL_STILL_BLOCKED",'
NEW = '"decision": "PRODUCTION_REPORT_PATH_HYGIENE_READY",'


def _load_check_module(root: Path):  # type: ignore[no-untyped-def]
    path = root / "tools/check_4B436629E_H2_production_readiness_evidence_selector_compat.py"
    spec = importlib.util.spec_from_file_location("check_29e_h2", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def main() -> int:
    root = Path.cwd()
    backup_dir = root / "tools" / f"_patch_backup_4B436629E_H2_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = root / "src/tradebot/production_readiness_gate.py"
    if not target.exists():
        raise SystemExit("missing src/tradebot/production_readiness_gate.py")
    shutil.copy2(target, backup_dir / "production_readiness_gate.py")
    text = target.read_text(encoding="utf-8")
    patched_selector_decision = False
    if OLD in text:
        text = text.replace(OLD, NEW, 1)
        patched_selector_decision = True
    elif NEW in text:
        patched_selector_decision = True
    else:
        raise SystemExit("29A-H1 evidence decision marker not found")
    target.write_text(text, encoding="utf-8", newline="\n")

    module = _load_check_module(root)
    report = module.build_report(root)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} production readiness evidence selector compatibility patch applied")
    print(f" - patched_selector_decision: {patched_selector_decision}")
    for key in (
        "all_expected_files_present",
        "all_py_compile_ok",
        "evidence_selector_accepts_actual_29a_h1_decision",
        "stale_29a_h1_decision_removed",
        "accepted_evidence_selector_still_present",
        "sample_evidence_probe_ok",
        "actual_evidence_probe_ok",
        "evidence_complete",
        "paper_candidate_preflight_ready",
        "live_real_hard_block_verified",
        "runtime_activation_blocked",
        "paper_live_order_blocked",
        "training_reload_blocked",
    ):
        print(f" - {key}: {report['checks'].get(key)}")
    print(" - runtime_overlay_activation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    print(" - paper_live_order_enablement_present: False")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
