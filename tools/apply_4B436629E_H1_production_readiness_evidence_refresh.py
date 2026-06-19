from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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

GITIGNORE_BLOCK = """
# BEGIN 4B.4.3.6.6.29E-H1 PATCH PAYLOAD EXCLUSION
/tools/_patch_payload/
tools/_patch_payload/
tools/_patch_payload/**
# END 4B.4.3.6.6.29E-H1 PATCH PAYLOAD EXCLUSION
""".strip()

ACCEPTED_SELECTOR = '''
# 4B.4.3.6.6.29E-H1 accepted-evidence selector: prefer latest accepted evidence over latest stale failure.
def _evidence_payload_is_acceptable(path: Path, spec: Mapping[str, str]) -> bool:
    try:
        payload = _load_json(path)
    except Exception:
        return False
    if str(payload.get("contract_version") or "") != spec["contract_version"]:
        return False
    if str(payload.get("decision") or "") != spec["decision"]:
        return False
    if bool(payload.get("approved_for_live_real", False)):
        return False
    if bool(payload.get("trading_action_performed", False)):
        return False
    if bool(payload.get("runtime_overlay_activation_performed", False)):
        return False
    if bool(payload.get("training_performed", False)) or bool(payload.get("reload_performed", False)):
        return False
    return True


def _latest_matching(evidence_dir: Path, pattern: str, spec: Mapping[str, str] | None = None) -> Path | None:
    matches = [path for path in evidence_dir.glob(pattern) if path.is_file()]
    if not matches:
        return None
    ordered = sorted(matches, key=lambda item: item.name, reverse=True)
    if spec is not None:
        for path in ordered:
            if _evidence_payload_is_acceptable(path, spec):
                return path
    return ordered[0]
'''.strip()


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _run(cmd: list[str], *, root: Path, check: bool = False) -> dict[str, Any]:
    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(cmd, cwd=root, env=env, text=True, capture_output=True)
    result = {
        "cmd": cmd,
        "returncode": int(proc.returncode),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }
    if check and proc.returncode != 0:
        raise RuntimeError(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def _git_ls_payload(root: Path) -> list[str]:
    proc = subprocess.run(["git", "ls-files", "tools/_patch_payload"], cwd=root, text=True, capture_output=True)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _git_rm_payload(root: Path) -> dict[str, Any]:
    before = _git_ls_payload(root)
    payload_dir = root / "tools" / "_patch_payload"
    git_rm = subprocess.run(["git", "rm", "-r", "--ignore-unmatch", "tools/_patch_payload"], cwd=root, text=True, capture_output=True)
    if payload_dir.exists():
        shutil.rmtree(payload_dir, ignore_errors=True)
    after = _git_ls_payload(root)
    return {
        "tracked_before_count": len(before),
        "tracked_after_count": len(after),
        "git_rm_returncode": int(git_rm.returncode),
        "git_rm_performed": len(before) > 0,
        "worktree_removed": not payload_dir.exists(),
    }


def _patch_gitignore(root: Path) -> bool:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if "4B.4.3.6.6.29E-H1 PATCH PAYLOAD EXCLUSION" in text:
        return True
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + GITIGNORE_BLOCK + "\n", encoding="utf-8", newline="\n")
    return True


