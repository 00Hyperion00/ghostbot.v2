from __future__ import annotations

import json
import py_compile
import shutil
import time
from pathlib import Path

PATCH_ID = '4B436633F_H1'
PATCH_VERSION = '4B.4.3.6.6.33F-H1'
PATCH_NAME = 'Source 33E Completion Gate Hotfix'
NEW_FUNCTION = 'def find_source_33e_status(repo_root: Path) -> Source33EStatus:\n    """Resolve the latest 33E READY source report.\n\n    33E-H1 can emit a full run report with nested sections. 33F-H1\n    accepts both the top-level check-summary shape and the nested run-report\n    shape while remaining fail-closed for missing, malformed, not READY, or\n    unresolved-conflict sources.\n    """\n    reports_dir = repo_root / "reports" / "recovery"\n    ready_candidates = [\n        path for path in reports_dir.glob("4B436633E_status_conflict_resolver_*_ready.json")\n        if "_not_ready" not in path.name.lower()\n    ]\n    all_candidates = list(reports_dir.glob("4B436633E_status_conflict_resolver_*.json"))\n    source = _latest(ready_candidates) or _latest(all_candidates)\n    if source is None:\n        return Source33EStatus(\n            complete=False,\n            report_path="",\n            status=None,\n            decision=None,\n            source_33d_complete=False,\n            status_conflict_resolution_complete=False,\n            unknown_evidence_triage_complete=False,\n            malformed_json_triage_complete=False,\n            unresolved_conflict_count=None,\n            residual_unknown_count=None,\n            error="source_33e_report_not_found",\n        )\n\n    payload, error = _read_json_object(source)\n    if payload is None:\n        return Source33EStatus(\n            complete=False,\n            report_path=_rel(source, repo_root),\n            status=None,\n            decision=None,\n            source_33d_complete=False,\n            status_conflict_resolution_complete=False,\n            unknown_evidence_triage_complete=False,\n            malformed_json_triage_complete=False,\n            unresolved_conflict_count=None,\n            residual_unknown_count=None,\n            error=error,\n        )\n\n    def _nested_bool(top_level_key: str, section_key: str | None = None, nested_key: str = "complete") -> bool:\n        if top_level_key in payload:\n            return _coerce_bool(payload.get(top_level_key))\n        if section_key:\n            section = payload.get(section_key)\n            if isinstance(section, dict) and nested_key in section:\n                return _coerce_bool(section.get(nested_key))\n        return False\n\n    def _nested_int(top_level_key: str, section_key: str | None = None, nested_key: str | None = None) -> int | None:\n        value = payload.get(top_level_key)\n        if value is None and section_key and nested_key:\n            section = payload.get(section_key)\n            if isinstance(section, dict):\n                value = section.get(nested_key)\n        try:\n            return int(value) if value is not None else None\n        except (TypeError, ValueError):\n            return None\n\n    status = str(payload.get("status") or "")\n    decision = str(payload.get("decision") or "")\n\n    source_33d_complete = _nested_bool("source_33d_complete", "source_gate")\n    status_conflict_complete = _nested_bool("status_conflict_resolution_complete", "status_conflict_summary")\n    unknown_complete = _nested_bool("unknown_evidence_triage_complete", "unknown_evidence_summary")\n    malformed_complete = _nested_bool("malformed_json_triage_complete", "malformed_json_summary")\n\n    unresolved_int = _nested_int("unresolved_conflict_count", "status_conflict_summary", "unresolved_conflict_count")\n    residual_int = _nested_int("residual_unknown_count", "unknown_evidence_summary", "residual_unknown_count")\n\n    source_gate = payload.get("source_gate")\n    if not source_33d_complete and isinstance(source_gate, dict):\n        source_33d_complete = _coerce_bool(source_gate.get("source_33d_runtime_safety_lockdown_complete"))\n\n    complete = (\n        status.upper() == "READY"\n        and decision == "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE"\n        and source_33d_complete\n        and status_conflict_complete\n        and unknown_complete\n        and malformed_complete\n        and (unresolved_int is None or unresolved_int == 0)\n    )\n\n    return Source33EStatus(\n        complete=complete,\n        report_path=_rel(source, repo_root),\n        status=status or None,\n        decision=decision or None,\n        source_33d_complete=source_33d_complete,\n        status_conflict_resolution_complete=status_conflict_complete,\n        unknown_evidence_triage_complete=unknown_complete,\n        malformed_json_triage_complete=malformed_complete,\n        unresolved_conflict_count=unresolved_int,\n        residual_unknown_count=residual_int,\n        error=None if complete else "source_33e_report_not_complete",\n    )\n'
README = '# Apply 4B.4.3.6.6.33F-H1 — Source 33E Completion Gate Hotfix\n\nPowerShell:\n\n```powershell\ncd C:\\Users\\muhas\\OneDrive\\Masaüstü\\trade_botV2\n\nExpand-Archive `\n  -Path "$env:USERPROFILE\\Downloads\\trade_botV2_4B436633F_H1_source_33e_gate_hotfix_patch.zip" `\n  -DestinationPath . `\n  -Force\n\npython tools/apply_4B436633F_H1_source_33e_gate_hotfix.py\n```\n'
DOC = '# 4B.4.3.6.6.33F-H1 — Source 33E Completion Gate Hotfix\n\nFixes 33F source gate parsing for 33E full run reports.\n\n33F originally accepted top-level check-summary fields. 33E run reports can store equivalent values in nested sections: `source_gate`, `status_conflict_summary`, `unknown_evidence_summary`, and `malformed_json_summary`.\n\nThis hotfix accepts both formats and remains fail-closed when the source is missing, malformed, not READY, or has unresolved conflicts.\n\nNo evidence files are modified. No cleanup, archive execution, submit, training, reload, runtime overlay, paper, live, or live-real approval is performed.\n'
CHECK = 'from __future__ import annotations\n\nimport argparse\nimport json\nimport sys\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nSRC = ROOT / "src"\nif str(SRC) not in sys.path:\n    sys.path.insert(0, str(SRC))\n\nfrom tradebot.evidence_retention_archive_policy import build_evidence_retention_archive_policy_report, summarize_report\n\n\ndef main() -> int:\n    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33F-H1 source 33E gate hotfix check")\n    parser.add_argument("--repo-root", default=".")\n    parser.add_argument("--once-json", action="store_true")\n    args = parser.parse_args()\n    report = build_evidence_retention_archive_policy_report(args.repo_root)\n    summary = summarize_report(report)\n    ok = report.status == "READY" and report.source_33e.complete\n    payload = {\n        "ok": ok,\n        "check_name": "source_33e_completion_gate_hotfix",\n        "patch_id": "4B436633F_H1",\n        "patch_version": "4B.4.3.6.6.33F-H1",\n        "status": "READY" if ok else "NOT_READY",\n        "decision": "SOURCE_33E_COMPLETION_GATE_HOTFIX_READY" if ok else "SOURCE_33E_COMPLETION_GATE_HOTFIX_NOT_READY",\n        "source_33e_complete": report.source_33e.complete,\n        "source_33e_report": report.source_33e.report_path,\n        "source_33e_error": report.source_33e.error,\n        "source_33f_status_after_hotfix": report.status,\n        "source_33f_decision_after_hotfix": report.decision,\n        "source_33f_ready_after_hotfix": report.status == "READY",\n        "retention_rules_complete": report.retention_rules_complete,\n        "report_retention_complete": report.report_retention.complete,\n        "backup_payload_archive_manifest_complete": report.backup_payload_archive_manifest.complete,\n        "non_destructive_cleanup_plan_complete": report.non_destructive_cleanup_plan.complete,\n        "evidence_aging_ledger_complete": report.evidence_aging_ledger.complete,\n        "destructive_cleanup_performed": report.safety_snapshot.destructive_cleanup_performed,\n        "exchange_submit_performed": report.safety_snapshot.exchange_submit_performed,\n        "trading_action_performed": report.safety_snapshot.trading_action_performed,\n        "training_performed": report.safety_snapshot.training_performed,\n        "reload_performed": report.safety_snapshot.reload_performed,\n        "runtime_overlay_activated": report.safety_snapshot.runtime_overlay_activated,\n        "approved_for_live_real": report.safety_snapshot.approved_for_live_real,\n        "approved_for_paper_transition": report.safety_snapshot.approved_for_paper_transition,\n        "approved_for_exchange_submit": report.safety_snapshot.approved_for_exchange_submit,\n        "approved_for_runtime_overlay": report.safety_snapshot.approved_for_runtime_overlay,\n        "evidence_retention_archive_policy_summary": summary,\n    }\n    print(json.dumps(payload, sort_keys=True, ensure_ascii=False) if args.once_json else json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'
RUN = 'from __future__ import annotations\n\nimport argparse\nimport json\nimport sys\nimport time\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nSRC = ROOT / "src"\nif str(SRC) not in sys.path:\n    sys.path.insert(0, str(SRC))\n\nfrom tradebot.evidence_retention_archive_policy import build_evidence_retention_archive_policy_report\n\n\ndef _write_json(path: Path, payload: object) -> None:\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")\n\n\ndef main() -> int:\n    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33F-H1 source 33E gate hotfix run")\n    parser.add_argument("--repo-root", default=".")\n    parser.add_argument("--reports-dir", default="reports/recovery")\n    parser.add_argument("--once-json", action="store_true")\n    args = parser.parse_args()\n    root = Path(args.repo_root).resolve()\n    report = build_evidence_retention_archive_policy_report(root)\n    ok = report.status == "READY" and report.source_33e.complete\n    payload = {\n        "ok": ok,\n        "check_name": "source_33e_completion_gate_hotfix",\n        "patch_id": "4B436633F_H1",\n        "patch_version": "4B.4.3.6.6.33F-H1",\n        "status": "READY" if ok else "NOT_READY",\n        "decision": "SOURCE_33E_COMPLETION_GATE_HOTFIX_READY" if ok else "SOURCE_33E_COMPLETION_GATE_HOTFIX_NOT_READY",\n        "source_33e_complete": report.source_33e.complete,\n        "source_33e_report": report.source_33e.report_path,\n        "source_33e_error": report.source_33e.error,\n        "source_33f_status_after_hotfix": report.status,\n        "source_33f_decision_after_hotfix": report.decision,\n        "source_33f_ready_after_hotfix": report.status == "READY",\n        "retention_rules_complete": report.retention_rules_complete,\n        "report_retention_complete": report.report_retention.complete,\n        "backup_payload_archive_manifest_complete": report.backup_payload_archive_manifest.complete,\n        "non_destructive_cleanup_plan_complete": report.non_destructive_cleanup_plan.complete,\n        "evidence_aging_ledger_complete": report.evidence_aging_ledger.complete,\n        "destructive_cleanup_performed": False,\n        "exchange_submit_performed": False,\n        "trading_action_performed": False,\n        "training_performed": False,\n        "reload_performed": False,\n        "runtime_overlay_activated": False,\n        "approved_for_live_real": False,\n        "approved_for_paper_transition": False,\n        "approved_for_exchange_submit": False,\n        "approved_for_runtime_overlay": False,\n    }\n    out_dir = (root / args.reports_dir).resolve() if not Path(args.reports_dir).is_absolute() else Path(args.reports_dir).resolve()\n    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())\n    suffix = "ready" if ok else "not_ready"\n    report_path = out_dir / f"4B436633F_H1_source_33e_gate_hotfix_{timestamp}_{suffix}.json"\n    _write_json(report_path, payload)\n    payload["report_path"] = str(report_path)\n    print(json.dumps(payload, sort_keys=True, ensure_ascii=False) if args.once_json else json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'
TESTS = 'from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nfrom tradebot.evidence_retention_archive_policy import (\n    READY_DECISION,\n    build_evidence_retention_archive_policy_report,\n    find_source_33e_status,\n)\n\n\ndef _write_json(path: Path, payload: object) -> None:\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(json.dumps(payload), encoding="utf-8")\n\n\ndef test_source_33e_gate_accepts_nested_33e_run_report(tmp_path: Path) -> None:\n    _write_json(\n        tmp_path / "reports/recovery/4B436633E_status_conflict_resolver_20260702T111131Z_ready.json",\n        {\n            "status": "READY",\n            "decision": "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE",\n            "source_gate": {"complete": True, "source_33d_runtime_safety_lockdown_complete": True},\n            "status_conflict_summary": {"complete": True, "unresolved_conflict_count": 0},\n            "unknown_evidence_summary": {"complete": True, "residual_unknown_count": 18},\n            "malformed_json_summary": {"complete": True},\n        },\n    )\n    source = find_source_33e_status(tmp_path)\n    assert source.complete is True\n    assert source.source_33d_complete is True\n    assert source.status_conflict_resolution_complete is True\n    assert source.unknown_evidence_triage_complete is True\n    assert source.malformed_json_triage_complete is True\n    assert source.unresolved_conflict_count == 0\n\n\ndef test_33f_ready_with_nested_33e_source(tmp_path: Path) -> None:\n    _write_json(\n        tmp_path / "reports/recovery/4B436633E_status_conflict_resolver_20260702T111131Z_ready.json",\n        {\n            "status": "READY",\n            "decision": "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE",\n            "source_gate": {"complete": True},\n            "status_conflict_summary": {"complete": True, "unresolved_conflict_count": 0},\n            "unknown_evidence_summary": {"complete": True, "residual_unknown_count": 18},\n            "malformed_json_summary": {"complete": True},\n        },\n    )\n    _write_json(tmp_path / "reports/recovery/4B436633E_unknown_evidence_classifier_ledger_20260702T111131Z.json", {"records": []})\n    (tmp_path / "tests/__pycache__").mkdir(parents=True)\n    (tmp_path / "tests/__pycache__/x.pyc").write_bytes(b"cache")\n    report = build_evidence_retention_archive_policy_report(tmp_path)\n    assert report.status == "READY"\n    assert report.decision == READY_DECISION\n    assert report.source_33e.complete is True\n    assert report.safety_snapshot.exchange_submit_performed is False\n    assert report.safety_snapshot.destructive_cleanup_performed is False\n\n\ndef test_source_33e_gate_still_blocks_unresolved_conflict(tmp_path: Path) -> None:\n    _write_json(\n        tmp_path / "reports/recovery/4B436633E_status_conflict_resolver_20260702T111131Z_ready.json",\n        {\n            "status": "READY",\n            "decision": "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE",\n            "source_gate": {"complete": True},\n            "status_conflict_summary": {"complete": True, "unresolved_conflict_count": 1},\n            "unknown_evidence_summary": {"complete": True},\n            "malformed_json_summary": {"complete": True},\n        },\n    )\n    source = find_source_33e_status(tmp_path)\n    assert source.complete is False\n    assert source.error == "source_33e_report_not_complete"\n'
ROLLBACK = 'from __future__ import annotations\n\nimport json\nimport shutil\nfrom pathlib import Path\n\nPATCH_ID = "4B436633F_H1"\n\n\ndef main() -> int:\n    root = Path(__file__).resolve().parents[1]\n    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"))\n    if not backups:\n        print(json.dumps({"rolled_back": False, "reason": "backup_not_found"}, sort_keys=True))\n        return 1\n    backup = backups[-1]\n    restored: list[str] = []\n    for path in backup.rglob("*"):\n        if path.is_file():\n            rel = path.relative_to(backup)\n            target = root / rel\n            target.parent.mkdir(parents=True, exist_ok=True)\n            shutil.copy2(path, target)\n            restored.append(rel.as_posix())\n    print(json.dumps({"rolled_back": True, "backup_root": str(backup.relative_to(root)), "restored_files": restored}, indent=2, sort_keys=True))\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _backup_existing(root: Path, rel_path: str, backup_root: Path, backed_up: list[str]) -> None:
    target = root / rel_path
    if not target.exists():
        return
    backup_path = backup_root / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup_path)
    backed_up.append(rel_path)


