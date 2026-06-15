from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/tradebot/hyp006_shadow_registration_operator_approval.py",
    "tools/run_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/run_4B436628D_hyp006_canonical_shadow_cycle.py",
    "tools/check_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/apply_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/rollback_4B436628D_hyp006_shadow_registration_approval.py",
    "tests/test_hyp006_shadow_registration_approval_4B436628D.py",
    "docs/HYP006_R1_CANONICAL_SHADOW_REGISTRATION_4B436628D.md",
    "README_APPLY_4B436628D.txt",
]


def main() -> int:
    removed = []
    for rel in FILES:
        path = ROOT / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
    print("4B.4.3.6.6.28D rollback completed")
    for item in removed:
        print(f" - removed: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
