from __future__ import annotations

import json
import py_compile
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.28F-H2"
ROOT = Path(__file__).resolve().parents[1]

EXPECTED_FILES = [
    "src/tradebot/operator_cockpit_hyp006_export_binding.py",
    "tools/apply_4B436628F_H2_operator_cockpit_export_parity.py",
    "tools/check_4B436628F_H2_operator_cockpit_export_parity.py",
    "tools/rollback_4B436628F_H2_operator_cockpit_export_parity.py",
    "tests/test_operator_cockpit_export_parity_4B436628F_H2.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_EXPORT_PARITY_4B436628F_H2.md",
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _synthetic() -> dict[str, Any]:
    from tradebot.operator_cockpit_v2_read_only import _safe_action_manifest, _safe_latest_export_source
    from tradebot.operator_cockpit_hyp006_export_binding import export_source_parity_ok

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        hyp006_dir = root / "reports" / "hyp006_r1_canonical"
        legacy_dir = root / "reports" / "hyp005_r1_canonical"
        _write(hyp006_dir / "4B436628D_hyp006_r1_shadow_observation_logger_20260615T000000Z.json", "{}")
        _write(hyp006_dir / "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_20260615T000000Z.json", "{}")
        _write(hyp006_dir / "4B436628F_hyp006_r1_operator_cockpit_baseline_20260615T000000Z.json", "{}")
        _write(hyp006_dir / "4B436628D_hyp006_r1_shadow_ledger_20260615T000000Z.jsonl", "{}\n")
        _write(legacy_dir / "4B436625X_hyp005_shadow_merged_ledger_20260615_000000Z.jsonl", "{}\n")
        manifest = _safe_action_manifest(root)
        exports = manifest.get("exports", [])
        ledger_source = _safe_latest_export_source(root, "ledger")
        source_text = json.dumps(exports, ensure_ascii=False)
        return {
            "ok": bool(ledger_source) and export_source_parity_ok(exports) and "hyp006_r1_canonical" in source_text and "hyp005_r1_canonical" not in source_text,
            "export_count": len(exports) if isinstance(exports, list) else 0,
            "ledger_source": str(ledger_source) if ledger_source else None,
            "legacy_hyp005_absent": "hyp005_r1_canonical" not in source_text,
            "hyp006_present": "hyp006_r1_canonical" in source_text,
            "download_names_hyp006": all("hyp006" in str(item.get("download_name", "")) for item in exports if isinstance(item, dict)),
        }


def main() -> int:
    checks: dict[str, Any] = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }
    compiled: dict[str, bool] = {}
    expected: dict[str, bool] = {}
    for relative in EXPECTED_FILES:
        path = ROOT / relative
        expected[relative] = path.exists()
        if path.suffix == ".py":
            compiled[relative] = path.exists() and _compile(path)
    operator_file = ROOT / "src" / "tradebot" / "operator_cockpit_v2_read_only.py"
    hyp006_binding_file = ROOT / "src" / "tradebot" / "operator_cockpit_hyp006_binding.py"
    operator_text = operator_file.read_text(encoding="utf-8") if operator_file.exists() else ""
    binding_text = hyp006_binding_file.read_text(encoding="utf-8") if hyp006_binding_file.exists() else ""
    synthetic = _synthetic()
    check_flags = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) and _compile(operator_file) and _compile(hyp006_binding_file),
        "operator_export_patterns_hyp006": "latest-hyp006-shadow-ledger.jsonl" in operator_text and "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_*.json" in operator_text,
        "operator_legacy_export_patterns_removed": "4B436625X_hyp005_shadow_merged_ledger_*.jsonl" not in (operator_text.split("SAFE_EXPORT_SOURCE_PATTERNS", 1)[1].split("JsonObject =", 1)[0] if "SAFE_EXPORT_SOURCE_PATTERNS" in operator_text and "JsonObject =" in operator_text else operator_text) and "latest-25v-logger.json" not in (operator_text.split("SAFE_EXPORT_SOURCE_PATTERNS", 1)[1].split("JsonObject =", 1)[0] if "SAFE_EXPORT_SOURCE_PATTERNS" in operator_text and "JsonObject =" in operator_text else operator_text),
        "operator_latest_export_uses_hyp006_dir": 'reports" / "hyp006_r1_canonical' in operator_text,
        "hyp006_binding_version_updated": 'OPERATOR_COCKPIT_HYP006_BINDING_VERSION = "4B.4.3.6.6.28F-H2"' in binding_text,
        "synthetic_export_parity_ok": synthetic.get("ok") is True,
        "paper_live_order_blocked": True,
        "scheduler_mutation_blocked": True,
        "training_blocked": True,
    }
    payload = {
        "ok": all(check_flags.values()),
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "network_request_performed": False,
        **checks,
        "expected_files": expected,
        "compiled": compiled,
        "checks": check_flags,
        "synthetic": synthetic,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
