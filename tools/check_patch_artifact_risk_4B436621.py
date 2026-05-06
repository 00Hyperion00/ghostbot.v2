"""Legacy patch risk scanner for 4B.4.3.6.6.21c.

The scanner is intentionally read-only. It lists historical patch/apply scripts that
should not be re-run after the stable 4B.4.3.6.6.20t11 + 21a/21b baseline.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

PHASE = "4B.4.3.6.6.21c"
STABLE_BASELINE = "4B.4.3.6.6.20t11 + 4B.4.3.6.6.21a/21b"
LATEST_ALLOWED_20_PATCH = "20t11"
HIGH_RISK_RE = re.compile(r"apply_4B436620(?P<tag>[a-z0-9]+).*\.py$", re.IGNORECASE)
CURRENT_TOOL_RE = re.compile(r"apply_4B436621[a-z0-9_]*.*\.py$", re.IGNORECASE)

HIGH_RISK_KEYWORDS = {
    "dashboard",
    "contract",
    "restore",
    "hotfix",
    "compat",
    "final",
    "root",
    "api_post",
    "position_text",
    "future_import",
    "syntax",
}

SAFE_21_KEYWORDS = {
    "acceptance",
    "runtime_smoke",
    "dashboard_contract",
    "dataclass",
    "optional_diagnostics",
    "legacy_patch",
}


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _tag_sort_key(tag: str) -> tuple[int, str]:
    # Tags look like: t10, t9, s2, r, p2, d, 11i, etc. Keep ordering stable.
    m = re.match(r"([a-z]+)(\d*)", tag.lower())
    if not m:
        return (999, tag.lower())
    prefix, number = m.group(1), m.group(2)
    prefix_rank = {chr(ord("a") + i): i for i in range(26)}.get(prefix[:1], 999)
    return (prefix_rank, f"{prefix}{int(number or 0):03d}")


def classify_patch(path: Path, root: Path) -> dict[str, Any]:
    name = path.name
    lower = name.lower()
    rel = str(path.relative_to(root)).replace("\\", "/")
    is_current_tool = bool(CURRENT_TOOL_RE.match(name))
    m = HIGH_RISK_RE.match(name)
    tag = m.group("tag").lower() if m else None

    risk_level = "none"
    reason_codes: list[str] = []
    recommendation = "KEEP"

    if m:
        risk_level = "high"
        recommendation = "ARCHIVE"
        reason_codes.append("LEGACY_4B436620_PATCH")
        if tag != LATEST_ALLOWED_20_PATCH:
            reason_codes.append("PRE_STABLE_20_PATCH")
        else:
            reason_codes.append("STABLE_BASELINE_PATCH")
        for keyword in sorted(HIGH_RISK_KEYWORDS):
            if keyword in lower:
                reason_codes.append(f"TOUCHES_{keyword.upper()}")
        if not any(code.startswith("TOUCHES_") for code in reason_codes):
            reason_codes.append("UNKNOWN_20_PATCH_SCOPE")
    elif is_current_tool:
        risk_level = "low"
        recommendation = "KEEP"
        reason_codes.append("CURRENT_4B436621_TOOLING")
        for keyword in sorted(SAFE_21_KEYWORDS):
            if keyword in lower:
                reason_codes.append(f"TOOLING_{keyword.upper()}")
    elif name.startswith("apply_") and name.endswith(".py"):
        risk_level = "medium"
        recommendation = "REVIEW"
        reason_codes.append("UNCLASSIFIED_APPLY_SCRIPT")

    return {
        "path": rel,
        "name": name,
        "tag": tag,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "reason_codes": reason_codes,
    }


def scan_legacy_patches(root: Path) -> dict[str, Any]:
    tools_dir = root / "tools"
    items: list[dict[str, Any]] = []
    if tools_dir.exists():
        for path in sorted(tools_dir.glob("apply_*.py"), key=lambda p: p.name.lower()):
            item = classify_patch(path, root)
            if item["risk_level"] != "none":
                items.append(item)

    high_risk = [item for item in items if item["risk_level"] == "high"]
    medium_risk = [item for item in items if item["risk_level"] == "medium"]
    low_risk = [item for item in items if item["risk_level"] == "low"]
    stable_seen = any(item.get("tag") == LATEST_ALLOWED_20_PATCH for item in high_risk)

    decision = "PASS"
    warnings: list[str] = []
    if high_risk:
        warnings.append("Legacy 4B436620 patch scripts are present. Do not run them after stable baseline.")
    if medium_risk:
        warnings.append("Unclassified apply scripts require manual review before release packaging.")
    if not tools_dir.exists():
        decision = "FAIL"
        warnings.append("tools directory not found")

    return {
        "phase": PHASE,
        "stable_baseline": STABLE_BASELINE,
        "latest_allowed_20_patch": LATEST_ALLOWED_20_PATCH,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "decision": decision,
        "summary": {
            "total_apply_scripts": len(items),
            "high_risk_legacy": len(high_risk),
            "medium_review": len(medium_risk),
            "low_current_tooling": len(low_risk),
            "stable_20t11_script_seen": stable_seen,
        },
        "warnings": warnings,
        "items": items,
    }


def _item_lines(items: list[dict[str, Any]], title: str) -> list[str]:
    lines = [f"## {title}", ""]
    if not items:
        lines.extend(["- None", ""])
        return lines
    for item in items:
        codes = ", ".join(item.get("reason_codes", [])) or "-"
        lines.append(f"- `{item['path']}` — **{item['risk_level']}** / {item['recommendation']} / {codes}")
    lines.append("")
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    items = list(report.get("items", []))
    high = [item for item in items if item.get("risk_level") == "high"]
    medium = [item for item in items if item.get("risk_level") == "medium"]
    low = [item for item in items if item.get("risk_level") == "low"]
    summary = report.get("summary", {})
    lines = [
        f"# {PHASE} Legacy Patch Risk Scanner",
        "",
        f"- Generated at: `{report.get('generated_at')}`",
        f"- Decision: **{report.get('decision')}**",
        f"- Stable baseline: `{report.get('stable_baseline')}`",
        f"- Latest valid 20-series baseline: `{report.get('latest_allowed_20_patch')}`",
        "",
        "## Summary",
        "",
        f"- Total apply scripts scanned: `{summary.get('total_apply_scripts', 0)}`",
        f"- High-risk legacy scripts: `{summary.get('high_risk_legacy', 0)}`",
        f"- Medium review scripts: `{summary.get('medium_review', 0)}`",
        f"- Current 21 tooling scripts: `{summary.get('low_current_tooling', 0)}`",
        "",
        "## Warnings",
        "",
    ]
    warnings = report.get("warnings", [])
    if warnings:
        lines.extend([f"- {warning}" for warning in warnings])
    else:
        lines.append("- None")
    lines.append("")
    lines.extend(_item_lines(high, "High-risk legacy scripts — archive recommended"))
    lines.extend(_item_lines(medium, "Medium-risk unclassified scripts — manual review"))
    lines.extend(_item_lines(low, "Current 21 tooling — keep"))
    lines.extend([
        "## Release Policy",
        "",
        "Do not re-run historical `apply_4B436620*.py` scripts after the stable `20t11` baseline.",
        "Use the archive tool only after reports are reviewed and a fresh backup exists.",
        "",
    ])
    return "\n".join(lines)


def write_reports(root: Path, report: dict[str, Any], prefix: str = "4B436621_legacy_patch_risk") -> tuple[Path, Path]:
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()
    json_path = reports_dir / f"{prefix}_{stamp}.json"
    md_path = reports_dir / f"{prefix}_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan legacy patch scripts for release-candidate risk.")
    parser.add_argument("--root", default=".", help="Project root. Default: current directory")
    parser.add_argument("--json-only", action="store_true", help="Print JSON report to stdout and skip file output")
    parser.add_argument("--fail-on-high-risk", action="store_true", help="Exit non-zero if legacy high-risk scripts are present")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    report = scan_legacy_patches(root)
    if args.json_only:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        json_path, md_path = write_reports(root, report)
        summary = report.get("summary", {})
        print(f"{PHASE} legacy patch risk scan {report.get('decision')}")
        print(f" - high_risk_legacy: {summary.get('high_risk_legacy', 0)}")
        print(f" - medium_review: {summary.get('medium_review', 0)}")
        print(f" - low_current_tooling: {summary.get('low_current_tooling', 0)}")
        print(f"JSON report: {json_path}")
        print(f"Markdown report: {md_path}")
    if args.fail_on_high_risk and report.get("summary", {}).get("high_risk_legacy", 0):
        return 2
    return 0 if report.get("decision") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
