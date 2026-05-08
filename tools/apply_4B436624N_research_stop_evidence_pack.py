from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/research_stop_evidence_pack.py",
    "tools/run_research_stop_evidence_pack_4B436624N.py",
    "tests/test_research_stop_evidence_pack_4B436624N.py",
]
MARKERS = {
    "src/tradebot/research_stop_evidence_pack.py": [
        "RESEARCH_STOP_CONTRACT_VERSION",
        "build_research_stop_evidence_pack",
        "NEXT_HYPOTHESIS_BACKLOG",
        "NO_EDGE_EVIDENCE_CONFIRMED",
        "approved_for_live_real",
        "post_requests_allowed",
    ],
    "tools/run_research_stop_evidence_pack_4B436624N.py": [
        "--reports-dir",
        "--input-json",
        "--include-all",
        "--review-ok",
        "research stop evidence pack",
    ],
    "tests/test_research_stop_evidence_pack_4B436624N.py": [
        "test_research_stop_pack_confirms_no_go_from_terminal_blocks",
        "test_tool_writes_report_from_explicit_input_json",
    ],
}


def main() -> int:
    print("4B.4.3.6.6.24N research stop / no-edge evidence pack patch applied")
    ok = True
    for rel in CHECKS:
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
        text = path.read_text(encoding="utf-8")
        for marker in MARKERS.get(rel, []):
            present = marker in text
            print(f" - {marker}_present: {present}")
            ok = ok and present

    doc = ROOT / "docs/RESEARCH_STOP_EVIDENCE_PACK_RUNBOOK_4B436624N.md"
    print(f" - docs/RESEARCH_STOP_EVIDENCE_PACK_RUNBOOK_4B436624N.md_exists: {doc.exists()}")
    return 0 if ok and doc.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
