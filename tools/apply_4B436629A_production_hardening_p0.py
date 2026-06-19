from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "4B.4.3.6.6.29A"
BACKUP_DIR = ROOT / "tools" / f"_patch_backup_4B436629A_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _backup(path: Path) -> None:
    if path.exists():
        target = BACKUP_DIR / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _ensure_contains(path: Path, marker: str, block: str) -> bool:
    text = _read(path)
    if marker in text:
        return False
    _backup(path)
    text = text.rstrip() + "\n" + block.strip() + "\n"
    _write(path, text)
    return True


def patch_config() -> bool:
    path = ROOT / "src" / "tradebot" / "config.py"
    text = _read(path)
    changed = False
    if "strict_config_validation: bool = True" not in text:
        _backup(path)
        marker = '    api_port: int = 8787\n'
        block = '''\n    # 4B.4.3.6.6.29A production hardening controls\n    strict_config_validation: bool = True\n    api_auth_enabled: bool = False\n    api_auth_token: str = ""\n    api_auth_header: str = "X-TradeBot-Auth"\n    api_auth_env_var: str = "TRADEBOT_API_TOKEN"\n    destructive_action_confirmation_required: bool = False\n    destructive_action_confirmation_header: str = "X-TradeBot-Confirm"\n    runtime_lock_enabled: bool = True\n    runtime_lock_path: str = ".tradebot/runtime.lock"\n    sqlite_wal_enabled: bool = True\n    sqlite_busy_timeout_ms: int = 5000\n    sqlite_schema_version: int = 1\n    sqlite_backup_enabled: bool = True\n    fee_slippage_baseline_bps: float = 24.0\n    promotion_gate_isolation_enabled: bool = True\n'''
        if marker not in text:
            raise RuntimeError("config.py api_port marker not found")
        text = text.replace(marker, marker + block, 1)
        changed = True
    old_from_yaml = '''    @classmethod\n    def from_yaml(cls, path: str | Path) -> "Settings":\n        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}\n        if not isinstance(payload, dict):\n            raise TypeError("Settings yaml must decode to a mapping")\n        allowed = {field.name for field in fields(cls)}\n        filtered = {key: value for key, value in payload.items() if key in allowed}\n        return cls(**filtered)\n'''
    new_from_yaml = '''    @classmethod\n    def from_yaml(cls, path: str | Path) -> "Settings":\n        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}\n        if not isinstance(payload, dict):\n            raise TypeError("Settings yaml must decode to a mapping")\n        allowed = {field.name for field in fields(cls)}\n        unknown_keys = sorted(str(key) for key in payload if key not in allowed)\n        strict_value = payload.get("strict_config_validation", True)\n        strict_config_validation = bool(strict_value)\n        if unknown_keys and strict_config_validation:\n            joined = ", ".join(unknown_keys)\n            raise ValueError(f"Unknown Settings yaml key(s): {joined}")\n        filtered = {key: value for key, value in payload.items() if key in allowed}\n        return cls(**filtered)\n'''
    if "Unknown Settings yaml key(s)" not in text:
        if old_from_yaml not in text:
            raise RuntimeError("config.py from_yaml block not found")
        if not changed:
            _backup(path)
        text = text.replace(old_from_yaml, new_from_yaml, 1)
        changed = True
    if "payload['api_auth_token'] = '[REDACTED]'" not in text:
        needle = "        if not include_secrets:\n            payload['api_key'] = '[REDACTED]' if self.api_key else ''\n"
        replacement = "        if not include_secrets:\n            payload['api_auth_token'] = '[REDACTED]' if payload.get('api_auth_token') else ''\n            payload['api_key'] = '[REDACTED]' if self.api_key else ''\n"
        if needle not in text:
            raise RuntimeError("config.py to_dict redaction marker not found")
        if not changed:
            _backup(path)
        text = text.replace(needle, replacement, 1)
        changed = True
    if changed:
        _write(path, text)
    return changed


