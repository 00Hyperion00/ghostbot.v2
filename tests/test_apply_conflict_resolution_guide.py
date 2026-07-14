from __future__ import annotations

from pathlib import Path


def test_conflict_resolution_guide_covers_reported_conflict_set() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs/ARCHITECTURE_CONFLICT_RESOLUTION.md").read_text(encoding="utf-8")

    for path in (
        "README.md",
        "docs/ARCHITECTURE.md",
        "src/tradebot/strategy.py",
        "tests/test_strategy_ai_merge.py",
    ):
        assert path in text

    assert "AI_PROVIDER_PREDICT_FAILED" in text
    assert "aiProviderError" in text
    assert "tools/check_apply_conflict_resolution.py" in text
    assert "PYTHONPATH=src pytest -q tests/test_strategy_ai_merge.py" in text
