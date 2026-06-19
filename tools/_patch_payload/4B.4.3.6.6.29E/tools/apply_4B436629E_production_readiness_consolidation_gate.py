from __future__ import annotations

import importlib.util
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.29E"

PAYLOAD_FILES: dict[str, str] = {
    "src/tradebot/production_readiness_gate.py": "src/tradebot/production_readiness_gate.py",
    "tests/test_production_readiness_consolidation_gate_4B436629E.py": "tests/test_production_readiness_consolidation_gate_4B436629E.py",
    "tools/check_4B436629E_production_readiness_consolidation_gate.py": "tools/check_4B436629E_production_readiness_consolidation_gate.py",
    "tools/run_4B436629E_production_readiness_consolidation_gate.py": "tools/run_4B436629E_production_readiness_consolidation_gate.py",
    "tools/rollback_4B436629E_production_readiness_consolidation_gate.py": "tools/rollback_4B436629E_production_readiness_consolidation_gate.py",
    "docs/PRODUCTION_READINESS_CONSOLIDATION_GATE_4B436629E.md": "docs/PRODUCTION_READINESS_CONSOLIDATION_GATE_4B436629E.md",
    "README_APPLY_4B436629E.txt": "README_APPLY_4B436629E.txt",
}
CONFIG_BLOCK = '''
    # 4B.4.3.6.6.29E production readiness consolidation gate controls
    production_readiness_consolidation_enabled: bool = True
    production_readiness_evidence_dir: str = "reports/production_hardening"
    production_readiness_require_29a: bool = True
    production_readiness_require_29b: bool = True
    production_readiness_require_29c: bool = True
    production_readiness_require_29d: bool = True
    paper_candidate_preflight_enabled: bool = True
    live_real_hard_block_required: bool = True
'''


def _copy_payload(root: Path) -> None:
    payload_root = root / "tools" / "_patch_payload" / CONTRACT_VERSION
    for src_rel, dst_rel in PAYLOAD_FILES.items():
        src = payload_root / src_rel
        dst = root / dst_rel
        if not src.exists():
            raise FileNotFoundError(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _patch_config(root: Path) -> bool:
    path = root / "src/tradebot/config.py"
    text = path.read_text(encoding="utf-8")
    if "production_readiness_consolidation_enabled" in text:
        return True
    marker = '    live_real_start_confirmation: str = "CONFIRM_LIVE_REAL_START"\n'
    if marker not in text:
        marker = "    # 4B.4.3.6.6.29C SQLite audit ledger upgrade\n"
        if marker not in text:
            raise RuntimeError("config.py marker not found for 29E fields")
        text = text.replace(marker, CONFIG_BLOCK + "\n" + marker, 1)
    else:
        text = text.replace(marker, marker + CONFIG_BLOCK, 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def _load_checker(root: Path):
    path = root / "tools/check_4B436629E_production_readiness_consolidation_gate.py"
    spec = importlib.util.spec_from_file_location("check_29e", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load 29E checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    root = Path.cwd()
    backup = root / "tools" / f"_patch_backup_4B436629E_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    backup.mkdir(parents=True, exist_ok=True)
    for rel in ["src/tradebot/config.py", *PAYLOAD_FILES.values()]:
        src = root / rel
        if src.exists():
            dst = backup / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    _copy_payload(root)
    patched_config = _patch_config(root)
    checker = _load_checker(root)
    report = checker.build_report(root)
    print(f"{CONTRACT_VERSION} Production Readiness Consolidation Gate patch applied")
    for key, value in report["checks"].items():
        print(f" - {key}: {value}")
    print(f" - patched_config_production_readiness_fields: {patched_config}")
    for key in (
        "runtime_overlay_activation_performed",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
        "paper_live_order_enablement_present",
    ):
        print(f" - {key}: {report[key]}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