def patch_persistence() -> bool:
    path = ROOT / "src" / "tradebot" / "persistence.py"
    text = _read(path)
    changed = False
    if "import shutil" not in text:
        _backup(path)
        text = text.replace("import json\n", "import json\nimport shutil\n", 1)
        changed = True
    if "def _configure_connection" not in text:
        if not changed:
            _backup(path)
        text = text.replace("        self._conn.row_factory = sqlite3.Row\n        self._bootstrap()\n", "        self._conn.row_factory = sqlite3.Row\n        self._configure_connection()\n        self._bootstrap()\n", 1)
        marker = "    def _bootstrap(self) -> None:\n"
        block = '''    def _configure_connection(self) -> None:\n        # 4B.4.3.6.6.29A SQLite audit baseline: avoid silent lock errors and enable WAL.\n        self._conn.execute("PRAGMA busy_timeout = 5000")\n        self._conn.execute("PRAGMA journal_mode = WAL")\n        self._conn.execute("PRAGMA foreign_keys = ON")\n\n'''
        if marker not in text:
            raise RuntimeError("persistence.py _bootstrap marker not found")
        text = text.replace(marker, block + marker, 1)
        changed = True
    if "schema_meta" not in text:
        if not changed:
            _backup(path)
        marker = "\n    def set_json"
        block = '''            self._conn.execute(\n                "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"\n            )\n            self._conn.execute(\n                """\n                CREATE TABLE IF NOT EXISTS operator_actions (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    ts INTEGER NOT NULL,\n                    action TEXT NOT NULL,\n                    actor TEXT NOT NULL,\n                    confirmation TEXT NOT NULL,\n                    outcome TEXT NOT NULL,\n                    data TEXT NOT NULL\n                )\n                """\n            )\n            self._conn.execute("PRAGMA user_version = 1")\n            self._conn.execute(\n                "INSERT INTO schema_meta(key, value) VALUES('schema_version', '1') "\n                "ON CONFLICT(key) DO UPDATE SET value=excluded.value"\n            )\n\n    def set_json'''
        if marker not in text:
            raise RuntimeError("persistence.py set_json marker not found")
        text = text.replace(marker, "\n" + block, 1)
        changed = True
    if "def integrity_check" not in text:
        if not changed:
            _backup(path)
        marker = "\n    def fetch_audit_events("
        block = '''\n\n    def integrity_check(self) -> dict[str, Any]:\n        with self._lock:\n            rows = self._conn.execute("PRAGMA integrity_check").fetchall()\n            journal = self._conn.execute("PRAGMA journal_mode").fetchone()\n            user_version = self._conn.execute("PRAGMA user_version").fetchone()\n        results = [str(row[0]) for row in rows]\n        return {\n            "ok": results == ["ok"],\n            "contract_version": "4B.4.3.6.6.29A",\n            "integrity_check": results,\n            "journal_mode": str(journal[0]) if journal else None,\n            "schema_version": int(user_version[0]) if user_version else 0,\n        }\n\n    def backup_to(self, destination: str | Path) -> Path:\n        target = Path(destination)\n        target.parent.mkdir(parents=True, exist_ok=True)\n        with self._lock:\n            self._conn.commit()\n            shutil.copy2(self.path, target)\n        return target\n'''
        if marker not in text:
            raise RuntimeError("persistence.py fetch_audit_events marker not found")
        text = text.replace(marker, block + marker, 1)
        changed = True
    if changed:
        _write(path, text)
    return changed


def patch_api() -> bool:
    path = ROOT / "src" / "tradebot" / "api.py"
    text = _read(path)
    changed = False
    if "from .api_security import install_api_security" not in text:
        _backup(path)
        marker = "from .ai.decision_contract import AIDecisionContractError, assert_startup_reload_parity, decision_contract_from_payload, decision_contract_from_settings\n"
        if marker not in text:
            raise RuntimeError("api.py decision_contract import marker not found")
        text = text.replace(marker, marker + "from .api_security import install_api_security\n", 1)
        changed = True
    if "install_api_security(app, engine.settings" not in text:
        if not changed:
            _backup(path)
        marker = '    app = FastAPI(title="Trade Bot Python API", version="0.2.6")\n'
        if marker not in text:
            raise RuntimeError("api.py FastAPI marker not found")
        text = text.replace(marker, marker + '    install_api_security(app, engine.settings, logger=getattr(engine, "logger", None))\n', 1)
        changed = True
    if changed:
        _write(path, text)
    return changed


def patch_labeling() -> bool:
    path = ROOT / "src" / "tradebot" / "training" / "labeling.py"
    text = _read(path)
    changed = False
    replacements = {
        "entry_fee_bps: float = 0.0": "entry_fee_bps: float = 10.0",
        "exit_fee_bps: float = 0.0": "exit_fee_bps: float = 10.0",
        "entry_slippage_bps: float = 0.0": "entry_slippage_bps: float = 2.0",
        "exit_slippage_bps: float = 0.0": "exit_slippage_bps: float = 2.0",
        "min_profit_bps: float = 0.0": "min_profit_bps: float = 24.0",
    }
    for old, new in replacements.items():
        if old in text:
            if not changed:
                _backup(path)
            text = text.replace(old, new, 1)
            changed = True
    if changed:
        _write(path, text)
    return changed


def patch_gitignore() -> bool:
    path = ROOT / ".gitignore"
    block = '''\n# BEGIN 4B.4.3.6.6.29A PRODUCTION HARDENING P0\ntools/_patch_backup_*/\ntools/_patch_payload_*/\nruntime_reports/\nreports/**/scratch/\nreports/**/tmp/\n# END 4B.4.3.6.6.29A PRODUCTION HARDENING P0\n'''
    return _ensure_contains(path, "BEGIN 4B.4.3.6.6.29A PRODUCTION HARDENING P0", block)


def main() -> int:
    patches = {
        "config_strict_api_runtime_fields": patch_config(),
        "sqlite_audit_baseline": patch_persistence(),
        "api_security_integration": patch_api(),
        "fee_slippage_training_baseline": patch_labeling(),
        "repo_hygiene_gitignore_policy": patch_gitignore(),
    }
    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    from check_4B436629A_production_hardening_p0 import build_report  # noqa: E402
    report = build_report(ROOT)
    print(f"{CONTRACT_VERSION} Production Hardening P0 patch applied")
    for key, value in patches.items():
        print(f" - patched_{key}: {value}")
    for key, value in report["checks"].items():
        print(f" - {key}: {value}")
    for key in ("config_mutation_performed", "scheduler_mutation_performed", "strategy_parameter_mutation_performed", "runtime_overlay_activation_performed", "training_performed", "reload_performed", "trading_action_performed", "paper_live_order_enablement_present"):
        print(f" - {key}: {report.get(key)}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
