from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src" / "tradebot"
TOOLS = PROJECT_ROOT / "tools"
PAYLOAD = TOOLS / "_patch_payload"
BACKUP = TOOLS / "_patch_backup_4B436627F"
CREATED_MARKER = BACKUP / ".created_files.txt"

SIZING_TARGET = SRC / "position_sizing.py"
SIZING_PAYLOAD = PAYLOAD / "position_sizing_4B436627F.py"
CONFIG = SRC / "config.py"
CONFIG_SAFETY = SRC / "config_safety.py"
ENGINE = SRC / "engine.py"
CHECKER = TOOLS / "check_risk_percent_position_sizing_4B436627F.py"
ROLLBACK = TOOLS / "rollback_4B436627F_risk_percent_position_sizing.py"
TEST_FILE = PROJECT_ROOT / "tests" / "test_risk_percent_position_sizing_4B436627F.py"
ACTIVE_FILES = [CONFIG, CONFIG_SAFETY, ENGINE]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _backup(path: Path) -> None:
    relative = path.relative_to(PROJECT_ROOT)
    target = BACKUP / relative
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _created(path: Path) -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    current = set(CREATED_MARKER.read_text(encoding="utf-8").splitlines()) if CREATED_MARKER.exists() else set()
    current.add(relative)
    CREATED_MARKER.write_text("\n".join(sorted(item for item in current if item)) + "\n", encoding="utf-8")


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"27F_EXPECTED_SOURCE_FRAGMENT_MISSING:{path}:{old[:120]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _restore_on_failure() -> None:
    if BACKUP.exists():
        for source in sorted(
            path for path in BACKUP.rglob("*")
            if path.is_file() and path != CREATED_MARKER and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
        ):
            relative = source.relative_to(BACKUP)
            target = PROJECT_ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    if CREATED_MARKER.exists():
        for raw in CREATED_MARKER.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw:
                target = PROJECT_ROOT / raw
                if target.exists():
                    target.unlink()


def _patch() -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    for path in ACTIVE_FILES:
        if not path.exists():
            raise RuntimeError(f"27F_REQUIRED_ACTIVE_FILE_MISSING:{path}")
        _backup(path)
    if not SIZING_TARGET.exists():
        SIZING_TARGET.parent.mkdir(parents=True, exist_ok=True)
        _created(SIZING_TARGET)
    shutil.copy2(SIZING_PAYLOAD, SIZING_TARGET)

    _replace(
        CONFIG,
        '    sizing_mode: str = "fixed_quote"\n    risk_percent_quote_balance: float = 2.5\n',
        '    sizing_mode: str = "fixed_quote"\n    risk_percent_quote_balance: float = 2.5\n    quote_balance_reserve_usd: float = 0.0\n    max_quote_budget_usd: float = 0.0\n',
    )

    _replace(
        CONFIG_SAFETY,
        'from .enums import AutoSignalMode, ExecutionMode, MarketType\n',
        'from .enums import AutoSignalMode, ExecutionMode, MarketType\nfrom .position_sizing import PositionSizingError, validate_sizing_settings\n',
    )
    _replace(
        CONFIG_SAFETY,
        '    risk_percent_quote_balance: float\n    min_notional_buffer_multiplier: float\n',
        '    risk_percent_quote_balance: float\n    quote_balance_reserve_usd: float\n    max_quote_budget_usd: float\n    min_notional_buffer_multiplier: float\n',
    )
    _replace(
        CONFIG_SAFETY,
        "        risk_percent_quote_balance=float(getattr(settings, 'risk_percent_quote_balance', 0.0) or 0.0),\n        min_notional_buffer_multiplier=float(getattr(settings, 'min_notional_buffer_multiplier', 0.0) or 0.0),\n",
        "        risk_percent_quote_balance=float(getattr(settings, 'risk_percent_quote_balance', 0.0) or 0.0),\n        quote_balance_reserve_usd=float(getattr(settings, 'quote_balance_reserve_usd', 0.0) or 0.0),\n        max_quote_budget_usd=float(getattr(settings, 'max_quote_budget_usd', 0.0) or 0.0),\n        min_notional_buffer_multiplier=float(getattr(settings, 'min_notional_buffer_multiplier', 0.0) or 0.0),\n",
    )
    _replace(
        CONFIG_SAFETY,
        "    if cfg.order_notional_usd <= 0:\n        criticals.append('order_notional_usd pozitif değil')\n        reason_codes.append('ORDER_NOTIONAL_INVALID')\n    if cfg.sizing_mode == 'risk_percent' and not (0 < cfg.risk_percent_quote_balance <= 100):\n        criticals.append('risk_percent_quote_balance 0-100 aralığında değil')\n        reason_codes.append('RISK_PERCENT_INVALID')\n",
        "    try:\n        sizing_snapshot = validate_sizing_settings(cfg).to_dict()\n    except PositionSizingError as error:\n        sizing_snapshot = {'contract_version': '4B.4.3.6.6.27F', 'ok': False, 'reason_code': error.reason_code}\n        criticals.append('Entry sizing konfigürasyonu geçersiz')\n        reason_codes.append(error.reason_code)\n",
    )
    _replace(
        CONFIG_SAFETY,
        "        'risk_percent_quote_balance': cfg.risk_percent_quote_balance,\n        'risk_controls': {\n",
        "        'risk_percent_quote_balance': cfg.risk_percent_quote_balance,\n        'quote_balance_reserve_usd': cfg.quote_balance_reserve_usd,\n        'max_quote_budget_usd': cfg.max_quote_budget_usd,\n        'position_sizing': sizing_snapshot,\n        'risk_controls': {\n",
    )

    _replace(
        ENGINE,
        'from .risk import build_risk_plan\n',
        'from .risk import build_risk_plan\nfrom .position_sizing import PositionSizingError, build_entry_sizing_decision\n',
    )
    _replace(
        ENGINE,
        "            target_notional = min(self.settings.order_notional_usd, quote.free)\n            qty = round_down_to_step(target_notional / price, self.symbol_rules.step_size) if price > 0 else 0.0\n            if qty < self.symbol_rules.min_qty or qty * price < self.symbol_rules.min_notional * self.settings.min_notional_buffer_multiplier:\n                self.logger.warn('ENTRY_BLOCKED', 'Giriş emri minNotional/minQty nedeniyle engellendi', {'skipCode': 'MIN_NOTIONAL_BLOCKED', 'qty': qty, 'price': price, 'freeQuote': quote.free})\n                return\n",
        "            try:\n                sizing = build_entry_sizing_decision(\n                    settings=self.settings,\n                    symbol_rules=self.symbol_rules,\n                    free_quote_balance=quote.free,\n                    reference_price=price,\n                )\n            except PositionSizingError as error:\n                self.logger.warn('ENTRY_BLOCKED', 'Giriş miktarı fail-closed sizing kontratı tarafından engellendi', {\n                    'skipCode': error.reason_code,\n                    'price': price,\n                    'freeQuote': quote.free,\n                    'sizingMode': self.settings.sizing_mode,\n                    'sizingContractVersion': '4B.4.3.6.6.27F',\n                })\n                return\n            target_notional = sizing.quote_budget\n            qty = sizing.quantity\n            self.logger.info('ENTRY_SIZING_VERIFIED', 'Giriş miktarı fail-closed sizing kontratı ile doğrulandı', sizing.to_dict())\n",
    )
    _replace(
        ENGINE,
        "'sizingMode': self.settings.sizing_mode,'source': source,'targetNotional': self.settings.order_notional_usd})\n",
        "'sizingMode': sizing.sizing_mode,'sizingContractVersion': sizing.contract_version,'source': source,'targetNotional': target_notional,'sizingSnapshot': sizing.to_dict()})\n",
    )


