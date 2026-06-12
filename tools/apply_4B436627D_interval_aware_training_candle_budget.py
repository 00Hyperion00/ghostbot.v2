from __future__ import annotations

import py_compile
import shutil
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
PAYLOAD_DIR = TOOLS_DIR / "_patch_payload"
SRC_DIR = PROJECT_ROOT / "src" / "tradebot"
BACKUP_DIR = TOOLS_DIR / "_patch_backup_4B436627D"

BUDGET_TARGET = SRC_DIR / "training" / "candle_budget.py"
BUDGET_PAYLOAD = PAYLOAD_DIR / "training_candle_budget_4B436627D.py"
TRAIN_TARGET = SRC_DIR / "training" / "train_xgb.py"
CHECKER = TOOLS_DIR / "check_interval_aware_training_candle_budget_4B436627D.py"
ROLLBACK = TOOLS_DIR / "rollback_4B436627D_interval_aware_training_candle_budget.py"
TEST_FILE = PROJECT_ROOT / "tests" / "test_interval_aware_training_candle_budget_4B436627D.py"
CREATED_MARKER = BACKUP_DIR / "created_files.txt"


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def _backup(path: Path) -> None:
    relative = path.relative_to(PROJECT_ROOT)
    destination = BACKUP_DIR / relative
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)


def _record_created(path: Path) -> None:
    CREATED_MARKER.parent.mkdir(parents=True, exist_ok=True)
    current = set(CREATED_MARKER.read_text(encoding="utf-8").splitlines()) if CREATED_MARKER.exists() else set()
    current.add(path.relative_to(PROJECT_ROOT).as_posix())
    CREATED_MARKER.write_text("\n".join(sorted(current)) + "\n", encoding="utf-8")


def _replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"27D_EXPECTED_SOURCE_FRAGMENT_MISSING:{path}:{old[:100]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _restore_on_failure(transaction_train_backup: Path, budget_existed_before: bool) -> None:
    shutil.copy2(transaction_train_backup, TRAIN_TARGET)
    if not budget_existed_before:
        BUDGET_TARGET.unlink(missing_ok=True)


def main() -> int:
    required = [BUDGET_PAYLOAD, TRAIN_TARGET, CHECKER, ROLLBACK, TEST_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("27d_apply_error: required file missing")
        for item in missing:
            print(f" - missing: {item}")
        return 2
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    _backup(TRAIN_TARGET)
    budget_existed_before = BUDGET_TARGET.exists()
    with tempfile.NamedTemporaryFile(prefix="27d_train_xgb_", suffix=".py", delete=False) as handle:
        transaction_train_backup = Path(handle.name)
    shutil.copy2(TRAIN_TARGET, transaction_train_backup)
    try:
        if not budget_existed_before:
            _record_created(BUDGET_TARGET)
        BUDGET_TARGET.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BUDGET_PAYLOAD, BUDGET_TARGET)
        _replace_once(
            TRAIN_TARGET,
            "from .labeling import ATRLabelConfig, build_cost_aware_atr_targets\n",
            "from .labeling import ATRLabelConfig, build_cost_aware_atr_targets\nfrom .candle_budget import TRAINING_CANDLE_BUDGET_VERSION, build_training_candle_budget\n",
        )
        _replace_once(
            TRAIN_TARGET,
            "    total_candles = days * 24 * 60\n",
            "    budget = build_training_candle_budget(interval, days)\n    total_candles = budget.requested_candles\n",
        )
        _replace_once(
            TRAIN_TARGET,
            "    return df[['open_time','close_time','open','high','low','close','volume','quote_volume']].astype(float)\n",
            "    frame = df[['open_time','close_time','open','high','low','close','volume','quote_volume']].astype(float)\n    return frame.tail(total_candles).reset_index(drop=True)\n",
        )
        _replace_once(
            TRAIN_TARGET,
            "        'days': days,\n        'accuracy': float(acc),\n",
            "        'days': days,\n        'training_candle_budget_contract_version': TRAINING_CANDLE_BUDGET_VERSION,\n        'training_candle_budget': build_training_candle_budget(interval, days).to_dict(),\n        'accuracy': float(acc),\n",
        )
    except Exception as error:
        _restore_on_failure(transaction_train_backup, budget_existed_before)
        transaction_train_backup.unlink(missing_ok=True)
        print(f"27d_apply_error: {error}")
        return 3
    transaction_train_backup.unlink(missing_ok=True)

    checks: list[tuple[str, bool]] = [
        ("config_mutation_performed", False),
        ("scheduler_mutation_performed", False),
        ("trading_action_performed", False),
        ("budget_module_py_compile_ok", _compile(BUDGET_TARGET)),
        ("train_xgb_py_compile_ok", _compile(TRAIN_TARGET)),
        ("checker_py_compile_ok", _compile(CHECKER)),
        ("rollback_py_compile_ok", _compile(ROLLBACK)),
        ("test_file_py_compile_ok", _compile(TEST_FILE)),
        ("budget_version_present", 'TRAINING_CANDLE_BUDGET_VERSION: Final[str] = "4B.4.3.6.6.27D"' in BUDGET_TARGET.read_text(encoding="utf-8")),
        ("interval_budget_hook_present", "build_training_candle_budget(interval, days)" in TRAIN_TARGET.read_text(encoding="utf-8")),
        ("legacy_one_minute_formula_absent", "total_candles = days * 24 * 60" not in TRAIN_TARGET.read_text(encoding="utf-8")),
        ("training_result_budget_manifest_present", "training_candle_budget_contract_version" in TRAIN_TARGET.read_text(encoding="utf-8")),
        ("paper_live_order_enablement_present", False),
    ]
    print("4B.4.3.6.6.27D Interval-aware training candle budget / historical range accuracy hardening applied")
    ok = True
    for name, value in checks:
        print(f" - {name}: {value}")
        if name in {"config_mutation_performed", "scheduler_mutation_performed", "trading_action_performed", "paper_live_order_enablement_present"}:
            ok = ok and (value is False)
        else:
            ok = ok and value
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
