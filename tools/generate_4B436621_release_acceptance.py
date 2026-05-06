import argparse
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PHASE = "4B.4.3.6.6.21d"
REPORT_STEM = "RELEASE_ACCEPTANCE_4B436621"
RUNBOOK_NAME = "OPERATOR_ACCEPTANCE_RUNBOOK_4B436621.md"

REPORT_PATTERNS = {
    "acceptance_gate": "4B436621_acceptance_*.json",
    "runtime_smoke": "4B436621_runtime_smoke_*.json",
    "dashboard_contract": "4B436621_dashboard_contract_*.json",
    "legacy_patch_risk": "4B436621_legacy_patch_risk_*.json",
    "legacy_patch_archive": "4B436621_legacy_patch_archive_*.json",
}

REQUIRED_REPORTS = ("acceptance_gate", "runtime_smoke", "dashboard_contract", "legacy_patch_risk", "legacy_patch_archive")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"raw": data}
    except Exception as exc:
        return {"load_error": str(exc)}


def latest_file(directory: Path, pattern: str) -> Path | None:
    files = [p for p in directory.glob(pattern) if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def truthy_pass(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"pass", "passed", "ok", "true", "success"}
    return False




def archive_report_passed(data: dict[str, Any]) -> bool:
    """Return True for 21c archive reports produced by archive_legacy_patch_scripts.

    21c archive reports do not contain a generic `passed/status/decision` field.
    Their source of truth is:
      - applied: True
      - actions: [{status: moved|already_archived|missing}, ...]

    `missing` is not a PASS state because it means the scanner planned a move but
    the file was not found during apply. Dry-run/planned reports are also not PASS.
    """
    if not isinstance(data, dict):
        return False
    if data.get("applied") is not True:
        return False
    actions = data.get("actions")
    if not isinstance(actions, list):
        return False
    allowed = {"moved", "already_archived"}
    return all(isinstance(item, dict) and item.get("status") in allowed for item in actions)


def archive_moved_count(data: dict[str, Any]) -> int | str:
    actions = data.get("actions") if isinstance(data, dict) else None
    if not isinstance(actions, list):
        return "-"
    return sum(1 for item in actions if isinstance(item, dict) and item.get("status") == "moved")

def extract_result(data: dict[str, Any], *, default: bool = False) -> bool:
    if archive_report_passed(data):
        return True
    for key in ("passed", "ok", "success", "gate_passed", "all_passed"):
        if key in data:
            return truthy_pass(data.get(key))
    status = data.get("status") or data.get("result") or data.get("decision")
    if status is not None:
        return truthy_pass(status)
    groups = data.get("groups") or data.get("results") or data.get("checks")
    if isinstance(groups, list) and groups:
        statuses = []
        for item in groups:
            if isinstance(item, dict):
                if "passed" in item:
                    statuses.append(truthy_pass(item.get("passed")))
                elif "ok" in item:
                    statuses.append(truthy_pass(item.get("ok")))
                elif "status" in item:
                    statuses.append(truthy_pass(item.get("status")))
        if statuses:
            return all(statuses)
    if isinstance(groups, dict) and groups:
        statuses = []
        for value in groups.values():
            if isinstance(value, dict):
                statuses.append(extract_result(value, default=False))
            else:
                statuses.append(truthy_pass(value))
        if statuses:
            return all(statuses)
    return default


def summarize_acceptance(data: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    groups = data.get("groups") or data.get("results") or []
    if isinstance(groups, list):
        for item in groups:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("group") or item.get("id") or "unknown")
            status = item.get("status") or ("PASS" if truthy_pass(item.get("passed")) else "FAIL")
            duration = item.get("duration_sec") or item.get("elapsed_sec") or item.get("duration") or "-"
            rows.append(f"| {name} | {status} | {duration} |")
    elif isinstance(groups, dict):
        for name, value in sorted(groups.items()):
            if isinstance(value, dict):
                status = value.get("status") or ("PASS" if extract_result(value) else "FAIL")
                duration = value.get("duration_sec") or value.get("elapsed_sec") or value.get("duration") or "-"
            else:
                status = "PASS" if truthy_pass(value) else "FAIL"
                duration = "-"
            rows.append(f"| {name} | {status} | {duration} |")
    return rows


def summarize_runtime(data: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    checks = data.get("checks") or data.get("results") or data.get("groups") or []
    if isinstance(checks, list):
        for item in checks:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("endpoint") or item.get("id") or "unknown")
            status = item.get("status") or ("PASS" if truthy_pass(item.get("passed") or item.get("ok")) else "FAIL")
            reason = str(item.get("reason") or item.get("message") or "-")
            rows.append(f"| {name} | {status} | {reason} |")
    elif isinstance(checks, dict):
        for name, value in sorted(checks.items()):
            if isinstance(value, dict):
                status = value.get("status") or ("PASS" if extract_result(value) else "FAIL")
                reason = value.get("reason") or value.get("message") or "-"
            else:
                status = "PASS" if truthy_pass(value) else "FAIL"
                reason = "-"
            rows.append(f"| {name} | {status} | {reason} |")
    return rows


def summarize_dashboard_contract(data: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    checks = data.get("checks") or data.get("results") or []
    if isinstance(checks, list):
        for item in checks:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("id") or "unknown")
                status = item.get("status") or ("PASS" if truthy_pass(item.get("passed") or item.get("ok")) else "FAIL")
                reason = str(item.get("reason") or item.get("message") or "-")
                rows.append(f"| {name} | {status} | {reason} |")
    elif isinstance(checks, dict):
        for name, value in sorted(checks.items()):
            if isinstance(value, dict):
                status = value.get("status") or ("PASS" if extract_result(value) else "FAIL")
                reason = value.get("reason") or value.get("message") or "-"
            else:
                status = "PASS" if truthy_pass(value) else "FAIL"
                reason = "-"
            rows.append(f"| {name} | {status} | {reason} |")
    return rows


def collect_reports(root: Path) -> dict[str, dict[str, Any]]:
    reports_dir = root / "reports"
    collected: dict[str, dict[str, Any]] = {}
    for key, pattern in REPORT_PATTERNS.items():
        path = latest_file(reports_dir, pattern)
        data = load_json(path) if path else {"missing": True}
        collected[key] = {
            "path": str(path.relative_to(root)) if path else None,
            "exists": path is not None,
            "data": data,
            "passed": extract_result(data, default=False) if path else False,
        }
    return collected


def evaluate_release(collected: dict[str, dict[str, Any]], *, strict: bool) -> tuple[str, list[str]]:
    reasons: list[str] = []
    for key in REQUIRED_REPORTS:
        entry = collected.get(key, {})
        if not entry.get("exists"):
            reasons.append(f"missing report: {key}")
        elif not entry.get("passed"):
            reasons.append(f"report not passing: {key}")
    if strict and reasons:
        return "FAIL", reasons
    if reasons:
        return "REVIEW", reasons
    return "PASS", ["All release gate reports exist and passed."]


def markdown_table_or_dash(rows: list[str], headers: str) -> str:
    if not rows:
        return "-"
    return "\n".join([headers, "|---|---|---|", *rows])


def build_release_markdown(collected: dict[str, dict[str, Any]], decision: str, reasons: list[str]) -> str:
    acceptance = collected["acceptance_gate"]["data"]
    runtime = collected["runtime_smoke"]["data"]
    dashboard = collected["dashboard_contract"]["data"]
    risk = collected["legacy_patch_risk"]["data"]
    archive = collected["legacy_patch_archive"]["data"]
    lines = [
        "# 4B.4.3.6.6.21 Release Acceptance Final Report",
        "",
        f"Generated at UTC: {utc_now()}",
        f"Python: {platform.python_version()}",
        f"Platform: {platform.platform()}",
        "",
        "## Release Decision",
        "",
        f"**Decision:** {decision}",
        "",
        "## Decision Reasons",
        "",
        *[f"- {reason}" for reason in reasons],
        "",
        "## Source Reports",
        "",
    ]
    for key, entry in collected.items():
        status = "PASS" if entry.get("passed") else "FAIL/MISSING"
        path = entry.get("path") or "-"
        lines.append(f"- {key}: {status} — `{path}`")
    lines.extend([
        "",
        "## Acceptance Test Matrix",
        "",
        markdown_table_or_dash(summarize_acceptance(acceptance), "| Group | Status | Duration sec |"),
        "",
        "## Runtime Smoke Matrix",
        "",
        markdown_table_or_dash(summarize_runtime(runtime), "| Check | Status | Reason |"),
        "",
        "## Dashboard Contract Matrix",
        "",
        markdown_table_or_dash(summarize_dashboard_contract(dashboard), "| Contract | Status | Reason |"),
        "",
        "## Legacy Patch Risk Summary",
        "",
        f"- High-risk legacy scripts: {risk.get('high_risk_legacy', risk.get('summary', {}).get('high_risk_legacy', '-'))}",
        f"- Medium review scripts: {risk.get('medium_review', risk.get('summary', {}).get('medium_review', '-'))}",
        f"- Low/current tooling: {risk.get('low_current_tooling', risk.get('summary', {}).get('low_current_tooling', '-'))}",
        f"- Archive moved: {archive_moved_count(archive)}",
        "",
        "## Operator Acceptance Statement",
        "",
        "The 4B.4.3.6.6.21 release candidate is accepted only if this report decision is PASS, the stable backup exists, and runtime smoke is executed against the intended local API instance.",
        "",
        "## Next Phase",
        "",
        "4B.4.3.6.6.22 — Live-demo supervised soak test.",
        "",
        "## Non-Negotiable Guardrails",
        "",
        "- Do not rerun archived 4B436620 dashboard patch scripts.",
        "- Do not arm real live trading in this release-candidate phase.",
        "- Keep `live_trading_armed=false` and `live_real_double_confirm=false` unless a dedicated live pilot phase explicitly changes them.",
        "- If any acceptance group fails, freeze feature work and fix the failing gate first.",
    ])
    return "\n".join(lines) + "\n"


def build_runbook_markdown() -> str:
    return r"""# 4B.4.3.6.6.21 Operator Acceptance Runbook

## Purpose

This runbook freezes the 4B.4.3.6.6.21 release candidate and gives the operator a repeatable acceptance path before moving to supervised live-demo soak testing.

## Required Starting Point

- Stable backup exists after 4B.4.3.6.6.20t11.
- 4B.4.3.6.6.21a acceptance runner installed.
- 4B.4.3.6.6.21b runtime smoke and dashboard contract checker installed.
- 4B.4.3.6.6.21c legacy patch scanner/archive completed.

## Acceptance Commands

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2
python -m compileall -q src tests tools
python tools/run_4B436621_acceptance_tests.py
python tools/check_dashboard_contract_4B436621.py
```

Start the API in a separate PowerShell and keep it open:

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2
$env:PYTHONPATH="$PWD\src"
python -m tradebot.cli api --config config.local.yaml --host 127.0.0.1 --port 8000
```

Run runtime smoke in another PowerShell:

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2
python tools/run_runtime_smoke_4B436621.py --base-url http://127.0.0.1:8000
```

Generate the final report:

```powershell
python tools/generate_4B436621_release_acceptance.py
```

## PASS Criteria

- Acceptance gate is PASS.
- Dashboard contract checker is PASS.
- Runtime smoke is PASS.
- Legacy high-risk scripts are archived or explicitly reviewed.
- No syntax/import errors exist.
- No critical config warning exists before supervised live-demo soak.

## Stop Conditions

- Any acceptance group fails.
- Runtime smoke cannot reach `/health` or `/status`.
- Dashboard contract checker fails.
- Archived dashboard patch scripts are accidentally restored to active `tools` flow.
- Config indicates real live trading is armed outside a dedicated live pilot phase.

## Next Phase

4B.4.3.6.6.22 — Live-demo supervised soak test.
"""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def generate(root: Path, *, strict: bool) -> dict[str, Any]:
    collected = collect_reports(root)
    decision, reasons = evaluate_release(collected, strict=strict)
    payload = {
        "phase": PHASE,
        "generated_at_utc": utc_now(),
        "decision": decision,
        "reasons": reasons,
        "reports": collected,
    }
    reports_dir = root / "reports"
    docs_dir = root / "docs"
    write_json(reports_dir / f"{REPORT_STEM}.json", payload)
    write_text(reports_dir / f"{REPORT_STEM}.md", build_release_markdown(collected, decision, reasons))
    write_text(docs_dir / RUNBOOK_NAME, build_runbook_markdown())
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.21 final release acceptance report and operator runbook.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--review-ok", action="store_true", help="Exit 0 when reports are missing/non-passing but decision is REVIEW instead of PASS.")
    parser.add_argument("--strict", action="store_true", help="Missing or non-passing source reports produce FAIL decision and non-zero exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    payload = generate(root, strict=args.strict)
    decision = str(payload["decision"])
    print(f"4B.4.3.6.6.21d release acceptance report generated: {decision}")
    print(f" - reports/{REPORT_STEM}.json")
    print(f" - reports/{REPORT_STEM}.md")
    print(f" - docs/{RUNBOOK_NAME}")
    if decision == "PASS":
        return 0
    if decision == "REVIEW" and args.review_ok:
        return 0
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
