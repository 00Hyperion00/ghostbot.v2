from __future__ import annotations

import argparse
import importlib.util
import json
import py_compile
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29D"
EXPECTED_FILES = [
    "src/tradebot/replay_gate.py",
    "tests/test_replay_backtest_walkforward_gate_4B436629D.py",
    "tools/apply_4B436629D_replay_backtest_walkforward_gate.py",
    "tools/check_4B436629D_replay_backtest_walkforward_gate.py",
    "tools/run_4B436629D_replay_backtest_walkforward_gate.py",
    "tools/rollback_4B436629D_replay_backtest_walkforward_gate.py",
    "docs/REPLAY_BACKTEST_WALKFORWARD_GATE_4B436629D.md",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _load(root: Path):
    spec = importlib.util.spec_from_file_location("tradebot.replay_gate", root / "src/tradebot/replay_gate.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load replay_gate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _probe(root: Path) -> dict[str, Any]:
    module = _load(root)
    rows = [{"ts": 1, "signal": "HOLD"}, {"ts": 2, "signal": "SELL"}]
    digest = module.deterministic_decision_replay_digest(rows)
    verify = module.verify_replay_digest(rows, digest.digest)
    decision = module.evaluate_oos_report_gate({
        "matured_count": 31,
        "win_rate_pct": 65.0,
        "profit_factor": 1.9,
        "mean_return_bps": 11.0,
        "worst_return_bps": -200.0,
        "worst_mae_bps": -250.0,
        "unique_oos_days": 3,
        "regime_count": 2,
        "measurement_guard_pass": True,
    })
    blocked = module.evaluate_oos_report_gate({"matured_count": 13, "tail_risk_worsened": True})
    windows = module.build_walk_forward_windows(total_samples=80, train_size=40, test_size=10, step_size=10)
    with tempfile.TemporaryDirectory() as tmp:
        model = Path(tmp) / "model.ubj"
        model.write_bytes(b"probe-model")
        manifest = module.hash_model_artifact(model)
        registry = module.register_last_known_good_model(Path(tmp) / "lkg.json", manifest, reason="PROBE")
    return {
        "ok": bool(verify.ok and decision.approved_for_promotion_review_candidate and not decision.approved_for_live_real and not blocked.approved_for_promotion_review_candidate and windows and registry.get("latest")),
        "digest_ok": bool(verify.ok),
        "review_candidate_only": bool(decision.approved_for_promotion_review_candidate and not decision.approved_for_live_real),
        "small_sample_blocked": "OOS_MATURED_COUNT_BELOW_MIN" in blocked.reason_codes,
        "tail_risk_blocked": "OOS_TAIL_RISK_WORSENED" in blocked.reason_codes,
        "walk_forward_window_count": len(windows),
        "model_hash_len": len(manifest.sha256),
        "registry_latest_present": bool(registry.get("latest")),
    }


def build_report(root: Path) -> dict[str, Any]:
    expected = {path: (root / path).exists() for path in EXPECTED_FILES}
    compiled = {path: _compile(root / path) for path in EXPECTED_FILES if path.endswith(".py") and (root / path).exists()}
    config_text = _read(root / "src/tradebot/config.py")
    module_text = _read(root / "src/tradebot/replay_gate.py")
    try:
        probe = _probe(root)
    except Exception as exc:
        probe = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) if compiled else False,
        "contract_version_ok": f'REPLAY_GATE_CONTRACT_VERSION = "{CONTRACT_VERSION}"' in module_text,
        "deterministic_replay_digest_present": "deterministic_decision_replay_digest" in module_text,
        "model_artifact_hash_present": "hash_model_artifact" in module_text and "sha256" in module_text,
        "last_known_good_registry_present": "register_last_known_good_model" in module_text,
        "walk_forward_gate_present": "build_walk_forward_windows" in module_text,
        "oos_report_gate_present": "evaluate_oos_report_gate" in module_text,
        "promotion_review_only_guard_present": "approved_for_promotion_review_candidate" in module_text and "approved_for_live_real=False" in module_text,
        "config_replay_gate_fields_present": "replay_gate_enabled" in config_text and "last_known_good_model_registry_path" in config_text,
        "module_probe_ok": bool(probe.get("ok")),
        "runtime_activation_blocked": "approved_for_runtime_overlay_activation_candidate=False" in module_text,
        "paper_live_order_blocked": "approved_for_paper_candidate=False" in module_text and "approved_for_live_real=False" in module_text,
        "training_reload_blocked": "training_reload_blocked=True" in module_text,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "replay_backtest_walkforward_gate": True,
        "expected_files": expected,
        "compiled": compiled,
        "checks": checks,
        "module_probe": probe,
        "hyp006_strategy_threshold_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    parser.parse_args()
    report = build_report(Path.cwd())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
