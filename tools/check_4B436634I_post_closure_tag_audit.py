from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ensure_src_path() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    _ensure_src_path()
    from tradebot.post_closure_tag_audit import evaluate_post_closure_tag_audit

    parser = argparse.ArgumentParser(description="4B436634I post-closure tag audit check")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = evaluate_post_closure_tag_audit(repo_root=args.repo_root, reports_dir=args.reports_dir)
    indent = 2 if args.pretty and not args.once_json else None
    print(json.dumps(result, indent=indent, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
