from __future__ import annotations

from pathlib import Path

from tradebot.replay_gate import build_walk_forward_windows, deterministic_decision_replay_digest, evaluate_oos_report_gate, hash_model_artifact, load_last_known_good_registry, register_last_known_good_model, verify_replay_digest


def test_deterministic_replay_digest_is_stable() -> None:
    rows_a = [{"ts": 1, "signal": "HOLD", "score": 0.12}, {"signal": "SELL", "ts": 2, "score": 0.81}]
    rows_b = [{"score": 0.12, "signal": "HOLD", "ts": 1}, {"score": 0.81, "ts": 2, "signal": "SELL"}]
    digest_a = deterministic_decision_replay_digest(rows_a)
    digest_b = deterministic_decision_replay_digest(rows_b)
    assert digest_a.digest == digest_b.digest
    assert verify_replay_digest(rows_b, digest_a.digest).ok is True


def test_model_artifact_hash_and_lkg_registry(tmp_path: Path) -> None:
    model = tmp_path / "model.ubj"
    model.write_bytes(b"stable-model-bytes")
    manifest = hash_model_artifact(model, metadata={"symbol": "BNBUSDT"})
    registry_path = tmp_path / "last_known_good_model_registry.json"
    registry = register_last_known_good_model(registry_path, manifest, reason="OOS_GATE_ACCEPTED_FOR_REVIEW_ONLY", gate_snapshot={"approved_for_live_real": False})
    loaded = load_last_known_good_registry(registry_path)
    assert registry["latest"]["manifest"]["sha256"] == manifest.sha256
    assert loaded["latest"]["manifest"]["metadata"]["symbol"] == "BNBUSDT"


def test_oos_gate_blocks_runtime_even_when_review_candidate() -> None:
    decision = evaluate_oos_report_gate({"matured_count": 31, "win_rate_pct": 65.0, "profit_factor": 1.8, "mean_return_bps": 12.5, "worst_return_bps": -220.0, "worst_mae_bps": -300.0, "unique_oos_days": 3, "regime_count": 2, "measurement_guard_pass": True})
    assert decision.approved_for_promotion_review_candidate is True
    assert decision.approved_for_runtime_overlay_activation_candidate is False
    assert decision.approved_for_paper_candidate is False
    assert decision.approved_for_live_real is False


def test_oos_gate_rejects_small_sample_and_tail_risk() -> None:
    decision = evaluate_oos_report_gate({"matured_count": 13, "win_rate_pct": 76.9, "profit_factor": 5.4, "mean_return_bps": 126.6, "worst_return_bps": -312.0, "worst_mae_bps": -426.0, "unique_oos_days": 1, "regime_count": 1, "tail_risk_worsened": True})
    assert decision.approved_for_promotion_review_candidate is False
    assert "OOS_MATURED_COUNT_BELOW_MIN" in decision.reason_codes
    assert "OOS_TAIL_RISK_WORSENED" in decision.reason_codes


def test_walk_forward_windows_are_deterministic() -> None:
    windows = build_walk_forward_windows(total_samples=100, train_size=40, test_size=10, step_size=10)
    assert [w.to_dict() for w in windows[:2]] == [
        {"window_id": 1, "train_start": 0, "train_end": 40, "test_start": 40, "test_end": 50},
        {"window_id": 2, "train_start": 10, "train_end": 50, "test_start": 50, "test_end": 60},
    ]
