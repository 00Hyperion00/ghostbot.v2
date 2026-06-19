from __future__ import annotations

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
