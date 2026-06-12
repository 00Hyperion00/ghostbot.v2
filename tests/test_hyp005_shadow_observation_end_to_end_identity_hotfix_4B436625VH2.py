from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tradebot.hyp005_shadow_observation_identity import (
    HYP005_SHADOW_OBSERVATION_END_TO_END_CANONICAL_IDENTITY,
    HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION,
    assert_artifact_equivalence,
    normalize_observation_identity,
    stable_observation_id,
)
from tradebot.research_hyp005_shadow_collection_orchestrator import merge_observations


def _row(*, ordinal: int = 235, symbol: str = "BNBUSDT", timestamp: str = "2026-06-05T04:00:00+00:00", entry: float = 593.26) -> dict[str, object]:
    return {
        "hypothesis_id": "HYP-005",
        "symbol": symbol,
        "timeframe": "4h",
        "timestamp_utc": timestamp,
        "observation_id": f"HYP-005-{symbol}-4h-{ordinal}-{timestamp.replace(':', '').replace('+00:00', 'Z')}",
        "strategy_family": "long_liquidity_sweep_reversal",
        "sweep_direction": "DOWNSIDE_SWEEP_LONG_REVERSAL",
        "entry_reference_price": entry,
        "no_order_shadow_only": True,
        "order_action": "NONE",
    }


def test_25vh2_declares_end_to_end_identity_contract() -> None:
    assert HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION == "4B.4.3.6.6.25V-H2"
    assert HYP005_SHADOW_OBSERVATION_END_TO_END_CANONICAL_IDENTITY is True


def test_25vh2_stable_id_ignores_rolling_ordinal() -> None:
    assert stable_observation_id(_row(ordinal=235)) == stable_observation_id(_row(ordinal=234))
    assert stable_observation_id(_row()) == "HYP-005-BNBUSDT-4h-2026-06-05T040000Z"


def test_25vh2_normalization_preserves_legacy_identity() -> None:
    normalized = normalize_observation_identity(_row())
    assert normalized["legacy_observation_id"] == _row()["observation_id"]
    assert normalized["observation_id"] == "HYP-005-BNBUSDT-4h-2026-06-05T040000Z"
    assert normalized["identity_contract_version"] == "4B.4.3.6.6.25V-H1"
    assert normalized["identity_chain_contract_version"] == "4B.4.3.6.6.25V-H2"


def test_25vh2_artifact_equivalence_fails_closed() -> None:
    baseline = [normalize_observation_identity(_row())]
    changed = [normalize_observation_identity(_row(symbol="BTCUSDT"))]
    assert_artifact_equivalence(baseline, list(baseline), list(baseline))
    with pytest.raises(ValueError, match="HYP005_IDENTITY_ARTIFACT_EQUIVALENCE_FAILED"):
        assert_artifact_equivalence(baseline, changed)


def test_25vh2_orchestrator_normalizes_and_deduplicates_by_canonical_event() -> None:
    merged, duplicates = merge_observations([[_row(ordinal=235, entry=593.26)], [_row(ordinal=234, entry=593.27)]])
    assert duplicates == 1
    assert len(merged) == 1
    assert merged[0]["observation_id"] == "HYP-005-BNBUSDT-4h-2026-06-05T040000Z"
    assert merged[0]["legacy_observation_id"].startswith("HYP-005-BNBUSDT-4h-")


