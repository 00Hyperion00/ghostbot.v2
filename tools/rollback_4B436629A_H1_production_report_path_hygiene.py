from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "4B.4.3.6.6.29A-H1"


def main() -> int:
    print(f"{CONTRACT_VERSION} rollback is intentionally manual-only")
    print("Reason: H1 removes a wrongly committed report path and adds a fail-closed reports-dir guard.")
    print("Use git revert <H1_COMMIT> if a full rollback is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
