from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.27G-H2"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp005_shadow_evidence_path_contract import (  # noqa: E402
    HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION,
    normalize_logger_report_evidence_paths,
    resolve_evidence_output_directory,
    resolve_existing_evidence_path,
    write_json_ascii_atomic,
)


def _functional_probe() -> dict[str, bool]:
    with tempfile.TemporaryDirectory(prefix="Masaüstü_ALKILIÇ_") as temp:
        root = Path(temp)
        spec = root / "aday_çalışma.json"
        ledger_json = root / "gözlem.json"
        ledger_jsonl = root / "gözlem.jsonl"
        spec.write_text("{}", encoding="utf-8")
        ledger_json.write_text("[]", encoding="utf-8")
        ledger_jsonl.write_text("", encoding="utf-8")
        mojibake = str(spec).encode("utf-8").decode("latin-1")
        repaired = resolve_existing_evidence_path(mojibake, field="candidate_spec", expect_directory=False)
        payload = normalize_logger_report_evidence_paths(
            {"ledger_json": str(ledger_json), "ledger_jsonl": str(ledger_jsonl), "source_reports": [mojibake]},
            require_exists=True,
        )
        out_dir = root / "çıktı" / "reports"
        out_dir.parent.mkdir(parents=True)
        created_out_dir = resolve_evidence_output_directory(str(out_dir), field="out_dir")
        report = root / "rapor.json"
        write_json_ascii_atomic(report, payload)
        raw = report.read_text(encoding="utf-8")
        return {
            "reversible_mojibake_repaired": repaired == spec.resolve(),
            "mandatory_paths_resolved": payload.get("evidence_paths_resolved") is True,
            "missing_output_directory_created": created_out_dir == out_dir.resolve() and out_dir.is_dir(),
            "powershell_safe_ascii_json": "\\u" in raw and "ü" not in raw and "ç" not in raw,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    legacy = (ROOT / "tools" / "run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py").read_text(encoding="utf-8")
    wrapper = (ROOT / "tools" / "run_hyp005_shadow_observation_logger_4B436625V.py").read_text(encoding="utf-8")
    epoch = (ROOT / "tools" / "run_hyp005_r1_canonical_epoch_cycle_4B436625AEH5.ps1").read_text(encoding="utf-8")
    checks: dict[str, bool] = {
        "contract_version_ok": HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION == CONTRACT_VERSION,
        "legacy_ascii_writer_present": "write_json_ascii_atomic(json_path, report)" in legacy,
        "legacy_fail_closed_normalization_present": "normalize_logger_report_evidence_paths(report, require_exists=True)" in legacy,
        "wrapper_fail_closed_normalization_present": "normalize_logger_report_evidence_paths(report_payload, require_exists=True)" in wrapper,
        "wrapper_ascii_writer_present": "write_json_ascii_atomic(report_json, report_payload)" in wrapper,
        "powershell_python_utf8_present": "$env:PYTHONUTF8 = \"1\"" in epoch and "$env:PYTHONIOENCODING = \"utf-8\"" in epoch,
        **_functional_probe(),
    }
    payload: dict[str, Any] = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=True) if args.once_json else payload)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
