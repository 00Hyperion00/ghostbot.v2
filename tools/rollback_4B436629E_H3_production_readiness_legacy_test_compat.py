from __future__ import annotations

from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.29E-H3"


def main() -> int:
    root = Path.cwd()
    backup_dirs = sorted((root / "tools").glob(f"_patch_backup_{CONTRACT_VERSION}_*"))
    if not backup_dirs:
        print(f"No {CONTRACT_VERSION} backup directory found")
        return 1
    backup = backup_dirs[-1]
    src = backup / "test_production_readiness_evidence_refresh_4B436629E_H1.py"
    dst = root / "tests" / "test_production_readiness_evidence_refresh_4B436629E_H1.py"
    if src.exists():
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    for rel in (
        "tools/apply_4B436629E_H3_production_readiness_legacy_test_compat.py",
        "tools/check_4B436629E_H3_production_readiness_legacy_test_compat.py",
        "tools/run_4B436629E_H3_production_readiness_legacy_test_compat.py",
        "tools/rollback_4B436629E_H3_production_readiness_legacy_test_compat.py",
        "tests/test_production_readiness_legacy_test_compat_4B436629E_H3.py",
        "docs/PRODUCTION_READINESS_LEGACY_TEST_COMPAT_4B436629E_H3.md",
        "README_APPLY_4B436629E_H3.txt",
    ):
        path = root / rel
        if path.exists():
            path.unlink()
    print(f"{CONTRACT_VERSION} rollback restored legacy H1 test and removed H3 files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
