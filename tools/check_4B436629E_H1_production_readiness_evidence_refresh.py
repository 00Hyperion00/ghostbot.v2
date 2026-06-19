from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29E-H1"
EXPECTED_FILES = [
    "docs/PRODUCTION_READINESS_EVIDENCE_REFRESH_4B436629E_H1.md",
    "tests/test_production_readiness_evidence_refresh_4B436629E_H1.py",
    "tools/apply_4B436629E_H1_production_readiness_evidence_refresh.py",
    "tools/check_4B436629E_H1_production_readiness_evidence_refresh.py",
    "tools/rollback_4B436629E_H1_production_readiness_evidence_refresh.py",
    "tools/run_4B436629E_H1_production_readiness_evidence_refresh.py",
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _git_ls_payload(root: Path) -> list[str]:
    proc = subprocess.run(["git", "ls-files", "tools/_patch_payload"], cwd=root, text=True, capture_output=True)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def build_report(root: Path) -> dict[str, Any]:
    import sys
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from tradebot.production_readiness_gate import build_consolidated_readiness_snapshot, load_production_hardening_evidence

    expected = {item: (root / item).exists() for item in EXPECTED_FILES}
    compile_targets = [
        root / "src/tradebot/production_readiness_gate.py",
        root / "tests/test_production_readiness_evidence_refresh_4B436629E_H1.py",
        root / "tools/apply_4B436629E_H1_production_readiness_evidence_refresh.py",
        root / "tools/check_4B436629E_H1_production_readiness_evidence_refresh.py",
        root / "tools/run_4B436629E_H1_production_readiness_evidence_refresh.py",
        root / "tools/rollback_4B436629E_H1_production_readiness_evidence_refresh.py",
    ]
    compiled = {str(path.relative_to(root)): _compile(path) for path in compile_targets if path.exists()}
    gate_text = (root / "src/tradebot/production_readiness_gate.py").read_text(encoding="utf-8")
    gitignore_text = (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").exists() else ""
    payload_tracked = _git_ls_payload(root)
    payload_dir_exists = (root / "tools/_patch_payload").exists()
    evidence = load_production_hardening_evidence(root / "reports/production_hardening")
    evidence_payload = {key: item.to_dict() for key, item in evidence.items()}
    snapshot = build_consolidated_readiness_snapshot(root / "reports/production_hardening")
    evidence_complete = bool(snapshot.get("evidence_complete", False))
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) and bool(compiled),
        "accepted_evidence_selector_present": "29E-H1 accepted-evidence selector" in gate_text,
        "accepted_evidence_selector_wired": '_latest_matching(base, spec["pattern"], spec)' in gate_text,
        "patch_payload_gitignore_policy_present": "tools/_patch_payload/" in gitignore_text,
        "patch_payload_not_tracked": len(payload_tracked) == 0,
        "patch_payload_removed_from_worktree": not payload_dir_exists,
        "evidence_29a_accepted": bool(evidence_payload.get("29A", {}).get("ok")),
        "evidence_29a_h1_accepted": bool(evidence_payload.get("29A-H1", {}).get("ok")),
        "evidence_29b_accepted": bool(evidence_payload.get("29B", {}).get("ok")),
        "evidence_29c_accepted": bool(evidence_payload.get("29C", {}).get("ok")),
        "evidence_29c_h2_accepted": bool(evidence_payload.get("29C-H2", {}).get("ok")),
        "evidence_29d_accepted": bool(evidence_payload.get("29D", {}).get("ok")),
        "evidence_complete": evidence_complete,
        "paper_candidate_preflight_ready": bool(snapshot.get("approved_for_paper_candidate_preflight", False)),
        "live_real_hard_block_verified": bool(snapshot.get("live_real_hard_block_verified", False)),
        "runtime_activation_blocked": bool(snapshot.get("runtime_activation_blocked", True)),
        "paper_live_order_blocked": bool(snapshot.get("paper_live_order_blocked", True)),
        "training_reload_blocked": bool(snapshot.get("training_reload_blocked", True)),
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "production_readiness_evidence_refresh": True,
        "read_only": True,
        "expected_files": expected,
        "compiled": compiled,
        "patch_payload_tracked_files": payload_tracked,
        "evidence": evidence_payload,
        "snapshot": snapshot,
        "checks": checks,
        "ok": all(checks.values()),
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