def _copy_wrapper_fixture(project: Path) -> tuple[Path, Path]:
    source_root = Path(__file__).resolve().parents[1]
    tools = project / "tools"
    src = project / "src" / "tradebot"
    reports = project / "reports" / "hyp005_r1_canonical"
    tools.mkdir(parents=True)
    src.mkdir(parents=True)
    reports.mkdir(parents=True)
    shutil.copy2(source_root / "src/tradebot/hyp005_shadow_observation_identity.py", src / "hyp005_shadow_observation_identity.py")
    (src / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy2(source_root / "tools/run_hyp005_shadow_observation_logger_4B436625V.py", tools / "run_hyp005_shadow_observation_logger_4B436625V.py")
    legacy = tools / "run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py"
    legacy.write_text(
        """from __future__ import annotations
import argparse, json
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--out-dir', type=Path, required=True); p.add_argument('--ordinal', type=int, required=True); a=p.parse_args()
a.out_dir.mkdir(parents=True, exist_ok=True)
stamp=str(a.ordinal)
row={'hypothesis_id':'HYP-005','symbol':'BNBUSDT','timeframe':'4h','timestamp_utc':'2026-06-05T04:00:00+00:00','observation_id':f'HYP-005-BNBUSDT-4h-{a.ordinal}-2026-06-05T040000Z0000','strategy_family':'long_liquidity_sweep_reversal','sweep_direction':'DOWNSIDE_SWEEP_LONG_REVERSAL','entry_reference_price':593.26,'no_order_shadow_only':True,'order_action':'NONE'}
ledger=a.out_dir / f'4B436625V_hyp005_shadow_observation_ledger_{stamp}'
(ledger.with_suffix('.json')).write_text(json.dumps([row]), encoding='utf-8')
(ledger.with_suffix('.jsonl')).write_text(json.dumps(row)+'\\n', encoding='utf-8')
report={'decision':'HYP005_SHADOW_OBSERVATION_LOGGER_READY','shadow_observations':[row]}
(a.out_dir / f'4B436625V_hyp005_shadow_observation_logger_{stamp}.json').write_text(json.dumps(report), encoding='utf-8')
""",
        encoding="utf-8",
    )
    return tools / "run_hyp005_shadow_observation_logger_4B436625V.py", reports


def test_25vh2_wrapper_aligns_json_jsonl_and_report(tmp_path: Path) -> None:
    wrapper, reports = _copy_wrapper_fixture(tmp_path / "trade_botV2")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(wrapper.parents[1] / "src")
    completed = subprocess.run(
        [sys.executable, str(wrapper), "--out-dir", str(reports), "--ordinal", "235"],
        cwd=wrapper.parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    json_rows = json.loads(next(reports.glob("*ledger_235.json")).read_text(encoding="utf-8"))
    jsonl_rows = [json.loads(line) for line in next(reports.glob("*ledger_235.jsonl")).read_text(encoding="utf-8").splitlines()]
    report = json.loads(next(reports.glob("*logger_235.json")).read_text(encoding="utf-8"))
    assert json_rows == jsonl_rows == report["shadow_observations"]
    assert report["identity_artifact_equivalence_verified"] is True
    assert json_rows[0]["observation_id"] == "HYP-005-BNBUSDT-4h-2026-06-05T040000Z"


def test_25vh2_orchestrator_runner_declares_jsonl_single_source() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py").read_text(encoding="utf-8")
    assert 'HYP005_CANONICAL_LEDGER_JSONL_SINGLE_SOURCE = True' in text
    assert 'ledger_json_paths = []' in text


def test_25vh2_chain_checker_passes_for_aligned_bundle_and_merged_ledger(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    reports = tmp_path / "reports"
    reports.mkdir()
    row = normalize_observation_identity(_row())
    (reports / "4B436625V_hyp005_shadow_observation_ledger_20260610_120000.json").write_text(json.dumps([row]), encoding="utf-8")
    (reports / "4B436625V_hyp005_shadow_observation_ledger_20260610_120000.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    logger = {"shadow_observations": [row], "identity_contract_version": "4B.4.3.6.6.25V-H1", "identity_chain_contract_version": "4B.4.3.6.6.25V-H2", "canonical_identity_end_to_end": True, "identity_artifact_equivalence_verified": True}
    (reports / "4B436625V_hyp005_shadow_observation_logger_20260610_120000.json").write_text(json.dumps(logger), encoding="utf-8")
    (reports / "4B436625X_hyp005_shadow_merged_ledger_20260610_120000.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    checker = root / "tools/check_hyp005_shadow_observation_identity_chain_4B436625VH2.py"
    completed = subprocess.run([sys.executable, str(checker), "--reports-dir", str(reports), "--require-runtime-chain", "--once-json"], cwd=root, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["active_runtime_chain_ready"] is True


def test_25vh2_chain_checker_blocks_legacy_merged_ledger(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    reports = tmp_path / "reports"
    reports.mkdir()
    canonical = normalize_observation_identity(_row())
    legacy = _row()
    (reports / "4B436625V_hyp005_shadow_observation_ledger_20260610_120000.json").write_text(json.dumps([canonical]), encoding="utf-8")
    (reports / "4B436625V_hyp005_shadow_observation_ledger_20260610_120000.jsonl").write_text(json.dumps(canonical) + "\n", encoding="utf-8")
    logger = {"shadow_observations": [canonical], "identity_contract_version": "4B.4.3.6.6.25V-H1", "identity_chain_contract_version": "4B.4.3.6.6.25V-H2", "canonical_identity_end_to_end": True, "identity_artifact_equivalence_verified": True}
    (reports / "4B436625V_hyp005_shadow_observation_logger_20260610_120000.json").write_text(json.dumps(logger), encoding="utf-8")
    (reports / "4B436625X_hyp005_shadow_merged_ledger_20260610_120000.jsonl").write_text(json.dumps(legacy) + "\n", encoding="utf-8")
    checker = root / "tools/check_hyp005_shadow_observation_identity_chain_4B436625VH2.py"
    completed = subprocess.run([sys.executable, str(checker), "--reports-dir", str(reports), "--require-runtime-chain", "--once-json"], cwd=root, text=True, capture_output=True, check=False)
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["merged_ledger_canonical"] is False
    assert payload["active_runtime_chain_ready"] is False
