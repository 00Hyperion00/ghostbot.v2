from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp003_robustness_walkforward.py", [
        "HYP003_ROBUSTNESS_HOTFIX_VERSION",
        "4B.4.3.6.6.25K-H1",
        "_ensure_edges_dataframe",
        "_split_dataframe",
        "np.array_split",
        "iloc",
    ]),
    ("tests/test_hyp003_robustness_walkforward_hotfix_25KH1.py", [
        "test_25kh1_declares_hotfix_version",
        "test_25kh1_walk_forward_keeps_dataframe_chunks",
        "test_25kh1_original_robustness_report_no_numpy_chunk_crash",
    ]),
    ("docs/HYP003_ROBUSTNESS_WALKFORWARD_HOTFIX_25KH1.md", [
        "Walk-Forward DataFrame Split Hotfix",
        "numpy.ndarray",
        "Paper/live remain blocked",
    ]),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:  # pragma: no cover
        print(f" - {path}_py_compile_error: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25K-H1 HYP-003 robustness walk-forward DataFrame split hotfix applied")
    ok = True
    for rel, markers in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        ok = ok and exists
        if exists and path.suffix == ".py":
            compiled = _compile(path)
            print(f" - {rel}_py_compile_ok: {compiled}")
            ok = ok and compiled
        text = path.read_text(encoding="utf-8") if exists else ""
        for marker in markers:
            present = marker in text
            safe_marker = marker.replace("-", "_").replace(" ", "_").replace("/", "_")
            print(f" - {safe_marker}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
