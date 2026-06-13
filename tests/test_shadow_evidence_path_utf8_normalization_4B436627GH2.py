from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.hyp005_shadow_evidence_path_contract import (
    HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION,
    normalize_logger_report_evidence_paths,
    resolve_evidence_output_directory,
    resolve_existing_evidence_path,
    write_json_ascii_atomic,
)


def _mojibake(value: str) -> str:
    return value.encode("utf-8").decode("latin-1")


def test_contract_version() -> None:
    assert HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION == "4B.4.3.6.6.27G-H2"


def test_unicode_path_is_preserved_when_exact_path_exists(tmp_path: Path) -> None:
    path = tmp_path / "Masaüstü" / "ALKILIÇ" / "kanıt.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    assert resolve_existing_evidence_path(str(path), field="evidence", expect_directory=False) == path.resolve()


def test_reversible_mojibake_is_repaired_only_when_resolvable(tmp_path: Path) -> None:
    path = tmp_path / "Masaüstü" / "kanıt.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    assert resolve_existing_evidence_path(_mojibake(str(path)), field="evidence", expect_directory=False) == path.resolve()


def test_unresolved_mandatory_path_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="HYP005_EVIDENCE_PATH_UNRESOLVED"):
        resolve_existing_evidence_path(str(tmp_path / "yok.json"), field="ledger_json", expect_directory=False)


def test_logger_report_paths_are_normalized_and_ascii_escaped(tmp_path: Path) -> None:
    spec = tmp_path / "Masaüstü" / "aday.json"
    ledger_json = tmp_path / "Masaüstü" / "ledger.json"
    ledger_jsonl = tmp_path / "Masaüstü" / "ledger.jsonl"
    spec.parent.mkdir(parents=True)
    spec.write_text("{}", encoding="utf-8")
    ledger_json.write_text("[]", encoding="utf-8")
    ledger_jsonl.write_text("", encoding="utf-8")
    payload = normalize_logger_report_evidence_paths(
        {"ledger_json": str(ledger_json), "ledger_jsonl": str(ledger_jsonl), "source_reports": [_mojibake(str(spec))]},
        require_exists=True,
    )
    report = tmp_path / "rapor.json"
    write_json_ascii_atomic(report, payload)
    raw = report.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert "\\u00fc" in raw
    assert "Masaüstü" not in raw
    assert parsed["source_reports"] == [str(spec.resolve())]
    assert parsed["evidence_paths_resolved"] is True
    assert parsed["powershell_safe_ascii_json"] is True


def test_missing_output_directory_is_created_under_existing_unicode_parent(tmp_path: Path) -> None:
    parent = tmp_path / "Masaüstü" / "ALKILIÇ"
    parent.mkdir(parents=True)
    target = parent / "reports"
    assert not target.exists()
    resolved = resolve_evidence_output_directory(str(target), field="out_dir")
    assert resolved == target.resolve()
    assert target.is_dir()