def _replace_function(text: str, function_name: str, replacement: str, next_function_name: str) -> tuple[str, bool]:
    start_marker = f"def {function_name}("
    start = text.find(start_marker)
    if start < 0:
        return text, False
    next_marker = f"\ndef {next_function_name}("
    end = text.find(next_marker, start)
    if end < 0:
        return text, False
    return text[:start] + replacement.rstrip() + "\n" + text[end:], True


def _patch_source(root: Path) -> dict[str, object]:
    rel = "src/tradebot/evidence_retention_archive_policy.py"
    path = root / rel
    if not path.exists():
        return {"patched": False, "path": rel, "reason": "source_missing"}
    text = path.read_text(encoding="utf-8")
    new_text, patched = _replace_function(text, "find_source_33e_status", NEW_FUNCTION, "default_retention_rules")
    if not patched:
        return {"patched": False, "path": rel, "reason": "function_boundary_not_found"}
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return {"patched": True, "path": rel, "reason": "source_33e_gate_replaced"}


def main() -> int:
    root = _repo_root()
    backup_root = root / "tools" / f"_patch_backup_{PATCH_ID}_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    backed_up: list[str] = []
    _backup_existing(root, "src/tradebot/evidence_retention_archive_policy.py", backup_root, backed_up)
    source_gate_patch_result = _patch_source(root)
    written_files: list[str] = []
    payloads = {
        "README_APPLY_4B436633F_H1.txt": README,
        "docs/EVIDENCE_RETENTION_ARCHIVE_POLICY_SOURCE_33E_GATE_HOTFIX_4B436633F_H1.md": DOC,
        "tests/test_evidence_retention_archive_policy_h1_4B436633F_H1.py": TESTS,
        "tools/check_4B436633F_H1_source_33e_gate_hotfix.py": CHECK,
        "tools/run_4B436633F_H1_source_33e_gate_hotfix.py": RUN,
        "tools/rollback_4B436633F_H1_source_33e_gate_hotfix.py": ROLLBACK,
    }
    for rel, content in payloads.items():
        target = root / rel
        if target.exists():
            _backup_existing(root, rel, backup_root, backed_up)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written_files.append(rel)
    compile_errors: dict[str, str] = {}
    for rel in [
        "src/tradebot/evidence_retention_archive_policy.py",
        "tests/test_evidence_retention_archive_policy_h1_4B436633F_H1.py",
        "tools/check_4B436633F_H1_source_33e_gate_hotfix.py",
        "tools/run_4B436633F_H1_source_33e_gate_hotfix.py",
        "tools/rollback_4B436633F_H1_source_33e_gate_hotfix.py",
    ]:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception as exc:
            compile_errors[rel] = str(exc)
    result = {
        "applied": bool(source_gate_patch_result.get("patched")) and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "source_gate_patch_result": source_gate_patch_result,
        "modified_files": ["src/tradebot/evidence_retention_archive_policy.py"] if source_gate_patch_result.get("patched") else [],
        "written_files": written_files,
        "backed_up_files": sorted(set(backed_up)),
        "backup_root": str(backup_root.relative_to(root)) if backed_up else "",
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "exchange_submit_performed": False,
        "runtime_overlay_activated": False,
        "destructive_cleanup_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
