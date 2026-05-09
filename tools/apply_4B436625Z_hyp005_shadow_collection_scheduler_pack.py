from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp005_shadow_collection_scheduler_pack.py", "HYP005_SHADOW_SCHEDULER_PACK_CONTRACT_VERSION"),
    ("src/tradebot/research_hyp005_shadow_collection_scheduler_pack.py", "SchedulerPackRequest"),
    ("src/tradebot/research_hyp005_shadow_collection_scheduler_pack.py", "build_hyp005_shadow_scheduler_pack_report"),
    ("src/tradebot/research_hyp005_shadow_collection_scheduler_pack.py", "NO_ORDER_SCHEDULER_PACK_ONLY"),
    ("src/tradebot/research_hyp005_shadow_collection_scheduler_pack.py", "WINDOWS_TASK_SCHEDULER_MANUAL_IMPORT_ONLY"),
    ("src/tradebot/research_hyp005_shadow_collection_scheduler_pack.py", "run_hyp005_shadow_cycle_no_order.ps1"),
    ("src/tradebot/research_hyp005_shadow_collection_scheduler_pack.py", "register_hyp005_shadow_cycle_task.ps1"),
    ("tools/run_hyp005_shadow_collection_scheduler_pack_4B436625Z.py", "--review-ok"),
    ("tools/run_hyp005_shadow_collection_scheduler_pack_4B436625Z.py", "--task-name"),
    ("tests/test_hyp005_shadow_collection_scheduler_pack_4B436625Z.py", "test_25z_builds_scheduler_pack_from_25y_audit"),
    ("docs/HYP005_SHADOW_COLLECTION_SCHEDULER_PACK_4B436625Z.md", "Paper/live remain blocked"),
]
PY_COMPILE = [
    "src/tradebot/research_hyp005_shadow_collection_scheduler_pack.py",
    "tools/run_hyp005_shadow_collection_scheduler_pack_4B436625Z.py",
    "tests/test_hyp005_shadow_collection_scheduler_pack_4B436625Z.py",
]


def main() -> int:
    print("4B.4.3.6.6.25Z HYP-005 shadow collection scheduler pack patch applied")
    ok = True
    for rel in PY_COMPILE:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        if not exists:
            ok = False
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            print(f" - {rel}_py_compile_ok: True")
        except Exception as exc:  # pragma: no cover
            print(f" - {rel}_py_compile_ok: False ({exc})")
            ok = False
    for rel, marker in CHECKS:
        path = ROOT / rel
        present = path.exists() and marker in path.read_text(encoding="utf-8")
        label = marker.replace(" ", "_").replace("/", "_")
        print(f" - {label}_present: {present}")
        ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