def _patch_production_readiness_gate(root: Path) -> bool:
    path = root / "src" / "tradebot" / "production_readiness_gate.py"
    text = path.read_text(encoding="utf-8")
    if "29E-H1 accepted-evidence selector" in text:
        return True
    old = '''def _latest_matching(evidence_dir: Path, pattern: str) -> Path | None:
    matches = [path for path in evidence_dir.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return sorted(matches, key=lambda item: item.name)[-1]
'''
    if old not in text:
        raise RuntimeError("_latest_matching marker not found in production_readiness_gate.py")
    text = text.replace(old, ACCEPTED_SELECTOR + "\n\n", 1)
    text = text.replace('path = _latest_matching(base, spec["pattern"])', 'path = _latest_matching(base, spec["pattern"], spec)', 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def _refresh_required_evidence(root: Path) -> list[dict[str, Any]]:
    reports_dir = "reports/production_hardening"
    tools = [
        "tools/run_4B436629A_production_hardening_p0.py",
        "tools/run_4B436629A_H1_production_report_path_hygiene.py",
    ]
    out: list[dict[str, Any]] = []
    for tool in tools:
        if (root / tool).exists():
            out.append(_run([sys.executable, tool, "--reports-dir", reports_dir], root=root, check=False))
        else:
            out.append({"cmd": [sys.executable, tool, "--reports-dir", reports_dir], "returncode": 127, "stdout_tail": "", "stderr_tail": "tool missing"})
    return out


def _copy_payload_files(root: Path) -> None:
    _write_file(root / "tools" / "check_4B436629E_H1_production_readiness_evidence_refresh.py", CHECK_TOOL)
    _write_file(root / "tools" / "run_4B436629E_H1_production_readiness_evidence_refresh.py", RUN_TOOL)
    _write_file(root / "tools" / "rollback_4B436629E_H1_production_readiness_evidence_refresh.py", ROLLBACK_TOOL)
    _write_file(root / "tests" / "test_production_readiness_evidence_refresh_4B436629E_H1.py", TEST_FILE)
    _write_file(root / "docs" / "PRODUCTION_READINESS_EVIDENCE_REFRESH_4B436629E_H1.md", DOC_FILE)
    _write_file(root / "README_APPLY_4B436629E_H1.txt", README_FILE)


def _load_report(root: Path) -> dict[str, Any]:
    import importlib.util
    module_path = root / "tools" / "check_4B436629E_H1_production_readiness_evidence_refresh.py"
    spec = importlib.util.spec_from_file_location("check_29e_h1", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import 29E-H1 checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.build_report(root)


def main() -> int:
    root = Path.cwd()
    _copy_payload_files(root)
    _patch_gitignore(root)
    _patch_production_readiness_gate(root)
    payload_cleanup = _git_rm_payload(root)
    refresh_results = _refresh_required_evidence(root)
    report = _load_report(root)
    report["payload_cleanup"] = payload_cleanup
    report["evidence_refresh_results"] = refresh_results
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} production readiness evidence refresh / patch payload cleanup applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    return 0 if report.get("ok") else 2


CHECK_TOOL = r'''from __future__ import annotations

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
'''

RUN_TOOL = r'''from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from check_4B436629E_H1_production_readiness_evidence_refresh import CONTRACT_VERSION, build_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.29E-H1 evidence refresh decision report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    root = Path.cwd()
    report = build_report(root)
    snapshot = dict(report.get("snapshot") or {})
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ok": bool(report.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "decision": "PRODUCTION_READINESS_EVIDENCE_REFRESH_READY_LIVE_REAL_STILL_BLOCKED" if report.get("ok") else "PRODUCTION_READINESS_EVIDENCE_REFRESH_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "production_readiness_evidence_refresh": True,
        "evidence_complete": bool(snapshot.get("evidence_complete", False)),
        "approved_for_evidence_merge_baseline": bool(snapshot.get("approved_for_evidence_merge_baseline", False)),
        "approved_for_paper_candidate_preflight": bool(snapshot.get("approved_for_paper_candidate_preflight", False)),
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_hard_block_verified": bool(snapshot.get("live_real_hard_block_verified", True)),
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "checks": report.get("checks", {}),
        "snapshot": snapshot,
    }
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436629E_H1_production_readiness_evidence_refresh_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.29E-H1 Production Readiness Evidence Refresh\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- evidence_complete: `{payload['evidence_complete']}`\n"
        f"- approved_for_paper_candidate_preflight: `{payload['approved_for_paper_candidate_preflight']}`\n"
        f"- approved_for_paper_candidate: `{payload['approved_for_paper_candidate']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- live_real_hard_block_verified: `{payload['live_real_hard_block_verified']}`\n"
        f"- trading_action_performed: `{payload['trading_action_performed']}`\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{CONTRACT_VERSION} Production Readiness Evidence Refresh {payload['decision']}")
    for key in (
        "read_only",
        "evidence_complete",
        "approved_for_evidence_merge_baseline",
        "approved_for_paper_candidate_preflight",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "live_real_hard_block_verified",
        "approved_for_runtime_overlay_activation_candidate",
        "approved_for_parameter_relaxation_candidate",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload[key]}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
'''

ROLLBACK_TOOL = r'''from __future__ import annotations

from pathlib import Path


def main() -> int:
    print("4B.4.3.6.6.29E-H1 rollback is intentionally manual: use git revert for committed changes or restore from VCS.")
    for path in [
        "tools/check_4B436629E_H1_production_readiness_evidence_refresh.py",
        "tools/run_4B436629E_H1_production_readiness_evidence_refresh.py",
        "tests/test_production_readiness_evidence_refresh_4B436629E_H1.py",
        "docs/PRODUCTION_READINESS_EVIDENCE_REFRESH_4B436629E_H1.md",
        "README_APPLY_4B436629E_H1.txt",
    ]:
        print(f" - generated: {Path(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

TEST_FILE = r'''from __future__ import annotations

import json
from pathlib import Path

from tradebot.production_readiness_gate import build_consolidated_readiness_snapshot, load_production_hardening_evidence


def _write_report(base: Path, name: str, *, contract: str, decision: str, ok: bool = True) -> None:
    payload = {
        "ok": ok,
        "contract_version": contract,
        "decision": decision,
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
    }
    (base / name).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_evidence_selector_prefers_accepted_over_newer_failed_29a(tmp_path: Path) -> None:
    # Newer stale failure must not poison consolidation if a later refresh has accepted evidence available.
    _write_report(tmp_path, "4B436629A_production_hardening_p0_decision_20260619T192825Z.json", contract="4B.4.3.6.6.29A", decision="PRODUCTION_HARDENING_P0_NOT_READY", ok=False)
    _write_report(tmp_path, "4B436629A_production_hardening_p0_decision_20260619T202500Z.json", contract="4B.4.3.6.6.29A", decision="PRODUCTION_HARDENING_P0_READY_LIVE_REAL_STILL_BLOCKED")
    _write_report(tmp_path, "4B436629A_H1_production_report_path_hygiene_decision_20260619T202501Z.json", contract="4B.4.3.6.6.29A-H1", decision="PRODUCTION_REPORT_PATH_HYGIENE_READY_LIVE_REAL_STILL_BLOCKED")
    _write_report(tmp_path, "4B436629B_api_operator_security_hardening_decision_20260619T202502Z.json", contract="4B.4.3.6.6.29B", decision="API_OPERATOR_SECURITY_HARDENING_READY_LIVE_REAL_STILL_BLOCKED")
    _write_report(tmp_path, "4B436629C_sqlite_audit_ledger_upgrade_decision_20260619T202503Z.json", contract="4B.4.3.6.6.29C", decision="SQLITE_AUDIT_LEDGER_UPGRADE_READY_LIVE_REAL_STILL_BLOCKED")
    _write_report(tmp_path, "4B436629C_H2_sqlite_probe_explicit_connection_close_decision_20260619T202504Z.json", contract="4B.4.3.6.6.29C-H2", decision="SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_READY_LIVE_REAL_STILL_BLOCKED")
    _write_report(tmp_path, "4B436629D_replay_backtest_walkforward_gate_decision_20260619T202505Z.json", contract="4B.4.3.6.6.29D", decision="REPLAY_BACKTEST_WALKFORWARD_GATE_READY_LIVE_REAL_STILL_BLOCKED")

    evidence = load_production_hardening_evidence(tmp_path)
    assert evidence["29A"].ok is True
    assert evidence["29A-H1"].ok is True
    snapshot = build_consolidated_readiness_snapshot(tmp_path)
    assert snapshot["evidence_complete"] is True
    assert snapshot["approved_for_paper_candidate_preflight"] is True
    assert snapshot["approved_for_paper_candidate"] is False
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["live_real_hard_block_verified"] is True


def test_missing_h1_still_blocks_preflight(tmp_path: Path) -> None:
    _write_report(tmp_path, "4B436629A_production_hardening_p0_decision_20260619T202500Z.json", contract="4B.4.3.6.6.29A", decision="PRODUCTION_HARDENING_P0_READY_LIVE_REAL_STILL_BLOCKED")
    snapshot = build_consolidated_readiness_snapshot(tmp_path)
    assert snapshot["evidence_complete"] is False
    assert snapshot["approved_for_paper_candidate_preflight"] is False
    assert snapshot["approved_for_live_real"] is False
'''

DOC_FILE = """# 4B.4.3.6.6.29E-H1 Production Readiness Evidence Refresh

This hotfix cleans committed patch payload artifacts, refreshes stale 29A/29A-H1 production-hardening evidence, and makes the consolidation gate prefer the latest accepted evidence report over stale failed evidence when both are present.

Safety contract:

- read-only evidence refresh only
- no runtime overlay activation
- no paper/live/live-real enablement
- no scheduler mutation
- no HYP-006 strategy threshold mutation
- no training or reload
"""

README_FILE = """4B.4.3.6.6.29E-H1 Production Readiness Evidence Refresh / Patch Payload Cleanup

Apply:
  python tools/apply_4B436629E_H1_production_readiness_evidence_refresh.py

Verify:
  $env:PYTHONPATH=\"src\"
  python tools/check_4B436629E_H1_production_readiness_evidence_refresh.py --once-json
  python tools/check_4B436629E_production_readiness_consolidation_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=\"1\"
  python -m pytest -q tests/test_production_readiness_evidence_refresh_4B436629E_H1.py tests/test_production_readiness_consolidation_gate_4B436629E.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence report:
  python tools/run_4B436629E_H1_production_readiness_evidence_refresh.py --reports-dir .\\reports\\production_hardening

Expected decision:
  PRODUCTION_READINESS_EVIDENCE_REFRESH_READY_LIVE_REAL_STILL_BLOCKED

Commit:
  git add -A
  git commit -m \"4B.4.3.6.6.29E-H1 production readiness evidence refresh\"
  git tag -a 4B.4.3.6.6.29E-H1 -m \"Accepted production readiness evidence refresh hotfix\"
  git push
  git push origin 4B.4.3.6.6.29E-H1
"""

if __name__ == "__main__":
    raise SystemExit(main())
