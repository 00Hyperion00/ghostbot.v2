from __future__ import annotations

import json
from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_safe_exports_bind_to_hyp006_sources(tmp_path: Path) -> None:
    from tradebot.operator_cockpit_v2_read_only import _safe_action_manifest, _safe_latest_export_source

    hyp006_dir = tmp_path / "reports" / "hyp006_r1_canonical"
    legacy_dir = tmp_path / "reports" / "hyp005_r1_canonical"
    _write(hyp006_dir / "4B436628D_hyp006_r1_shadow_observation_logger_20260615T010000Z.json", "{}")
    _write(hyp006_dir / "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_20260615T010000Z.json", "{}")
    _write(hyp006_dir / "4B436628F_hyp006_r1_operator_cockpit_baseline_20260615T010000Z.json", "{}")
    _write(hyp006_dir / "4B436628D_hyp006_r1_shadow_ledger_20260615T010000Z.jsonl", "{}\n")
    _write(legacy_dir / "4B436625X_hyp005_shadow_merged_ledger_20260615_010000Z.jsonl", "{}\n")

    ledger = _safe_latest_export_source(tmp_path, "ledger")
    assert ledger is not None
    assert "hyp006_r1_canonical" in str(ledger)
    assert "hyp005" not in str(ledger).lower()

    manifest = _safe_action_manifest(tmp_path)
    exports = manifest["exports"]
    assert len(exports) == 4
    rendered = json.dumps(exports, ensure_ascii=False)
    assert "hyp006_r1_canonical" in rendered
    assert "hyp005_r1_canonical" not in rendered
    assert "latest-hyp006-shadow-ledger.jsonl" in rendered
    assert "latest-25" not in rendered


def test_hyp006_export_binding_helper_validates_manifest(tmp_path: Path) -> None:
    from tradebot.operator_cockpit_hyp006_export_binding import expected_export_manifest, export_source_parity_ok

    hyp006_dir = tmp_path / "reports" / "hyp006_r1_canonical"
    _write(hyp006_dir / "4B436628D_hyp006_r1_shadow_observation_logger_20260615T020000Z.json", "{}")
    _write(hyp006_dir / "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_20260615T020000Z.json", "{}")
    _write(hyp006_dir / "4B436628F_hyp006_r1_operator_cockpit_baseline_20260615T020000Z.json", "{}")
    _write(hyp006_dir / "4B436628D_hyp006_r1_shadow_ledger_20260615T020000Z.jsonl", "{}\n")

    exports = expected_export_manifest(tmp_path)
    assert export_source_parity_ok(exports)
    assert {item["kind"] for item in exports} == {"logger", "collection", "audit", "ledger"}
    assert all(item["branch_id"] == "HYP-006-R1" for item in exports)
    assert all(item["legacy_hyp005_source_suppressed"] is True for item in exports)


def test_paper_live_order_flags_remain_absent() -> None:
    from tradebot.operator_cockpit_hyp006_export_binding import OPERATOR_COCKPIT_HYP006_EXPORT_BINDING_VERSION

    assert OPERATOR_COCKPIT_HYP006_EXPORT_BINDING_VERSION == "4B.4.3.6.6.28F-H2"
