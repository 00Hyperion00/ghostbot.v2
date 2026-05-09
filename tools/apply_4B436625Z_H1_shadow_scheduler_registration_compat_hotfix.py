from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp005_shadow_collection_scheduler_pack.py", [
        "HYP005_SHADOW_SCHEDULER_PACK_HOTFIX_VERSION",
        "4B.4.3.6.6.25Z_H1",
        "25Z-H1 compatibility hotfix",
        "PSObject.Properties.Name",
        "DisallowStartIfOnBatteries",
        "StopIfGoingOnBatteries",
        "AllowStartIfOnBatteries",
        "$ReportsDir = Split-Path -Parent $PackDir",
        "$ProjectRoot = Split-Path -Parent $ReportsDir",
        "Test-Path (Join-Path $ProjectRoot \"tools\")",
    ]),
    ("tests/test_hyp005_shadow_collection_scheduler_pack_hotfix_25ZH1.py", [
        "test_25zh1_register_script_avoids_unsupported_battery_parameters",
        "test_25zh1_cycle_script_resolves_project_root_from_reports_pack_dir",
        "test_25zh1_scheduler_pack_still_ready_and_no_order",
    ]),
    ("docs/HYP005_SHADOW_SCHEDULER_REGISTRATION_COMPAT_HOTFIX_25ZH1.md", [
        "25Z-H1",
        "PowerShell compatibility",
        "Paper/live remain blocked",
    ]),
]

def main() -> None:
    print("4B.4.3.6.6.25Z-H1 HYP-005 scheduler registration compatibility hotfix applied")
    for rel, markers in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        if not exists:
            raise SystemExit(1)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)
            print(f" - {rel}_py_compile_ok: True")
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            present = marker in text
            print(f" - {marker}_present: {present}")
            if not present:
                raise SystemExit(1)

if __name__ == "__main__":
    main()
