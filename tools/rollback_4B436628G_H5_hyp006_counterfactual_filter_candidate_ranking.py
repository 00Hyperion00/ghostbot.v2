from __future__ import annotations

from pathlib import Path

FILES = [
    "src/tradebot/hyp006_counterfactual_filter_candidate_ranking.py",
    "tools/run_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py",
    "tools/apply_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py",
    "tools/check_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py",
    "tools/rollback_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py",
    "tests/test_hyp006_counterfactual_filter_candidate_ranking_4B436628G_H5.py",
    "docs/HYP006_R1_COUNTERFACTUAL_FILTER_CANDIDATE_RANKING_4B436628G_H5.md",
    "README_APPLY_4B436628G_H5.txt",
]


def main() -> int:
    root = Path.cwd()
    removed = []
    for name in FILES:
        path = root / name
        if path.exists():
            path.unlink()
            removed.append(name)
    print("4B.4.3.6.6.28G-H5 rollback removed files:")
    for name in removed:
        print(f" - {name}")
    print("No config, scheduler, training, reload, trading, or order state was touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
