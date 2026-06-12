from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.hyp005_shadow_observation_identity import (  # noqa: E402
    HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_VERSION,
    normalize_jsonl_file,
)

HYP005_25V_STABLE_IDENTITY_WRAPPER = True
LEGACY_RUNNER = Path(__file__).with_name(
    "run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py"
)
LEDGER_PATTERN = "4B436625V_hyp005_shadow_observation_ledger_*.jsonl"
FileSignature = tuple[int, int]


def _parse_out_dir(argv: list[str]) -> Path:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--out-dir", type=Path, required=True)
    args, _ = parser.parse_known_args(argv)
    return args.out_dir.resolve()


def _ledger_signatures(out_dir: Path) -> dict[Path, FileSignature]:
    if not out_dir.exists():
        return {}
    signatures: dict[Path, FileSignature] = {}
    for path in out_dir.glob(LEDGER_PATTERN):
        if not path.is_file():
            continue
        stat = path.stat()
        signatures[path.resolve()] = (stat.st_mtime_ns, stat.st_size)
    return signatures


def _run_legacy_runner() -> int:
    if not LEGACY_RUNNER.exists():
        print(f"legacy_runner_missing: {LEGACY_RUNNER}", file=sys.stderr)
        return 2
    try:
        runpy.run_path(str(LEGACY_RUNNER), run_name="__main__")
    except SystemExit as error:
        if error.code is None:
            return 0
        if isinstance(error.code, int):
            return error.code
        print(str(error.code), file=sys.stderr)
        return 1
    return 0


def _normalize_changed_ledgers(out_dir: Path, *, before: dict[Path, FileSignature]) -> tuple[int, int]:
    matched = 0
    changed = 0
    after = _ledger_signatures(out_dir)
    for path, signature in sorted(after.items(), key=lambda item: str(item[0])):
        if before.get(path) == signature:
            continue
        matched += 1
        changed += normalize_jsonl_file(path)
    return matched, changed


def main() -> int:
    out_dir = _parse_out_dir(sys.argv[1:])
    before = _ledger_signatures(out_dir)
    exit_code = _run_legacy_runner()
    if exit_code != 0:
        return exit_code
    matched, changed = _normalize_changed_ledgers(out_dir, before=before)
    print(f" - stable_identity_version: {HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_VERSION}")
    print(f" - normalized_new_or_changed_ledgers: {matched}")
    print(f" - normalized_rows: {changed}")
    print(" - rolling_ordinal_identity_used: False")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    if matched == 0:
        print(" - stable_identity_warning: HYP005_25V_NEW_OR_CHANGED_LEDGER_NOT_FOUND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
