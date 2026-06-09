from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tradebot.hyp005_shadow_observation_identity import (
    HYP005_SHADOW_OBSERVATION_ROLLING_ORDINAL_DISABLED,
    HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY,
    HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_VERSION,
    canonical_event_key,
    normalize_jsonl_file,
    normalize_observation_identity,
    stable_observation_id,
)


def _row(*, symbol: str = "BNBUSDT", timestamp: str = "2026-06-05T04:00:00+00:00", ordinal: int = 235) -> dict[str, object]:
    return {
        "hypothesis_id": "HYP-005",
        "symbol": symbol,
        "timeframe": "4h",
        "timestamp_utc": timestamp,
        "observation_id": f"HYP-005-{symbol}-4h-{ordinal}-{timestamp.replace(':', '').replace('+00:00', 'Z')}",
        "no_order_shadow_only": True,
        "order_action": "NONE",
    }


def test_25vh1_declares_stable_identity_and_disables_rolling_ordinal() -> None:
    assert HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_VERSION == "4B.4.3.6.6.25V-H1"
    assert HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY is True
    assert HYP005_SHADOW_OBSERVATION_ROLLING_ORDINAL_DISABLED is True


def test_25vh1_same_event_has_same_identity_across_rolling_positions() -> None:
    assert stable_observation_id(_row(ordinal=235)) == stable_observation_id(_row(ordinal=234))
    assert stable_observation_id(_row(ordinal=235)) == "HYP-005-BNBUSDT-4h-2026-06-05T040000Z"


def test_25vh1_symbol_or_timestamp_change_produces_distinct_identity() -> None:
    baseline = stable_observation_id(_row())
    assert stable_observation_id(_row(symbol="BTCUSDT")) != baseline
    assert stable_observation_id(_row(timestamp="2026-06-05T08:00:00+00:00")) != baseline


def test_25vh1_normalization_preserves_legacy_id_for_auditability() -> None:
    source = _row(ordinal=235)
    normalized = normalize_observation_identity(source)
    assert normalized["legacy_observation_id"] == source["observation_id"]
    assert normalized["observation_id"] == "HYP-005-BNBUSDT-4h-2026-06-05T040000Z"
    assert normalized["identity_event_key"] == "HYP-005|BNBUSDT|4h|2026-06-05T040000Z"
    assert normalized["identity_contract_version"] == "4B.4.3.6.6.25V-H1"
    assert source["observation_id"] != normalized["observation_id"]


def test_25vh1_normalize_jsonl_file_is_atomic_and_idempotent(tmp_path: Path) -> None:
    ledger = tmp_path / "4B436625V_hyp005_shadow_observation_ledger_20260609_120009.jsonl"
    ledger.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
    assert normalize_jsonl_file(ledger) == 1
    first = ledger.read_text(encoding="utf-8")
    assert normalize_jsonl_file(ledger) == 0
    assert ledger.read_text(encoding="utf-8") == first
    assert not list(tmp_path.glob("*.tmp"))


def test_25vh1_canonical_count_remains_stable_when_raw_ordinal_drifts() -> None:
    previous = [_row(symbol="BNBUSDT", ordinal=235), _row(symbol="BTCUSDT", ordinal=216)]
    current = [_row(symbol="BNBUSDT", ordinal=234), _row(symbol="BTCUSDT", ordinal=215)]
    assert {canonical_event_key(row) for row in previous} == {canonical_event_key(row) for row in current}
    assert {stable_observation_id(row) for row in previous} == {stable_observation_id(row) for row in current}


def test_25vh1_wrapper_normalizes_new_ledger_after_legacy_runner(tmp_path: Path) -> None:
    project = tmp_path / "trade_botV2"
    tools = project / "tools"
    src = project / "src" / "tradebot"
    reports = project / "reports" / "hyp005_r1_isolated"
    tools.mkdir(parents=True)
    src.mkdir(parents=True)
    reports.mkdir(parents=True)
    source_root = Path(__file__).resolve().parents[1]
    shutil.copy2(source_root / "src/tradebot/hyp005_shadow_observation_identity.py", src / "hyp005_shadow_observation_identity.py")
    (src / "__init__.py").write_text("", encoding="utf-8")
    legacy = tools / "run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py"
    legacy.write_text(
        """from __future__ import annotations\nimport argparse, json\nfrom pathlib import Path\np=argparse.ArgumentParser(); p.add_argument('--out-dir', type=Path, required=True); p.add_argument('--ordinal', type=int, required=True); a=p.parse_args()\na.out_dir.mkdir(parents=True, exist_ok=True)\nrow={'hypothesis_id':'HYP-005','symbol':'BNBUSDT','timeframe':'4h','timestamp_utc':'2026-06-05T04:00:00+00:00','observation_id':f'HYP-005-BNBUSDT-4h-{a.ordinal}-2026-06-05T040000Z0000','no_order_shadow_only':True,'order_action':'NONE'}\n(a.out_dir / f'4B436625V_hyp005_shadow_observation_ledger_{a.ordinal}.jsonl').write_text(json.dumps(row)+'\\n', encoding='utf-8')\n""",
        encoding="utf-8",
    )
    wrapper = tools / "run_hyp005_shadow_observation_logger_4B436625V.py"
    shutil.copy2(source_root / "tools/_patch_payload/run_hyp005_shadow_observation_logger_4B436625V_stable_identity_wrapper.py", wrapper)
    env = {"PYTHONPATH": str(project / "src")}
    for ordinal in (235, 234):
        completed = subprocess.run(
            [sys.executable, str(wrapper), "--out-dir", str(reports), "--ordinal", str(ordinal)],
            cwd=project,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
    rows = []
    for path in sorted(reports.glob("*.jsonl")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    assert {row["observation_id"] for row in rows} == {"HYP-005-BNBUSDT-4h-2026-06-05T040000Z"}
    assert {row["legacy_observation_id"] for row in rows} == {
        "HYP-005-BNBUSDT-4h-235-2026-06-05T040000Z0000",
        "HYP-005-BNBUSDT-4h-234-2026-06-05T040000Z0000",
    }


def test_25vh1_rejects_missing_identity_fields() -> None:
    with pytest.raises(ValueError, match="HYP005_STABLE_IDENTITY_MISSING_FIELD:symbol"):
        stable_observation_id({"hypothesis_id": "HYP-005", "timeframe": "4h", "timestamp_utc": "2026-06-05T04:00:00+00:00"})