def main() -> int:
    required = [SIZING_PAYLOAD, CHECKER, ROLLBACK, TEST_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("27f_apply_error: required overlay file missing")
        for item in missing:
            print(f" - missing: {item}")
        return 2
    try:
        _patch()
    except Exception as error:
        _restore_on_failure()
        print(f"27f_apply_error: {error}")
        return 3

    checks = [
        ("config_mutation_performed", False),
        ("scheduler_mutation_performed", False),
        ("training_performed", False),
        ("reload_performed", False),
        ("trading_action_performed", False),
        ("sizing_module_py_compile_ok", _compile(SIZING_TARGET)),
        ("config_py_compile_ok", _compile(CONFIG)),
        ("config_safety_py_compile_ok", _compile(CONFIG_SAFETY)),
        ("engine_py_compile_ok", _compile(ENGINE)),
        ("checker_py_compile_ok", _compile(CHECKER)),
        ("rollback_py_compile_ok", _compile(ROLLBACK)),
        ("test_file_py_compile_ok", _compile(TEST_FILE)),
        ("sizing_contract_version_present", 'POSITION_SIZING_CONTRACT_VERSION = "4B.4.3.6.6.27F"' in SIZING_TARGET.read_text(encoding="utf-8")),
        ("risk_percent_mode_present", '"risk_percent_quote_balance"' in SIZING_TARGET.read_text(encoding="utf-8")),
        ("quote_balance_boundaries_present", 'SIZING_QUOTE_BUDGET_EXCEEDS_AVAILABLE_BALANCE' in SIZING_TARGET.read_text(encoding="utf-8")),
        ("symbol_filter_gate_present", 'SIZING_SYMBOL_FILTERS_MISSING' in SIZING_TARGET.read_text(encoding="utf-8")),
        ("engine_entry_sizing_hook_present", 'build_entry_sizing_decision(' in ENGINE.read_text(encoding="utf-8")),
        ("engine_exit_quantity_path_untouched", 'requested_qty = float(requested_qty_override)' in ENGINE.read_text(encoding="utf-8")),
        ("config_safety_sizing_gate_present", 'validate_sizing_settings(cfg)' in CONFIG_SAFETY.read_text(encoding="utf-8")),
        ("paper_live_order_enablement_present", False),
    ]
    print("4B.4.3.6.6.27F Risk-percent position sizing / quote-balance boundaries / fail-closed quantity contract hardening applied")
    ok = True
    false_expected = {"config_mutation_performed", "scheduler_mutation_performed", "training_performed", "reload_performed", "trading_action_performed", "paper_live_order_enablement_present"}
    for name, value in checks:
        print(f" - {name}: {value}")
        ok = ok and ((value is False) if name in false_expected else bool(value))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
