from __future__ import annotations

import py_compile
from pathlib import Path

PHASE = "4B.4.3.6.6.24A"
FILES = [
    Path("src/tradebot/api.py"),
    Path("src/tradebot/config.py"),
    Path("tools/build_release_archive_4B436624A.py"),
    Path("tests/test_release_cleanup_4B436624A.py"),
    Path("docs/PRE_LIVE_HYGIENE_RUNBOOK_4B436624A.md"),
    Path("config.local.yaml"),
    Path("config.local.example.yaml"),
    Path(".gitignore"),
    Path(".releaseignore"),
]


def compile_ok(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def _file_contains(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8", errors="ignore")


def _config_local_has_plain_secret(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    forbidden_prefixes = ("api_key:", "api_secret:")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(forbidden_prefixes):
            _, _, value = line.partition(":")
            clean = value.strip().strip("'\"")
            if clean and clean not in {"[REDACTED]", "${TRADEBOT_API_KEY}", "${TRADEBOT_API_SECRET}"}:
                return True
    return False


def main() -> int:
    root = Path.cwd()
    checks: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        checks[f"{rel.as_posix()}_exists"] = path.exists()
        if path.suffix == ".py" and path.exists():
            checks[f"{rel.as_posix()}_py_compile_ok"] = compile_ok(path)

    api_text = (root / "src/tradebot/api.py").read_text(encoding="utf-8")
    cfg_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8")
    release_text = (root / "tools/build_release_archive_4B436624A.py").read_text(encoding="utf-8")

    checks["health_degraded_contract_present"] = "'degraded': degraded" in api_text and "'start_error': error" in api_text
    checks["status_stopped_fallback_present"] = "'state': 'STOPPED'" in api_text and "_build_degraded_status_payload" in api_text
    checks["settings_redacts_secrets_by_default"] = "include_secrets: bool = False" in cfg_text and "[REDACTED]" in cfg_text
    checks["config_local_secret_free"] = not _config_local_has_plain_secret(root / "config.local.yaml")
    checks["release_excludes_local_config"] = _file_contains(root / ".releaseignore", "config.local.yaml")
    checks["release_excludes_venv"] = _file_contains(root / ".releaseignore", ".venv/**")
    checks["release_builder_secret_scan_present"] = "scan_release_files_for_plain_secrets" in release_text

    print(f"{PHASE} pre-live hygiene patch applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if not all(checks.values()):
        failed = {key: value for key, value in checks.items() if not value}
        raise RuntimeError(f"{PHASE} checks failed: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
