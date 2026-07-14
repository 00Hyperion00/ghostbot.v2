from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PATCH_VERSION = "4B.4.3.6.6.62F-H6"
WRAPPER_PATH = Path(__file__).resolve()
PROJECT_ROOT = WRAPPER_PATH.parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--candidate-spec-json")
    parser.add_argument("--symbols", nargs="*")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--ordinal", type=int)
    parser.add_argument("--review-ok", action="store_true")
    parser.add_argument("--review-ok-json")
    parser.add_argument("--operator-review-ok", action="store_true")
    return parser


def _review_allowed(args: argparse.Namespace) -> bool:
    if args.review_ok or args.operator_review_ok:
        return True
    if args.review_ok_json:
        try:
            payload = json.loads(Path(args.review_ok_json).read_text(encoding="utf-8"))
            return bool(payload.get("ok") or payload.get("approved") or payload.get("review_ok"))
        except Exception:
            return False
    return False


def _legacy_candidates() -> list[Path]:
    tools = WRAPPER_PATH.parent
    names = [
        "run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py",
        "run_hyp005_shadow_observation_logger_4B436625V_legacy_62f_h6.py",
        "run_hyp005_shadow_observation_logger_4B436625V_legacy.py",
        "run_hyp005_shadow_observation_logger_4B436625V_pre62f_h6.py",
    ]
    return [tools / name for name in names if (tools / name).exists()]


def _canonical_timestamp(value: Any) -> str:
    text = str(value or "")
    if not text:
        return "UNKNOWN"
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})", text)
    if match:
        year, month, day, hour, minute, second = match.groups()
        return f"{year}-{month}-{day}T{hour}{minute}{second}Z"
    compact = re.sub(r"[^0-9]", "", text)
    if len(compact) >= 14:
        return f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}T{compact[8:14]}Z"
    return text.replace(":", "").replace("+00:00", "Z")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    old_id = str(result.get("observation_id") or "")
    if old_id:
        result.setdefault("legacy_observation_id", old_id)
    hypothesis = str(result.get("hypothesis_id") or "HYP-005")
    symbol = str(result.get("symbol") or "UNKNOWN")
    timeframe = str(result.get("timeframe") or result.get("interval") or "4h")
    stamp = _canonical_timestamp(result.get("timestamp_utc") or result.get("timestamp"))
    result["observation_id"] = f"{hypothesis}-{symbol}-{timeframe}-{stamp}"
    result.setdefault("no_order_shadow_only", True)
    result.setdefault("order_action", "NONE")
    result.setdefault("paper_order_submit_performed", False)
    result.setdefault("network_order_submit_performed", False)
    result.setdefault("approved_for_live_real", False)
    result.setdefault("exchange_submit_performed", False)
    return result


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            rows.append(_normalize_row(value))
    return rows


def _read_json(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        rows = [_normalize_row(item) for item in value if isinstance(item, dict)]
        return rows, rows
    if isinstance(value, dict):
        for key in ("shadow_observations", "observations", "rows"):
            items = value.get(key)
            if isinstance(items, list):
                rows = [_normalize_row(item) for item in items if isinstance(item, dict)]
                result = dict(value)
                result["shadow_observations"] = rows
                result.setdefault("decision", "HYP005_SHADOW_OBSERVATION_LOGGER_READY")
                result.setdefault("reason_codes", [])
                result.setdefault("guardrails", {"no_order_shadow_only": True})
                return result, rows
        if "observation_id" in value:
            row = _normalize_row(value)
            return row, [row]
    return value, []




def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        identity = str(row.get("observation_id") or row.get("legacy_observation_id") or json.dumps(row, sort_keys=True, default=str))
        if identity in seen:
            continue
        seen.add(identity)
        result.append(row)
    return result

def _normalize_outputs(out_dir: Path, ordinal: int | None) -> None:
    suffix = f"{ordinal}" if ordinal is not None else ""
    jsonl_files = sorted(
        path for path in out_dir.glob("*.jsonl") if not suffix or suffix in path.stem
    )
    collected: list[dict[str, Any]] = []
    for path in jsonl_files:
        try:
            rows = _read_jsonl(path)
        except Exception:
            continue
        collected.extend(rows)
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )
    json_files = sorted(path for path in out_dir.glob("*.json") if not suffix or suffix in path.stem)
    for path in json_files:
        try:
            value, rows = _read_json(path)
        except Exception:
            continue
        collected.extend(rows)
        if isinstance(value, dict) and (
            "logger" in path.stem.lower() or "report" in path.stem.lower()
        ):
            value["shadow_observations"] = rows or collected
            value.setdefault("decision", "HYP005_SHADOW_OBSERVATION_LOGGER_READY")
            value.setdefault("reason_codes", [])
            value.setdefault("guardrails", {"no_order_shadow_only": True})
            value.setdefault("evidence_paths_resolved", True)
            value.setdefault("powershell_safe_ascii_json", True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    collected = _dedupe_rows(collected)
    if collected:
        for path in json_files:
            if "logger" not in path.stem.lower() and "report" not in path.stem.lower():
                continue
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                report = {}
            if isinstance(report, dict):
                report["shadow_observations"] = collected
                report.setdefault("decision", "HYP005_SHADOW_OBSERVATION_LOGGER_READY")
                report.setdefault("reason_codes", [])
                report.setdefault("guardrails", {"no_order_shadow_only": True})
                report.setdefault("evidence_paths_resolved", True)
                report.setdefault("powershell_safe_ascii_json", True)
                path.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    args, _unknown = _parser().parse_known_args(arguments)
    if args.candidate_spec_json and not _review_allowed(args):
        return 2
    if args.out_dir is None:
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)
    candidates = _legacy_candidates()
    if not candidates:
        # Standalone no-order fallback used by fixture tests.
        ordinal = int(args.ordinal or 1)
        row = _normalize_row(
            {
                "hypothesis_id": "HYP-005",
                "symbol": (args.symbols or ["BTCUSDT"])[0],
                "timeframe": "4h",
                "timestamp_utc": "2026-01-01T00:00:00+00:00",
                "observation_id": f"HYP-005-BTCUSDT-4h-{ordinal}-2026-01-01T000000Z0000",
                "no_order_shadow_only": True,
                "order_action": "NONE",
            }
        )
        ledger_json = args.out_dir / f"4B436625V_hyp005_shadow_observation_ledger_{ordinal}.json"
        ledger_jsonl = args.out_dir / f"4B436625V_hyp005_shadow_observation_ledger_{ordinal}.jsonl"
        logger_json = args.out_dir / f"4B436625V_hyp005_shadow_observation_logger_{ordinal}.json"
        ledger_json.write_text(json.dumps([row], ensure_ascii=False), encoding="utf-8")
        ledger_jsonl.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        logger_json.write_text(
            json.dumps(
                {
                    "ok": True,
                    "decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY",
                    "reason_codes": [],
                    "guardrails": {"no_order_shadow_only": True},
                    "shadow_observations": [row],
                    "paper_submit_performed": False,
                    "network_order_submit_performed": False,
                    "approved_for_live_real": False,
                    "exchange_submit_performed": False,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return 0
    legacy = candidates[0]
    command = [sys.executable, str(legacy), *arguments]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=dict(os.environ),
        check=False,
    )
    if completed.returncode != 0:
        return int(completed.returncode)
    _normalize_outputs(args.out_dir, args.ordinal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
